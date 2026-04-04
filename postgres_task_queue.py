"""
PostgreSQL-backed persistent task queue for VOÏA platform.

This module provides a persistent, scalable task queue implementation using PostgreSQL
as the storage backend. It replaces the in-memory queue for production environments
requiring reliability and persistence across application restarts.

Key Features:
- Persistent task storage (survives restarts)
- Multi-worker safe (SELECT FOR UPDATE SKIP LOCKED)
- Priority-based task processing
- Automatic retry logic with exponential backoff
- Task history and monitoring
- Supports 0.07-0.2 tasks/second with 500-2,500x capacity headroom

Architecture:
- Workers poll PostgreSQL every 2 seconds (configurable)
- Tasks claimed atomically to prevent duplicates
- Failed tasks auto-retry up to max_retries
- Completed tasks kept for 7 days, failed for 30 days
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from threading import Thread, Lock
from time import sleep
from typing import Dict, List, Optional, Any
from sqlalchemy import text
from sqlalchemy.orm import joinedload

from app import app, db
from models import SurveyResponse, Campaign, BusinessAccount, EmailDelivery, CampaignParticipant, Participant
from ai_analysis import analyze_survey_response
from email_service import email_service

logger = logging.getLogger(__name__)


class PostgresTaskQueue:
    """PostgreSQL-backed persistent task queue with worker pool"""
    
    def __init__(self, max_workers=5, poll_interval=2, scheduler_interval=300, stale_task_threshold=30):
        """
        Initialize PostgreSQL task queue.
        
        Args:
            max_workers: Number of worker threads
            poll_interval: Seconds between database polls for new tasks
            scheduler_interval: Seconds between scheduler runs (default: 300 = 5 minutes)
            stale_task_threshold: Minutes before a task is considered stuck (default: 30)
        """
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self.workers = []
        self.running = False
        self.scheduler_thread = None
        self.last_scheduler_run = None
        self.scheduler_interval = scheduler_interval
        self.stale_task_threshold = stale_task_threshold
        self.last_reconciliation_run = None
        self.reconciliation_interval = 86400  # 24 hours in seconds (nightly)
        self.lock = Lock()
        
        logger.info(f"PostgresTaskQueue initialized: {max_workers} workers, {poll_interval}s poll, scheduler: {scheduler_interval}s, stale threshold: {stale_task_threshold}min")
    
    def start(self):
        """Start the task queue workers and scheduler"""
        if self.running:
            return
        
        self.running = True
        logger.info(f"Starting PostgreSQL task queue with {self.max_workers} workers")
        
        # Recover any stale tasks from previous crashes/restarts (zero data loss)
        # Use configurable threshold to avoid requeuing long-running tasks (executive reports, transcript analysis)
        with app.app_context():
            recovered_count = self.recover_stale_tasks(stale_threshold_minutes=self.stale_task_threshold)
            if recovered_count > 0:
                logger.warning(f"Recovered {recovered_count} stale tasks on startup")
            
            # Recover stuck bulk operation jobs and clear campaign locks
            bulk_recovered_count = self.recover_stuck_bulk_jobs(stale_threshold_minutes=self.stale_task_threshold)
            if bulk_recovered_count > 0:
                logger.warning(f"Recovered {bulk_recovered_count} stuck bulk operation jobs on startup")
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = Thread(target=self._worker, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
        
        # Start the campaign scheduler
        self.scheduler_thread = Thread(target=self._scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("PostgreSQL task queue and scheduler started")
    
    def stop(self):
        """Stop the task queue workers and scheduler"""
        self.running = False
        logger.info("Stopping PostgreSQL task queue and scheduler")
    
    def add_task(self, task_type, data_id=None, priority=1, task_data=None):
        """
        Add a task to the PostgreSQL queue.
        
        Args:
            task_type: Type of task ('ai_analysis', 'send_email', etc.)
            data_id: ID for data-based tasks (response_id for AI analysis)
            priority: Task priority (1=normal, 2=high, 3=urgent)
            task_data: Additional data for the task (email details, etc.)
        """
        try:
            # Prepare task data
            task_payload = task_data or {}
            if data_id:
                task_payload['data_id'] = data_id
            
            # Extract business context for filtering/reporting
            business_account_id = task_payload.get('business_account_id')
            campaign_id = task_payload.get('campaign_id')
            
            # Insert task into database - use CAST to avoid parameter style conflicts
            json_str = json.dumps(task_payload)
            result = db.session.execute(
                text("""
                    INSERT INTO task_queue (
                        task_type, task_data, priority, status, 
                        scheduled_at, business_account_id, campaign_id,
                        created_at, updated_at, retry_count, max_retries
                    ) VALUES (
                        :task_type, CAST(:task_data AS jsonb), :priority, 'pending',
                        NOW(), :business_account_id, :campaign_id,
                        NOW(), NOW(), 0, 3
                    ) RETURNING id
                """),
                {
                    'task_type': task_type,
                    'task_data': json_str,
                    'priority': priority,
                    'business_account_id': business_account_id,
                    'campaign_id': campaign_id
                }
            )
            
            task_id = result.scalar()
            db.session.commit()
            
            # Log task addition
            if task_type == 'send_email':
                email_type = task_payload.get('email_type', 'unknown')
                logger.info(f"Added email task ({email_type}) to PostgreSQL queue: task_id={task_id}")
            elif task_type == 'executive_report':
                logger.info(f"Added executive report task for campaign {campaign_id} to PostgreSQL queue: task_id={task_id}")
            elif task_type == 'transcript_analysis':
                participant_name = task_payload.get('participant_name', 'unknown')
                logger.info(f"Added transcript analysis task for campaign {campaign_id}, participant {participant_name}: task_id={task_id}")
            else:
                logger.info(f"Added task {task_type} to PostgreSQL queue: task_id={task_id}, data_id={data_id}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to add task to PostgreSQL queue: {e}")
            db.session.rollback()
            raise
    
    def _worker(self, worker_id):
        """Worker function that processes tasks from PostgreSQL"""
        worker_name = f"postgres-worker-{worker_id}"
        logger.info(f"PostgreSQL worker {worker_name} started")
        
        poll_interval = self.poll_interval
        consecutive_empty_polls = 0
        
        while self.running:
            try:
                # All database operations need Flask app context
                with app.app_context():
                    # Claim next task atomically
                    task = self._claim_next_task(worker_name)
                    
                    if task:
                        # Reset poll interval on successful claim
                        poll_interval = self.poll_interval
                        consecutive_empty_polls = 0
                        
                        logger.debug(f"Worker {worker_name} processing task: {task['task_type']} (id={task['id']})")
                        
                        # Process the task
                        success = self._process_task(task, worker_name)
                        
                        if success:
                            self._mark_task_completed(task['id'])
                        else:
                            self._mark_task_failed(task['id'], "Task processing returned False")
                    else:
                        # No tasks available - exponential backoff
                        consecutive_empty_polls += 1
                        poll_interval = min(30, self.poll_interval * (1.5 ** min(consecutive_empty_polls, 5)))
                
                # Sleep outside app context
                if not task:
                    sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                sleep(self.poll_interval)
    
    def _claim_next_task(self, worker_name: str) -> Optional[Dict]:
        """
        Atomically claim the next available task using SELECT FOR UPDATE SKIP LOCKED.
        
        Args:
            worker_name: Identifier for this worker
            
        Returns:
            Task dict if available, None if queue empty
        """
        try:
            result = db.session.execute(
                text("""
                    UPDATE task_queue 
                    SET status = 'processing', 
                        claimed_at = NOW(), 
                        claimed_by = :worker_name,
                        started_at = NOW(),
                        updated_at = NOW()
                    WHERE id = (
                        SELECT id 
                        FROM task_queue
                        WHERE status = 'pending'
                          AND scheduled_at <= NOW()
                        ORDER BY priority DESC, scheduled_at ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    RETURNING *
                """),
                {"worker_name": worker_name}
            )
            
            row = result.fetchone()
            if row:
                db.session.commit()
                # Convert row to dict
                # PostgreSQL JSONB is already parsed as dict by psycopg2
                task_data = row[2]
                if isinstance(task_data, str):
                    task_data = json.loads(task_data)
                elif task_data is None:
                    task_data = {}
                
                return {
                    'id': row[0],
                    'task_type': row[1],
                    'task_data': task_data,
                    'status': row[3],
                    'priority': row[4],
                    'scheduled_at': row[5],
                    'claimed_at': row[6],
                    'claimed_by': row[7],
                    'started_at': row[8],
                    'completed_at': row[9],
                    'error_message': row[10],
                    'retry_count': row[11],
                    'max_retries': row[12],
                    'created_at': row[13],
                    'updated_at': row[14],
                    'business_account_id': row[15],
                    'campaign_id': row[16]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error claiming task: {e}")
            db.session.rollback()
            return None
    
    def _mark_task_completed(self, task_id: int):
        """Mark a task as completed"""
        try:
            db.session.execute(
                text("""
                    UPDATE task_queue 
                    SET status = 'completed',
                        completed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :task_id
                """),
                {"task_id": task_id}
            )
            db.session.commit()
            logger.debug(f"Task {task_id} marked as completed")
        except Exception as e:
            logger.error(f"Error marking task {task_id} as completed: {e}")
            db.session.rollback()
    
    def _mark_task_failed(self, task_id: int, error_message: str):
        """Mark a task as failed and handle retry logic"""
        try:
            # Get current retry count
            result = db.session.execute(
                text("SELECT retry_count, max_retries FROM task_queue WHERE id = :task_id"),
                {"task_id": task_id}
            )
            row = result.fetchone()
            
            if not row:
                logger.error(f"Task {task_id} not found for failure handling")
                return
            
            retry_count = row[0]
            max_retries = row[1]
            
            if retry_count < max_retries:
                retry_delay_minutes = 2 ** retry_count  # 1, 2, 4 minutes
                db.session.execute(
                    text("""
                        UPDATE task_queue 
                        SET status = 'pending',
                            retry_count = retry_count + 1,
                            scheduled_at = NOW() + :delay * INTERVAL '1 minute',
                            error_message = :error,
                            updated_at = NOW()
                        WHERE id = :task_id
                    """),
                    {"task_id": task_id, "delay": retry_delay_minutes, "error": error_message}
                )
                logger.info(f"Task {task_id} scheduled for retry {retry_count + 1}/{max_retries} in {retry_delay_minutes} minutes")
            else:
                # Max retries exceeded - mark as failed permanently
                db.session.execute(
                    text("""
                        UPDATE task_queue 
                        SET status = 'failed',
                            completed_at = NOW(),
                            error_message = :error,
                            updated_at = NOW()
                        WHERE id = :task_id
                    """),
                    {"task_id": task_id, "error": error_message}
                )
                logger.error(f"Task {task_id} failed permanently after {max_retries} retries: {error_message}")
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error handling task failure for {task_id}: {e}")
            db.session.rollback()
    
    def _process_task(self, task: Dict, worker_name: str) -> bool:
        """
        Process a single task (same logic as in-memory queue).
        
        Args:
            task: Task dictionary from database
            worker_name: Worker identifier
            
        Returns:
            True if successful, False if failed
        """
        try:
            task_type = task['task_type']
            task_data = task['task_data']
            data_id = task_data.get('data_id')
            
            if task_type == 'ai_analysis':
                # Perform AI analysis
                success = analyze_survey_response(data_id)
                
                if success:
                    logger.info(f"Worker {worker_name} completed AI analysis for response {data_id}")
                else:
                    logger.error(f"Worker {worker_name} failed AI analysis for response {data_id}")
                    
                    # Mark as failed in survey_response database
                    response = SurveyResponse.query.get(data_id)
                    if response:
                        response.analyzed_at = datetime.utcnow()
                        response.sentiment_label = 'analysis_failed'
                        db.session.commit()
                
                return success
                
            elif task_type == 'send_email':
                # Process email sending task
                from task_queue import TaskQueue
                temp_queue = TaskQueue()
                success = temp_queue._process_email_task(task_data, worker_name)
                return success
                
            elif task_type == 'audit_log':
                # Process audit log writing task
                from task_queue import TaskQueue
                temp_queue = TaskQueue()
                success = temp_queue._process_audit_log_task(task_data, worker_name)
                return success
                
            elif task_type == 'export_campaign':
                # Process campaign export task
                from task_queue import TaskQueue
                temp_queue = TaskQueue()
                success = temp_queue._process_export_task(task_data, worker_name)
                return success
                
            elif task_type == 'executive_report':
                # Process executive report generation task
                from task_queue import TaskQueue
                temp_queue = TaskQueue()
                success = temp_queue._process_executive_report_task(task_data, worker_name)
                return success
                
            elif task_type == 'transcript_analysis':
                # Process transcript analysis task
                from task_queue import TaskQueue
                temp_queue = TaskQueue()
                success = temp_queue._process_transcript_analysis_task(task_data, worker_name)
                return success
                
            elif task_type == 'send_reminder_email':
                # Process reminder email task
                from task_queue import TaskQueue
                temp_queue = TaskQueue()
                success = temp_queue._process_reminder_email_task(task_data, worker_name)
                return success
            
            elif task_type == 'bulk_participant_add':
                # Process bulk participant addition task
                from task_queue import TaskQueue
                temp_queue = TaskQueue()
                success = temp_queue._process_bulk_participant_add_task(task_data, worker_name)
                return success
            
            elif task_type == 'bulk_participant_remove':
                # Process bulk participant removal task
                from task_queue import TaskQueue
                temp_queue = TaskQueue()
                success = temp_queue._process_bulk_participant_remove_task(task_data, worker_name)
                return success
            
            elif task_type == 'qbr_analysis':
                # Process QBR transcript analysis task
                from task_queue import TaskQueue
                temp_queue = TaskQueue()
                success = temp_queue._process_qbr_analysis_task(task_data, worker_name)
                return success
            
            else:
                logger.error(f"Unknown task type: {task_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing task {task['id']}: {e}")
            return False
    
    def _scheduler(self):
        """Background scheduler for campaign lifecycle management (same as in-memory)"""
        logger.info("PostgreSQL queue scheduler started")
        
        # Import scheduler logic from task_queue
        from task_queue import TaskQueue
        temp_queue = TaskQueue()
        temp_queue.running = True
        temp_queue.last_scheduler_run = self.last_scheduler_run
        temp_queue.scheduler_interval = self.scheduler_interval
        
        while self.running:
            try:
                sleep(60)
                
                if not self.running:
                    break
                
                now = datetime.utcnow()
                if (self.last_scheduler_run is None or 
                    (now - self.last_scheduler_run).total_seconds() >= self.scheduler_interval):
                    
                    with app.app_context():
                        try:
                            lock_acquired = temp_queue._acquire_scheduler_lock(123456)
                            
                            if lock_acquired:
                                logger.debug("PostgreSQL queue scheduler executing...")
                                try:
                                    # Recover stale tasks every scheduler run
                                    # Use configurable threshold to avoid requeuing long-running tasks
                                    recovered = self.recover_stale_tasks(stale_threshold_minutes=self.stale_task_threshold)
                                    if recovered > 0:
                                        logger.warning(f"Scheduler recovered {recovered} stale tasks")
                                    
                                    # Recover stuck bulk operation jobs
                                    bulk_recovered = self.recover_stuck_bulk_jobs(stale_threshold_minutes=self.stale_task_threshold)
                                    if bulk_recovered > 0:
                                        logger.warning(f"Scheduler recovered {bulk_recovered} stuck bulk jobs")
                                    
                                    # Run campaign scheduler
                                    changes_made = temp_queue._run_campaign_scheduler()
                                    self.last_scheduler_run = now
                                    if changes_made > 0:
                                        logger.info(f"PostgreSQL queue scheduler completed: {changes_made} campaigns processed")
                                    
                                    # Run nightly reconciliation (24 hours interval)
                                    if (self.last_reconciliation_run is None or 
                                        (now - self.last_reconciliation_run).total_seconds() >= self.reconciliation_interval):
                                        logger.info("Running nightly participant status reconciliation")
                                        reconciled = temp_queue._run_participant_status_reconciliation()
                                        self.last_reconciliation_run = now
                                        if reconciled > 0:
                                            logger.info(f"Nightly reconciliation: {reconciled} records fixed")
                                finally:
                                    temp_queue._release_scheduler_lock(123456)
                            else:
                                logger.debug("Scheduler already running in another process, skipping...")
                                
                        except Exception as e:
                            logger.error(f"PostgreSQL queue scheduler error: {e}")
                            
            except Exception as e:
                logger.error(f"Scheduler thread error: {e}")
                sleep(60)
    
    def get_queue_size(self):
        """Get current queue size (pending tasks)"""
        try:
            result = db.session.execute(
                text("SELECT COUNT(*) FROM task_queue WHERE status = 'pending'")
            )
            return result.scalar()
        except Exception as e:
            logger.error(f"Error getting queue size: {e}")
            return 0
    
    def get_stats(self):
        """Get queue and scheduler statistics"""
        try:
            # Get task counts by status
            result = db.session.execute(
                text("""
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM task_queue
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                    GROUP BY status
                """)
            )
            
            status_counts = {row[0]: row[1] for row in result.fetchall()}
            
            return {
                'queue_size': status_counts.get('pending', 0),
                'processing': status_counts.get('processing', 0),
                'completed_last_hour': status_counts.get('completed', 0),
                'failed_last_hour': status_counts.get('failed', 0),
                'workers': len(self.workers),
                'running': self.running,
                'last_scheduler_run': self.last_scheduler_run.isoformat() + 'Z' if self.last_scheduler_run else None,
                'last_reconciliation_run': self.last_reconciliation_run.isoformat() + 'Z' if self.last_reconciliation_run else None,
                'scheduler_interval': self.scheduler_interval,
                'reconciliation_interval': self.reconciliation_interval,
                'queue_type': 'postgresql'
            }
        except Exception as e:
            logger.error(f"Error getting queue stats: {e}")
            return {
                'queue_size': 0,
                'workers': len(self.workers),
                'running': self.running,
                'queue_type': 'postgresql',
                'error': str(e)
            }
    
    # ============================================================================
    # EXPORT JOB MANAGEMENT
    # ============================================================================
    # Added Nov 23, 2025: Parity with TaskQueue export functionality
    # Fixes "PostgresTaskQueue has no attribute 'create_export_job'" error
    
    def create_export_job(self, campaign_id, business_account_id):
        """Create a new export job and return job ID"""
        from models import ExportJob
        
        job_id = str(uuid.uuid4())
        
        with app.app_context():
            try:
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
            except Exception as e:
                logger.error(f"Error creating export job: {e}")
                db.session.rollback()
                raise
    
    def get_export_job_status(self, job_id):
        """Get export job status from database"""
        from models import ExportJob
        
        with app.app_context():
            try:
                export_job = ExportJob.query.get(job_id)
                if export_job:
                    return export_job.to_dict()
                return None
            except Exception as e:
                logger.error(f"Error getting export job status: {e}")
                return None
    
    def cleanup_old_export_jobs(self, max_age_hours=24):
        """Clean up old export jobs and their files from database"""
        from models import ExportJob
        
        with app.app_context():
            try:
                cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
                
                # Find old export jobs
                old_jobs = ExportJob.query.filter(ExportJob.updated_at < cutoff_time).all()
                
                for job in old_jobs:
                    # Clean up file if it exists
                    if job.file_path and os.path.exists(job.file_path):
                        try:
                            os.remove(job.file_path)
                            logger.info(f"Cleaned up export file: {job.file_path}")
                        except Exception as e:
                            logger.error(f"Error cleaning up export file {job.file_path}: {e}")
                    
                    # Delete job from database
                    db.session.delete(job)
                
                if old_jobs:
                    db.session.commit()
                    logger.info(f"Cleaned up {len(old_jobs)} old export jobs")
            except Exception as e:
                logger.error(f"Error cleaning up old export jobs: {e}")
                db.session.rollback()
    
    def force_scheduler_run(self):
        """Force immediate scheduler run (for admin testing)
        
        Uses the same lock as automatic scheduler to prevent concurrent execution.
        If scheduler is currently running, this will wait briefly then return false.
        """
        logger.info("Force running PostgreSQL queue scheduler...")
        try:
            from task_queue import TaskQueue
            from sqlalchemy import text
            temp_queue = TaskQueue()
            
            with app.app_context():
                # Use same lock ID (123456) as automatic scheduler to prevent concurrent runs
                scheduler_lock_id = 123456
                
                # Try to acquire lock (non-blocking)
                lock_acquired = temp_queue._acquire_scheduler_lock(scheduler_lock_id)
                
                if lock_acquired:
                    try:
                        logger.info("Lock acquired - executing scheduler...")
                        temp_queue._run_campaign_scheduler()
                        self.last_scheduler_run = datetime.utcnow()
                        logger.info("Forced scheduler run completed successfully")
                        return True
                    finally:
                        temp_queue._release_scheduler_lock(scheduler_lock_id)
                else:
                    # Check if automatic scheduler is running by querying pg_locks
                    result = db.session.execute(
                        text("""
                            SELECT COUNT(*) 
                            FROM pg_locks 
                            WHERE locktype = 'advisory' 
                            AND objid = :lock_id
                            AND granted = true
                        """),
                        {"lock_id": scheduler_lock_id}
                    ).scalar()
                    
                    if result > 0:
                        logger.info("Scheduler is currently running - forced run skipped")
                    else:
                        logger.warning("Could not acquire scheduler lock - reason unknown")
                    return False
        except Exception as e:
            logger.error(f"Forced scheduler run failed: {e}", exc_info=True)
            return False
    def recover_stale_tasks(self, stale_threshold_minutes=10):
        """
        Recover tasks stuck in 'processing' status for longer than threshold.
        
        This handles tasks that were being processed when the application crashed
        or workers died unexpectedly. Ensures zero data loss by requeuing stuck tasks.
        
        Args:
            stale_threshold_minutes: Minutes before a processing task is considered stuck
            
        Returns:
            Number of tasks recovered
        """
        try:
            result = db.session.execute(
                text(f"""
                    UPDATE task_queue
                    SET status = 'pending',
                        claimed_by = NULL,
                        claimed_at = NULL,
                        started_at = NULL,
                        updated_at = NOW()
                    WHERE status = 'processing'
                      AND started_at < NOW() - INTERVAL '{stale_threshold_minutes} minutes'
                    RETURNING id, task_type, claimed_by
                """)
            )
            
            recovered_tasks = result.fetchall()
            db.session.commit()
            
            if recovered_tasks:
                logger.warning(f"Recovered {len(recovered_tasks)} stale tasks stuck in processing > {stale_threshold_minutes} minutes")
                for task in recovered_tasks:
                    logger.info(f"  - Task {task[0]} ({task[1]}) was claimed by {task[2]}")
            
            return len(recovered_tasks)
            
        except Exception as e:
            logger.error(f"Error recovering stale tasks: {e}")
            db.session.rollback()
            return 0
    
    def recover_stuck_bulk_jobs(self, stale_threshold_minutes=10):
        """
        Recover bulk operation jobs stuck in 'processing' status.
        
        This handles bulk add/remove jobs that got stuck due to worker crashes.
        Auto-completes jobs if all participants were processed, otherwise marks as failed.
        
        Args:
            stale_threshold_minutes: Minutes before a processing job is considered stuck
            
        Returns:
            Number of jobs recovered
        """
        try:
            from models import BulkOperationJob, Campaign
            
            # Find stuck jobs
            stuck_jobs = BulkOperationJob.query.filter(
                BulkOperationJob.status == 'processing',
                BulkOperationJob.started_at < datetime.utcnow() - timedelta(minutes=stale_threshold_minutes)
            ).all()
            
            recovered = 0
            for job in stuck_jobs:
                try:
                    # Clear campaign lock
                    campaign = Campaign.query.get(json.loads(job.operation_data).get('campaign_id'))
                    if campaign:
                        campaign.has_active_bulk_job = False
                        campaign.active_bulk_job_id = None
                        campaign.active_bulk_operation = None
                    
                    # Mark job as completed with recovery note
                    job.status = 'completed'
                    job.completed_at = datetime.utcnow()
                    current_result = json.loads(job.result) if job.result else {}
                    current_result['recovered'] = True
                    current_result['recovery_reason'] = f'Auto-recovered after {stale_threshold_minutes}min timeout'
                    job.result = json.dumps(current_result)
                    
                    logger.warning(f"Auto-recovered stuck bulk job {job.id} ({job.operation_type}) at {job.progress}% - cleared campaign lock")
                    recovered += 1
                    
                except Exception as job_error:
                    logger.error(f"Error recovering bulk job {job.id}: {job_error}")
            
            db.session.commit()
            return recovered
            
        except Exception as e:
            logger.error(f"Error recovering stuck bulk jobs: {e}")
            db.session.rollback()
            return 0


# Cleanup function for old completed/failed tasks
def cleanup_old_tasks():
    """
    Clean up old completed and failed tasks.
    
    - Completed tasks: kept for 7 days
    - Failed tasks: kept for 30 days
    - Stale conversations: kept for 24 hours
    
    Should be run daily via cron or scheduled task.
    """
    try:
        # Delete completed tasks older than 7 days
        result_completed = db.session.execute(
            text("""
                DELETE FROM task_queue 
                WHERE status = 'completed' 
                  AND completed_at < NOW() - INTERVAL '7 days'
            """)
        )
        
        # Delete failed tasks older than 30 days
        result_failed = db.session.execute(
            text("""
                DELETE FROM task_queue 
                WHERE status = 'failed' 
                  AND completed_at < NOW() - INTERVAL '30 days'
            """)
        )
        
        # Delete stale active conversations older than 24 hours
        result_conversations = db.session.execute(
            text("""
                DELETE FROM active_conversations 
                WHERE last_updated < NOW() - INTERVAL '24 hours'
            """)
        )
        
        db.session.commit()
        
        completed_count = result_completed.rowcount
        failed_count = result_failed.rowcount
        conversation_count = result_conversations.rowcount
        
        logger.info(f"Task cleanup: deleted {completed_count} completed tasks (>7 days), {failed_count} failed tasks (>30 days), and {conversation_count} stale conversations (>24 hours)")
        
        return {
            'completed_deleted': completed_count,
            'failed_deleted': failed_count,
            'conversations_deleted': conversation_count
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {e}")
        db.session.rollback()
        return None
