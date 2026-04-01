from app import db
from datetime import datetime, date, timedelta
from sqlalchemy import or_, and_, func, text, desc
from sqlalchemy.dialects.postgresql import TSVECTOR
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import uuid

class SurveyResponse(db.Model):
    __tablename__ = 'survey_response'
    __table_args__ = (
        # Composite index for efficient business account and campaign filtering
        db.Index('idx_survey_response_business_campaign', 'campaign_id', 'campaign_participant_id'),
        # Index for common queries by email and creation date
        db.Index('idx_survey_response_email_date', 'respondent_email', 'created_at'),
        # Basic index on conversation_history for text search (will use ILIKE in queries)
        db.Index('idx_survey_response_conversation', 'conversation_history'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    company_name = db.Column(db.String(200), nullable=False, index=True)
    respondent_name = db.Column(db.String(200), nullable=False)
    respondent_email = db.Column(db.String(200), nullable=False, index=True)
    tenure_with_fc = db.Column(db.String(50), nullable=True, index=True)  # Business relationship duration with FC inc
    nps_score = db.Column(db.Integer, nullable=False, index=True)
    nps_category = db.Column(db.String(20), nullable=False, index=True)  # Promoter, Passive, Detractor
    
    # Follow-up responses stored as JSON
    satisfaction_rating = db.Column(db.Integer)
    product_value_rating = db.Column(db.Integer)
    service_rating = db.Column(db.Integer)
    pricing_rating = db.Column(db.Integer)
    support_rating = db.Column(db.Integer, nullable=True)
    
    # Text responses
    improvement_feedback = db.Column(db.Text)
    recommendation_reason = db.Column(db.Text)
    additional_comments = db.Column(db.Text)
    
    # New unique feedback fields for topic-specific responses (backend-controlled completion)
    product_quality_feedback = db.Column(db.Text, nullable=True)
    support_experience_feedback = db.Column(db.Text, nullable=True)
    service_rating_feedback = db.Column(db.Text, nullable=True)
    user_experience_feedback = db.Column(db.Text, nullable=True)
    feature_requests = db.Column(db.Text, nullable=True)
    general_feedback = db.Column(db.Text, nullable=True)
    
    # AI Analysis results
    sentiment_score = db.Column(db.Float)
    sentiment_label = db.Column(db.String(50))
    key_themes = db.Column(db.Text)  # JSON string of themes
    churn_risk_score = db.Column(db.Float)
    churn_risk_level = db.Column(db.String(20))  # Minimal, Low, Medium, High
    churn_risk_factors = db.Column(db.Text)  # JSON string
    growth_opportunities = db.Column(db.Text)  # JSON string
    account_risk_factors = db.Column(db.Text)  # JSON string - Account-specific risk factors
    growth_factor = db.Column(db.Float)  # Growth factor from NPS lookup table
    growth_rate = db.Column(db.String(10))  # Expected organic growth rate (e.g., "25%")
    growth_range = db.Column(db.String(20))  # NPS range (e.g., "50-69")
    commercial_value = db.Column(db.Float)  # Commercial value of the client in dollars
    influence_weight = db.Column(db.Float, nullable=True, default=1.0)  # Respondent seniority multiplier (C-level=5, VP/Dir=3, Manager=2, Team Lead=1.5, End User=1)
    
    csat_score = db.Column(db.Integer, nullable=True)  # Customer Satisfaction Score (1-5)
    ces_score = db.Column(db.Integer, nullable=True)  # Customer Effort Score (1-8)
    loyalty_drivers = db.Column(db.JSON, nullable=True)  # JSON array of selected driver keys
    recommendation_status = db.Column(db.String(50), nullable=True)  # 'recommended', 'would_consider', 'would_not_recommend'
    
    # AI-generated summary and reasoning (for transparency and trust)
    analysis_summary = db.Column(db.Text, nullable=True)  # 2-3 sentence plain-language summary of findings
    analysis_reasoning = db.Column(db.Text, nullable=True)  # Explanation of why AI reached these conclusions
    
    # Conversational transcript
    conversation_history = db.Column(db.Text, nullable=True)  # JSON string of conversation transcript
    
    # AI prompts debugging log (JSON array of all prompts sent to OpenAI during conversation)
    ai_prompts_log = db.Column(db.Text, nullable=True)  # For debugging language issues and prompt effectiveness
    
    # Deflection summary (Phase 6, Dec 2025)
    # JSON storing topic status with deflection metadata for analytics
    # Structure: {"total_topics": N, "completed": N, "skipped": N, "deflections": [...]}
    deflection_summary = db.Column(db.Text, nullable=True)
    
    # Full-text search vector (automatically maintained by PostgreSQL trigger)
    conversation_search = db.Column(TSVECTOR, nullable=True)
    
    # Campaign tracking
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=True, index=True)
    
    # Foreign key to CampaignParticipant for proper association tracking
    campaign_participant_id = db.Column(db.Integer, db.ForeignKey('campaign_participants.id'), nullable=True, index=True)
    
    campaign = db.relationship('Campaign', backref=db.backref('responses', lazy='dynamic'))
    campaign_participant = db.relationship('CampaignParticipant', foreign_keys='SurveyResponse.campaign_participant_id', backref='survey_responses')
    
    # Transcript Analysis Fields
    source_type = db.Column(db.String(20), nullable=False, default='conversational', index=True)  # 'conversational', 'traditional', 'transcript'
    transcript_content = db.Column(db.Text, nullable=True)  # Original transcript text for transcript-sourced responses
    transcript_hash = db.Column(db.String(64), nullable=True, index=True)  # SHA-256 hash for duplicate detection
    transcript_filename = db.Column(db.String(255), nullable=True)  # Original filename for download
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow, index=True)
    analyzed_at = db.Column(db.DateTime, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_name': self.company_name,
            'respondent_name': self.respondent_name,
            'respondent_email': self.respondent_email,
            'tenure_with_fc': self.tenure_with_fc,
            'nps_score': self.nps_score,
            'nps_category': self.nps_category,
            'satisfaction_rating': self.satisfaction_rating,
            'product_value_rating': self.product_value_rating,
            'service_rating': self.service_rating,
            'pricing_rating': self.pricing_rating,
            'support_rating': self.support_rating,
            'improvement_feedback': self.improvement_feedback,
            'recommendation_reason': self.recommendation_reason,
            'additional_comments': self.additional_comments,
            'product_quality_feedback': self.product_quality_feedback,
            'support_experience_feedback': self.support_experience_feedback,
            'service_rating_feedback': self.service_rating_feedback,
            'user_experience_feedback': self.user_experience_feedback,
            'feature_requests': self.feature_requests,
            'general_feedback': self.general_feedback,
            'sentiment_score': self.sentiment_score,
            'sentiment_label': self.sentiment_label,
            'key_themes': json.loads(self.key_themes) if self.key_themes else [],
            'churn_risk_score': self.churn_risk_score,
            'churn_risk_level': self.churn_risk_level,
            'churn_risk_factors': json.loads(self.churn_risk_factors) if self.churn_risk_factors else [],
            'growth_opportunities': json.loads(self.growth_opportunities) if self.growth_opportunities else [],
            'account_risk_factors': json.loads(self.account_risk_factors) if self.account_risk_factors else [],
            'growth_factor': self.growth_factor,
            'growth_rate': self.growth_rate,
            'growth_range': self.growth_range,
            'commercial_value': self.commercial_value,
            'influence_weight': self.influence_weight,
            'analysis_summary': self.analysis_summary,
            'analysis_reasoning': self.analysis_reasoning,
            'campaign_id': self.campaign_id,
            'campaign_participant_id': self.campaign_participant_id,
            'campaign_name': self.campaign.name if self.campaign else None,
            'conversation_history': json.loads(self.conversation_history) if self.conversation_history else [],
            'source_type': self.source_type,
            'transcript_filename': self.transcript_filename,
            'deflection_summary': json.loads(self.deflection_summary) if self.deflection_summary else None,
            'csat_score': self.csat_score,
            'ces_score': self.ces_score,
            'loyalty_drivers': self.loyalty_drivers,
            'recommendation_status': self.recommendation_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None
        }
    
    def get_account_risk_factors(self):
        """Parse account risk factors from JSON"""
        if self.account_risk_factors:
            try:
                return json.loads(self.account_risk_factors)
            except:
                return []
        return []


class ActiveConversation(db.Model):
    __tablename__ = 'active_conversations'
    __table_args__ = (
        db.Index('idx_active_conv_last_updated', 'last_updated'),
    )
    
    conversation_id = db.Column(db.String(36), primary_key=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=True, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=True, index=True)
    participant_data = db.Column(db.Text, nullable=True)
    conversation_history = db.Column(db.Text, nullable=False, default='[]')
    extracted_data = db.Column(db.Text, nullable=False, default='{}')
    survey_data = db.Column(db.Text, nullable=False, default='{}')
    step_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    business_account = db.relationship('BusinessAccount', foreign_keys='ActiveConversation.business_account_id')
    campaign = db.relationship('Campaign', foreign_keys='ActiveConversation.campaign_id')
    
    def to_dict(self):
        return {
            'conversation_id': self.conversation_id,
            'business_account_id': self.business_account_id,
            'campaign_id': self.campaign_id,
            'participant_data': json.loads(self.participant_data) if self.participant_data else None,
            'conversation_history': json.loads(self.conversation_history) if self.conversation_history else [],
            'extracted_data': json.loads(self.extracted_data) if self.extracted_data else {},
            'survey_data': json.loads(self.survey_data) if self.survey_data else {},
            'step_count': self.step_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class Campaign(db.Model):
    """Campaign model for tracking feedback collection periods"""
    __tablename__ = 'campaigns'
    __table_args__ = (
        # Note: Single active campaign constraint now enforced by database trigger
        # 'check_single_active_campaign' which respects BusinessAccount.allow_parallel_campaigns
        # Regular index for common queries
        db.Index('idx_campaign_business_status', 'business_account_id', 'status'),
        db.Index('idx_campaign_dates', 'start_date', 'end_date'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='draft', index=True)  # draft, ready, active, completed
    survey_type = db.Column(db.String(20), nullable=False, default='conversational', index=True)  # 'conversational' or 'classic'
    
    # Language configuration (en=English, fr=French)
    language_code = db.Column(db.String(5), nullable=False, default='en', index=True)
    
    # Client tracking (for future multi-client support)
    # Client identifier tracks which business account owns this campaign
    # Set during creation to business_account.name for multi-tenant tracking
    client_identifier = db.Column(db.String(200), nullable=True, index=True)
    
    # Business account ownership (Phase 2.5: Schema Fix)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=True, index=True)
    business_account = db.relationship('BusinessAccount', backref=db.backref('campaigns', lazy='dynamic'))
    
    # Add participants relationship through campaign_participants
    participants = db.relationship('Participant', 
                                 secondary='campaign_participants',
                                 backref='campaigns',
                                 lazy='dynamic')
    
    # Campaign-specific survey customization fields
    product_description = db.Column(db.Text, nullable=True)
    target_clients_description = db.Column(db.Text, nullable=True)
    survey_goals = db.Column(db.JSON, nullable=True)
    max_questions = db.Column(db.Integer, nullable=True, default=8)
    max_duration_seconds = db.Column(db.Integer, nullable=True, default=120)
    max_follow_ups_per_topic = db.Column(db.Integer, nullable=True, default=2)
    prioritized_topics = db.Column(db.JSON, nullable=True)
    optional_topics = db.Column(db.JSON, nullable=True)
    custom_end_message = db.Column(db.Text, nullable=True)
    custom_system_prompt = db.Column(db.Text, nullable=True)
    
    # Industry-specific prompt verticalization (Phase 2: Topic Hints)
    industry = db.Column(db.String(100), nullable=True, index=True)  # Override BusinessAccount industry if set
    
    # Inheritance flags for survey settings (default: inherit from business account)
    use_business_topics = db.Column(db.Boolean, nullable=False, default=True)
    use_business_controls = db.Column(db.Boolean, nullable=False, default=True)
    use_business_product_focus = db.Column(db.Boolean, nullable=False, default=True)
    
    # Role-based prompt overrides (Dec 2025: 4-tier configuration)
    # Campaign-specific overrides for persona questioning guidance
    # Structure: {"manager": {"prompt_guidance": {"en": "...", "fr": "..."}, "question_templates": {...}}}
    role_prompt_overrides = db.Column(db.JSON, nullable=True, default={})
    use_business_role_prompts = db.Column(db.Boolean, nullable=False, default=True)  # Inherit from business account
    
    # Campaign-specific email content customization (hybrid: campaign overrides → account defaults → hardcoded)
    use_custom_email_content = db.Column(db.Boolean, nullable=False, default=False)
    custom_subject_template = db.Column(db.String(500), nullable=True)
    custom_intro_message = db.Column(db.Text, nullable=True)
    custom_cta_text = db.Column(db.String(100), nullable=True)
    custom_closing_message = db.Column(db.Text, nullable=True)
    custom_footer_note = db.Column(db.Text, nullable=True)
    
    # Anonymization setting
    anonymize_responses = db.Column(db.Boolean, nullable=False, default=False)
    
    # Reminder email configuration
    reminder_enabled = db.Column(db.Boolean, nullable=False, default=False)
    reminder_delay_days = db.Column(db.Integer, nullable=False, default=5)
    
    # Bulk operation tracking (concurrency control)
    has_active_bulk_job = db.Column(db.Boolean, nullable=False, default=False, index=True)
    active_bulk_job_id = db.Column(db.Integer, db.ForeignKey('bulk_operation_jobs.id'), nullable=True, index=True)
    active_bulk_operation = db.Column(db.String(50), nullable=True)  # 'add' or 'remove'
    
    # Vetting tracking (added 2026-03-31)
    simulation_completed_at = db.Column(db.DateTime, nullable=True)
    manager_validated_at = db.Column(db.DateTime, nullable=True)
    manager_validated_by = db.Column(db.String(200), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    VETTING_FEATURE_DATE = datetime(2026, 3, 31, 0, 0, 0)

    @property
    def vetting_status(self):
        """
        Compute vetting readiness state.
        Returns None for campaigns predating the vetting feature to avoid misleading badges.
        Returns 'simulated_and_validated', 'simulated_not_validated', or 'not_simulated'.
        """
        if self.created_at and self.created_at < self.VETTING_FEATURE_DATE:
            return None
        if self.simulation_completed_at and self.manager_validated_at:
            return 'simulated_and_validated'
        if self.simulation_completed_at:
            return 'simulated_not_validated'
        return 'not_simulated'

    def to_dict(self, include_response_count=False, response_count=None):
        """
        Serialize campaign to dictionary.
        
        Args:
            include_response_count: Whether to include response count (expensive query if not pre-computed)
            response_count: Pre-computed response count to avoid N+1 queries (overrides include_response_count)
        """
        result = {
            'id': self.id,
            'uuid': self.uuid,
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'survey_type': self.survey_type,
            'language_code': self.language_code,
            'client_identifier': self.client_identifier,
            'business_account_id': self.business_account_id,
            'business_account_name': self.business_account.name if self.business_account else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'is_active': self.is_active(),
            'days_remaining': self.days_remaining(),
            'days_since_ended': self.days_since_ended(),
            'days_until_start': self.days_until_start(),
            # Campaign-specific survey customization fields
            'product_description': self.product_description,
            'target_clients_description': self.target_clients_description,
            'survey_goals': self.survey_goals,
            'max_questions': self.max_questions,
            'max_duration_seconds': self.max_duration_seconds,
            'max_follow_ups_per_topic': self.max_follow_ups_per_topic,
            'prioritized_topics': self.prioritized_topics,
            'optional_topics': self.optional_topics,
            'custom_end_message': self.custom_end_message,
            'custom_system_prompt': self.custom_system_prompt,
            'industry': self.industry,
            'anonymize_responses': self.anonymize_responses,
            # Reminder configuration
            'reminder_enabled': self.reminder_enabled,
            'reminder_delay_days': self.reminder_delay_days,
            # Email customization flags and content
            'use_custom_email_content': self.use_custom_email_content,
            'custom_subject_template': self.custom_subject_template,
            'custom_intro_message': self.custom_intro_message,
            'custom_cta_text': self.custom_cta_text,
            'custom_closing_message': self.custom_closing_message,
            'custom_footer_note': self.custom_footer_note,
            'has_campaign_customization': self.product_description is not None or self.target_clients_description is not None,
            # Inheritance flags for survey settings
            'use_business_topics': self.use_business_topics,
            'use_business_controls': self.use_business_controls,
            'use_business_product_focus': self.use_business_product_focus,
            # Role prompt overrides (Dec 2025: 4-tier configuration)
            'role_prompt_overrides': self.role_prompt_overrides or {},
            'use_business_role_prompts': self.use_business_role_prompts,
            # Vetting fields (added 2026-03-31)
            'simulation_completed_at': self.simulation_completed_at.isoformat() if self.simulation_completed_at else None,
            'manager_validated_at': self.manager_validated_at.isoformat() if self.manager_validated_at else None,
            'manager_validated_by': self.manager_validated_by,
            'vetting_status': self.vetting_status
        }
        
        # OPTIMIZATION: Only include response_count if explicitly requested or pre-computed
        if response_count is not None:
            result['response_count'] = response_count
        elif include_response_count:
            # WARNING: This triggers a query - should be avoided in loops
            result['response_count'] = len([r for r in SurveyResponse.query.filter_by(campaign_id=self.id).all()])
        # Otherwise: omit response_count key entirely (don't default to 0 to surface regressions)
        
        return result
    
    def is_active(self):
        """Check if campaign is currently active"""
        return self.status == 'active'
    
    def is_ready_for_activation(self):
        """Check if campaign can be activated (has participants and description)"""
        if self.status != 'ready':
            return False
        today = date.today()
        return self.start_date == today and self.description and self.participants.count() > 0
    
    def can_modify_participants(self):
        """Check if participants can be modified (only when not active)"""
        return self.status in ['draft', 'ready']
    
    def days_remaining(self):
        """Calculate days remaining in campaign"""
        if self.status != 'active':
            return 0
        today = date.today()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days
    
    def days_since_ended(self):
        """Calculate days since campaign ended"""
        if self.status == 'active':
            return 0
        today = date.today()
        if today <= self.end_date:
            return 0
        return (today - self.end_date).days
    
    def days_until_start(self):
        """Calculate days until campaign starts"""
        if self.status == 'active':
            return 0
        today = date.today()
        if today >= self.start_date:
            return 0
        return (self.start_date - today).days
    
    @property
    def participants_count(self):
        """Get current count of participants for this campaign"""
        from models import CampaignParticipant  # Import here to avoid circular imports
        return CampaignParticipant.query.filter_by(campaign_id=self.id).count()
    
    def get_engagement_metrics(self):
        """Get engagement metrics for this campaign"""
        from models import EmailDelivery, SurveyResponse  # Import here to avoid circular imports
        
        # Count sent invitations
        invitations_sent = EmailDelivery.query.filter_by(
            campaign_id=self.id,
            status='sent',
            email_type='participant_invitation'
        ).count()
        
        # Count completed surveys
        surveys_completed = SurveyResponse.query.filter_by(campaign_id=self.id).count()
        
        # Count responses by source type
        email_responses = SurveyResponse.query.filter(
            SurveyResponse.campaign_id == self.id,
            SurveyResponse.source_type.in_(['form', 'conversational'])
        ).count()
        
        transcript_responses = SurveyResponse.query.filter_by(
            campaign_id=self.id,
            source_type='transcript'
        ).count()
        
        # Get total participants count
        total_participants = self.participants_count
        
        # Calculate participation rate (completed / total participants)
        participation_rate = None
        if total_participants > 0:
            participation_rate = round((surveys_completed / total_participants) * 100, 1)
        
        # Calculate email success rate (completed / successfully sent)
        email_success_rate = None
        if invitations_sent > 0:
            email_success_rate = round((surveys_completed / invitations_sent) * 100, 1)
        
        # Only calculate reminder metrics if reminders are enabled
        reminders_sent = 0
        reminder_conversions = 0
        reminder_conversion_rate = None
        
        if self.reminder_enabled:
            # Count sent reminders (total emails)
            reminders_sent = EmailDelivery.query.filter_by(
                campaign_id=self.id,
                status='sent',
                email_type='reminder'
            ).count()
            
            # Count DISTINCT participants who received at least one reminder
            participants_reminded = db.session.query(
                func.count(func.distinct(EmailDelivery.campaign_participant_id))
            ).filter(
                EmailDelivery.campaign_id == self.id,
                EmailDelivery.status == 'sent',
                EmailDelivery.email_type == 'reminder'
            ).scalar() or 0
            
            # Calculate reminder conversion rate
            # (responses that came after reminder was sent)
            if participants_reminded > 0:
                # Count DISTINCT participants who responded after receiving a reminder
                # This avoids overcounting if multiple reminder emails exist per participant
                reminder_conversions = db.session.query(
                    func.count(func.distinct(SurveyResponse.campaign_participant_id))
                ).select_from(SurveyResponse).join(
                    EmailDelivery,
                    EmailDelivery.campaign_participant_id == SurveyResponse.campaign_participant_id
                ).filter(
                    SurveyResponse.campaign_id == self.id,
                    EmailDelivery.campaign_id == self.id,
                    EmailDelivery.email_type == 'reminder',
                    EmailDelivery.status == 'sent',
                    SurveyResponse.created_at > EmailDelivery.sent_at
                ).scalar() or 0
                
                # Calculate conversion rate: (participants who converted) / (participants who received reminders) * 100
                reminder_conversion_rate = round((reminder_conversions / participants_reminded) * 100, 1)
        
        return {
            'invitations_sent': invitations_sent,
            'surveys_completed': surveys_completed,
            'email_responses': email_responses,
            'transcript_responses': transcript_responses,
            'total_participants': total_participants,
            'participation_rate': participation_rate,
            'email_success_rate': email_success_rate,
            'reminders_sent': reminders_sent,
            'reminder_conversions': reminder_conversions,
            'reminder_conversion_rate': reminder_conversion_rate
        }
    
    def close_campaign(self):
        """Mark campaign as completed and generate KPI snapshot"""
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Set completion status and timestamp
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        
        # Generate KPI snapshot to preserve analytics data
        try:
            # Import here to avoid circular imports (data_storage imports models)
            from data_storage import generate_campaign_kpi_snapshot
            
            logger.info(f"Generating KPI snapshot for campaign '{self.name}' (ID: {self.id})")
            snapshot = generate_campaign_kpi_snapshot(self.id)
            
            if snapshot:
                logger.info(f"KPI snapshot successfully created for campaign '{self.name}' (ID: {self.id})")
            else:
                logger.warning(f"KPI snapshot generation returned None for campaign '{self.name}' (ID: {self.id})")
                
        except Exception as e:
            logger.error(f"Failed to generate KPI snapshot for campaign '{self.name}' (ID: {self.id}): {e}")
            # Don't raise the exception - campaign completion should succeed even if snapshot fails
            # The snapshot can be generated manually later if needed
        
        # Trigger automatic executive report generation
        try:
            from task_queue import task_queue
            task_queue.add_task('executive_report', data_id=self.id, task_data={
                'campaign_id': self.id,
                'business_account_id': self.business_account_id
            })
            logger.info(f"Queued executive report generation for completed campaign '{self.name}' (ID: {self.id})")
        except Exception as report_error:
            logger.error(f"Failed to queue executive report for campaign '{self.name}' (ID: {self.id}): {report_error}")
            # Don't raise - campaign completion should succeed even if report queueing fails
    
    def mark_ready(self):
        """Mark campaign as ready for activation"""
        if self.status == 'draft' and self.description and self.participants.count() > 0:
            self.status = 'ready'
            return True
        return False
    
    def activate(self):
        """Activate campaign if conditions are met"""
        if self.status == 'ready' and not Campaign.get_active_campaign():
            self.status = 'active'
            return True
        return False
    
    @staticmethod
    def get_active_campaign(client_identifier='archelo_group'):
        """Get the currently active campaign for a client"""
        today = date.today()
        return Campaign.query.filter(
            Campaign.client_identifier == client_identifier,
            Campaign.status == 'active',
            Campaign.start_date <= today,
            Campaign.end_date >= today
        ).first()
    
    @staticmethod
    def get_active_campaigns(business_account_id):
        """Get all currently active campaigns for a business account.
        
        This method supports accounts with allow_parallel_campaigns enabled,
        returning all active campaigns rather than just one.
        
        Args:
            business_account_id: The ID of the business account
            
        Returns:
            List of active Campaign objects
        """
        today = date.today()
        return Campaign.query.filter(
            Campaign.business_account_id == business_account_id,
            Campaign.status == 'active',
            Campaign.start_date <= today,
            Campaign.end_date >= today
        ).order_by(Campaign.start_date).all()
    
    @staticmethod
    def count_active_campaigns(business_account_id):
        """Count active campaigns for a business account.
        
        Used for parallel campaigns enforcement and UI display.
        
        Args:
            business_account_id: The ID of the business account
            
        Returns:
            Integer count of active campaigns
        """
        return Campaign.query.filter(
            Campaign.business_account_id == business_account_id,
            Campaign.status == 'active'
        ).count()
    
    @staticmethod
    def count_client_campaigns(client_identifier='archelo_group'):
        """Count total campaigns for a client"""
        return Campaign.query.filter(
            Campaign.client_identifier == client_identifier
        ).count()
    
    @staticmethod
    def can_create_campaign(client_identifier='archelo_group'):
        """Check if client can create a new campaign (max 4 per year)"""
        return Campaign.count_client_campaigns(client_identifier) < 4
    
    @staticmethod
    def has_overlapping_campaign(start_date, end_date, client_identifier='archelo_group', exclude_id=None):
        """Check if there's an overlapping active campaign"""
        query = Campaign.query.filter(
            Campaign.client_identifier == client_identifier,
            Campaign.status == 'active',
            or_(
                and_(Campaign.start_date <= start_date, Campaign.end_date >= start_date),
                and_(Campaign.start_date <= end_date, Campaign.end_date >= end_date),
                and_(Campaign.start_date >= start_date, Campaign.end_date <= end_date)
            )
        )
        
        if exclude_id:
            query = query.filter(Campaign.id != exclude_id)
            
        return query.first() is not None
    
    def get_survey_config(self):
        """Return all survey configuration as dict"""
        return {
            'product_description': self.product_description,
            'target_clients_description': self.target_clients_description,
            'survey_goals': self.survey_goals,
            'max_questions': self.max_questions,
            'max_duration_seconds': self.max_duration_seconds,
            'max_follow_ups_per_topic': self.max_follow_ups_per_topic,
            'prioritized_topics': self.prioritized_topics,
            'optional_topics': self.optional_topics,
            'custom_end_message': self.custom_end_message,
            'custom_system_prompt': self.custom_system_prompt
        }
    
    def has_campaign_customization(self):
        """Return True if campaign has any customization data"""
        return bool(
            self.product_description or
            self.target_clients_description or
            self.survey_goals or
            self.max_questions != 8 or  # Default is 8
            self.max_duration_seconds != 120 or  # Default is 120
            self.max_follow_ups_per_topic != 2 or  # Default is 2
            self.prioritized_topics or
            self.optional_topics or
            self.custom_end_message or
            self.custom_system_prompt
        )
    
    def get_effective_survey_goals(self):
        """Return survey_goals or default fallback"""
        if self.survey_goals:
            return self.survey_goals
        # Default survey goals fallback
        return ["NPS", "Product Quality", "Support Experience", "Overall Satisfaction"]
    
    def validate_custom_email_content(self):
        """Validate custom email content fields if enabled"""
        import re
        errors = []
        
        if not self.use_custom_email_content:
            return errors  # No validation needed if not using custom content
        
        # Validate subject template
        if self.custom_subject_template and len(self.custom_subject_template) > 500:
            errors.append("Subject template must be 500 characters or less")
        
        # Validate intro message
        if self.custom_intro_message and len(self.custom_intro_message) > 2000:
            errors.append("Intro message must be 2000 characters or less")
        
        # Validate CTA text
        if self.custom_cta_text and len(self.custom_cta_text) > 100:
            errors.append("CTA text must be 100 characters or less")
        
        # Validate closing message
        if self.custom_closing_message and len(self.custom_closing_message) > 2000:
            errors.append("Closing message must be 2000 characters or less")
        
        # Validate footer note
        if self.custom_footer_note and len(self.custom_footer_note) > 1000:
            errors.append("Footer note must be 1000 characters or less")
        
        # Check for potentially harmful HTML tags (basic XSS prevention)
        dangerous_pattern = re.compile(r'<script|<iframe|javascript:|onerror=|onclick=', re.IGNORECASE)
        
        fields_to_check = {
            'Subject': self.custom_subject_template,
            'Intro': self.custom_intro_message,
            'CTA': self.custom_cta_text,
            'Closing': self.custom_closing_message,
            'Footer': self.custom_footer_note
        }
        
        for field_name, field_value in fields_to_check.items():
            if field_value and dangerous_pattern.search(field_value):
                errors.append(f"{field_name} contains potentially unsafe content")
        
        return errors
    
    def get_email_content(self):
        """
        Get email content for this campaign.
        Returns dict with subject, intro, cta_text, closing, footer.
        If custom content is not used or empty, returns None for those fields.
        """
        if not self.use_custom_email_content:
            return {
                'subject_template': None,
                'intro_message': None,
                'cta_text': None,
                'closing_message': None,
                'footer_note': None
            }
        
        return {
            'subject_template': self.custom_subject_template,
            'intro_message': self.custom_intro_message,
            'cta_text': self.custom_cta_text,
            'closing_message': self.custom_closing_message,
            'footer_note': self.custom_footer_note
        }


class CampaignKPISnapshot(db.Model):
    """Immutable KPI snapshot for closed campaigns to prevent data drift"""
    __tablename__ = 'campaign_kpi_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, unique=True, index=True)
    campaign = db.relationship('Campaign', backref=db.backref('kpi_snapshot', uselist=False))
    
    # Core Metrics
    total_responses = db.Column(db.Integer, nullable=False, default=0)
    total_companies = db.Column(db.Integer, nullable=False, default=0)
    
    # NPS Metrics
    nps_score = db.Column(db.Float, nullable=False, default=0.0)
    promoters_count = db.Column(db.Integer, nullable=False, default=0)
    passives_count = db.Column(db.Integer, nullable=False, default=0)
    detractors_count = db.Column(db.Integer, nullable=False, default=0)
    
    # Average Ratings (1-5 scale)
    avg_satisfaction_rating = db.Column(db.Float, nullable=True)
    avg_pricing_rating = db.Column(db.Float, nullable=True)
    avg_service_rating = db.Column(db.Float, nullable=True)
    avg_product_value_rating = db.Column(db.Float, nullable=True)
    avg_support_rating = db.Column(db.Float, nullable=True)
    
    # Sentiment Distribution (percentages)
    sentiment_positive_pct = db.Column(db.Float, nullable=True, default=0.0)
    sentiment_negative_pct = db.Column(db.Float, nullable=True, default=0.0)
    sentiment_neutral_pct = db.Column(db.Float, nullable=True, default=0.0)
    
    # Risk Assessment
    high_risk_accounts_count = db.Column(db.Integer, nullable=False, default=0)
    churn_risk_high_pct = db.Column(db.Float, nullable=True, default=0.0)
    churn_risk_medium_pct = db.Column(db.Float, nullable=True, default=0.0)
    churn_risk_low_pct = db.Column(db.Float, nullable=True, default=0.0)
    churn_risk_minimal_pct = db.Column(db.Float, nullable=True, default=0.0)
    
    # Growth Metrics
    avg_growth_factor = db.Column(db.Float, nullable=True, default=0.0)
    total_growth_potential = db.Column(db.Float, nullable=True, default=0.0)
    
    # Company Aggregations
    avg_company_nps = db.Column(db.Float, nullable=True, default=0.0)
    
    # Distribution Data (stored as JSON for charts)
    nps_distribution = db.Column(db.Text, nullable=True)  # JSON: [{"category": "Promoter", "count": 5}, ...]
    sentiment_distribution = db.Column(db.Text, nullable=True)  # JSON: [{"label": "Positive", "count": 8}, ...]
    tenure_distribution = db.Column(db.Text, nullable=True)  # JSON: [{"tenure": "1-2 years", "count": 3}, ...]
    ratings_distribution = db.Column(db.Text, nullable=True)  # JSON: [{"category": "Satisfaction", "rating": 3.4}, ...]
    growth_factor_distribution = db.Column(db.Text, nullable=True)  # JSON: [{"range": "70-100", "count": 2}, ...]
    key_themes = db.Column(db.Text, nullable=True)  # JSON: [{"theme": "pricing", "frequency": 8}, ...]
    high_risk_accounts = db.Column(db.Text, nullable=True)  # JSON: [{"company": "Acme Inc", "risk": "High"}, ...]
    
    # Account Intelligence Data
    account_intelligence = db.Column(db.Text, nullable=True)  # JSON: Full account intelligence analysis
    growth_opportunities_analysis = db.Column(db.Text, nullable=True)  # JSON: Growth opportunities by company
    account_risk_factors_analysis = db.Column(db.Text, nullable=True)  # JSON: Risk factors by company
    
    # Survey Insights Data  
    company_nps_breakdown = db.Column(db.Text, nullable=True)  # JSON: Company-level NPS data
    tenure_analysis = db.Column(db.Text, nullable=True)  # JSON: Tenure-based analysis
    
    # Analytics Charts Data
    growth_factor_analysis_detailed = db.Column(db.Text, nullable=True)  # JSON: Detailed growth factor data
    
    # Segmentation Analytics Data
    segmentation_analytics = db.Column(db.Text, nullable=True)  # JSON: NPS and satisfaction by role, region, customer tier
    
    # Classic Survey-Specific Metrics
    survey_type = db.Column(db.String(20), nullable=True, default='conversational')
    avg_csat = db.Column(db.Float, nullable=True)
    avg_ces = db.Column(db.Float, nullable=True)
    csat_distribution = db.Column(db.Text, nullable=True)  # JSON: {"1": 2, "2": 1, "3": 5, ...}
    ces_distribution = db.Column(db.Text, nullable=True)  # JSON: {"1": 0, "2": 1, ...}
    driver_attribution = db.Column(db.Text, nullable=True)  # JSON: {driver_key: {count, percentage, promoters, passives, detractors, net_impact, label_en, label_fr}}
    feature_analytics = db.Column(db.Text, nullable=True)  # JSON: {feature_key: {name_en, name_fr, adoption_rate, avg_satisfaction, ...}}
    recommendation_distribution = db.Column(db.Text, nullable=True)  # JSON: {recommended: N, would_consider: N, ...}
    correlation_data = db.Column(db.Text, nullable=True)  # JSON: {points: [{csat, ces, nps_score, nps_category}], summary: {...}}
    
    # Snapshot Metadata
    snapshot_version = db.Column(db.String(10), nullable=False, default='v1.0')  # Track engine versions
    snapshot_created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    data_period_start = db.Column(db.Date, nullable=False)  # Campaign start date
    data_period_end = db.Column(db.Date, nullable=False)  # Campaign end date
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'campaign_name': self.campaign.name if self.campaign else None,
            'total_responses': self.total_responses,
            'total_companies': self.total_companies,
            'nps_score': self.nps_score,
            'promoters_count': self.promoters_count,
            'passives_count': self.passives_count,
            'detractors_count': self.detractors_count,
            'avg_satisfaction_rating': self.avg_satisfaction_rating,
            'avg_pricing_rating': self.avg_pricing_rating,
            'avg_service_rating': self.avg_service_rating,
            'avg_product_value_rating': self.avg_product_value_rating,
            'avg_support_rating': self.avg_support_rating,
            'sentiment_positive_pct': self.sentiment_positive_pct,
            'sentiment_negative_pct': self.sentiment_negative_pct,
            'sentiment_neutral_pct': self.sentiment_neutral_pct,
            'high_risk_accounts_count': self.high_risk_accounts_count,
            'churn_risk_high_pct': self.churn_risk_high_pct,
            'churn_risk_medium_pct': self.churn_risk_medium_pct,
            'churn_risk_low_pct': self.churn_risk_low_pct,
            'churn_risk_minimal_pct': self.churn_risk_minimal_pct,
            'avg_growth_factor': self.avg_growth_factor,
            'total_growth_potential': self.total_growth_potential,
            'avg_company_nps': self.avg_company_nps,
            'nps_distribution': json.loads(self.nps_distribution) if self.nps_distribution else [],
            'sentiment_distribution': json.loads(self.sentiment_distribution) if self.sentiment_distribution else [],
            'tenure_distribution': json.loads(self.tenure_distribution) if self.tenure_distribution else [],
            'ratings_distribution': json.loads(self.ratings_distribution) if self.ratings_distribution else [],
            'growth_factor_distribution': json.loads(self.growth_factor_distribution) if self.growth_factor_distribution else [],
            'key_themes': json.loads(self.key_themes) if self.key_themes else [],
            'high_risk_accounts': json.loads(self.high_risk_accounts) if self.high_risk_accounts else [],
            'account_intelligence': json.loads(self.account_intelligence) if self.account_intelligence else [],
            'growth_opportunities_analysis': json.loads(self.growth_opportunities_analysis) if self.growth_opportunities_analysis else {},
            'account_risk_factors_analysis': json.loads(self.account_risk_factors_analysis) if self.account_risk_factors_analysis else {},
            'company_nps_breakdown': json.loads(self.company_nps_breakdown) if self.company_nps_breakdown else [],
            'tenure_analysis': json.loads(self.tenure_analysis) if self.tenure_analysis else [],
            'growth_factor_analysis_detailed': json.loads(self.growth_factor_analysis_detailed) if self.growth_factor_analysis_detailed else {},
            'segmentation_analytics': json.loads(self.segmentation_analytics) if self.segmentation_analytics else {},
            'survey_type': self.survey_type or 'conversational',
            'avg_csat': self.avg_csat,
            'avg_ces': self.avg_ces,
            'csat_distribution': json.loads(self.csat_distribution) if self.csat_distribution else {},
            'ces_distribution': json.loads(self.ces_distribution) if self.ces_distribution else {},
            'driver_attribution': json.loads(self.driver_attribution) if self.driver_attribution else {},
            'feature_analytics': json.loads(self.feature_analytics) if self.feature_analytics else {},
            'recommendation_distribution': json.loads(self.recommendation_distribution) if self.recommendation_distribution else {},
            'correlation_data': json.loads(self.correlation_data) if self.correlation_data else {},
            'snapshot_version': self.snapshot_version,
            'snapshot_created_at': self.snapshot_created_at.isoformat() if self.snapshot_created_at else None,
            'data_period_start': self.data_period_start.isoformat() if self.data_period_start else None,
            'data_period_end': self.data_period_end.isoformat() if self.data_period_end else None
        }


# ==== NEW MULTI-TENANT MODELS FOR PARTICIPANT MANAGEMENT SYSTEM ====

class BusinessAccount(db.Model):
    """Business Account model for multi-tenant participant management"""
    __tablename__ = 'business_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    name = db.Column(db.String(200), nullable=False, index=True)
    account_type = db.Column(db.String(20), nullable=False, default='customer', index=True)  # customer, demo
    
    # Contact information
    contact_email = db.Column(db.String(200), nullable=True)
    contact_name = db.Column(db.String(200), nullable=True)
    
    # Account status
    status = db.Column(db.String(20), nullable=False, default='active', index=True)  # active, suspended, trial
    
    # License management fields
    license_activated_at = db.Column(db.DateTime, nullable=True, index=True)  # License activation date (start of license period)
    license_expires_at = db.Column(db.DateTime, nullable=True, index=True)  # License expiration date
    license_status = db.Column(db.String(20), nullable=False, default='trial', index=True)  # trial, active, expired
    
    # Concurrent Campaigns Setting (Platform Admin controlled)
    allow_parallel_campaigns = db.Column(db.Boolean, nullable=False, default=False, index=True)  # Allow multiple active campaigns simultaneously
    
    # Survey Customization Fields (Phase 1: VOÏA Customizable Implementation)
    # Company Profile for Survey Customization
    industry = db.Column(db.String(100), nullable=True, index=True)  # Healthcare, SaaS, Retail, etc.
    company_description = db.Column(db.Text, nullable=True)  # "We provide cloud-based accounting solutions..."
    product_description = db.Column(db.Text, nullable=True)  # "Our flagship product ArcheloFlow helps..."
    target_clients_description = db.Column(db.Text, nullable=True)  # "Small business owners, CFOs..."
    conversation_tone = db.Column(db.String(50), nullable=True, default='professional')  # professional, warm, casual, formal
    survey_goals = db.Column(db.JSON, nullable=True)  # ["NPS", "Product", "Support", "Pricing"] - DEPRECATED Phase 1
    
    # Industry-specific prompt verticalization (Phase 2: Topic Hints)
    industry_topic_hints = db.Column(db.JSON, nullable=True)  # Custom topic hints override platform defaults: {"Product Quality": "custom keywords"}
    
    # Role-based prompt overrides (Dec 2025: 4-tier configuration)
    # Overrides platform defaults for persona-specific questioning guidance
    # Structure: {"manager": {"prompt_guidance": {"en": "...", "fr": "..."}, "question_templates": {...}}}
    role_prompt_overrides = db.Column(db.JSON, nullable=True, default={})
    
    # Survey Control Parameters
    max_questions = db.Column(db.Integer, nullable=True, default=8)  # Absolute hard stop (3-15 range)
    max_duration_seconds = db.Column(db.Integer, nullable=True, default=120)  # Time limit (60-300 range)
    max_follow_ups_per_topic = db.Column(db.Integer, nullable=True, default=2)  # Topic depth control (1-3 range)
    prioritized_topics = db.Column(db.JSON, nullable=True)  # ["NPS", "Product Quality", "Support Experience"]
    optional_topics = db.Column(db.JSON, nullable=True)  # ["Pricing Value"] - skip if time runs out
    custom_end_message = db.Column(db.Text, nullable=True)  # Custom completion message
    
    # Advanced Customization (for power users)
    custom_system_prompt = db.Column(db.Text, nullable=True)  # Override default template entirely
    prompt_template_version = db.Column(db.String(10), nullable=True, default='v1.0')  # Track template versions
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'account_type': self.account_type,
            'contact_email': self.contact_email,
            'contact_name': self.contact_name,
            'status': self.status,
            'license_activated_at': self.license_activated_at.isoformat() if self.license_activated_at else None,
            'license_expires_at': self.license_expires_at.isoformat() if self.license_expires_at else None,
            'current_users_count': self.current_users_count,  # Use dynamic property instead of static counter
            'license_status': self.license_status,
            'allow_parallel_campaigns': self.allow_parallel_campaigns,
            # Survey Customization Fields
            'industry': self.industry,
            'company_description': self.company_description,
            'product_description': self.product_description,
            'target_clients_description': self.target_clients_description,
            'conversation_tone': self.conversation_tone,
            'survey_goals': self.survey_goals,
            'max_questions': self.max_questions,
            'max_duration_seconds': self.max_duration_seconds,
            'max_follow_ups_per_topic': self.max_follow_ups_per_topic,
            'prioritized_topics': self.prioritized_topics,
            'optional_topics': self.optional_topics,
            'custom_end_message': self.custom_end_message,
            'custom_system_prompt': self.custom_system_prompt,
            'prompt_template_version': self.prompt_template_version,
            'industry_topic_hints': self.industry_topic_hints,
            'role_prompt_overrides': self.role_prompt_overrides or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_email_configuration(self):
        """Get email configuration for this business account"""
        return EmailConfiguration.query.filter_by(business_account_id=self.id).first()
    
    def has_email_configuration(self):
        """Check if business account has email configuration set up"""
        return self.get_email_configuration() is not None
    
    @property
    def current_users_count(self):
        """Get current count of active users for this business account"""
        from models import BusinessAccountUser  # Import here to avoid circular imports
        return BusinessAccountUser.query.filter_by(
            business_account_id=self.id,
            is_active_user=True
        ).count()
    
    def get_license_period(self, reference_date=None):
        """Calculate license period boundaries based on activation date
        
        Args:
            reference_date: Date to check (defaults to today)
            
        Returns:
            tuple: (period_start_date, period_end_date) or (None, None) if no valid license
        """
        from datetime import date, timedelta
        
        if reference_date is None:
            reference_date = date.today()
        
        # If no license_activated_at, try to infer from license_expires_at
        if not self.license_activated_at and self.license_expires_at:
            # Infer activation as 1 year prior to expiration
            expires_date = self.license_expires_at.date() if hasattr(self.license_expires_at, 'date') else self.license_expires_at
            try:
                # Try to subtract exactly 1 year, handling leap year edge cases
                inferred_activation = expires_date.replace(year=expires_date.year - 1)
            except ValueError:
                # Handle Feb 29 leap year case - move to Feb 28
                inferred_activation = expires_date.replace(year=expires_date.year - 1, day=28)
            
            return inferred_activation, expires_date
        
        # If we have license_activated_at, use it
        if self.license_activated_at:
            activation_date = self.license_activated_at.date() if hasattr(self.license_activated_at, 'date') else self.license_activated_at
            
            if self.license_expires_at:
                expires_date = self.license_expires_at.date() if hasattr(self.license_expires_at, 'date') else self.license_expires_at
                return activation_date, expires_date
            else:
                # If no expiration set, assume 1 year license
                try:
                    expires_date = activation_date.replace(year=activation_date.year + 1)
                except ValueError:
                    # Handle Feb 29 leap year case
                    expires_date = activation_date.replace(year=activation_date.year + 1, day=28)
                return activation_date, expires_date
        
        # No valid license period can be determined
        return None, None
    
    def can_activate_campaign(self):
        """Check if business account can activate another campaign (limit: 4 per license period)
        
        Legacy method - now uses LicenseService for comprehensive license management.
        This method is kept for backward compatibility.
        """
        from license_service import LicenseService
        return LicenseService.can_activate_campaign(self.id)
    
    def can_add_user(self):
        """Check if business account can add another user (limit: 5 users)
        
        Legacy method - now uses LicenseService for comprehensive license management.
        This method is kept for backward compatibility.
        """
        from license_service import LicenseService
        return LicenseService.can_add_user(self.id)
    
    def can_add_participants(self, campaign_id, additional_count):
        """Check if campaign can add more participants (limit: 500 per campaign)
        
        Legacy method - now uses LicenseService for comprehensive license management.
        This method is kept for backward compatibility.
        """
        from license_service import LicenseService
        return LicenseService.can_add_participants(self.id, campaign_id, additional_count)


class EmailConfiguration(db.Model):
    """Email Configuration model for business account-specific SMTP settings"""
    __tablename__ = 'email_configurations'
    __table_args__ = (
        # Only one email configuration per business account
        db.UniqueConstraint('business_account_id', name='uq_email_config_business_account'),
        db.Index('idx_email_config_business_account', 'business_account_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    
    # Email Provider Selection
    email_provider = db.Column(db.String(20), nullable=False, default='smtp')  # 'smtp' or 'aws_ses'
    
    # SMTP Configuration (used for both standard SMTP and AWS SES SMTP interface)
    smtp_server = db.Column(db.String(255), nullable=True)  # Auto-generated for AWS SES based on region
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_username = db.Column(db.String(255), nullable=True)  # AWS SES SMTP username or standard SMTP
    smtp_password_encrypted = db.Column(db.Text, nullable=True)  # Encrypted password
    use_tls = db.Column(db.Boolean, nullable=False, default=True)
    use_ssl = db.Column(db.Boolean, nullable=False, default=False)
    
    # AWS SES Specific Configuration
    aws_region = db.Column(db.String(50), nullable=True)  # e.g., 'us-east-1', 'eu-west-1'
    
    # Platform Email Mode (NEW - for dual-mode support)
    use_platform_email = db.Column(db.Boolean, nullable=False, default=False)  # True = VOÏA-managed, False = Client-managed
    
    # Domain Verification (NEW - for VOÏA-managed AWS SES mode)
    sender_domain = db.Column(db.String(255), nullable=True)  # e.g., 'clientA.com'
    domain_verified = db.Column(db.Boolean, nullable=False, default=False)
    domain_verification_status = db.Column(db.String(50), nullable=True)  # 'pending', 'verified', 'failed'
    
    # DKIM Records for DNS Configuration (NEW - manually entered by platform admin from AWS Console)
    dkim_record_1_name = db.Column(db.String(500), nullable=True)  # e.g., 'abc123._domainkey.clientA.com'
    dkim_record_1_value = db.Column(db.String(500), nullable=True)  # e.g., 'abc123.dkim.amazonses.com'
    dkim_record_2_name = db.Column(db.String(500), nullable=True)
    dkim_record_2_value = db.Column(db.String(500), nullable=True)
    dkim_record_3_name = db.Column(db.String(500), nullable=True)
    dkim_record_3_value = db.Column(db.String(500), nullable=True)
    
    domain_verified_at = db.Column(db.DateTime, nullable=True)  # When verification was confirmed
    
    # Sender Configuration
    sender_name = db.Column(db.String(200), nullable=False)
    sender_email = db.Column(db.String(200), nullable=False)
    reply_to_email = db.Column(db.String(200), nullable=True)
    
    # Admin Notification Settings
    admin_notification_emails = db.Column(db.Text, nullable=True)  # JSON array of admin emails
    
    # Custom Email Content
    use_custom_content = db.Column(db.Boolean, nullable=False, default=False)  # Toggle between default and custom templates
    custom_subject_template = db.Column(db.String(200), nullable=True)  # Custom email subject
    custom_intro_message = db.Column(db.Text, nullable=True)  # Custom introduction message
    custom_cta_text = db.Column(db.String(50), nullable=True)  # Custom call-to-action button text
    custom_closing_message = db.Column(db.Text, nullable=True)  # Custom closing message
    custom_footer_note = db.Column(db.Text, nullable=True)  # Custom footer disclaimer
    
    # Configuration Status
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)  # Whether SMTP config has been tested
    last_test_at = db.Column(db.DateTime, nullable=True)
    last_test_result = db.Column(db.Text, nullable=True)  # JSON result of last test
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business_account = db.relationship('BusinessAccount', backref=db.backref('email_configuration', uselist=False))
    
    def __init__(self, **kwargs):
        # Handle password encryption on initialization
        if 'smtp_password' in kwargs:
            self.set_smtp_password(kwargs.pop('smtp_password'))
        super().__init__(**kwargs)
    
    def set_smtp_password(self, password):
        """Encrypt and store SMTP password"""
        if password:
            self.smtp_password_encrypted = self._encrypt_password(password)
    
    def get_smtp_password(self):
        """Decrypt and return SMTP password"""
        if self.smtp_password_encrypted:
            return self._decrypt_password(self.smtp_password_encrypted)
        return None
    
    def _encrypt_password(self, password):
        """Encrypt password using Fernet symmetric encryption"""
        from cryptography.fernet import Fernet
        import base64
        import os
        
        # Always prefer dedicated EMAIL_ENCRYPTION_KEY for new encryptions
        key = os.environ.get('EMAIL_ENCRYPTION_KEY')
        if not key:
            # Fallback to SESSION_SECRET for backward compatibility
            secret_key = os.environ.get('SESSION_SECRET', 'development-key').encode()
            key = base64.urlsafe_b64encode(secret_key[:32].ljust(32, b'0'))
        else:
            key = key.encode()
        
        fernet = Fernet(key)
        encrypted_password = fernet.encrypt(password.encode())
        return base64.urlsafe_b64encode(encrypted_password).decode()
    
    def _decrypt_password(self, encrypted_password):
        """Decrypt password using Fernet symmetric encryption with key migration support"""
        from cryptography.fernet import Fernet
        import base64
        import os
        import logging
        
        logger = logging.getLogger(__name__)
        
        # List of keys to try (current first, then fallbacks)
        key_sources = []
        
        # Primary key: EMAIL_ENCRYPTION_KEY
        primary_key = os.environ.get('EMAIL_ENCRYPTION_KEY')
        if primary_key:
            key_sources.append(('primary', primary_key.encode()))
        
        # Fallback key: EMAIL_ENCRYPTION_PREVIOUS_KEY for migration
        previous_key = os.environ.get('EMAIL_ENCRYPTION_PREVIOUS_KEY')
        if previous_key:
            key_sources.append(('previous', previous_key.encode()))
        
        # Legacy fallback: SESSION_SECRET (current)
        session_secret = os.environ.get('SESSION_SECRET', 'development-key').encode()
        session_key = base64.urlsafe_b64encode(session_secret[:32].ljust(32, b'0'))
        key_sources.append(('session_current', session_key))
        
        # Try each key source
        for key_name, key in key_sources:
            try:
                fernet = Fernet(key)
                encrypted_data = base64.urlsafe_b64decode(encrypted_password.encode())
                decrypted_password = fernet.decrypt(encrypted_data).decode()
                
                # If we successfully decrypted with a non-primary key, migrate to primary
                if key_name != 'primary' and primary_key:
                    logger.info(f"Email password decrypted with {key_name} key, migrating to primary key")
                    self._migrate_password_encryption(decrypted_password)
                
                return decrypted_password
                
            except Exception as e:
                logger.error(f"Failed to decrypt password with {key_name} key: {str(e)[:100]}")
                continue
        
        logger.error(f"CRITICAL: Failed to decrypt email password with any available key for business_account_id {getattr(self, 'business_account_id', 'unknown')}")
        logger.error(f"Available keys tried: {[name for name, _ in key_sources]}")
        logger.error(f"Encrypted password length: {len(encrypted_password)}")
        return None
    
    def _migrate_password_encryption(self, decrypted_password):
        """Migrate password to primary encryption key"""
        try:
            # Re-encrypt with primary key
            new_encrypted = self._encrypt_password(decrypted_password)
            
            # Update the stored encrypted password
            self.smtp_password_encrypted = new_encrypted
            
            # Save to database
            from app import db
            db.session.commit()
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Successfully migrated email password encryption for business account {self.business_account_id}")
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to migrate password encryption: {e}")
    
    def get_admin_emails(self):
        """Parse admin notification emails from JSON"""
        if self.admin_notification_emails:
            try:
                return json.loads(self.admin_notification_emails)
            except:
                return []
        return []
    
    def set_admin_emails(self, emails):
        """Set admin notification emails as JSON"""
        if emails and isinstance(emails, list):
            self.admin_notification_emails = json.dumps(emails)
        else:
            self.admin_notification_emails = None
    
    def get_last_test_result(self):
        """Parse last test result from JSON"""
        if self.last_test_result:
            try:
                return json.loads(self.last_test_result)
            except:
                return {}
        return {}
    
    def set_test_result(self, result):
        """Set test result as JSON and update verification status"""
        self.last_test_at = datetime.utcnow()
        self.last_test_result = json.dumps(result)
        self.is_verified = result.get('success', False)
    
    def to_dict(self, include_password=False):
        """Convert to dictionary representation"""
        data = {
            'id': self.id,
            'business_account_id': self.business_account_id,
            'business_account_name': self.business_account.name if self.business_account else None,
            'email_provider': self.email_provider,
            'aws_region': self.aws_region,
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'smtp_username': self.smtp_username,
            'use_tls': self.use_tls,
            'use_ssl': self.use_ssl,
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'reply_to_email': self.reply_to_email,
            'admin_notification_emails': self.get_admin_emails(),
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_test_at': self.last_test_at.isoformat() if self.last_test_at else None,
            'last_test_result': self.get_last_test_result(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            # New fields for domain verification
            'use_platform_email': self.use_platform_email,
            'sender_domain': self.sender_domain,
            'domain_verified': self.domain_verified,
            'domain_verification_status': self.domain_verification_status,
            'domain_verified_at': self.domain_verified_at.isoformat() if self.domain_verified_at else None,
            'dkim_records': self.get_dkim_records()
        }
        
        if include_password:
            data['smtp_password'] = self.get_smtp_password()
        
        return data
    
    def validate_configuration(self):
        """Validate email configuration fields"""
        errors = []
        
        if self.use_platform_email:
            # Platform-managed AWS SES mode validation
            # No SMTP credentials needed (uses platform settings)
            # Only validate sender identity and domain verification
            
            if not self.sender_domain:
                errors.append("Sender domain is required for platform email")
            
            if not self.sender_name:
                errors.append("Sender name is required")
            
            if not self.sender_email:
                errors.append("Sender email is required")
            elif '@' not in self.sender_email:
                errors.append("Valid sender email is required")
            elif self.sender_domain and self.sender_domain not in self.sender_email:
                errors.append(f"Sender email must be from domain {self.sender_domain}")
            
            # Check DKIM records are present
            if not self.has_dkim_records():
                errors.append("DKIM records must be configured for domain verification")
        
        else:
            # Client-managed SMTP mode validation (original logic)
            
            # Provider-specific validation
            if self.is_aws_ses():
                # AWS SES validation
                if not self.aws_region:
                    errors.append("AWS region is required for AWS SES")
                # SMTP server is auto-generated for AWS SES, so don't validate it here
            else:
                # Standard SMTP validation
                if not self.smtp_server:
                    errors.append("SMTP server is required")
            
            # Common validations for both providers
            if not self.smtp_port or not (1 <= self.smtp_port <= 65535):
                errors.append("Valid SMTP port (1-65535) is required")
            
            if not self.smtp_username:
                errors.append("SMTP username is required")
            
            if not self.smtp_password_encrypted:
                errors.append("SMTP password is required")
            
            if not self.sender_name:
                errors.append("Sender name is required")
            
            if not self.sender_email:
                errors.append("Sender email is required")
            elif '@' not in self.sender_email:
                errors.append("Valid sender email is required")
        
        # Common validation for both modes
        if self.reply_to_email and '@' not in self.reply_to_email:
            errors.append("Valid reply-to email is required")
        
        return errors
    
    def is_valid(self):
        """Check if configuration is valid and password can be decrypted"""
        # Check basic field validation
        if len(self.validate_configuration()) > 0:
            return False
        
        # Check that password can actually be decrypted
        decrypted_password = self.get_smtp_password()
        return decrypted_password is not None and len(decrypted_password) > 0
    
    def is_aws_ses(self):
        """Check if this configuration uses AWS SES"""
        return self.email_provider == 'aws_ses'
    
    def get_ses_smtp_server(self):
        """Get AWS SES SMTP server endpoint based on region"""
        if not self.aws_region:
            return None
        return f"email-smtp.{self.aws_region}.amazonaws.com"
    
    def ensure_ses_smtp_server(self):
        """Auto-generate SMTP server for AWS SES if using AWS SES provider"""
        if self.is_aws_ses() and self.aws_region:
            self.smtp_server = self.get_ses_smtp_server()
    
    def get_email_content(self):
        """Get email content configuration (custom or default)
        
        Returns:
            Dict with subject, intro, cta, closing, footer - either custom or defaults
        """
        import re
        
        # Default templates
        defaults = {
            'subject': "Your feedback is requested: {campaign_name}",
            'intro': "{business_account_name} is requesting your valuable feedback through our Voice of Client system.",
            'cta_text': "Complete Your Survey",
            'closing': "Your feedback helps improve services and experiences. The survey should take just a few minutes to complete.\n\nThank you for your time and valuable insights!",
            'footer': "This is an automated message. If you have any questions, please contact the organization that sent this survey."
        }
        
        # If not using custom content, return defaults
        if not self.use_custom_content:
            return defaults
        
        # Otherwise return custom content with fallback to defaults
        return {
            'subject': self.custom_subject_template or defaults['subject'],
            'intro': self.custom_intro_message or defaults['intro'],
            'cta_text': self.custom_cta_text or defaults['cta_text'],
            'closing': self.custom_closing_message or defaults['closing'],
            'footer': self.custom_footer_note or defaults['footer']
        }
    
    def validate_custom_content(self):
        """Validate custom email content fields
        
        Returns:
            List of validation errors
        """
        errors = []
        
        if not self.use_custom_content:
            return errors  # No validation needed if using defaults
        
        # Validate subject template
        if self.custom_subject_template:
            if len(self.custom_subject_template) > 200:
                errors.append("Subject template must be 200 characters or less")
        
        # Validate CTA text
        if self.custom_cta_text:
            if len(self.custom_cta_text) > 50:
                errors.append("Call-to-action text must be 50 characters or less")
        
        # Check for HTML tags (security - strip HTML)
        import re
        html_pattern = re.compile(r'<[^>]+>')
        
        fields_to_check = [
            ('custom_subject_template', self.custom_subject_template),
            ('custom_intro_message', self.custom_intro_message),
            ('custom_cta_text', self.custom_cta_text),
            ('custom_closing_message', self.custom_closing_message),
            ('custom_footer_note', self.custom_footer_note)
        ]
        
        for field_name, field_value in fields_to_check:
            if field_value and html_pattern.search(field_value):
                errors.append(f"{field_name.replace('custom_', '').replace('_', ' ').title()} cannot contain HTML tags")
        
        return errors
    
    def get_dkim_records(self):
        """Get DKIM records as a list of dictionaries
        
        Returns:
            List of DKIM records with name and value, filtering out empty records
        """
        records = []
        
        if self.dkim_record_1_name and self.dkim_record_1_value:
            records.append({
                'name': self.dkim_record_1_name,
                'value': self.dkim_record_1_value,
                'record_number': 1
            })
        
        if self.dkim_record_2_name and self.dkim_record_2_value:
            records.append({
                'name': self.dkim_record_2_name,
                'value': self.dkim_record_2_value,
                'record_number': 2
            })
        
        if self.dkim_record_3_name and self.dkim_record_3_value:
            records.append({
                'name': self.dkim_record_3_name,
                'value': self.dkim_record_3_value,
                'record_number': 3
            })
        
        return records
    
    def has_dkim_records(self):
        """Check if any DKIM records are configured"""
        return len(self.get_dkim_records()) > 0
    
    @staticmethod
    def get_for_business_account(business_account_id):
        """Get email configuration for a business account"""
        return EmailConfiguration.query.filter_by(
            business_account_id=business_account_id,
            is_active=True
        ).first()


class PlatformEmailSettings(db.Model):
    """Platform-wide AWS SES configuration (single record for VOÏA platform)"""
    __tablename__ = 'platform_email_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    
    # AWS SES credentials (used for ALL business accounts when use_platform_email=True)
    aws_region = db.Column(db.String(50), nullable=False)  # e.g., 'us-east-1'
    smtp_server = db.Column(db.String(255), nullable=False)  # Auto-generated: email-smtp.{region}.amazonaws.com
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_username = db.Column(db.String(255), nullable=False)  # VOÏA's SES SMTP username
    smtp_password_encrypted = db.Column(db.Text, nullable=False)  # VOÏA's SES SMTP password (encrypted)
    use_tls = db.Column(db.Boolean, nullable=False, default=True)
    use_ssl = db.Column(db.Boolean, nullable=False, default=False)
    
    # Configuration status
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    last_test_at = db.Column(db.DateTime, nullable=True)
    last_test_result = db.Column(db.Text, nullable=True)  # JSON result of last test
    
    # Metadata
    configured_at = db.Column(db.DateTime, default=datetime.utcnow)
    configured_by_user_id = db.Column(db.Integer, db.ForeignKey('business_account_users.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    configured_by = db.relationship('BusinessAccountUser', foreign_keys=[configured_by_user_id])
    
    def set_smtp_password(self, password):
        """Encrypt and store SMTP password (reuses EmailConfiguration encryption logic)"""
        if password:
            from cryptography.fernet import Fernet
            import base64
            import os
            
            key = os.environ.get('EMAIL_ENCRYPTION_KEY')
            if not key:
                secret_key = os.environ.get('SESSION_SECRET', 'development-key').encode()
                key = base64.urlsafe_b64encode(secret_key[:32].ljust(32, b'0'))
            else:
                key = key.encode()
            
            fernet = Fernet(key)
            encrypted_password = fernet.encrypt(password.encode())
            self.smtp_password_encrypted = base64.urlsafe_b64encode(encrypted_password).decode()
    
    def get_smtp_password(self):
        """Decrypt and return SMTP password"""
        if self.smtp_password_encrypted:
            from cryptography.fernet import Fernet
            import base64
            import os
            import logging
            
            logger = logging.getLogger(__name__)
            key_sources = []
            
            primary_key = os.environ.get('EMAIL_ENCRYPTION_KEY')
            if primary_key:
                key_sources.append(('primary', primary_key.encode()))
            
            previous_key = os.environ.get('EMAIL_ENCRYPTION_PREVIOUS_KEY')
            if previous_key:
                key_sources.append(('previous', previous_key.encode()))
            
            session_secret = os.environ.get('SESSION_SECRET', 'development-key').encode()
            session_key = base64.urlsafe_b64encode(session_secret[:32].ljust(32, b'0'))
            key_sources.append(('session_current', session_key))
            
            for key_name, key in key_sources:
                try:
                    fernet = Fernet(key)
                    encrypted_data = base64.urlsafe_b64decode(self.smtp_password_encrypted.encode())
                    decrypted_password = fernet.decrypt(encrypted_data).decode()
                    return decrypted_password
                except Exception as e:
                    logger.debug(f"Failed to decrypt with {key_name} key: {str(e)[:100]}")
                    continue
            
            logger.error("Failed to decrypt platform email password with any available key")
            return None
        return None
    
    def set_test_result(self, result):
        """Set test result as JSON and update verification status"""
        self.last_test_at = datetime.utcnow()
        self.last_test_result = json.dumps(result)
        self.is_verified = result.get('success', False)
    
    def get_last_test_result(self):
        """Parse last test result from JSON"""
        if self.last_test_result:
            try:
                return json.loads(self.last_test_result)
            except:
                return {}
        return {}
    
    def to_dict(self, include_password=False):
        """Convert to dictionary representation"""
        data = {
            'id': self.id,
            'aws_region': self.aws_region,
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'smtp_username': self.smtp_username,
            'use_tls': self.use_tls,
            'use_ssl': self.use_ssl,
            'is_verified': self.is_verified,
            'last_test_at': self.last_test_at.isoformat() if self.last_test_at else None,
            'configured_at': self.configured_at.isoformat() if self.configured_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_password:
            data['smtp_password'] = self.get_smtp_password()
        
        return data


class PlatformSurveySettings(db.Model):
    """Platform-wide survey configuration (single record for VOÏA platform)
    
    Dec 2025: Added for 4-tier role prompt override configuration.
    Super-admins can set platform-wide defaults that all tenants inherit.
    """
    __tablename__ = 'platform_survey_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Role-based prompt overrides (platform-level defaults)
    # Structure: {"manager": {"prompt_guidance": {"en": "...", "fr": "..."}, "question_templates": {...}}}
    role_prompt_overrides = db.Column(db.JSON, nullable=True, default={})
    
    # Industry topic hints (platform-level defaults)
    industry_topic_hints = db.Column(db.JSON, nullable=True, default={})
    
    # Feature flags for survey behavior
    use_role_prompt_overrides = db.Column(db.Boolean, nullable=False, default=False)  # Enable 4-tier resolution
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by_user_id = db.Column(db.Integer, db.ForeignKey('business_account_users.id'), nullable=True)
    
    # Relationship
    updated_by = db.relationship('BusinessAccountUser', foreign_keys=[updated_by_user_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'role_prompt_overrides': self.role_prompt_overrides or {},
            'industry_topic_hints': self.industry_topic_hints or {},
            'use_role_prompt_overrides': self.use_role_prompt_overrides,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def get_instance():
        """Get or create the singleton platform survey settings record"""
        settings = PlatformSurveySettings.query.first()
        if not settings:
            settings = PlatformSurveySettings()
            db.session.add(settings)
            db.session.commit()
        return settings


class Participant(db.Model):
    """Participant model for campaign-based surveys with token authentication and origin tracking"""
    __tablename__ = 'participants'
    __table_args__ = (
        db.UniqueConstraint('business_account_id', 'email', name='uq_participant_business_email'),
        db.Index('idx_participant_business_email', 'business_account_id', 'email'),
        db.Index('idx_participant_source', 'source'),
        # Indexes for filtering in campaign participant assignment
        db.Index('idx_participant_company_name', 'company_name'),
        db.Index('idx_participant_role', 'role'),
        db.Index('idx_participant_region', 'region'),
        db.Index('idx_participant_customer_tier', 'customer_tier'),
        db.Index('idx_participant_language', 'language'),
        db.Index('idx_participant_tenure_years', 'tenure_years'),
        # Composite indexes for optimized filter queries (October 2025)
        db.Index('idx_participant_ba_company', 'business_account_id', 'company_name', 'status'),
        db.Index('idx_participant_ba_role', 'business_account_id', 'role', 'status'),
        db.Index('idx_participant_ba_region', 'business_account_id', 'region', 'status'),
        db.Index('idx_participant_ba_tier', 'business_account_id', 'customer_tier', 'status'),
        db.Index('idx_participant_ba_language', 'business_account_id', 'language', 'status'),
        db.Index('idx_participant_ba_tenure', 'business_account_id', 'tenure_years', 'status'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=True, index=True)  # NULL for trial users
    # Note: No direct campaign relationship - associations managed via CampaignParticipant table
    
    # Participant information
    email = db.Column(db.String(200), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200), nullable=True)
    
    # Segmentation attributes (optional, for personalized surveys and analytics)
    role = db.Column(db.String(100), nullable=True)  # e.g., "C-Level", "Manager", "End User"
    region = db.Column(db.String(100), nullable=True)  # e.g., "North America", "EMEA", "APAC"
    customer_tier = db.Column(db.String(50), nullable=True)  # e.g., "Enterprise", "SMB", "Startup"
    language = db.Column(db.String(10), nullable=True, default='en')  # ISO language code (en, es, fr, etc.)
    client_industry = db.Column(db.String(120), nullable=True)  # e.g., "Healthcare", "EMS", "Software" - Industry sector of participant's company
    
    # Company-level financial data (manual input only, synced across all participants from same company)
    company_commercial_value = db.Column(db.Float, nullable=True)  # Estimated account value in USD
    
    # Participant tenure tracking (optional, represents years using the product/service)
    tenure_years = db.Column(db.Float, nullable=True)  # Years of product/service usage (e.g., 2.5 years)
    
    # Origin tracking for management visibility
    source = db.Column(db.String(20), nullable=False, default='trial', index=True)  # 'trial', 'admin_single', 'admin_bulk', 'transcript_upload'
    
    # Token authentication (unified token system)
    token = db.Column(db.String(255), nullable=True, unique=True, index=True)  # UUID token for survey access
    
    # Status tracking (context-dependent)
    status = db.Column(db.String(20), nullable=False, default='invited', index=True)  # invited, started, completed, created
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    invited_at = db.Column(db.DateTime, nullable=True, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    business_account = db.relationship('BusinessAccount', backref='participants')
    # Note: Campaign relationships handled via CampaignParticipant association table
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_account_id': self.business_account_id,
            'email': self.email,
            'name': self.name,
            'company_name': self.company_name,
            'role': self.role,
            'region': self.region,
            'customer_tier': self.customer_tier,
            'language': self.language,
            'client_industry': self.client_industry,
            'company_commercial_value': self.company_commercial_value,
            'tenure_years': self.tenure_years,
            'source': self.source,
            'token': self.token,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'business_account_name': self.business_account.name if self.business_account else None,
            'is_trial_user': self.is_trial_user(),
            'origin_badge': self.get_origin_badge()
        }
    
    def generate_token(self):
        """Generate a unique token for participant survey access"""
        import uuid
        self.token = str(uuid.uuid4())
        return self.token
    
    def is_completed(self):
        """Check if participant has completed the survey"""
        return self.status == 'completed' and self.completed_at is not None
    
    def is_trial_user(self):
        """Check if participant is a trial user"""
        return self.source == 'trial'
    
    def is_admin_created(self):
        """Check if participant was created by admin"""
        return self.source in ['admin_single', 'admin_bulk']
    
    def get_origin_badge(self):
        """Get display badge for participant origin"""
        origin_badges = {
            'trial': {'text': 'Trial User', 'class': 'badge-info'},
            'admin_single': {'text': 'Admin Created', 'class': 'badge-success'},
            'admin_bulk': {'text': 'Bulk Upload', 'class': 'badge-warning'},
            'transcript_upload': {'text': 'Transcript Upload', 'class': 'badge-info'}
        }
        return origin_badges.get(self.source, {'text': 'Unknown', 'class': 'badge-secondary'})
    
    def set_appropriate_status_for_context(self, is_trial=False):
        """Set appropriate status based on creation context"""
        if is_trial:
            self.status = 'invited'  # Trial users are immediately invited
        else:
            self.status = 'created'   # Business participants are created but not campaign-specific yet
    
    def has_survey_history(self):
        """
        Check if participant has any survey history (responses, campaign associations, or email deliveries).
        Used to determine if email can be edited or participant can be deleted.
        CRITICAL: All checks are scoped to participant's business account for multi-tenant isolation.
        
        Returns:
            bool: True if participant has any survey-related data within their business account
        """
        # Check for CampaignParticipant associations
        has_campaign_associations = CampaignParticipant.query.filter_by(
            participant_id=self.id
        ).first() is not None
        
        if has_campaign_associations:
            return True
        
        # Check for SurveyResponse records (by email for legacy data)
        # CRITICAL: Join to Campaign to enforce business account scoping
        from sqlalchemy import and_
        has_responses = db.session.query(SurveyResponse).join(
            Campaign, SurveyResponse.campaign_id == Campaign.id
        ).filter(
            and_(
                SurveyResponse.respondent_email == self.email,
                Campaign.business_account_id == self.business_account_id
            )
        ).first() is not None
        
        if has_responses:
            return True
        
        # Check for EmailDelivery records (sent or pending)
        has_email_deliveries = EmailDelivery.query.filter_by(
            participant_id=self.id
        ).first() is not None
        
        return has_email_deliveries


class CampaignParticipant(db.Model):
    """Association model for campaign-participant relationships with individual tokens"""
    __tablename__ = 'campaign_participants'
    __table_args__ = (
        db.UniqueConstraint('campaign_id', 'participant_id', name='uq_campaign_participant'),
        db.Index('idx_campaign_participant', 'campaign_id', 'participant_id'),
        db.Index('idx_campaign_participant_business', 'business_account_id'),
        db.Index('idx_campaign_participant_reminder', 'campaign_id', 'status', 'invited_at'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False, index=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    
    # Campaign-participant specific token for JWT authentication
    token = db.Column(db.String(36), nullable=True, unique=True, index=True)  # UUID token for this association
    
    # Status tracking per campaign
    status = db.Column(db.String(20), nullable=False, default='invited', index=True)  # invited, started, completed
    
    # Timestamps per campaign-participant relationship
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    invited_at = db.Column(db.DateTime, nullable=True, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    campaign = db.relationship('Campaign', 
                              backref=db.backref('campaign_participants', overlaps="campaigns,participants"), 
                              overlaps="campaigns,participants")
    participant = db.relationship('Participant', 
                                 foreign_keys='CampaignParticipant.participant_id', 
                                 backref=db.backref('campaign_participations', overlaps="campaigns,participants"), 
                                 overlaps="campaigns,participants")
    business_account = db.relationship('BusinessAccount', backref='campaign_participants')
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'participant_id': self.participant_id,
            'business_account_id': self.business_account_id,
            'participant_token': self.participant.token if self.participant else None,  # Reference unified token
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'campaign_name': self.campaign.name if self.campaign else None,
            'participant_email': self.participant.email if self.participant else None,
            'participant_name': self.participant.name if self.participant else None,
            'participant_source': self.participant.source if self.participant else None  # Include origin tracking
        }
    
    def generate_token(self):
        """Generate a unique token for this campaign-participant association"""
        import uuid
        self.token = str(uuid.uuid4())
        return self.token
    
    def is_completed(self):
        """Check if this campaign-participant assignment is completed"""
        return self.status == 'completed' and self.completed_at is not None
    
    def mark_started(self):
        """Mark participant as started for this campaign"""
        if self.status == 'invited':
            self.status = 'started'
            self.started_at = datetime.utcnow()
    
    def mark_completed(self):
        """Mark participant as completed for this campaign"""
        if self.status in ['invited', 'started']:
            self.status = 'completed'
            self.completed_at = datetime.utcnow()


# ==== PHASE 2: BUSINESS ACCOUNT AUTHENTICATION MODELS ====

class BusinessAccountUser(UserMixin, db.Model):
    """User authentication model for business accounts (Phase 2)"""
    __tablename__ = 'business_account_users'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    
    # User credentials
    email = db.Column(db.String(200), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    
    # User profile
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    
    # User role and permissions
    role = db.Column(db.String(50), nullable=False, default='admin', index=True)  # admin, manager, viewer, platform_admin (business_account_admin deprecated)
    is_active_user = db.Column(db.Boolean, nullable=False, default=True, index=True)  # Renamed to avoid conflict with UserMixin
    
    # Email verification
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    email_verification_token = db.Column(db.String(255), nullable=True)
    
    # Password reset
    password_reset_token = db.Column(db.String(255), nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)
    
    # Invitation flow (Phase 1: Business Account Onboarding)
    invitation_token = db.Column(db.String(255), nullable=True, unique=True, index=True)
    invited_at = db.Column(db.DateTime, nullable=True, index=True)
    activated_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Onboarding flow (Phase 3: Mandatory Setup for Core/Plus licenses)
    onboarding_progress = db.Column(db.JSON, nullable=True, default=dict)
    onboarding_completed = db.Column(db.Boolean, nullable=False, default=False, index=True)
    onboarding_version = db.Column(db.Integer, nullable=True, default=1)
    onboarding_completed_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # User Preferences
    language_preference = db.Column(db.String(10), nullable=True)  # 'en' or 'fr' - user's preferred language across all devices
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    business_account = db.relationship('BusinessAccount', backref='users')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        if self.password_hash is None:
            return False  # Invited users without activated accounts cannot log in
        return check_password_hash(self.password_hash, password)
    
    def generate_password_reset_token(self):
        """Generate password reset token"""
        self.password_reset_token = str(uuid.uuid4())
        self.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        return self.password_reset_token
    
    def validate_password_reset_token(self, token):
        """Validate password reset token and check expiration"""
        if not self.password_reset_token or not self.password_reset_expires:
            return False
        
        if self.password_reset_token != token:
            return False
        
        # Check if token is expired
        current_time = datetime.utcnow()
        
        # Convert to naive datetime if password_reset_expires is timezone-aware
        expiry_time = self.password_reset_expires
        if hasattr(expiry_time, 'tzinfo') and expiry_time.tzinfo is not None:
            expiry_time = expiry_time.replace(tzinfo=None)
        
        if current_time > expiry_time:
            return False
        
        return True
    
    def reset_password(self, new_password):
        """Reset password and clear reset token"""
        self.set_password(new_password)
        self.password_reset_token = None
        self.password_reset_expires = None
        return True
    
    def generate_email_verification_token(self):
        """Generate email verification token"""
        self.email_verification_token = str(uuid.uuid4())
        return self.email_verification_token
    
    def verify_email(self):
        """Mark email as verified"""
        self.email_verified = True
        self.email_verification_token = None
    
    def generate_invitation_token(self):
        """Generate invitation token for account activation"""
        self.invitation_token = str(uuid.uuid4())
        self.invited_at = datetime.utcnow()
        self.activated_at = None  # Reset activation status
        return self.invitation_token
    
    def activate_account(self, password):
        """Activate account with password during invitation flow"""
        if not self.invitation_token:
            raise ValueError("No invitation token found")
        
        # Set password and mark as activated
        self.set_password(password)
        self.activated_at = datetime.utcnow()
        self.invitation_token = None  # Clear invitation token
        self.email_verified = True  # Auto-verify email on activation
        
        return True
    
    def is_invitation_valid(self):
        """Check if invitation token is valid and not expired (24 hours)"""
        if not self.invitation_token or not self.invited_at:
            return False
        
        # Check if invitation is within 24 hours
        expiry_time = self.invited_at + timedelta(hours=24)
        
        # Ensure both datetime objects have same timezone awareness
        current_time = datetime.utcnow()
        
        # Convert to naive datetime if invited_at is timezone-aware
        if hasattr(self.invited_at, 'tzinfo') and self.invited_at.tzinfo is not None:
            expiry_time = expiry_time.replace(tzinfo=None)
        
        return current_time <= expiry_time
    
    def is_activated(self):
        """Check if account has been activated"""
        return self.activated_at is not None
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login_at = datetime.utcnow()
    
    def get_language_preference(self):
        """Get user's language preference, returns 'en', 'fr', or None if not set"""
        if self.language_preference and self.language_preference in ['en', 'fr']:
            return self.language_preference
        return None
    
    def set_language_preference(self, language):
        """Set user's language preference (validates to 'en' or 'fr' only)"""
        if language in ['en', 'fr']:
            self.language_preference = language
            self.updated_at = datetime.utcnow()
            return True
        return False
    
    @property
    def is_authenticated(self):
        """Override UserMixin property"""
        return True
    
    @property  
    def is_anonymous(self):
        """Override UserMixin property"""
        return False
    
    def get_full_name(self):
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    def has_permission(self, permission):
        """Check if user has specific permission
        
        Roles (3 active):
        - platform_admin: Full platform control, cross-tenant operations, license management
        - admin: Full control within their business account
        - manager: Day-to-day operations, cannot manage users or delete
        
        Deprecated roles (mapped to admin for backward compatibility):
        - business_account_admin: Use 'admin' instead
        """
        role_permissions = {
            'admin': ['view', 'create', 'edit', 'delete', 'manage_users', 'export_data', 'manage_participants'],
            'manager': ['view', 'create', 'edit', 'export_data', 'manage_participants'],
            'platform_admin': ['view', 'create', 'edit', 'delete', 'manage_users', 'export_data', 'manage_participants', 'platform_admin', 'manage_licenses', 'cross_tenant_access']
        }
        
        # Backward compatibility: map old business_account_admin to admin
        if self.role == 'business_account_admin':
            return permission in role_permissions.get('admin', [])
        
        return permission in role_permissions.get(self.role, [])
    
    def is_platform_admin(self):
        """Check if user is a platform administrator with cross-tenant permissions"""
        # Enhanced security: Platform admins must have BOTH:
        # 1. 'platform_admin' role AND belong to 'platform_owner' business account
        # 2. OR be specific admin emails (for emergency fallback)
        platform_admin_emails = {
            'admin@voia.com',            # Platform admin for license management
            'admin@rivvalue.com',        # Generic admin
            'platform@rivvalue.com'      # Platform admin
        }
        
        # Check for dual-layer authentication: role + business account type
        role_and_account_check = (
            self.role == 'platform_admin' and 
            self.business_account and 
            self.business_account.account_type == 'platform_owner'
        )
        
        # Fallback for emergency access via hardcoded emails
        email_fallback = self.email.lower().strip() in platform_admin_emails
        
        return role_and_account_check or email_fallback
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_account_id': self.business_account_id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'role': self.role,
            'is_active': self.is_active_user,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'business_account_name': self.business_account.name if self.business_account else None
        }
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        return BusinessAccountUser.query.filter_by(email=email).first()
    
    @staticmethod
    def get_by_business_account(business_account_id):
        """Get all users for a business account"""
        return BusinessAccountUser.query.filter_by(business_account_id=business_account_id).all()
    
    # ==== ONBOARDING METHODS ====
    
    def requires_onboarding(self):
        """Check if user needs mandatory onboarding based on license and role"""
        # Only admin roles need onboarding
        if self.role not in ['admin', 'business_account_admin']:
            return False
        
        # Platform admins skip onboarding
        if self.is_platform_admin():
            return False
        
        # Check if already completed
        if self.onboarding_completed:
            return False
        
        # Check license type - only Core and Plus require onboarding
        try:
            from license_service import LicenseService
            license_info = LicenseService.get_license_info(self.business_account_id)
            return license_info['license_type'] in ['core', 'plus']
        except Exception:
            # Default to requiring onboarding if license check fails
            return True
    
    def get_onboarding_progress(self):
        """Get current onboarding progress"""
        if not self.onboarding_progress:
            return self._get_default_onboarding_progress()
        return self.onboarding_progress
    
    def _get_default_onboarding_progress(self):
        """Get default onboarding progress structure"""
        return {
            "version": "1.0",
            "steps": {
                "welcome": {"completed": False},
                "smtp": {"completed": False},
                "users": {"completed": False}
            },
            "current_step": "welcome"
        }
    
    def initialize_onboarding(self):
        """Initialize onboarding progress for user"""
        if not self.onboarding_progress:
            self.onboarding_progress = self._get_default_onboarding_progress()
            self.onboarding_version = 1
    
    def complete_onboarding_step(self, step_name):
        """Mark an onboarding step as completed"""
        self.initialize_onboarding()
        
        progress = self.onboarding_progress.copy()
        if step_name in progress["steps"]:
            progress["steps"][step_name]["completed"] = True
            progress["steps"][step_name]["completed_at"] = datetime.utcnow().isoformat()
            
            # Update current step to next incomplete step
            progress["current_step"] = self._get_next_step(progress)
            
            self.onboarding_progress = progress
            
            # Check if all steps are completed
            if self._all_steps_completed(progress):
                self.complete_onboarding()
    
    def _get_next_step(self, progress):
        """Get the next incomplete step"""
        step_order = ["welcome", "smtp", "users"]
        for step in step_order:
            if not progress["steps"].get(step, {}).get("completed", False):
                return step
        return "completed"
    
    def _all_steps_completed(self, progress):
        """Check if all required steps are completed"""
        required_steps = ["welcome", "smtp", "users"]
        return all(progress["steps"].get(step, {}).get("completed", False) for step in required_steps)
    
    def complete_onboarding(self):
        """Mark entire onboarding as completed"""
        self.onboarding_completed = True
        self.onboarding_completed_at = datetime.utcnow()
        
        # Update progress
        progress = self.get_onboarding_progress()
        progress["current_step"] = "completed"
        self.onboarding_progress = progress
    
    def get_current_onboarding_step(self):
        """Get current onboarding step"""
        progress = self.get_onboarding_progress()
        return progress.get("current_step", "welcome")
    
    def get_onboarding_step_status(self, step_name):
        """Get status of specific onboarding step"""
        progress = self.get_onboarding_progress()
        return progress["steps"].get(step_name, {"completed": False})
    
    def get_onboarding_progress_percentage(self):
        """Get onboarding progress as percentage (0-100)"""
        try:
            from license_service import LicenseService
            from onboarding_config import OnboardingFlowManager
            
            license_info = LicenseService.get_license_info(self.business_account_id)
            license_type = license_info.get('license_type', 'core')
            progress = self.get_onboarding_progress()
            
            return OnboardingFlowManager.get_progress_percentage(progress, license_type)
        except Exception:
            return 0.0


class UserSession(db.Model):
    """User session management for business account users (Phase 2)"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('business_account_users.id'), nullable=False, index=True)
    
    # Session data
    session_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    session_data = db.Column(db.Text, nullable=True)  # JSON session data
    
    # Session tracking
    ip_address = db.Column(db.String(255), nullable=True)  # Supports multiple proxy IPs
    user_agent = db.Column(db.Text, nullable=True)
    
    # Session status
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_activity_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('BusinessAccountUser', backref='sessions')
    
    def __init__(self, user_id, session_data=None, ip_address=None, user_agent=None, duration_hours=24):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.session_data = session_data
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
    
    def is_expired(self):
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at
    
    def extend_session(self, hours=24):
        """Extend session expiration"""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
        self.last_activity_at = datetime.utcnow()
    
    def deactivate(self):
        """Deactivate session"""
        self.is_active = False
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = datetime.utcnow()
    
    def set_session_data(self, data):
        """Set session data as JSON"""
        import json
        self.session_data = json.dumps(data) if data else None
    
    def get_session_data(self):
        """Get session data from JSON"""
        import json
        return json.loads(self.session_data) if self.session_data else {}
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'session_data': self.get_session_data(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired()
        }
    
    @staticmethod
    def get_active_session(session_id):
        """Get active session by session_id"""
        return UserSession.query.filter_by(
            session_id=session_id,
            is_active=True
        ).filter(UserSession.expires_at > func.now()).first()
    
    @staticmethod
    def cleanup_expired_sessions():
        """Clean up expired sessions"""
        expired_sessions = UserSession.query.filter(
            UserSession.expires_at <= func.now()
        ).all()
        
        for session in expired_sessions:
            session.deactivate()
        
        return len(expired_sessions)
    
    @staticmethod
    def get_user_sessions(user_id, active_only=True):
        """Get all sessions for a user"""
        query = UserSession.query.filter_by(user_id=user_id)
        
        if active_only:
            query = query.filter(
                UserSession.is_active == True,
                UserSession.expires_at > func.now()
            )
        
        return query.order_by(desc(UserSession.last_activity_at)).all()
    
    @staticmethod
    def revoke_user_sessions(user_id, exclude_session_id=None):
        """Revoke all sessions for a user (except optionally one)"""
        query = UserSession.query.filter_by(user_id=user_id, is_active=True)
        
        if exclude_session_id:
            query = query.filter(UserSession.session_id != exclude_session_id)
        
        sessions = query.all()
        for session in sessions:
            session.deactivate()
        
        return len(sessions)


class EmailDelivery(db.Model):
    """Email delivery tracking model for monitoring and retry logic"""
    __tablename__ = 'email_deliveries'
    __table_args__ = (
        # Index for finding failed emails to retry
        db.Index('idx_email_retry_status', 'status', 'retry_count', 'next_retry_at'),
        # Index for business account scoping
        db.Index('idx_email_business_account', 'business_account_id'),
        # Index for campaign-specific email tracking
        db.Index('idx_email_campaign', 'campaign_id'),
        # Index for participant-specific email tracking
        db.Index('idx_email_participant', 'participant_id'),
        # Index for email type queries
        db.Index('idx_email_type', 'email_type'),
        # Index for reminder duplicate checking
        db.Index('idx_email_reminder_lookup', 'campaign_participant_id', 'email_type'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    
    # Relationships and scoping
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=True, index=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=True, index=True)
    campaign_participant_id = db.Column(db.Integer, db.ForeignKey('campaign_participants.id'), nullable=True, index=True)
    
    # Email details
    email_type = db.Column(db.String(50), nullable=False, index=True)  # participant_invitation, campaign_notification, etc.
    recipient_email = db.Column(db.String(200), nullable=False, index=True)
    recipient_name = db.Column(db.String(200), nullable=True)
    subject = db.Column(db.String(500), nullable=False)
    
    # Delivery tracking
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)  # pending, sending, sent, failed, permanent_failure
    retry_count = db.Column(db.Integer, nullable=False, default=0, index=True)
    max_retries = db.Column(db.Integer, nullable=False, default=3)
    
    # Timing
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    first_attempted_at = db.Column(db.DateTime, nullable=True)
    last_attempted_at = db.Column(db.DateTime, nullable=True)
    sent_at = db.Column(db.DateTime, nullable=True, index=True)
    next_retry_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Error tracking
    last_error = db.Column(db.Text, nullable=True)
    error_history = db.Column(db.Text, nullable=True)  # JSON string of error attempts
    
    # Email content metadata (for debugging)
    email_data = db.Column(db.Text, nullable=True)  # JSON string of email parameters
    
    # Relationships
    business_account = db.relationship('BusinessAccount', backref='email_deliveries')
    campaign = db.relationship('Campaign', backref='email_deliveries')
    participant = db.relationship('Participant', backref='email_deliveries')
    campaign_participant = db.relationship('CampaignParticipant', backref='email_deliveries')
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_account_id': self.business_account_id,
            'campaign_id': self.campaign_id,
            'participant_id': self.participant_id,
            'campaign_participant_id': self.campaign_participant_id,
            'email_type': self.email_type,
            'recipient_email': self.recipient_email,
            'recipient_name': self.recipient_name,
            'subject': self.subject,
            'status': self.status,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'first_attempted_at': self.first_attempted_at.isoformat() if self.first_attempted_at else None,
            'last_attempted_at': self.last_attempted_at.isoformat() if self.last_attempted_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'last_error': self.last_error,
            'error_history': json.loads(self.error_history) if self.error_history else [],
            'email_data': json.loads(self.email_data) if self.email_data else None,
            'business_account_name': self.business_account.name if self.business_account else None,
            'campaign_name': self.campaign.name if self.campaign else None,
            'participant_name': self.participant.name if self.participant else None
        }
    
    def mark_sending(self):
        """Mark email as currently being sent"""
        self.status = 'sending'
        if not self.first_attempted_at:
            self.first_attempted_at = datetime.utcnow()
        self.last_attempted_at = datetime.utcnow()
    
    def mark_sent(self):
        """Mark email as successfully sent"""
        self.status = 'sent'
        self.sent_at = datetime.utcnow()
        self.next_retry_at = None
        self.last_error = None
    
    def mark_failed(self, error_message, is_permanent=False):
        """Mark email as failed and calculate next retry time"""
        self.status = 'permanent_failure' if is_permanent else 'failed'
        self.last_error = error_message
        
        # Add to error history
        error_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'retry_attempt': self.retry_count,
            'error': error_message
        }
        
        error_history = []
        if self.error_history:
            try:
                error_history = json.loads(self.error_history)
            except:
                error_history = []
        
        error_history.append(error_entry)
        self.error_history = json.dumps(error_history)
        
        # Calculate next retry time using exponential backoff if not permanent failure
        if not is_permanent and self.retry_count < self.max_retries:
            # Exponential backoff: 2^retry_count minutes, with jitter
            import random
            base_delay = 2 ** self.retry_count  # 1, 2, 4, 8 minutes
            jitter = random.uniform(0.5, 1.5)  # Add randomness to prevent thundering herd
            delay_minutes = base_delay * jitter
            
            self.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)
        else:
            self.next_retry_at = None
    
    def increment_retry(self):
        """Increment retry count and mark as pending for retry"""
        self.retry_count += 1
        self.status = 'pending'
    
    def should_retry(self):
        """Check if this email should be retried"""
        return (
            self.status == 'failed' and 
            self.retry_count < self.max_retries and
            self.next_retry_at and 
            self.next_retry_at <= datetime.utcnow()
        )
    
    def get_error_history(self):
        """Parse error history from JSON"""
        if self.error_history:
            try:
                return json.loads(self.error_history)
            except:
                return []
        return []
    
    def get_email_data(self):
        """Parse email data from JSON"""
        if self.email_data:
            try:
                return json.loads(self.email_data)
            except:
                return {}
        return {}
    
    @staticmethod
    def get_pending_retries():
        """Get all emails that are ready for retry"""
        return EmailDelivery.query.filter(
            EmailDelivery.status == 'failed',
            EmailDelivery.retry_count < EmailDelivery.max_retries,
            EmailDelivery.next_retry_at <= func.now()
        ).all()
    
    @staticmethod
    def get_delivery_stats(business_account_id=None, campaign_id=None):
        """Get delivery statistics"""
        query = EmailDelivery.query
        
        if business_account_id:
            query = query.filter(EmailDelivery.business_account_id == business_account_id)
        
        if campaign_id:
            query = query.filter(EmailDelivery.campaign_id == campaign_id)
        
        total = query.count()
        sent = query.filter(EmailDelivery.status == 'sent').count()
        failed = query.filter(EmailDelivery.status.in_(['failed', 'permanent_failure'])).count()
        pending = query.filter(EmailDelivery.status == 'pending').count()
        
        return {
            'total': total,
            'sent': sent,
            'failed': failed,
            'pending': pending,
            'success_rate': (sent / total * 100) if total > 0 else 0
        }


class AuditLog(db.Model):
    """Audit logging model for client-visible activity tracking"""
    __tablename__ = 'audit_logs'
    __table_args__ = (
        # Primary index for business account scoping and time-based queries
        db.Index('idx_audit_business_time', 'business_account_id', 'created_at'),
        # Index for action-based filtering
        db.Index('idx_audit_action', 'business_account_id', 'action_type'),
        # Index for user-based filtering
        db.Index('idx_audit_user', 'business_account_id', 'user_email'),
        # Index for resource-based queries
        db.Index('idx_audit_resource', 'business_account_id', 'resource_type', 'resource_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    
    def __init__(self, **kwargs):
        super(AuditLog, self).__init__(**kwargs)
    
    # Multi-tenant scoping
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    
    # User context (client-friendly)
    user_email = db.Column(db.String(200), nullable=True, index=True)  # Who performed the action
    user_name = db.Column(db.String(200), nullable=True)  # Full name for display
    
    # Action details (client-friendly language)
    action_type = db.Column(db.String(50), nullable=False, index=True)  # login, campaign_created, participants_added, etc.
    action_description = db.Column(db.String(500), nullable=False)  # "Campaign 'Q1 Survey' created"
    
    # Resource context
    resource_type = db.Column(db.String(50), nullable=True, index=True)  # campaign, participant, email_config, etc.
    resource_id = db.Column(db.String(50), nullable=True, index=True)  # ID of the affected resource
    resource_name = db.Column(db.String(200), nullable=True)  # Human-readable resource name
    
    # Additional context (JSON for flexibility)
    details = db.Column(db.Text, nullable=True)  # JSON string for additional details
    
    # Request context (minimal, client-relevant)
    ip_address = db.Column(db.String(255), nullable=True)  # Supports multiple proxy IPs
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    business_account = db.relationship('BusinessAccount', backref='audit_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_account_id': self.business_account_id,
            'user_email': self.user_email,
            'user_name': self.user_name,
            'action_type': self.action_type,
            'action_description': self.action_description,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'resource_name': self.resource_name,
            'details': json.loads(self.details) if self.details else None,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'business_account_name': self.business_account.name if self.business_account else None,
            'formatted_time': self.created_at.strftime('%B %d, %Y at %I:%M %p') if self.created_at else None
        }
    
    def set_details(self, details_dict):
        """Set details as JSON string"""
        if details_dict:
            self.details = json.dumps(details_dict)
    
    def get_details(self):
        """Get details from JSON string"""
        if self.details:
            try:
                return json.loads(self.details)
            except:
                return {}
        return {}
    
    @staticmethod
    def create_audit_entry(business_account_id, action_type, action_description, 
                          user_email=None, user_name=None, resource_type=None, 
                          resource_id=None, resource_name=None, details=None, ip_address=None,
                          created_at=None):
        """Create a new audit log entry"""
        # Parse created_at if it's an ISO string (from queue), otherwise use as-is
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        audit = AuditLog(
            business_account_id=business_account_id,
            user_email=user_email,
            user_name=user_name,
            action_type=action_type,
            action_description=action_description,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            resource_name=resource_name,
            ip_address=ip_address,
            created_at=created_at or datetime.utcnow()  # Use passed timestamp or fallback
        )
        
        if details:
            audit.set_details(details)
        
        return audit
    
    @staticmethod
    def get_business_audit_logs(business_account_id, action_type=None, user_email=None, 
                               days_back=30, limit=100, offset=0):
        """Get audit logs for a business account with filtering"""
        query = AuditLog.query.filter_by(business_account_id=business_account_id)
        
        # Apply filters
        if action_type:
            query = query.filter(AuditLog.action_type == action_type)
        
        if user_email:
            query = query.filter(AuditLog.user_email == user_email)
        
        if days_back:
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            query = query.filter(AuditLog.created_at >= cutoff_date)
        
        # Order by newest first with pagination
        return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    
    @staticmethod
    def get_audit_stats(business_account_id, days_back=30):
        """Get audit statistics for a business account"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back) if days_back else None
        
        query = AuditLog.query.filter_by(business_account_id=business_account_id)
        if cutoff_date:
            query = query.filter(AuditLog.created_at >= cutoff_date)
        
        total_actions = query.count()
        
        # Count by action type
        action_counts = {}
        action_results = query.with_entities(
            AuditLog.action_type, 
            func.count(AuditLog.id)
        ).group_by(AuditLog.action_type).all()
        
        for action_type, count in action_results:
            action_counts[action_type] = count
        
        # Count by user
        user_counts = {}
        user_results = query.with_entities(
            AuditLog.user_email,
            func.count(AuditLog.id)
        ).group_by(AuditLog.user_email).all()
        
        for user_email, count in user_results:
            user_counts[user_email or 'System'] = count
        
        return {
            'total_actions': total_actions,
            'action_counts': action_counts,
            'user_counts': user_counts,
            'date_range_days': days_back
        }


class LicenseHistory(db.Model):
    """License History model for tracking license periods and changes over time"""
    __tablename__ = 'license_history'
    __table_args__ = (
        # CRITICAL: Prevent overlapping active licenses with partial unique index
        # This creates a unique constraint only for active licenses per business account
        db.Index('uq_license_history_active_per_business', 'business_account_id',
               unique=True, postgresql_where=db.text("status = 'active'")),
        # Performance indexes for common queries
        db.Index('idx_license_history_business_status', 'business_account_id', 'status'),
        db.Index('idx_license_history_dates', 'activated_at', 'expires_at'),
        db.Index('idx_license_history_type', 'license_type'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    
    # License Details
    license_type = db.Column(db.String(20), nullable=False, index=True)  # trial, standard, premium, enterprise
    status = db.Column(db.String(20), nullable=False, index=True)  # active, expired, cancelled, suspended
    
    # License Period
    activated_at = db.Column(db.DateTime, nullable=False, index=True)  # When license became active
    expires_at = db.Column(db.DateTime, nullable=False, index=True)   # When license expires/expired
    
    # License Limits (stored here for historical accuracy)
    max_campaigns_per_year = db.Column(db.Integer, nullable=False, default=4)
    max_users = db.Column(db.Integer, nullable=False, default=5)
    max_participants_per_campaign = db.Column(db.Integer, nullable=False, default=500)  # Target responses
    max_invitations_per_campaign = db.Column(db.Integer, nullable=False, default=2500)  # Hard limit for invitations
    
    # Pricing
    annual_price = db.Column(db.Numeric(10, 2), nullable=True)  # Annual price in USD (null for trial/custom pricing)
    
    # Migration Metadata (for tracking data migration)
    migrated_from_business_account = db.Column(db.Boolean, nullable=False, default=False)  # True if migrated from old schema
    migration_notes = db.Column(db.Text, nullable=True)  # Notes about migration process
    
    # Audit Trail
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = db.Column(db.String(200), nullable=True)  # User who created this license record
    notes = db.Column(db.Text, nullable=True)  # General notes about this license period
    
    # Relationships
    business_account = db.relationship('BusinessAccount', backref=db.backref('license_histories', lazy='dynamic', order_by='LicenseHistory.activated_at.desc()'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_account_id': self.business_account_id,
            'business_account_name': self.business_account.name if self.business_account else None,
            'license_type': self.license_type,
            'status': self.status,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'max_campaigns_per_year': self.max_campaigns_per_year,
            'max_users': self.max_users,
            'max_participants_per_campaign': self.max_participants_per_campaign,
            'max_invitations_per_campaign': self.max_invitations_per_campaign,
            'annual_price': float(self.annual_price) if self.annual_price else None,
            'migrated_from_business_account': self.migrated_from_business_account,
            'migration_notes': self.migration_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'notes': self.notes,
            'is_active': self.is_active(),
            'is_expired': self.is_expired(),
            'days_remaining': self.days_remaining(),
            'days_since_expired': self.days_since_expired()
        }
    
    def is_active(self):
        """Check if license is currently active"""
        from datetime import datetime
        now = datetime.utcnow()
        return (self.status == 'active' and 
                self.activated_at <= now <= self.expires_at)
    
    def is_expired(self):
        """Check if license is expired"""
        from datetime import datetime
        now = datetime.utcnow()
        return (now > self.expires_at or self.status == 'expired')
    
    def days_remaining(self):
        """Calculate days remaining in license period"""
        if not self.is_active():
            return 0
        from datetime import datetime
        now = datetime.utcnow()
        return max(0, (self.expires_at - now).days)
    
    def days_since_expired(self):
        """Calculate days since license expired"""
        if not self.is_expired():
            return 0
        from datetime import datetime
        now = datetime.utcnow()
        return max(0, (now - self.expires_at).days)
    
    def get_license_period_dates(self):
        """Get license period as date objects for comparison"""
        activated_date = self.activated_at.date() if hasattr(self.activated_at, 'date') else self.activated_at
        expires_date = self.expires_at.date() if hasattr(self.expires_at, 'date') else self.expires_at
        return activated_date, expires_date
    
    @staticmethod
    def get_current_license(business_account_id):
        """Get the current active license for a business account"""
        from datetime import datetime
        now = datetime.utcnow()
        
        return LicenseHistory.query.filter(
            LicenseHistory.business_account_id == business_account_id,
            LicenseHistory.status == 'active',
            LicenseHistory.activated_at <= now,
            LicenseHistory.expires_at >= now
        ).first()
    
    @staticmethod
    def get_license_for_date(business_account_id, reference_date):
        """Get the license that was active on a specific date"""
        from datetime import datetime
        
        # Convert date to datetime if needed
        if hasattr(reference_date, 'date'):
            check_datetime = reference_date
        else:
            check_datetime = datetime.combine(reference_date, datetime.min.time())
        
        # First try to get an active license for the date
        active_license = LicenseHistory.query.filter(
            LicenseHistory.business_account_id == business_account_id,
            LicenseHistory.status == 'active',
            LicenseHistory.activated_at <= check_datetime,
            LicenseHistory.expires_at >= check_datetime
        ).first()
        
        # If no active license found, get any license that was valid for that date
        if not active_license:
            return LicenseHistory.query.filter(
                LicenseHistory.business_account_id == business_account_id,
                LicenseHistory.activated_at <= check_datetime,
                LicenseHistory.expires_at >= check_datetime
            ).order_by(LicenseHistory.created_at.desc()).first()
        
        return active_license
    
    @staticmethod
    def create_trial_license(business_account_id, activated_at=None, created_by='system_migration'):
        """Create a trial license for a business account"""
        from datetime import datetime, timedelta
        
        if activated_at is None:
            activated_at = datetime.utcnow()
        
        # Trial licenses are valid for 1 year
        expires_at = activated_at + timedelta(days=365)
        
        license_record = LicenseHistory()
        license_record.business_account_id = business_account_id
        license_record.license_type = 'trial'
        license_record.status = 'active'
        license_record.activated_at = activated_at
        license_record.expires_at = expires_at
        license_record.max_campaigns_per_year = 4
        license_record.max_users = 5
        license_record.max_participants_per_campaign = 500
        license_record.created_by = created_by
        license_record.notes = 'Trial license created during data migration'
        
        return license_record
    
    @staticmethod
    def migrate_from_business_account(business_account, created_by='data_migration'):
        """Create license history record from BusinessAccount legacy fields"""
        from datetime import datetime, timedelta
        
        # Determine license type based on account status
        if business_account.license_status == 'trial':
            license_type = 'trial'
        elif business_account.license_status == 'active':
            license_type = 'standard'  # Default to standard for active licenses
        else:
            license_type = 'trial'  # Fallback to trial
        
        # Handle dates
        if business_account.license_activated_at:
            activated_at = business_account.license_activated_at
        else:
            # Use account creation date as fallback
            activated_at = business_account.created_at
        
        if business_account.license_expires_at:
            expires_at = business_account.license_expires_at
        else:
            # Default to 1 year from activation for trial/missing data
            expires_at = activated_at + timedelta(days=365)
        
        # Determine current status
        now = datetime.utcnow()
        if business_account.license_status == 'expired' or now > expires_at:
            status = 'expired'
        elif business_account.license_status == 'trial' and now <= expires_at:
            status = 'active'
        elif business_account.license_status == 'active' and now <= expires_at:
            status = 'active'
        else:
            status = 'expired'
        
        # Create migration notes
        migration_notes = []
        if not business_account.license_activated_at:
            migration_notes.append(f"activated_at inferred from account created_at ({business_account.created_at})")
        if not business_account.license_expires_at:
            migration_notes.append("expires_at calculated as 1 year from activation (default trial period)")
        
        migration_notes_str = "; ".join(migration_notes) if migration_notes else None
        
        license_record = LicenseHistory()
        license_record.business_account_id = business_account.id
        license_record.license_type = license_type
        license_record.status = status
        license_record.activated_at = activated_at
        license_record.expires_at = expires_at
        license_record.max_campaigns_per_year = 4
        license_record.max_users = 5
        license_record.max_participants_per_campaign = 500
        license_record.migrated_from_business_account = True
        license_record.migration_notes = migration_notes_str
        license_record.created_by = created_by
        license_record.notes = f'Migrated from BusinessAccount.license_status="{business_account.license_status}"'
        
        return license_record


class BrandingConfig(db.Model):
    """Branding Configuration model for business account-specific branding settings"""
    __tablename__ = 'branding_configs'
    __table_args__ = (
        # Only one branding configuration per business account
        db.UniqueConstraint('business_account_id', name='uq_branding_config_business_account'),
        db.Index('idx_branding_config_business_account', 'business_account_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False)
    
    def __init__(self, **kwargs):
        super(BrandingConfig, self).__init__(**kwargs)
    
    # Branding Configuration
    company_display_name = db.Column(db.String(200), nullable=True)  # Fallback to business_account.name if empty
    logo_filename = db.Column(db.String(255), nullable=True)  # Legacy: filename reference, kept for backward compat
    logo_data = db.Column(db.LargeBinary, nullable=True)  # Binary image data stored in PostgreSQL
    logo_content_type = db.Column(db.String(50), nullable=True, default='image/png')  # MIME type of stored logo
    
    # Color Palette Configuration
    primary_color = db.Column(db.String(7), nullable=True, default='#dc3545')  # Hex color code (e.g., #dc3545)
    secondary_color = db.Column(db.String(7), nullable=True, default='#6c757d')  # Hex color code  
    accent_color = db.Column(db.String(7), nullable=True, default='#28a745')  # Hex color code for highlights
    text_color = db.Column(db.String(7), nullable=True, default='#212529')  # Primary text color
    background_color = db.Column(db.String(7), nullable=True, default='#ffffff')  # Background color
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    business_account = db.relationship('BusinessAccount', backref=db.backref('branding_config', uselist=False))
    
    def to_dict(self):
        """Convert to dictionary representation"""
        return {
            'id': self.id,
            'business_account_id': self.business_account_id,
            'business_account_name': self.business_account.name if self.business_account else None,
            'company_display_name': self.company_display_name,
            'logo_filename': self.logo_filename,
            'logo_url': self.get_logo_url(),
            'display_name': self.get_company_display_name(),
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'accent_color': self.accent_color,
            'text_color': self.text_color,
            'background_color': self.background_color,
            'color_palette': self.get_color_palette(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_company_display_name(self):
        """Get company display name with fallback to business account name"""
        if self.company_display_name and self.company_display_name.strip():
            return self.company_display_name.strip()
        return self.business_account.name if self.business_account else 'Unknown Company'
    
    def get_color_palette(self):
        """Get color palette dictionary with defaults"""
        return {
            'primary': self.primary_color or '#dc3545',
            'secondary': self.secondary_color or '#6c757d',
            'accent': self.accent_color or '#28a745',
            'text': self.text_color or '#212529',
            'background': self.background_color or '#ffffff'
        }
    
    def get_chart_colors(self):
        """Get color palette optimized for charts"""
        palette = self.get_color_palette()
        return [
            palette['primary'],
            palette['accent'], 
            palette['secondary'],
            '#17a2b8',  # Info color
            '#ffc107',  # Warning color
            '#fd7e14',  # Orange
            '#6610f2',  # Indigo
            '#e83e8c'   # Pink
        ]
    
    def get_logo_url(self):
        """Get logo URL path — serves from database via /business/logo/<id> route"""
        if self.logo_data and self.business_account_id:
            return f'/business/logo/{self.business_account_id}'
        return None
    
    def has_logo(self):
        """Check if branding config has a logo stored in the database"""
        return bool(self.logo_data)
    
    def get_logo_path(self):
        """Get full filesystem path to logo file (legacy fallback)"""
        import os
        from flask import current_app
        
        if not self.logo_filename:
            return None
        
        static_dir = os.path.join(current_app.root_path, 'static')
        logo_path = os.path.join(static_dir, 'uploads', 'logos', str(self.business_account_id), self.logo_filename)
        return logo_path
    
    def get_logo_base64_data_uri(self):
        """Get logo as a base64 data URI for embedding in HTML/PDF"""
        import base64
        if self.logo_data:
            content_type = self.logo_content_type or 'image/png'
            logo_b64 = base64.b64encode(self.logo_data).decode('utf-8')
            return f"data:{content_type};base64,{logo_b64}"
        return None
    
    def logo_exists_on_filesystem(self):
        """Check if logo file actually exists on filesystem (legacy)"""
        import os
        logo_path = self.get_logo_path()
        return logo_path and os.path.exists(logo_path)
    
    @staticmethod
    def get_or_create_for_business_account(business_account_id):
        """Get existing branding config or create a new one for business account"""
        branding_config = BrandingConfig.query.filter_by(business_account_id=business_account_id).first()
        
        if not branding_config:
            branding_config = BrandingConfig(business_account_id=business_account_id)
            db.session.add(branding_config)
            # Don't commit here - let caller handle the transaction
        
        return branding_config


class ExecutiveReport(db.Model):
    """Executive Report model for storing generated campaign reports"""
    __tablename__ = 'executive_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, processing, completed, failed
    generated_at = db.Column(db.DateTime, nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # File size in bytes
    download_count = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    campaign = db.relationship('Campaign', backref='executive_reports')
    business_account = db.relationship('BusinessAccount', backref='executive_reports')
    
    # Ensure one report per campaign
    __table_args__ = (
        db.UniqueConstraint('campaign_id', 'business_account_id', name='_campaign_business_report_uc'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'business_account_id': self.business_account_id,
            'file_path': self.file_path,
            'status': self.status,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'file_size': self.file_size,
            'download_count': self.download_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'campaign_name': self.campaign.name if self.campaign else None
        }

class ExportJob(db.Model):
    """Model for tracking campaign data export jobs"""
    __tablename__ = 'export_jobs'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default='queued', nullable=False, index=True)  # queued, processing, completed, failed
    file_path = db.Column(db.String(500), nullable=True)
    error = db.Column(db.Text, nullable=True)
    progress = db.Column(db.Text, nullable=True)  # Progress message
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    campaign = db.relationship('Campaign', backref='export_jobs')
    business_account = db.relationship('BusinessAccount', backref='export_jobs')
    
    def to_dict(self):
        return {
            'job_id': self.id,
            'campaign_id': self.campaign_id,
            'business_account_id': self.business_account_id,
            'status': self.status,
            'file_path': self.file_path,
            'error': self.error,
            'progress': self.progress,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'campaign_name': self.campaign.name if self.campaign else None
        }

class Notification(db.Model):
    """Model for persistent in-app notifications"""
    __tablename__ = 'notifications'
    __table_args__ = (
        db.Index('idx_user_unread', 'user_id', 'unread', 'created_at'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    
    message = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(20), nullable=False, default='info')
    meta_data = db.Column(db.Text, nullable=True)
    
    unread = db.Column(db.Boolean, default=True, index=True)
    dismissed = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    read_at = db.Column(db.DateTime, nullable=True)
    
    business_account = db.relationship('BusinessAccount', backref='notifications')
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_account_id': self.business_account_id,
            'user_id': self.user_id,
            'message': self.message,
            'category': self.category,
            'metadata': json.loads(self.meta_data) if self.meta_data else {},
            'unread': self.unread,
            'dismissed': self.dismissed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None
        }

class BulkOperationJob(db.Model):
    """Model for tracking bulk operation jobs"""
    __tablename__ = 'bulk_operation_jobs'
    __table_args__ = (
        db.Index('idx_job_status', 'business_account_id', 'status', 'created_at'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, index=True, server_default=db.text("gen_random_uuid()::text"))
    job_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=True)
    
    operation_type = db.Column(db.String(50), nullable=False)
    operation_data = db.Column(db.Text, nullable=True)
    
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    progress = db.Column(db.Integer, default=0)
    result = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    business_account = db.relationship('BusinessAccount', backref='bulk_jobs')
    
    def to_dict(self):
        result_data = json.loads(self.result) if self.result else {}
        operation_data = json.loads(self.operation_data) if self.operation_data else {}
        
        return {
            'id': self.id,
            'job_id': self.job_id,
            'business_account_id': self.business_account_id,
            'user_id': self.user_id,
            'operation_type': self.operation_type,
            'operation_data': operation_data,
            'status': self.status,
            'progress': self.progress,
            'result': result_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class SurveyTemplate(db.Model):
    """Reusable survey template defining structure and default content."""
    __tablename__ = 'survey_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    version = db.Column(db.String(20), nullable=False, default='1.0')
    is_system = db.Column(db.Boolean, nullable=False, default=True)
    
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=True, index=True)
    
    description_en = db.Column(db.Text, nullable=True)
    description_fr = db.Column(db.Text, nullable=True)
    estimated_duration_minutes = db.Column(db.Integer, nullable=True, default=10)
    
    sections_config = db.Column(db.JSON, nullable=False, default={})
    
    default_driver_labels = db.Column(db.JSON, nullable=False, default=[])
    default_feature_count = db.Column(db.Integer, nullable=False, default=5)
    max_features = db.Column(db.Integer, nullable=False, default=9)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'is_system': self.is_system,
            'description_en': self.description_en,
            'description_fr': self.description_fr,
            'estimated_duration_minutes': self.estimated_duration_minutes,
            'sections_config': self.sections_config,
            'default_driver_labels': self.default_driver_labels,
            'default_feature_count': self.default_feature_count,
            'max_features': self.max_features,
        }


class ClassicSurveyConfig(db.Model):
    """Campaign-specific customization of a survey template. Created from template, editable per campaign."""
    __tablename__ = 'classic_survey_configs'
    __table_args__ = (
        db.Index('idx_classic_survey_config_campaign', 'campaign_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, unique=True)
    template_id = db.Column(db.Integer, db.ForeignKey('survey_templates.id'), nullable=False)
    
    sections_enabled = db.Column(db.JSON, nullable=False, default={'section_1': True, 'section_2': True, 'section_3': True})
    
    feature_count = db.Column(db.Integer, nullable=False, default=5)
    features = db.Column(db.JSON, nullable=False, default=[])
    
    driver_labels = db.Column(db.JSON, nullable=False, default=[])
    
    custom_prompts = db.Column(db.JSON, nullable=False, default={})
    
    frozen_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    campaign = db.relationship('Campaign', backref=db.backref('classic_survey_config', uselist=False, lazy='joined'))
    template = db.relationship('SurveyTemplate')
    
    def is_frozen(self):
        return self.frozen_at is not None
    
    def freeze(self):
        if not self.frozen_at:
            self.frozen_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'template_id': self.template_id,
            'sections_enabled': self.sections_enabled,
            'feature_count': self.feature_count,
            'features': self.features,
            'driver_labels': self.driver_labels,
            'custom_prompts': self.custom_prompts,
            'frozen_at': self.frozen_at.isoformat() if self.frozen_at else None,
            'is_frozen': self.is_frozen(),
        }
