#!/usr/bin/env python3
"""
Simple test for LicenseService core functionality
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_license_service_simple():
    """Simple test of LicenseService functionality"""
    
    try:
        from app import app
        from license_service import LicenseService
        
        with app.app_context():
            print("Testing LicenseService with Rivvalue Inc (ID: 1)")
            print("-" * 50)
            
            business_account_id = 1
            
            # Test 1: Get current license
            print("1. Get current license:")
            current_license = LicenseService.get_current_license(business_account_id)
            if current_license:
                print(f"   ✅ Found: {current_license.license_type} license")
                print(f"   Status: {current_license.status}")
                print(f"   Expires: {current_license.expires_at}")
            else:
                print("   ❌ No current license found")
            
            # Test 2: Get license period
            print("\n2. Get license period:")
            try:
                period_start, period_end = LicenseService.get_license_period(business_account_id)
                if period_start and period_end:
                    print(f"   ✅ Period: {period_start} to {period_end}")
                else:
                    print("   ❌ No license period found")
            except Exception as e:
                print(f"   ❌ Error getting license period: {e}")
            
            # Test 3: Can activate campaign
            print("\n3. Can activate campaign:")
            try:
                can_activate = LicenseService.can_activate_campaign(business_account_id)
                print(f"   ✅ Can activate: {can_activate}")
            except Exception as e:
                print(f"   ❌ Error checking campaign activation: {e}")
            
            # Test 4: License info
            print("\n4. Get license info:")
            try:
                license_info = LicenseService.get_license_info(business_account_id)
                print(f"   ✅ License type: {license_info.get('license_type', 'Unknown')}")
                print(f"   Status: {license_info.get('license_status', 'Unknown')}")
                print(f"   Campaigns: {license_info.get('campaigns_used', 0)}/{license_info.get('campaigns_limit', 4)}")
            except Exception as e:
                print(f"   ❌ Error getting license info: {e}")
            
            print("\n" + "=" * 50)
            print("Simple license test completed")
            
    except ImportError as e:
        print(f"Import error: {e}")
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == "__main__":
    test_license_service_simple()