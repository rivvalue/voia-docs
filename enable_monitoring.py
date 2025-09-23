#!/usr/bin/env python3
"""
VOÏA Performance Monitoring Enabler
Programmatically enable monitoring for testing optimizations
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def enable_monitoring():
    """Enable performance monitoring programmatically"""
    try:
        from performance_monitor import performance_monitor
        from optimization_status import optimization_status
        
        print("🔥 Enabling performance monitoring...")
        performance_monitor.enable_monitoring(True)
        
        print("📊 Checking optimization status...")
        status = optimization_status.get_comprehensive_status()
        
        print("\n=== OPTIMIZATION STATUS ===")
        print(f"Stage 1 Status: {status['optimization_summary']['stage_1_status']}")
        print(f"Stage 2 Status: {status['optimization_summary']['stage_2_status']}")
        print(f"Overall Readiness: {status['optimization_summary']['overall_readiness']}")
        
        print(f"\n=== GATE VALIDATION ===")
        stage_1 = status['gate_validation']['stage_1']
        print(f"Stage 1 Gates: {stage_1['gates_passed']}/{stage_1['total_gates']} passed")
        print(f"Stage 1 Success: {stage_1['overall_success']}")
        
        if stage_1['status'] == 'monitoring_required':
            print("⚠️ Monitoring was required but now enabled programmatically")
        
        print(f"\n=== RECOMMENDATIONS ===")
        for rec in status['recommendations']:
            print(f"• {rec}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error enabling monitoring: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = enable_monitoring()
    sys.exit(0 if success else 1)