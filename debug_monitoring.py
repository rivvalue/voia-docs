#!/usr/bin/env python3
"""
VOÏA Monitoring Debug Script
Detailed debugging of performance monitoring and gate validation
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_monitoring():
    """Debug monitoring system in detail"""
    try:
        from performance_monitor import performance_monitor, get_performance_metrics
        from optimization_status import optimization_status
        
        print("🔍 DETAILED MONITORING DEBUG")
        print("=" * 50)
        
        # Check monitoring status
        env_monitoring = os.environ.get('PERF_MONITORING', 'false').lower() == 'true'
        prog_monitoring = performance_monitor.is_monitoring_enabled()
        override_state = performance_monitor._monitoring_override
        
        print(f"Environment PERF_MONITORING: {env_monitoring}")
        print(f"Programmatic monitoring enabled: {prog_monitoring}")
        print(f"Override state: {override_state}")
        
        # Enable monitoring
        performance_monitor.enable_monitoring(True)
        print(f"After enabling - is_monitoring_enabled(): {performance_monitor.is_monitoring_enabled()}")
        
        # Get raw performance metrics
        raw_metrics = get_performance_metrics()
        print(f"\nRaw performance metrics:")
        print(f"  Type: {type(raw_metrics)}")
        print(f"  Content: {raw_metrics}")
        
        # Check collected data
        with performance_monitor.lock:
            response_times = list(performance_monitor.response_times)
            error_count = list(performance_monitor.error_count)
            request_count = performance_monitor.request_count
            
        print(f"\nPerformance Monitor Internal State:")
        print(f"  Request count: {request_count}")
        print(f"  Response times collected: {len(response_times)}")
        print(f"  Recent response times: {response_times[-10:] if response_times else 'None'}")
        print(f"  Error count: {len(error_count)}")
        
        # Test gate validation directly
        stage_1_gates = optimization_status.validate_stage_1_gates()
        print(f"\nStage 1 Gate Validation:")
        print(f"  Status: {stage_1_gates['status']}")
        print(f"  Message: {stage_1_gates.get('message', 'No message')}")
        print(f"  Gates passed: {stage_1_gates['gates_passed']}/{stage_1_gates['total_gates']}")
        print(f"  Overall success: {stage_1_gates['overall_success']}")
        
        if 'gates' in stage_1_gates:
            print(f"  Individual gates:")
            for gate_name, gate_info in stage_1_gates['gates'].items():
                print(f"    {gate_name}: {gate_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in debug: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = debug_monitoring()
    sys.exit(0 if success else 1)