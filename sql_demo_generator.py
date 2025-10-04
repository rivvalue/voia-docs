#!/usr/bin/env python3
"""Direct SQL Demo Data Generator - No imports, no circular dependencies"""

import os
import sys
import random
import json
import psycopg2
from datetime import datetime, timedelta, date
from uuid import uuid4

# Campaign configs
CAMPAIGNS = {
    "Q1": {
        "name": "Loyalty measurement Q1 2025",
        "start": date(2025, 1, 1),
        "end": date(2025, 3, 31),
        "responses": 180,
        "reuse": 0
    },
    "Q2": {
        "name": "Loyalty measurement Q2 2025",
        "start": date(2025, 4, 1),
        "end": date(2025, 6, 30),
        "responses": 220,
        "reuse": 40
    },
    "Q3": {
        "name": "Loyalty measurement Q3 2025",
        "start": date(2025, 7, 1),
        "end": date(2025, 9, 30),
        "responses": 200,
        "reuse": 50
    }
}

COMPANIES = [
    "CloudSync Technologies", "DataFlow Solutions", "API Masters Inc", "TechVision Corp",
    "SecureBank Financial", "FinanceFirst Ltd", "MediCare Plus", "HealthTech Partners",
    "RetailPro International", "EcomGrow Solutions", "LogiTrack Express", "SupplyChain Pro",
    "EduTech Academy", "LearnPath Systems", "GreenEnergy Solutions", "SolarTech Industries",
    "FoodService Partners", "RestaurantTech Inc", "TravelBook Solutions", "HotelSync Technologies",
    "AutoParts Wholesale", "VehicleTech Systems", "ManufacturePro Inc", "IndustryTech Solutions",
    "MediaStream Corp", "ContentHub Technologies", "LegalTech Partners", "ComplianceSync Inc",
    "PropertyTech Solutions", "RealEstateFlow Inc", "InsureTech Corp", "PolicyFlow Systems",
    "ConsultPro Partners", "AdvisoryTech Inc", "StrategyFlow Systems", "ExpertHub International",
    "PaymentHub Systems", "InvestPro Group", "CareConnect Health", "ShopFlow Systems",
    "FreightFlow Inc", "CargoSync Logistics", "KnowledgeHub Inc", "TrainingPro Solutions",
    "EcoPower Systems", "RenewCorp Energy", "MenuMaster Systems", "ChefConnect Platform",
    "TourismPro Inc", "BookingFlow Tech", "FleetManager Pro", "DriveSync Automotive",
    "ProductionFlow Systems", "FactorySync Industries", "BroadcastPro Inc", "StreamFlow Media",
    "JusticeFlow Systems", "LawyerHub Legal", "BuildingSync Pro", "HomeHub RealEstate",
    "ClaimSync Solutions", "RiskHub Insurance", "WellBeing Systems", "MarketReach Analytics"
]

NAMES = [("Sarah","Johnson"), ("Michael","Williams"), ("Jennifer","Brown"), ("David","Jones"),
         ("Lisa","Garcia"), ("James","Miller"), ("Emily","Davis"), ("Robert","Rodriguez"),
         ("Jessica","Martinez"), ("John","Hernandez"), ("Amanda","Lopez"), ("William","Gonzalez")]

ROLES = ["CEO", "CTO", "CFO", "VP Operations", "Director", "Manager"]

FEEDBACK = {
    "P": ["Excellent service and responsive team.", "Outstanding support and great ROI.",
          "Best solution we've used. Highly recommend.", "Fantastic product with helpful customer success."],
    "Pa": ["Good product but pricing could be better.", "Solid service with some missing features.",
           "Works well though documentation needs improvement.", "Decent solution with room for UX improvements."],
    "D": ["Pricing too high for value. Slow support.", "Frequent bugs and stability issues.",
          "Poor customer service and responsiveness.", "Unacceptable downtime and missing features."]
}

THEMES = ["Service Quality", "Pricing", "Product Features", "Support", "Integration", "UX", "Reliability", "Documentation"]

# Account Intelligence Templates
GROWTH_OPPORTUNITIES = {
    "Promoter": [
        {"type": "upsell", "description": "High satisfaction indicates readiness for premium tier", "action": "Present enterprise features and ROI analysis"},
        {"type": "expansion", "description": "Strong product adoption across team", "action": "Discuss additional seats or departments"},
        {"type": "advocacy", "description": "Enthusiastic feedback suggests advocacy potential", "action": "Request case study, referral, or testimonial"},
        {"type": "cross_sell", "description": "Using core features extensively", "action": "Introduce complementary products or modules"},
    ],
    "Passive": [
        {"type": "engagement", "description": "Moderate satisfaction with room for growth", "action": "Schedule product training or success review"},
        {"type": "feature_adoption", "description": "Not utilizing advanced capabilities", "action": "Demonstrate underused features aligned with their goals"},
        {"type": "optimization", "description": "Good fit but could maximize value", "action": "Conduct workflow optimization session"},
    ],
    "Detractor": [
        {"type": "retention", "description": "At-risk customer requires intervention", "action": "Immediate executive outreach and improvement plan"},
        {"type": "win_back", "description": "Dissatisfaction suggests competitive vulnerability", "action": "Address specific pain points and demonstrate commitment"},
    ]
}

RISK_FACTORS = {
    "Promoter": [
        {"type": "complacency", "description": "High scores may mask emerging issues", "severity": "Low", "action": "Maintain regular check-ins to catch issues early"},
    ],
    "Passive": [
        {"type": "engagement", "description": "Moderate engagement indicates potential drift", "severity": "Medium", "action": "Increase touchpoints and success initiatives"},
        {"type": "competitive_pressure", "description": "Neutral sentiment suggests openness to alternatives", "severity": "Medium", "action": "Reinforce value proposition and differentiation"},
        {"type": "pricing_sensitivity", "description": "Cost concerns mentioned in feedback", "severity": "Medium", "action": "Review pricing alignment and demonstrate ROI"},
    ],
    "Detractor": [
        {"type": "churn_risk", "description": "Low satisfaction indicates high churn probability", "severity": "High", "action": "Immediate escalation and retention strategy"},
        {"type": "support_issues", "description": "Poor service experience driving dissatisfaction", "severity": "High", "action": "Assign dedicated support resource and SLA review"},
        {"type": "product_gaps", "description": "Missing features impacting business outcomes", "severity": "High", "action": "Product roadmap discussion and workaround solutions"},
        {"type": "poor_onboarding", "description": "Adoption challenges due to insufficient training", "severity": "Medium", "action": "Comprehensive re-onboarding and enablement program"},
    ]
}


def nps_score():
    r = random.random()
    return random.choice([9,9,10]) if r < 0.3 else random.choice([7,7,8,8]) if r < 0.7 else random.choice([3,4,5,6])


def nps_cat(s):
    return "Promoter" if s >= 9 else "Passive" if s >= 7 else "Detractor"


def sentiment(s):
    if s >= 9:
        return random.uniform(0.6, 0.9), "positive"
    elif s >= 7:
        return random.uniform(-0.2, 0.2), "neutral"
    return random.uniform(-0.8, -0.3), "negative"


def churn(s):
    """Adjusted churn risk: only 30% of detractors become High risk"""
    if s >= 9:
        return random.uniform(0.05, 0.25), "Minimal"
    elif s >= 7:
        return random.uniform(0.3, 0.6), random.choice(["Low", "Medium"])
    # Detractors: 30% High, 70% Medium
    risk_level = "High" if random.random() < 0.3 else "Medium"
    score = random.uniform(0.7, 0.95) if risk_level == "High" else random.uniform(0.5, 0.75)
    return score, risk_level


def calculate_growth_factor(nps_score):
    """Calculate growth factor, rate, and range based on NPS score
    
    Matches the lookup table from ai_analysis.py:
    - NPS <0: 0% growth
    - NPS 0-29: 5% growth
    - NPS 30-49: 15% growth
    - NPS 50-69: 25% growth
    - NPS 70-100: 40% growth
    """
    if nps_score < 0:
        return 0.0, '0%', '<0'
    elif 0 <= nps_score <= 29:
        return 0.05, '5%', '0-29'
    elif 30 <= nps_score <= 49:
        return 0.15, '15%', '30-49'
    elif 50 <= nps_score <= 69:
        return 0.25, '25%', '50-69'
    elif 70 <= nps_score <= 100:
        return 0.4, '40%', '70-100'
    else:
        return 0.0, '0%', 'invalid'


def generate_account_intelligence(nps_cat, churn_risk_level):
    """Generate realistic growth opportunities and risk factors based on NPS category and churn risk
    
    Logic mirrors VOÏA's actual AI analysis:
    - Promoters: High chance of opportunities, low/no critical risks
    - Passives: Balanced mix
    - Detractors: High chance of risks, minimal opportunities (only win-back)
    """
    opportunities = []
    risks = []
    
    # ============================================================================
    # GROWTH OPPORTUNITIES (based on NPS category)
    # ============================================================================
    if nps_cat == "Promoter":
        # 90% chance to get 1-2 opportunities
        if random.random() < 0.9:
            num_opps = random.randint(1, 2)
            opportunities = random.sample(GROWTH_OPPORTUNITIES[nps_cat], k=min(num_opps, len(GROWTH_OPPORTUNITIES[nps_cat])))
    
    elif nps_cat == "Passive":
        # 50% chance to get 1 opportunity (engagement/optimization)
        if random.random() < 0.5:
            opportunities = random.sample(GROWTH_OPPORTUNITIES[nps_cat], k=1)
    
    elif nps_cat == "Detractor":
        # 20% chance to get 1 win-back/retention opportunity
        if random.random() < 0.2:
            opportunities = random.sample(GROWTH_OPPORTUNITIES[nps_cat], k=1)
    
    # ============================================================================
    # ACCOUNT RISK FACTORS (based on NPS category and churn risk)
    # ============================================================================
    if nps_cat == "Promoter":
        # 20% chance to get 1 LOW severity risk only
        if random.random() < 0.2:
            # Promoters only get low-severity risks (complacency)
            low_risks = [r for r in RISK_FACTORS[nps_cat] if r.get('severity') == 'Low']
            if low_risks:
                risks = random.sample(low_risks, k=1)
    
    elif nps_cat == "Passive":
        # 60% chance to get 1-2 risks (Medium severity primarily)
        if random.random() < 0.6:
            num_risks = random.randint(1, 2)
            risks = random.sample(RISK_FACTORS[nps_cat], k=min(num_risks, len(RISK_FACTORS[nps_cat])))
            
            # If churn risk is High, ensure at least one High severity risk
            if churn_risk_level == "High" and risks:
                # Upgrade one risk to High severity
                risks[0] = risks[0].copy()
                risks[0]['severity'] = 'High'
    
    elif nps_cat == "Detractor":
        # 100% chance to get 2-3 risks (High/Critical severity)
        num_risks = random.randint(2, 3)
        risks = random.sample(RISK_FACTORS[nps_cat], k=min(num_risks, len(RISK_FACTORS[nps_cat])))
        
        # If churn risk is High, ensure at least one Critical severity risk
        if churn_risk_level == "High" and risks:
            # Upgrade first risk to Critical severity
            risks[0] = risks[0].copy()
            risks[0]['severity'] = 'Critical'
    
    return json.dumps(opportunities), json.dumps(risks)


def rand_time(start, end):
    days = (end - start).days
    dt = start + timedelta(days=random.randint(0, days))
    return datetime.combine(dt, datetime.min.time()).replace(
        hour=random.randint(9, 18), minute=random.randint(0, 59)
    )


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['Q1', 'Q2', 'Q3']:
        print("Usage: python sql_demo_generator.py {Q1|Q2|Q3}")
        sys.exit(1)
    
    q = sys.argv[1]
    cfg = CAMPAIGNS[q]
    
    print(f"\n{'='*70}")
    print(f"Generating: {cfg['name']}")
    print(f"{'='*70}\n")
    
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()
    
    try:
        # Get business account
        cur.execute("SELECT id FROM business_accounts WHERE name = 'Archelo Group inc'")
        ba_id = cur.fetchone()[0]
        print(f"✓ Business Account ID: {ba_id}")
        
        # Create or get campaign
        cur.execute("""
            SELECT id, status FROM campaigns 
            WHERE business_account_id = %s AND name = %s
        """, (ba_id, cfg['name']))
        
        row = cur.fetchone()
        if row:
            camp_id, status = row
            print(f"✓ Found campaign ID: {camp_id} (status: {status})")
            if status != 'active':
                print(f"❌ Campaign must be active, currently: {status}")
                return
        else:
            cur.execute("""
                INSERT INTO campaigns (business_account_id, name, description, start_date, end_date, status, client_identifier, created_at)
                VALUES (%s, %s, %s, %s, %s, 'ready', 'archelo_group', NOW())
                RETURNING id
            """, (ba_id, cfg['name'], f"Q{q[1]} 2025 loyalty measurement", cfg['start'], cfg['end']))
            camp_id = cur.fetchone()[0]
            print(f"✓ Created campaign ID: {camp_id}")
        
        # Get existing companies for reuse
        existing = []
        if cfg['reuse'] > 0:
            cur.execute("""
                SELECT DISTINCT company_name FROM survey_response r
                JOIN campaigns c ON r.campaign_id = c.id
                WHERE c.business_account_id = %s AND r.campaign_id != %s
            """, (ba_id, camp_id))
            existing = [row[0] for row in cur.fetchall()]
        
        # Select companies
        num_reuse = int(len(existing) * (cfg['reuse'] / 100))
        reused = random.sample(existing, min(num_reuse, len(existing))) if existing else []
        new_cos = [c for c in COMPANIES if c not in existing]
        new = random.sample(new_cos, min(cfg['responses'] - num_reuse, len(new_cos)))
        cos = reused + new
        
        print(f"✓ Companies: {len(reused)} reused + {len(new)} new\n")
        
        # Generate responses
        dist = {"Promoter": 0, "Passive": 0, "Detractor": 0}
        
        for i in range(cfg['responses']):
            co = random.choice(cos)
            fn, ln = random.choice(NAMES)
            role = random.choice(ROLES)
            name = f"{fn} {ln} ({role})"
            email = f"{fn.lower()}.{ln.lower()}@{co.lower().replace(' ', '')}.com"
            
            # Get or create participant
            cur.execute("""
                SELECT id FROM participants 
                WHERE business_account_id = %s AND email = %s
            """, (ba_id, email))
            
            row = cur.fetchone()
            if row:
                p_id = row[0]
            else:
                cur.execute("""
                    INSERT INTO participants (business_account_id, email, name, company_name, source, status, token, created_at)
                    VALUES (%s, %s, %s, %s, 'admin_bulk', 'created', %s, NOW())
                    RETURNING id
                """, (ba_id, email, name, co, str(uuid4())))
                p_id = cur.fetchone()[0]
            
            # Get or create campaign participant
            cur.execute("""
                SELECT id FROM campaign_participants
                WHERE campaign_id = %s AND participant_id = %s
            """, (camp_id, p_id))
            
            row = cur.fetchone()
            if row:
                cp_id = row[0]
            else:
                cur.execute("""
                    INSERT INTO campaign_participants (campaign_id, participant_id, business_account_id, status, token, created_at)
                    VALUES (%s, %s, %s, 'created', %s, NOW())
                    RETURNING id
                """, (camp_id, p_id, ba_id, str(uuid4())))
                cp_id = cur.fetchone()[0]
            
            # Generate response data
            nps = nps_score()
            cat = nps_cat(nps)
            ss, sl = sentiment(nps)
            cs, cl = churn(nps)
            fb = random.choice(FEEDBACK[cat[0] if cat == "Promoter" else "Pa" if cat == "Passive" else "D"])
            themes = json.dumps(random.sample(THEMES, random.randint(2, 3)))
            growth_opps, risk_factors = generate_account_intelligence(cat, cl)
            gf, gr, grng = calculate_growth_factor(nps)
            
            # Insert response
            cur.execute("""
                INSERT INTO survey_response (
                    campaign_id, campaign_participant_id, company_name, respondent_name, respondent_email,
                    tenure_with_fc, nps_score, nps_category,
                    satisfaction_rating, product_value_rating, service_rating, pricing_rating,
                    improvement_feedback, recommendation_reason,
                    sentiment_score, sentiment_label, key_themes,
                    churn_risk_score, churn_risk_level, churn_risk_factors,
                    growth_opportunities, account_risk_factors,
                    growth_factor, growth_rate, growth_range, commercial_value, source_type, created_at, analyzed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'conversational', %s, NOW()
                )
            """, (camp_id, cp_id, co, name, email,
                  random.choice(["< 1 year", "1-2 years", "2-3 years", "3-5 years", "> 5 years"]),
                  nps, cat,
                  random.randint(1, 5), random.randint(1, 5), random.randint(1, 5), random.randint(1, 5),
                  fb, fb, ss, sl, themes, cs, cl,
                  json.dumps(random.sample(THEMES, 2)), growth_opps, risk_factors,
                  gf, gr, grng, random.uniform(10000, 500000),
                  rand_time(cfg['start'], cfg['end'])))
            
            dist[cat] += 1
            
            if (i + 1) % 50 == 0:
                conn.commit()  # Commit every 50 responses
                print(f"   Progress: {i + 1}/{cfg['responses']} (committed)")
        
        conn.commit()  # Final commit
        
        tot = sum(dist.values())
        nps_val = (dist["Promoter"] / tot * 100 - dist["Detractor"] / tot * 100)
        
        print(f"\n✅ Generated {cfg['responses']} responses")
        print(f"📊 NPS: {nps_val:.1f} (P:{dist['Promoter']}, Pa:{dist['Passive']}, D:{dist['Detractor']})")
        print(f"\n✓ Next: Complete campaign '{cfg['name']}' to generate snapshot\n")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    main()
