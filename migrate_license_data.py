#!/usr/bin/env python3
"""
Comprehensive License Data Migration Script
==========================================

This script migrates license data from BusinessAccount fields to the new 
license_history table with extensive validation and safety measures.

Author: Data Migration Agent
Date: September 17, 2025
Version: 1.0

Usage:
    python migrate_license_data.py [--dry-run] [--force] [--debug]
    
Options:
    --dry-run    Perform validation checks without making changes
    --force      Skip confirmation prompts (use with caution)
    --debug      Enable detailed debug logging
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Add the current directory to Python path to import our models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import BusinessAccount, LicenseHistory


class LicenseMigrationValidator:
    """Validator class for license migration process"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_errors = []
        self.validation_warnings = []
    
    def validate_business_account(self, business_account: BusinessAccount) -> Dict:
        """Validate a single business account for migration"""
        validation_result = {
            'account_id': business_account.id,
            'account_name': business_account.name,
            'errors': [],
            'warnings': [],
            'migration_plan': {}
        }
        
        # Basic validation
        if not business_account.name or not business_account.name.strip():
            validation_result['errors'].append("Business account has no name")
        
        if not business_account.created_at:
            validation_result['errors'].append("Business account has no creation date")
        
        # License status validation
        if business_account.license_status not in ['trial', 'active', 'expired']:
            validation_result['warnings'].append(f"Unusual license_status: {business_account.license_status}")
        
        # Date validation
        if business_account.license_activated_at and business_account.license_expires_at:
            if business_account.license_activated_at >= business_account.license_expires_at:
                validation_result['errors'].append("license_activated_at is not before license_expires_at")
        
        # Check for existing license_history records
        existing_licenses = LicenseHistory.query.filter_by(business_account_id=business_account.id).count()
        if existing_licenses > 0:
            validation_result['warnings'].append(f"Account already has {existing_licenses} license_history records")
        
        # Generate migration plan
        validation_result['migration_plan'] = self._generate_migration_plan(business_account)
        
        return validation_result
    
    def _generate_migration_plan(self, business_account: BusinessAccount) -> Dict:
        """Generate migration plan for a business account"""
        plan = {
            'source_license_status': business_account.license_status,
            'source_activated_at': business_account.license_activated_at.isoformat() if business_account.license_activated_at else None,
            'source_expires_at': business_account.license_expires_at.isoformat() if business_account.license_expires_at else None,
            'target_license_type': None,
            'target_activated_at': None,
            'target_expires_at': None,
            'target_status': None,
            'migration_notes': []
        }
        
        # Determine license type
        if business_account.license_status == 'trial':
            plan['target_license_type'] = 'trial'
        elif business_account.license_status == 'active':
            plan['target_license_type'] = 'standard'  # Default assumption
        else:
            plan['target_license_type'] = 'trial'  # Fallback
            plan['migration_notes'].append(f"Unknown license_status '{business_account.license_status}', defaulting to trial")
        
        # Handle activation date
        if business_account.license_activated_at:
            plan['target_activated_at'] = business_account.license_activated_at.isoformat()
        else:
            plan['target_activated_at'] = business_account.created_at.isoformat()
            plan['migration_notes'].append("license_activated_at was null, using account creation date")
        
        # Handle expiration date
        if business_account.license_expires_at:
            plan['target_expires_at'] = business_account.license_expires_at.isoformat()
        else:
            # Calculate 1 year from activation
            activation_date = business_account.license_activated_at or business_account.created_at
            expires_date = activation_date + timedelta(days=365)
            plan['target_expires_at'] = expires_date.isoformat()
            plan['migration_notes'].append("license_expires_at was null, calculated as 1 year from activation")
        
        # Determine current status
        now = datetime.utcnow()
        expires_date = datetime.fromisoformat(plan['target_expires_at'].replace('Z', '+00:00')) if plan['target_expires_at'].endswith('Z') else datetime.fromisoformat(plan['target_expires_at'])
        
        if business_account.license_status == 'expired' or now > expires_date:
            plan['target_status'] = 'expired'
        else:
            plan['target_status'] = 'active'
        
        return plan


class LicenseDataMigrator:
    """Main migration class with comprehensive validation and safety measures"""
    
    def __init__(self, dry_run: bool = False, force: bool = False, debug: bool = False):
        self.dry_run = dry_run
        self.force = force
        self.debug = debug
        
        # Configure logging
        self._setup_logging()
        
        self.logger = logging.getLogger(__name__)
        self.validator = LicenseMigrationValidator()
        
        # Migration statistics
        self.stats = {
            'total_accounts': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'skipped_accounts': 0,
            'validation_errors': 0,
            'validation_warnings': 0
        }
        
        self.migration_results = []
    
    def _setup_logging(self):
        """Configure logging for migration process"""
        log_level = logging.DEBUG if self.debug else logging.INFO
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/license_migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def create_database_backup(self) -> str:
        """Create database backup before migration"""
        self.logger.info("Creating database backup before migration...")
        
        try:
            # Create backup using SQL dump
            backup_filename = f"license_migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            backup_path = os.path.join('backups', backup_filename)
            
            # Create backups directory
            os.makedirs('backups', exist_ok=True)
            
            # For development database, we'll export the relevant tables
            with app.app_context():
                # Export business_accounts table data
                business_accounts = BusinessAccount.query.all()
                backup_data = {
                    'created_at': datetime.utcnow().isoformat(),
                    'migration_version': '1.0',
                    'business_accounts': []
                }
                
                for account in business_accounts:
                    backup_data['business_accounts'].append({
                        'id': account.id,
                        'name': account.name,
                        'account_type': account.account_type,
                        'license_status': account.license_status,
                        'license_activated_at': account.license_activated_at.isoformat() if account.license_activated_at else None,
                        'license_expires_at': account.license_expires_at.isoformat() if account.license_expires_at else None,
                        'created_at': account.created_at.isoformat() if account.created_at else None,
                        'status': account.status
                    })
                
                # Save backup
                with open(backup_path, 'w') as f:
                    json.dump(backup_data, f, indent=2)
                
                self.logger.info(f"Database backup created: {backup_path}")
                return backup_path
                
        except Exception as e:
            self.logger.error(f"Failed to create database backup: {e}")
            raise
    
    def validate_pre_migration(self) -> Tuple[bool, List[Dict]]:
        """Perform comprehensive pre-migration validation"""
        self.logger.info("Starting pre-migration validation...")
        
        validation_results = []
        overall_success = True
        
        with app.app_context():
            # Get all business accounts
            business_accounts = BusinessAccount.query.all()
            self.stats['total_accounts'] = len(business_accounts)
            
            self.logger.info(f"Found {len(business_accounts)} business accounts to validate")
            
            for account in business_accounts:
                self.logger.debug(f"Validating account: {account.name} (ID: {account.id})")
                
                result = self.validator.validate_business_account(account)
                validation_results.append(result)
                
                if result['errors']:
                    overall_success = False
                    self.stats['validation_errors'] += len(result['errors'])
                    self.logger.error(f"Validation errors for {account.name}: {result['errors']}")
                
                if result['warnings']:
                    self.stats['validation_warnings'] += len(result['warnings'])
                    self.logger.warning(f"Validation warnings for {account.name}: {result['warnings']}")
        
        self.logger.info(f"Pre-migration validation complete. Success: {overall_success}")
        self.logger.info(f"Validation stats: {self.stats['validation_errors']} errors, {self.stats['validation_warnings']} warnings")
        
        return overall_success, validation_results
    
    def migrate_business_account(self, business_account: BusinessAccount, migration_plan: Dict) -> Dict:
        """Migrate a single business account to license_history"""
        result = {
            'account_id': business_account.id,
            'account_name': business_account.name,
            'success': False,
            'license_history_id': None,
            'error': None
        }
        
        try:
            # Create license history record using the model's migration method
            license_record = LicenseHistory.migrate_from_business_account(
                business_account, 
                created_by='migration_script_v1.0'
            )
            
            # Verify the record matches our migration plan
            expected_type = migration_plan['target_license_type']
            expected_status = migration_plan['target_status']
            
            if license_record.license_type != expected_type:
                self.logger.warning(f"License type mismatch for {business_account.name}: expected {expected_type}, got {license_record.license_type}")
            
            if license_record.status != expected_status:
                self.logger.warning(f"License status mismatch for {business_account.name}: expected {expected_status}, got {license_record.status}")
            
            if not self.dry_run:
                # Save to database
                db.session.add(license_record)
                db.session.flush()  # Get the ID without committing
                
                result['license_history_id'] = license_record.id
                self.logger.info(f"Created license_history record {license_record.id} for {business_account.name}")
            else:
                self.logger.info(f"DRY RUN: Would create license_history record for {business_account.name}")
            
            result['success'] = True
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Failed to migrate {business_account.name}: {e}")
        
        return result
    
    def perform_migration(self, validation_results: List[Dict]) -> bool:
        """Perform the actual migration process"""
        self.logger.info("Starting license data migration...")
        
        migration_success = True
        
        with app.app_context():
            try:
                # Start database transaction
                db.session.begin()
                
                for validation_result in validation_results:
                    # Skip accounts with validation errors
                    if validation_result['errors']:
                        self.stats['skipped_accounts'] += 1
                        self.logger.warning(f"Skipping {validation_result['account_name']} due to validation errors")
                        continue
                    
                    # Get the business account
                    business_account = BusinessAccount.query.get(validation_result['account_id'])
                    if not business_account:
                        self.logger.error(f"Business account {validation_result['account_id']} not found")
                        self.stats['failed_migrations'] += 1
                        continue
                    
                    # Migrate the account
                    migration_result = self.migrate_business_account(
                        business_account, 
                        validation_result['migration_plan']
                    )
                    
                    self.migration_results.append(migration_result)
                    
                    if migration_result['success']:
                        self.stats['successful_migrations'] += 1
                    else:
                        self.stats['failed_migrations'] += 1
                        migration_success = False
                
                if not self.dry_run and migration_success:
                    # Commit all changes
                    db.session.commit()
                    self.logger.info("Migration transaction committed successfully")
                elif not self.dry_run:
                    # Rollback on failure
                    db.session.rollback()
                    self.logger.error("Migration failed, rolling back transaction")
                else:
                    # Always rollback for dry runs
                    db.session.rollback()
                    self.logger.info("DRY RUN: Transaction rolled back")
                
            except Exception as e:
                if not self.dry_run:
                    db.session.rollback()
                self.logger.error(f"Migration transaction failed: {e}")
                migration_success = False
        
        return migration_success
    
    def validate_post_migration(self) -> bool:
        """Perform post-migration validation"""
        if self.dry_run:
            self.logger.info("Skipping post-migration validation for dry run")
            return True
        
        self.logger.info("Starting post-migration validation...")
        
        validation_success = True
        
        with app.app_context():
            try:
                # Check that all business accounts have license_history records
                business_accounts = BusinessAccount.query.all()
                
                for account in business_accounts:
                    license_histories = LicenseHistory.query.filter_by(business_account_id=account.id).all()
                    
                    if not license_histories:
                        self.logger.error(f"Business account {account.name} has no license_history records")
                        validation_success = False
                    
                    # Check for duplicate active licenses
                    active_licenses = [lh for lh in license_histories if lh.status == 'active']
                    if len(active_licenses) > 1:
                        self.logger.error(f"Business account {account.name} has multiple active licenses")
                        validation_success = False
                    
                    # Verify migration metadata
                    migrated_licenses = [lh for lh in license_histories if lh.migrated_from_business_account]
                    if not migrated_licenses:
                        self.logger.warning(f"Business account {account.name} has no migrated license records")
                
                # Verify foreign key integrity
                orphaned_licenses = db.session.query(LicenseHistory).filter(
                    ~LicenseHistory.business_account_id.in_(
                        db.session.query(BusinessAccount.id)
                    )
                ).count()
                
                if orphaned_licenses > 0:
                    self.logger.error(f"Found {orphaned_licenses} orphaned license_history records")
                    validation_success = False
                
                self.logger.info(f"Post-migration validation complete. Success: {validation_success}")
                
            except Exception as e:
                self.logger.error(f"Post-migration validation failed: {e}")
                validation_success = False
        
        return validation_success
    
    def generate_migration_report(self, validation_results: List[Dict], backup_path: str) -> str:
        """Generate comprehensive migration report"""
        report_filename = f"license_migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join('logs', report_filename)
        
        report_data = {
            'migration_metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0',
                'dry_run': self.dry_run,
                'force': self.force,
                'backup_path': backup_path
            },
            'statistics': self.stats,
            'validation_results': validation_results,
            'migration_results': self.migration_results,
            'summary': {
                'total_accounts_processed': self.stats['total_accounts'],
                'migration_success_rate': (self.stats['successful_migrations'] / max(1, self.stats['total_accounts'])) * 100,
                'overall_success': self.stats['failed_migrations'] == 0 and self.stats['validation_errors'] == 0
            }
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.logger.info(f"Migration report generated: {report_path}")
        return report_path
    
    def run_migration(self) -> bool:
        """Run the complete migration process"""
        try:
            self.logger.info("="*60)
            self.logger.info("LICENSE DATA MIGRATION STARTING")
            self.logger.info("="*60)
            self.logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE MIGRATION'}")
            
            # Step 1: Create backup
            backup_path = self.create_database_backup()
            
            # Step 2: Pre-migration validation
            validation_success, validation_results = self.validate_pre_migration()
            
            if not validation_success and not self.force:
                self.logger.error("Pre-migration validation failed. Use --force to proceed anyway.")
                return False
            
            # Step 3: Confirm migration (unless forced or dry run)
            if not self.dry_run and not self.force:
                print("\n" + "="*60)
                print("MIGRATION CONFIRMATION REQUIRED")
                print("="*60)
                print(f"Total accounts to migrate: {self.stats['total_accounts']}")
                print(f"Validation errors: {self.stats['validation_errors']}")
                print(f"Validation warnings: {self.stats['validation_warnings']}")
                print(f"Backup created: {backup_path}")
                
                confirm = input("\nProceed with migration? (yes/no): ").strip().lower()
                if confirm != 'yes':
                    self.logger.info("Migration cancelled by user")
                    return False
            
            # Step 4: Perform migration
            migration_success = self.perform_migration(validation_results)
            
            # Step 5: Post-migration validation
            post_validation_success = self.validate_post_migration()
            
            # Step 6: Generate report
            report_path = self.generate_migration_report(validation_results, backup_path)
            
            overall_success = migration_success and post_validation_success
            
            self.logger.info("="*60)
            self.logger.info("LICENSE DATA MIGRATION COMPLETE")
            self.logger.info("="*60)
            self.logger.info(f"Overall Success: {overall_success}")
            self.logger.info(f"Statistics: {self.stats}")
            self.logger.info(f"Report: {report_path}")
            self.logger.info(f"Backup: {backup_path}")
            
            return overall_success
            
        except Exception as e:
            self.logger.error(f"Migration process failed: {e}")
            return False


def main():
    """Main entry point for migration script"""
    parser = argparse.ArgumentParser(description='License Data Migration Script')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Perform validation checks without making changes')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompts (use with caution)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable detailed debug logging')
    
    args = parser.parse_args()
    
    # Create migrator and run migration
    migrator = LicenseDataMigrator(
        dry_run=args.dry_run,
        force=args.force,
        debug=args.debug
    )
    
    success = migrator.run_migration()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()