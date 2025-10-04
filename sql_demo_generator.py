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
    if s >= 9:
        return random.uniform(0.05, 0.25), "Minimal"
    elif s >= 7:
        return random.uniform(0.3, 0.6), random.choice(["Low", "Medium"])
    return random.uniform(0.6, 0.95), random.choice(["Medium", "High"])


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
            
            # Insert response
            cur.execute("""
                INSERT INTO survey_response (
                    campaign_id, campaign_participant_id, company_name, respondent_name, respondent_email,
                    tenure_with_fc, nps_score, nps_category,
                    satisfaction_rating, product_value_rating, service_rating, pricing_rating,
                    improvement_feedback, recommendation_reason,
                    sentiment_score, sentiment_label, key_themes,
                    churn_risk_score, churn_risk_level, churn_risk_factors,
                    growth_factor, commercial_value, source_type, created_at, analyzed_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'conversational', %s, NOW()
                )
            """, (camp_id, cp_id, co, name, email,
                  random.choice(["< 1 year", "1-2 years", "2-3 years", "3-5 years", "> 5 years"]),
                  nps, cat,
                  random.randint(1, 5), random.randint(1, 5), random.randint(1, 5), random.randint(1, 5),
                  fb, fb, ss, sl, themes, cs, cl,
                  json.dumps(random.sample(THEMES, 2)), random.uniform(0.8, 1.5), random.uniform(10000, 500000),
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
