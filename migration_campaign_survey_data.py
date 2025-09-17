#!/usr/bin/env python3
"""
Migration Script: Campaign Survey Customization Data Population
Copies survey customization fields from business accounts to their associated campaigns.

Usage:
    python migration_campaign_survey_data.py --test     # Test on first 3 campaigns
    python migration_campaign_survey_data.py --run      # Migrate all campaigns
    python migration_campaign_survey_data.py --status   # Check migration status
"""

import argparse
import json
import logging
from datetime import datetime
from sqlalchemy import text
from app import app, db
from models import Campaign, BusinessAccount

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/campaign_survey_migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CampaignSurveyMigration:
    """Handles migration of survey customization data from business accounts to campaigns"""
    
    # Default fallback values for campaigns without business accounts
    DEFAULT_SURVEY_CONFIG = {
        'product_description': 'Our financial consulting services help businesses optimize their operations and achieve sustainable growth.',
        'target_clients_description': 'Growing businesses and their leadership teams seeking strategic financial guidance.',
        'survey_goals': ["NPS", "Service Quality", "Growth Opportunities"],
        'max_questions': 8,
        'max_duration_seconds': 120,
        'max_follow_ups_per_topic': 2,
        'prioritized_topics': ["NPS", "Service Quality"],
        'optional_topics': ["Growth Opportunities"],
        'custom_end_message': 'Thank you for helping us improve our services!',
        'custom_system_prompt': None
    }
    
    def __init__(self):
        self.processed_count = 0
        self.updated_count = 0
        self.skipped_count = 0
        self.error_count = 0
    
    def get_campaign_status(self, limit=None):
        """Get status of campaigns and their survey customization fields"""
        logger.info("=== Campaign Survey Customization Status ===")
        
        with app.app_context():
            query = """
            SELECT 
                c.id,
                c.name,
                c.business_account_id,
                ba.name as business_account_name,
                CASE WHEN c.product_description IS NOT NULL THEN 'SET' ELSE 'NULL' END as product_desc_status,
                CASE WHEN c.target_clients_description IS NOT NULL THEN 'SET' ELSE 'NULL' END as target_clients_status,
                CASE WHEN c.survey_goals IS NOT NULL THEN 'SET' ELSE 'NULL' END as survey_goals_status,
                CASE WHEN c.custom_end_message IS NOT NULL THEN 'SET' ELSE 'NULL' END as end_message_status
            FROM campaigns c
            LEFT JOIN business_accounts ba ON c.business_account_id = ba.id
            ORDER BY c.id
            """
            
            if limit:
                query += f" LIMIT {limit}"
                
            result = db.session.execute(text(query))
            campaigns = result.fetchall()
            
            logger.info(f"Found {len(campaigns)} campaigns:")
            for campaign in campaigns:
                logger.info(f"  Campaign {campaign[0]}: {campaign[1]}")
                logger.info(f"    Business Account: {campaign[3] or 'None'}")
                logger.info(f"    Status: Product={campaign[4]}, Clients={campaign[5]}, Goals={campaign[6]}, Message={campaign[7]}")
            
            return campaigns
    
    def migrate_campaign_batch(self, campaign_ids, test_mode=False):
        """Migrate survey customization data for a batch of campaigns"""
        logger.info(f"{'[TEST MODE] ' if test_mode else ''}Processing batch of {len(campaign_ids)} campaigns: {campaign_ids}")
        
        with app.app_context():
            for campaign_id in campaign_ids:
                try:
                    self.migrate_single_campaign(campaign_id, test_mode)
                except Exception as e:
                    logger.error(f"Error processing campaign {campaign_id}: {e}")
                    self.error_count += 1
        
        return self.get_batch_summary()
    
    def migrate_single_campaign(self, campaign_id, test_mode=False):
        """Migrate survey customization data for a single campaign"""
        self.processed_count += 1
        
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            logger.warning(f"Campaign {campaign_id} not found")
            self.skipped_count += 1
            return
        
        logger.info(f"Processing Campaign {campaign_id}: {campaign.name}")
        
        # Get source data (business account or defaults)
        source_data = self.get_source_survey_config(campaign)
        
        # Check if migration is needed
        updates_needed = self.get_required_updates(campaign, source_data)
        
        if not updates_needed:
            logger.info(f"  Campaign {campaign_id}: No updates needed (all fields already set)")
            self.skipped_count += 1
            return
        
        # Apply updates
        if test_mode:
            logger.info(f"  [TEST MODE] Would update {len(updates_needed)} fields: {list(updates_needed.keys())}")
            for field, value in updates_needed.items():
                if isinstance(value, list):
                    logger.info(f"    {field}: {json.dumps(value)}")
                else:
                    logger.info(f"    {field}: {value}")
        else:
            self.apply_updates(campaign, updates_needed)
            db.session.commit()
            logger.info(f"  Campaign {campaign_id}: Updated {len(updates_needed)} fields: {list(updates_needed.keys())}")
        
        self.updated_count += 1
    
    def get_source_survey_config(self, campaign):
        """Get survey configuration from business account or defaults"""
        if campaign.business_account_id:
            business_account = BusinessAccount.query.get(campaign.business_account_id)
            if business_account:
                logger.info(f"  Using data from business account: {business_account.name}")
                return {
                    'product_description': business_account.product_description,
                    'target_clients_description': business_account.target_clients_description,
                    'survey_goals': business_account.survey_goals,
                    'max_questions': business_account.max_questions or 8,
                    'max_duration_seconds': business_account.max_duration_seconds or 120,
                    'max_follow_ups_per_topic': business_account.max_follow_ups_per_topic or 2,
                    'prioritized_topics': business_account.prioritized_topics,
                    'optional_topics': business_account.optional_topics,
                    'custom_end_message': business_account.custom_end_message,
                    'custom_system_prompt': business_account.custom_system_prompt
                }
        
        logger.info(f"  Using default survey configuration (no business account)")
        return self.DEFAULT_SURVEY_CONFIG.copy()
    
    def get_required_updates(self, campaign, source_data):
        """Determine which fields need to be updated (only NULL fields)"""
        updates = {}
        
        # Check each field and only update if campaign field is NULL
        if campaign.product_description is None and source_data.get('product_description'):
            updates['product_description'] = source_data['product_description']
        
        if campaign.target_clients_description is None and source_data.get('target_clients_description'):
            updates['target_clients_description'] = source_data['target_clients_description']
        
        if campaign.survey_goals is None and source_data.get('survey_goals'):
            updates['survey_goals'] = source_data['survey_goals']
        
        if campaign.prioritized_topics is None and source_data.get('prioritized_topics'):
            updates['prioritized_topics'] = source_data['prioritized_topics']
        
        if campaign.optional_topics is None and source_data.get('optional_topics'):
            updates['optional_topics'] = source_data['optional_topics']
        
        if campaign.custom_end_message is None and source_data.get('custom_end_message'):
            updates['custom_end_message'] = source_data['custom_end_message']
        
        if campaign.custom_system_prompt is None and source_data.get('custom_system_prompt'):
            updates['custom_system_prompt'] = source_data['custom_system_prompt']
        
        # Handle integer fields with defaults
        if campaign.max_questions is None or campaign.max_questions == 8:  # Only update if not customized
            if source_data.get('max_questions') and source_data['max_questions'] != 8:
                updates['max_questions'] = source_data['max_questions']
        
        if campaign.max_duration_seconds is None or campaign.max_duration_seconds == 120:
            if source_data.get('max_duration_seconds') and source_data['max_duration_seconds'] != 120:
                updates['max_duration_seconds'] = source_data['max_duration_seconds']
        
        if campaign.max_follow_ups_per_topic is None or campaign.max_follow_ups_per_topic == 2:
            if source_data.get('max_follow_ups_per_topic') and source_data['max_follow_ups_per_topic'] != 2:
                updates['max_follow_ups_per_topic'] = source_data['max_follow_ups_per_topic']
        
        return updates
    
    def apply_updates(self, campaign, updates):
        """Apply the updates to the campaign object"""
        for field, value in updates.items():
            setattr(campaign, field, value)
            logger.debug(f"    Set {field} = {value}")
    
    def get_batch_summary(self):
        """Get summary of current batch processing"""
        return {
            'processed': self.processed_count,
            'updated': self.updated_count,
            'skipped': self.skipped_count,
            'errors': self.error_count
        }
    
    def run_full_migration(self, test_mode=False):
        """Run migration on all campaigns"""
        logger.info(f"=== {'TEST MODE: ' if test_mode else ''}Campaign Survey Data Migration ===")
        
        with app.app_context():
            # Get all campaign IDs
            campaigns = Campaign.query.order_by(Campaign.id).all()
            campaign_ids = [c.id for c in campaigns]
            
            logger.info(f"Found {len(campaign_ids)} campaigns to process")
            
            # Process in batches of 10
            batch_size = 10
            for i in range(0, len(campaign_ids), batch_size):
                batch = campaign_ids[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}: campaigns {batch}")
                self.migrate_campaign_batch(batch, test_mode)
        
        # Final summary
        summary = self.get_batch_summary()
        logger.info("=== Migration Summary ===")
        logger.info(f"Processed: {summary['processed']}")
        logger.info(f"Updated: {summary['updated']}")
        logger.info(f"Skipped: {summary['skipped']}")
        logger.info(f"Errors: {summary['errors']}")
        
        return summary


def main():
    parser = argparse.ArgumentParser(description='Migrate campaign survey customization data')
    parser.add_argument('--test', action='store_true', help='Run test migration on first 3 campaigns')
    parser.add_argument('--run', action='store_true', help='Run full migration on all campaigns')
    parser.add_argument('--status', action='store_true', help='Show migration status')
    
    args = parser.parse_args()
    
    migration = CampaignSurveyMigration()
    
    if args.status:
        migration.get_campaign_status()
    elif args.test:
        logger.info("Running test migration on first 3 campaigns")
        with app.app_context():
            campaigns = Campaign.query.order_by(Campaign.id).limit(3).all()
            campaign_ids = [c.id for c in campaigns]
            migration.migrate_campaign_batch(campaign_ids, test_mode=True)
    elif args.run:
        logger.info("Running full migration on all campaigns")
        migration.run_full_migration(test_mode=False)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()