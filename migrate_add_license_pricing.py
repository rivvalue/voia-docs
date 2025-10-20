"""
Database Migration: Add License Pricing
Created: October 20, 2025

This migration adds the annual_price column to the license_history table
and backfills existing licenses with pricing based on their license type.

Pricing structure:
- Core: $8,000/year
- Plus: $12,000/year
- Pro: NULL (custom pricing)
- Trial: NULL (no cost)
"""

from app import app, db
from models import LicenseHistory
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_pricing_column():
    """Add annual_price column to license_history table"""
    with app.app_context():
        try:
            # Check if column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='license_history' 
                AND column_name='annual_price'
            """)).fetchone()
            
            if result:
                logger.info("✓ Column annual_price already exists in license_history table")
                return True
            
            # Add the column
            logger.info("Adding annual_price column to license_history table...")
            db.session.execute(text("""
                ALTER TABLE license_history 
                ADD COLUMN annual_price NUMERIC(10, 2) NULL
            """))
            db.session.commit()
            logger.info("✓ Column annual_price added successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ Error adding column: {e}")
            return False

def backfill_pricing():
    """Backfill pricing data for existing licenses"""
    with app.app_context():
        try:
            # Define pricing for each license type
            pricing_map = {
                'core': 8000.00,
                'plus': 12000.00,
                'pro': None,  # Custom pricing
                'trial': None  # No cost
            }
            
            logger.info("Backfilling pricing data...")
            
            # Get all licenses
            licenses = LicenseHistory.query.all()
            total_licenses = len(licenses)
            logger.info(f"Found {total_licenses} license records to update")
            
            updated_count = 0
            skipped_count = 0
            
            for license in licenses:
                license_type = license.license_type.lower()
                
                # Skip if already has pricing
                if license.annual_price is not None:
                    skipped_count += 1
                    continue
                
                # Set pricing based on type
                if license_type in pricing_map:
                    license.annual_price = pricing_map[license_type]
                    updated_count += 1
                    logger.debug(f"  License ID {license.id} ({license_type}): ${pricing_map[license_type] or 'NULL'}")
                else:
                    logger.warning(f"  Unknown license type: {license_type} for license ID {license.id}")
                    skipped_count += 1
            
            # Commit changes
            db.session.commit()
            
            logger.info("=" * 60)
            logger.info("BACKFILL SUMMARY:")
            logger.info(f"  Total licenses: {total_licenses}")
            logger.info(f"  Updated: {updated_count}")
            logger.info(f"  Skipped (already had pricing): {skipped_count}")
            logger.info("=" * 60)
            
            # Show pricing breakdown
            core_count = LicenseHistory.query.filter_by(license_type='core').filter(LicenseHistory.annual_price == 8000.00).count()
            plus_count = LicenseHistory.query.filter_by(license_type='plus').filter(LicenseHistory.annual_price == 12000.00).count()
            pro_count = LicenseHistory.query.filter_by(license_type='pro').count()
            trial_count = LicenseHistory.query.filter_by(license_type='trial').count()
            
            logger.info("PRICING BREAKDOWN:")
            logger.info(f"  Core licenses ($8,000): {core_count}")
            logger.info(f"  Plus licenses ($12,000): {plus_count}")
            logger.info(f"  Pro licenses (custom): {pro_count}")
            logger.info(f"  Trial licenses (free): {trial_count}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ Error backfilling pricing: {e}")
            import traceback
            traceback.print_exc()
            return False

def verify_migration():
    """Verify the migration was successful"""
    with app.app_context():
        try:
            logger.info("Verifying migration...")
            
            # Check column exists
            result = db.session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name='license_history' 
                AND column_name='annual_price'
            """)).fetchone()
            
            if not result:
                logger.error("✗ Column annual_price not found!")
                return False
            
            logger.info(f"✓ Column exists: {result[0]} ({result[1]})")
            
            # Check pricing data
            core_with_price = LicenseHistory.query.filter_by(license_type='core').filter(LicenseHistory.annual_price != None).count()
            plus_with_price = LicenseHistory.query.filter_by(license_type='plus').filter(LicenseHistory.annual_price != None).count()
            
            logger.info(f"✓ Core licenses with pricing: {core_with_price}")
            logger.info(f"✓ Plus licenses with pricing: {plus_with_price}")
            
            # Sample a few records
            sample_licenses = LicenseHistory.query.limit(5).all()
            logger.info("\nSample license records:")
            for lic in sample_licenses:
                price_str = f"${lic.annual_price:,.2f}" if lic.annual_price else "NULL"
                logger.info(f"  ID {lic.id}: {lic.license_type} - {price_str}")
            
            logger.info("\n✓ Migration verified successfully!")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error verifying migration: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Run the complete migration"""
    logger.info("=" * 60)
    logger.info("LICENSE PRICING MIGRATION")
    logger.info("=" * 60)
    
    # Step 1: Add column
    if not add_pricing_column():
        logger.error("Migration failed at step 1 (add column)")
        return False
    
    # Step 2: Backfill data
    if not backfill_pricing():
        logger.error("Migration failed at step 2 (backfill)")
        return False
    
    # Step 3: Verify
    if not verify_migration():
        logger.error("Migration verification failed")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("✓ MIGRATION COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
