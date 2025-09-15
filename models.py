from app import db
from datetime import datetime, date, timedelta
from sqlalchemy import or_, and_, func, text
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import uuid

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
    __table_args__ = (
        # Partial unique index to enforce single active campaign per business account
        db.Index('idx_single_active_campaign_per_account', 
                'business_account_id', 
                unique=True, 
                postgresql_where=db.text("status = 'active'")),
        # Regular index for common queries
        db.Index('idx_campaign_business_status', 'business_account_id', 'status'),
        db.Index('idx_campaign_dates', 'start_date', 'end_date'),
    )
    
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
    
    # Add participants relationship through campaign_participants
    participants = db.relationship('Participant', 
                                 secondary='campaign_participants',
                                 backref='campaigns',
                                 lazy='dynamic')
    
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
            'days_since_ended': self.days_since_ended(),
            'days_until_start': self.days_until_start()
        }
    
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
    
    def get_email_configuration(self):
        """Get email configuration for this business account"""
        return EmailConfiguration.query.filter_by(business_account_id=self.id).first()
    
    def has_email_configuration(self):
        """Check if business account has email configuration set up"""
        return self.get_email_configuration() is not None


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
    
    # SMTP Configuration
    smtp_server = db.Column(db.String(255), nullable=False)
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_username = db.Column(db.String(255), nullable=False)
    smtp_password_encrypted = db.Column(db.Text, nullable=False)  # Encrypted password
    use_tls = db.Column(db.Boolean, nullable=False, default=True)
    use_ssl = db.Column(db.Boolean, nullable=False, default=False)
    
    # Sender Configuration
    sender_name = db.Column(db.String(200), nullable=False)
    sender_email = db.Column(db.String(200), nullable=False)
    reply_to_email = db.Column(db.String(200), nullable=True)
    
    # Admin Notification Settings
    admin_notification_emails = db.Column(db.Text, nullable=True)  # JSON array of admin emails
    
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
        
        # Get encryption key from environment or generate one
        key = os.environ.get('EMAIL_ENCRYPTION_KEY')
        if not key:
            # In production, this should be set as an environment variable
            # For development, we'll generate a consistent key based on SECRET_KEY
            secret_key = os.environ.get('SESSION_SECRET', 'development-key').encode()
            key = base64.urlsafe_b64encode(secret_key[:32].ljust(32, b'0'))
        else:
            key = key.encode()
        
        fernet = Fernet(key)
        encrypted_password = fernet.encrypt(password.encode())
        return base64.urlsafe_b64encode(encrypted_password).decode()
    
    def _decrypt_password(self, encrypted_password):
        """Decrypt password using Fernet symmetric encryption"""
        from cryptography.fernet import Fernet
        import base64
        import os
        
        try:
            # Get encryption key
            key = os.environ.get('EMAIL_ENCRYPTION_KEY')
            if not key:
                secret_key = os.environ.get('SESSION_SECRET', 'development-key').encode()
                key = base64.urlsafe_b64encode(secret_key[:32].ljust(32, b'0'))
            else:
                key = key.encode()
            
            fernet = Fernet(key)
            encrypted_data = base64.urlsafe_b64decode(encrypted_password.encode())
            decrypted_password = fernet.decrypt(encrypted_data)
            return decrypted_password.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt email password: {e}")
            return None
    
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
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_password:
            data['smtp_password'] = self.get_smtp_password()
        
        return data
    
    def validate_configuration(self):
        """Validate email configuration fields"""
        errors = []
        
        if not self.smtp_server:
            errors.append("SMTP server is required")
        
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
        
        if self.reply_to_email and '@' not in self.reply_to_email:
            errors.append("Valid reply-to email is required")
        
        return errors
    
    def is_valid(self):
        """Check if configuration is valid"""
        return len(self.validate_configuration()) == 0
    
    @staticmethod
    def get_for_business_account(business_account_id):
        """Get email configuration for a business account"""
        return EmailConfiguration.query.filter_by(
            business_account_id=business_account_id,
            is_active=True
        ).first()


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
        db.Index('idx_campaign_participant_business', 'business_account_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
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
    campaign = db.relationship('Campaign', backref='campaign_participants', overlaps="participants")
    participant = db.relationship('Participant', foreign_keys='CampaignParticipant.participant_id', backref='campaign_participations', overlaps="campaigns")
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
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    
    # User credentials
    email = db.Column(db.String(200), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # User profile
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    
    # User role and permissions
    role = db.Column(db.String(50), nullable=False, default='admin', index=True)  # admin, viewer, manager
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)  # Note: Conflicts with UserMixin but maintained for DB compatibility
    
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
    )
    
    id = db.Column(db.Integer, primary_key=True)
    
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
            EmailDelivery.next_retry_at <= datetime.utcnow()
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
    ip_address = db.Column(db.String(45), nullable=True)  # For security audit purposes
    
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
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
                          resource_id=None, resource_name=None, details=None, ip_address=None):
        """Create a new audit log entry"""
        audit = AuditLog(
            business_account_id=business_account_id,
            user_email=user_email,
            user_name=user_name,
            action_type=action_type,
            action_description=action_description,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            resource_name=resource_name,
            ip_address=ip_address
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


class BrandingConfig(db.Model):
    """Branding Configuration model for business account-specific branding settings"""
    __tablename__ = 'branding_configs'
    __table_args__ = (
        # Only one branding configuration per business account
        db.UniqueConstraint('business_account_id', name='uq_branding_config_business_account'),
        db.Index('idx_branding_config_business_account', 'business_account_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    business_account_id = db.Column(db.Integer, db.ForeignKey('business_accounts.id'), nullable=False, index=True)
    
    def __init__(self, **kwargs):
        super(BrandingConfig, self).__init__(**kwargs)
    
    # Branding Configuration
    company_display_name = db.Column(db.String(200), nullable=True)  # Fallback to business_account.name if empty
    logo_filename = db.Column(db.String(255), nullable=True)  # Filename only, stored in /static/uploads/logos/{business_account_id}/
    
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_company_display_name(self):
        """Get company display name with fallback to business account name"""
        if self.company_display_name and self.company_display_name.strip():
            return self.company_display_name.strip()
        return self.business_account.name if self.business_account else 'Unknown Company'
    
    def get_logo_url(self):
        """Get logo URL path with proper fallback"""
        if self.logo_filename and self.business_account_id:
            return f'/static/uploads/logos/{self.business_account_id}/{self.logo_filename}'
        return None
    
    def has_logo(self):
        """Check if branding config has a logo configured"""
        return bool(self.logo_filename and self.logo_filename.strip())
    
    def get_logo_path(self):
        """Get full filesystem path to logo file"""
        import os
        from flask import current_app
        
        if not self.has_logo():
            return None
        
        # Construct full path: /static/uploads/logos/{business_account_id}/{filename}
        static_dir = os.path.join(current_app.root_path, 'static')
        logo_path = os.path.join(static_dir, 'uploads', 'logos', str(self.business_account_id), self.logo_filename)
        return logo_path
    
    def logo_exists_on_filesystem(self):
        """Check if logo file actually exists on filesystem"""
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
