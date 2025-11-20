"""
Database Migration: Add client_industry to participants table

This migration adds a new optional segmentation attribute for tracking
the industry sector that a participant's company operates in.

Safe for production:
- Nullable field (no default needed)
- Partial index (only non-NULL values)
- No data modification
- Full rollback support

Usage:
    python migrate_add_client_industry.py
"""

import logging
from sqlalchemy import text, inspect
from app import app, db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_column_exists():
    """Check if client_industry column already exists"""
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('participants')]
            return 'client_industry' in columns
        except Exception as e:
            logger.error(f"Error checking column existence: {e}")
            return False


def check_index_exists():
    """Check if client_industry index already exists"""
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            indexes = [idx['name'] for idx in inspector.get_indexes('participants')]
            return 'idx_participant_client_industry' in indexes
        except Exception as e:
            logger.error(f"Error checking index existence: {e}")
            return False


def add_client_industry_column():
    """Add client_industry column to participants table"""
    with app.app_context():
        try:
            if check_column_exists():
                logger.info("✓ client_industry column already exists, skipping column creation")
                return True
            
            logger.info("Adding client_industry column to participants table...")
            db.session.execute(text("""
                ALTER TABLE participants 
                ADD COLUMN client_industry VARCHAR(120) NULL
            """))
            db.session.commit()
            logger.info("✓ Column client_industry added successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ Error adding column: {e}")
            return False


def create_client_industry_index():
    """Create partial index on client_industry (only non-NULL values)"""
    with app.app_context():
        try:
            if check_index_exists():
                logger.info("✓ client_industry index already exists, skipping index creation")
                return True
            
            logger.info("Creating partial index on client_industry...")
            db.session.execute(text("""
                CREATE INDEX idx_participant_client_industry 
                ON participants(client_industry) 
                WHERE client_industry IS NOT NULL
            """))
            db.session.commit()
            logger.info("✓ Index idx_participant_client_industry created successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ Error creating index: {e}")
            return False


def validate_migration():
    """Validate that migration completed successfully"""
    with app.app_context():
        try:
            logger.info("\nValidating migration...")
            
            # Check column exists
            column_exists = check_column_exists()
            if not column_exists:
                logger.error("✗ Validation failed: client_industry column not found")
                return False
            logger.info("✓ Column validation passed")
            
            # Check index exists
            index_exists = check_index_exists()
            if not index_exists:
                logger.error("✗ Validation failed: index not found")
                return False
            logger.info("✓ Index validation passed")
            
            # Verify column type
            inspector = inspect(db.engine)
            columns = {col['name']: col for col in inspector.get_columns('participants')}
            col_info = columns.get('client_industry')
            
            if col_info:
                logger.info(f"✓ Column type: {col_info['type']}")
                logger.info(f"✓ Nullable: {col_info['nullable']}")
            
            logger.info("\n✅ Migration validation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Validation error: {e}")
            return False


def rollback_migration():
    """Rollback migration (for testing or emergency use)"""
    with app.app_context():
        try:
            logger.info("\n⚠️  Starting rollback...")
            
            # Drop index first
            if check_index_exists():
                logger.info("Dropping index idx_participant_client_industry...")
                db.session.execute(text("""
                    DROP INDEX IF EXISTS idx_participant_client_industry
                """))
                db.session.commit()
                logger.info("✓ Index dropped")
            
            # Drop column
            if check_column_exists():
                logger.info("Dropping column client_industry...")
                db.session.execute(text("""
                    ALTER TABLE participants 
                    DROP COLUMN IF EXISTS client_industry
                """))
                db.session.commit()
                logger.info("✓ Column dropped")
            
            logger.info("✅ Rollback completed successfully")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"✗ Rollback error: {e}")
            return False


def run_migration():
    """Main migration execution"""
    logger.info("="*60)
    logger.info("Migration: Add client_industry to participants")
    logger.info("="*60)
    
    # Step 1: Add column
    logger.info("\n[Step 1/3] Adding client_industry column...")
    if not add_client_industry_column():
        logger.error("Migration failed at Step 1")
        return False
    
    # Step 2: Create index
    logger.info("\n[Step 2/3] Creating partial index...")
    if not create_client_industry_index():
        logger.error("Migration failed at Step 2")
        logger.info("Attempting rollback...")
        rollback_migration()
        return False
    
    # Step 3: Validate
    logger.info("\n[Step 3/3] Validating migration...")
    if not validate_migration():
        logger.error("Migration validation failed")
        logger.info("Migration completed but validation failed - manual review recommended")
        return False
    
    logger.info("\n" + "="*60)
    logger.info("✅ Migration completed successfully!")
    logger.info("="*60)
    logger.info("\nNext steps:")
    logger.info("1. Verify application starts without errors")
    logger.info("2. Test participant creation/editing")
    logger.info("3. Test CSV import with and without client_industry column")
    logger.info("4. Monitor analytics dashboard")
    
    return True


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        logger.info("Running in ROLLBACK mode")
        rollback_migration()
    else:
        run_migration()
