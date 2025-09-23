#!/usr/bin/env python3
"""
VOÏA Performance-Optimized Server Startup Script
Gate-controlled worker scaling and optimization features
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_optimal_workers():
    """Calculate optimal number of workers based on CPU and feature flags"""
    
    # Feature flag control
    worker_override = os.environ.get('GUNICORN_WORKERS')
    if worker_override:
        try:
            workers = int(worker_override)
            logger.info(f"Using explicit worker count from GUNICORN_WORKERS: {workers}")
            return workers
        except ValueError:
            logger.warning(f"Invalid GUNICORN_WORKERS value: {worker_override}, using default")
    
    # Stage 1 optimization: Controlled worker scaling
    enable_scaling = os.environ.get('ENABLE_WORKER_SCALING', 'false').lower() == 'true'
    
    if enable_scaling:
        # Calculate based on CPU cores (2 * cores + 1 is a common formula)
        try:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            workers = min(8, max(2, (2 * cpu_count) + 1))  # Cap at 8 for safety
            logger.info(f"Auto-scaling enabled: {cpu_count} CPUs detected, using {workers} workers")
            return workers
        except:
            logger.warning("Failed to detect CPU count, using 2 workers")
            return 2
    else:
        logger.info("Worker scaling disabled, using single worker")
        return 1

def get_worker_class():
    """Get the optimal worker class based on feature flags"""
    
    # Feature flag for async workers
    use_async = os.environ.get('USE_ASYNC_WORKERS', 'false').lower() == 'true'
    
    if use_async:
        logger.info("Using gevent async workers for better I/O performance")
        return 'gevent'
    else:
        logger.info("Using sync workers")
        return 'sync'

def get_gunicorn_options():
    """Build gunicorn command line options"""
    
    workers = get_optimal_workers()
    worker_class = get_worker_class()
    
    options = [
        'gunicorn',
        '--bind', '0.0.0.0:5000',
        '--workers', str(workers),
        '--worker-class', worker_class,
        '--reuse-port',
        '--access-logfile', '-',
        '--error-logfile', '-',
    ]
    
    # Stage 1 optimization: Enable reload for development
    if os.environ.get('GUNICORN_RELOAD', 'true').lower() == 'true':
        options.append('--reload')
    
    # Performance tuning options
    options.extend([
        '--max-requests', '1000',  # Restart workers after 1000 requests
        '--max-requests-jitter', '100',  # Add randomness to prevent thundering herd
        '--preload',  # Load application code before forking workers
        '--timeout', '30',  # 30 second timeout
    ])
    
    options.append('main:app')
    
    return options

def main():
    """Start the VOÏA server with optimized configuration"""
    
    logger.info("🚀 Starting VOÏA Performance-Optimized Server")
    
    # Log current optimization settings
    settings = {
        'workers': get_optimal_workers(),
        'worker_class': get_worker_class(),
        'compression': os.environ.get('ENABLE_COMPRESSION', 'false'),
        'monitoring': os.environ.get('PERF_MONITORING', 'false'),
        'scaling': os.environ.get('ENABLE_WORKER_SCALING', 'false'),
    }
    
    logger.info(f"Optimization settings: {settings}")
    
    # Build and execute gunicorn command
    cmd = get_gunicorn_options()
    logger.info(f"Executing: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except subprocess.CalledProcessError as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()