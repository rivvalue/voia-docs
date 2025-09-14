import json
import os
import logging
from datetime import datetime, timedelta, date
from threading import Thread
from queue import Queue, Empty
from time import sleep
from app import app, db
from models import SurveyResponse, Campaign, BusinessAccount, EmailDelivery
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
                    email_delivery_id=email_delivery.id
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
                    email_delivery_id=email_delivery.id
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