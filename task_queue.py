import json
import os
import logging
import uuid
from datetime import datetime, timedelta, date
from threading import Thread, Lock
from queue import Queue, Empty
from time import sleep
from sqlalchemy.orm import joinedload
from app import app, db
from models import SurveyResponse, Campaign, BusinessAccount, EmailDelivery, CampaignParticipant, Participant
from ai_analysis import analyze_survey_response
from email_service import email_service

logger = logging.getLogger(__name__)

# LLM Gateway support for transcript analysis
# Cached gateway instance per worker process (avoids repeated construction)
_cached_transcript_gateway = None
_gateway_cache_checked = False

def _get_transcript_gateway():
    """Get cached LLM gateway for transcript analysis if enabled.
    
    Uses module-level caching to avoid repeated gateway construction
    within the same worker process. Thread-safe as each worker process
    has its own memory space.
    
    Retry behavior: Only caches when gateway is successfully created or
    explicitly disabled. Transient failures allow retry on next call.
    """
    global _cached_transcript_gateway, _gateway_cache_checked
    
    # Return cached instance if already successfully initialized
    if _cached_transcript_gateway is not None:
        return _cached_transcript_gateway
    
    # Skip repeated checks if gateway is disabled (not due to error)
    if _gateway_cache_checked:
        return None
    
    try:
        from llm_gateway import LLMGateway, is_gateway_enabled
        if is_gateway_enabled():
            _cached_transcript_gateway = LLMGateway()
            logger.info("LLM gateway initialized and cached for transcript analysis")
            return _cached_transcript_gateway
        else:
            # Gateway explicitly disabled - don't retry
            _gateway_cache_checked = True
            logger.debug("LLM gateway disabled, will use direct OpenAI for transcripts")
            return None
    except ImportError:
        # Module not available - don't retry
        _gateway_cache_checked = True
        logger.debug("LLM gateway not available, using direct OpenAI")
        return None
    except Exception as e:
        # Transient error - allow retry on next call
        logger.warning(f"Failed to initialize LLM gateway for transcripts: {e}")
        return None

class TaskQueue:
    """Simple in-memory task queue for processing AI analysis tasks with campaign scheduler"""
    
    def __init__(self, max_workers=5):
        self.task_queue = Queue()
        self.max_workers = max_workers
        self.workers = []
        self.running = False
        self.scheduler_thread = None
        self.last_scheduler_run = None
        self.scheduler_interval = 300  # 5 minutes in seconds
        self.last_reconciliation_run = None
        self.reconciliation_interval = 86400  # 24 hours in seconds (nightly)
        
    def start(self):
        """Start the task queue workers and scheduler"""
        if self.running:
            return
            
        self.running = True
        logger.info(f"Starting task queue with {self.max_workers} workers")
        
        for i in range(self.max_workers):
            worker = Thread(target=self._worker, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
        
        # Start the campaign scheduler
        self.scheduler_thread = Thread(target=self._scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Campaign scheduler started")
    
    def stop(self):
        """Stop the task queue workers and scheduler"""
        self.running = False
        logger.info("Stopping task queue and scheduler")
    
    def add_task(self, task_type, data_id=None, priority=1, task_data=None):
        """Add a task to the queue
        
        Args:
            task_type: Type of task ('ai_analysis', 'send_email', etc.)
            data_id: ID for data-based tasks (response_id for AI analysis)
            priority: Task priority (higher = more important)  
            task_data: Additional data for the task (email details, etc.)
        """
        task = {
            'type': task_type,
            'data_id': data_id,  # Backward compatible with response_id
            'priority': priority,
            'created_at': datetime.utcnow(),
            'task_data': task_data or {}
        }
        
        self.task_queue.put(task)
        
        # Log differently based on task type
        if task_type == 'send_email':
            email_type = task_data.get('email_type', 'unknown') if task_data else 'unknown'
            logger.info(f"Added email task ({email_type}) to queue")
        elif task_type == 'executive_report':
            campaign_id = task_data.get('campaign_id', 'unknown') if task_data else 'unknown'
            logger.info(f"Added executive report task for campaign {campaign_id} to queue")
        elif task_type == 'transcript_analysis':
            campaign_id = task_data.get('campaign_id', 'unknown') if task_data else 'unknown'
            participant_name = task_data.get('participant_name', 'unknown') if task_data else 'unknown'
            logger.info(f"Added transcript analysis task for campaign {campaign_id}, participant {participant_name}")
        elif task_type == 'qbr_analysis':
            session_id = task_data.get('session_id', 'unknown') if task_data else 'unknown'
            company_name = task_data.get('company_name', 'unknown') if task_data else 'unknown'
            logger.info(f"Added QBR analysis task for session {session_id} ({company_name})")
        else:
            logger.info(f"Added task {task_type} for data_id {data_id}")
    
    def _worker(self, worker_id):
        """Worker function that processes tasks from the queue"""
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get task from queue with timeout
                task = self.task_queue.get(timeout=1)
                
                logger.info(f"Worker {worker_id} processing task: {task}")
                
                # Process the task
                with app.app_context():
                    self._process_task(task, worker_id)
                
                # Mark task as done
                self.task_queue.task_done()
                
            except Empty:
                # No tasks available, continue
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error processing task: {e}")
                # Mark task as done even if failed
                self.task_queue.task_done()
    
    def _process_task(self, task, worker_id):
        """Process a single task"""
        try:
            task_type = task['type']
            data_id = task.get('data_id') or task.get('response_id')  # Backward compatibility
            task_data = task.get('task_data', {})
            
            if task_type == 'ai_analysis':
                # Perform AI analysis
                success = analyze_survey_response(data_id)
                
                if success:
                    logger.info(f"Worker {worker_id} completed AI analysis for response {data_id}")
                else:
                    logger.error(f"Worker {worker_id} failed AI analysis for response {data_id}")
                    
                    # Mark as failed in database
                    response = SurveyResponse.query.get(data_id)
                    if response:
                        response.analyzed_at = datetime.utcnow()
                        response.sentiment_label = 'analysis_failed'
                        db.session.commit()
                        
            elif task_type == 'send_email':
                # Process email sending task
                success = self._process_email_task(task_data, worker_id)
                
                if success:
                    email_type = task_data.get('email_type', 'unknown')
                    logger.info(f"Worker {worker_id} completed email task ({email_type})")
                else:
                    logger.error(f"Worker {worker_id} failed email task")
                    
            elif task_type == 'audit_log':
                # Process audit log writing task
                success = self._process_audit_log_task(task_data, worker_id)
                
                if success:
                    action_type = task_data.get('action_type', 'unknown')
                    logger.debug(f"Worker {worker_id} completed audit log ({action_type})")
                else:
                    logger.error(f"Worker {worker_id} failed audit log task")
                    
            elif task_type == 'export_campaign':
                # Process campaign export task (unified async pattern using BulkOperationJob)
                success = self._process_export_campaign_task(task_data, worker_id)
                
                if success:
                    campaign_id = task_data.get('campaign_id', 'unknown')
                    logger.info(f"Worker {worker_id} completed campaign export for campaign {campaign_id}")
                else:
                    logger.error(f"Worker {worker_id} failed campaign export task")
                    
            elif task_type == 'executive_report':
                # Process executive report generation task
                success = self._process_executive_report_task(task_data, worker_id)
                
                if success:
                    campaign_id = task_data.get('campaign_id', 'unknown')
                    logger.info(f"Worker {worker_id} completed executive report for campaign {campaign_id}")
                else:
                    logger.error(f"Worker {worker_id} failed executive report task")
                    
            elif task_type == 'transcript_analysis':
                # Process transcript analysis task
                success = self._process_transcript_analysis_task(task_data, worker_id)
                
                if success:
                    campaign_id = task_data.get('campaign_id', 'unknown')
                    participant_name = task_data.get('participant_name', 'unknown')
                    logger.info(f"Worker {worker_id} completed transcript analysis for campaign {campaign_id}, participant {participant_name}")
                else:
                    logger.error(f"Worker {worker_id} failed transcript analysis task")
                    
            elif task_type == 'send_reminder_email':
                # Process reminder email task (EmailDelivery record already created)
                success = self._process_reminder_email_task(task_data, worker_id)
                
                if success:
                    participant_email = task_data.get('participant_email', 'unknown')
                    logger.info(f"Worker {worker_id} completed reminder email to {participant_email}")
                else:
                    logger.error(f"Worker {worker_id} failed reminder email task")
                    
            elif task_type == 'bulk_participant_add':
                # Process bulk participant addition task
                success = self._process_bulk_participant_add_task(task_data, worker_id)
                
                if success:
                    campaign_id = task_data.get('campaign_id', 'unknown')
                    participant_count = task_data.get('participant_count', 0)
                    logger.info(f"Worker {worker_id} completed bulk participant add for campaign {campaign_id} ({participant_count} participants)")
                else:
                    logger.error(f"Worker {worker_id} failed bulk participant add task")

            elif task_type == 'csv_participant_import':
                # Process CSV participant import task
                success = self._process_csv_participant_import_task(task_data, worker_id)

                if success:
                    row_count = len(task_data.get('rows', []))
                    logger.info(f"Worker {worker_id} completed CSV participant import ({row_count} rows)")
                else:
                    logger.error(f"Worker {worker_id} failed CSV participant import task")

            elif task_type == 'qbr_analysis':
                # Process QBR transcript analysis task
                success = self._process_qbr_analysis_task(task_data, worker_id)

                if success:
                    session_id = task_data.get('session_id', 'unknown')
                    logger.info(f"Worker {worker_id} completed QBR analysis for session {session_id}")
                else:
                    logger.error(f"Worker {worker_id} failed QBR analysis task")
                        
        except Exception as e:
            logger.error(f"Error processing task {task}: {e}")
    
    def _process_export_campaign_task(self, task_data, worker_id):
        """Process campaign export using BulkOperationJob framework (unified async pattern)"""
        from models import BulkOperationJob, Campaign, SurveyResponse
        from notification_utils import notify
        import os
        
        job_id = task_data.get('job_id')
        campaign_id = task_data.get('campaign_id')
        business_account_id = task_data.get('business_account_id')
        user_id = task_data.get('user_id')
        
        if not all([job_id, campaign_id, business_account_id]):
            logger.error(f"Export campaign task missing required data")
            return False
        
        try:
            # Get the job record
            job = BulkOperationJob.query.filter_by(job_id=job_id).first()
            if not job:
                logger.error(f"BulkOperationJob {job_id} not found for export")
                return False
            
            # Update job status to processing
            job.status = 'processing'
            job.started_at = datetime.utcnow()
            job.progress = 10
            db.session.commit()
            
            # Verify campaign access
            campaign = Campaign.query.filter_by(
                id=campaign_id,
                business_account_id=business_account_id
            ).first()
            
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found or access denied")
                job.status = 'failed'
                job.completed_at = datetime.utcnow()
                job.result = json.dumps({'error': 'Campaign not found or access denied'})
                db.session.commit()
                return False
            
            job.progress = 20
            db.session.commit()
            
            # Query all responses for this campaign
            responses = SurveyResponse.query.filter_by(
                campaign_id=campaign_id
            ).all()
            
            logger.info(f"Export: Found {len(responses)} responses for campaign {campaign_id}")
            job.progress = 40
            db.session.commit()
            
            # Convert responses to dictionaries
            data = []
            for idx, response in enumerate(responses):
                response_dict = response.to_dict()
                response_dict['campaign_name'] = campaign.name
                data.append(response_dict)
                
                # Update progress for large exports
                if len(responses) > 100 and idx % 50 == 0:
                    progress = 40 + int((idx / len(responses)) * 40)
                    job.progress = min(progress, 80)
                    db.session.commit()
            
            job.progress = 80
            db.session.commit()
            
            # Create export file
            export_filename = f"campaign_{campaign_id}_export_{job_id[:8]}.json"
            export_dir = os.path.join('exports', 'campaigns')
            os.makedirs(export_dir, exist_ok=True)
            export_path = os.path.join(export_dir, export_filename)
            
            export_data = {
                'export_info': {
                    'campaign_id': campaign_id,
                    'campaign_name': campaign.name,
                    'business_account_id': business_account_id,
                    'total_responses': len(responses),
                    'exported_at': datetime.utcnow().isoformat(),
                    'exported_by_user_id': user_id
                },
                'responses': data
            }
            
            # Write to file
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            file_size = os.path.getsize(export_path)
            
            job.progress = 90
            db.session.commit()
            
            # Mark job as completed with file path in result
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.progress = 100
            job.result = json.dumps({
                'file_path': export_path,
                'file_size': file_size,
                'total_responses': len(responses),
                'campaign_name': campaign.name
            })
            db.session.commit()
            
            # Send success notification
            notify(
                business_account_id=business_account_id,
                user_id=user_id,
                category='success',
                message=f"Campaign '{campaign.name}' export completed ({len(responses)} responses)"
            )
            
            logger.info(f"Campaign export completed: {export_path} ({file_size} bytes, {len(responses)} responses)")
            return True
            
        except Exception as e:
            logger.error(f"Campaign export task error: {e}")
            db.session.rollback()
            
            # Update job status
            try:
                job = BulkOperationJob.query.filter_by(job_id=job_id).first()
                if job:
                    job.status = 'failed'
                    job.completed_at = datetime.utcnow()
                    job.result = json.dumps({'error': str(e)})
                    db.session.commit()
                
                # Send error notification
                notify(
                    business_account_id=business_account_id,
                    user_id=user_id,
                    category='error',
                    message=f"Campaign export failed: {str(e)}"
                )
            except Exception as notify_error:
                logger.error(f"Failed to send export error notification: {notify_error}")
            
            return False
    
    def _process_email_task(self, task_data, worker_id):
        """Process an email sending task with delivery tracking"""
        email_delivery = None
        try:
            email_type = task_data.get('email_type')
            
            # Create EmailDelivery record for tracking
            email_delivery = self._create_email_delivery_record(task_data)
            if not email_delivery:
                logger.error(f"Failed to create EmailDelivery record for {email_type}")
                return False
            
            db.session.commit()
            
            if email_type == 'participant_invitation':
                # Fetch Campaign object for language-aware email content
                campaign = None
                campaign_id = task_data.get('campaign_id')
                if campaign_id:
                    from models import Campaign
                    campaign = Campaign.query.get(campaign_id)
                    if campaign:
                        logger.debug(f"Fetched Campaign {campaign_id} with language: {campaign.language_code}")
                    else:
                        logger.warning(f"Campaign {campaign_id} not found for invitation email")
                
                # Send participant invitation email with delivery tracking
                result = email_service.send_participant_invitation(
                    participant_email=task_data['participant_email'],
                    participant_name=task_data['participant_name'],
                    campaign_name=task_data['campaign_name'],
                    survey_token=task_data['survey_token'],
                    business_account_name=task_data['business_account_name'],
                    email_delivery_id=email_delivery.id,
                    business_account_id=task_data.get('business_account_id'),
                    campaign=campaign
                )
                
                return result['success']
                
            elif email_type == 'campaign_notification':
                # Send campaign notification email with delivery tracking
                result = email_service.send_campaign_notification(
                    notification_type=task_data['notification_type'],
                    campaign_name=task_data['campaign_name'],
                    campaign_id=task_data['campaign_id'],
                    business_account_name=task_data['business_account_name'],
                    additional_data=task_data.get('additional_data'),
                    email_delivery_id=email_delivery.id,
                    business_account_id=task_data.get('business_account_id')
                )
                
                return result['success']
                
            else:
                logger.error(f"Unknown email type: {email_type}")
                if email_delivery:
                    email_delivery.mark_failed(f"Unknown email type: {email_type}", is_permanent=True)
                    db.session.commit()
                return False
                
        except Exception as e:
            logger.error(f"Email task processing error: {e}")
            if email_delivery:
                email_delivery.mark_failed(f"Task processing error: {str(e)}", is_permanent=False)
                db.session.commit()
            return False
    
    def _process_audit_log_task(self, task_data, worker_id):
        """Process an audit log writing task"""
        try:
            from models import AuditLog
            
            # Create audit log entry
            audit = AuditLog.create_audit_entry(**task_data)
            db.session.add(audit)
            db.session.commit()
            
            logger.debug(f"Audit log created: {audit.action_description}")
            return True
            
        except Exception as e:
            logger.error(f"Audit log task processing error: {e}")
            # Don't let audit failures break the system - just log the error
            return False
    
    def _process_reminder_email_task(self, task_data, worker_id):
        """Process a reminder email task (EmailDelivery record already created)"""
        email_delivery = None
        try:
            email_delivery_id = task_data.get('email_delivery_id')
            
            if not email_delivery_id:
                logger.error("No email_delivery_id provided for reminder email task")
                return False
            
            # Get the EmailDelivery record
            email_delivery = EmailDelivery.query.get(email_delivery_id)
            if not email_delivery:
                logger.error(f"EmailDelivery record {email_delivery_id} not found")
                return False
            
            # Get email_type from task_data (either 'reminder_primary' or 'reminder_midpoint')
            email_type = task_data.get('email_type', 'reminder_primary')
            
            # Fetch Campaign object for language-aware email content
            campaign = None
            campaign_id = task_data.get('campaign_id')
            if campaign_id:
                from models import Campaign
                campaign = Campaign.query.get(campaign_id)
                if campaign:
                    logger.debug(f"Fetched Campaign {campaign_id} with language: {campaign.language_code} for reminder email")
                else:
                    logger.warning(f"Campaign {campaign_id} not found for reminder email")
            
            # Send the reminder email with the appropriate type
            result = email_service.send_participant_reminder(
                participant_email=task_data['participant_email'],
                participant_name=task_data['participant_name'],
                campaign_name=task_data['campaign_name'],
                survey_token=task_data['survey_token'],
                business_account_name=task_data['business_account_name'],
                email_delivery_id=email_delivery_id,
                business_account_id=task_data.get('business_account_id'),
                campaign=campaign,
                email_type=email_type  # Pass email_type to differentiate primary vs midpoint
            )
            
            return result['success']
            
        except Exception as e:
            logger.error(f"Reminder email task processing error: {e}")
            if email_delivery:
                email_delivery.mark_failed(f"Task processing error: {str(e)}", is_permanent=False)
                db.session.commit()
            return False
    
    def _process_bulk_participant_add_task(self, task_data, worker_id):
        """Process bulk participant addition task with batching and progress tracking"""
        from models import BulkOperationJob
        from notification_utils import notify
        from license_service import LicenseService
        
        job_id = task_data.get('job_id')
        campaign_id = task_data.get('campaign_id')
        participant_ids = task_data.get('participant_ids', [])
        business_account_id = task_data.get('business_account_id')
        user_id = task_data.get('user_id')
        
        if not all([job_id, campaign_id, participant_ids, business_account_id]):
            logger.error(f"Bulk participant add task missing required data")
            return False
        
        try:
            # Get the job record
            job = BulkOperationJob.query.get(job_id)
            if not job:
                logger.error(f"BulkOperationJob {job_id} not found")
                return False
            
            # Update job status to processing
            job.status = 'processing'
            job.started_at = datetime.utcnow()
            db.session.commit()
            
            # Get campaign
            campaign = Campaign.query.filter_by(
                id=campaign_id,
                business_account_id=business_account_id
            ).first()
            
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                job.status = 'failed'
                job.completed_at = datetime.utcnow()
                job.result = json.dumps({'error': 'Campaign not found'})
                db.session.commit()
                return False
            
            # Process participants in batches of 100
            BATCH_SIZE = 100
            total_count = len(participant_ids)
            success_count = 0
            skip_count = 0
            error_count = 0
            
            for i in range(0, len(participant_ids), BATCH_SIZE):
                batch = participant_ids[i:i + BATCH_SIZE]
                
                # Process batch
                for participant_id in batch:
                    try:
                        # Check if already exists
                        existing = CampaignParticipant.query.filter_by(
                            campaign_id=campaign_id,
                            participant_id=participant_id
                        ).first()
                        
                        if existing:
                            skip_count += 1
                            continue
                        
                        # Create new campaign participant
                        campaign_participant = CampaignParticipant(
                            campaign_id=campaign_id,
                            participant_id=participant_id,
                            business_account_id=business_account_id,
                            status='invited'
                        )
                        
                        db.session.add(campaign_participant)
                        success_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error adding participant {participant_id}: {e}")
                        error_count += 1
                
                # Commit batch
                db.session.commit()
                
                # Update job progress
                processed = min(i + BATCH_SIZE, total_count)
                job.progress = int((processed / total_count) * 100)
                db.session.commit()
                
                logger.info(f"Batch processed: {processed}/{total_count} participants")
            
            # Mark job as completed
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.result = json.dumps({
                'total': total_count,
                'added': success_count,
                'skipped': skip_count,
                'failed': error_count
            })
            
            # Clear campaign lock
            campaign.has_active_bulk_job = False
            campaign.active_bulk_job_id = None
            campaign.active_bulk_operation = None
            
            db.session.commit()
            
            # Audit logging for bulk participant add
            try:
                from audit_utils import queue_audit_log
                queue_audit_log(
                    business_account_id=business_account_id,
                    action_type='participants_added',
                    resource_type='campaign',
                    resource_id=campaign_id,
                    resource_name=campaign.name,
                    details={
                        'job_id': job.job_id,
                        'total': total_count,
                        'added': success_count,
                        'skipped': skip_count,
                        'failed': error_count,
                        'method': 'background_task'
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to log bulk participant add audit: {audit_error}")
            
            # Send notification
            message = f"{success_count} participants added to campaign '{campaign.name}'"
            if skip_count > 0:
                message += f" ({skip_count} already assigned)"
            if error_count > 0:
                message += f" ({error_count} failed)"
            
            notify(
                business_account_id=business_account_id,
                user_id=user_id,
                category='success' if error_count == 0 else 'warning',
                message=message
            )
            
            logger.info(f"Bulk participant add completed: {success_count} added, {skip_count} skipped, {error_count} failed")
            return True
            
        except Exception as e:
            logger.error(f"Bulk participant add task error: {e}")
            db.session.rollback()
            
            # Update job status and clear campaign lock
            try:
                job = BulkOperationJob.query.get(job_id)
                campaign = Campaign.query.get(campaign_id)
                if job:
                    job.status = 'failed'
                    job.completed_at = datetime.utcnow()
                    job.result = json.dumps({'error': str(e)})
                    
                # Clear campaign lock even on failure
                if campaign:
                    campaign.has_active_bulk_job = False
                    campaign.active_bulk_job_id = None
                    campaign.active_bulk_operation = None
                    
                db.session.commit()
                
                # Send error notification
                notify(
                    business_account_id=business_account_id,
                    user_id=user_id,
                    category='error',
                    message=f"Failed to add participants to campaign: {str(e)}"
                )
            except Exception as notify_error:
                logger.error(f"Failed to send error notification: {notify_error}")
            
            return False
    
    def _process_bulk_participant_remove_task(self, task_data, worker_id):
        """Process bulk participant removal task with batching and progress tracking"""
        from models import BulkOperationJob
        from notification_utils import notify
        
        job_id = task_data.get('job_id')
        campaign_id = task_data.get('campaign_id')
        association_ids = task_data.get('association_ids', [])
        business_account_id = task_data.get('business_account_id')
        user_id = task_data.get('user_id')
        
        if not all([job_id, campaign_id, association_ids, business_account_id]):
            logger.error(f"Bulk participant remove task missing required data")
            return False
        
        try:
            # Get the job record
            job = BulkOperationJob.query.get(job_id)
            if not job:
                logger.error(f"BulkOperationJob {job_id} not found")
                return False
            
            # Update job status to processing
            job.status = 'processing'
            job.started_at = datetime.utcnow()
            db.session.commit()
            
            # Get campaign
            campaign = Campaign.query.filter_by(
                id=campaign_id,
                business_account_id=business_account_id
            ).first()
            
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                job.status = 'failed'
                job.completed_at = datetime.utcnow()
                job.result = json.dumps({'error': 'Campaign not found'})
                db.session.commit()
                return False
            
            # Process participants in batches of 100
            BATCH_SIZE = 100
            total_count = len(association_ids)
            removed_count = 0
            error_count = 0
            
            for i in range(0, len(association_ids), BATCH_SIZE):
                batch = association_ids[i:i + BATCH_SIZE]
                
                # Process batch
                for association_id in batch:
                    try:
                        # Find and delete the association (association_id is a UUID string)
                        association = CampaignParticipant.query.filter_by(
                            uuid=association_id,
                            campaign_id=campaign_id,
                            business_account_id=business_account_id
                        ).first()
                        
                        if association:
                            db.session.delete(association)
                            removed_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error removing association {association_id}: {e}")
                        error_count += 1
                
                # Commit batch
                db.session.commit()
                
                # Update job progress
                processed = min(i + BATCH_SIZE, total_count)
                job.progress = int((processed / total_count) * 100)
                db.session.commit()
                
                logger.info(f"Batch processed: {processed}/{total_count} participants removed")
            
            # Mark job as completed
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.result = json.dumps({
                'total': total_count,
                'removed': removed_count,
                'failed': error_count
            })
            
            # Clear campaign lock
            campaign.has_active_bulk_job = False
            campaign.active_bulk_job_id = None
            campaign.active_bulk_operation = None
            
            db.session.commit()
            
            # Audit logging for bulk participant removal
            try:
                from audit_utils import queue_audit_log
                queue_audit_log(
                    business_account_id=business_account_id,
                    action_type='participants_removed',
                    resource_type='campaign',
                    resource_id=campaign_id,
                    resource_name=campaign.name,
                    details={
                        'job_id': job.job_id,
                        'total': total_count,
                        'removed': removed_count,
                        'failed': error_count,
                        'method': 'background_task'
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to log bulk participant removal audit: {audit_error}")
            
            # Send notification
            message = f"{removed_count} participants removed from campaign '{campaign.name}'"
            if error_count > 0:
                message += f" ({error_count} failed)"
            
            notify(
                business_account_id=business_account_id,
                user_id=user_id,
                category='success' if error_count == 0 else 'warning',
                message=message
            )
            
            logger.info(f"Bulk participant remove completed: {removed_count} removed, {error_count} failed")
            return True
            
        except Exception as e:
            logger.error(f"Bulk participant remove task error: {e}")
            db.session.rollback()
            
            # Update job status and clear campaign lock
            try:
                job = BulkOperationJob.query.get(job_id)
                campaign = Campaign.query.get(campaign_id)
                if job:
                    job.status = 'failed'
                    job.completed_at = datetime.utcnow()
                    job.result = json.dumps({'error': str(e)})
                    
                # Clear campaign lock even on failure
                if campaign:
                    campaign.has_active_bulk_job = False
                    campaign.active_bulk_job_id = None
                    campaign.active_bulk_operation = None
                    
                db.session.commit()
                
                # Send error notification
                notify(
                    business_account_id=business_account_id,
                    user_id=user_id,
                    category='error',
                    message=f"Failed to remove participants from campaign: {str(e)}"
                )
            except Exception as notify_error:
                logger.error(f"Failed to send error notification: {notify_error}")
            
            return False
    
    def _process_csv_participant_import_task(self, task_data, worker_id):
        """Process CSV participant import task with batching and progress tracking"""
        from models import BulkOperationJob
        from notification_utils import notify
        from license_service import LicenseService

        job_id = task_data.get('job_id')
        business_account_id = task_data.get('business_account_id')
        user_id = task_data.get('user_id')
        rows = task_data.get('rows', [])

        if not all([job_id, business_account_id, rows is not None]):
            logger.error("CSV participant import task missing required data")
            return False

        try:
            # Get the job record
            job = BulkOperationJob.query.get(job_id)
            if not job:
                logger.error(f"BulkOperationJob {job_id} not found")
                return False

            # Update job status to processing
            job.status = 'processing'
            job.started_at = datetime.utcnow()
            db.session.commit()

            BATCH_SIZE = 100
            total_count = len(rows)
            created_count = 0
            error_count = 0
            row_errors = []

            for i in range(0, total_count, BATCH_SIZE):
                batch = rows[i:i + BATCH_SIZE]

                # Bulk email lookup for this batch to avoid N+1 queries
                batch_emails = [r.get('email', '').strip().lower() for r in batch if r.get('email')]
                existing_emails = set()
                if batch_emails:
                    from sqlalchemy import func as sqlfunc
                    existing_records = Participant.query.filter(
                        Participant.business_account_id == business_account_id,
                        sqlfunc.lower(Participant.email).in_(batch_emails)
                    ).with_entities(Participant.email).all()
                    existing_emails = {e.lower() for (e,) in existing_records}

                for row in batch:
                    row_num = row.get('row_num', '?')
                    try:
                        email = row.get('email', '').strip().lower()
                        name = row.get('name', '').strip()
                        company_name = row.get('company_name', '').strip()

                        if not email or not name or not company_name:
                            row_errors.append(f"Row {row_num}: Email, name, and company name are required")
                            error_count += 1
                            continue

                        if email in existing_emails:
                            row_errors.append(f"Row {row_num}: Participant {email} already exists in your account")
                            error_count += 1
                            continue

                        role = row.get('role') or None
                        region = row.get('region') or None
                        customer_tier = row.get('customer_tier') or None
                        language = row.get('language') or 'en'
                        client_industry = row.get('client_industry') or None
                        commercial_value = row.get('commercial_value')
                        tenure_years = row.get('tenure_years')

                        participant = Participant()
                        participant.business_account_id = business_account_id
                        participant.email = email
                        participant.name = name
                        participant.company_name = company_name
                        participant.role = role
                        participant.region = region
                        participant.customer_tier = customer_tier
                        participant.language = language
                        participant.client_industry = client_industry
                        participant.company_commercial_value = float(commercial_value) if commercial_value is not None else None
                        participant.tenure_years = float(tenure_years) if tenure_years is not None else None
                        participant.source = 'admin_bulk'
                        participant.generate_token()
                        participant.set_appropriate_status_for_context(is_trial=False)

                        db.session.add(participant)
                        existing_emails.add(email)
                        created_count += 1

                    except Exception as e:
                        logger.error(f"CSV import row {row_num} error: {e}")
                        row_errors.append(f"Row {row_num}: {str(e)}")
                        error_count += 1

                # Commit batch
                db.session.commit()

                # Update job progress
                processed = min(i + BATCH_SIZE, total_count)
                job.progress = int((processed / total_count) * 100)
                db.session.commit()

                logger.info(f"CSV import batch processed: {processed}/{total_count} rows")

            # Sync commercial values to all existing participants from same companies
            company_commercial_values = {}
            for row in rows:
                company_name = row.get('company_name', '').strip()
                commercial_value = row.get('commercial_value')
                if company_name and commercial_value is not None:
                    company_commercial_values[company_name.upper()] = float(commercial_value)

            if company_commercial_values:
                from sqlalchemy import func as sqlfunc2
                for company_key, cv in company_commercial_values.items():
                    Participant.query.filter(
                        sqlfunc2.upper(Participant.company_name) == company_key,
                        Participant.business_account_id == business_account_id
                    ).update({'company_commercial_value': cv}, synchronize_session=False)
                db.session.commit()

            # Mark job as completed
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            job.result = json.dumps({
                'total': total_count,
                'created': created_count,
                'failed': error_count,
                'errors': row_errors[:50]
            })
            db.session.commit()

            # Audit logging
            try:
                from audit_utils import queue_audit_log
                queue_audit_log(
                    business_account_id=business_account_id,
                    action_type='participants_uploaded',
                    resource_type='participant',
                    details={
                        'job_id': job.job_id,
                        'total': total_count,
                        'created': created_count,
                        'failed': error_count,
                        'method': 'background_task'
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to log CSV participant import audit: {audit_error}")

            # Send notification
            message = f"CSV import complete: {created_count} participant(s) created"
            if error_count > 0:
                message += f", {error_count} row(s) had errors"

            notify(
                business_account_id=business_account_id,
                user_id=user_id,
                category='success' if error_count == 0 else 'warning',
                message=message
            )

            logger.info(f"CSV participant import completed: {created_count} created, {error_count} failed")
            return True

        except Exception as e:
            logger.error(f"CSV participant import task error: {e}")
            db.session.rollback()

            try:
                job = BulkOperationJob.query.get(job_id)
                if job:
                    job.status = 'failed'
                    job.completed_at = datetime.utcnow()
                    job.result = json.dumps({'error': str(e)})
                    db.session.commit()

                notify(
                    business_account_id=business_account_id,
                    user_id=user_id,
                    category='error',
                    message=f"CSV participant import failed: {str(e)}"
                )
            except Exception as notify_error:
                logger.error(f"Failed to send CSV import error notification: {notify_error}")

            return False

    def _create_email_delivery_record(self, task_data):
        """Create EmailDelivery record for tracking"""
        try:
            email_type = task_data.get('email_type')
            
            # Extract common fields
            business_account_id = task_data.get('business_account_id')
            campaign_id = task_data.get('campaign_id')
            participant_id = task_data.get('participant_id')
            campaign_participant_id = task_data.get('campaign_participant_id')
            
            if email_type == 'participant_invitation':
                recipient_email = task_data['participant_email']
                recipient_name = task_data['participant_name']
                subject = f"Your feedback is requested: {task_data['campaign_name']}"
                
            elif email_type == 'campaign_notification':
                recipient_email = task_data.get('recipient_email')
                recipient_name = task_data.get('recipient_name', 'Admin')
                subject = f"Campaign notification: {task_data['campaign_name']}"
                
            else:
                logger.error(f"Unknown email type for delivery record: {email_type}")
                return None
            
            # Create EmailDelivery record
            email_delivery = EmailDelivery(
                business_account_id=business_account_id,
                campaign_id=campaign_id,
                participant_id=participant_id,
                campaign_participant_id=campaign_participant_id,
                email_type=email_type,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                status='pending',
                retry_count=0,
                max_retries=3,  # Default max retries
                email_data=json.dumps(task_data)  # Store task data for debugging
            )
            
            db.session.add(email_delivery)
            return email_delivery
            
        except Exception as e:
            logger.error(f"Failed to create EmailDelivery record: {e}")
            return None
            
    def _process_export_task(self, task_data, worker_id):
        """Process a campaign export task with streaming to avoid memory issues"""
        job_id = task_data.get('job_id')
        campaign_id = task_data.get('campaign_id')
        business_account_id = task_data.get('business_account_id')
        
        if not job_id or not campaign_id or not business_account_id:
            logger.error(f"Export task missing required data: job_id={job_id}, campaign_id={campaign_id}, business_account_id={business_account_id}")
            return False
            
        try:
            # Update job status to processing
            self._update_export_job_status(job_id, 'processing')
            
            # Verify campaign belongs to business account
            campaign = Campaign.query.filter_by(
                id=campaign_id, 
                business_account_id=business_account_id
            ).first()
            
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found for business account {business_account_id}")
                self._update_export_job_status(job_id, 'failed', error='Campaign not found')
                return False
            
            # Generate export file
            export_file_path = f"/tmp/export_{job_id}.json"
            success = self._generate_export_file(campaign, export_file_path, job_id)
            
            if success:
                self._update_export_job_status(job_id, 'completed', file_path=export_file_path)
                logger.info(f"Export completed for campaign {campaign_id}, file: {export_file_path}")
                
                # Add audit log for export completion
                try:
                    from audit_utils import queue_audit_log
                    queue_audit_log(
                        business_account_id=business_account_id,
                        action_type='campaign_export_completed',
                        resource_type='campaign',
                        resource_id=campaign_id,
                        resource_name=campaign.name,
                        details={
                            'job_id': job_id,
                            'file_path': export_file_path,
                            'export_type': 'campaign_data'
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to log export completion audit event: {e}")
                
                return True
            else:
                self._update_export_job_status(job_id, 'failed', error='Export generation failed')
                return False
                
        except Exception as e:
            logger.error(f"Export task error for job {job_id}: {e}")
            self._update_export_job_status(job_id, 'failed', error=str(e))
            return False
    
    def _generate_export_file(self, campaign, file_path, job_id):
        """Generate export file with streaming to avoid memory issues"""
        try:
            export_data = {
                'export_metadata': {
                    'job_id': job_id,
                    'campaign_id': campaign.id,
                    'campaign_name': campaign.name,
                    'business_account_id': campaign.business_account_id,
                    'export_timestamp': datetime.utcnow().isoformat(),
                    'export_version': '1.0'
                },
                'campaign': campaign.to_dict(),
                'responses': [],
                'participants': []
            }
            
            # Stream survey responses in chunks
            chunk_size = 100
            offset = 0
            response_count = 0
            
            while True:
                # Get chunk of responses
                response_chunk = SurveyResponse.query.filter_by(
                    campaign_id=campaign.id
                ).offset(offset).limit(chunk_size).all()
                
                if not response_chunk:
                    break
                    
                # Add responses to export data
                for response in response_chunk:
                    export_data['responses'].append(response.to_dict())
                    response_count += 1
                
                offset += chunk_size
                
                # Update progress
                self._update_export_job_status(job_id, 'processing', 
                                               progress=f"Processed {response_count} survey responses")
            
            # Stream participants in chunks  
            offset = 0
            participant_count = 0
            
            while True:
                # Get chunk of campaign participants with eager loading to prevent N+1 queries
                participant_chunk = CampaignParticipant.query.filter_by(
                    campaign_id=campaign.id
                ).options(joinedload(CampaignParticipant.participant)).offset(offset).limit(chunk_size).all()
                
                if not participant_chunk:
                    break
                    
                # Add participants to export data
                for cp in participant_chunk:
                    participant_data = cp.to_dict()
                    if cp.participant:
                        participant_data['participant_details'] = cp.participant.to_dict()
                    export_data['participants'].append(participant_data)
                    participant_count += 1
                
                offset += chunk_size
                
                # Update progress
                self._update_export_job_status(job_id, 'processing', 
                                               progress=f"Processed {participant_count} participants")
            
            # Write export file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Export file generated: {file_path} ({response_count} responses, {participant_count} participants)")
            return True
            
        except Exception as e:
            logger.error(f"Error generating export file {file_path}: {e}")
            return False
    
    def _update_export_job_status(self, job_id, status, error=None, file_path=None, progress=None):
        """Update export job status in database"""
        from models import ExportJob
        from app import db
        
        try:
            export_job = ExportJob.query.get(job_id)
            if export_job:
                export_job.status = status
                export_job.error = error
                if file_path:
                    export_job.file_path = file_path
                if progress is not None:
                    export_job.progress = progress
                if status == 'completed':
                    export_job.completed_at = datetime.utcnow()
                
                db.session.commit()
                logger.debug(f"Updated export job {job_id} status to {status}")
            else:
                logger.warning(f"Export job {job_id} not found for status update")
        except Exception as e:
            logger.error(f"Error updating export job status: {e}")
            db.session.rollback()
    
    def create_export_job(self, campaign_id, business_account_id):
        """Create a new export job and return job ID"""
        from models import ExportJob
        from app import db
        
        job_id = str(uuid.uuid4())
        
        # Create export job in database
        export_job = ExportJob(
            id=job_id,
            campaign_id=campaign_id,
            business_account_id=business_account_id,
            status='queued',
            progress=0
        )
        
        db.session.add(export_job)
        db.session.commit()
        
        logger.info(f"Created export job {job_id} for campaign {campaign_id}")
        
        return job_id
    
    def get_export_job_status(self, job_id):
        """Get export job status from database"""
        from models import ExportJob
        
        try:
            export_job = ExportJob.query.get(job_id)
            if export_job:
                return export_job.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error getting export job status: {e}")
            return None
    
    def cleanup_old_export_jobs(self, max_age_hours=24):
        """
        DEPRECATED: Clean up old ExportJob records (legacy system).
        New exports use BulkOperationJob - see cleanup_old_bulk_export_jobs().
        This method is kept for backwards compatibility only.
        """
        from models import ExportJob
        from app import db
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            # Find old export jobs
            old_jobs = ExportJob.query.filter(ExportJob.updated_at < cutoff_time).all()
            
            for job in old_jobs:
                # Clean up file if it exists
                if job.file_path and os.path.exists(job.file_path):
                    try:
                        os.remove(job.file_path)
                        logger.info(f"Cleaned up legacy export file: {job.file_path}")
                    except Exception as e:
                        logger.error(f"Error cleaning up export file {job.file_path}: {e}")
                
                # Delete job from database
                db.session.delete(job)
            
            if old_jobs:
                db.session.commit()
                logger.info(f"Cleaned up {len(old_jobs)} old legacy export jobs")
        except Exception as e:
            logger.error(f"Error cleaning up old export jobs: {e}")
            db.session.rollback()
    
    def cleanup_old_bulk_export_jobs(self, max_age_hours=48):
        """
        Clean up old campaign export jobs from BulkOperationJob (unified async pattern).
        Removes completed/failed export jobs older than max_age_hours and their files.
        
        Args:
            max_age_hours: Age threshold in hours (default: 48 hours for exports)
        
        Returns:
            int: Number of jobs cleaned up
        """
        from models import BulkOperationJob
        from app import db
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            # Find old export jobs (only completed/failed, keep pending/processing)
            old_export_jobs = BulkOperationJob.query.filter(
                BulkOperationJob.operation_type == 'export_campaign',
                BulkOperationJob.status.in_(['completed', 'failed']),
                BulkOperationJob.completed_at < cutoff_time
            ).all()
            
            cleaned_files = 0
            missing_files = 0
            
            for job in old_export_jobs:
                # Clean up export file if it exists in result
                try:
                    result_data = json.loads(job.result) if job.result else {}
                    file_path = result_data.get('file_path')
                    
                    if file_path:
                        # SECURITY: Validate path is within export directory before deletion
                        # Use realpath to resolve symlinks and prevent path substitution
                        export_base_dir = os.path.realpath(os.path.join('exports', 'campaigns'))
                        file_absolute = os.path.realpath(file_path)
                        
                        if file_absolute.startswith(export_base_dir + os.sep):
                            if os.path.exists(file_absolute):
                                os.remove(file_absolute)
                                cleaned_files += 1
                                logger.debug(f"Cleaned up export file: {file_path}")
                            else:
                                missing_files += 1
                                logger.debug(f"Export file already missing: {file_path}")
                        else:
                            logger.warning(f"Skipping file outside export directory: {file_path}")
                    
                except Exception as e:
                    logger.error(f"Error cleaning up export file for job {job.job_id}: {e}")
                
                # Delete job from database (removes completed jobs to prevent 404s on downloads)
                # This is safer than leaving completed jobs with missing files
                db.session.delete(job)
            
            if old_export_jobs:
                db.session.commit()
                logger.info(f"Cleaned up {len(old_export_jobs)} old export jobs ({cleaned_files} files removed, {missing_files} already missing)")
            
            return len(old_export_jobs)
            
        except Exception as e:
            logger.error(f"Error cleaning up old bulk export jobs: {e}")
            db.session.rollback()
            return 0
    
    def _process_executive_report_task(self, task_data, worker_id):
        """Process executive report generation task (both new and regeneration)"""
        try:
            # Get task parameters
            campaign_id = task_data.get('campaign_id')
            business_account_id = task_data.get('business_account_id')
            is_regenerating = task_data.get('regenerating', False)
            report_id = task_data.get('report_id')
            user_language = task_data.get('user_language', 'en')
            
            if not all([campaign_id, business_account_id]):
                logger.error(f"Missing executive report task parameters: {task_data}")
                return False
            
            # If regenerating, handle existing report and old file cleanup
            if is_regenerating and report_id:
                try:
                    from models import ExecutiveReport
                    existing_report = ExecutiveReport.query.get(report_id)
                    if existing_report and existing_report.file_path:
                        # Delete old file if it exists
                        if os.path.exists(existing_report.file_path):
                            os.remove(existing_report.file_path)
                            logger.info(f"Deleted old executive report file: {existing_report.file_path}")
                except Exception as e:
                    logger.error(f"Error cleaning up old report file: {e}")
            
            # Use lazy import to avoid circular dependency and import correct class
            from executive_report_service import ExecutiveReportGenerator
            
            generator = ExecutiveReportGenerator()
            report_file_path = generator.generate_campaign_report(campaign_id, business_account_id, user_language=user_language)
            
            if report_file_path:
                # Store report information in database
                report_record = self._store_executive_report_info(campaign_id, business_account_id, report_file_path, is_regenerating, report_id)
                
                action_type = "regenerated" if is_regenerating else "generated"
                logger.info(f"Executive report {action_type} for campaign {campaign_id}: {report_file_path}")
                
                # Add audit log for report generation/regeneration
                try:
                    from audit_utils import queue_audit_log
                    from models import Campaign
                    
                    campaign = Campaign.query.get(campaign_id)
                    
                    # Extract user information from task data (passed from manual trigger)
                    user_email = task_data.get('user_email')
                    user_name = task_data.get('user_name')
                    
                    queue_audit_log(
                        business_account_id=business_account_id,
                        action_type='executive_report_regenerated' if is_regenerating else 'executive_report_generated',
                        resource_type='campaign',
                        resource_id=campaign_id,
                        resource_name=campaign.name if campaign else f'Campaign {campaign_id}',
                        user_email=user_email,
                        user_name=user_name,
                        details={
                            'file_path': report_file_path,
                            'report_type': 'executive_report',
                            'is_regeneration': is_regenerating
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to log executive report audit event: {e}")
                
                # Send success notification
                try:
                    from notification_utils import notify
                    from models import Campaign
                    
                    campaign = Campaign.query.get(campaign_id)
                    campaign_name = campaign.name if campaign else f'Campaign {campaign_id}'
                    
                    action_verb = "regenerated" if is_regenerating else "ready to download"
                    message = f"Executive report for '{campaign_name}' is {action_verb}"
                    
                    notify(
                        business_account_id=business_account_id,
                        user_id=task_data.get('user_id'),  # None if not provided (account-wide notification)
                        category='success',
                        message=message,
                        campaign_id=campaign_id,
                        report_id=report_record.id if report_record else None,
                        report_file=report_file_path,
                        action_type=action_type
                    )
                except Exception as notify_error:
                    logger.error(f"Failed to send executive report success notification: {notify_error}")
                
                return True
            else:
                # If regeneration failed, update status back to failed
                if is_regenerating and report_id:
                    try:
                        from models import ExecutiveReport
                        existing_report = ExecutiveReport.query.get(report_id)
                        if existing_report:
                            existing_report.status = 'failed'
                            existing_report.updated_at = datetime.utcnow()
                            db.session.commit()
                    except Exception as e:
                        logger.error(f"Error updating report status to failed: {e}")
                
                # Send failure notification
                try:
                    from notification_utils import notify
                    from models import Campaign
                    
                    campaign = Campaign.query.get(campaign_id)
                    campaign_name = campaign.name if campaign else f'Campaign {campaign_id}'
                    
                    action_verb = "regeneration" if is_regenerating else "generation"
                    message = f"Executive report {action_verb} failed for '{campaign_name}'"
                    
                    notify(
                        business_account_id=business_account_id,
                        user_id=task_data.get('user_id'),
                        category='error',
                        message=message,
                        campaign_id=campaign_id,
                        action_type=action_verb
                    )
                except Exception as notify_error:
                    logger.error(f"Failed to send executive report failure notification: {notify_error}")
                
                logger.error(f"Failed to generate executive report for campaign {campaign_id}")
                return False
                
        except Exception as e:
            # If regeneration failed, update status back to failed
            if task_data.get('regenerating') and task_data.get('report_id'):
                try:
                    from models import ExecutiveReport
                    existing_report = ExecutiveReport.query.get(task_data.get('report_id'))
                    if existing_report:
                        existing_report.status = 'failed'
                        existing_report.updated_at = datetime.utcnow()
                        db.session.commit()
                except Exception as db_e:
                    logger.error(f"Error updating report status to failed: {db_e}")
            
            # Send error notification for exception case
            try:
                from notification_utils import notify
                from models import Campaign
                
                campaign = Campaign.query.get(campaign_id)
                campaign_name = campaign.name if campaign else f'Campaign {campaign_id}'
                
                is_regenerating = task_data.get('regenerating', False)
                action_verb = "regeneration" if is_regenerating else "generation"
                message = f"Executive report {action_verb} failed for '{campaign_name}'"
                
                notify(
                    business_account_id=business_account_id,
                    user_id=task_data.get('user_id'),
                    category='error',
                    message=message,
                    campaign_id=campaign_id,
                    error=str(e),
                    action_type=action_verb
                )
            except Exception as notify_error:
                logger.error(f"Failed to send executive report exception notification: {notify_error}")
            
            logger.error(f"Executive report task error for campaign {campaign_id}: {e}")
            return False
    
    def _store_executive_report_info(self, campaign_id, business_account_id, file_path, is_regenerating=False, report_id=None):
        """Store executive report information in the database"""
        try:
            from models import ExecutiveReport
            from datetime import datetime
            import os
            
            # Calculate file size
            file_size = None
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
            
            # For regeneration, use existing report record if available
            if is_regenerating and report_id:
                report = ExecutiveReport.query.get(report_id)
                if not report:
                    logger.error(f"Report ID {report_id} not found for regeneration")
                    return
            else:
                # Create or update executive report record (original behavior)
                report = ExecutiveReport.query.filter_by(
                    campaign_id=campaign_id,
                    business_account_id=business_account_id
                ).first()
            
            if not report:
                report = ExecutiveReport(
                    campaign_id=campaign_id,
                    business_account_id=business_account_id,
                    file_path=file_path,
                    generated_at=datetime.utcnow(),
                    status='completed',
                    file_size=file_size
                )
                db.session.add(report)
            else:
                report.file_path = file_path
                report.generated_at = datetime.utcnow()
                report.status = 'completed'
                report.file_size = file_size
                report.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            action = "regenerated" if is_regenerating else "stored"
            logger.info(f"Executive report info {action} for campaign {campaign_id}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to store executive report info: {e}")
            return None
    
    def _process_transcript_analysis_task(self, task_data, worker_id):
        """Process transcript analysis task - create participant and analyze transcript"""
        try:
            # Get task parameters
            campaign_id = task_data.get('campaign_id')
            business_account_id = task_data.get('business_account_id')
            transcript_content = task_data.get('transcript_content')
            transcript_hash = task_data.get('transcript_hash')
            transcript_filename = task_data.get('transcript_filename')
            participant_name = task_data.get('participant_name')
            participant_email = task_data.get('participant_email')
            participant_company = task_data.get('participant_company')
            
            if not all([campaign_id, business_account_id, transcript_content, participant_name, participant_email, participant_company]):
                logger.error(f"Missing transcript analysis task parameters: {task_data}")
                return False
            
            # Get campaign to verify it exists
            from models import Campaign
            campaign = Campaign.query.filter_by(
                id=campaign_id,
                business_account_id=business_account_id
            ).first()
            
            if not campaign:
                logger.error(f"Campaign {campaign_id} not found for business {business_account_id}")
                return False
            
            # Create or get participant record
            from models import Participant, CampaignParticipant
            
            # Check if participant already exists in this business account
            participant = Participant.query.filter_by(
                email=participant_email,
                business_account_id=business_account_id
            ).first()
            
            if not participant:
                # Create new participant
                participant = Participant(
                    name=participant_name,
                    email=participant_email,
                    company_name=participant_company,
                    business_account_id=business_account_id,
                    source='transcript_upload'  # Track origin as transcript upload
                )
                db.session.add(participant)
                db.session.flush()  # Get participant ID
                logger.info(f"Created new participant {participant_name} ({participant_email})")
            else:
                # Update existing participant details if needed
                if participant.name != participant_name or participant.company_name != participant_company:
                    participant.name = participant_name
                    participant.company_name = participant_company
                    logger.info(f"Updated participant {participant_name} ({participant_email})")
            
            # Create campaign participation record if doesn't exist
            campaign_participant = CampaignParticipant.query.filter_by(
                campaign_id=campaign_id,
                participant_id=participant.id
            ).first()
            
            if not campaign_participant:
                campaign_participant = CampaignParticipant(
                    campaign_id=campaign_id,
                    participant_id=participant.id,
                    business_account_id=business_account_id,
                    status='completed'  # Transcript implies survey completed
                )
                db.session.add(campaign_participant)
                db.session.flush()  # Get campaign_participant ID
            
            # Analyze transcript using OpenAI
            analysis_result = self._analyze_transcript_with_ai(transcript_content, participant_name, participant_company)
            
            if not analysis_result:
                logger.error(f"Failed to analyze transcript for participant {participant_name}")
                return False
            
            # Create survey response record with transcript and analysis data
            from models import SurveyResponse
            
            survey_response = SurveyResponse(
                company_name=participant_company,
                respondent_name=participant_name,
                respondent_email=participant_email,
                nps_score=analysis_result.get('nps_score'),
                nps_category=analysis_result.get('nps_category'),
                satisfaction_rating=analysis_result.get('satisfaction_rating'),
                product_value_rating=analysis_result.get('product_value_rating'),
                service_rating=analysis_result.get('service_rating'),
                pricing_rating=analysis_result.get('pricing_rating'),
                improvement_feedback=analysis_result.get('improvement_feedback'),
                recommendation_reason=analysis_result.get('recommendation_reason'),
                additional_comments=analysis_result.get('additional_comments'),
                sentiment_score=analysis_result.get('sentiment_score'),
                sentiment_label=analysis_result.get('sentiment_label'),
                key_themes=analysis_result.get('key_themes'),
                churn_risk_score=analysis_result.get('churn_risk_score'),
                churn_risk_level=analysis_result.get('churn_risk_level'),
                churn_risk_factors=analysis_result.get('churn_risk_factors'),
                growth_opportunities=analysis_result.get('growth_opportunities'),
                account_risk_factors=analysis_result.get('account_risk_factors'),
                growth_factor=analysis_result.get('growth_factor'),
                growth_rate=analysis_result.get('growth_rate'),
                growth_range=analysis_result.get('growth_range'),
                campaign_id=campaign_id,
                campaign_participant_id=campaign_participant.id,
                source_type='transcript',
                transcript_content=transcript_content,
                transcript_hash=transcript_hash,
                transcript_filename=transcript_filename,
                analyzed_at=datetime.utcnow()
            )
            
            db.session.add(survey_response)
            db.session.commit()
            
            logger.info(f"Transcript analysis completed for participant {participant_name} in campaign {campaign_id}")
            
            # Add audit log for transcript analysis
            try:
                from audit_utils import queue_audit_log
                
                queue_audit_log(
                    business_account_id=business_account_id,
                    action_type='transcript_analyzed',
                    resource_type='campaign',
                    resource_id=campaign_id,
                    resource_name=campaign.name,
                    details={
                        'participant_name': participant_name,
                        'participant_email': participant_email,
                        'transcript_filename': transcript_filename,
                        'nps_score': analysis_result.get('nps_score'),
                        'sentiment_label': analysis_result.get('sentiment_label')
                    }
                )
            except Exception as e:
                logger.error(f"Failed to log transcript analysis audit event: {e}")
            
            # Send notification for transcript analysis completion
            try:
                from notification_utils import notify
                
                nps_score = analysis_result.get('nps_score', 'N/A')
                sentiment = analysis_result.get('sentiment_label', 'Unknown')
                
                notify(
                    business_account_id=business_account_id,
                    user_id=None,  # Account-wide notification
                    category='success',
                    message=f"Transcript analyzed for {participant_name} in campaign '{campaign.name}' - NPS: {nps_score}, Sentiment: {sentiment}"
                )
            except Exception as e:
                logger.error(f"Failed to send transcript analysis notification: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Transcript analysis task error for campaign {campaign_id}: {e}")
            db.session.rollback()
            return False
    
    def _analyze_transcript_with_ai(self, transcript_content, participant_name, participant_company):
        """Use LLM gateway (or direct OpenAI fallback) to analyze transcript and extract survey response data"""
        try:
            import os
            import json
            
            # Create specialized prompt for transcript analysis
            prompt = f"""You are VOÏA (Voice of Client), an AI assistant specialized in analyzing customer feedback transcripts. 

Analyze this meeting/call transcript between our team and {participant_name} from {participant_company}:

TRANSCRIPT:
{transcript_content}

Extract the following information and respond with a valid JSON object:

1. NPS Score (0-10): Based on likelihood to recommend us
2. NPS Category: "Promoter" (9-10), "Passive" (7-8), or "Detractor" (0-6)
3. Satisfaction Rating (1-5): Overall satisfaction with our service
4. Product Value Rating (1-5): Perceived value of our product/service
5. Service Rating (1-5): Quality of our customer service
6. Pricing Rating (1-5): Satisfaction with pricing
7. Improvement Feedback: What they want improved (max 500 chars)
8. Recommendation Reason: Why they would/wouldn't recommend us (max 500 chars)
9. Additional Comments: Other important insights (max 1000 chars)
10. Sentiment Score (-1.0 to 1.0): Overall emotional tone
11. Sentiment Label: "Positive", "Neutral", or "Negative"
12. Key Themes: JSON array of up to 5 main topics discussed
13. Churn Risk Score (0.0-1.0): Likelihood of leaving us
14. Churn Risk Level: "Minimal", "Low", "Medium", or "High"
15. Churn Risk Factors: JSON array of factors indicating churn risk
16. Growth Opportunities: JSON array of expansion/upsell opportunities
17. Account Risk Factors: JSON array of business risks with this account
18. Growth Factor (1.0-3.0): Expected organic growth multiplier based on NPS
19. Growth Rate: Expected growth percentage (e.g., "25%")
20. Growth Range: NPS range (e.g., "9-10" for promoters)

Respond with ONLY the JSON object, no other text:"""

            # Try gateway first, fallback to direct OpenAI
            gateway = _get_transcript_gateway()
            if gateway:
                from llm_gateway import LLMRequest, LLMMessage
                request = LLMRequest(
                    messages=[LLMMessage(role="user", content=prompt)],
                    model="gpt-4o",
                    temperature=0.1,
                    max_tokens=2000
                )
                response = gateway.chat_completion(request)
                ai_response = response.content.strip() if response.content else ""
                logger.debug("Transcript analysis using LLM gateway")
            else:
                from openai import OpenAI
                client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2000
                )
                ai_response = response.choices[0].message.content.strip()
                logger.debug("Transcript analysis using direct OpenAI")
            
            # Strip markdown code blocks if present (OpenAI sometimes wraps JSON in ```json...```)
            if ai_response.startswith('```'):
                # Remove opening fence (```json or ```)
                lines = ai_response.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]  # Remove first line
                # Remove closing fence (```)
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]  # Remove last line
                ai_response = '\n'.join(lines).strip()
            
            try:
                analysis_data = json.loads(ai_response)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response from LLM: {ai_response[:200]}...")
                logger.error(f"JSON decode error: {e}")
                return None
            
            # Convert analysis data to match SurveyResponse schema
            # Note: LLM returns fields with capital letters and spaces (e.g., "NPS Score")
            # We normalize sentiment_label to lowercase for consistency with regular surveys
            sentiment_label_raw = analysis_data.get('Sentiment Label', 'Neutral')
            sentiment_label = sentiment_label_raw.lower() if sentiment_label_raw else 'neutral'
            
            result = {
                'nps_score': analysis_data.get('NPS Score', 0),
                'nps_category': analysis_data.get('NPS Category', 'Detractor'),
                'satisfaction_rating': analysis_data.get('Satisfaction Rating'),
                'product_value_rating': analysis_data.get('Product Value Rating'),
                'service_rating': analysis_data.get('Service Rating'),
                'pricing_rating': analysis_data.get('Pricing Rating'),
                'improvement_feedback': analysis_data.get('Improvement Feedback', ''),
                'recommendation_reason': analysis_data.get('Recommendation Reason', ''),
                'additional_comments': analysis_data.get('Additional Comments', ''),
                'sentiment_score': analysis_data.get('Sentiment Score', 0.0),
                'sentiment_label': sentiment_label,
                'key_themes': json.dumps(analysis_data.get('Key Themes', [])),
                'churn_risk_score': analysis_data.get('Churn Risk Score', 0.0),
                'churn_risk_level': analysis_data.get('Churn Risk Level', 'Minimal'),
                'churn_risk_factors': json.dumps(analysis_data.get('Churn Risk Factors', [])),
                'growth_opportunities': json.dumps(analysis_data.get('Growth Opportunities', [])),
                'account_risk_factors': json.dumps(analysis_data.get('Account Risk Factors', [])),
                'growth_factor': analysis_data.get('Growth Factor', 1.0),
                'growth_rate': analysis_data.get('Growth Rate', '0%'),
                'growth_range': analysis_data.get('Growth Range', '0-6')
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing transcript with AI: {e}")
            return None

    def _analyze_qbr_transcript_with_ai(self, transcript_content, company_name, quarter, year):
        """Use LLM gateway (or direct OpenAI fallback) to analyze QBR transcript and extract strategic insights"""
        try:
            quarter_label = f"Q{quarter} {year}"
            prompt = f"""You are VOÏA, an AI specialized in analyzing Quarterly Business Review (QBR) transcripts. Analyze the following QBR transcript for {company_name} ({quarter_label}) and extract strategic intelligence.

TRANSCRIPT:
{transcript_content}

STEP 1 — PARTICIPANT IDENTIFICATION (complete this before the JSON output):
Read the entire transcript above and identify every person present. Participants appear as:
  • Speaker-turn labels:  "Alice Chen:", "Alice:", "A.Chen:", "Alice Chen (VP):", "Alice [AcmeCorp]:"
  • Attendee lists in the header: "Attendees: Alice Chen, Bob Smith, ..."
  • Self-introductions: "Hi, I'm Alice Chen, VP of Product at Acme"
  • Third-party mentions as active participants: "Bob Smith will handle this"
If a person speaks even once, include them. If a name appears in the transcript without a clear role, use "Participant" as the role. If you cannot tell which organisation they belong to, use side = "unknown". You MUST NOT return an empty stakeholders array if any person can be identified.

LANGUAGE DETECTION: First, detect the language of the transcript. All text fields in your response (top_concerns[].text, action_items[].text, positive_highlights, competitive_mentions[].context, expansion_signals, key_themes, executive_summary) must be written in the SAME language as the transcript. Enum values (renewal_sentiment, overall_relationship_health, threat_level, stakeholders[].side) must always remain in English.

Respond with ONLY a valid JSON object (no markdown, no code fences) with these exact fields:

{{
  "detected_language": "en",
  "meeting_date": "Not specified",
  "meeting_time_range": "Not specified",
  "analysis_confidence": 0.0,
  "renewal_sentiment": "positive|neutral|at_risk",
  "renewal_confidence_score": 0.0,
  "overall_relationship_health": "strong|stable|fragile",
  "relationship_health_score": 0.0,
  "stakeholders": [{{"name": "Full Name", "role": "Job Title or Role", "side": "client|vendor|unknown"}}],
  "top_concerns": ["concern description in transcript language"],
  "top_concerns_quotes": ["verbatim excerpt ≤120 chars supporting each concern, same order"],
  "positive_highlights": ["highlight in transcript language"],
  "positive_highlights_quotes": ["verbatim excerpt ≤120 chars supporting each highlight, same order"],
  "action_items": ["action/commitment description in transcript language"],
  "action_items_quotes": ["verbatim excerpt ≤120 chars supporting each action item, same order"],
  "competitive_mentions": [{{"name": "CompetitorName", "context": "brief context in transcript language", "threat_level": "low|medium|high"}}],
  "expansion_signals": ["signal in transcript language"],
  "key_themes": ["theme in transcript language"],
  "executive_summary": "max 300 char summary in transcript language"
}}

Rules:
- detected_language: ISO 639-1 code of the transcript language ("en", "fr", "es", "de", "pt", etc.)
- meeting_date: the date of the conversation as explicitly stated in the transcript (e.g. "March 12, 2025"); use "Not specified" if no date is mentioned
- meeting_time_range: the time range of the conversation as explicitly stated in the transcript (e.g. "10:00 AM – 11:30 AM"); use "Not specified" if no time is mentioned
- analysis_confidence (0.0–1.0): Rate your overall confidence in the accuracy and completeness of this analysis. Base this score on the following factors: how much of the transcript contains clear, attributable dialogue (vs. crosstalk, inaudible segments, or filler); whether key QBR topics were explicitly discussed (renewal, performance, concerns, next steps); and how unambiguous the sentiment signals are. A score of 1.0 means the transcript was detailed, clear, and provided strong signals across all sections. A score below 0.5 means significant content was missing, unclear, or too ambiguous to analyze reliably.
- renewal_sentiment: "positive" if client is happy/renewing, "neutral" if uncertain, "at_risk" if showing churn signals
- renewal_confidence_score: 0.0 to 1.0 (1.0 = very confident in renewal sentiment)
- overall_relationship_health: "strong" if excellent partnership, "stable" if adequate, "fragile" if at risk
- relationship_health_score: 0.0 to 1.0 (1.0 = very strong relationship)
- stakeholders: use the participant list you identified in STEP 1 above; max 10 entries; name = full name as written in transcript (or first name if only first name appears), or "Unknown Participant" only if truly no name exists; role = job title/function from transcript, or "Participant" if not stated; side = "client" (buying organisation), "vendor" (selling/CSM organisation), "unknown" if affiliation is not clear; NEVER return [] if any person is identifiable in the transcript
- top_concerns: max 5 strings in transcript language describing the client's key concerns
- top_concerns_quotes: parallel array to top_concerns (same length, same order); each entry is the shortest verbatim excerpt (≤120 chars) from the transcript that best supports the corresponding concern; use empty string "" if no clear source quote
- positive_highlights: max 5 strings in transcript language describing positive feedback or wins
- positive_highlights_quotes: parallel array to positive_highlights (same length, same order); each entry is the shortest verbatim excerpt (≤120 chars) from the transcript that best supports the corresponding highlight; use empty string "" if no clear source quote
- action_items: max 10 strings in transcript language describing specific commitments or follow-up actions
- action_items_quotes: parallel array to action_items (same length, same order); each entry is the shortest verbatim excerpt (≤120 chars) from the transcript supporting the corresponding action; use empty string "" if no clear source quote
- competitive_mentions: array; name = competitor name; context in transcript language; threat_level always "low", "medium", or "high"
- expansion_signals: max 5 strings in transcript language
- key_themes: max 5 strings in transcript language
- executive_summary: plain text in transcript language, max 300 characters"""

            from llm_gateway import LLMConfig
            qbr_config_env = LLMConfig.from_environment()
            qbr_model = qbr_config_env.get_qbr_model()
            qbr_provider = qbr_config_env.get_qbr_provider()
            gateway = _get_transcript_gateway()
            if gateway:
                from llm_gateway import LLMRequest, LLMMessage
                logger.debug(f"QBR analysis using LLM gateway with model: {qbr_model} provider: {qbr_provider}")
                llm_request = LLMRequest(
                    messages=[LLMMessage(role="user", content=prompt)],
                    model=qbr_model,
                    temperature=0.1,
                    max_tokens=6000,
                    json_mode=True
                )
                response = gateway.chat_completion(llm_request, provider_override=qbr_provider)
                ai_response = response.content.strip() if response.content else ""
            else:
                from llm_gateway import VALID_MODELS as _VALID_MODELS
                if qbr_model in _VALID_MODELS['anthropic']:
                    logger.warning(
                        f"QBR_LLM_MODEL resolves to Anthropic model '{qbr_model}' but LLM gateway "
                        f"is unavailable. Falling back to default OpenAI model: {qbr_config_env.default_openai_model}"
                    )
                    qbr_model = qbr_config_env.default_openai_model
                logger.debug(f"QBR analysis using direct OpenAI with model: {qbr_model}")
                from openai import OpenAI
                client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
                response = client.chat.completions.create(
                    model=qbr_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=6000,
                    response_format={"type": "json_object"}
                )
                ai_response = response.choices[0].message.content.strip()

            if ai_response.startswith('```'):
                lines = ai_response.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                ai_response = '\n'.join(lines).strip()

            try:
                insights = json.loads(ai_response)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response from LLM for QBR: {ai_response[:200]}... Error: {e}")
                return None

            return insights

        except Exception as e:
            logger.error(f"Error analyzing QBR transcript with AI: {e}")
            return None

    def _process_qbr_analysis_task(self, task_data, worker_id):
        """Process a QBR analysis task"""
        from models import QBRSession, AuditLog
        from notification_utils import notify

        session_id = task_data.get('session_id')
        business_account_id = task_data.get('business_account_id')
        uploaded_by_user_id = task_data.get('uploaded_by_user_id')

        if not all([session_id, business_account_id]):
            logger.error("QBR analysis task missing required data")
            return False

        try:
            qbr_session = QBRSession.query.filter_by(
                id=session_id,
                business_account_id=business_account_id
            ).first()

            if not qbr_session:
                logger.error(f"QBR session {session_id} not found or access denied")
                return False

            qbr_session.status = 'processing'
            qbr_session.updated_at = datetime.utcnow()
            db.session.commit()

            insights = self._analyze_qbr_transcript_with_ai(
                qbr_session.transcript_content,
                qbr_session.company_name,
                qbr_session.quarter,
                qbr_session.year
            )

            if insights:
                qbr_session.extracted_insights = insights
                qbr_session.status = 'complete'
                qbr_session.updated_at = datetime.utcnow()
                db.session.commit()

                quarter_label = f"Q{qbr_session.quarter} {qbr_session.year}"
                notify(
                    business_account_id=business_account_id,
                    user_id=uploaded_by_user_id,
                    category='success',
                    message=f"QBR brief for {qbr_session.company_name} — {quarter_label} is ready"
                )

                try:
                    audit = AuditLog.create_audit_entry(
                        business_account_id=business_account_id,
                        action_type='qbr_analysis_completed',
                        action_description=f"QBR analysis completed for {qbr_session.company_name} {quarter_label}",
                        resource_type='qbr_session',
                        resource_id=str(session_id),
                        resource_name=qbr_session.company_name,
                        details={'quarter': qbr_session.quarter, 'year': qbr_session.year, 'uuid': qbr_session.uuid}
                    )
                    db.session.add(audit)
                    db.session.commit()
                except Exception as audit_err:
                    logger.error(f"Failed to create audit log for QBR completion: {audit_err}")

                logger.info(f"QBR analysis completed for session {session_id}")
                return True
            else:
                qbr_session.status = 'failed'
                qbr_session.updated_at = datetime.utcnow()
                db.session.commit()

                notify(
                    business_account_id=business_account_id,
                    user_id=uploaded_by_user_id,
                    category='error',
                    message=f"QBR analysis failed for transcript '{qbr_session.transcript_filename or 'unknown'}'"
                )

                try:
                    audit = AuditLog.create_audit_entry(
                        business_account_id=business_account_id,
                        action_type='qbr_analysis_failed',
                        action_description=f"QBR analysis failed for {qbr_session.company_name} Q{qbr_session.quarter} {qbr_session.year}",
                        resource_type='qbr_session',
                        resource_id=str(session_id),
                        resource_name=qbr_session.company_name,
                        details={'quarter': qbr_session.quarter, 'year': qbr_session.year, 'uuid': qbr_session.uuid}
                    )
                    db.session.add(audit)
                    db.session.commit()
                except Exception as audit_err:
                    logger.error(f"Failed to create audit log for QBR failure: {audit_err}")

                logger.error(f"QBR analysis failed for session {session_id}")
                return False

        except Exception as e:
            logger.error(f"QBR analysis task error for session {session_id}: {e}")
            db.session.rollback()
            company_name_for_log = task_data.get('company_name', 'unknown')
            transcript_filename_for_log = None
            try:
                qbr_session = QBRSession.query.filter_by(id=session_id, business_account_id=business_account_id).first()
                if qbr_session:
                    company_name_for_log = qbr_session.company_name
                    transcript_filename_for_log = qbr_session.transcript_filename
                    qbr_session.status = 'failed'
                    qbr_session.updated_at = datetime.utcnow()
                    db.session.commit()
            except Exception:
                pass
            filename_label = f"transcript '{transcript_filename_for_log}'" if transcript_filename_for_log else f"QBR for {company_name_for_log}"
            try:
                notify(
                    business_account_id=business_account_id,
                    user_id=uploaded_by_user_id,
                    category='error',
                    message=f"QBR analysis failed for {filename_label}"
                )
            except Exception:
                pass
            try:
                audit = AuditLog.create_audit_entry(
                    business_account_id=business_account_id,
                    action_type='qbr_analysis_failed',
                    action_description=f"QBR analysis failed (exception) for session {session_id}",
                    resource_type='qbr_session',
                    resource_id=str(session_id),
                    resource_name=company_name_for_log,
                    details={'error': str(e)[:200]}
                )
                db.session.add(audit)
                db.session.commit()
            except Exception:
                pass
            return False

    def _scheduler(self):
        """Background scheduler for campaign lifecycle management with DB advisory lock"""
        logger.info("Campaign scheduler started")
        
        while self.running:
            try:
                sleep(60)  # Check every minute, but only run scheduler every 5 minutes
                
                if not self.running:
                    break
                
                # Check if it's time to run the scheduler
                now = datetime.utcnow()
                if (self.last_scheduler_run is None or 
                    (now - self.last_scheduler_run).total_seconds() >= self.scheduler_interval):
                    
                    with app.app_context():
                        try:
                            # Use PostgreSQL advisory lock to ensure only one scheduler runs across all processes
                            # Lock ID: 123456 (arbitrary unique number for campaign scheduler)
                            lock_acquired = self._acquire_scheduler_lock(123456)
                            
                            if lock_acquired:
                                logger.debug("Campaign scheduler executing...")
                                try:
                                    changes_made = self._run_campaign_scheduler()
                                    self.last_scheduler_run = now
                                    if changes_made > 0:
                                        logger.info(f"Campaign scheduler completed: {changes_made} campaigns processed")
                                    
                                    # Run nightly reconciliation (24 hours interval)
                                    if (self.last_reconciliation_run is None or 
                                        (now - self.last_reconciliation_run).total_seconds() >= self.reconciliation_interval):
                                        logger.info("Running nightly participant status reconciliation")
                                        reconciled = self._run_participant_status_reconciliation()
                                        self.last_reconciliation_run = now
                                        if reconciled > 0:
                                            logger.info(f"Nightly reconciliation: {reconciled} records fixed")
                                finally:
                                    # Always release the lock
                                    self._release_scheduler_lock(123456)
                            else:
                                logger.debug("Scheduler already running in another process, skipping...")
                                
                        except Exception as e:
                            logger.error(f"Campaign scheduler error: {e}")
                            # Continue running despite errors
                            
            except Exception as e:
                logger.error(f"Scheduler thread error: {e}")
                # Continue running despite errors
                sleep(60)
    
    def _run_campaign_scheduler(self):
        """Execute campaign lifecycle transitions and email retries with business account scoping"""
        changes_made = 0
        try:
            today = date.today()
            logger.debug(f"Checking campaign transitions for date: {today}")
            
            # Get all business accounts
            business_accounts = BusinessAccount.query.filter_by(status='active').all()
            
            for account in business_accounts:
                try:
                    account_changes = self._process_account_campaigns(account, today)
                    changes_made += account_changes
                except Exception as e:
                    logger.error(f"Error processing campaigns for business account {account.id}: {e}")
                    # Rollback the failed transaction to prevent cascade failures
                    db.session.rollback()
                    # Continue with other accounts
            
            # Process email retries
            try:
                retry_changes = self._process_email_retries()
                changes_made += retry_changes
            except Exception as e:
                logger.error(f"Error processing email retries: {e}")
                # Rollback the failed transaction
                db.session.rollback()
            
            # Process reminder emails (twice daily: 9 AM and 2 PM UTC)
            # Dual-reminder system: Primary (after delay_days) + Midpoint (halfway through campaign)
            try:
                from reminder_service import ReminderService
                from datetime import datetime
                
                current_hour = datetime.utcnow().hour
                
                # Only process reminders during scheduled hours (9 AM and 2 PM UTC)
                # This runs twice daily for efficiency and professional timing
                if current_hour in [9, 14]:
                    # Process PRIMARY reminders (sent after reminder_delay_days)
                    primary_start = datetime.utcnow()
                    primary_stats = ReminderService.process_reminder_batch(
                        reminder_type='primary',
                        campaign_id=None,      # Process all eligible campaigns
                        batch_size=50,         # Limit to prevent queue overload
                        stagger_minutes=0      # Queue handles async delivery naturally
                    )
                    primary_duration_ms = (datetime.utcnow() - primary_start).total_seconds() * 1000
                    
                    if primary_stats['processed'] > 0:
                        logger.info(f"Primary reminder batch: {primary_stats['processed']} queued, "
                                   f"{primary_stats['total_eligible']} total eligible, "
                                   f"{primary_duration_ms:.1f}ms")
                    
                    changes_made += primary_stats['processed']
                    
                    # Process MIDPOINT reminders (sent halfway through campaign)
                    midpoint_start = datetime.utcnow()
                    midpoint_stats = ReminderService.process_reminder_batch(
                        reminder_type='midpoint',
                        campaign_id=None,      # Process all eligible campaigns
                        batch_size=50,         # Limit to prevent queue overload
                        stagger_minutes=0      # Queue handles async delivery naturally
                    )
                    midpoint_duration_ms = (datetime.utcnow() - midpoint_start).total_seconds() * 1000
                    
                    if midpoint_stats['processed'] > 0:
                        logger.info(f"Midpoint reminder batch: {midpoint_stats['processed']} queued, "
                                   f"{midpoint_stats['total_eligible']} total eligible, "
                                   f"{midpoint_duration_ms:.1f}ms")
                    
                    changes_made += midpoint_stats['processed']
                else:
                    # Outside scheduled hours - skip reminder processing
                    logger.info(f"Reminder processing skipped (current hour: {current_hour}:00 UTC, scheduled: 09:00 and 14:00 UTC)")
                
            except Exception as e:
                logger.error(f"Error processing reminders: {e}")
                # Rollback this transaction only - doesn't affect campaign transitions
                db.session.rollback()
            
            return changes_made
                    
        except Exception as e:
            logger.error(f"Campaign scheduler failed: {e}")
            return changes_made
    
    def _process_email_retries(self):
        """Process failed emails that are ready for retry"""
        retry_count = 0
        try:
            # Get emails ready for retry
            pending_retries = EmailDelivery.get_pending_retries()
            
            for email_delivery in pending_retries:
                try:
                    # Increment retry count
                    email_delivery.increment_retry()
                    
                    # Parse email data to recreate task
                    task_data = email_delivery.get_email_data()
                    if not task_data:
                        logger.error(f"No task data found for EmailDelivery {email_delivery.id}")
                        continue
                    
                    # Add email_delivery_id to task data for tracking
                    task_data['email_delivery_id'] = email_delivery.id
                    
                    # Add retry task to queue
                    self.add_task(
                        task_type='send_email',
                        priority=2,  # Higher priority for retries
                        task_data=task_data
                    )
                    
                    retry_count += 1
                    logger.info(f"Queued email retry {email_delivery.retry_count}/{email_delivery.max_retries} for delivery {email_delivery.id}")
                    
                except Exception as e:
                    logger.error(f"Error processing retry for EmailDelivery {email_delivery.id}: {e}")
                    # Mark as failed to avoid endless retry loops
                    email_delivery.mark_failed(f"Retry processing error: {str(e)}", is_permanent=True)
            
            # Commit all changes
            if retry_count > 0:
                db.session.commit()
                logger.info(f"Processed {retry_count} email retries")
            
        except Exception as e:
            logger.error(f"Email retry processing failed: {e}")
            # Rollback on error
            db.session.rollback()
            
        return retry_count
    
    def _run_participant_status_reconciliation(self):
        """
        Reconcile participant status with survey responses (drift healing).
        Finds CampaignParticipant records where status != 'completed' but a response exists.
        This fixes historical inconsistencies caused by non-atomic status updates.
        Uses atomic transactions for each reconciliation batch.
        """
        reconciled_count = 0
        
        try:
            logger.info("Starting participant status reconciliation")
            
            # Find all campaign-participant associations that:
            # 1. Status is not 'completed'
            # 2. Have a linked survey response (via campaign_participant_id)
            # Use read-only query to avoid locking during scan
            incomplete_association_ids = db.session.query(
                CampaignParticipant.id,
                CampaignParticipant.participant_id,
                CampaignParticipant.campaign_id,
                CampaignParticipant.status
            ).filter(
                CampaignParticipant.status != 'completed',
                CampaignParticipant.id.in_(
                    db.session.query(SurveyResponse.campaign_participant_id).filter(
                        SurveyResponse.campaign_participant_id.isnot(None)
                    )
                )
            ).all()
            
            # Process each association in a separate transaction for safety
            for assoc_id, participant_id, campaign_id, old_status in incomplete_association_ids:
                try:
                    # Start a new scoped transaction for each update
                    association = CampaignParticipant.query.filter_by(id=assoc_id).first()
                    if not association:
                        continue
                    
                    # Find the linked response to get created timestamp
                    response = SurveyResponse.query.filter_by(
                        campaign_participant_id=assoc_id
                    ).first()
                    
                    if response:
                        association.status = 'completed'
                        association.completed_at = response.created_at
                        
                        # Commit this individual reconciliation
                        db.session.commit()
                        
                        reconciled_count += 1
                        logger.info(
                            f"Reconciled participant {participant_id} "
                            f"in campaign {campaign_id}: "
                            f"{old_status} -> completed (response created at {response.created_at})"
                        )
                
                except Exception as e:
                    logger.error(f"Error reconciling association {assoc_id}: {e}")
                    db.session.rollback()
                    # Continue with next association
                    continue
            
            # Log final summary
            if reconciled_count > 0:
                logger.info(f"✅ Participant status reconciliation completed: {reconciled_count} records fixed")
            else:
                logger.debug("Participant status reconciliation: No drift detected")
            
        except Exception as e:
            logger.error(f"Participant status reconciliation failed: {e}")
            db.session.rollback()
        
        return reconciled_count
    
    def _process_account_campaigns(self, business_account, today):
        """Process campaign transitions for a specific business account"""
        account_id = business_account.id
        account_name = business_account.name
        changes_made = 0
        
        # Check for campaigns that need to be activated (ready -> active)
        ready_campaigns = Campaign.query.filter_by(
            business_account_id=account_id,
            status='ready'
        ).filter(Campaign.start_date <= today).all()
        
        # Check for campaigns that need to be completed (active -> completed)
        # FIX: Use <= instead of < to complete campaigns ON their end_date (at midnight)
        expired_campaigns = Campaign.query.filter_by(
            business_account_id=account_id,
            status='active'
        ).filter(Campaign.end_date <= today).all()
        
        # Log only when there are campaigns to process
        if ready_campaigns or expired_campaigns:
            logger.debug(f"Processing campaigns for business account {account_id} ({account_name}): "
                        f"{len(ready_campaigns)} ready, {len(expired_campaigns)} expired")
        
        # Process activations (respecting single active campaign constraint)
        if ready_campaigns:
            activation_changes = self._process_campaign_activations(account_id, account_name, ready_campaigns, today)
            changes_made += activation_changes
        
        # Process completions
        if expired_campaigns:
            completion_changes = self._process_campaign_completions(account_id, account_name, expired_campaigns)
            changes_made += completion_changes
        
        return changes_made
    
    def _process_campaign_activations(self, account_id, account_name, ready_campaigns, today):
        """Process campaign activations with single active campaign constraint.
        
        Respects the BusinessAccount.allow_parallel_campaigns setting:
        - If False (default): Only activate one campaign if no active campaigns exist
        - If True: Activate all eligible ready campaigns
        """
        changes_made = 0
        
        # Check if parallel campaigns are allowed for this business account
        account = BusinessAccount.query.get(account_id)
        allow_parallel = account.allow_parallel_campaigns if account else False
        
        # Check if there's already an active campaign for this business account
        existing_active = Campaign.query.filter_by(
            business_account_id=account_id,
            status='active'
        ).first()
        
        if existing_active and not allow_parallel:
            logger.debug(f"Cannot activate campaigns for account {account_id} ({account_name}): "
                        f"Campaign '{existing_active.name}' is already active (parallel campaigns disabled)")
            return changes_made
        
        # Activate ready campaigns that meet criteria
        for campaign in sorted(ready_campaigns, key=lambda c: c.start_date):
            try:
                # Double-check activation criteria
                # Use count() instead of len() to avoid loading all participants
                participant_count = CampaignParticipant.query.filter_by(campaign_id=campaign.id).count()
                if (campaign.status == 'ready' and 
                    campaign.start_date <= today and 
                    campaign.description and 
                    participant_count > 0):
                    
                    # Activate the campaign
                    campaign.status = 'active'
                    
                    # Generate tokens for all campaign participants
                    import uuid
                    from datetime import datetime
                    campaign_participants = CampaignParticipant.query.filter_by(
                        campaign_id=campaign.id,
                        business_account_id=account_id
                    ).all()
                    
                    token_success_count = 0
                    for cp in campaign_participants:
                        try:
                            # Generate token if missing
                            if not cp.token:
                                cp.token = str(uuid.uuid4())
                            
                            # Update status and timestamp
                            if cp.status == 'pending':
                                cp.status = 'invited'
                                cp.invited_at = datetime.utcnow()
                            
                            token_success_count += 1
                        except Exception as e:
                            logger.error(f"Error generating token for participant {cp.id} in campaign {campaign.id}: {e}")
                    
                    db.session.commit()
                    
                    logger.info(f"Auto-activated campaign '{campaign.name}' (ID: {campaign.id}) "
                               f"for business account {account_id} ({account_name}) with {token_success_count} tokens generated")
                    
                    # Audit log auto-activation
                    try:
                        from audit_utils import queue_audit_log
                        queue_audit_log(
                            business_account_id=account_id,
                            action_type='campaign_activated',
                            resource_type='campaign',
                            resource_id=campaign.id,
                            resource_name=campaign.name,
                            details={
                                'auto_activated': True,
                                'previous_status': 'ready',
                                'activated_by': 'scheduler'
                            }
                        )
                    except Exception as audit_error:
                        logger.error(f"Failed to audit auto-activation of campaign {campaign.id}: {audit_error}")
                    
                    changes_made += 1
                    
                    # Only activate one campaign at a time if parallel campaigns disabled
                    if not allow_parallel:
                        break
                    
            except Exception as e:
                logger.error(f"Failed to activate campaign {campaign.id}: {e}")
                db.session.rollback()
        
        return changes_made
    
    def _process_campaign_completions(self, account_id, account_name, expired_campaigns):
        """Process campaign completions for expired campaigns"""
        changes_made = 0
        
        for campaign in expired_campaigns:
            try:
                # Complete the campaign and generate KPI snapshot
                campaign.close_campaign()
                db.session.commit()
                
                logger.info(f"Auto-completed campaign '{campaign.name}' (ID: {campaign.id}) "
                           f"for business account {account_id} ({account_name}) - expired on {campaign.end_date}")
                
                # Audit log auto-completion
                try:
                    from audit_utils import queue_audit_log
                    queue_audit_log(
                        business_account_id=account_id,
                        action_type='campaign_completed',
                        resource_type='campaign',
                        resource_id=campaign.id,
                        resource_name=campaign.name,
                        details={
                            'auto_completed': True,
                            'previous_status': 'active',
                            'completed_by': 'scheduler',
                            'kpi_snapshot_generated': True
                        }
                    )
                except Exception as audit_error:
                    logger.error(f"Failed to audit auto-completion of campaign {campaign.id}: {audit_error}")
                
                changes_made += 1
                
            except Exception as e:
                logger.error(f"Failed to complete campaign {campaign.id}: {e}")
                db.session.rollback()
        
        return changes_made
    
    def _acquire_scheduler_lock(self, lock_id):
        """Acquire PostgreSQL advisory lock for scheduler"""
        try:
            from sqlalchemy import text
            # Use PostgreSQL advisory lock to prevent multiple schedulers
            result = db.session.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": lock_id}
            ).scalar()
            return result
        except Exception as e:
            logger.error(f"Failed to acquire scheduler lock: {e}")
            return False
    
    def _release_scheduler_lock(self, lock_id):
        """Release PostgreSQL advisory lock for scheduler"""
        try:
            from sqlalchemy import text
            db.session.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": lock_id}
            )
        except Exception as e:
            logger.error(f"Failed to release scheduler lock: {e}")

    def force_scheduler_run(self):
        """Force immediate scheduler run (for admin testing) with lock protection"""
        logger.info("Force running campaign scheduler...")
        try:
            with app.app_context():
                # Use advisory lock even for forced runs to prevent conflicts
                lock_acquired = self._acquire_scheduler_lock(123456)
                
                if lock_acquired:
                    try:
                        self._run_campaign_scheduler()
                        self.last_scheduler_run = datetime.utcnow()
                        return True
                    finally:
                        self._release_scheduler_lock(123456)
                else:
                    logger.warning("Could not acquire scheduler lock for forced run")
                    return False
        except Exception as e:
            logger.error(f"Forced scheduler run failed: {e}")
            return False
    
    def get_queue_size(self):
        """Get current queue size"""
        return self.task_queue.qsize()
    
    def get_stats(self):
        """Get queue and scheduler statistics"""
        return {
            'queue_size': self.task_queue.qsize(),
            'workers': len(self.workers),
            'running': self.running,
            'last_scheduler_run': self.last_scheduler_run.isoformat() + 'Z' if self.last_scheduler_run else None,
            'scheduler_interval': self.scheduler_interval
        }

# Global task queue instance - conditionally initialized based on feature flag
task_queue = None  # Will be initialized in start_task_queue()

def start_task_queue():
    """Start the global task queue (in-memory or PostgreSQL based on feature flag)"""
    global task_queue
    
    # Import queue configuration
    from queue_config import queue_config
    
    if queue_config.is_postgres_enabled():
        # Use PostgreSQL-backed persistent queue
        from postgres_task_queue import PostgresTaskQueue
        task_queue = PostgresTaskQueue(
            max_workers=queue_config.get_worker_count(),
            poll_interval=queue_config.get_poll_interval(),
            scheduler_interval=queue_config.get_scheduler_interval(),
            stale_task_threshold=queue_config.get_stale_task_threshold()
        )
        logger.info("✅ PostgreSQL task queue initialized")
    else:
        # Use in-memory queue (current/default)
        task_queue = TaskQueue(max_workers=3)
        logger.info("📝 In-memory task queue initialized (default)")
    
    task_queue.start()

def add_analysis_task(response_id):
    """Add an AI analysis task to the queue"""
    task_queue.add_task('ai_analysis', data_id=response_id)

def add_email_task(email_type, task_data, priority=2):
    """Add an email task to the queue
    
    Args:
        email_type: 'participant_invitation' or 'campaign_notification'
        task_data: Dict with email-specific data
        priority: Task priority (2 = high for emails, 1 = normal)
    """
    task_data['email_type'] = email_type
    task_queue.add_task('send_email', priority=priority, task_data=task_data)

def send_participant_invitation_async(participant_email, participant_name, 
                                      campaign_name, survey_token, business_account_name):
    """Queue participant invitation email for background sending"""
    task_data = {
        'participant_email': participant_email,
        'participant_name': participant_name,
        'campaign_name': campaign_name,
        'survey_token': survey_token,
        'business_account_name': business_account_name
    }
    add_email_task('participant_invitation', task_data)

def send_campaign_notification_async(notification_type, campaign_name, campaign_id,
                                     business_account_name, additional_data=None):
    """Queue campaign notification email for background sending"""
    task_data = {
        'notification_type': notification_type,
        'campaign_name': campaign_name,
        'campaign_id': campaign_id,
        'business_account_name': business_account_name,
        'additional_data': additional_data
    }
    add_email_task('campaign_notification', task_data)

def get_queue_stats():
    """Get queue statistics"""
    return task_queue.get_stats()

def add_export_task(campaign_id, business_account_id):
    """Add a campaign export task to the queue
    
    Args:
        campaign_id: ID of the campaign to export
        business_account_id: ID of the business account (for security)
        
    Returns:
        job_id: Unique identifier for tracking the export job
    """
    # Create export job and get job ID
    job_id = task_queue.create_export_job(campaign_id, business_account_id)
    
    # Queue the export task
    task_data = {
        'job_id': job_id,
        'campaign_id': campaign_id,
        'business_account_id': business_account_id
    }
    task_queue.add_task('export_campaign', priority=1, task_data=task_data)
    
    logger.info(f"Added export task for campaign {campaign_id} (job_id: {job_id})")
    return job_id

def get_export_job_status(job_id):
    """Get the status of an export job"""
    return task_queue.get_export_job_status(job_id)

def cleanup_export_jobs():
    """Clean up old export jobs and files"""
    task_queue.cleanup_old_export_jobs()