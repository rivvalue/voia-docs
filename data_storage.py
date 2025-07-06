import json
from datetime import datetime, timedelta
from sqlalchemy import func
from app import db
from models import SurveyResponse
from flask import request

def get_dashboard_data():
    """Compile dashboard data for visualization"""
    try:
        # Basic statistics
        total_responses = SurveyResponse.query.count()
        
        # NPS distribution
        nps_distribution = db.session.query(
            SurveyResponse.nps_category,
            func.count(SurveyResponse.id).label('count')
        ).group_by(SurveyResponse.nps_category).all()
        
        # Calculate NPS score
        promoters = db.session.query(func.count(SurveyResponse.id)).filter(
            SurveyResponse.nps_score >= 9
        ).scalar() or 0
        
        detractors = db.session.query(func.count(SurveyResponse.id)).filter(
            SurveyResponse.nps_score <= 6
        ).scalar() or 0
        
        nps_score = ((promoters - detractors) / total_responses * 100) if total_responses > 0 else 0
        
        # Recent responses (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_responses = SurveyResponse.query.filter(
            SurveyResponse.created_at >= thirty_days_ago
        ).count()
        
        # Sentiment distribution
        sentiment_distribution = db.session.query(
            SurveyResponse.sentiment_label,
            func.count(SurveyResponse.id).label('count')
        ).filter(
            SurveyResponse.sentiment_label.isnot(None)
        ).group_by(SurveyResponse.sentiment_label).all()
        
        # Churn risk distribution
        churn_risk_data = db.session.query(
            SurveyResponse.churn_risk_score,
            SurveyResponse.company_name,
            SurveyResponse.nps_score
        ).filter(
            SurveyResponse.churn_risk_score.isnot(None)
        ).order_by(SurveyResponse.churn_risk_score.desc()).all()
        
        # High risk accounts - updated to use new categorical system
        high_risk_responses = SurveyResponse.query.filter(
            SurveyResponse.churn_risk_level.in_(['High'])
        ).all()
        
        high_risk_accounts = [
            {
                'company_name': row.company_name,
                'risk_level': row.churn_risk_level,
                'risk_score': row.churn_risk_score,
                'nps_score': row.nps_score
            }
            for row in high_risk_responses
        ]
        
        # Growth opportunities summary
        growth_opportunities = []
        responses_with_opportunities = SurveyResponse.query.filter(
            SurveyResponse.growth_opportunities.isnot(None)
        ).all()
        
        for response in responses_with_opportunities:
            if response.growth_opportunities:
                try:
                    opportunities = json.loads(response.growth_opportunities)
                    for opp in opportunities:
                        growth_opportunities.append({
                            'company_name': response.company_name,
                            'type': opp.get('type', 'unknown'),
                            'description': opp.get('description', ''),
                            'action': opp.get('action', '')
                        })
                except json.JSONDecodeError:
                    continue
        
        # Key themes aggregation
        all_themes = {}
        responses_with_themes = SurveyResponse.query.filter(
            SurveyResponse.key_themes.isnot(None)
        ).all()
        
        for response in responses_with_themes:
            if response.key_themes:
                try:
                    themes = json.loads(response.key_themes)
                    for theme in themes:
                        theme_name = theme.get('theme', 'unknown')
                        if theme_name not in all_themes:
                            all_themes[theme_name] = {'count': 0, 'sentiments': []}
                        all_themes[theme_name]['count'] += 1
                        all_themes[theme_name]['sentiments'].append(theme.get('sentiment', 'neutral'))
                except json.JSONDecodeError:
                    continue
        
        # Average ratings
        avg_satisfaction = db.session.query(func.avg(SurveyResponse.satisfaction_rating)).filter(
            SurveyResponse.satisfaction_rating.isnot(None)
        ).scalar() or 0
        
        avg_product_value = db.session.query(func.avg(SurveyResponse.product_value_rating)).filter(
            SurveyResponse.product_value_rating.isnot(None)
        ).scalar() or 0
        
        avg_service = db.session.query(func.avg(SurveyResponse.service_rating)).filter(
            SurveyResponse.service_rating.isnot(None)
        ).scalar() or 0
        
        avg_pricing = db.session.query(func.avg(SurveyResponse.pricing_rating)).filter(
            SurveyResponse.pricing_rating.isnot(None)
        ).scalar() or 0
        
        return {
            'total_responses': total_responses,
            'nps_score': round(nps_score, 1),
            'recent_responses': recent_responses,
            'nps_distribution': [
                {'category': row.nps_category, 'count': row.count}
                for row in nps_distribution
            ],
            'sentiment_distribution': [
                {'sentiment': row.sentiment_label, 'count': row.count}
                for row in sentiment_distribution
            ],
            'high_risk_accounts': high_risk_accounts,
            'growth_opportunities': growth_opportunities,
            'key_themes': [
                {'theme': theme, 'count': data['count']}
                for theme, data in all_themes.items()
            ],
            'average_ratings': {
                'satisfaction': round(avg_satisfaction, 1),
                'product_value': round(avg_product_value, 1),
                'service': round(avg_service, 1),
                'pricing': round(avg_pricing, 1)
            }
        }
        
    except Exception as e:
        raise Exception(f"Error compiling dashboard data: {e}")
