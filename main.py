#!/usr/bin/env python3
"""
VOÏA Optimized Application Launcher
Proper wrapper that configures and launches Gunicorn with optimization settings
"""

import os
import sys
import subprocess
import logging
import signal
import time

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv('.env', verbose=False)
    logger_temp = logging.getLogger(__name__)
    logger_temp.info("📁 .env file loaded successfully")
except ImportError:
    pass  # python-dotenv not available, continue without it

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_rollback_recovery():
    """Check if we're recovering from a rollback and apply settings"""
    try:
        from rollback_manager import rollback_manager
        rollback_recovered = rollback_manager.check_rollback_on_startup()
        if rollback_recovered:
            logger.info("🔄 ROLLBACK RECOVERY: System recovered from previous rollback")
        return rollback_recovered
    except ImportError:
        logger.debug("Rollback manager not available")
        return False

def apply_optimization_settings():
    """Apply feature flag controlled optimization settings"""
    
    logger.info("🚀 VOÏA Performance Optimization: Configuring Gunicorn settings")
    
    # Check rollback first
    check_rollback_recovery()
    
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
    
    return workers, worker_class

def build_gunicorn_command(workers, worker_class):
    """Build the optimized Gunicorn command"""
    
    cmd = [
        'gunicorn',
        '--bind', '0.0.0.0:5000',
        '--workers', str(workers),
        '--worker-class', worker_class,
        '--reuse-port',
        '--reload',
        '--max-requests', '1000',
        '--max-requests-jitter', '100',
        '--preload',
        '--timeout', '30',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'main:app'  # Import from main.py
    ]
    
    return cmd

def supervisor_loop():
    """Supervisor loop that handles controlled restarts for rollbacks"""
    
    while True:
        try:
            # Apply optimization settings
            workers, worker_class = apply_optimization_settings()
            
            # Build Gunicorn command
            cmd = build_gunicorn_command(workers, worker_class)
            
            logger.info(f"🚀 Starting Gunicorn: {' '.join(cmd)}")
            
            # Start Gunicorn process
            process = subprocess.Popen(cmd)
            
            # Wait for process to complete
            returncode = process.wait()
            
            logger.info(f"Gunicorn exited with code: {returncode}")
            
            # Handle rollback restart
            if returncode == 42:
                logger.info("🔄 ROLLBACK RESTART: Restarting with safe configuration")
                time.sleep(2)  # Brief pause before restart
                continue
            else:
                # Normal exit or error
                logger.info("🛑 Supervisor loop exiting")
                break
                
        except KeyboardInterrupt:
            logger.info("🛑 Shutdown requested")
            try:
                process.terminate()
                process.wait()
            except NameError:
                pass  # Process wasn't started yet
            break
        except Exception as e:
            logger.error(f"Supervisor error: {e}")
            time.sleep(5)  # Wait before retry
            continue

# Check if we're being called as a launcher or as a module
if __name__ == '__main__':
    # Called as launcher - start supervisor loop with full optimizations
    logger.info("🚀 VOÏA Optimization System Starting (Supervisor Mode)")
    supervisor_loop()
else:
    # Called as module by gunicorn - apply limited optimizations and import app
    logger.info("⚡ VOÏA Limited Optimization Mode (Module Import)")
    
    # Load environment variables when imported as module
    try:
        from dotenv import load_dotenv
        load_dotenv('.env', verbose=False)
        logger.info("📁 .env file loaded in module mode")
    except ImportError:
        pass
    
    # Log current optimization status when loaded as module
    enable_scaling = os.environ.get('ENABLE_WORKER_SCALING', 'false').lower() == 'true'
    use_async = os.environ.get('USE_ASYNC_WORKERS', 'false').lower() == 'true'
    perf_monitoring = os.environ.get('PERF_MONITORING', 'false').lower() == 'true'
    
    logger.info(f"📊 Module mode optimizations: scaling={enable_scaling}, async={use_async}, monitoring={perf_monitoring}")
    
    if enable_scaling:
        logger.warning("⚠️ Worker scaling requires supervisor mode. Use 'python main.py' for full optimizations.")
    
    from app import app  # noqa: F401
