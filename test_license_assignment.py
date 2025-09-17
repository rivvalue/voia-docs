#!/usr/bin/env python3
"""
Test Script for License Assignment Logic
Author: System Integration Agent
Created: September 17, 2025

This script tests the comprehensive license assignment functionality implemented
in the LicenseService class.
"""

import os
import sys
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and models
from app import app, db
from models import BusinessAccount, LicenseHistory
from license_service import LicenseService
from license_templates import LicenseTemplateManager

def setup_test_environment():
    """Setup test environment with a test business account"""
    print("Setting up test environment...")
    
    with app.app_context():
        try:
            # Create a test business account if it doesn't exist
            test_business = BusinessAccount.query.filter_by(name='Test License Assignment Business').first()
            if not test_business:
                test_business = BusinessAccount(
                    name='Test License Assignment Business',
                    account_type='customer',
                    contact_email='test@licenseassignment.com',
                    contact_name='Test User',
                    status='active'
                )
                db.session.add(test_business)
                db.session.commit()
                print(f"Created test business account with ID: {test_business.id}")
            else:
                print(f"Using existing test business account with ID: {test_business.id}")
            
            return test_business.id
            
        except Exception as e:
            print(f"Error setting up test environment: {e}")
            return None

def test_license_templates():
    """Test license template functionality"""
    print("\n=== Testing License Templates ===")
    
    # Test getting available license types
    available_types = LicenseTemplateManager.get_available_license_types()
    print(f"Available license types: {[t['license_type'] for t in available_types]}")
    
    # Test individual templates
    for license_type in ['core', 'plus', 'pro', 'trial']:
        template = LicenseTemplateManager.get_template(license_type)
        if template:
            print(f"{license_type.title()} template: {template.max_users} users, {template.max_campaigns_per_year} campaigns/year")
        else:
            print(f"ERROR: Template not found for {license_type}")
    
    return True

def test_license_assignment_validation():
    """Test license assignment validation logic"""
    print("\n=== Testing License Assignment Validation ===")
    
    with app.app_context():
        test_business_id = setup_test_environment()
        if not test_business_id:
            print("ERROR: Could not setup test business")
            return False
        
        # Test valid assignment validation
        success, message = LicenseService.validate_license_assignment(test_business_id, 'core')
        print(f"Core license validation: {'PASS' if success else 'FAIL'} - {message}")
        
        # Test invalid business ID
        success, message = LicenseService.validate_license_assignment(999999, 'core')
        print(f"Invalid business ID validation: {'PASS' if not success else 'FAIL'} - {message}")
        
        # Test invalid license type
        success, message = LicenseService.validate_license_assignment(test_business_id, 'invalid')
        print(f"Invalid license type validation: {'PASS' if not success else 'FAIL'} - {message}")
        
        # Test Pro license with valid custom limits
        custom_limits = {
            'max_campaigns_per_year': 20,
            'max_users': 50,
            'max_participants_per_campaign': 5000
        }
        success, message = LicenseService.validate_license_assignment(test_business_id, 'pro', custom_limits)
        print(f"Pro license with custom limits validation: {'PASS' if success else 'FAIL'} - {message}")
        
        # Test Pro license with invalid custom limits
        invalid_limits = {
            'max_campaigns_per_year': -5,  # Invalid: negative
            'max_users': 0,  # Invalid: zero
            'max_participants_per_campaign': 2000000  # Invalid: too high
        }
        success, message = LicenseService.validate_license_assignment(test_business_id, 'pro', invalid_limits)
        print(f"Pro license with invalid limits validation: {'PASS' if not success else 'FAIL'} - {message}")
        
        return True

def test_license_assignment():
    """Test complete license assignment process"""
    print("\n=== Testing License Assignment ===")
    
    with app.app_context():
        test_business_id = setup_test_environment()
        if not test_business_id:
            print("ERROR: Could not setup test business")
            return False
        
        # Test 1: Assign Core license
        print("\nTest 1: Assigning Core license...")
        success, license_record, message = LicenseService.assign_license_to_business(
            business_id=test_business_id,
            license_type='core',
            assigned_by='test_user@example.com'
        )
        print(f"Core license assignment: {'SUCCESS' if success else 'FAILED'} - {message}")
        
        if success and license_record:
            print(f"  License ID: {license_record.id}")
            print(f"  License Type: {license_record.license_type}")
            print(f"  Max Users: {license_record.max_users}")
            print(f"  Max Campaigns: {license_record.max_campaigns_per_year}")
            print(f"  Expires: {license_record.expires_at}")
        
        # Test 2: Try to assign another license (should handle transition)
        print("\nTest 2: Upgrading to Plus license...")
        success, license_record2, message = LicenseService.assign_license_to_business(
            business_id=test_business_id,
            license_type='plus',
            assigned_by='test_user@example.com'
        )
        print(f"Plus license assignment: {'SUCCESS' if success else 'FAILED'} - {message}")
        
        if success and license_record2:
            print(f"  New License ID: {license_record2.id}")
            print(f"  License Type: {license_record2.license_type}")
            print(f"  Max Users: {license_record2.max_users}")
        
        # Test 3: Assign Pro license with custom limits
        print("\nTest 3: Assigning Pro license with custom limits...")
        custom_limits = {
            'max_campaigns_per_year': 24,
            'max_users': 75,
            'max_participants_per_campaign': 15000
        }
        success, license_record3, message = LicenseService.assign_license_to_business(
            business_id=test_business_id,
            license_type='pro',
            custom_limits=custom_limits,
            assigned_by='admin@example.com'
        )
        print(f"Pro license with custom limits: {'SUCCESS' if success else 'FAILED'} - {message}")
        
        if success and license_record3:
            print(f"  New License ID: {license_record3.id}")
            print(f"  Max Users: {license_record3.max_users} (custom)")
            print(f"  Max Campaigns: {license_record3.max_campaigns_per_year} (custom)")
            print(f"  Max Participants: {license_record3.max_participants_per_campaign} (custom)")
        
        return True

def test_license_history():
    """Test license assignment history"""
    print("\n=== Testing License Assignment History ===")
    
    with app.app_context():
        test_business_id = setup_test_environment()
        if not test_business_id:
            print("ERROR: Could not setup test business")
            return False
        
        # Get license assignment history
        history = LicenseService.get_license_assignment_history(test_business_id)
        print(f"Found {len(history)} license records in history")
        
        for i, record in enumerate(history[:5], 1):  # Show first 5 records
            print(f"  {i}. {record['license_type']} license (Status: {record['status']})")
            print(f"     Created: {record['created_at']}")
            print(f"     Created by: {record['created_by']}")
            if record.get('notes'):
                print(f"     Notes: {record['notes']}")
        
        return True

def main():
    """Main test function"""
    print("License Assignment Logic Test Suite")
    print("=" * 50)
    
    try:
        # Run all tests
        tests = [
            test_license_templates,
            test_license_assignment_validation,
            test_license_assignment,
            test_license_history
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"ERROR in test {test.__name__}: {e}")
                results.append(False)
        
        # Summary
        print("\n" + "=" * 50)
        print("Test Results Summary:")
        passed = sum(results)
        total = len(results)
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("❌ Some tests failed.")
            return False
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)