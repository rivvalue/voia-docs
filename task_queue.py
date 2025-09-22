import json
import os
import logging
import uuid
from datetime import datetime, timedelta, date
from threading import Thread, Lock
from queue import Queue, Empty
from time import sleep
from app import app, db
from models import SurveyResponse, Campaign, BusinessAccount, EmailDelivery, CampaignParticipant, Participant
from ai_analysis import analyze_survey_response
from email_service import email_service

logger = logging.getLogger(__name__)

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
        
        # Export job tracking
        self.export_jobs = {}  # job_id -> job_status
        self.export_jobs_lock = Lock()
        
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
                # Process campaign export task
                success = self._process_export_task(task_data, worker_id)
                
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
                        
        except Exception as e:
            logger.error(f"Error processing task {task}: {e}")
    
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
                # Send participant invitation email with delivery tracking
                result = email_service.send_participant_invitation(
                    participant_email=task_data['participant_email'],
                    participant_name=task_data['participant_name'],
                    campaign_name=task_data['campaign_name'],
                    survey_token=task_data['survey_token'],
                    business_account_name=task_data['business_account_name'],
                    email_delivery_id=email_delivery.id,
                    business_account_id=task_data.get('business_account_id')
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
                # Get chunk of campaign participants
                participant_chunk = CampaignParticipant.query.filter_by(
                    campaign_id=campaign.id
                ).join(Participant).offset(offset).limit(chunk_size).all()
                
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
        """Update export job status thread-safely"""
        with self.export_jobs_lock:
            if job_id in self.export_jobs:
                self.export_jobs[job_id].update({
                    'status': status,
                    'updated_at': datetime.utcnow(),
                    'error': error,
                    'file_path': file_path,
                    'progress': progress
                })
    
    def create_export_job(self, campaign_id, business_account_id):
        """Create a new export job and return job ID"""
        job_id = str(uuid.uuid4())
        
        with self.export_jobs_lock:
            self.export_jobs[job_id] = {
                'job_id': job_id,
                'campaign_id': campaign_id,
                'business_account_id': business_account_id,
                'status': 'queued',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'error': None,
                'file_path': None,
                'progress': None
            }
        
        return job_id
    
    def get_export_job_status(self, job_id):
        """Get export job status"""
        with self.export_jobs_lock:
            return self.export_jobs.get(job_id)
    
    def cleanup_old_export_jobs(self, max_age_hours=24):
        """Clean up old export jobs and their files"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        with self.export_jobs_lock:
            jobs_to_remove = []
            for job_id, job_data in self.export_jobs.items():
                if job_data['updated_at'] < cutoff_time:
                    # Clean up file if it exists
                    if job_data.get('file_path') and os.path.exists(job_data['file_path']):
                        try:
                            os.remove(job_data['file_path'])
                            logger.info(f"Cleaned up export file: {job_data['file_path']}")
                        except Exception as e:
                            logger.error(f"Error cleaning up export file {job_data['file_path']}: {e}")
                    
                    jobs_to_remove.append(job_id)
            
            for job_id in jobs_to_remove:
                del self.export_jobs[job_id]
                
            if jobs_to_remove:
                logger.info(f"Cleaned up {len(jobs_to_remove)} old export jobs")
    
    def _process_executive_report_task(self, task_data, worker_id):
        """Process executive report generation task"""
        try:
            # Get task parameters
            campaign_id = task_data.get('campaign_id')
            business_account_id = task_data.get('business_account_id')
            
            if not all([campaign_id, business_account_id]):
                logger.error(f"Missing executive report task parameters: {task_data}")
                return False
            
            # Use lazy import to avoid circular dependency and import correct class
            from executive_report_service import ExecutiveReportGenerator
            
            generator = ExecutiveReportGenerator()
            report_file_path = generator.generate_campaign_report(campaign_id, business_account_id)
            
            if report_file_path:
                # Store report information in database
                self._store_executive_report_info(campaign_id, business_account_id, report_file_path)
                
                logger.info(f"Executive report generated for campaign {campaign_id}: {report_file_path}")
                
                # Add audit log for report generation
                try:
                    from audit_utils import queue_audit_log
                    from models import Campaign
                    
                    campaign = Campaign.query.get(campaign_id)
                    
                    queue_audit_log(
                        business_account_id=business_account_id,
                        action_type='executive_report_generated',
                        resource_type='campaign',
                        resource_id=campaign_id,
                        resource_name=campaign.name if campaign else f'Campaign {campaign_id}',
                        details={
                            'file_path': report_file_path,
                            'report_type': 'executive_report'
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to log executive report audit event: {e}")
                
                return True
            else:
                logger.error(f"Failed to generate executive report for campaign {campaign_id}")
                return False
                
        except Exception as e:
            logger.error(f"Executive report task error for campaign {campaign_id}: {e}")
            return False
    
    def _store_executive_report_info(self, campaign_id, business_account_id, file_path):
        """Store executive report information in the database"""
        try:
            from models import ExecutiveReport
            from datetime import datetime
            import os
            
            # Calculate file size
            file_size = None
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
            
            # Create or update executive report record
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
            
            db.session.commit()
            logger.info(f"Executive report info stored for campaign {campaign_id}")
            
        except Exception as e:
            logger.error(f"Failed to store executive report info: {e}")
    
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
                    # Continue with other accounts
            
            # Process email retries
            try:
                retry_changes = self._process_email_retries()
                changes_made += retry_changes
            except Exception as e:
                logger.error(f"Error processing email retries: {e}")
            
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
            
        return retry_count
    
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
        expired_campaigns = Campaign.query.filter_by(
            business_account_id=account_id,
            status='active'
        ).filter(Campaign.end_date < today).all()
        
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
        """Process campaign activations with single active campaign constraint"""
        changes_made = 0
        
        # Check if there's already an active campaign for this business account
        existing_active = Campaign.query.filter_by(
            business_account_id=account_id,
            status='active'
        ).first()
        
        if existing_active:
            logger.debug(f"Cannot activate campaigns for account {account_id} ({account_name}): "
                        f"Campaign '{existing_active.name}' is already active")
            return changes_made
        
        # Activate the earliest ready campaign that meets criteria
        for campaign in sorted(ready_campaigns, key=lambda c: c.start_date):
            try:
                # Double-check activation criteria
                if (campaign.status == 'ready' and 
                    campaign.start_date <= today and 
                    campaign.description and 
                    len(campaign.participants) > 0):
                    
                    # Activate the campaign
                    campaign.status = 'active'
                    db.session.commit()
                    
                    logger.info(f"Auto-activated campaign '{campaign.name}' (ID: {campaign.id}) "
                               f"for business account {account_id} ({account_name})")
                    
                    changes_made += 1
                    # Only activate one campaign at a time
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
            'last_scheduler_run': self.last_scheduler_run.isoformat() if self.last_scheduler_run else None,
            'scheduler_interval': self.scheduler_interval
        }

# Global task queue instance
task_queue = TaskQueue(max_workers=3)  # Start with 3 workers for AI analysis

def start_task_queue():
    """Start the global task queue"""
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