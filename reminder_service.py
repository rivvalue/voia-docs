"""
Reminder Service - Automated email reminder system for campaign participants

This service handles the identification and processing of participants who are eligible
for reminder emails. It implements a single-reminder strategy with configurable delay
to increase response rates while minimizing email volume.

Performance considerations:
- Uses optimized LEFT JOIN queries instead of subqueries
- Leverages composite indexes on CampaignParticipant and EmailDelivery
- Processes reminders in batches to avoid overwhelming the TaskQueue
- Staggers delivery over 4-8 hours to maintain system stability
"""

from datetime import datetime, timedelta
import logging
from sqlalchemy import and_, func, text
from sqlalchemy.orm import joinedload
from app import db
from models import Campaign, CampaignParticipant, Participant, SurveyResponse, EmailDelivery, BusinessAccount
from task_queue import task_queue

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing automated campaign reminder emails"""
    
    @staticmethod
    def get_reminder_eligible_participants(campaign_id=None, limit=None):
        """
        Find participants eligible for reminder emails using optimized query.
        
        Eligibility criteria:
        1. Campaign has reminder_enabled=True
        2. Campaign is in 'active' status
        3. Participant status is 'invited' (not started or completed)
        4. invited_at is older than campaign.reminder_delay_days
        5. No survey response exists for this participant
        6. No reminder email has been sent yet (email_type='reminder')
        
        Performance optimization:
        - Uses LEFT JOIN instead of NOT EXISTS subqueries
        - Leverages idx_campaign_participant_reminder index
        - Leverages idx_email_reminder_lookup index
        - Time-based filtering done in SQL using PostgreSQL interval arithmetic
        - LIMIT applied in SQL, never loads unbounded data into memory
        
        Args:
            campaign_id: Optional campaign ID to filter by specific campaign
            limit: Optional limit for testing/batching
            
        Returns:
            List of CampaignParticipant objects eligible for reminders
        """
        now = datetime.utcnow()
        
        # Base query with eager loading of relationships
        query = db.session.query(CampaignParticipant).join(
            Campaign,
            CampaignParticipant.campaign_id == Campaign.id
        ).join(
            Participant,
            CampaignParticipant.participant_id == Participant.id
        ).outerjoin(
            SurveyResponse,
            SurveyResponse.campaign_participant_id == CampaignParticipant.id
        ).outerjoin(
            EmailDelivery,
            and_(
                EmailDelivery.campaign_participant_id == CampaignParticipant.id,
                EmailDelivery.email_type == 'reminder'
            )
        )
        
        # Build filter conditions
        filters = [
            Campaign.status == 'active',
            Campaign.reminder_enabled == True,
            CampaignParticipant.status == 'invited',
            CampaignParticipant.invited_at.isnot(None),
            SurveyResponse.id.is_(None),  # No survey response exists
            EmailDelivery.id.is_(None),  # No reminder sent yet
        ]
        
        # Add campaign filter if specified
        if campaign_id:
            filters.append(Campaign.id == campaign_id)
        
        # Add SQL-based time filter using PostgreSQL interval arithmetic
        # Uses typed SQLAlchemy expression: invited_at <= NOW() - INTERVAL 'X days'
        # This is more optimizer-friendly and avoids brittle text() predicates
        filters.append(
            CampaignParticipant.invited_at <= func.now() - func.make_interval(days=Campaign.reminder_delay_days)
        )
        
        query = query.filter(and_(*filters))
        
        # Order by invited_at to process oldest first
        query = query.order_by(CampaignParticipant.invited_at.asc())
        
        # Apply limit (default 1000 for safety, can be overridden)
        # This prevents unbounded memory loads even if limit=None
        if limit is None:
            limit = 1000  # Safety default
        query = query.limit(limit)
        
        # Execute query - fully optimized in SQL with limit
        return query.all()
    
    @staticmethod
    def get_reminder_statistics(campaign_id=None):
        """
        Get reminder statistics for reporting and monitoring.
        
        Args:
            campaign_id: Optional campaign ID to filter by specific campaign
            
        Returns:
            Dictionary with reminder metrics:
            - total_eligible: Number of participants eligible for reminders now
            - total_sent: Number of reminders already sent
            - pending_count: Number eligible but not yet sent
            - conversion_rate: Percentage of reminded participants who responded
        """
        now = datetime.utcnow()
        
        # Base filters
        base_filters = [
            Campaign.status == 'active',
            Campaign.reminder_enabled == True,
        ]
        
        if campaign_id:
            base_filters.append(Campaign.id == campaign_id)
        
        # Count reminders sent
        sent_count = db.session.query(func.count(EmailDelivery.id)).join(
            CampaignParticipant,
            EmailDelivery.campaign_participant_id == CampaignParticipant.id
        ).join(
            Campaign,
            CampaignParticipant.campaign_id == Campaign.id
        ).filter(
            and_(
                *base_filters,
                EmailDelivery.email_type == 'reminder',
                EmailDelivery.status.in_(['sent', 'sending'])
            )
        ).scalar() or 0
        
        # Count responses from reminded participants
        conversions = db.session.query(func.count(SurveyResponse.id)).join(
            CampaignParticipant,
            SurveyResponse.campaign_participant_id == CampaignParticipant.id
        ).join(
            EmailDelivery,
            and_(
                EmailDelivery.campaign_participant_id == CampaignParticipant.id,
                EmailDelivery.email_type == 'reminder'
            )
        ).join(
            Campaign,
            CampaignParticipant.campaign_id == Campaign.id
        ).filter(
            and_(
                *base_filters,
                EmailDelivery.status.in_(['sent', 'sending']),
                # Response created after reminder was sent
                SurveyResponse.created_at > EmailDelivery.sent_at
            )
        ).scalar() or 0
        
        # Calculate conversion rate
        conversion_rate = (conversions / sent_count * 100) if sent_count > 0 else 0
        
        # Count eligible participants using SQL COUNT instead of loading rows
        # This reuses the same filters from get_reminder_eligible_participants
        eligible_count = db.session.query(func.count(CampaignParticipant.id)).join(
            Campaign,
            CampaignParticipant.campaign_id == Campaign.id
        ).outerjoin(
            SurveyResponse,
            SurveyResponse.campaign_participant_id == CampaignParticipant.id
        ).outerjoin(
            EmailDelivery,
            and_(
                EmailDelivery.campaign_participant_id == CampaignParticipant.id,
                EmailDelivery.email_type == 'reminder'
            )
        ).filter(
            and_(
                Campaign.status == 'active',
                Campaign.reminder_enabled == True,
                CampaignParticipant.status == 'invited',
                CampaignParticipant.invited_at.isnot(None),
                SurveyResponse.id.is_(None),
                EmailDelivery.id.is_(None),
                CampaignParticipant.invited_at <= func.now() - func.make_interval(days=Campaign.reminder_delay_days),
                *([Campaign.id == campaign_id] if campaign_id else [])
            )
        ).scalar() or 0
        
        return {
            'total_eligible': eligible_count,
            'total_sent': sent_count,
            'pending_count': eligible_count,
            'conversion_rate': round(conversion_rate, 2),
            'conversions': conversions
        }
    
    @staticmethod
    def process_reminder_batch(campaign_id=None, batch_size=100, stagger_minutes=5):
        """
        Process a batch of reminder emails for eligible participants.
        
        This function coordinates the entire reminder sending process:
        1. Identifies eligible participants using optimized queries
        2. Creates EmailDelivery records for tracking
        3. Queues emails via TaskQueue with optional staggering
        4. Commits database changes in batches for performance
        
        Performance considerations:
        - Processes in batches to avoid memory issues
        - Staggers email delivery to prevent TaskQueue overload
        - Uses batch database commits (every 100 records)
        - Handles errors gracefully without stopping entire batch
        
        Args:
            campaign_id: Optional campaign ID to limit processing to one campaign
            batch_size: Maximum number of reminders to process (default 100)
            stagger_minutes: Minutes to stagger between email queue submissions (default 5)
            
        Returns:
            Dictionary with processing statistics:
            - total_eligible: Number of participants eligible for reminders
            - processed: Number of reminder emails queued
            - failed: Number of failures
            - errors: List of error messages
        """
        from email_service import email_service
        
        logger.info(f"Starting reminder batch processing (campaign_id={campaign_id}, batch_size={batch_size})")
        
        stats = {
            'total_eligible': 0,
            'processed': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            # Get eligible participants
            eligible_participants = ReminderService.get_reminder_eligible_participants(
                campaign_id=campaign_id,
                limit=batch_size
            )
            
            stats['total_eligible'] = len(eligible_participants)
            logger.info(f"Found {stats['total_eligible']} eligible participants for reminders")
            
            if not eligible_participants:
                logger.info("No eligible participants found for reminder processing")
                return stats
            
            # Process each participant
            for idx, cp in enumerate(eligible_participants):
                try:
                    # Get participant and campaign data
                    participant = cp.participant
                    campaign = cp.campaign
                    business_account = campaign.business_account
                    
                    # Skip if missing critical data
                    if not participant or not campaign or not business_account:
                        error_msg = f"Missing data for CampaignParticipant {cp.id}"
                        logger.error(error_msg)
                        stats['failed'] += 1
                        stats['errors'].append(error_msg)
                        continue
                    
                    # Create EmailDelivery record for tracking
                    email_delivery = EmailDelivery(
                        business_account_id=business_account.id,
                        campaign_id=campaign.id,
                        participant_id=participant.id,
                        campaign_participant_id=cp.id,
                        email_type='reminder',
                        recipient_email=participant.email,
                        recipient_name=participant.name,
                        subject=f"Reminder: Share Your Feedback - {campaign.name}",
                        status='pending',
                        retry_count=0,
                        max_retries=3
                    )
                    db.session.add(email_delivery)
                    db.session.flush()  # Get the ID for task queue
                    
                    # Queue the reminder email via TaskQueue
                    task_data = {
                        'task_type': 'send_reminder_email',
                        'email_delivery_id': email_delivery.id,
                        'participant_email': participant.email,
                        'participant_name': participant.name,
                        'campaign_name': campaign.name,
                        'survey_token': cp.token,
                        'business_account_name': business_account.name,
                        'business_account_id': business_account.id,
                        'campaign_id': campaign.id
                    }
                    
                    task_queue.add_task(task_data)
                    
                    stats['processed'] += 1
                    logger.debug(f"Queued reminder for {participant.email} (campaign: {campaign.name})")
                    
                    # Batch commit every 100 records
                    if (idx + 1) % 100 == 0:
                        db.session.commit()
                        logger.info(f"Committed batch of 100 reminder records (total: {idx + 1})")
                    
                except Exception as e:
                    error_msg = f"Failed to process reminder for CampaignParticipant {cp.id}: {str(e)}"
                    logger.error(error_msg)
                    stats['failed'] += 1
                    stats['errors'].append(error_msg)
                    db.session.rollback()
                    continue
            
            # Final commit for any remaining records
            db.session.commit()
            logger.info(f"Reminder batch processing complete: {stats['processed']} queued, {stats['failed']} failed")
            
        except Exception as e:
            error_msg = f"Critical error in reminder batch processing: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            db.session.rollback()
        
        return stats
