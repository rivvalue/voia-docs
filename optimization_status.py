"""
VOÏA Optimization Status and Gate Validation System
Comprehensive monitoring of Stage 1 and Stage 2 optimizations
"""

import os
import time
import logging
from typing import Dict, Any, List
from flask import current_app
from performance_monitor import get_performance_metrics
from query_optimization import get_query_optimization_status
from database_config import db_config

logger = logging.getLogger(__name__)

class OptimizationStatusManager:
    """Centralized optimization status and gate validation"""
    
    def __init__(self):
        self.stage_1_features = {
            'performance_monitoring': 'PERF_MONITORING',
            'worker_scaling': 'ENABLE_WORKER_SCALING', 
            'compression': 'ENABLE_COMPRESSION',
            'async_workers': 'USE_ASYNC_WORKERS'
        }
        
        self.stage_2_features = {
            'database_optimization': 'OPTIMIZE_DB_POOL',
            'query_optimization': 'USE_OPTIMIZED_QUERIES',
            'eager_loading': 'ENABLE_EAGER_LOADING'
        }
    
    def get_feature_flag_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all feature flags"""
        stage_1 = {}
        for feature, env_var in self.stage_1_features.items():
            stage_1[feature] = {
                'enabled': os.environ.get(env_var, 'false').lower() == 'true',
                'env_var': env_var,
                'current_value': os.environ.get(env_var, 'false')
            }
        
        stage_2 = {}
        for feature, env_var in self.stage_2_features.items():
            stage_2[feature] = {
                'enabled': os.environ.get(env_var, 'false').lower() == 'true',
                'env_var': env_var,
                'current_value': os.environ.get(env_var, 'false')
            }
        
        return {
            'stage_1': stage_1,
            'stage_2': stage_2
        }
    
    def get_database_status(self) -> Dict[str, Any]:
        """Get database optimization status"""
        engine_options = db_config.get_engine_options()
        
        return {
            'environment': db_config.current_environment,
            'optimization_enabled': os.environ.get('OPTIMIZE_DB_POOL', 'false').lower() == 'true',
            'pool_size': engine_options.get('pool_size', 0),
            'max_overflow': engine_options.get('max_overflow', 0),
            'pool_timeout': engine_options.get('pool_timeout', 0),
            'connection_optimizations': 'echo' in engine_options and not engine_options['echo']
        }
    
    def get_worker_status(self) -> Dict[str, Any]:
        """Get worker configuration status"""
        return {
            'current_workers': 1,  # Currently still single worker from logs
            'target_workers': os.environ.get('GUNICORN_WORKERS', '1'),
            'worker_class': 'sync',  # Currently sync from logs
            'target_worker_class': 'gevent' if os.environ.get('USE_ASYNC_WORKERS', 'false').lower() == 'true' else 'sync',
            'scaling_enabled': os.environ.get('ENABLE_WORKER_SCALING', 'false').lower() == 'true'
        }
    
    def validate_stage_1_gates(self) -> Dict[str, Any]:
        """Validate Stage 1 success gates"""
        perf_metrics = get_performance_metrics()
        
        if perf_metrics.get('status') == 'no_data':
            return {
                'status': 'insufficient_data',
                'message': 'Need more requests to validate gates',
                'gates_passed': 0,
                'total_gates': 3
            }
        
        # Stage 1 Gate Thresholds
        response_time_gate = perf_metrics.get('avg_response_time_ms', 0) < 1000  # < 1 second
        error_rate_gate = perf_metrics.get('error_rate_percent', 0) < 5.0  # < 5% errors
        monitoring_gate = perf_metrics.get('monitoring') != 'disabled'  # Monitoring working
        
        gates_passed = sum([response_time_gate, error_rate_gate, monitoring_gate])
        
        return {
            'status': 'gates_evaluated',
            'gates': {
                'response_time_gate': {
                    'passed': response_time_gate,
                    'current_value': perf_metrics.get('avg_response_time_ms', 0),
                    'threshold': 1000,
                    'unit': 'ms'
                },
                'error_rate_gate': {
                    'passed': error_rate_gate,
                    'current_value': perf_metrics.get('error_rate_percent', 0),
                    'threshold': 5.0,
                    'unit': '%'
                },
                'monitoring_gate': {
                    'passed': monitoring_gate,
                    'current_value': 'enabled' if monitoring_gate else 'disabled',
                    'threshold': 'enabled',
                    'unit': 'status'
                }
            },
            'gates_passed': gates_passed,
            'total_gates': 3,
            'overall_success': gates_passed >= 2  # At least 2 of 3 gates must pass
        }
    
    def validate_stage_2_gates(self) -> Dict[str, Any]:
        """Validate Stage 2 success gates"""
        # For Stage 2, we check implementation status since performance gains
        # would be visible after enabling optimizations
        
        db_status = self.get_database_status()
        query_status = get_query_optimization_status()
        
        db_optimization_gate = db_status['optimization_enabled']
        query_optimization_gate = query_status.get('use_optimized_queries', False)
        pool_size_gate = db_status['pool_size'] >= 20  # Minimum pool size for concurrency
        
        gates_passed = sum([db_optimization_gate, query_optimization_gate, pool_size_gate])
        
        return {
            'status': 'implementation_validated',
            'gates': {
                'database_optimization_gate': {
                    'passed': db_optimization_gate,
                    'current_value': 'enabled' if db_optimization_gate else 'disabled',
                    'threshold': 'enabled',
                    'unit': 'status'
                },
                'query_optimization_gate': {
                    'passed': query_optimization_gate,
                    'current_value': 'enabled' if query_optimization_gate else 'disabled',
                    'threshold': 'enabled',
                    'unit': 'status'
                },
                'connection_pool_gate': {
                    'passed': pool_size_gate,
                    'current_value': db_status['pool_size'],
                    'threshold': 20,
                    'unit': 'connections'
                }
            },
            'gates_passed': gates_passed,
            'total_gates': 3,
            'overall_success': gates_passed >= 2
        }
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get complete optimization status report"""
        feature_flags = self.get_feature_flag_status()
        db_status = self.get_database_status()
        worker_status = self.get_worker_status()
        perf_metrics = get_performance_metrics()
        query_status = get_query_optimization_status()
        stage_1_gates = self.validate_stage_1_gates()
        stage_2_gates = self.validate_stage_2_gates()
        
        # Calculate overall readiness
        stage_1_ready = stage_1_gates['overall_success']
        stage_2_ready = stage_2_gates['overall_success']
        
        return {
            'timestamp': time.time(),
            'optimization_summary': {
                'stage_1_status': 'ready' if stage_1_ready else 'in_progress',
                'stage_2_status': 'ready' if stage_2_ready else 'in_progress',
                'overall_readiness': 'production_ready' if (stage_1_ready and stage_2_ready) else 'development'
            },
            'feature_flags': feature_flags,
            'infrastructure': {
                'database': db_status,
                'workers': worker_status,
                'performance_monitoring': perf_metrics
            },
            'gate_validation': {
                'stage_1': stage_1_gates,
                'stage_2': stage_2_gates
            },
            'query_optimization': query_status,
            'recommendations': self._generate_recommendations(stage_1_gates, stage_2_gates, worker_status)
        }
    
    def _generate_recommendations(self, stage_1_gates: Dict, stage_2_gates: Dict, worker_status: Dict) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Stage 1 recommendations
        if not stage_1_gates['overall_success']:
            recommendations.append("Enable Stage 1 optimizations: Set PERF_MONITORING=true")
            recommendations.append("Enable worker scaling: Set ENABLE_WORKER_SCALING=true and GUNICORN_WORKERS=4")
        
        # Stage 2 recommendations  
        if not stage_2_gates['overall_success']:
            recommendations.append("Enable Stage 2 database optimizations: Set OPTIMIZE_DB_POOL=true")
            recommendations.append("Enable query optimizations: Set USE_OPTIMIZED_QUERIES=true")
        
        # Worker recommendations
        if worker_status['current_workers'] == 1 and worker_status['scaling_enabled']:
            recommendations.append("Restart server with multiple workers to see scaling benefits")
        
        # Performance recommendations
        if not recommendations:
            recommendations.append("All optimizations implemented! Monitor performance and proceed to Stage 3 when ready")
        
        return recommendations

# Global optimization status manager
optimization_status = OptimizationStatusManager()