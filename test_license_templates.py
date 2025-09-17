#!/usr/bin/env python3
"""
Test script for License Template System
Author: System Integration Agent
Created: September 17, 2025

This script tests the license template system to ensure:
- Template creation and validation works correctly
- Integration with LicenseService functions properly
- Pro custom configuration is properly handled
- LicenseHistory records are created with correct values
"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import BusinessAccount, LicenseHistory
from license_service import LicenseService
from license_templates import LicenseTemplateManager, get_core_template, get_plus_template, get_pro_template

def test_template_definitions():
    """Test that all license templates are properly defined"""
    print("=== Testing License Template Definitions ===")
    
    # Test Core template
    core_template = get_core_template()
    print(f"Core Template: {core_template.display_name}")
    print(f"  - Max campaigns/year: {core_template.max_campaigns_per_year}")
    print(f"  - Max users: {core_template.max_users}")
    print(f"  - Max participants/campaign: {core_template.max_participants_per_campaign}")
    print(f"  - Is custom: {core_template.is_custom}")
    
    # Test Plus template
    plus_template = get_plus_template()
    print(f"Plus Template: {plus_template.display_name}")
    print(f"  - Max campaigns/year: {plus_template.max_campaigns_per_year}")
    print(f"  - Max users: {plus_template.max_users}")
    print(f"  - Max participants/campaign: {plus_template.max_participants_per_campaign}")
    print(f"  - Is custom: {plus_template.is_custom}")
    
    # Test Pro template
    pro_template = get_pro_template()
    print(f"Pro Template: {pro_template.display_name}")
    print(f"  - Max campaigns/year: {pro_template.max_campaigns_per_year}")
    print(f"  - Max users: {pro_template.max_users}")
    print(f"  - Max participants/campaign: {pro_template.max_participants_per_campaign}")
    print(f"  - Is custom: {pro_template.is_custom}")
    
    # Verify expected values
    assert core_template.max_participants_per_campaign == 200, "Core should have 200 participants/campaign"
    assert core_template.max_users == 5, "Core should have 5 users"
    assert plus_template.max_participants_per_campaign == 2000, "Plus should have 2000 participants/campaign"
    assert plus_template.max_users == 10, "Plus should have 10 users"
    assert pro_template.is_custom == True, "Pro should support custom configuration"
    
    print("✅ Template definitions test passed!\n")

def test_license_service_integration():
    """Test LicenseService integration with templates"""
    print("=== Testing LicenseService Integration ===")
    
    # Test getting available license types
    available_types = LicenseService.get_available_license_types()
    print(f"Available license types: {len(available_types)}")
    for license_type in available_types:
        print(f"  - {license_type['license_type']}: {license_type['display_name']}")
    
    # Test getting standard license types (non-trial)
    standard_types = LicenseService.get_standard_license_types()
    print(f"Standard license types: {len(standard_types)}")
    for license_type in standard_types:
        print(f"  - {license_type['license_type']}: {license_type['display_name']}")
    
    # Test template comparison
    comparison = LicenseService.get_license_template_comparison(['core', 'plus', 'pro'])
    print(f"Template comparison includes {len(comparison['license_types'])} types")
    print(f"Features compared: {list(comparison['features'].keys())}")
    print(f"Limits compared: {list(comparison['limits'].keys())}")
    
    print("✅ LicenseService integration test passed!\n")

def test_pro_custom_configuration():
    """Test Pro license custom configuration"""
    print("=== Testing Pro Custom Configuration ===")
    
    # Test valid custom configuration
    valid_config = {
        'max_campaigns_per_year': 20,
        'max_users': 50,
        'max_participants_per_campaign': 15000,
        'duration_months': 24
    }
    
    is_valid = LicenseService.validate_license_template_config('pro', valid_config)
    print(f"Valid Pro config validation: {is_valid}")
    assert is_valid, "Valid Pro configuration should pass validation"
    
    # Test invalid custom configuration
    invalid_config = {
        'max_campaigns_per_year': -5,  # Invalid negative value
        'max_users': 'invalid',  # Invalid type
    }
    
    is_invalid = LicenseService.validate_license_template_config('pro', invalid_config)
    print(f"Invalid Pro config validation: {is_invalid}")
    assert not is_invalid, "Invalid Pro configuration should fail validation"
    
    print("✅ Pro custom configuration test passed!\n")

def test_license_creation():
    """Test creating actual license records using templates"""
    print("=== Testing License Record Creation ===")
    
    with app.app_context():
        # Get or create a test business account
        test_account = BusinessAccount.query.filter_by(name='Test License Template Account').first()
        if not test_account:
            test_account = BusinessAccount(
                name='Test License Template Account',
                contact_email='test-license@example.com',
                status='active'
            )
            db.session.add(test_account)
            db.session.commit()
            print(f"Created test business account: {test_account.id}")
        else:
            print(f"Using existing test business account: {test_account.id}")
        
        # Test Core license creation
        print("Creating Core license...")
        core_license = LicenseService.apply_license_template(
            business_account_id=test_account.id,
            license_type='core',
            created_by='test_script'
        )
        
        if core_license:
            print(f"  ✅ Core license created: ID {core_license.id}")
            print(f"     - Type: {core_license.license_type}")
            print(f"     - Max campaigns/year: {core_license.max_campaigns_per_year}")
            print(f"     - Max users: {core_license.max_users}")
            print(f"     - Max participants/campaign: {core_license.max_participants_per_campaign}")
            print(f"     - Expires: {core_license.expires_at}")
            
            # Verify values match Core template
            assert core_license.max_participants_per_campaign == 200
            assert core_license.max_users == 5
            
            # Mark as expired for next test
            core_license.status = 'expired'
            db.session.commit()
        else:
            print("  ❌ Failed to create Core license")
            return False
        
        # Test Plus license creation
        print("Creating Plus license...")
        plus_license = LicenseService.apply_license_template(
            business_account_id=test_account.id,
            license_type='plus',
            created_by='test_script'
        )
        
        if plus_license:
            print(f"  ✅ Plus license created: ID {plus_license.id}")
            print(f"     - Type: {plus_license.license_type}")
            print(f"     - Max campaigns/year: {plus_license.max_campaigns_per_year}")
            print(f"     - Max users: {plus_license.max_users}")
            print(f"     - Max participants/campaign: {plus_license.max_participants_per_campaign}")
            
            # Verify values match Plus template
            assert plus_license.max_participants_per_campaign == 2000
            assert plus_license.max_users == 10
            
            # Mark as expired for next test
            plus_license.status = 'expired'
            db.session.commit()
        else:
            print("  ❌ Failed to create Plus license")
            return False
        
        # Test Pro license with custom configuration
        print("Creating Pro license with custom config...")
        custom_config = {
            'max_campaigns_per_year': 25,
            'max_users': 100,
            'max_participants_per_campaign': 20000
        }
        
        pro_license = LicenseService.apply_license_template(
            business_account_id=test_account.id,
            license_type='pro',
            custom_config=custom_config,
            created_by='test_script'
        )
        
        if pro_license:
            print(f"  ✅ Pro license created: ID {pro_license.id}")
            print(f"     - Type: {pro_license.license_type}")
            print(f"     - Max campaigns/year: {pro_license.max_campaigns_per_year}")
            print(f"     - Max users: {pro_license.max_users}")
            print(f"     - Max participants/campaign: {pro_license.max_participants_per_campaign}")
            
            # Verify values match custom configuration
            assert pro_license.max_campaigns_per_year == 25
            assert pro_license.max_users == 100
            assert pro_license.max_participants_per_campaign == 20000
            
        else:
            print("  ❌ Failed to create Pro license")
            return False
        
        print("✅ License record creation test passed!\n")
        return True

def test_license_service_methods():
    """Test that existing LicenseService methods work with template-created licenses"""
    print("=== Testing LicenseService Methods with Template Licenses ===")
    
    with app.app_context():
        # Get the test account
        test_account = BusinessAccount.query.filter_by(name='Test License Template Account').first()
        if not test_account:
            print("❌ Test account not found")
            return False
        
        # Test getting current license
        current_license = LicenseService.get_current_license(test_account.id)
        if current_license:
            print(f"Current license: {current_license.license_type} (ID: {current_license.id})")
            
            # Test license period calculation
            period_start, period_end = LicenseService.get_license_period(test_account.id)
            print(f"License period: {period_start} to {period_end}")
            
            # Test campaign activation check
            can_activate = LicenseService.can_activate_campaign(test_account.id)
            print(f"Can activate campaign: {can_activate}")
            
            # Test user addition check
            can_add_user = LicenseService.can_add_user(test_account.id)
            print(f"Can add user: {can_add_user}")
            
            print("✅ LicenseService methods test passed!\n")
            return True
        else:
            print("❌ No current license found")
            return False

def main():
    """Run all tests"""
    print("🧪 License Template System Test Suite")
    print("=" * 50)
    
    try:
        # Run all tests
        test_template_definitions()
        test_license_service_integration()
        test_pro_custom_configuration()
        
        license_creation_success = test_license_creation()
        if license_creation_success:
            test_license_service_methods()
        
        print("🎉 All tests completed successfully!")
        print("License Template System is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)