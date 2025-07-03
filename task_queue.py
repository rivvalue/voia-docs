import json
import os
import logging
from datetime import datetime, timedelta
from threading import Thread
from queue import Queue, Empty
from time import sleep
from app import app, db
from models import SurveyResponse
from ai_analysis import analyze_survey_response

logger = logging.getLogger(__name__)

class TaskQueue:
    """Simple in-memory task queue for processing AI analysis tasks"""
    
    def __init__(self, max_workers=5):
        self.task_queue = Queue()
        self.max_workers = max_workers
        self.workers = []
        self.running = False
        
    def start(self):
        """Start the task queue workers"""
        if self.running:
            return
            
        self.running = True
        logger.info(f"Starting task queue with {self.max_workers} workers")
        
        for i in range(self.max_workers):
            worker = Thread(target=self._worker, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def stop(self):
        """Stop the task queue workers"""
        self.running = False
        logger.info("Stopping task queue")
    
    def add_task(self, task_type, response_id, priority=1):
        """Add a task to the queue"""
        task = {
            'type': task_type,
            'response_id': response_id,
            'priority': priority,
            'created_at': datetime.utcnow()
        }
        
        self.task_queue.put(task)
        logger.info(f"Added task {task_type} for response {response_id}")
    
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
            response_id = task['response_id']
            
            if task_type == 'ai_analysis':
                # Perform AI analysis
                success = analyze_survey_response(response_id)
                
                if success:
                    logger.info(f"Worker {worker_id} completed AI analysis for response {response_id}")
                else:
                    logger.error(f"Worker {worker_id} failed AI analysis for response {response_id}")
                    
                    # Mark as failed in database
                    response = SurveyResponse.query.get(response_id)
                    if response:
                        response.analyzed_at = datetime.utcnow()
                        response.sentiment_label = 'analysis_failed'
                        db.session.commit()
                        
        except Exception as e:
            logger.error(f"Error processing task {task}: {e}")
    
    def get_queue_size(self):
        """Get current queue size"""
        return self.task_queue.qsize()
    
    def get_stats(self):
        """Get queue statistics"""
        return {
            'queue_size': self.task_queue.qsize(),
            'workers': len(self.workers),
            'running': self.running
        }

# Global task queue instance
task_queue = TaskQueue(max_workers=3)  # Start with 3 workers for AI analysis

def start_task_queue():
    """Start the global task queue"""
    task_queue.start()

def add_analysis_task(response_id):
    """Add an AI analysis task to the queue"""
    task_queue.add_task('ai_analysis', response_id)

def get_queue_stats():
    """Get queue statistics"""
    return task_queue.get_stats()