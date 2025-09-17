#!/usr/bin/env python3
"""
License Migration Rollback Script
=================================

This script provides a safe rollback mechanism for the license data migration.
It can restore BusinessAccount license fields from license_history data or
from backup files.

Author: Data Migration Agent
Date: September 17, 2025
Version: 1.0

Usage:
    python rollback_license_migration.py [--backup-file path] [--dry-run] [--force]
    
Options:
    --backup-file    Path to backup file created before migration
    --dry-run        Show what would be restored without making changes
    --force          Skip confirmation prompts
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional

# Add the current directory to Python path to import our models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import BusinessAccount, LicenseHistory


class LicenseRollbackManager:
    """Manager class for rolling back license migration"""
    
    def __init__(self, backup_file: Optional[str] = None, dry_run: bool = False, force: bool = False):
        self.backup_file = backup_file
        self.dry_run = dry_run
        self.force = force
        
        # Configure logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Rollback statistics
        self.stats = {
            'total_accounts': 0,
            'successful_rollbacks': 0,
            'failed_rollbacks': 0,
            'skipped_accounts': 0,
            'license_histories_removed': 0
        }
        
        self.rollback_results = []
    
    def _setup_logging(self):
        """Configure logging for rollback process"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/license_rollback_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def load_backup_data(self) -> Optional[Dict]:
        """Load backup data from file"""
        if not self.backup_file:
            self.logger.info("No backup file specified, will use license_history data for rollback")
            return None
        
        try:
            if not os.path.exists(self.backup_file):
                self.logger.error(f"Backup file not found: {self.backup_file}")
                return None
            
            with open(self.backup_file, 'r') as f:
                backup_data = json.load(f)
            
            self.logger.info(f"Loaded backup data from {self.backup_file}")
            self.logger.info(f"Backup contains {len(backup_data.get('business_accounts', []))} business accounts")
            
            return backup_data
            
        except Exception as e:
            self.logger.error(f"Failed to load backup file: {e}")
            return None
    
    def validate_rollback_safety(self) -> bool:
        """Validate that rollback is safe to perform"""
        self.logger.info("Validating rollback safety...")
        
        validation_success = True
        
        with app.app_context():
            try:
                # Check if license_history table exists and has migrated data
                migrated_licenses = LicenseHistory.query.filter_by(migrated_from_business_account=True).count()
                
                if migrated_licenses == 0:
                    self.logger.warning("No migrated license records found. Migration may not have been performed.")
                    validation_success = False
                else:
                    self.logger.info(f"Found {migrated_licenses} migrated license records")
                
                # Check for existing campaigns that might depend on license_history
                business_accounts = BusinessAccount.query.all()
                total_campaigns = 0
                
                for account in business_accounts:
                    campaign_count = len(account.campaigns.all()) if hasattr(account, 'campaigns') else 0
                    total_campaigns += campaign_count
                
                if total_campaigns > 0:
                    self.logger.warning(f"Found {total_campaigns} existing campaigns. Rolling back license data may affect campaign functionality.")
                
                self.logger.info(f"Rollback safety validation complete. Safe: {validation_success}")
                
            except Exception as e:
                self.logger.error(f"Rollback safety validation failed: {e}")
                validation_success = False
        
        return validation_success
    
    def rollback_from_backup(self, backup_data: Dict) -> bool:
        """Rollback license data from backup file"""
        self.logger.info("Rolling back license data from backup file...")
        
        rollback_success = True
        backup_accounts = backup_data.get('business_accounts', [])
        
        with app.app_context():
            try:
                db.session.begin()
                
                for backup_account in backup_accounts:
                    account_id = backup_account['id']
                    
                    # Find the current business account
                    business_account = BusinessAccount.query.get(account_id)
                    if not business_account:
                        self.logger.warning(f"Business account {account_id} not found, skipping")
                        self.stats['skipped_accounts'] += 1
                        continue
                    
                    # Restore license fields from backup
                    result = self._restore_business_account_from_backup(business_account, backup_account)
                    
                    self.rollback_results.append(result)
                    
                    if result['success']:
                        self.stats['successful_rollbacks'] += 1
                    else:
                        self.stats['failed_rollbacks'] += 1
                        rollback_success = False
                
                if not self.dry_run and rollback_success:
                    db.session.commit()
                    self.logger.info("Rollback transaction committed successfully")
                elif not self.dry_run:
                    db.session.rollback()
                    self.logger.error("Rollback failed, rolling back transaction")
                else:
                    db.session.rollback()
                    self.logger.info("DRY RUN: Transaction rolled back")
                
            except Exception as e:
                if not self.dry_run:
                    db.session.rollback()
                self.logger.error(f"Rollback transaction failed: {e}")
                rollback_success = False
        
        return rollback_success
    
    def rollback_from_license_history(self) -> bool:
        """Rollback license data from existing license_history records"""
        self.logger.info("Rolling back license data from license_history records...")
        
        rollback_success = True
        
        with app.app_context():
            try:
                db.session.begin()
                
                # Get all business accounts with migrated license history
                business_accounts = BusinessAccount.query.all()
                self.stats['total_accounts'] = len(business_accounts)
                
                for business_account in business_accounts:
                    migrated_licenses = LicenseHistory.query.filter_by(
                        business_account_id=business_account.id,
                        migrated_from_business_account=True
                    ).all()
                    
                    if not migrated_licenses:
                        self.logger.info(f"No migrated licenses found for {business_account.name}, skipping")
                        self.stats['skipped_accounts'] += 1
                        continue
                    
                    # Use the most recent migrated license for rollback
                    license_record = migrated_licenses[0]  # They should be ordered by activation date
                    
                    result = self._restore_business_account_from_license_history(business_account, license_record)
                    
                    self.rollback_results.append(result)
                    
                    if result['success']:
                        self.stats['successful_rollbacks'] += 1
                    else:
                        self.stats['failed_rollbacks'] += 1
                        rollback_success = False
                
                if not self.dry_run and rollback_success:
                    db.session.commit()
                    self.logger.info("Rollback transaction committed successfully")
                elif not self.dry_run:
                    db.session.rollback()
                    self.logger.error("Rollback failed, rolling back transaction")
                else:
                    db.session.rollback()
                    self.logger.info("DRY RUN: Transaction rolled back")
                
            except Exception as e:
                if not self.dry_run:
                    db.session.rollback()
                self.logger.error(f"Rollback transaction failed: {e}")
                rollback_success = False
        
        return rollback_success
    
    def _restore_business_account_from_backup(self, business_account: BusinessAccount, backup_data: Dict) -> Dict:
        """Restore a business account from backup data"""
        result = {
            'account_id': business_account.id,
            'account_name': business_account.name,
            'success': False,
            'changes_made': [],
            'error': None
        }
        
        try:
            changes = []
            
            # Restore license_status
            old_status = business_account.license_status
            new_status = backup_data.get('license_status')
            if old_status != new_status:
                if not self.dry_run:
                    business_account.license_status = new_status
                changes.append(f"license_status: {old_status} -> {new_status}")
            
            # Restore license_activated_at
            old_activated = business_account.license_activated_at
            new_activated_str = backup_data.get('license_activated_at')
            new_activated = datetime.fromisoformat(new_activated_str) if new_activated_str else None
            
            if old_activated != new_activated:
                if not self.dry_run:
                    business_account.license_activated_at = new_activated
                changes.append(f"license_activated_at: {old_activated} -> {new_activated}")
            
            # Restore license_expires_at
            old_expires = business_account.license_expires_at
            new_expires_str = backup_data.get('license_expires_at')
            new_expires = datetime.fromisoformat(new_expires_str) if new_expires_str else None
            
            if old_expires != new_expires:
                if not self.dry_run:
                    business_account.license_expires_at = new_expires
                changes.append(f"license_expires_at: {old_expires} -> {new_expires}")
            
            result['changes_made'] = changes
            result['success'] = True
            
            if changes:
                self.logger.info(f"Restored {business_account.name}: {', '.join(changes)}")
            else:
                self.logger.info(f"No changes needed for {business_account.name}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Failed to restore {business_account.name}: {e}")
        
        return result
    
    def _restore_business_account_from_license_history(self, business_account: BusinessAccount, license_record: LicenseHistory) -> Dict:
        """Restore a business account from license_history data"""
        result = {
            'account_id': business_account.id,
            'account_name': business_account.name,
            'success': False,
            'changes_made': [],
            'error': None
        }
        
        try:
            changes = []
            
            # Map license_type back to license_status
            if license_record.license_type == 'trial':
                target_status = 'trial'
            elif license_record.license_type in ['standard', 'premium', 'enterprise']:
                target_status = 'active' if license_record.status == 'active' else 'expired'
            else:
                target_status = 'trial'  # fallback
            
            # Restore license_status
            old_status = business_account.license_status
            if old_status != target_status:
                if not self.dry_run:
                    business_account.license_status = target_status
                changes.append(f"license_status: {old_status} -> {target_status}")
            
            # Restore license_activated_at
            old_activated = business_account.license_activated_at
            new_activated = license_record.activated_at
            if old_activated != new_activated:
                if not self.dry_run:
                    business_account.license_activated_at = new_activated
                changes.append(f"license_activated_at: {old_activated} -> {new_activated}")
            
            # Restore license_expires_at
            old_expires = business_account.license_expires_at
            new_expires = license_record.expires_at
            if old_expires != new_expires:
                if not self.dry_run:
                    business_account.license_expires_at = new_expires
                changes.append(f"license_expires_at: {old_expires} -> {new_expires}")
            
            result['changes_made'] = changes
            result['success'] = True
            
            if changes:
                self.logger.info(f"Restored {business_account.name}: {', '.join(changes)}")
            else:
                self.logger.info(f"No changes needed for {business_account.name}")
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Failed to restore {business_account.name}: {e}")
        
        return result
    
    def remove_migrated_license_history(self) -> bool:
        """Remove license_history records created by migration"""
        if self.dry_run:
            self.logger.info("DRY RUN: Would remove migrated license_history records")
            return True
        
        self.logger.info("Removing migrated license_history records...")
        
        try:
            with app.app_context():
                # Find and remove all migrated license history records
                migrated_licenses = LicenseHistory.query.filter_by(migrated_from_business_account=True).all()
                
                self.stats['license_histories_removed'] = len(migrated_licenses)
                
                for license_record in migrated_licenses:
                    self.logger.debug(f"Removing license_history record {license_record.id} for {license_record.business_account.name}")
                    db.session.delete(license_record)
                
                db.session.commit()
                self.logger.info(f"Removed {len(migrated_licenses)} migrated license_history records")
                
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove migrated license_history records: {e}")
            return False
    
    def generate_rollback_report(self) -> str:
        """Generate rollback report"""
        report_filename = f"license_rollback_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join('logs', report_filename)
        
        report_data = {
            'rollback_metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'backup_file': self.backup_file,
                'dry_run': self.dry_run,
                'force': self.force
            },
            'statistics': self.stats,
            'rollback_results': self.rollback_results,
            'summary': {
                'total_accounts_processed': self.stats['total_accounts'],
                'rollback_success_rate': (self.stats['successful_rollbacks'] / max(1, self.stats['total_accounts'])) * 100,
                'overall_success': self.stats['failed_rollbacks'] == 0
            }
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.logger.info(f"Rollback report generated: {report_path}")
        return report_path
    
    def run_rollback(self) -> bool:
        """Run the complete rollback process"""
        try:
            self.logger.info("="*60)
            self.logger.info("LICENSE MIGRATION ROLLBACK STARTING")
            self.logger.info("="*60)
            self.logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE ROLLBACK'}")
            
            # Step 1: Validate rollback safety
            if not self.validate_rollback_safety() and not self.force:
                self.logger.error("Rollback safety validation failed. Use --force to proceed anyway.")
                return False
            
            # Step 2: Load backup data if specified
            backup_data = self.load_backup_data()
            
            # Step 3: Confirm rollback (unless forced or dry run)
            if not self.dry_run and not self.force:
                print("\n" + "="*60)
                print("ROLLBACK CONFIRMATION REQUIRED")
                print("="*60)
                print(f"Rollback method: {'From backup file' if backup_data else 'From license_history'}")
                if backup_data:
                    print(f"Backup file: {self.backup_file}")
                    print(f"Backup accounts: {len(backup_data.get('business_accounts', []))}")
                
                confirm = input("\nProceed with rollback? (yes/no): ").strip().lower()
                if confirm != 'yes':
                    self.logger.info("Rollback cancelled by user")
                    return False
            
            # Step 4: Perform rollback
            if backup_data:
                rollback_success = self.rollback_from_backup(backup_data)
            else:
                rollback_success = self.rollback_from_license_history()
            
            # Step 5: Remove migrated license_history records (if successful)
            if rollback_success:
                remove_success = self.remove_migrated_license_history()
                rollback_success = rollback_success and remove_success
            
            # Step 6: Generate report
            report_path = self.generate_rollback_report()
            
            self.logger.info("="*60)
            self.logger.info("LICENSE MIGRATION ROLLBACK COMPLETE")
            self.logger.info("="*60)
            self.logger.info(f"Overall Success: {rollback_success}")
            self.logger.info(f"Statistics: {self.stats}")
            self.logger.info(f"Report: {report_path}")
            
            return rollback_success
            
        except Exception as e:
            self.logger.error(f"Rollback process failed: {e}")
            return False


def main():
    """Main entry point for rollback script"""
    parser = argparse.ArgumentParser(description='License Migration Rollback Script')
    parser.add_argument('--backup-file', type=str,
                       help='Path to backup file created before migration')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be restored without making changes')
    parser.add_argument('--force', action='store_true',
                       help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    # Create rollback manager and run rollback
    rollback_manager = LicenseRollbackManager(
        backup_file=args.backup_file,
        dry_run=args.dry_run,
        force=args.force
    )
    
    success = rollback_manager.run_rollback()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()