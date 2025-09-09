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
            'snapshot_version': self.snapshot_version,
            'snapshot_created_at': self.snapshot_created_at.isoformat() if self.snapshot_created_at else None,
            'data_period_start': self.data_period_start.isoformat() if self.data_period_start else None,
            'data_period_end': self.data_period_end.isoformat() if self.data_period_end else None
        }
