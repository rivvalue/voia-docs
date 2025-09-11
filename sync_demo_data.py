#!/usr/bin/env python3
"""
Demo Data Sync Script
Copies survey responses from development SQLite to deployment PostgreSQL
"""

import os
import sys
import json
from datetime import datetime
from app import app, db
from models import SurveyResponse, Campaign

def export_dev_data():
    """Export survey responses from development database"""
    print("🔍 Exporting development survey data...")
    
    # Query all survey responses from development
    responses = SurveyResponse.query.all()
    campaigns = Campaign.query.all()
    
    exported_data = {
        'campaigns': [],
        'responses': []
    }
    
    # Export campaigns
    for campaign in campaigns:
        exported_data['campaigns'].append({
            'id': campaign.id,
            'name': campaign.name,
            'description': campaign.description,
            'status': campaign.status,
            'start_date': campaign.start_date.isoformat(),
            'end_date': campaign.end_date.isoformat(),
            'created_at': campaign.created_at.isoformat()
        })
    
    # Export survey responses
    for response in responses:
        exported_data['responses'].append({
            'company_name': response.company_name,
            'respondent_name': response.respondent_name,
            'respondent_email': response.respondent_email,
            'tenure_with_fc': response.tenure_with_fc,
            'nps_score': response.nps_score,
            'nps_category': response.nps_category,
            'satisfaction_rating': response.satisfaction_rating,
            'product_value_rating': response.product_value_rating,
            'service_rating': response.service_rating,
            'pricing_rating': response.pricing_rating,
            'improvement_feedback': response.improvement_feedback,
            'recommendation_reason': response.recommendation_reason,
            'additional_comments': response.additional_comments,
            'sentiment_score': response.sentiment_score,
            'sentiment_label': response.sentiment_label,
            'key_themes': response.key_themes,
            'churn_risk_score': response.churn_risk_score,
            'churn_risk_level': response.churn_risk_level,
            'churn_risk_factors': response.churn_risk_factors,
            'growth_opportunities': response.growth_opportunities,
            'account_risk_factors': response.account_risk_factors,
            'growth_factor': response.growth_factor,
            'growth_rate': response.growth_rate,
            'growth_range': response.growth_range,
            'commercial_value': response.commercial_value,
            'campaign_id': response.campaign_id,
            'created_at': response.created_at.isoformat() if response.created_at else None,
            'analyzed_at': response.analyzed_at.isoformat() if response.analyzed_at else None
        })
    
    print(f"✅ Exported {len(exported_data['campaigns'])} campaigns and {len(exported_data['responses'])} responses")
    return exported_data

def import_to_deployment(exported_data):
    """Import data to deployment database"""
    print("🚀 Importing data to deployment database...")
    
    # Clear existing data (for demo purposes)
    print("🧹 Clearing existing deployment data...")
    SurveyResponse.query.delete()
    Campaign.query.delete()
    db.session.commit()
    
    # Import campaigns first
    print("📊 Importing campaigns...")
    for camp_data in exported_data['campaigns']:
        existing = Campaign.query.get(camp_data['id'])
        if not existing:
            campaign = Campaign(
                id=camp_data['id'],
                name=camp_data['name'],
                description=camp_data['description'],
                status=camp_data['status'],
                start_date=datetime.fromisoformat(camp_data['start_date']).date(),
                end_date=datetime.fromisoformat(camp_data['end_date']).date(),
                created_at=datetime.fromisoformat(camp_data['created_at'])
            )
            db.session.add(campaign)
    
    db.session.commit()
    print(f"✅ Imported {len(exported_data['campaigns'])} campaigns")
    
    # Import survey responses
    print("📋 Importing survey responses...")
    for resp_data in exported_data['responses']:
        # Check if response already exists (by email + campaign to avoid duplicates)
        existing = SurveyResponse.query.filter_by(
            respondent_email=resp_data['respondent_email'],
            campaign_id=resp_data['campaign_id']
        ).first()
        
        if not existing:
            response = SurveyResponse(
                company_name=resp_data['company_name'],
                respondent_name=resp_data['respondent_name'],
                respondent_email=resp_data['respondent_email'],
                tenure_with_fc=resp_data['tenure_with_fc'],
                nps_score=resp_data['nps_score'],
                nps_category=resp_data['nps_category'],
                satisfaction_rating=resp_data['satisfaction_rating'],
                product_value_rating=resp_data['product_value_rating'],
                service_rating=resp_data['service_rating'],
                pricing_rating=resp_data['pricing_rating'],
                improvement_feedback=resp_data['improvement_feedback'],
                recommendation_reason=resp_data['recommendation_reason'],
                additional_comments=resp_data['additional_comments'],
                sentiment_score=resp_data['sentiment_score'],
                sentiment_label=resp_data['sentiment_label'],
                key_themes=resp_data['key_themes'],
                churn_risk_score=resp_data['churn_risk_score'],
                churn_risk_level=resp_data['churn_risk_level'],
                churn_risk_factors=resp_data['churn_risk_factors'],
                growth_opportunities=resp_data['growth_opportunities'],
                account_risk_factors=resp_data['account_risk_factors'],
                growth_factor=resp_data['growth_factor'],
                growth_rate=resp_data['growth_rate'],
                growth_range=resp_data['growth_range'],
                commercial_value=resp_data['commercial_value'],
                campaign_id=resp_data['campaign_id'],
                created_at=datetime.fromisoformat(resp_data['created_at']) if resp_data['created_at'] else datetime.utcnow(),
                analyzed_at=datetime.fromisoformat(resp_data['analyzed_at']) if resp_data['analyzed_at'] else None
            )
            db.session.add(response)
    
    db.session.commit()
    print(f"✅ Imported {len(exported_data['responses'])} survey responses")

def verify_sync():
    """Verify the sync worked correctly"""
    print("🔍 Verifying sync results...")
    
    total_responses = SurveyResponse.query.count()
    pricing_responses = SurveyResponse.query.filter(SurveyResponse.pricing_rating.isnot(None)).count()
    
    if pricing_responses > 0:
        avg_pricing = db.session.query(db.func.avg(SurveyResponse.pricing_rating)).filter(
            SurveyResponse.pricing_rating.isnot(None)
        ).scalar()
        print(f"✅ Total responses: {total_responses}")
        print(f"✅ Pricing responses: {pricing_responses}")
        print(f"✅ Average pricing: {round(float(avg_pricing), 2) if avg_pricing else 0}")
    else:
        print("❌ No pricing responses found after sync")

def main():
    """Main sync function"""
    with app.app_context():
        print("🚀 Starting demo data sync...")
        print(f"📊 Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')[:50]}...")
        
        # Export from development
        exported_data = export_dev_data()
        
        # Import to deployment
        import_to_deployment(exported_data)
        
        # Verify
        verify_sync()
        
        print("🎉 Demo data sync completed!")

if __name__ == '__main__':
    main()