"""
VOÏA Performance Monitoring System
Gate-controlled optimization with real-time monitoring and automatic rollback capabilities
"""

import os
import time
import logging
from functools import wraps
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque
import threading

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Real-time performance monitoring with gate controls"""
    
    def __init__(self):
        # Feature flags from environment
        self.enabled = os.environ.get('PERF_MONITORING', 'false').lower() == 'true'
        self.auto_rollback = os.environ.get('AUTO_ROLLBACK', 'false').lower() == 'true'
        
        # Performance thresholds (gates)
        self.response_time_threshold = float(os.environ.get('RESPONSE_TIME_THRESHOLD', '1000'))  # ms
        self.error_rate_threshold = float(os.environ.get('ERROR_RATE_THRESHOLD', '5.0'))  # percentage
        self.memory_threshold = float(os.environ.get('MEMORY_THRESHOLD', '50'))  # GB
        
        # Metrics storage (last 1000 requests)
        self.response_times = deque(maxlen=1000)
        self.error_count = deque(maxlen=1000)
        self.request_count = 0
        self.error_total = 0
        
        # Thread safety
        self.lock = threading.Lock()
        
        if self.enabled:
            logger.info("Performance monitoring enabled with thresholds: "
                       f"response_time={self.response_time_threshold}ms, "
                       f"error_rate={self.error_rate_threshold}%, "
                       f"auto_rollback={self.auto_rollback}")
    
    def track_request(self, func):
        """Decorator to track request performance"""
        if not self.enabled:
            return func
            
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            error_occurred = False
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error_occurred = True
                raise
            finally:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                
                with self.lock:
                    self.response_times.append(response_time)
                    self.error_count.append(1 if error_occurred else 0)
                    self.request_count += 1
                    if error_occurred:
                        self.error_total += 1
                
                # Log slow requests
                if response_time > 500:
                    logger.warning(f"Slow request: {func.__name__} took {response_time:.2f}ms")
                
                # Check gates if auto-rollback enabled
                if self.auto_rollback:
                    self._check_performance_gates()
        
        return wrapper
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self.enabled:
            return {"monitoring": "disabled"}
        
        with self.lock:
            if not self.response_times:
                return {"status": "no_data"}
            
            avg_response_time = sum(self.response_times) / len(self.response_times)
            p95_response_time = sorted(self.response_times)[int(len(self.response_times) * 0.95)]
            
            recent_errors = sum(list(self.error_count)[-100:])  # Last 100 requests
            recent_requests = min(100, len(self.error_count))
            error_rate = (recent_errors / recent_requests * 100) if recent_requests > 0 else 0
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "total_requests": self.request_count,
                "avg_response_time_ms": round(avg_response_time, 2),
                "p95_response_time_ms": round(p95_response_time, 2),
                "error_rate_percent": round(error_rate, 2),
                "recent_requests": recent_requests,
                "gates": {
                    "response_time_gate": avg_response_time < self.response_time_threshold,
                    "error_rate_gate": error_rate < self.error_rate_threshold,
                },
                "thresholds": {
                    "response_time_ms": self.response_time_threshold,
                    "error_rate_percent": self.error_rate_threshold,
                    "memory_gb": self.memory_threshold
                }
            }
    
    def _check_performance_gates(self):
        """Check if performance gates are met, trigger rollback if needed"""
        metrics = self.get_metrics()
        
        if metrics.get("status") == "no_data":
            return
        
        gates = metrics.get("gates", {})
        
        # Check if any gate failed
        failed_gates = [gate for gate, passed in gates.items() if not passed]
        
        if failed_gates:
            logger.critical(f"Performance gates failed: {failed_gates}")
            logger.critical(f"Current metrics: {metrics}")
            
            if self.auto_rollback:
                self._trigger_rollback(failed_gates, metrics)
    
    def _trigger_rollback(self, failed_gates: list, metrics: Dict[str, Any]):
        """Trigger automatic rollback when gates fail"""
        logger.critical("AUTOMATIC ROLLBACK TRIGGERED")
        logger.critical(f"Failed gates: {failed_gates}")
        logger.critical(f"Metrics: {metrics}")
        
        # Set environment variables to safe defaults
        rollback_env = {
            'GUNICORN_WORKERS': '1',
            'ENABLE_COMPRESSION': 'false',
            'CREATE_INDEXES': 'false',
            'OPTIMIZE_DB_POOL': 'false',
            'USE_OPTIMIZED_QUERIES': 'false'
        }
        
        for key, value in rollback_env.items():
            os.environ[key] = value
            logger.critical(f"Rollback: Set {key}={value}")
        
        # Log rollback event for manual intervention
        rollback_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "trigger": "automatic_gate_failure",
            "failed_gates": failed_gates,
            "metrics": metrics,
            "rollback_actions": rollback_env
        }
        
        logger.critical(f"ROLLBACK_EVENT: {rollback_event}")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def monitor_performance(func):
    """Decorator for monitoring function performance"""
    return performance_monitor.track_request(func)

def get_performance_metrics() -> Dict[str, Any]:
    """Get current performance metrics"""
    return performance_monitor.get_metrics()