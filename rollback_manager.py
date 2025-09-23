#!/usr/bin/env python3
"""
VOÏA Effective Rollback Manager
Implements controlled restart mechanism for optimization rollbacks
"""

import os
import sys
import signal
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RollbackManager:
    """Manages effective rollbacks with controlled restart capability"""
    
    def __init__(self):
        self.rollback_file = '/tmp/voia_rollback_state.json'
        self.restart_signal_file = '/tmp/voia_restart_required.flag'
        
    def trigger_rollback(self, reason: str, failed_gates: List[str], metrics: Dict[str, Any]):
        """Trigger effective rollback with controlled restart"""
        
        logger.critical("🚨 EFFECTIVE ROLLBACK TRIGGERED")
        logger.critical(f"Reason: {reason}")
        logger.critical(f"Failed gates: {failed_gates}")
        
        # Step 1: Set safe rollback environment variables
        safe_env = self._get_safe_environment()
        self._apply_rollback_environment(safe_env)
        
        # Step 2: Create rollback state file for persistence
        rollback_state = {
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "failed_gates": failed_gates,
            "metrics": metrics,
            "rollback_env": safe_env,
            "restart_required": True
        }
        
        self._save_rollback_state(rollback_state)
        
        # Step 3: Signal for controlled restart
        self._request_controlled_restart()
        
        logger.critical("✅ Rollback state saved, restart requested")
        
    def _get_safe_environment(self) -> Dict[str, str]:
        """Get safe environment configuration for rollback"""
        return {
            # Stage 1: Disable scaling and async workers
            'ENABLE_WORKER_SCALING': 'false',
            'USE_ASYNC_WORKERS': 'false', 
            'GUNICORN_WORKERS': '1',
            
            # Stage 2: Disable database optimizations
            'OPTIMIZE_DB_POOL': 'false',
            'USE_OPTIMIZED_QUERIES': 'false',
            'ENABLE_EAGER_LOADING': 'false',
            
            # Disable performance features
            'ENABLE_COMPRESSION': 'false',
            'PERF_MONITORING': 'false',
            
            # Set safe defaults
            'AUTO_ROLLBACK': 'false',  # Prevent rollback loops
        }
    
    def _apply_rollback_environment(self, safe_env: Dict[str, str]):
        """Apply rollback environment variables"""
        for key, value in safe_env.items():
            old_value = os.environ.get(key, 'unset')
            os.environ[key] = value
            logger.critical(f"🔧 Rollback: {key}={old_value} → {value}")
    
    def _save_rollback_state(self, state: Dict[str, Any]):
        """Save rollback state to persistent file"""
        try:
            with open(self.rollback_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"💾 Rollback state saved to {self.rollback_file}")
        except Exception as e:
            logger.error(f"Failed to save rollback state: {e}")
    
    def _request_controlled_restart(self):
        """Request controlled restart via signal file"""
        try:
            # Create restart signal file
            with open(self.restart_signal_file, 'w') as f:
                f.write(json.dumps({
                    "restart_requested": True,
                    "timestamp": datetime.utcnow().isoformat(),
                    "pid": os.getpid()
                }))
            
            logger.critical(f"🔄 Restart signal created: {self.restart_signal_file}")
            
            # Give time for logging to flush
            time.sleep(1)
            
            # Trigger graceful restart by exiting with special code
            logger.critical("💀 Triggering controlled restart (exit code 42)")
            os._exit(42)  # Special exit code for restart
            
        except Exception as e:
            logger.error(f"Failed to request restart: {e}")
    
    def check_rollback_on_startup(self):
        """Check if rollback was applied and clean up state"""
        if os.path.exists(self.rollback_file):
            try:
                with open(self.rollback_file, 'r') as f:
                    rollback_state = json.load(f)
                
                logger.info("🔄 ROLLBACK RECOVERY: Previous rollback detected")
                logger.info(f"Rollback reason: {rollback_state.get('reason')}")
                logger.info(f"Rollback time: {rollback_state.get('timestamp')}")
                
                # Apply rollback environment on startup
                if rollback_state.get('rollback_env'):
                    self._apply_rollback_environment(rollback_state['rollback_env'])
                    logger.info("✅ Rollback environment applied on startup")
                
                # Clean up rollback state after successful recovery
                os.remove(self.rollback_file)
                logger.info("🧹 Rollback state cleaned up")
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to process rollback state: {e}")
        
        # Clean up restart signal if exists
        if os.path.exists(self.restart_signal_file):
            try:
                os.remove(self.restart_signal_file)
            except:
                pass
                
        return False

# Global rollback manager instance
rollback_manager = RollbackManager()

def trigger_effective_rollback(reason: str, failed_gates: List[str], metrics: Dict[str, Any]):
    """Global function to trigger effective rollback"""
    rollback_manager.trigger_rollback(reason, failed_gates, metrics)