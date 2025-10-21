"""
Queue configuration for VOÏA platform.

Supports both in-memory and PostgreSQL-backed task queues with feature flags
for gradual rollout and safe testing.

Environment Variables:
- USE_POSTGRES_QUEUE: Enable PostgreSQL queue (default: false)
- QUEUE_POLL_INTERVAL: Polling interval in seconds (default: 2)
- QUEUE_WORKER_COUNT: Number of worker threads (default: 5)
"""

import os
import logging

logger = logging.getLogger(__name__)


class QueueConfig:
    """Queue configuration with feature flags"""
    
    def __init__(self):
        # Queue type selection
        self.use_postgres_queue = os.environ.get('USE_POSTGRES_QUEUE', 'false').lower() == 'true'
        
        # Worker configuration
        self.poll_interval = int(os.environ.get('QUEUE_POLL_INTERVAL', '2'))
        self.worker_count = int(os.environ.get('QUEUE_WORKER_COUNT', '5'))
        
        # Scheduler configuration
        self.scheduler_interval = int(os.environ.get('QUEUE_SCHEDULER_INTERVAL', '300'))  # 5 minutes
        
        # Stale task recovery threshold (in minutes)
        self.stale_task_threshold = int(os.environ.get('QUEUE_STALE_THRESHOLD_MINUTES', '30'))
        
        # Log configuration
        if self.use_postgres_queue:
            logger.info(f"✅ PostgreSQL Queue enabled - Workers: {self.worker_count}, Poll: {self.poll_interval}s")
        else:
            logger.info(f"📝 In-memory Queue (current) - Workers: 3 (fixed)")
    
    def get_queue_type(self):
        """Get configured queue type"""
        return 'postgresql' if self.use_postgres_queue else 'memory'
    
    def get_worker_count(self):
        """Get number of workers"""
        return self.worker_count if self.use_postgres_queue else 3  # In-memory uses 3
    
    def get_poll_interval(self):
        """Get polling interval (PostgreSQL only)"""
        return self.poll_interval
    
    def get_scheduler_interval(self):
        """Get scheduler run interval"""
        return self.scheduler_interval
    
    def get_stale_task_threshold(self):
        """Get stale task recovery threshold in minutes (default: 30)"""
        return self.stale_task_threshold
    
    def is_postgres_enabled(self):
        """Check if PostgreSQL queue is enabled"""
        return self.use_postgres_queue
    
    def get_config_summary(self):
        """Get configuration summary for logging/debugging"""
        return {
            'queue_type': self.get_queue_type(),
            'use_postgres_queue': self.use_postgres_queue,
            'worker_count': self.get_worker_count(),
            'poll_interval': self.poll_interval if self.use_postgres_queue else 'N/A (in-memory)',
            'scheduler_interval': self.scheduler_interval
        }


# Global queue configuration instance
queue_config = QueueConfig()
