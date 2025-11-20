"""
Database Migration: Add Industry-Specific Topic Hints Fields

This migration adds support for industry-specific AI prompt verticalization:
1. Adds Campaign.industry field (String 100) - allows campaign-specific industry override
2. Adds BusinessAccount.industry_topic_hints field (JSON) - stores custom topic hint overrides

Architecture:
- Platform defaults stored in industry_topic_hints_config.py
- BusinessAccount.industry_topic_hints overrides platform defaults
- Campaign.industry overrides BusinessAccount.industry if set
- Campaign inherits industry from BusinessAccount if not set

Created: November 20, 2025
"""

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add industry topic hints fields"""
    from app import app, db
    from models import Campaign, BusinessAccount
    
    with app.app_context():
        try:
            logger.info("=" * 80)
            logger.info("MIGRATION: Add Industry Topic Hints Fields")
            logger.info("=" * 80)
            
            # Step 1: Check existing columns
            logger.info("\n[Step 1] Checking existing columns...")
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            campaigns_columns = [col['name'] for col in inspector.get_columns('campaigns')]
            business_accounts_columns = [col['name'] for col in inspector.get_columns('business_accounts')]
            
            # Track what needs to be added
            needs_campaign_industry = 'industry' not in campaigns_columns
            needs_ba_industry_hints = 'industry_topic_hints' not in business_accounts_columns
            
            if not needs_campaign_industry and not needs_ba_industry_hints:
                logger.info("✅ All columns already exist. Migration already applied.")
                return True
            
            # Step 2: Add Campaign.industry column
            if needs_campaign_industry:
                logger.info("\n[Step 2] Adding Campaign.industry column...")
                db.session.execute(db.text(
                    "ALTER TABLE campaigns "
                    "ADD COLUMN industry VARCHAR(100)"
                ))
                db.session.execute(db.text(
                    "CREATE INDEX IF NOT EXISTS idx_campaign_industry ON campaigns (industry)"
                ))
                db.session.commit()
                logger.info("✅ Campaign.industry column created with index")
            else:
                logger.info("\n[Step 2] Campaign.industry column already exists, skipping")
            
            # Step 3: Add BusinessAccount.industry_topic_hints column
            if needs_ba_industry_hints:
                logger.info("\n[Step 3] Adding BusinessAccount.industry_topic_hints column...")
                db.session.execute(db.text(
                    "ALTER TABLE business_accounts "
                    "ADD COLUMN industry_topic_hints JSON"
                ))
                db.session.commit()
                logger.info("✅ BusinessAccount.industry_topic_hints column created")
            else:
                logger.info("\n[Step 3] BusinessAccount.industry_topic_hints column already exists, skipping")
            
            # Step 4: Validation
            logger.info("\n[Step 4] Validating migration...")
            
            # Re-inspect to confirm columns were added
            inspector = inspect(db.engine)
            campaigns_columns_after = [col['name'] for col in inspector.get_columns('campaigns')]
            business_accounts_columns_after = [col['name'] for col in inspector.get_columns('business_accounts')]
            
            validation_errors = []
            
            if 'industry' not in campaigns_columns_after:
                validation_errors.append("Campaign.industry column not found after migration")
            
            if 'industry_topic_hints' not in business_accounts_columns_after:
                validation_errors.append("BusinessAccount.industry_topic_hints column not found after migration")
            
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
            logger.info(f"Campaign.industry: {'ADDED' if needs_campaign_industry else 'ALREADY EXISTS'}")
            logger.info(f"BusinessAccount.industry_topic_hints: {'ADDED' if needs_ba_industry_hints else 'ALREADY EXISTS'}")
            logger.info("\n✅ Migration completed successfully!")
            logger.info("=" * 80)
            
            # Step 6: Show current state
            logger.info("\n[Current State]")
            total_campaigns = Campaign.query.count()
            campaigns_with_industry = Campaign.query.filter(Campaign.industry.isnot(None)).count()
            logger.info(f"Total campaigns: {total_campaigns}")
            logger.info(f"Campaigns with industry set: {campaigns_with_industry}")
            
            total_ba = BusinessAccount.query.count()
            ba_with_hints = BusinessAccount.query.filter(BusinessAccount.industry_topic_hints.isnot(None)).count()
            logger.info(f"Total business accounts: {total_ba}")
            logger.info(f"Business accounts with custom hints: {ba_with_hints}")
            
            logger.info("\n📝 Next Steps:")
            logger.info("  1. BusinessAccount.industry field already exists (created in earlier migration)")
            logger.info("  2. UI updates needed for industry topic hints editing")
            logger.info("  3. PromptTemplateService integration to use hints")
            logger.info("  4. Platform defaults available in industry_topic_hints_config.py")
            
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
