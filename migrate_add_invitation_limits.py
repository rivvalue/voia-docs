"""
Database Migration: Add max_invitations_per_campaign column to LicenseHistory table

This migration:
1. Adds the max_invitations_per_campaign column
2. Backfills existing licenses with max_invitations_per_campaign = max_participants_per_campaign * 5
3. Validates the migration results

Created: October 20, 2025
"""

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add and backfill max_invitations_per_campaign"""
    from app import app, db
    from models import LicenseHistory
    
    with app.app_context():
        try:
            logger.info("=" * 80)
            logger.info("MIGRATION: Add max_invitations_per_campaign column")
            logger.info("=" * 80)
            
            # Step 1: Check if column already exists
            logger.info("\n[Step 1] Checking if column exists...")
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('license_history')]
            
            if 'max_invitations_per_campaign' in columns:
                logger.warning("Column 'max_invitations_per_campaign' already exists!")
                logger.info("Checking for NULL values that need backfilling...")
            else:
                logger.info("Column does not exist. Creating...")
                
                # Create the column with a default value
                db.session.execute(db.text(
                    "ALTER TABLE license_history "
                    "ADD COLUMN max_invitations_per_campaign INTEGER NOT NULL DEFAULT 2500"
                ))
                db.session.commit()
                logger.info("✅ Column created successfully with default value 2500")
            
            # Step 2: Count licenses needing backfill
            logger.info("\n[Step 2] Counting licenses that need backfilling...")
            total_licenses = LicenseHistory.query.count()
            logger.info(f"Total licenses in database: {total_licenses}")
            
            # Step 3: Backfill existing licenses
            logger.info("\n[Step 3] Backfilling existing licenses...")
            logger.info("Formula: max_invitations_per_campaign = max_participants_per_campaign * 5")
            
            licenses = LicenseHistory.query.all()
            updated_count = 0
            
            for license in licenses:
                # Calculate the 5x multiplier
                target_invitations = license.max_participants_per_campaign * 5
                
                # Only update if current value is the default or significantly different
                if (license.max_invitations_per_campaign == 2500 or 
                    license.max_invitations_per_campaign != target_invitations):
                    
                    old_value = license.max_invitations_per_campaign
                    license.max_invitations_per_campaign = target_invitations
                    updated_count += 1
                    
                    logger.info(
                        f"  License ID {license.id} ({license.license_type}): "
                        f"{old_value} → {target_invitations}"
                    )
            
            db.session.commit()
            logger.info(f"\n✅ Updated {updated_count} out of {total_licenses} licenses")
            
            # Step 4: Validation
            logger.info("\n[Step 4] Validating migration...")
            validation_errors = []
            
            for license in LicenseHistory.query.all():
                # Validate: max_invitations >= max_participants
                if license.max_invitations_per_campaign < license.max_participants_per_campaign:
                    validation_errors.append(
                        f"License ID {license.id}: "
                        f"invitations ({license.max_invitations_per_campaign}) < "
                        f"participants ({license.max_participants_per_campaign})"
                    )
                
                # Validate: positive values
                if license.max_invitations_per_campaign <= 0:
                    validation_errors.append(
                        f"License ID {license.id}: "
                        f"invitations value is not positive ({license.max_invitations_per_campaign})"
                    )
            
            if validation_errors:
                logger.error("\n❌ VALIDATION FAILED:")
                for error in validation_errors:
                    logger.error(f"  - {error}")
                raise ValueError("Migration validation failed")
            else:
                logger.info("✅ All validations passed!")
            
            # Step 5: Summary
            logger.info("\n" + "=" * 80)
            logger.info("MIGRATION SUMMARY")
            logger.info("=" * 80)
            logger.info(f"Total licenses: {total_licenses}")
            logger.info(f"Updated: {updated_count}")
            logger.info(f"Validation errors: {len(validation_errors)}")
            logger.info("\n✅ Migration completed successfully!")
            logger.info("=" * 80)
            
            # Step 6: Show sample results
            logger.info("\n[Sample Results] First 5 licenses after migration:")
            sample_licenses = LicenseHistory.query.limit(5).all()
            for license in sample_licenses:
                logger.info(
                    f"  ID {license.id} | {license.license_type:8} | "
                    f"Target: {license.max_participants_per_campaign:5} | "
                    f"Invitations: {license.max_invitations_per_campaign:5} | "
                    f"Status: {license.status}"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"\n❌ Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    try:
        run_migration()
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        exit(1)
