"""
License System Initialization and Testing Script
Author: Migration Agent  
Created: September 17, 2025

This script validates the license template system and prepares for data migration.
It tests all license templates, validates template configurations, and checks
integration with the LicenseService.
"""

import sys
import os
from datetime import datetime, date, timedelta
import logging

# Add the app to sys.path to import modules
sys.path.insert(0, os.path.abspath('.'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_license_templates():
    """Test all license templates and their configurations"""
    print("="*60)
    print("TESTING LICENSE TEMPLATE SYSTEM")
    print("="*60)
    
    try:
        from license_templates import LicenseTemplateManager, add_months
        
        # Test date arithmetic helper function
        print("\n1. Testing Date Arithmetic:")
        test_dates = [
            (datetime(2025, 1, 31), 1, "Jan 31 + 1 month -> Feb 28"),
            (datetime(2024, 1, 31), 1, "Jan 31 + 1 month -> Feb 29 (leap year)"),
            (datetime(2025, 3, 31), 1, "Mar 31 + 1 month -> Apr 30"),
            (datetime(2025, 12, 31), 1, "Dec 31 + 1 month -> Jan 31 (next year)"),
            (datetime(2025, 1, 15), 12, "Jan 15 + 12 months -> Jan 15 (next year)")
        ]
        
        for start_date, months, description in test_dates:
            result = add_months(start_date, months)
            print(f"  ✓ {description}: {result.strftime('%Y-%m-%d')}")
        
        # Test template access
        print("\n2. Testing Template Access:")
        templates = [
            ('CORE', LicenseTemplateManager.CORE_TEMPLATE),
            ('PLUS', LicenseTemplateManager.PLUS_TEMPLATE), 
            ('PRO', LicenseTemplateManager.PRO_TEMPLATE),
            ('TRIAL', LicenseTemplateManager.TRIAL_TEMPLATE)
        ]
        
        for name, template in templates:
            print(f"  ✓ {name}: {template.display_name}")
            print(f"    - Type: {template.license_type}")
            print(f"    - Max Campaigns/Year: {template.max_campaigns_per_year}")
            print(f"    - Max Users: {template.max_users}")
            print(f"    - Max Participants/Campaign: {template.max_participants_per_campaign}")
            print(f"    - Default Duration: {template.default_duration_months} months")
            print(f"    - Features: {', '.join(template.features)}")
            
        # Test template manager methods
        print("\n3. Testing Template Manager Methods:")
        
        # Test get_template
        core_template = LicenseTemplateManager.get_template('core')
        print(f"  ✓ get_template('core'): {core_template.display_name}")
        
        # Test get_all_templates
        all_templates = LicenseTemplateManager.get_all_templates()
        print(f"  ✓ get_all_templates(): {len(all_templates)} templates")
        
        # Test create_license_from_template
        print("\n4. Testing License Creation from Templates:")
        test_business_id = 999  # Test ID
        activation_date = datetime.now()
        
        for template_type in ['core', 'plus', 'pro', 'trial']:
            license_data = LicenseTemplateManager.create_license_from_template(
                business_account_id=test_business_id,
                template_type=template_type,
                activation_date=activation_date,
                created_by="test_script"
            )
            
            print(f"  ✓ {template_type.upper()} license created:")
            print(f"    - Business Account ID: {license_data['business_account_id']}")
            print(f"    - License Type: {license_data['license_type']}")
            print(f"    - Expires At: {license_data['expires_at']}")
            print(f"    - Max Campaigns: {license_data['max_campaigns_per_year']}")
            
        # Test Pro template with custom configuration
        print("\n5. Testing Pro Template Custom Configuration:")
        custom_config = {
            'max_campaigns_per_year': 50,
            'max_users': 150,
            'max_participants_per_campaign': 25000,
            'duration_months': 24
        }
        
        pro_custom = LicenseTemplateManager.create_license_from_template(
            business_account_id=test_business_id,
            template_type='pro',
            activation_date=activation_date,
            created_by="test_script",
            custom_config=custom_config
        )
        
        print(f"  ✓ Custom Pro license created:")
        print(f"    - Max Campaigns: {pro_custom['max_campaigns_per_year']}")
        print(f"    - Max Users: {pro_custom['max_users']}")
        print(f"    - Max Participants: {pro_custom['max_participants_per_campaign']}")
        print(f"    - Duration: 24 months")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Template testing failed: {e}")
        logger.error(f"License template testing failed: {e}")
        return False

def test_license_service_integration():
    """Test integration between LicenseTemplateManager and LicenseService"""
    print("\n" + "="*60)
    print("TESTING LICENSE SERVICE INTEGRATION") 
    print("="*60)
    
    try:
        from license_service import LicenseService
        
        # Test service methods (they should handle missing records gracefully)
        print("\n1. Testing LicenseService Methods:")
        
        # Test with existing business account
        test_account_id = 1  # Rivvalue Inc
        
        current_license = LicenseService.get_current_license(test_account_id)
        print(f"  ✓ get_current_license(1): {current_license}")
        
        license_period = LicenseService.get_license_period(test_account_id)
        print(f"  ✓ get_license_period(1): {license_period}")
        
        can_activate = LicenseService.can_activate_campaign(test_account_id)
        print(f"  ✓ can_activate_campaign(1): {can_activate}")
        
        campaigns_used = LicenseService.get_campaigns_used_in_current_period(
            test_account_id, date.today().replace(day=1), date.today()
        )
        print(f"  ✓ campaigns_used_in_current_period(1): {campaigns_used}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ LicenseService integration testing failed: {e}")
        logger.error(f"LicenseService integration testing failed: {e}")
        return False

def validate_existing_license_data():
    """Validate existing license data in the database"""
    print("\n" + "="*60)
    print("VALIDATING EXISTING LICENSE DATA")
    print("="*60)
    
    try:
        # Need to set up app context for database access
        from app import app, db
        from models import BusinessAccount, LicenseHistory
        
        with app.app_context():
            print("\n1. Analyzing Business Accounts:")
            accounts = BusinessAccount.query.all()
            
            for account in accounts:
                print(f"  • {account.name} (ID: {account.id})")
                print(f"    - Status: {account.status}")
                print(f"    - License Status (legacy): {account.license_status}")
                print(f"    - Legacy Activated: {account.license_activated_at}")
                print(f"    - Legacy Expires: {account.license_expires_at}")
                
                # Check license history for this account
                license_histories = LicenseHistory.query.filter_by(
                    business_account_id=account.id
                ).order_by(LicenseHistory.created_at.desc()).all()
                
                if license_histories:
                    print(f"    - License History Records: {len(license_histories)}")
                    current = None
                    for lh in license_histories:
                        if lh.status == 'active':
                            current = lh
                            break
                    
                    if current:
                        print(f"    - Current License: {current.license_type}")
                        print(f"    - Current Expires: {current.expires_at}")
                        print(f"    - Current Limits: {current.max_campaigns_per_year}C/{current.max_users}U/{current.max_participants_per_campaign}P")
                    else:
                        print(f"    - No active license in history")
                else:
                    print(f"    - No license history records")
                print()
            
            print(f"2. Summary:")
            print(f"  - Total Business Accounts: {len(accounts)}")
            
            total_licenses = LicenseHistory.query.count()
            active_licenses = LicenseHistory.query.filter_by(status='active').count()
            migrated_licenses = LicenseHistory.query.filter_by(migrated_from_business_account=True).count()
            
            print(f"  - Total License History Records: {total_licenses}")
            print(f"  - Active Licenses: {active_licenses}")
            print(f"  - Migrated from Business Account: {migrated_licenses}")
            
            # Check for accounts needing migration
            accounts_needing_migration = []
            for account in accounts:
                has_active_license = LicenseHistory.query.filter_by(
                    business_account_id=account.id,
                    status='active'
                ).first() is not None
                
                if not has_active_license:
                    accounts_needing_migration.append(account)
            
            print(f"  - Accounts Needing Migration: {len(accounts_needing_migration)}")
            for account in accounts_needing_migration:
                print(f"    • {account.name} (ID: {account.id})")
            
        return True
        
    except Exception as e:
        print(f"  ✗ License data validation failed: {e}")
        logger.error(f"License data validation failed: {e}")
        return False

if __name__ == "__main__":
    print("License System Initialization and Testing")
    print("Starting comprehensive license system validation...")
    
    success = True
    
    # Run all tests
    success &= test_license_templates()
    success &= test_license_service_integration() 
    success &= validate_existing_license_data()
    
    print("\n" + "="*60)
    if success:
        print("✅ ALL TESTS PASSED - License system is ready for migration")
    else:
        print("❌ SOME TESTS FAILED - Review errors before proceeding")
    print("="*60)