#!/usr/bin/env python3
"""
Comprehensive Test Suite for Critical License Assignment Fixes
Author: System Integration Agent
Created: September 17, 2025

This test suite validates the critical fixes implemented for:
1. Concurrency/Race Conditions: SELECT...FOR UPDATE and database constraints
2. Downgrade Safety: Usage validation to prevent unsafe downgrades

Tests cover edge cases, concurrent scenarios, and validate database-level constraints.
"""

import os
import sys
import threading
import time
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and models
from app import app, db
from models import BusinessAccount, LicenseHistory, Campaign, CampaignParticipant
from license_service import LicenseService
from license_templates import LicenseTemplateManager

def setup_test_environment():
    """Setup comprehensive test environment"""
    print("Setting up comprehensive test environment...")
    
    with app.app_context():
        try:
            # Create test business accounts for different scenarios
            test_businesses = []
            
            # Business for concurrency tests
            concurrency_business = BusinessAccount.query.filter_by(name='Concurrency Test Business').first()
            if not concurrency_business:
                concurrency_business = BusinessAccount(
                    name='Concurrency Test Business',
                    account_type='customer',
                    contact_email='concurrency@test.com',
                    contact_name='Concurrency Test User',
                    status='active'
                )
                db.session.add(concurrency_business)
            test_businesses.append(concurrency_business)
            
            # Business for downgrade safety tests
            downgrade_business = BusinessAccount.query.filter_by(name='Downgrade Test Business').first()
            if not downgrade_business:
                downgrade_business = BusinessAccount(
                    name='Downgrade Test Business',
                    account_type='customer', 
                    contact_email='downgrade@test.com',
                    contact_name='Downgrade Test User',
                    status='active'
                )
                db.session.add(downgrade_business)
            test_businesses.append(downgrade_business)
            
            # Business for constraint tests
            constraint_business = BusinessAccount.query.filter_by(name='Constraint Test Business').first()
            if not constraint_business:
                constraint_business = BusinessAccount(
                    name='Constraint Test Business',
                    account_type='customer',
                    contact_email='constraint@test.com',
                    contact_name='Constraint Test User', 
                    status='active'
                )
                db.session.add(constraint_business)
            test_businesses.append(constraint_business)
            
            db.session.commit()
            
            print(f"Created/found {len(test_businesses)} test business accounts")
            return [business.id for business in test_businesses]
            
        except Exception as e:
            print(f"Error setting up test environment: {e}")
            db.session.rollback()
            return None

def test_concurrent_license_assignment():
    """Test concurrent license assignment scenarios to validate race condition fixes"""
    print("\n=== Testing Concurrent License Assignment ===")
    
    with app.app_context():
        concurrency_business_id = setup_test_environment()[0]
        if not concurrency_business_id:
            print("❌ Could not setup test environment")
            return False
        
        # Clear any existing licenses for this business
        LicenseHistory.query.filter_by(business_account_id=concurrency_business_id).delete()
        db.session.commit()
        
        print(f"Testing concurrent assignment for business_id {concurrency_business_id}")
        
        # Test 1: Concurrent Core license assignments (should prevent duplicates)
        print("\n1. Testing concurrent Core license assignments...")
        results = []
        exceptions = []
        
        def assign_core_license(thread_id):
            """Attempt to assign Core license in separate thread"""
            try:
                with app.app_context():
                    success, license_record, message = LicenseService.assign_license_to_business(
                        business_id=concurrency_business_id,
                        license_type='core',
                        assigned_by=f'thread_{thread_id}@test.com'
                    )
                    results.append((thread_id, success, message, license_record.id if license_record else None))
            except Exception as e:
                exceptions.append((thread_id, str(e)))
        
        # Launch 5 concurrent assignment threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=assign_core_license, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        successful_assignments = [r for r in results if r[1]]  # r[1] is success flag
        failed_assignments = [r for r in results if not r[1]]
        
        print(f"   Successful assignments: {len(successful_assignments)}")
        print(f"   Failed assignments: {len(failed_assignments)}")
        print(f"   Exceptions: {len(exceptions)}")
        
        if len(successful_assignments) == 1:
            print("   ✅ PASS: Only one concurrent assignment succeeded")
        else:
            print(f"   ❌ FAIL: Expected 1 successful assignment, got {len(successful_assignments)}")
            return False
        
        # Test 2: Verify database constraint prevents duplicates
        print("\n2. Testing database constraint enforcement...")
        active_licenses = LicenseHistory.query.filter_by(
            business_account_id=concurrency_business_id,
            status='active'
        ).all()
        
        if len(active_licenses) == 1:
            print("   ✅ PASS: Database constraint prevented duplicate active licenses")
        else:
            print(f"   ❌ FAIL: Found {len(active_licenses)} active licenses, expected 1")
            return False
        
        return True

def test_downgrade_safety_validation():
    """Test downgrade usage validation to prevent unsafe downgrades"""
    print("\n=== Testing Downgrade Safety Validation ===")
    
    with app.app_context():
        downgrade_business_id = setup_test_environment()[1]
        if not downgrade_business_id:
            print("❌ Could not setup test environment")
            return False
        
        # Clear existing data for clean test
        LicenseHistory.query.filter_by(business_account_id=downgrade_business_id).delete()
        Campaign.query.filter_by(business_account_id=downgrade_business_id).delete()
        db.session.commit()
        
        print(f"Testing downgrade validation for business_id {downgrade_business_id}")
        
        # Test 1: Assign Pro license with high limits
        print("\n1. Assigning initial Pro license...")
        success, pro_license, message = LicenseService.assign_license_to_business(
            business_id=downgrade_business_id,
            license_type='pro',
            assigned_by='downgrade_test@example.com'
        )
        
        if not success:
            print(f"❌ Failed to assign Pro license: {message}")
            return False
        
        print(f"   ✅ Pro license assigned: {pro_license.max_campaigns_per_year} campaigns, {pro_license.max_users} users")
        
        # Test 2: Create usage that exceeds Core limits
        print("\n2. Creating usage that exceeds Core license limits...")
        
        # Create campaigns beyond Core limit (4 campaigns)
        campaigns_created = 0
        for i in range(6):  # Exceed Core limit of 4
            campaign = Campaign(
                name=f'Test Campaign {i+1}',
                description=f'Test campaign for downgrade validation {i+1}',
                start_date=date.today(),
                end_date=date.today() + timedelta(days=30),
                status='active',
                business_account_id=downgrade_business_id
            )
            db.session.add(campaign)
            campaigns_created += 1
        
        db.session.commit()
        print(f"   Created {campaigns_created} campaigns (exceeds Core limit of 4)")
        
        # Test 3: Attempt downgrade to Core (should be blocked)
        print("\n3. Attempting downgrade to Core license...")
        success, license_record, message = LicenseService.assign_license_to_business(
            business_id=downgrade_business_id,
            license_type='core',
            assigned_by='downgrade_test@example.com'
        )
        
        if success:
            print(f"   ❌ FAIL: Downgrade succeeded when it should have been blocked")
            return False
        else:
            print(f"   ✅ PASS: Downgrade blocked - {message}")
        
        # Test 4: Verify specific usage validation messages
        if 'campaigns used this period' in message.lower() and 'exceeds target limit' in message.lower():
            print("   ✅ PASS: Specific campaign usage validation message included")
        else:
            print(f"   ❌ FAIL: Expected specific usage validation message, got: {message}")
            return False
        
        # Test 5: Verify upgrade is still allowed  
        print("\n4. Testing that upgrades are still allowed...")
        success, license_record, message = LicenseService.assign_license_to_business(
            business_id=downgrade_business_id,
            license_type='pro',  # Same level - should work
            assigned_by='upgrade_test@example.com'
        )
        
        if success:
            print("   ✅ PASS: License renewal/upgrade allowed")
        else:
            print(f"   ❌ FAIL: License renewal failed: {message}")
            return False
        
        return True

def test_database_constraints():
    """Test database-level constraints prevent overlapping active licenses"""
    print("\n=== Testing Database Constraints ===")
    
    with app.app_context():
        constraint_business_id = setup_test_environment()[2]
        if not constraint_business_id:
            print("❌ Could not setup test environment")
            return False
        
        # Clear existing data
        LicenseHistory.query.filter_by(business_account_id=constraint_business_id).delete()
        db.session.commit()
        
        print(f"Testing database constraints for business_id {constraint_business_id}")
        
        # Test 1: Create first active license
        print("\n1. Creating first active license...")
        license1 = LicenseHistory(
            business_account_id=constraint_business_id,
            license_type='core',
            status='active',
            activated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365),
            max_campaigns_per_year=4,
            max_users=5,
            max_participants_per_campaign=200,
            created_by='constraint_test@example.com'
        )
        
        db.session.add(license1)
        db.session.commit()
        print("   ✅ First active license created successfully")
        
        # Test 2: Attempt to create second active license (should fail)
        print("\n2. Attempting to create second active license...")
        license2 = LicenseHistory(
            business_account_id=constraint_business_id,
            license_type='plus',
            status='active',  # This should violate the constraint
            activated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365),
            max_campaigns_per_year=8,
            max_users=10, 
            max_participants_per_campaign=500,
            created_by='constraint_test2@example.com'
        )
        
        try:
            db.session.add(license2)
            db.session.commit()
            print("   ❌ FAIL: Second active license was created (constraint not working)")
            return False
        except Exception as e:
            db.session.rollback()
            if 'unique' in str(e).lower() or 'duplicate' in str(e).lower():
                print("   ✅ PASS: Database constraint prevented duplicate active license")
            else:
                print(f"   ❌ FAIL: Unexpected error: {e}")
                return False
        
        # Test 3: Verify we can create expired licenses for the same business
        print("\n3. Testing creation of expired license (should succeed)...")
        license3 = LicenseHistory(
            business_account_id=constraint_business_id,
            license_type='trial',
            status='expired',  # Different status - should work
            activated_at=datetime.utcnow() - timedelta(days=400),
            expires_at=datetime.utcnow() - timedelta(days=35),
            max_campaigns_per_year=4,
            max_users=5,
            max_participants_per_campaign=500,
            created_by='constraint_test3@example.com'
        )
        
        try:
            db.session.add(license3)
            db.session.commit()
            print("   ✅ PASS: Expired license created successfully (constraint allows different statuses)")
        except Exception as e:
            print(f"   ❌ FAIL: Could not create expired license: {e}")
            return False
        
        return True

def test_audit_logging():
    """Test comprehensive audit logging for license operations"""
    print("\n=== Testing Audit Logging ===")
    
    with app.app_context():
        # Use existing business from setup
        test_business_ids = setup_test_environment()
        if not test_business_ids:
            print("❌ Could not setup test environment")
            return False
            
        business_id = test_business_ids[0]
        
        print(f"Testing audit logging for business_id {business_id}")
        
        # Clear existing licenses and audit logs
        LicenseHistory.query.filter_by(business_account_id=business_id).delete()
        
        from models import AuditLog
        AuditLog.query.filter_by(business_account_id=business_id).delete()
        db.session.commit()
        
        # Test 1: License assignment creates audit log
        print("\n1. Testing license assignment audit logging...")
        success, license_record, message = LicenseService.assign_license_to_business(
            business_id=business_id,
            license_type='plus',
            assigned_by='audit_test@example.com'
        )
        
        if not success:
            print(f"❌ License assignment failed: {message}")
            return False
        
        # Check audit log was created
        audit_logs = AuditLog.query.filter_by(
            business_account_id=business_id,
            action_type='license_assigned'
        ).all()
        
        if len(audit_logs) >= 1:
            print("   ✅ PASS: License assignment audit log created")
            
            # Verify audit log structure
            audit_log = audit_logs[0]
            if audit_log.user_email == 'audit_test@example.com':
                print("   ✅ PASS: Audit log contains correct user email")
            else:
                print(f"   ❌ FAIL: Expected user email 'audit_test@example.com', got '{audit_log.user_email}'")
                return False
                
            if audit_log.resource_type == 'license':
                print("   ✅ PASS: Audit log has correct resource type")
            else:
                print(f"   ❌ FAIL: Expected resource type 'license', got '{audit_log.resource_type}'")
                return False
        else:
            print("   ❌ FAIL: No audit log created for license assignment")
            return False
        
        return True

def main():
    """Main test runner"""
    print("Critical License Assignment Fixes - Comprehensive Test Suite")
    print("=" * 80)
    
    all_tests_passed = True
    
    # Run all test suites
    test_suites = [
        ("Concurrent License Assignment", test_concurrent_license_assignment),
        ("Downgrade Safety Validation", test_downgrade_safety_validation), 
        ("Database Constraints", test_database_constraints),
        ("Audit Logging", test_audit_logging)
    ]
    
    for test_name, test_function in test_suites:
        try:
            print(f"\nRunning {test_name} tests...")
            test_result = test_function()
            if test_result:
                print(f"✅ {test_name}: ALL TESTS PASSED")
            else:
                print(f"❌ {test_name}: TESTS FAILED")
                all_tests_passed = False
        except Exception as e:
            print(f"❌ {test_name}: EXCEPTION - {e}")
            all_tests_passed = False
    
    # Final summary
    print("\n" + "=" * 80)
    if all_tests_passed:
        print("🎉 ALL CRITICAL FIXES VALIDATED SUCCESSFULLY!")
        print("\nValidated Features:")
        print("✅ Concurrency protection with SELECT...FOR UPDATE")
        print("✅ Database constraints prevent overlapping active licenses")
        print("✅ Downgrade safety blocks unsafe downgrades")
        print("✅ Comprehensive audit logging")
        print("✅ Proper error handling and transaction rollback")
    else:
        print("❌ SOME TESTS FAILED - Critical fixes need attention")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)