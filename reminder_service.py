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
from sqlalchemy import and_, func
from sqlalchemy.orm import joinedload
from app import db
from models import Campaign, CampaignParticipant, Participant, SurveyResponse, EmailDelivery


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
        - Time-based filtering done in Python for campaign-specific delays
        
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
        
        query = query.filter(and_(*filters))
        
        # Order by invited_at to process oldest first
        query = query.order_by(CampaignParticipant.invited_at.asc())
        
        # Fetch candidates and filter by campaign-specific delay in Python
        candidates = query.all()
        
        eligible = []
        for cp in candidates:
            # Check if enough time has passed based on campaign's reminder_delay_days
            delay_threshold = cp.invited_at + timedelta(days=cp.campaign.reminder_delay_days)
            if now >= delay_threshold:
                eligible.append(cp)
                
                # Check limit
                if limit and len(eligible) >= limit:
                    break
        
        return eligible
    
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
        
        # Get currently eligible count (for pending)
        eligible_count = len(ReminderService.get_reminder_eligible_participants(campaign_id=campaign_id))
        
        return {
            'total_eligible': eligible_count,
            'total_sent': sent_count,
            'pending_count': eligible_count,
            'conversion_rate': round(conversion_rate, 2),
            'conversions': conversions
        }
