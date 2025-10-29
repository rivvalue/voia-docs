#!/usr/bin/env python3
"""Test script to diagnose timeline API issue"""

import os
import sys
from datetime import datetime

# Add app context
sys.path.insert(0, '/home/runner/workspace')

from app import app, db
from models import BusinessAccount, LicenseHistory, Campaign
from license_service import LicenseService

def test_timeline_for_account(business_account_id):
    """Test timeline data generation for a specific account"""
    with app.app_context():
        print(f"\n{'='*60}")
        print(f"Testing Timeline for Business Account ID: {business_account_id}")
        print(f"{'='*60}\n")
        
        # Get business account
        account = BusinessAccount.query.get(business_account_id)
        if not account:
            print(f"❌ Business account {business_account_id} not found")
            return
        
        print(f"✓ Account found: {account.name}")
        print(f"  Account Type: {account.account_type}")
        print(f"  Status: {account.status}")
        
        # Check legacy fields
        print(f"\n--- Legacy Fields (BusinessAccount table) ---")
        print(f"  license_activated_at: {account.license_activated_at}")
        print(f"  license_expires_at: {account.license_expires_at}")
        print(f"  license_status: {account.license_status}")
        
        # Get current license from LicenseHistory
        print(f"\n--- Current License (LicenseHistory table) ---")
        current_license = LicenseService.get_current_license(business_account_id)
        if current_license:
            print(f"  ✓ Current license found:")
            print(f"    Type: {current_license.license_type}")
            print(f"    Status: {current_license.status}")
            print(f"    Activated: {current_license.activated_at}")
            print(f"    Expires: {current_license.expires_at}")
        else:
            print(f"  ❌ No current active license found")
        
        # Get license info from service
        print(f"\n--- License Info (from LicenseService) ---")
        license_info = LicenseService.get_license_info(business_account_id, bypass_admin_override=True)
        if license_info:
            print(f"  ✓ License info retrieved:")
            print(f"    Type: {license_info.get('license_type')}")
            print(f"    Status: {license_info.get('license_status')}")
            print(f"    Start: {license_info.get('license_start')}")
            print(f"    End: {license_info.get('license_end')}")
            print(f"    Start type: {type(license_info.get('license_start'))}")
            print(f"    End type: {type(license_info.get('license_end'))}")
        else:
            print(f"  ❌ No license info returned")
        
        # Test timeline calculation
        print(f"\n--- Timeline Calculation ---")
        license_start = license_info.get('license_start') if license_info else None
        license_end = license_info.get('license_end') if license_info else None
        
        if not license_start or not license_end:
            print(f"  ❌ Cannot calculate timeline: missing dates")
            print(f"     license_start is None: {license_start is None}")
            print(f"     license_end is None: {license_end is None}")
        else:
            print(f"  ✓ Dates available for timeline")
            try:
                # Try to access .year and .month
                months_diff = (license_end.year - license_start.year) * 12 + (license_end.month - license_start.month)
                print(f"    License duration: {months_diff} months")
                
                # Get campaigns
                campaigns = Campaign.query.filter_by(business_account_id=business_account_id).all()
                print(f"    Total campaigns: {len(campaigns)}")
                
                for campaign in campaigns:
                    print(f"      - {campaign.name}: {campaign.start_date} to {campaign.end_date}")
                    
            except AttributeError as e:
                print(f"  ❌ Error accessing date attributes: {e}")
                print(f"     license_start value: {license_start}")
                print(f"     license_end value: {license_end}")
        
        print(f"\n{'='*60}\n")

if __name__ == "__main__":
    # Test for account ID 1 (Archelo Group)
    test_timeline_for_account(1)
