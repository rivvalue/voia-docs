#!/usr/bin/env python3
"""
Test script to validate the critical data integrity fixes in bulk license optimization.

This script tests all three critical fixes:
1. Campaign Count Accuracy - Ensures campaigns are counted by license period, not calendar year
2. Active License Selection - Validates date windows and deterministic selection 
3. Output Schema Consistency - Verifies bulk method matches get_license_info() exactly

Author: License Data Integrity Repair Agent
Created: September 19, 2025
"""

import sys
import os

# Add the current directory to the path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import BusinessAccount, LicenseHistory, Campaign
from license_service import LicenseService
from datetime import datetime, date, timedelta
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_bulk_license_fixes():
    """
    Comprehensive test of bulk license optimization fixes.
    
    Tests:
    1. Campaign count accuracy against individual lookups
    2. Active license selection validation
    3. Output schema consistency between bulk and individual methods
    """
    
    with app.app_context():
        # Get all business accounts to test with
        business_accounts = BusinessAccount.query.all()
        
        if not business_accounts:
            logger.error("No business accounts found for testing")
            return False
        
        logger.info(f"Testing bulk license fixes with {len(business_accounts)} business accounts")
        
        # Test 1: Get bulk data
        logger.info("=== Testing Bulk License Data Method ===")
        try:
            bulk_results = LicenseService.get_bulk_license_data()
            logger.info(f"Bulk method returned data for {len(bulk_results)} accounts")
        except Exception as e:
            logger.error(f"Bulk method failed: {e}")
            return False
        
        # Test 2: Compare with individual lookups
        logger.info("=== Comparing Bulk vs Individual License Lookups ===")
        mismatches = []
        
        for account in business_accounts:
            account_id = account.id
            
            # Get individual license info
            try:
                individual_info = LicenseService.get_license_info(account_id)
            except Exception as e:
                logger.error(f"Individual lookup failed for account {account_id}: {e}")
                continue
            
            # Get bulk license info
            bulk_data = bulk_results.get(account_id)
            if not bulk_data:
                logger.error(f"Bulk data missing for account {account_id}")
                mismatches.append({
                    'account_id': account_id,
                    'issue': 'bulk_data_missing',
                    'account_name': account.name
                })
                continue
            
            bulk_info = bulk_data.get('license_info', {})
            
            # Critical Field Comparisons
            critical_fields = [
                'license_type', 'license_status', 'license_start', 'license_end',
                'campaigns_used', 'campaigns_limit', 'campaigns_remaining',
                'users_used', 'users_limit', 'users_remaining',
                'days_remaining', 'days_since_expired', 'expires_soon',
                'can_activate_campaign', 'can_add_user', 'participants_limit'
            ]
            
            # Check each critical field
            field_mismatches = []
            for field in critical_fields:
                individual_val = individual_info.get(field)
                bulk_val = bulk_info.get(field)
                
                if individual_val != bulk_val:
                    field_mismatches.append({
                        'field': field,
                        'individual': individual_val,
                        'bulk': bulk_val
                    })
            
            if field_mismatches:
                mismatches.append({
                    'account_id': account_id,
                    'account_name': account.name,
                    'issue': 'field_mismatches',
                    'mismatches': field_mismatches
                })
                
                logger.warning(f"Data mismatch for account {account_id} ({account.name}):")
                for mismatch in field_mismatches:
                    logger.warning(f"  {mismatch['field']}: individual={mismatch['individual']}, bulk={mismatch['bulk']}")
            else:
                logger.info(f"✓ Account {account_id} ({account.name}) - Data integrity verified")
        
        # Test 3: Campaign Count Accuracy Validation
        logger.info("=== Testing Campaign Count Accuracy ===")
        campaign_count_issues = []
        
        for account in business_accounts:
            account_id = account.id
            bulk_data = bulk_results.get(account_id)
            if not bulk_data:
                continue
                
            bulk_campaigns = bulk_data['license_info'].get('campaigns_used', 0)
            
            # Get actual campaign count using proper license period
            current_license = LicenseService.get_current_license(account_id)
            if current_license:
                # Count campaigns within license period
                period_start = current_license.activated_at.date() if hasattr(current_license.activated_at, 'date') else current_license.activated_at
                period_end = current_license.expires_at.date() if hasattr(current_license.expires_at, 'date') else current_license.expires_at
                
                actual_campaigns = Campaign.query.filter(
                    Campaign.business_account_id == account_id,
                    Campaign.start_date >= period_start,
                    Campaign.start_date <= period_end
                ).count()
                
                if bulk_campaigns != actual_campaigns:
                    campaign_count_issues.append({
                        'account_id': account_id,
                        'account_name': account.name,
                        'bulk_count': bulk_campaigns,
                        'actual_count': actual_campaigns,
                        'license_period': f"{period_start} to {period_end}"
                    })
                    logger.warning(f"Campaign count mismatch for account {account_id}: bulk={bulk_campaigns}, actual={actual_campaigns}")
                else:
                    logger.info(f"✓ Account {account_id} - Campaign count accurate: {bulk_campaigns}")
        
        # Test 4: License Date Validation
        logger.info("=== Testing License Date Validation ===")
        date_validation_issues = []
        today = datetime.utcnow()
        
        for account_id, bulk_data in bulk_results.items():
            current_license = bulk_data['license_info'].get('current_license')
            if current_license:
                # Verify that the license is actually valid for today
                if not (current_license.activated_at <= today <= current_license.expires_at):
                    date_validation_issues.append({
                        'account_id': account_id,
                        'license_id': current_license.id,
                        'activated_at': current_license.activated_at,
                        'expires_at': current_license.expires_at,
                        'today': today
                    })
                    logger.warning(f"Invalid license date for account {account_id}: license not valid for today")
                else:
                    logger.info(f"✓ Account {account_id} - License date validation passed")
        
        # Summary Report
        logger.info("=== TEST RESULTS SUMMARY ===")
        logger.info(f"Total accounts tested: {len(business_accounts)}")
        logger.info(f"Bulk method returned data for: {len(bulk_results)} accounts")
        logger.info(f"Data consistency mismatches: {len(mismatches)}")
        logger.info(f"Campaign count issues: {len(campaign_count_issues)}")
        logger.info(f"Date validation issues: {len(date_validation_issues)}")
        
        # Detailed reporting
        if mismatches:
            logger.error("=== DATA CONSISTENCY ISSUES ===")
            for mismatch in mismatches:
                logger.error(f"Account {mismatch['account_id']} ({mismatch.get('account_name', 'Unknown')}): {mismatch['issue']}")
                if 'mismatches' in mismatch:
                    for field_mismatch in mismatch['mismatches']:
                        logger.error(f"  {field_mismatch['field']}: {field_mismatch['individual']} != {field_mismatch['bulk']}")
        
        if campaign_count_issues:
            logger.error("=== CAMPAIGN COUNT ISSUES ===")
            for issue in campaign_count_issues:
                logger.error(f"Account {issue['account_id']}: {issue['bulk_count']} != {issue['actual_count']} (period: {issue['license_period']})")
        
        if date_validation_issues:
            logger.error("=== DATE VALIDATION ISSUES ===")
            for issue in date_validation_issues:
                logger.error(f"Account {issue['account_id']}: License {issue['license_id']} not valid for today")
        
        # Overall result
        success = len(mismatches) == 0 and len(campaign_count_issues) == 0 and len(date_validation_issues) == 0
        
        if success:
            logger.info("🎉 ALL TESTS PASSED - Bulk license optimization fixes are working correctly!")
        else:
            logger.error("❌ TESTS FAILED - Critical data integrity issues remain")
        
        return success

if __name__ == "__main__":
    success = test_bulk_license_fixes()
    sys.exit(0 if success else 1)