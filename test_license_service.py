#!/usr/bin/env python3
"""
Test script for LicenseService functionality
Tests the new LicenseService class against real data (Rivvalue Inc trial account)
"""

import os
import sys
from datetime import date, datetime, timedelta

# Add the current directory to Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from license_service import LicenseService
from models import BusinessAccount, LicenseHistory, Campaign

def test_license_service():
    """Test LicenseService methods with real Rivvalue Inc data"""
    
    with app.app_context():
        print("=" * 60)
        print("LicenseService Test Suite")
        print("Testing with Rivvalue Inc trial account (ID: 1)")
        print("=" * 60)
        
        business_account_id = 1
        
        # Test 1: Get current license
        print("\n1. Testing get_current_license()")
        print("-" * 40)
        current_license = LicenseService.get_current_license(business_account_id)
        if current_license:
            print(f"✅ Found current license:")
            print(f"   - License ID: {current_license.id}")
            print(f"   - Type: {current_license.license_type}")
            print(f"   - Status: {current_license.status}")
            print(f"   - Activated: {current_license.activated_at}")
            print(f"   - Expires: {current_license.expires_at}")
            print(f"   - Days remaining: {current_license.days_remaining()}")
        else:
            print("❌ No current license found")
        
        # Test 2: Get license period
        print("\n2. Testing get_license_period()")
        print("-" * 40)
        period_start, period_end = LicenseService.get_license_period(business_account_id)
        if period_start and period_end:
            print(f"✅ License period found:")
            print(f"   - Start: {period_start}")
            print(f"   - End: {period_end}")
            print(f"   - Duration: {(period_end - period_start).days} days")
        else:
            print("❌ No license period found")
        
        # Test 3: Campaign activation check
        print("\n3. Testing can_activate_campaign()")
        print("-" * 40)
        can_activate = LicenseService.can_activate_campaign(business_account_id)
        campaigns_used = LicenseService.get_campaigns_used_in_current_period(business_account_id)
        print(f"✅ Campaign activation check:")
        print(f"   - Can activate: {can_activate}")
        print(f"   - Campaigns used in current period: {campaigns_used}")
        print(f"   - Campaign limit: {current_license.max_campaigns_per_year if current_license else 4}")
        
        # Test 4: User limits
        print("\n4. Testing can_add_user()")
        print("-" * 40)
        can_add_user = LicenseService.can_add_user(business_account_id)
        business_account = BusinessAccount.query.get(business_account_id)
        print(f"✅ User limit check:")
        print(f"   - Can add user: {can_add_user}")
        print(f"   - Current users: {business_account.current_users_count if business_account else 'N/A'}")
        print(f"   - User limit: {current_license.max_users if current_license else 5}")
        
        # Test 5: Comprehensive license info
        print("\n5. Testing get_license_info()")
        print("-" * 40)
        license_info = LicenseService.get_license_info(business_account_id)
        print(f"✅ License info retrieved:")
        print(f"   - License type: {license_info['license_type']}")
        print(f"   - Status: {license_info['license_status']}")
        print(f"   - Days remaining: {license_info['days_remaining']}")
        print(f"   - Expires soon: {license_info['expires_soon']}")
        print(f"   - Campaigns: {license_info['campaigns_used']}/{license_info['campaigns_limit']}")
        print(f"   - Users: {license_info['users_used']}/{license_info['users_limit']}")
        print(f"   - Can activate campaign: {license_info['can_activate_campaign']}")
        print(f"   - Can add user: {license_info['can_add_user']}")
        
        # Test 6: License history
        print("\n6. Testing get_license_history()")
        print("-" * 40)
        license_history = LicenseService.get_license_history(business_account_id)
        print(f"✅ License history retrieved:")
        print(f"   - Total license periods: {len(license_history)}")
        for i, license_record in enumerate(license_history, 1):
            print(f"   - Period {i}: {license_record.license_type} ({license_record.status}) "
                  f"{license_record.activated_at.date()} to {license_record.expires_at.date()}")
        
        # Test 7: License validation
        print("\n7. Testing validate_license_integrity()")
        print("-" * 40)
        validation = LicenseService.validate_license_integrity(business_account_id)
        print(f"✅ License validation result:")
        print(f"   - Is valid: {validation['is_valid']}")
        print(f"   - Issues found: {len(validation['issues'])}")
        for issue in validation['issues']:
            print(f"     - {issue}")
        print(f"   - Recommendations: {len(validation['recommendations'])}")
        for rec in validation['recommendations']:
            print(f"     - {rec}")
        
        # Test 8: Usage summary
        print("\n8. Testing get_license_usage_summary()")
        print("-" * 40)
        usage_summary = LicenseService.get_license_usage_summary(business_account_id)
        if 'error' not in usage_summary:
            print(f"✅ Usage summary generated:")
            print(f"   - Campaign utilization: {usage_summary['campaign_utilization_pct']}%")
            print(f"   - User utilization: {usage_summary['user_utilization_pct']}%")
            print(f"   - Total license periods: {usage_summary['total_license_periods']}")
        else:
            print(f"❌ Usage summary error: {usage_summary['error']}")
        
        # Test 9: Compare with legacy BusinessAccount methods
        print("\n9. Testing backward compatibility")
        print("-" * 40)
        if business_account:
            try:
                # Test legacy get_license_period method
                legacy_period = business_account.get_license_period()
                new_period = LicenseService.get_license_period(business_account_id)
                
                print(f"✅ License period compatibility:")
                print(f"   - Legacy method: {legacy_period}")
                print(f"   - New service: {new_period}")
                print(f"   - Match: {legacy_period == new_period}")
                
                # Test legacy can_activate_campaign method
                legacy_can_activate = business_account.can_activate_campaign()
                new_can_activate = LicenseService.can_activate_campaign(business_account_id)
                
                print(f"✅ Campaign activation compatibility:")
                print(f"   - Legacy method: {legacy_can_activate}")
                print(f"   - New service: {new_can_activate}")
                print(f"   - Match: {legacy_can_activate == new_can_activate}")
                
            except Exception as e:
                print(f"❌ Backward compatibility test error: {e}")
        
        print("\n" + "=" * 60)
        print("LicenseService Test Suite Complete")
        print("=" * 60)

if __name__ == "__main__":
    test_license_service()