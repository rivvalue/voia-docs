#!/usr/bin/env python3
"""
Lightweight Bulk Demo Data Generator for Archelo Group  
Direct database access without full app initialization
"""

import os
import sys
import random
import json
from datetime import datetime, timedelta, date

# Set up minimal Flask app context
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Import models after db initialization
from models import BusinessAccount, Campaign, Participant, CampaignParticipant, SurveyResponse

# Campaign configurations - Updated for high-volume testing
CAMPAIGNS = {
    "Q1 2025": {
        "name": "Loyalty measurement Q1 2025",
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 3, 31),
        "responses": 1000,
        "company_reuse": 0
    },
    "Q2 2025": {
        "name": "Loyalty measurement Q2 2025",
        "start_date": date(2025, 4, 1),
        "end_date": date(2025, 6, 30),
        "responses": 1000,
        "company_reuse": 40
    },
    "Q3 2025": {
        "name": "Loyalty measurement Q3 2025",
        "start_date": date(2025, 7, 1),
        "end_date": date(2025, 9, 30),
        "responses": 1000,
        "company_reuse": 50
    }
}

# Demo company pool - Expanded to 70 companies
COMPANIES = [
    "CloudSync Technologies", "DataFlow Solutions", "API Masters Inc", "TechVision Corp",
    "SecureBank Financial", "FinanceFirst Ltd", "InvestPro Group", "PaymentHub",
    "MediCare Plus", "HealthTech Partners", "WellBeing Systems", "CareConnect",
    "RetailPro International", "EcomGrow Solutions", "ShopFlow Systems", "MarketReach",
    "LogiTrack Express", "SupplyChain Pro", "FreightFlow Inc", "CargoSync",
    "EduTech Academy", "LearnPath Systems", "KnowledgeHub Inc", "TrainingPro",
    "GreenEnergy Solutions", "SolarTech Industries", "EcoPower Systems", "RenewCorp",
    "FoodService Partners", "RestaurantTech Inc", "MenuMaster Systems", "ChefConnect",
    "TravelBook Solutions", "HotelSync Technologies", "TourismPro Inc", "BookingFlow",
    "AutoParts Wholesale", "VehicleTech Systems", "FleetManager Pro", "DriveSync",
    "ManufacturePro Inc", "IndustryTech Solutions", "ProductionFlow Systems", "FactorySync",
    "MediaStream Corp", "ContentHub Technologies", "BroadcastPro Inc", "StreamFlow",
    "LegalTech Partners", "ComplianceSync Inc", "JusticeFlow Systems", "LawyerHub",
    "PropertyTech Solutions", "RealEstateFlow Inc", "BuildingSync Pro", "HomeHub",
    "InsureTech Corp", "PolicyFlow Systems", "ClaimSync Solutions", "RiskHub",
    "ConsultPro Partners", "AdvisoryTech Inc", "StrategyFlow Systems", "ExpertHub",
    "CyberDefense Corp", "NetworkGuard Solutions", "CloudShield Technologies", "DataVault Inc",
    "Analytics360 Group", "InsightPro Systems", "MetricsHub Technologies", "ReportFlow Inc",
    "DevOps Masters", "CodePipeline Solutions", "DeployFast Technologies", "BuildSync Pro"
]

FIRST_NAMES = ["Sarah", "Michael", "Jennifer", "David", "Lisa", "James", "Emily", "Robert",
               "Jessica", "John", "Amanda", "William", "Michelle", "Richard", "Elizabeth", "Thomas"]

LAST_NAMES = ["Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
              "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor"]

ROLES = ["CEO", "CTO", "CFO", "COO", "VP Operations", "VP Sales", "Director", "Manager"]

# Segmentation attributes for participant personalization
REGIONS = ["North America", "EMEA", "APAC"]

CUSTOMER_TIERS = ["T1: Strategic", "T2: Managed", "T3: Self-serve"]

LANGUAGES = ["en", "en", "en", "en", "en", "es", "fr"]  # 70% English, 15% Spanish, 15% French

PROMOTER_FEEDBACK = [
    "Excellent service and product quality. The team is very responsive and professional.",
    "Outstanding support experience. They truly understand our business needs.",
    "Best-in-class solution. The ROI has exceeded our expectations significantly.",
    "Fantastic product with great features. Customer success team is always helpful.",
]

PASSIVE_FEEDBACK = [
    "Good product overall, but pricing could be more competitive for our scale.",
    "Solid service, though some features we need are still missing from the platform.",
    "Works well for most needs, but documentation could be more comprehensive.",
    "Decent solution with room for improvement in user experience and interface.",
]

DETRACTOR_FEEDBACK = [
    "Pricing is too high for the value received. Support response is often slow.",
    "Product has frequent bugs and stability issues. Very frustrating experience.",
    "Poor customer service and lack of responsiveness to critical issues.",
    "System downtime is unacceptable. Missing key features we were promised.",
]

KEY_THEMES = [
    "Service Quality", "Pricing Concerns", "Product Features", "Support Responsiveness",
    "Integration Capabilities", "User Experience", "System Reliability", "Documentation Quality",
]


def generate_nps_score():
    rand = random.random()
    if rand < 0.30:
        return random.choice([9, 9, 10])
    elif rand < 0.70:
        return random.choice([7, 7, 8, 8])
    else:
        return random.choice([3, 4, 5, 6])


def get_nps_category(score):
    if score >= 9:
        return "Promoter"
    elif score >= 7:
        return "Passive"
    else:
        return "Detractor"


def generate_sentiment(nps_score):
    if nps_score >= 9:
        return random.uniform(0.6, 0.9), "positive"
    elif nps_score >= 7:
        return random.uniform(-0.2, 0.2), "neutral"
    else:
        return random.uniform(-0.8, -0.3), "negative"


def generate_churn_risk(nps_score):
    if nps_score >= 9:
        return random.uniform(0.05, 0.25), "Minimal"
    elif nps_score >= 7:
        return random.uniform(0.25, 0.65), random.choice(["Low", "Medium"])
    else:
        return random.uniform(0.55, 0.95), random.choice(["Medium", "High"])


def generate_feedback(nps_category):
    if nps_category == "Promoter":
        return random.choice(PROMOTER_FEEDBACK)
    elif nps_category == "Passive":
        return random.choice(PASSIVE_FEEDBACK)
    else:
        return random.choice(DETRACTOR_FEEDBACK)


def generate_timestamp(start_date, end_date):
    days_between = (end_date - start_date).days
    random_days = random.randint(0, days_between)
    result_date = start_date + timedelta(days=random_days)
    return datetime.combine(result_date, datetime.min.time()).replace(
        hour=random.randint(9, 18), minute=random.randint(0, 59)
    )


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--campaign', choices=['Q1 2025', 'Q2 2025', 'Q3 2025'], required=True)
    args = parser.parse_args()
    
    config = CAMPAIGNS[args.campaign]
    
    print(f"\n{'='*70}")
    print(f"Generating Demo Data: {config['name']}")
    print(f"{'='*70}\n")
    
    with app.app_context():
        try:
            business_account = BusinessAccount.query.filter_by(name="Archelo Group inc").first()
            if not business_account:
                print("❌ Error: Business account not found!")
                return
            
            print(f"✓ Business Account: {business_account.name}")
            
            # Find or create campaign
            campaign = Campaign.query.filter_by(
                business_account_id=business_account.id,
                name=config['name']
            ).first()
            
            if not campaign:
                campaign = Campaign(
                    business_account_id=business_account.id,
                    name=config['name'],
                    description=f"Quarterly customer loyalty measurement Q{args.campaign[1]} 2025",
                    start_date=config['start_date'],
                    end_date=config['end_date'],
                    status='active',
                    client_identifier='archelo_group'
                )
                db.session.add(campaign)
                db.session.flush()
                print(f"✓ Created campaign: {campaign.name}")
            else:
                print(f"✓ Found campaign: {campaign.name} (status: {campaign.status})")
            
            # Get existing companies for reuse
            existing_companies = []
            if config['company_reuse'] > 0:
                prev_responses = SurveyResponse.query.join(Campaign).filter(
                    Campaign.business_account_id == business_account.id,
                    SurveyResponse.campaign_id != campaign.id
                ).all()
                existing_companies = list(set([r.company_name for r in prev_responses]))
            
            # Select companies
            num_reuse = int(len(existing_companies) * (config['company_reuse'] / 100))
            reused = random.sample(existing_companies, min(num_reuse, len(existing_companies))) if existing_companies else []
            new_cos = [c for c in COMPANIES if c not in existing_companies]
            new = random.sample(new_cos, min(config['responses'] - num_reuse, len(new_cos)))
            companies = reused + new
            
            print(f"✓ Companies: {len(reused)} reused + {len(new)} new\n")
            
            # Generate responses
            nps_dist = {"Promoter": 0, "Passive": 0, "Detractor": 0}
            company_commercial_values = {}  # Track company-level commercial values for consistency
            
            for i in range(config['responses']):
                company = random.choice(companies)
                first = random.choice(FIRST_NAMES)
                last = random.choice(LAST_NAMES)
                role = random.choice(ROLES)
                name = f"{first} {last}"
                email = f"{first.lower()}.{last.lower()}@{company.lower().replace(' ', '')}.com"
                
                # Segmentation attributes
                region = random.choice(REGIONS)
                customer_tier = random.choice(CUSTOMER_TIERS)
                language = random.choice(LANGUAGES)
                
                # Company-level commercial value (consistent across all participants from same company)
                if company not in company_commercial_values:
                    company_commercial_values[company] = random.uniform(10000, 500000)
                commercial_value = company_commercial_values[company]
                
                # Get or create participant
                participant = Participant.query.filter_by(
                    business_account_id=business_account.id,
                    email=email
                ).first()
                
                if not participant:
                    participant = Participant(
                        business_account_id=business_account.id,
                        email=email,
                        name=name,
                        company_name=company,
                        role=role,
                        region=region,
                        customer_tier=customer_tier,
                        language=language,
                        company_commercial_value=commercial_value,
                        source='admin_bulk',
                        status='created',
                        token=str(__import__('uuid').uuid4())
                    )
                    db.session.add(participant)
                    db.session.flush()
                else:
                    # Update segmentation fields and sync company commercial value if participant already exists
                    participant.role = role
                    participant.region = region
                    participant.customer_tier = customer_tier
                    participant.language = language
                    participant.company_commercial_value = commercial_value
                
                # Get or create campaign participant
                cp = CampaignParticipant.query.filter_by(
                    campaign_id=campaign.id,
                    participant_id=participant.id
                ).first()
                
                if not cp:
                    cp = CampaignParticipant(
                        campaign_id=campaign.id,
                        participant_id=participant.id,
                        business_account_id=business_account.id,
                        status='created',
                        token=str(__import__('uuid').uuid4())
                    )
                    db.session.add(cp)
                    db.session.flush()
                
                # Generate response
                nps_score = generate_nps_score()
                nps_cat = get_nps_category(nps_score)
                sent_score, sent_label = generate_sentiment(nps_score)
                churn_score, churn_level = generate_churn_risk(nps_score)
                
                response = SurveyResponse(
                    campaign_id=campaign.id,
                    campaign_participant_id=cp.id,
                    company_name=company,
                    respondent_name=name,
                    respondent_email=email,
                    tenure_with_fc=random.choice(["< 1 year", "1-2 years", "2-3 years", "3-5 years", "> 5 years"]),
                    nps_score=nps_score,
                    nps_category=nps_cat,
                    satisfaction_rating=random.randint(1, 10),
                    product_value_rating=random.randint(1, 10),
                    service_rating=random.randint(1, 10),
                    pricing_rating=random.randint(1, 10),
                    improvement_feedback=generate_feedback(nps_cat),
                    recommendation_reason=generate_feedback(nps_cat),
                    sentiment_score=sent_score,
                    sentiment_label=sent_label,
                    key_themes=json.dumps(random.sample(KEY_THEMES, random.randint(2, 3))),
                    churn_risk_score=churn_score,
                    churn_risk_level=churn_level,
                    churn_risk_factors=json.dumps(random.sample(KEY_THEMES, 2)),
                    source_type='conversational',
                    created_at=generate_timestamp(config['start_date'], config['end_date']),
                    analyzed_at=datetime.utcnow()
                )
                
                db.session.add(response)
                nps_dist[nps_cat] += 1
                
                if (i + 1) % 50 == 0:
                    print(f"   Progress: {i + 1}/{config['responses']}")
            
            db.session.commit()
            
            total = sum(nps_dist.values())
            nps = (nps_dist["Promoter"] / total * 100 - nps_dist["Detractor"] / total * 100)
            
            print(f"\n✅ Generated {config['responses']} responses")
            print(f"📊 NPS: {nps:.1f} (P:{nps_dist['Promoter']}, Pa:{nps_dist['Passive']}, D:{nps_dist['Detractor']})")
            print(f"\n✓ Next: Complete campaign '{campaign.name}' to generate snapshot\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
