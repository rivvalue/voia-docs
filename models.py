from app import db
from datetime import datetime, date
import json

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
    campaign = db.relationship('Campaign', backref='responses')
    
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
    status = db.Column(db.String(20), nullable=False, default='active', index=True)  # active, completed
    
    # Client tracking (for future multi-client support)
    client_identifier = db.Column(db.String(200), nullable=False, default='archelo_group', index=True)
    
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'response_count': len(self.responses) if hasattr(self, 'responses') else 0,
            'is_active': self.is_active(),
            'days_remaining': self.days_remaining()
        }
    
    def is_active(self):
        """Check if campaign is currently active (within date range and not completed)"""
        if self.status != 'active':
            return False
        today = date.today()
        return self.start_date <= today <= self.end_date
    
    def days_remaining(self):
        """Calculate days remaining in campaign"""
        if self.status != 'active':
            return 0
        today = date.today()
        if today > self.end_date:
            return 0
        return (self.end_date - today).days
    
    def close_campaign(self):
        """Mark campaign as completed"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
    
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
            db.or_(
                db.and_(Campaign.start_date <= start_date, Campaign.end_date >= start_date),
                db.and_(Campaign.start_date <= end_date, Campaign.end_date >= end_date),
                db.and_(Campaign.start_date >= start_date, Campaign.end_date <= end_date)
            )
        )
        
        if exclude_id:
            query = query.filter(Campaign.id != exclude_id)
            
        return query.first() is not None
