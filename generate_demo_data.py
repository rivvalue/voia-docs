#!/usr/bin/env python3
"""
Bulk Demo Data Generator for Archelo Group
Generates realistic survey responses for demo campaigns with transaction safety
"""

import os
import sys
import random
import json
from datetime import datetime, timedelta, date
from app import app, db
from models import (
    BusinessAccount, Campaign, Participant, CampaignParticipant, 
    SurveyResponse
)

# Campaign configurations
CAMPAIGNS = {
    "Q1 2025": {
        "name": "Loyalty measurement Q1 2025",
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 3, 31),
        "responses": 180,
        "company_reuse": 0  # First campaign, no reuse
    },
    "Q2 2025": {
        "name": "Loyalty measurement Q2 2025",
        "start_date": date(2025, 4, 1),
        "end_date": date(2025, 6, 30),
        "responses": 220,
        "company_reuse": 40  # 40% companies from Q1
    },
    "Q3 2025": {
        "name": "Loyalty measurement Q3 2025",
        "start_date": date(2025, 7, 1),
        "end_date": date(2025, 9, 30),
        "responses": 200,
        "company_reuse": 50  # 50% companies from Q1+Q2
    }
}

# Demo company pool
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
    "ConsultPro Partners", "AdvisoryTech Inc", "StrategyFlow Systems", "ExpertHub"
]

# Name pool for participants
FIRST_NAMES = [
    "Sarah", "Michael", "Jennifer", "David", "Lisa", "James", "Emily", "Robert",
    "Jessica", "John", "Amanda", "William", "Michelle", "Richard", "Elizabeth", "Thomas",
    "Ashley", "Christopher", "Stephanie", "Daniel", "Nicole", "Matthew", "Rebecca", "Mark",
    "Laura", "Donald", "Karen", "Paul", "Nancy", "Andrew", "Betty", "Joshua",
    "Margaret", "Kenneth", "Sandra", "Kevin", "Angela", "Brian", "Donna", "George",
    "Carol", "Edward", "Ruth", "Ronald", "Sharon", "Timothy", "Helen", "Jason"
]

LAST_NAMES = [
    "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
    "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor",
    "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris", "Clark",
    "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott",
    "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson", "Baker",
    "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts", "Turner", "Phillips"
]

ROLES = ["CEO", "CTO", "CFO", "COO", "VP Operations", "VP Sales", "Director", "Manager"]

# Feedback templates by NPS category
PROMOTER_FEEDBACK = [
    "Excellent service and product quality. The team is very responsive and professional.",
    "Outstanding support experience. They truly understand our business needs.",
    "Best-in-class solution. The ROI has exceeded our expectations significantly.",
    "Fantastic product with great features. Customer success team is always helpful.",
    "Superior quality and reliability. Would highly recommend to other businesses.",
    "Exceptional service delivery. The platform has transformed our operations.",
    "Great partnership with excellent communication and support throughout.",
    "Top-tier solution that delivers consistent value. Very satisfied overall.",
]

PASSIVE_FEEDBACK = [
    "Good product overall, but pricing could be more competitive for our scale.",
    "Solid service, though some features we need are still missing from the platform.",
    "Works well for most needs, but documentation could be more comprehensive.",
    "Decent solution with room for improvement in user experience and interface.",
    "Satisfactory performance, but competitors offer similar features at lower cost.",
    "Product meets our basic requirements, but lacks some advanced capabilities.",
    "Generally positive experience, though support response times vary significantly.",
    "Adequate solution for now, but evaluating alternatives for future expansion.",
]

DETRACTOR_FEEDBACK = [
    "Pricing is too high for the value received. Support response is often slow.",
    "Product has frequent bugs and stability issues. Very frustrating experience.",
    "Poor customer service and lack of responsiveness to critical issues.",
    "System downtime is unacceptable. Missing key features we were promised.",
    "Implementation was problematic and took much longer than expected.",
    "Integration challenges persist. Technical support lacks necessary expertise.",
    "Not meeting our needs. Considering switching to competitor solutions.",
    "Disappointed with overall experience. Product doesn't deliver as advertised.",
]

# Key themes pool
KEY_THEMES = [
    "Service Quality", "Pricing Concerns", "Product Features", "Support Responsiveness",
    "Integration Capabilities", "User Experience", "System Reliability", "Documentation Quality",
    "Implementation Process", "Value for Money", "Technical Support", "Account Management",
    "Performance Issues", "Feature Requests", "Training Resources", "Communication",
    "Innovation", "Scalability", "Security", "Customization Options"
]


def get_nps_category(score):
    """Get NPS category from score"""
    if score >= 9:
        return "Promoter"
    elif score >= 7:
        return "Passive"
    else:
        return "Detractor"


def generate_nps_score(distribution="realistic"):
    """Generate NPS score with realistic distribution"""
    rand = random.random()
    if distribution == "realistic":
        # Realistic B2B distribution: 30% Promoters, 40% Passives, 30% Detractors
        if rand < 0.30:  # 30% Promoters
            return random.choice([9, 9, 10])
        elif rand < 0.70:  # 40% Passives
            return random.choice([7, 7, 8, 8])
        else:  # 30% Detractors
            return random.choice([3, 4, 5, 6])
    return random.randint(0, 10)


def generate_sentiment(nps_score):
    """Generate sentiment based on NPS score"""
    if nps_score >= 9:
        return random.uniform(0.6, 0.9), "positive"
    elif nps_score >= 7:
        return random.uniform(-0.2, 0.2), "neutral"
    else:
        return random.uniform(-0.8, -0.3), "negative"


def generate_churn_risk(nps_score, sentiment_score):
    """Generate churn risk based on NPS and sentiment"""
    if nps_score >= 9:
        return random.uniform(0.05, 0.25), "Minimal"
    elif nps_score >= 7:
        if sentiment_score > 0:
            return random.uniform(0.25, 0.45), "Low"
        else:
            return random.uniform(0.45, 0.65), "Medium"
    else:
        if nps_score <= 4:
            return random.uniform(0.75, 0.95), "High"
        else:
            return random.uniform(0.55, 0.75), "Medium"


def generate_feedback(nps_category):
    """Generate realistic feedback based on NPS category"""
    if nps_category == "Promoter":
        return random.choice(PROMOTER_FEEDBACK)
    elif nps_category == "Passive":
        return random.choice(PASSIVE_FEEDBACK)
    else:
        return random.choice(DETRACTOR_FEEDBACK)


def generate_key_themes(nps_category):
    """Generate key themes based on NPS category"""
    if nps_category == "Promoter":
        themes = random.sample(["Service Quality", "Product Features", "Support Responsiveness", 
                               "Innovation", "Account Management"], random.randint(2, 3))
    elif nps_category == "Passive":
        themes = random.sample(["Pricing Concerns", "User Experience", "Feature Requests",
                               "Documentation Quality", "Value for Money"], random.randint(2, 3))
    else:
        themes = random.sample(["Pricing Concerns", "Support Responsiveness", "System Reliability",
                               "Integration Capabilities", "Performance Issues"], random.randint(2, 4))
    return json.dumps(themes)


def generate_random_timestamp(start_date, end_date):
    """Generate random timestamp within date range"""
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randint(0, days_between)
    random_hours = random.randint(9, 18)  # Business hours
    random_minutes = random.randint(0, 59)
    
    result_date = start_date + timedelta(days=random_days)
    return datetime.combine(result_date, datetime.min.time()).replace(
        hour=random_hours, minute=random_minutes
    )


def get_or_create_participant(business_account_id, company, campaign_id, existing_companies):
    """Get existing participant or create new one"""
    # Generate participant details
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    role = random.choice(ROLES)
    name = f"{first_name} {last_name} ({role})"
    email = f"{first_name.lower()}.{last_name.lower()}@{company.lower().replace(' ', '')}.com"
    
    # Check if participant exists
    participant = Participant.query.filter_by(
        business_account_id=business_account_id,
        email=email
    ).first()
    
    if not participant:
        participant = Participant(
            business_account_id=business_account_id,
            email=email,
            name=name,
            company_name=company,
            source='admin_bulk',
            status='created',
            created_at=datetime.utcnow()
        )
        participant.token = str(__import__('uuid').uuid4())
        db.session.add(participant)
        db.session.flush()
    
    # Create campaign participant association if not exists
    campaign_participant = CampaignParticipant.query.filter_by(
        campaign_id=campaign_id,
        participant_id=participant.id
    ).first()
    
    if not campaign_participant:
        campaign_participant = CampaignParticipant(
            campaign_id=campaign_id,
            participant_id=participant.id,
            business_account_id=business_account_id,
            status='created',
            created_at=datetime.utcnow()
        )
        campaign_participant.token = str(__import__('uuid').uuid4())
        db.session.add(campaign_participant)
        db.session.flush()
    
    return participant, campaign_participant


def generate_campaign_data(campaign_key, dry_run=False):
    """Generate demo data for a specific campaign"""
    config = CAMPAIGNS[campaign_key]
    
    print(f"\n{'='*70}")
    print(f"Generating Demo Data for: {config['name']}")
    print(f"{'='*70}")
    print(f"Date Range: {config['start_date']} to {config['end_date']}")
    print(f"Target Responses: {config['responses']}")
    print(f"Company Reuse: {config['company_reuse']}%")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
    print(f"{'='*70}\n")
    
    with app.app_context():
        try:
            # Get Archelo Group business account
            business_account = BusinessAccount.query.filter_by(name="Archelo Group inc").first()
            if not business_account:
                print("❌ Error: Archelo Group inc business account not found!")
                return False
            
            print(f"✓ Business Account: {business_account.name} (ID: {business_account.id})")
            
            # Find or create campaign
            campaign = Campaign.query.filter_by(
                business_account_id=business_account.id,
                name=config['name']
            ).first()
            
            if not campaign:
                campaign = Campaign(
                    business_account_id=business_account.id,
                    name=config['name'],
                    description=f"Quarterly customer loyalty measurement and feedback collection for Q{campaign_key[1]} 2025",
                    start_date=config['start_date'],
                    end_date=config['end_date'],
                    status='active',
                    client_identifier='archelo_group',
                    created_at=datetime.utcnow()
                )
                db.session.add(campaign)
                db.session.flush()
                print(f"✓ Created Campaign: {campaign.name} (ID: {campaign.id})")
            else:
                print(f"✓ Found Campaign: {campaign.name} (ID: {campaign.id}, Status: {campaign.status})")
                if campaign.status != 'active':
                    print(f"❌ Error: Campaign status is '{campaign.status}', must be 'active' to add responses")
                    return False
            
            # Get existing companies from previous campaigns
            existing_companies = []
            if config['company_reuse'] > 0:
                previous_responses = SurveyResponse.query.filter(
                    SurveyResponse.campaign_id != campaign.id,
                    SurveyResponse.campaign.has(business_account_id=business_account.id)
                ).all()
                existing_companies = list(set([r.company_name for r in previous_responses]))
                print(f"✓ Found {len(existing_companies)} companies from previous campaigns")
            
            # Determine companies for this campaign
            num_reuse = int(len(existing_companies) * (config['company_reuse'] / 100))
            num_new = config['responses'] - num_reuse
            
            reused_companies = random.sample(existing_companies, min(num_reuse, len(existing_companies))) if existing_companies else []
            available_new = [c for c in COMPANIES if c not in existing_companies]
            new_companies = random.sample(available_new, min(num_new, len(available_new)))
            
            campaign_companies = reused_companies + new_companies
            random.shuffle(campaign_companies)
            
            print(f"✓ Company Mix: {len(reused_companies)} reused + {len(new_companies)} new = {len(campaign_companies)} total")
            
            if dry_run:
                print("\n📋 DRY RUN SUMMARY:")
                print(f"   - Would create {config['responses']} survey responses")
                print(f"   - For campaign: {campaign.name}")
                print(f"   - Date range: {config['start_date']} to {config['end_date']}")
                print(f"   - Companies: {', '.join(campaign_companies[:5])}..." if len(campaign_companies) > 5 else f"   - Companies: {', '.join(campaign_companies)}")
                print("\n✓ Dry run completed successfully. Run without --dry-run to execute.\n")
                return True
            
            # Generate responses
            responses_created = 0
            nps_distribution = {"Promoter": 0, "Passive": 0, "Detractor": 0}
            
            print(f"\nGenerating {config['responses']} responses...")
            
            for i in range(config['responses']):
                company = random.choice(campaign_companies)
                
                # Get or create participant
                participant, campaign_participant = get_or_create_participant(
                    business_account.id, company, campaign.id, existing_companies
                )
                
                # Generate response data
                nps_score = generate_nps_score()
                nps_category = get_nps_category(nps_score)
                sentiment_score, sentiment_label = generate_sentiment(nps_score)
                churn_risk_score, churn_risk_level = generate_churn_risk(nps_score, sentiment_score)
                
                # Create survey response
                response = SurveyResponse(
                    campaign_id=campaign.id,
                    campaign_participant_id=campaign_participant.id,
                    company_name=company,
                    respondent_name=participant.name,
                    respondent_email=participant.email,
                    tenure_with_fc=random.choice(["< 1 year", "1-2 years", "2-3 years", "3-5 years", "> 5 years"]),
                    nps_score=nps_score,
                    nps_category=nps_category,
                    satisfaction_rating=random.randint(1, 10),
                    product_value_rating=random.randint(1, 10),
                    service_rating=random.randint(1, 10),
                    pricing_rating=random.randint(1, 10),
                    improvement_feedback=generate_feedback(nps_category),
                    recommendation_reason=generate_feedback(nps_category),
                    additional_comments=generate_feedback(nps_category) if random.random() > 0.5 else None,
                    sentiment_score=sentiment_score,
                    sentiment_label=sentiment_label,
                    key_themes=generate_key_themes(nps_category),
                    churn_risk_score=churn_risk_score,
                    churn_risk_level=churn_risk_level,
                    churn_risk_factors=json.dumps([random.choice(KEY_THEMES) for _ in range(random.randint(1, 3))]),
                    growth_opportunities=json.dumps([random.choice(KEY_THEMES) for _ in range(random.randint(1, 2))]) if nps_score >= 7 else None,
                    account_risk_factors=json.dumps([random.choice(KEY_THEMES) for _ in range(random.randint(1, 3))]) if nps_score < 7 else None,
                    commercial_value=random.uniform(10000, 500000),
                    source_type='conversational',
                    created_at=generate_random_timestamp(config['start_date'], config['end_date']),
                    analyzed_at=datetime.utcnow()
                )
                
                db.session.add(response)
                responses_created += 1
                nps_distribution[nps_category] += 1
                
                if (i + 1) % 50 == 0:
                    print(f"   Progress: {i + 1}/{config['responses']} responses created...")
            
            # Commit transaction
            db.session.commit()
            
            # Calculate NPS
            total = sum(nps_distribution.values())
            promoter_pct = (nps_distribution["Promoter"] / total * 100) if total > 0 else 0
            detractor_pct = (nps_distribution["Detractor"] / total * 100) if total > 0 else 0
            nps_score = promoter_pct - detractor_pct
            
            print(f"\n✅ SUCCESS! Generated {responses_created} responses for {campaign.name}")
            print(f"\n📊 NPS Distribution:")
            print(f"   Promoters: {nps_distribution['Promoter']} ({promoter_pct:.1f}%)")
            print(f"   Passives: {nps_distribution['Passive']} ({nps_distribution['Passive']/total*100:.1f}%)")
            print(f"   Detractors: {nps_distribution['Detractor']} ({detractor_pct:.1f}%)")
            print(f"   NPS Score: {nps_score:.1f}")
            print(f"\n✓ Next Step: Manually complete the campaign '{campaign.name}' to generate snapshot\n")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERROR: {str(e)}")
            print(f"   Transaction rolled back. No data was modified.\n")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate demo data for Archelo Group campaigns')
    parser.add_argument('--campaign', choices=['Q1 2025', 'Q2 2025', 'Q3 2025'], required=True,
                       help='Campaign to generate data for')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview what would be generated without making changes')
    
    args = parser.parse_args()
    
    success = generate_campaign_data(args.campaign, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
