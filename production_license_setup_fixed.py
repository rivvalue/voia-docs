#!/usr/bin/env python3
"""
Production License Setup Script for VOÏA - Voice Of Client
Author: System Migration Agent
Created: September 24, 2025

This script sets up the license system in production environment using Option 1:
Manual License Recreation with clean business account setup.

Usage:
    python production_license_setup_fixed.py [--dry-run] [--verbose]
    
Options:
    --dry-run    Validate setup without making changes
    --verbose    Enable detailed logging
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging(verbose=False):
    """Configure logging for the setup process"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'production_license_setup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    return logging.getLogger(__name__)

def validate_environment():
    """Validate we're in the right environment for production setup"""
    logger = logging.getLogger(__name__)
    
    try:
        # Check if database connection works
        from app import app, db
        from models import BusinessAccount, LicenseHistory
        
        # Run within Flask application context
        with app.app_context():
            # Test database connection
            db.session.execute(db.text('SELECT 1'))
            logger.info("✅ Database connection validated")
            
            # Check if tables exist
            result = db.session.execute(db.text(
                "SELECT table_name FROM information_schema.tables WHERE table_name IN ('business_accounts', 'license_history')"
            )).fetchall()
            
            table_names = [row[0] for row in result]
            required_tables = ['business_accounts', 'license_history']
            
            for table in required_tables:
                if table in table_names:
                    logger.info(f"✅ Table {table} exists")
                else:
                    logger.error(f"❌ Required table {table} missing")
                    return False
            
            # Import license system components
            from license_templates import LicenseTemplateManager
            from license_service import LicenseService
            
            # Validate license templates
            templates = LicenseTemplateManager.get_available_license_types()
            logger.info(f"✅ Available license templates: {templates}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Environment validation failed: {e}")
        return False

def create_production_business_accounts(dry_run=False):
    """Create clean production business accounts"""
    logger = logging.getLogger(__name__)
    
    try:
        from app import app, db
        from models import BusinessAccount, BusinessAccountUser
        
        production_accounts = [
            {
                'name': 'Rivvalue Inc',
                'account_type': 'premium',
                'contact_email': 'admin@rivvalue.com',
                'contact_name': 'Rivvalue Admin',
                'status': 'active',
                'industry': 'Technology Consulting',
                'company_description': 'Strategic technology consulting and implementation services',
                'target_clients_description': 'Mid-market technology companies and enterprises',
            },
            {
                'name': 'Demo Account',
                'account_type': 'demo', 
                'contact_email': 'demo@voia.com',
                'contact_name': 'Demo User',
                'status': 'active',
                'industry': 'Various',
                'company_description': 'Demonstration account for VOÏA system capabilities',
                'target_clients_description': 'Various industries and use cases',
            }
        ]
        
        created_accounts = []
        
        with app.app_context():
            for account_data in production_accounts:
                logger.info(f"Processing business account: {account_data['name']}")
                
                # Check if account already exists
                existing = BusinessAccount.query.filter_by(
                    name=account_data['name'],
                    account_type=account_data['account_type']
                ).first()
                
                if existing:
                    logger.info(f"  ⚠️  Account {account_data['name']} already exists (ID: {existing.id})")
                    created_accounts.append(existing)
                    continue
                
                if not dry_run:
                    # Create business account
                    business_account = BusinessAccount()
                    business_account.name = account_data['name']
                    business_account.account_type = account_data['account_type']
                    business_account.contact_email = account_data['contact_email']
                    business_account.contact_name = account_data['contact_name']
                    business_account.status = account_data['status']
                    business_account.industry = account_data.get('industry')
                    business_account.company_description = account_data.get('company_description')
                    business_account.target_clients_description = account_data.get('target_clients_description')
                    business_account.created_at = datetime.utcnow()
                    
                    db.session.add(business_account)
                    db.session.flush()  # Get ID without committing
                    
                    logger.info(f"  ✅ Created business account {account_data['name']} (ID: {business_account.id})")
                    created_accounts.append(business_account)
                else:
                    logger.info(f"  🔍 Would create business account: {account_data['name']}")
            
            if not dry_run:
                db.session.commit()
                logger.info("✅ All business accounts committed to database")
            
        return created_accounts
        
    except Exception as e:
        if not dry_run:
            from app import db
            db.session.rollback()
        logger.error(f"❌ Failed to create business accounts: {e}")
        raise

def assign_production_licenses(business_accounts, dry_run=False):
    """Assign licenses to production business accounts using template system"""
    logger = logging.getLogger(__name__)
    
    try:
        from app import app, db
        from license_service import LicenseService
        from models import LicenseHistory
        
        # License assignment mapping
        license_assignments = {
            'Rivvalue Inc': {
                'license_type': 'pro',
                'custom_config': {
                    'max_campaigns_per_year': 50,
                    'max_users': 100,  
                    'max_participants_per_campaign': 50000,
                    'duration_months': 24
                },
                'created_by': 'production_setup_script',
                'notes': 'Initial production license for Rivvalue Inc - 2 year Pro license with enhanced limits'
            },
            'Demo Account': {
                'license_type': 'trial',
                'created_by': 'production_setup_script',
                'notes': 'Demo account trial license for public demonstrations'
            }
        }
        
        assigned_licenses = []
        
        with app.app_context():
            for account in business_accounts:
                if account.name not in license_assignments:
                    logger.warning(f"  ⚠️  No license assignment configured for {account.name}")
                    continue
                
                assignment = license_assignments[account.name]
                logger.info(f"Assigning {assignment['license_type']} license to {account.name}")
                
                # Check if license already exists
                existing_license = LicenseService.get_current_license(account.id)
                if existing_license:
                    logger.info(f"  ⚠️  Active license already exists for {account.name} (Type: {existing_license.license_type})")
                    assigned_licenses.append(existing_license)
                    continue
                
                if not dry_run:
                    # Assign license using template system
                    success, license_record, message = LicenseService.assign_license_to_business(
                        business_id=account.id,
                        license_type=assignment['license_type'],
                        custom_config=assignment.get('custom_config'),
                        created_by=assignment['created_by']
                    )
                    
                    if not success or not license_record:
                        logger.error(f"  ❌ Failed to assign license to {account.name}: {message}")
                        continue
                    
                    # Add notes if provided
                    if assignment.get('notes'):
                        license_record.notes = assignment['notes']
                        db.session.commit()
                    
                    logger.info(f"  ✅ Assigned {assignment['license_type']} license to {account.name}")
                    logger.info(f"      - Campaigns: {license_record.max_campaigns_per_year}/year")
                    logger.info(f"      - Users: {license_record.max_users}")
                    logger.info(f"      - Participants: {license_record.max_participants_per_campaign}/campaign")
                    logger.info(f"      - Expires: {license_record.expires_at.date()}")
                    
                    assigned_licenses.append(license_record)
                else:
                    logger.info(f"  🔍 Would assign {assignment['license_type']} license to {account.name}")
                    if assignment.get('custom_config'):
                        logger.info(f"      - Custom config: {assignment['custom_config']}")
        
        return assigned_licenses
        
    except Exception as e:
        logger.error(f"❌ Failed to assign licenses: {e}")
        raise

def validate_license_setup(business_accounts, assigned_licenses, dry_run=False):
    """Validate the license setup is working correctly"""
    logger = logging.getLogger(__name__)
    
    try:
        from app import app
        from license_service import LicenseService
        
        validation_results = []
        
        with app.app_context():
            for account in business_accounts:
                logger.info(f"Validating license setup for {account.name}")
                
                # Test license lookup
                current_license = LicenseService.get_current_license(account.id)
                if current_license:
                    logger.info(f"  ✅ Current license: {current_license.license_type}")
                    logger.info(f"  ✅ License status: {current_license.status}")
                    logger.info(f"  ✅ Expires: {current_license.expires_at.date()}")
                else:
                    logger.warning(f"  ⚠️  No active license found for {account.name}")
                    continue
                
                # Test license period calculation
                period_start, period_end = LicenseService.get_license_period(account.id)
                if period_start and period_end:
                    logger.info(f"  ✅ License period: {period_start} to {period_end}")
                else:
                    logger.warning(f"  ⚠️  Could not determine license period for {account.name}")
                
                # Test usage limits
                can_activate_campaign = LicenseService.can_activate_campaign(account.id)
                can_add_user = LicenseService.can_add_user(account.id)
                
                logger.info(f"  ✅ Can activate campaign: {can_activate_campaign}")
                logger.info(f"  ✅ Can add user: {can_add_user}")
                
                # Get comprehensive license info
                license_info = LicenseService.get_license_info(account.id)
                logger.info(f"  ✅ License info retrieved: {license_info['license_type']} ({license_info['license_status']})")
                
                validation_results.append({
                    'account_name': account.name,
                    'account_id': account.id,
                    'license_valid': current_license is not None,
                    'license_type': current_license.license_type if current_license else None,
                    'period_valid': period_start is not None and period_end is not None,
                    'limits_working': can_activate_campaign is not None and can_add_user is not None
                })
            
            # Summary validation
            valid_setups = sum(1 for result in validation_results if all([
                result['license_valid'], 
                result['period_valid'], 
                result['limits_working']
            ]))
            
            logger.info(f"✅ Validation complete: {valid_setups}/{len(validation_results)} accounts fully validated")
            
        return validation_results
        
    except Exception as e:
        logger.error(f"❌ License validation failed: {e}")
        raise

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Setup production licenses for VOÏA system')
    parser.add_argument('--dry-run', action='store_true', help='Validate setup without making changes')
    parser.add_argument('--verbose', action='store_true', help='Enable detailed logging')
    
    args = parser.parse_args()
    
    logger = setup_logging(args.verbose)
    
    try:
        logger.info("🚀 Starting VOÏA Production License Setup")
        logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'PRODUCTION'}")
        
        # Step 1: Environment validation
        logger.info("\n📋 Step 1: Environment Validation")
        if not validate_environment():
            logger.error("❌ Environment validation failed. Aborting setup.")
            sys.exit(1)
        
        # Step 2: Create business accounts
        logger.info("\n🏢 Step 2: Business Account Setup")
        business_accounts = create_production_business_accounts(args.dry_run)
        
        # Step 3: Assign licenses
        logger.info("\n📄 Step 3: License Assignment")
        assigned_licenses = assign_production_licenses(business_accounts, args.dry_run)
        
        # Step 4: Validation
        logger.info("\n✅ Step 4: License Validation")
        validation_results = validate_license_setup(business_accounts, assigned_licenses, args.dry_run)
        
        # Final summary
        logger.info("\n🎯 Setup Summary")
        logger.info(f"Business Accounts: {len(business_accounts)}")
        logger.info(f"Licenses Assigned: {len(assigned_licenses)}")
        logger.info(f"Validation Results: {len([r for r in validation_results if r['license_valid']])}/{len(validation_results)} valid")
        
        if args.dry_run:
            logger.info("\n🔍 DRY RUN COMPLETE - No changes made to database")
            logger.info("Run without --dry-run to execute the setup")
        else:
            logger.info("\n✅ PRODUCTION SETUP COMPLETE")
            logger.info("License system ready for production use")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)