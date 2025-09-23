#!/usr/bin/env python3
"""
VOÏA Main Application Entry Point
Applies optimization settings via environment variables before Gunicorn startup
"""

import os
import logging

# Configure logging for optimization feedback
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_optimization_settings():
    """Apply feature flag controlled optimization settings to Gunicorn via env vars"""
    
    logger.info("🚀 VOÏA Performance Optimization: Configuring Gunicorn settings")
    
    # Get feature flag settings
    enable_scaling = os.environ.get('ENABLE_WORKER_SCALING', 'false').lower() == 'true'
    use_async = os.environ.get('USE_ASYNC_WORKERS', 'false').lower() == 'true'
    worker_override = os.environ.get('GUNICORN_WORKERS')
    
    # Calculate optimal workers based on feature flags
    if worker_override:
        try:
            workers = int(worker_override)
            logger.info(f"✅ Using explicit worker count: {workers}")
        except ValueError:
            workers = 1
            logger.warning(f"⚠️ Invalid GUNICORN_WORKERS value, using default: {workers}")
    elif enable_scaling:
        try:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            workers = min(8, max(2, (2 * cpu_count) + 1))  # Cap at 8 for safety
            logger.info(f"⚡ Auto-scaling enabled: {cpu_count} CPUs detected, using {workers} workers")
        except:
            workers = 2
            logger.warning("⚠️ Failed to detect CPU count, using 2 workers")
    else:
        workers = 1
        logger.info("📊 Worker scaling disabled, using single worker")
    
    # Set worker class based on feature flags
    worker_class = 'gevent' if use_async else 'sync'
    if use_async:
        logger.info("🔄 Using gevent async workers for better I/O performance")
    else:
        logger.info("⚙️ Using sync workers")
    
    # Apply settings via environment variables that Gunicorn will read
    os.environ['WEB_CONCURRENCY'] = str(workers)  # Heroku/standard env var for worker count
    os.environ['GUNICORN_CMD_ARGS'] = f'--worker-class {worker_class} --max-requests 1000 --max-requests-jitter 100 --preload --timeout 30'
    
    # Log optimization summary
    settings = {
        'workers': workers,
        'worker_class': worker_class,
        'compression': os.environ.get('ENABLE_COMPRESSION', 'false'),
        'monitoring': os.environ.get('PERF_MONITORING', 'false'),
        'scaling': os.environ.get('ENABLE_WORKER_SCALING', 'false'),
        'async_workers': os.environ.get('USE_ASYNC_WORKERS', 'false')
    }
    
    logger.info(f"🎯 Optimization settings applied: {settings}")
    logger.info("✅ Gunicorn will use optimized configuration via environment variables")

# Apply optimization settings before importing the app
apply_optimization_settings()

# Check for rollback recovery
def check_rollback_recovery():
    """Check if we're recovering from a rollback"""
    try:
        from rollback_manager import rollback_manager
        rollback_recovered = rollback_manager.check_rollback_on_startup()
        if rollback_recovered:
            logger.info("🔄 ROLLBACK RECOVERY: System recovered from previous rollback")
        return rollback_recovered
    except ImportError:
        logger.debug("Rollback manager not available")
        return False

# Check rollback state
check_rollback_recovery()

# Import the Flask application
from app import app  # noqa: F401
