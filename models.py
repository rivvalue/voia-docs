from app import db
from datetime import datetime, date, timedelta
from sqlalchemy import or_, and_
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import uuid
from sqlalchemy import or_, and_

class SurveyResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
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
    
    # Text responses
    improvement_feedback = db.Column(db.Text)
    recommendation_reason = db.Column(db.Text)
    additional_comments = db.Column(db.Text)
    
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
    
    # Campaign tracking
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=True, index=True)
    
    # Foreign key to CampaignParticipant for proper association tracking
    campaign_participant_id = db.Column(db.Integer, db.ForeignKey('campaign_participants.id'), nullable=True, index=True)
    
    campaign = db.relationship('Campaign', backref=db.backref('responses', lazy='dynamic'))
    campaign_participant = db.relationship('CampaignParticipant', foreign_keys='SurveyResponse.campaign_participant_id', backref='survey_responses')
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
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
            'improvement_feedback': self.improvement_feedback,
            'recommendation_reason': self.recommendation_reason,
            'additional_comments': self.additional_comments,
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
            'campaign_id': self.campaign_id,
            'campaign_name': self.campaign.name if self.campaign else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
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


class Campaign(db.Model):
    """Campaign model for tracking feedback collection periods"""
    __tablename__ = 'campaigns'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='draft', index=True)  # draft, ready, active, completed
    
    # Client tracking (for future multi-client support)
    client_identifier = db.Column(db.String(200), nullable=False, default='archelo_group', index=True)
    
    # Business account ownership (Phase 2.5: Schema Fix)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=True, index=True)
    business_account = db.relationship('BusinessAccount', backref=db.backref('campaigns', lazy='dynamic'))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status,
            'client_identifier': self.client_identifier,
            'business_account_id': self.business_account_id,
            'business_account_name': self.business_account.name if self.business_account else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'response_count': len([r for r in SurveyResponse.query.filter_by(campaign_id=self.id).all()]),
            'is_active': self.is_active(),
            'days_remaining': self.days_remaining(),
            'days_since_ended': self.days_since_ended()
        }
    
    def is_active(self):
        """Check if campaign is currently active"""
        return self.status == 'active'
    
    def is_ready_for_activation(self):
        """Check if campaign can be activated (has participants and description)"""
        if self.status != 'ready':
            return False
        today = date.today()
        return self.start_date == today and self.description and len(self.participants) > 0
    
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
    
    def close_campaign(self):
        """Mark campaign as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
    
    def mark_ready(self):
        """Mark campaign as ready for activation"""
        if self.status == 'draft' and self.description and len(self.participants) > 0:
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
    name = db.Column(db.String(200), nullable=False, index=True)
    account_type = db.Column(db.String(20), nullable=False, default='customer', index=True)  # customer, demo
    
    # Contact information
    contact_email = db.Column(db.String(200), nullable=True)
    contact_name = db.Column(db.String(200), nullable=True)
    
    # Account status
    status = db.Column(db.String(20), nullable=False, default='active', index=True)  # active, suspended, trial
    
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Participant(db.Model):
    """Participant model for campaign-based surveys with token authentication and origin tracking"""
    __tablename__ = 'participants'
    __table_args__ = (
        db.UniqueConstraint('business_account_id', 'email', name='uq_participant_business_email'),
        db.Index('idx_participant_business_email', 'business_account_id', 'email'),
        db.Index('idx_participant_source', 'source'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=True, index=True)  # NULL for trial users
    # Note: No direct campaign relationship - associations managed via CampaignParticipant table
    
    # Participant information
    email = db.Column(db.String(200), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200), nullable=True)
    
    # Origin tracking for management visibility
    source = db.Column(db.String(20), nullable=False, default='trial', index=True)  # 'trial', 'admin_single', 'admin_bulk'
    
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
            'admin_bulk': {'text': 'Bulk Upload', 'class': 'badge-warning'}
        }
        return origin_badges.get(self.source, {'text': 'Unknown', 'class': 'badge-secondary'})
    
    def set_appropriate_status_for_context(self, is_trial=False):
        """Set appropriate status based on creation context"""
        if is_trial:
            self.status = 'invited'  # Trial users are immediately invited
        else:
            self.status = 'created'   # Business participants are created but not campaign-specific yet


class CampaignParticipant(db.Model):
    """Association model for campaign-participant relationships with individual tokens"""
    __tablename__ = 'campaign_participants'
    __table_args__ = (
        db.UniqueConstraint('campaign_id', 'participant_id', name='uq_campaign_participant'),
        db.Index('idx_campaign_participant', 'campaign_id', 'participant_id'),
        db.Index('idx_campaign_participant_token', 'token'),
        db.Index('idx_campaign_participant_business', 'business_account_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), nullable=False, index=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False, index=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    
    # Token authentication (unique per campaign-participant pair)
    token = db.Column(db.String(255), nullable=True, unique=True, index=True)
    
    # Status tracking per campaign
    status = db.Column(db.String(20), nullable=False, default='invited', index=True)  # invited, started, completed
    
    # Timestamps per campaign-participant relationship
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    invited_at = db.Column(db.DateTime, nullable=True, index=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    campaign = db.relationship('Campaign', backref='campaign_participants')
    participant = db.relationship('Participant', foreign_keys='CampaignParticipant.participant_id', backref='campaign_participations')
    business_account = db.relationship('BusinessAccount', backref='campaign_participants')
    
    def to_dict(self):
        return {
            'id': self.id,
            'campaign_id': self.campaign_id,
            'participant_id': self.participant_id,
            'business_account_id': self.business_account_id,
            'token': self.token,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'campaign_name': self.campaign.name if self.campaign else None,
            'participant_email': self.participant.email if self.participant else None,
            'participant_name': self.participant.name if self.participant else None
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
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    
    # User credentials
    email = db.Column(db.String(200), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # User profile
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    
    # User role and permissions
    role = db.Column(db.String(50), nullable=False, default='admin', index=True)  # admin, viewer, manager
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)  # TODO: Rename to avoid UserMixin conflict in future migration
    
    # Email verification
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    email_verification_token = db.Column(db.String(255), nullable=True)
    
    # Password reset
    password_reset_token = db.Column(db.String(255), nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)
    
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
        return check_password_hash(self.password_hash, password)
    
    def generate_password_reset_token(self):
        """Generate password reset token"""
        self.password_reset_token = str(uuid.uuid4())
        self.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        return self.password_reset_token
    
    def generate_email_verification_token(self):
        """Generate email verification token"""
        self.email_verification_token = str(uuid.uuid4())
        return self.email_verification_token
    
    def verify_email(self):
        """Mark email as verified"""
        self.email_verified = True
        self.email_verification_token = None
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login_at = datetime.utcnow()
    
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
        """Check if user has specific permission"""
        role_permissions = {
            'admin': ['view', 'create', 'edit', 'delete', 'manage_users', 'export_data', 'manage_participants'],
            'manager': ['view', 'create', 'edit', 'export_data', 'manage_participants'],
            'viewer': ['view']
        }
        return permission in role_permissions.get(self.role, [])
    
    def to_dict(self):
        return {
            'id': self.id,
            'business_account_id': self.business_account_id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'role': self.role,
            'is_active': self.is_active,
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


class UserSession(db.Model):
    """User session management for business account users (Phase 2)"""
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('business_account_users.id'), nullable=False, index=True)
    
    # Session data
    session_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    session_data = db.Column(db.Text, nullable=True)  # JSON session data
    
    # Session tracking
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 support
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
        ).filter(UserSession.expires_at > datetime.utcnow()).first()
    
    @staticmethod
    def cleanup_expired_sessions():
        """Clean up expired sessions"""
        expired_sessions = UserSession.query.filter(
            UserSession.expires_at <= datetime.utcnow()
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
                UserSession.is_active.is_(True),
                UserSession.expires_at > datetime.utcnow()
            )
        
        return query.order_by(UserSession.last_activity_at.desc()).all()
    
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
