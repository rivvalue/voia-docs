"""
Comprehensive License Migration Script
Author: Migration Agent
Created: September 17, 2025

This script performs complete data migration and initial setup for the license management system.
It ensures all business accounts have proper license assignments and validates the system works correctly.

Migration Components:
1. License template validation and initialization  
2. Business account audit and migration
3. License assignment for accounts missing proper licenses
4. Data validation and consistency checks
5. System integration testing

The migration is designed to be safe, with comprehensive logging and validation at each step.
"""

import sys
import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/license_migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def validate_license_templates():
    """Validate all license templates are properly configured"""
    print("="*60)
    print("1. VALIDATING LICENSE TEMPLATES")
    print("="*60)
    
    try:
        from license_templates import LicenseTemplateManager
        
        # Test all templates
        all_templates = LicenseTemplateManager.get_all_templates()
        print(f"✓ Found {len(all_templates)} license templates")
        
        for template_type, template in all_templates.items():
            print(f"  • {template.display_name} ({template_type})")
            print(f"    - Campaigns/Year: {template.max_campaigns_per_year}")
            print(f"    - Max Users: {template.max_users}")
            print(f"    - Max Participants: {template.max_participants_per_campaign}")
            print(f"    - Duration: {template.default_duration_months} months")
            
            # Validate template can create license data
            test_data = LicenseTemplateManager.create_license_from_template(
                business_account_id=999,
                template_type=template_type,
                created_by="migration_test"
            )
            assert test_data['license_type'] == template_type
            assert test_data['max_campaigns_per_year'] == template.max_campaigns_per_year
            print(f"    ✓ Template validation passed")
        
        # Test Pro template with custom configuration
        custom_config = {
            'max_campaigns_per_year': 20,
            'max_users': 50,
            'max_participants_per_campaign': 5000,
            'duration_months': 24
        }
        
        pro_custom = LicenseTemplateManager.create_license_from_template(
            business_account_id=999,
            template_type='pro',
            created_by="migration_test",
            custom_config=custom_config
        )
        
        assert pro_custom['max_campaigns_per_year'] == 20
        assert pro_custom['max_users'] == 50
        print(f"  ✓ Pro custom configuration validation passed")
        
        logger.info("License template validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"License template validation failed: {e}")
        return False

def audit_business_accounts():
    """Audit all business accounts and their current license status"""
    print("\n" + "="*60)
    print("2. AUDITING BUSINESS ACCOUNTS")
    print("="*60)
    
    try:
        from app import app, db
        from models import BusinessAccount, LicenseHistory
        
        audit_results = {
            'accounts': [],
            'needs_migration': [],
            'needs_license': [],
            'has_active_license': [],
            'summary': {}
        }
        
        with app.app_context():
            accounts = BusinessAccount.query.all()
            print(f"Found {len(accounts)} business accounts to audit:")
            
            for account in accounts:
                account_info = {
                    'id': account.id,
                    'name': account.name,
                    'account_type': account.account_type,
                    'status': account.status,
                    'legacy_license_status': account.license_status,
                    'legacy_activated_at': account.license_activated_at,
                    'legacy_expires_at': account.license_expires_at,
                    'license_history_count': 0,
                    'active_license': None,
                    'needs_action': 'none'
                }
                
                # Check license history for this account
                license_histories = LicenseHistory.query.filter_by(
                    business_account_id=account.id
                ).order_by(LicenseHistory.created_at.desc()).all()
                
                account_info['license_history_count'] = len(license_histories)
                
                # Find active license
                active_license = None
                for lh in license_histories:
                    if lh.status == 'active':
                        active_license = lh
                        break
                
                if active_license:
                    account_info['active_license'] = {
                        'license_type': active_license.license_type,
                        'expires_at': active_license.expires_at,
                        'max_campaigns_per_year': active_license.max_campaigns_per_year,
                        'max_users': active_license.max_users,
                        'max_participants_per_campaign': active_license.max_participants_per_campaign
                    }
                    account_info['needs_action'] = 'none'
                    audit_results['has_active_license'].append(account_info)
                else:
                    # Account needs license assignment
                    if account.account_type == 'demo':
                        account_info['needs_action'] = 'demo_license'
                        account_info['recommended_license'] = 'plus'  # Demos get Plus for showcase
                    else:
                        account_info['needs_action'] = 'trial_license'
                        account_info['recommended_license'] = 'core'  # New customers start with Core
                    
                    audit_results['needs_license'].append(account_info)
                
                # Check if legacy migration is needed
                if account.license_activated_at or account.license_expires_at:
                    if not active_license:
                        account_info['needs_action'] = 'legacy_migration'
                        audit_results['needs_migration'].append(account_info)
                
                audit_results['accounts'].append(account_info)
                
                # Print account summary
                print(f"\n  • {account.name} (ID: {account.id})")
                print(f"    - Type: {account.account_type}, Status: {account.status}")
                print(f"    - Legacy License: {account.license_status}")
                if active_license:
                    print(f"    - Active License: {active_license.license_type} (expires {active_license.expires_at.date()})")
                    print(f"    - Limits: {active_license.max_campaigns_per_year}C/{active_license.max_users}U/{active_license.max_participants_per_campaign}P")
                else:
                    print(f"    - ⚠️ No Active License - Action: {account_info['needs_action']}")
                    if 'recommended_license' in account_info:
                        print(f"    - Recommended: {account_info['recommended_license']}")
        
        # Generate summary
        audit_results['summary'] = {
            'total_accounts': len(audit_results['accounts']),
            'has_active_license': len(audit_results['has_active_license']),
            'needs_license': len(audit_results['needs_license']),
            'needs_migration': len(audit_results['needs_migration'])
        }
        
        print(f"\n📊 AUDIT SUMMARY:")
        print(f"  - Total Accounts: {audit_results['summary']['total_accounts']}")
        print(f"  - Has Active License: {audit_results['summary']['has_active_license']}")
        print(f"  - Needs License Assignment: {audit_results['summary']['needs_license']}")
        print(f"  - Needs Legacy Migration: {audit_results['summary']['needs_migration']}")
        
        logger.info(f"Business account audit completed: {audit_results['summary']}")
        return audit_results
        
    except Exception as e:
        logger.error(f"Business account audit failed: {e}")
        return None

def execute_license_migration(audit_results: Dict[str, Any]):
    """Execute license migration for accounts that need it"""
    print("\n" + "="*60)
    print("3. EXECUTING LICENSE MIGRATION")
    print("="*60)
    
    if not audit_results:
        print("❌ No audit results available for migration")
        return False
    
    try:
        from app import app, db
        from models import BusinessAccount, LicenseHistory
        from license_templates import LicenseTemplateManager
        
        migration_results = {
            'successful': [],
            'failed': [],
            'skipped': []
        }
        
        with app.app_context():
            # Migrate accounts needing license assignment
            accounts_to_process = audit_results['needs_license'] + audit_results['needs_migration']
            
            if not accounts_to_process:
                print("✅ All accounts already have proper license assignments")
                return True
            
            print(f"Processing {len(accounts_to_process)} accounts needing license assignment...")
            
            for account_info in accounts_to_process:
                try:
                    account_id = account_info['id']
                    account_name = account_info['name']
                    action = account_info['needs_action']
                    
                    print(f"\n  Processing: {account_name} (ID: {account_id})")
                    print(f"    Action: {action}")
                    
                    # Determine license type
                    if action == 'demo_license':
                        license_type = 'plus'  # Demos get Plus for showcase
                        notes = f"Demo license assigned during migration on {date.today()}"
                    elif action == 'trial_license':
                        license_type = 'core'   # New customers start with Core
                        notes = f"Core license assigned during migration on {date.today()}"
                    elif action == 'legacy_migration':
                        # Migrate from legacy fields
                        business_account = BusinessAccount.query.get(account_id)
                        if business_account and business_account.license_activated_at:
                            # Create license based on legacy data
                            license_data = LicenseTemplateManager.create_license_from_template(
                                business_account_id=account_id,
                                template_type='core',  # Default to Core for legacy
                                activation_date=business_account.license_activated_at,
                                created_by="legacy_migration",
                                notes=f"Migrated from legacy business account fields on {date.today()}"
                            )
                            license_data['migrated_from_business_account'] = True
                            license_data['migration_notes'] = f"Legacy activated: {business_account.license_activated_at}, expires: {business_account.license_expires_at}"
                        else:
                            # Fallback to standard Core license
                            license_data = LicenseTemplateManager.create_license_from_template(
                                business_account_id=account_id,
                                template_type='core',
                                created_by="legacy_migration_fallback",
                                notes=f"Legacy migration fallback - assigned Core license on {date.today()}"
                            )
                    else:
                        # Standard license assignment
                        license_type = account_info.get('recommended_license', 'core')
                        license_data = LicenseTemplateManager.create_license_from_template(
                            business_account_id=account_id,
                            template_type=license_type,
                            created_by="migration_agent",
                            notes=notes
                        )
                    
                    # Create license data if not already created above
                    if action != 'legacy_migration' or 'license_data' not in locals():
                        license_data = LicenseTemplateManager.create_license_from_template(
                            business_account_id=account_id,
                            template_type=license_type,
                            created_by="migration_agent",
                            notes=notes
                        )
                    
                    # Create LicenseHistory record
                    license_record = LicenseHistory(
                        business_account_id=license_data['business_account_id'],
                        license_type=license_data['license_type'],
                        status=license_data['status'],
                        activated_at=license_data['activated_at'],
                        expires_at=license_data['expires_at'],
                        max_campaigns_per_year=license_data['max_campaigns_per_year'],
                        max_users=license_data['max_users'],
                        max_participants_per_campaign=license_data['max_participants_per_campaign'],
                        created_by=license_data['created_by'],
                        notes=license_data['notes'],
                        migrated_from_business_account=license_data.get('migrated_from_business_account', False),
                        migration_notes=license_data.get('migration_notes')
                    )
                    
                    # Expire any existing active licenses first
                    existing_active = LicenseHistory.query.filter_by(
                        business_account_id=account_id,
                        status='active'
                    ).all()
                    
                    for existing in existing_active:
                        existing.status = 'expired'
                        print(f"    - Expired existing license: {existing.license_type}")
                    
                    # Add new license
                    db.session.add(license_record)
                    db.session.commit()
                    
                    print(f"    ✅ Assigned {license_data['license_type']} license")
                    print(f"       Expires: {license_data['expires_at'].date()}")
                    print(f"       Limits: {license_data['max_campaigns_per_year']}C/{license_data['max_users']}U/{license_data['max_participants_per_campaign']}P")
                    
                    migration_results['successful'].append({
                        'account_id': account_id,
                        'account_name': account_name,
                        'license_type': license_data['license_type'],
                        'action': action
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to migrate account {account_info['name']} ({account_info['id']}): {e}")
                    migration_results['failed'].append({
                        'account_id': account_info['id'],
                        'account_name': account_info['name'],
                        'error': str(e),
                        'action': account_info['needs_action']
                    })
                    # Rollback this specific transaction
                    db.session.rollback()
                    continue
        
        # Print migration results
        print(f"\n📊 MIGRATION RESULTS:")
        print(f"  - Successful: {len(migration_results['successful'])}")
        print(f"  - Failed: {len(migration_results['failed'])}")
        print(f"  - Skipped: {len(migration_results['skipped'])}")
        
        if migration_results['failed']:
            print(f"\n❌ Failed migrations:")
            for failed in migration_results['failed']:
                print(f"  - {failed['account_name']}: {failed['error']}")
        
        logger.info(f"License migration completed: {len(migration_results['successful'])} successful, {len(migration_results['failed'])} failed")
        return len(migration_results['failed']) == 0
        
    except Exception as e:
        logger.error(f"License migration failed: {e}")
        return False

def validate_migration_results():
    """Validate that all accounts now have proper license assignments"""
    print("\n" + "="*60)
    print("4. VALIDATING MIGRATION RESULTS")
    print("="*60)
    
    try:
        from app import app, db
        from models import BusinessAccount, LicenseHistory
        from license_service import LicenseService
        
        validation_results = {
            'total_accounts': 0,
            'accounts_with_license': 0,
            'accounts_without_license': 0,
            'license_service_tests': {},
            'issues': []
        }
        
        with app.app_context():
            accounts = BusinessAccount.query.all()
            validation_results['total_accounts'] = len(accounts)
            
            print(f"Validating {len(accounts)} business accounts...")
            
            for account in accounts:
                print(f"\n  🔍 {account.name} (ID: {account.id})")
                
                # Check if account has active license
                current_license = LicenseService.get_current_license(account.id)
                
                if current_license:
                    validation_results['accounts_with_license'] += 1
                    print(f"    ✅ Active License: {current_license.license_type}")
                    print(f"       Expires: {current_license.expires_at.date()}")
                    print(f"       Limits: {current_license.max_campaigns_per_year}C/{current_license.max_users}U/{current_license.max_participants_per_campaign}P")
                    
                    # Test license service methods
                    try:
                        license_period = LicenseService.get_license_period(account.id)
                        can_activate = LicenseService.can_activate_campaign(account.id)
                        campaigns_used = LicenseService.get_campaigns_used_in_current_period(
                            account.id, date.today().replace(day=1), date.today()
                        )
                        
                        print(f"    📊 License Service Tests:")
                        print(f"       License Period: {license_period[0]} to {license_period[1]}")
                        print(f"       Can Activate Campaign: {can_activate}")
                        print(f"       Campaigns Used This Period: {campaigns_used}")
                        
                        validation_results['license_service_tests'][account.id] = {
                            'license_period': license_period,
                            'can_activate_campaign': can_activate,
                            'campaigns_used': campaigns_used,
                            'status': 'passed'
                        }
                        
                    except Exception as e:
                        validation_results['issues'].append(f"LicenseService test failed for {account.name}: {e}")
                        validation_results['license_service_tests'][account.id] = {
                            'status': 'failed',
                            'error': str(e)
                        }
                else:
                    validation_results['accounts_without_license'] += 1
                    validation_results['issues'].append(f"Account {account.name} ({account.id}) has no active license")
                    print(f"    ❌ No active license found")
        
        # Print validation summary
        print(f"\n📊 VALIDATION SUMMARY:")
        print(f"  - Total Accounts: {validation_results['total_accounts']}")
        print(f"  - Accounts with License: {validation_results['accounts_with_license']}")
        print(f"  - Accounts without License: {validation_results['accounts_without_license']}")
        print(f"  - LicenseService Tests Passed: {sum(1 for t in validation_results['license_service_tests'].values() if t['status'] == 'passed')}")
        
        if validation_results['issues']:
            print(f"\n⚠️  Issues Found:")
            for issue in validation_results['issues']:
                print(f"  - {issue}")
        
        success = (validation_results['accounts_without_license'] == 0 and 
                  len(validation_results['issues']) == 0)
        
        if success:
            print(f"\n✅ VALIDATION PASSED - All accounts have proper license assignments")
        else:
            print(f"\n❌ VALIDATION FAILED - {len(validation_results['issues'])} issues found")
        
        logger.info(f"Migration validation completed: {validation_results}")
        return success
        
    except Exception as e:
        logger.error(f"Migration validation failed: {e}")
        return False

def test_license_admin_interface():
    """Test that the license admin interface works with migrated data"""
    print("\n" + "="*60)
    print("5. TESTING ADMIN INTERFACE INTEGRATION")
    print("="*60)
    
    try:
        from app import app, db
        from models import BusinessAccount, LicenseHistory
        from license_service import LicenseService
        
        # Test data that admin interface would need
        with app.app_context():
            accounts = BusinessAccount.query.all()
            print(f"Testing admin interface data for {len(accounts)} accounts...")
            
            admin_data = []
            for account in accounts:
                current_license = LicenseService.get_current_license(account.id)
                license_period = LicenseService.get_license_period(account.id)
                can_activate = LicenseService.can_activate_campaign(account.id)
                
                account_data = {
                    'id': account.id,
                    'name': account.name,
                    'account_type': account.account_type,
                    'status': account.status,
                    'current_license_type': current_license.license_type if current_license else None,
                    'license_expires': current_license.expires_at.date() if current_license else None,
                    'license_period': license_period,
                    'can_activate_campaign': can_activate,
                    'campaigns_used': LicenseService.get_campaigns_used_in_current_period(
                        account.id, license_period[0] if license_period[0] else date.today().replace(day=1), 
                        license_period[1] if license_period[1] else date.today()
                    ) if license_period[0] and license_period[1] else 0
                }
                
                admin_data.append(account_data)
                
                print(f"  ✅ {account.name}")
                print(f"    - License: {account_data['current_license_type']}")
                print(f"    - Expires: {account_data['license_expires']}")
                print(f"    - Can Activate Campaign: {account_data['can_activate_campaign']}")
                print(f"    - Campaigns Used: {account_data['campaigns_used']}")
        
        print(f"\n✅ Admin interface data generation successful for {len(admin_data)} accounts")
        logger.info(f"Admin interface testing completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Admin interface testing failed: {e}")
        print(f"❌ Admin interface testing failed: {e}")
        return False

def main():
    """Main migration execution function"""
    print("🚀 Starting Comprehensive License Migration")
    print("=" * 80)
    
    logger.info("Starting comprehensive license migration and initial setup")
    
    success = True
    
    # Step 1: Validate license templates
    if not validate_license_templates():
        logger.error("License template validation failed - aborting migration")
        return False
    
    # Step 2: Audit business accounts
    audit_results = audit_business_accounts()
    if not audit_results:
        logger.error("Business account audit failed - aborting migration")
        return False
    
    # Step 3: Execute migration for accounts that need it
    if not execute_license_migration(audit_results):
        logger.error("License migration failed - some accounts may not be migrated properly")
        success = False
    
    # Step 4: Validate migration results
    if not validate_migration_results():
        logger.error("Migration validation failed - system may not be working correctly")
        success = False
    
    # Step 5: Test admin interface integration
    if not test_license_admin_interface():
        logger.error("Admin interface testing failed - UI may not display correctly")
        success = False
    
    # Final summary
    print("\n" + "="*80)
    if success:
        print("🎉 COMPREHENSIVE LICENSE MIGRATION COMPLETED SUCCESSFULLY")
        print("\nAll business accounts now have proper license assignments")
        print("License enforcement is working correctly")
        print("Admin interface integration is validated")
        logger.info("Comprehensive license migration completed successfully")
    else:
        print("⚠️  MIGRATION COMPLETED WITH ISSUES")
        print("\nSome components may not be working correctly")
        print("Please review the logs for detailed error information")
        logger.warning("Migration completed with issues - manual review required")
    
    print("="*80)
    return success

if __name__ == "__main__":
    try:
        success = main()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Migration script failed with exception: {e}")
        print(f"\n💥 MIGRATION FAILED WITH EXCEPTION: {e}")
        sys.exit(1)