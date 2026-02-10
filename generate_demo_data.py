#!/usr/bin/env python3
"""
Demo Data Generator for Archelo Group — ArcheloFlow HRIS SaaS
Generates realistic, coherent survey responses for demo campaigns.

Usage:
    python generate_demo_data.py --campaign Q1 --dry-run
    python generate_demo_data.py --campaign Q1
    python generate_demo_data.py --campaign Q1 --delete
"""

import os
import sys
import random
import json
import uuid
import argparse
from datetime import datetime, timedelta, date
from app import app, db
from models import (
    BusinessAccount, Campaign, Participant, CampaignParticipant,
    SurveyResponse, ClassicSurveyConfig, SurveyTemplate,
    ExecutiveReport, EmailDelivery, ActiveConversation, ExportJob
)


CAMPAIGN_CONFIGS = {
    "Q1": {
        "name": "Client Loyalty Survey Q1 2025",
        "description": "Quarterly ArcheloFlow client loyalty measurement and feedback collection — Q1 2025",
        "start_date": date(2025, 1, 6),
        "end_date": date(2025, 3, 28),
        "completed_at": datetime(2025, 4, 2, 10, 0, 0),
        "responses": 500,
        "survey_type": "conversational",
        "language_code": "en",
        "company_reuse_pct": 0,
        "nps_bias": 0,
    },
    "Q2": {
        "name": "Client Loyalty Survey Q2 2025",
        "description": "Quarterly ArcheloFlow client loyalty measurement and feedback collection — Q2 2025",
        "start_date": date(2025, 4, 1),
        "end_date": date(2025, 6, 27),
        "completed_at": datetime(2025, 7, 3, 10, 0, 0),
        "responses": 500,
        "survey_type": "conversational",
        "language_code": "en",
        "company_reuse_pct": 45,
        "nps_bias": 1,
    },
    "Q3": {
        "name": "Mesure de Fidélité Clients Q3 2025",
        "description": "Mesure trimestrielle de la fidélité et collecte de feedback clients ArcheloFlow — Q3 2025",
        "start_date": date(2025, 6, 2),
        "end_date": date(2025, 9, 26),
        "completed_at": datetime(2025, 10, 1, 10, 0, 0),
        "responses": 500,
        "survey_type": "conversational",
        "language_code": "fr",
        "company_reuse_pct": 50,
        "nps_bias": 2,
    },
    "CLASSIC": {
        "name": "ArcheloFlow Service Quality Assessment 2025",
        "description": "Structured service quality assessment survey for ArcheloFlow clients — 2025",
        "start_date": date(2025, 3, 3),
        "end_date": date(2025, 5, 30),
        "completed_at": datetime(2025, 6, 4, 10, 0, 0),
        "responses": 500,
        "survey_type": "classic",
        "language_code": "en",
        "company_reuse_pct": 40,
        "nps_bias": 0,
    },
}

BUSINESS_ACCOUNT_NAME = "Archelo Group inc"

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
]

FIRST_NAMES = [
    "Sarah", "Michael", "Jennifer", "David", "Lisa", "James", "Emily", "Robert",
    "Jessica", "John", "Amanda", "William", "Michelle", "Richard", "Elizabeth", "Thomas",
    "Ashley", "Christopher", "Stephanie", "Daniel", "Nicole", "Matthew", "Rebecca", "Mark",
    "Laura", "Donald", "Karen", "Paul", "Nancy", "Andrew", "Betty", "Joshua",
    "Margaret", "Kenneth", "Sandra", "Kevin", "Angela", "Brian", "Donna", "George",
    "Carol", "Edward", "Ruth", "Ronald", "Sharon", "Timothy", "Helen", "Jason",
]

LAST_NAMES = [
    "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
    "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor",
    "Moore", "Jackson", "Martin", "Lee", "Thompson", "White", "Harris", "Clark",
    "Lewis", "Robinson", "Walker", "Young", "Allen", "King", "Wright", "Scott",
    "Torres", "Nguyen", "Hill", "Flores", "Green", "Adams", "Nelson", "Baker",
    "Hall", "Rivera", "Campbell", "Mitchell", "Carter", "Roberts", "Turner", "Phillips",
]

ROLES_WEIGHTED = [
    ("End User", 50),
    ("Director", 25),
    ("VP", 25),
]

TIERS_WEIGHTED = [
    ("T1: Key Account", 20),
    ("T2: Strategic", 30),
    ("T3: Low Revenue", 50),
]

REGIONS = ["North America", "EMEA", "APAC"]

INDUSTRIES = [
    "Technology", "Financial Services", "Healthcare", "Manufacturing",
    "Retail & E-commerce", "Professional Services", "Education",
    "Energy & Utilities", "Transportation & Logistics", "Media & Entertainment",
]

DRIVER_KEYS = [
    "product_features", "value_pricing", "professional_services",
    "customer_support", "communication", "onboarding",
    "ease_of_use", "reliability", "integration",
]

DEFAULT_DRIVER_LABELS = [
    {'key': 'product_features', 'label_en': 'Product features & functionality', 'label_fr': 'Fonctionnalités du produit'},
    {'key': 'value_pricing', 'label_en': 'Product value/pricing', 'label_fr': 'Rapport qualité/prix'},
    {'key': 'professional_services', 'label_en': 'Professional services & support team', 'label_fr': 'Services professionnels et équipe de support'},
    {'key': 'customer_support', 'label_en': 'Customer support & after-sales service', 'label_fr': 'Support client et service après-vente'},
    {'key': 'communication', 'label_en': 'Communication & transparency', 'label_fr': 'Communication et transparence'},
    {'key': 'onboarding', 'label_en': 'Onboarding & implementation experience', 'label_fr': "Expérience d'intégration et de mise en œuvre"},
    {'key': 'ease_of_use', 'label_en': 'Ease of use', 'label_fr': "Facilité d'utilisation"},
    {'key': 'reliability', 'label_en': 'Reliability & performance', 'label_fr': 'Fiabilité et performance'},
    {'key': 'integration', 'label_en': 'Integration capabilities', 'label_fr': "Capacités d'intégration"},
]


PROMOTER_FEEDBACK_EN = [
    "ArcheloFlow has completely transformed how we manage onboarding and payroll. The HR team saves at least 10 hours per week on administrative tasks.",
    "The leave management and time tracking modules are incredibly intuitive. Our employees adopted ArcheloFlow within days, minimal training required.",
    "Outstanding platform for managing our growing workforce. The employee self-service portal has drastically reduced HR ticket volume.",
    "ArcheloFlow's performance review module is excellent. The 360-degree feedback feature gives managers actionable insights they never had before.",
    "Best HRIS investment we've made. The compliance tracking and document management features keep us audit-ready at all times.",
    "The recruitment pipeline in ArcheloFlow is seamless. From job posting to offer letter, everything flows naturally. Our time-to-hire dropped by 30%.",
    "Exceptional customer success team. They understood our SMB challenges and configured ArcheloFlow perfectly for our 200-person organization.",
    "ArcheloFlow's reporting dashboard gives our leadership real-time visibility into headcount, turnover, and compensation metrics. Game-changer for strategic planning.",
    "The benefits administration module simplified open enrollment dramatically. What used to take weeks now takes days.",
    "We evaluated several HRIS platforms and ArcheloFlow stood out for SMBs. The pricing is fair and the feature set rivals enterprise solutions.",
]

PASSIVE_FEEDBACK_EN = [
    "ArcheloFlow handles our core HR needs well, but the learning management module feels underdeveloped compared to dedicated LMS solutions.",
    "Decent platform overall. Payroll processing works reliably, though the reporting customization options could be more flexible.",
    "The employee directory and org chart features are solid, but we wish the mobile app had more functionality for approvals on the go.",
    "ArcheloFlow meets our basic HRIS requirements. However, the pricing feels steep for a company our size when we only use half the modules.",
    "Good product for time tracking and attendance. The integration with our accounting software works, but required more manual setup than expected.",
    "The platform is stable and the support team is helpful, but response times for non-critical issues can stretch to several days.",
    "Onboarding workflows are configurable, which is nice, but the performance management module lacks goal-setting features our managers want.",
    "ArcheloFlow's compensation management is adequate, though competitors offer more sophisticated benchmarking tools at a similar price point.",
    "Works well for US-based employees, but multi-country payroll support is limited. We need better localization for our Canadian offices.",
    "The document management and e-signature features are convenient, but the storage limits on our plan are restrictive for a growing team.",
]

DETRACTOR_FEEDBACK_EN = [
    "ArcheloFlow's implementation took four months instead of the promised six weeks. The data migration from our old system was riddled with errors.",
    "The payroll module has had two calculation errors this year that affected employee trust. For an HRIS, payroll accuracy should be non-negotiable.",
    "Customer support is frustratingly slow. We submitted a critical bug report about incorrect tax withholdings and waited 8 days for a response.",
    "The user interface feels dated compared to newer HRIS platforms. Our employees constantly complain about the clunky self-service portal.",
    "Pricing increases every renewal without corresponding feature improvements. We're paying 40% more than two years ago for essentially the same product.",
    "Integration with our ERP system has been a persistent headache. The API documentation is incomplete and the sync breaks regularly.",
    "The reporting engine is extremely limited. We can't build custom reports without exporting to Excel, which defeats the purpose of having an HRIS.",
    "The mobile experience is subpar. Employees can't complete time-off requests or view pay stubs on their phones without issues.",
    "We were promised a dedicated account manager when we signed up, but turnover on their side means we've had four different contacts in two years.",
    "System downtime during our last open enrollment period was unacceptable. Several employees missed benefits deadlines because of platform outages.",
]

PROMOTER_FEEDBACK_FR = [
    "ArcheloFlow a complètement transformé notre gestion des RH. L'équipe gagne au moins 10 heures par semaine sur les tâches administratives.",
    "Les modules de gestion des congés et du suivi du temps sont incroyablement intuitifs. Nos employés ont adopté la solution en quelques jours.",
    "Plateforme exceptionnelle pour gérer notre effectif croissant. Le portail libre-service a drastiquement réduit le volume de tickets RH.",
    "Le module d'évaluation de performance d'ArcheloFlow est excellent. Le feedback 360° donne aux managers des informations exploitables.",
    "Le meilleur investissement SIRH que nous ayons fait. Le suivi de conformité nous maintient prêts pour les audits en permanence.",
    "Le pipeline de recrutement dans ArcheloFlow est fluide. De la publication d'offre à la lettre d'embauche, tout s'enchaîne naturellement.",
    "L'équipe de support client est exceptionnelle. Ils ont compris nos défis de PME et configuré ArcheloFlow parfaitement pour notre organisation.",
    "Le tableau de bord de reporting donne à notre direction une visibilité en temps réel sur les effectifs et les indicateurs de rémunération.",
    "Le module d'administration des avantages sociaux a simplifié considérablement les campagnes d'adhésion annuelles.",
    "Nous avons évalué plusieurs plateformes SIRH et ArcheloFlow se démarque pour les PME. Le prix est juste et les fonctionnalités rivalisent avec les solutions entreprise.",
]

PASSIVE_FEEDBACK_FR = [
    "ArcheloFlow gère bien nos besoins RH de base, mais le module de formation semble sous-développé par rapport aux solutions LMS dédiées.",
    "Plateforme correcte dans l'ensemble. La paie fonctionne de manière fiable, mais les options de personnalisation des rapports pourraient être plus flexibles.",
    "L'annuaire des employés et l'organigramme sont solides, mais nous aimerions que l'application mobile ait plus de fonctionnalités.",
    "ArcheloFlow répond à nos besoins SIRH de base. Cependant, le prix semble élevé pour une entreprise de notre taille.",
    "Bon produit pour le suivi du temps et des présences. L'intégration avec notre logiciel comptable fonctionne, mais a nécessité plus de configuration que prévu.",
    "La plateforme est stable et l'équipe de support est serviable, mais les délais de réponse pour les problèmes non critiques peuvent s'étendre.",
    "Les flux d'intégration sont configurables, ce qui est bien, mais le module de gestion de la performance manque de fonctionnalités de définition d'objectifs.",
    "La gestion de la rémunération d'ArcheloFlow est adéquate, mais les concurrents offrent des outils de benchmarking plus sophistiqués.",
    "Fonctionne bien pour les employés basés en France, mais le support multi-pays est limité pour nos bureaux au Québec.",
    "Les fonctionnalités de gestion documentaire et de signature électronique sont pratiques, mais les limites de stockage sont restrictives.",
]

DETRACTOR_FEEDBACK_FR = [
    "La mise en œuvre d'ArcheloFlow a pris quatre mois au lieu des six semaines promises. La migration des données était truffée d'erreurs.",
    "Le module de paie a eu deux erreurs de calcul cette année qui ont affecté la confiance des employés. La précision de la paie devrait être non négociable.",
    "Le support client est frustrément lent. Nous avons soumis un rapport de bug critique et attendu 8 jours pour une réponse.",
    "L'interface utilisateur semble datée par rapport aux nouvelles plateformes SIRH. Nos employés se plaignent constamment du portail libre-service.",
    "Les augmentations de prix à chaque renouvellement sans améliorations correspondantes. Nous payons 40% de plus qu'il y a deux ans.",
    "L'intégration avec notre ERP est un casse-tête persistant. La documentation API est incomplète et la synchronisation casse régulièrement.",
    "Le moteur de reporting est extrêmement limité. Nous ne pouvons pas créer de rapports personnalisés sans exporter vers Excel.",
    "L'expérience mobile est insuffisante. Les employés ne peuvent pas compléter les demandes de congés sur leur téléphone sans problèmes.",
    "On nous avait promis un gestionnaire de compte dédié, mais le turnover chez eux fait que nous avons eu quatre contacts différents en deux ans.",
    "Les temps d'arrêt du système pendant notre dernière période d'adhésion aux avantages étaient inacceptables.",
]

KEY_THEMES_EN = [
    "Payroll Accuracy", "Onboarding Experience", "Employee Self-Service", "Performance Management",
    "Compliance & Reporting", "Recruitment Pipeline", "Mobile Experience", "Customer Support",
    "Pricing & Value", "Integration Capabilities", "User Interface", "System Reliability",
    "Data Migration", "Benefits Administration", "Training & LMS", "Compensation Management",
    "API & Integrations", "Implementation Process", "Account Management", "Time Tracking",
]

KEY_THEMES_FR = [
    "Précision de la Paie", "Expérience d'Intégration", "Libre-Service Employé", "Gestion de la Performance",
    "Conformité et Reporting", "Pipeline de Recrutement", "Expérience Mobile", "Support Client",
    "Prix et Valeur", "Capacités d'Intégration", "Interface Utilisateur", "Fiabilité du Système",
    "Migration de Données", "Administration des Avantages", "Formation et LMS", "Gestion de la Rémunération",
    "API et Intégrations", "Processus de Mise en Œuvre", "Gestion de Compte", "Suivi du Temps",
]


def weighted_choice(items_with_weights):
    population = []
    weights = []
    for item, weight in items_with_weights:
        population.append(item)
        weights.append(weight)
    return random.choices(population, weights=weights, k=1)[0]


def generate_nps_score(nps_bias=0):
    promoter_pct = 0.30 + (nps_bias * 0.08)
    passive_pct = 0.40 - (nps_bias * 0.03)
    rand = random.random()
    if rand < promoter_pct:
        return random.choice([9, 9, 10, 10])
    elif rand < promoter_pct + passive_pct:
        return random.choice([7, 7, 8, 8])
    else:
        return random.choice([3, 4, 5, 5, 6, 6])


def get_nps_category(score):
    if score >= 9:
        return "Promoter"
    elif score >= 7:
        return "Passive"
    return "Detractor"


def generate_coherent_scores(nps_score):
    nps_category = get_nps_category(nps_score)

    if nps_category == "Promoter":
        satisfaction = random.choice([4, 4, 5, 5])
        product_value = random.choice([4, 4, 5, 5])
        service = random.choice([4, 5, 5])
        pricing = random.choice([3, 4, 4, 5])
        support = random.choice([4, 4, 5, 5])
        csat = random.choice([4, 4, 5, 5])
        ces = random.choice([1, 2, 2, 3])
        sentiment_score = round(random.uniform(0.55, 0.92), 2)
        sentiment_label = "positive"
        churn_risk_score = round(random.uniform(0.03, 0.20), 2)
        churn_risk_level = "Minimal"
        recommendation_status = "recommended"
        promoter_drivers = ["product_features", "ease_of_use", "reliability", "professional_services", "customer_support"]
        loyalty_drivers = random.sample(promoter_drivers, random.randint(2, 4))
    elif nps_category == "Passive":
        satisfaction = random.choice([3, 3, 3, 4])
        product_value = random.choice([3, 3, 3, 4])
        service = random.choice([3, 3, 4, 4])
        pricing = random.choice([2, 3, 3, 3])
        support = random.choice([3, 3, 3, 4])
        csat = random.choice([3, 3, 3, 4])
        ces = random.choice([3, 4, 4, 5])
        sentiment_score = round(random.uniform(-0.15, 0.25), 2)
        sentiment_label = "neutral"
        churn_risk_score = round(random.uniform(0.30, 0.55), 2)
        churn_risk_level = random.choice(["Low", "Medium"])
        recommendation_status = "would_consider"
        passive_drivers = ["value_pricing", "communication", "onboarding", "integration"]
        loyalty_drivers = random.sample(passive_drivers, random.randint(1, 3))
    else:
        satisfaction = random.choice([1, 1, 2, 2, 3])
        product_value = random.choice([1, 1, 2, 2])
        service = random.choice([1, 2, 2, 2])
        pricing = random.choice([1, 1, 1, 2, 2])
        support = random.choice([1, 1, 2, 2])
        csat = random.choice([1, 1, 2, 2])
        ces = random.choice([5, 6, 6, 7, 7, 8])
        sentiment_score = round(random.uniform(-0.85, -0.25), 2)
        sentiment_label = "negative"
        if nps_score <= 4:
            churn_risk_score = round(random.uniform(0.70, 0.95), 2)
            churn_risk_level = "High"
        else:
            churn_risk_score = round(random.uniform(0.50, 0.75), 2)
            churn_risk_level = "Medium"
        recommendation_status = "would_not_recommend"
        detractor_drivers = ["value_pricing", "customer_support", "reliability", "onboarding"]
        loyalty_drivers = random.sample(detractor_drivers, random.randint(1, 2))

    return {
        "nps_category": nps_category,
        "satisfaction_rating": satisfaction,
        "product_value_rating": product_value,
        "service_rating": service,
        "pricing_rating": pricing,
        "support_rating": support,
        "csat_score": csat,
        "ces_score": ces,
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "churn_risk_score": churn_risk_score,
        "churn_risk_level": churn_risk_level,
        "recommendation_status": recommendation_status,
        "loyalty_drivers": loyalty_drivers,
    }


def generate_churn_risk_factors(nps_category, lang="en"):
    themes = KEY_THEMES_EN if lang == "en" else KEY_THEMES_FR
    if nps_category == "Promoter":
        return random.sample(themes[:6], random.randint(1, 2))
    elif nps_category == "Passive":
        return random.sample(themes[4:12], random.randint(2, 3))
    else:
        return random.sample(themes[6:16], random.randint(2, 4))


def generate_key_themes(nps_category, lang="en"):
    themes = KEY_THEMES_EN if lang == "en" else KEY_THEMES_FR
    sentiment_map = {"Promoter": "positive", "Passive": "neutral", "Detractor": "negative"}
    sentiment = sentiment_map.get(nps_category, "neutral")
    if nps_category == "Promoter":
        raw = random.sample(themes[:8], random.randint(2, 3))
    elif nps_category == "Passive":
        raw = random.sample(themes[4:14], random.randint(2, 3))
    else:
        raw = random.sample(themes[6:], random.randint(2, 4))
    return [{"theme": t, "sentiment": sentiment} for t in raw]


GROWTH_OPPORTUNITIES_EN = [
    {"type": "upselling", "description": "Client expressed interest in additional modules", "action": "Schedule product demo for advanced features"},
    {"type": "expansion", "description": "Growing headcount creates need for more licenses", "action": "Propose enterprise tier upgrade"},
    {"type": "referral", "description": "High satisfaction indicates referral potential", "action": "Enroll in referral program"},
    {"type": "cross_sell", "description": "Interest in complementary workforce analytics", "action": "Present analytics add-on package"},
    {"type": "advocacy", "description": "Promoter willing to provide testimonial", "action": "Invite to case study program"},
    {"type": "renewal", "description": "Strong satisfaction supports multi-year renewal", "action": "Propose multi-year contract with incentive"},
]

GROWTH_OPPORTUNITIES_FR = [
    {"type": "upselling", "description": "Le client a exprimé un intérêt pour des modules supplémentaires", "action": "Planifier une démo des fonctionnalités avancées"},
    {"type": "expansion", "description": "La croissance des effectifs crée un besoin de licences supplémentaires", "action": "Proposer une mise à niveau entreprise"},
    {"type": "referral", "description": "Satisfaction élevée indiquant un potentiel de recommandation", "action": "Inscrire au programme de parrainage"},
    {"type": "cross_sell", "description": "Intérêt pour des analyses RH complémentaires", "action": "Présenter le module analytique"},
    {"type": "advocacy", "description": "Promoteur disposé à fournir un témoignage", "action": "Inviter au programme d'études de cas"},
    {"type": "renewal", "description": "Forte satisfaction favorisant un renouvellement pluriannuel", "action": "Proposer un contrat pluriannuel avec incentive"},
]

ACCOUNT_RISKS_EN = [
    {"type": "churn_risk", "description": "Dissatisfaction with platform performance and reliability", "action": "Escalate to engineering for priority fix", "severity": "High"},
    {"type": "competitor_threat", "description": "Client evaluating competing HRIS platforms", "action": "Schedule executive business review", "severity": "Critical"},
    {"type": "pricing_concern", "description": "Renewal pricing perceived as too high for value delivered", "action": "Prepare custom retention pricing proposal", "severity": "High"},
    {"type": "support_failure", "description": "Repeated support tickets with slow resolution", "action": "Assign dedicated support engineer", "severity": "Medium"},
    {"type": "adoption_risk", "description": "Low platform adoption across employee base", "action": "Conduct adoption workshop with client HR team", "severity": "Medium"},
    {"type": "integration_issue", "description": "Persistent integration failures with client ERP", "action": "Deploy integration specialist for on-site audit", "severity": "High"},
]

ACCOUNT_RISKS_FR = [
    {"type": "churn_risk", "description": "Insatisfaction face à la performance et la fiabilité de la plateforme", "action": "Escalader à l'ingénierie pour correction prioritaire", "severity": "High"},
    {"type": "competitor_threat", "description": "Le client évalue des plateformes SIRH concurrentes", "action": "Planifier une revue d'affaires exécutive", "severity": "Critical"},
    {"type": "pricing_concern", "description": "Prix de renouvellement perçu comme trop élevé pour la valeur livrée", "action": "Préparer une proposition tarifaire de rétention", "severity": "High"},
    {"type": "support_failure", "description": "Tickets de support répétés avec résolution lente", "action": "Assigner un ingénieur de support dédié", "severity": "Medium"},
    {"type": "adoption_risk", "description": "Faible adoption de la plateforme par les employés", "action": "Organiser un atelier d'adoption avec l'équipe RH", "severity": "Medium"},
    {"type": "integration_issue", "description": "Échecs d'intégration persistants avec l'ERP du client", "action": "Déployer un spécialiste d'intégration", "severity": "High"},
]


def generate_growth_opportunities(nps_category, lang="en"):
    pool = GROWTH_OPPORTUNITIES_EN if lang == "en" else GROWTH_OPPORTUNITIES_FR
    if nps_category == "Promoter":
        return random.sample(pool, random.randint(2, 3))
    else:
        return random.sample(pool[:4], random.randint(1, 2))


def generate_account_risk_factors(nps_category, lang="en"):
    pool = ACCOUNT_RISKS_EN if lang == "en" else ACCOUNT_RISKS_FR
    if nps_category == "Detractor":
        return random.sample(pool, random.randint(2, 3))
    else:
        return random.sample(pool[3:], random.randint(1, 2))


def generate_feedback(nps_category, lang="en"):
    if lang == "fr":
        if nps_category == "Promoter":
            return random.choice(PROMOTER_FEEDBACK_FR)
        elif nps_category == "Passive":
            return random.choice(PASSIVE_FEEDBACK_FR)
        return random.choice(DETRACTOR_FEEDBACK_FR)
    else:
        if nps_category == "Promoter":
            return random.choice(PROMOTER_FEEDBACK_EN)
        elif nps_category == "Passive":
            return random.choice(PASSIVE_FEEDBACK_EN)
        return random.choice(DETRACTOR_FEEDBACK_EN)


def generate_growth_data(nps_score, commercial_value):
    if nps_score >= 9:
        growth_factor = round(random.uniform(1.15, 1.30), 2)
        growth_rate = f"{int((growth_factor - 1) * 100)}%"
        growth_range = "80-100" if nps_score == 10 else "70-89"
    elif nps_score >= 7:
        growth_factor = round(random.uniform(1.02, 1.12), 2)
        growth_rate = f"{int((growth_factor - 1) * 100)}%"
        growth_range = "50-69" if nps_score == 8 else "40-59"
    else:
        growth_factor = round(random.uniform(0.85, 1.00), 2)
        factor_val = growth_factor - 1
        growth_rate = f"{int(factor_val * 100)}%"
        growth_range = "0-39"
    return growth_factor, growth_rate, growth_range


def generate_random_timestamp(start_date, end_date):
    days_between = (end_date - start_date).days
    random_days = random.randint(0, max(days_between, 1))
    result_date = start_date + timedelta(days=random_days)
    return datetime.combine(result_date, datetime.min.time()).replace(
        hour=random.randint(8, 18), minute=random.randint(0, 59),
        second=random.randint(0, 59)
    )


def get_or_create_survey_template():
    template = SurveyTemplate.query.filter_by(
        name='Comprehensive CX Survey', is_system=True
    ).first()
    if template:
        return template
    template = SurveyTemplate()
    template.name = 'Comprehensive CX Survey'
    template.version = '1.0'
    template.is_system = True
    template.description_en = 'Complete customer experience survey with NPS, driver attribution, feature evaluation, and open feedback'
    template.description_fr = "Enquête complète sur l'expérience client avec NPS, attribution des facteurs, évaluation des fonctionnalités et feedback ouvert"
    template.estimated_duration_minutes = 10
    template.sections_config = {
        'section_1': {'name_en': 'NPS & Driver Attribution', 'name_fr': 'NPS et attribution des facteurs', 'required': True},
        'section_2': {'name_en': 'Feature Evaluation', 'name_fr': 'Évaluation des fonctionnalités', 'required': False},
        'section_3': {'name_en': 'Additional Insights', 'name_fr': 'Informations complémentaires', 'required': False},
    }
    template.default_driver_labels = DEFAULT_DRIVER_LABELS
    template.default_feature_count = 5
    template.max_features = 9
    db.session.add(template)
    db.session.flush()
    return template


def get_or_create_participant(business_account_id, company, campaign_id, company_commercial_values):
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    role = weighted_choice(ROLES_WEIGHTED)
    tier = weighted_choice(TIERS_WEIGHTED)
    region = random.choice(REGIONS)
    industry = random.choice(INDUSTRIES)
    tenure = round(random.uniform(1.0, 10.0), 1)
    name = f"{first_name} {last_name}"
    email = f"{first_name.lower()}.{last_name.lower()}@{company.lower().replace(' ', '').replace(',', '')}.com"

    if company not in company_commercial_values:
        company_commercial_values[company] = round(random.uniform(25000, 750000), 2)
    commercial_value = company_commercial_values[company]

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
            role=role,
            region=region,
            customer_tier=tier,
            client_industry=industry,
            language='en',
            tenure_years=tenure,
            company_commercial_value=commercial_value,
            source='admin_bulk',
            status='completed',
            token=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
        )
        db.session.add(participant)
        db.session.flush()
    else:
        participant.role = role
        participant.region = region
        participant.customer_tier = tier
        participant.client_industry = industry
        participant.tenure_years = tenure
        participant.company_commercial_value = commercial_value

    cp = CampaignParticipant.query.filter_by(
        campaign_id=campaign_id,
        participant_id=participant.id
    ).first()

    if not cp:
        cp = CampaignParticipant(
            campaign_id=campaign_id,
            participant_id=participant.id,
            business_account_id=business_account_id,
            status='completed',
            token=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db.session.add(cp)
        db.session.flush()

    return participant, cp


def generate_campaign(campaign_key, dry_run=False):
    config = CAMPAIGN_CONFIGS[campaign_key]

    print(f"\n{'=' * 70}")
    print(f"  Campaign: {config['name']}")
    print(f"  Type: {config['survey_type']} | Language: {config['language_code']}")
    print(f"  Dates: {config['start_date']} to {config['end_date']}")
    print(f"  Target responses: {config['responses']}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'=' * 70}\n")

    with app.app_context():
        try:
            ba = BusinessAccount.query.filter_by(name=BUSINESS_ACCOUNT_NAME).first()
            if not ba:
                print(f"  ERROR: Business account '{BUSINESS_ACCOUNT_NAME}' not found!")
                return False

            print(f"  Business Account: {ba.name} (ID: {ba.id})")

            existing = Campaign.query.filter_by(
                business_account_id=ba.id,
                name=config['name']
            ).first()
            if existing:
                print(f"  Campaign '{config['name']}' already exists (ID: {existing.id}, status: {existing.status})")
                print(f"  Use --delete to remove it first if you want to regenerate.")
                return False

            if dry_run:
                existing_companies = _get_existing_companies(ba.id, None)
                num_reuse = int(len(existing_companies) * (config['company_reuse_pct'] / 100)) if existing_companies else 0
                available_new = [c for c in COMPANIES if c not in existing_companies]
                num_new = min(config['responses'] - num_reuse, len(available_new))
                print(f"\n  DRY RUN SUMMARY:")
                print(f"    Would create 1 campaign: '{config['name']}'")
                print(f"    Would generate {config['responses']} survey responses")
                print(f"    Company mix: {num_reuse} reused + {num_new} new")
                print(f"    Survey type: {config['survey_type']}")
                print(f"    Language: {config['language_code']}")
                if config['survey_type'] == 'classic':
                    print(f"    Would create ClassicSurveyConfig with 9 driver labels")
                print(f"\n  Dry run passed. Run without --dry-run to execute.\n")
                return True

            campaign = Campaign(
                business_account_id=ba.id,
                name=config['name'],
                description=config['description'],
                start_date=config['start_date'],
                end_date=config['end_date'],
                status='completed',
                survey_type=config['survey_type'],
                language_code=config['language_code'],
                client_identifier=ba.name,
                created_at=datetime.combine(config['start_date'] - timedelta(days=7), datetime.min.time()),
                completed_at=config['completed_at'],
            )
            db.session.add(campaign)
            db.session.flush()
            print(f"  Created campaign: {campaign.name} (ID: {campaign.id})")

            if config['survey_type'] == 'classic':
                template = get_or_create_survey_template()
                classic_config = ClassicSurveyConfig(
                    campaign_id=campaign.id,
                    template_id=template.id,
                    sections_enabled={'section_1': True, 'section_2': True, 'section_3': True},
                    feature_count=5,
                    features=[
                        {'key': 'payroll', 'label_en': 'Payroll Processing', 'label_fr': 'Traitement de la Paie'},
                        {'key': 'leave_mgmt', 'label_en': 'Leave Management', 'label_fr': 'Gestion des Congés'},
                        {'key': 'performance', 'label_en': 'Performance Reviews', 'label_fr': 'Évaluations de Performance'},
                        {'key': 'recruitment', 'label_en': 'Recruitment Pipeline', 'label_fr': 'Pipeline de Recrutement'},
                        {'key': 'self_service', 'label_en': 'Employee Self-Service Portal', 'label_fr': 'Portail Libre-Service Employé'},
                    ],
                    driver_labels=DEFAULT_DRIVER_LABELS,
                    custom_prompts={},
                    frozen_at=config['completed_at'],
                )
                db.session.add(classic_config)
                db.session.flush()
                print(f"  Created ClassicSurveyConfig (ID: {classic_config.id})")

            existing_companies = _get_existing_companies(ba.id, campaign.id)
            num_reuse = int(len(existing_companies) * (config['company_reuse_pct'] / 100))
            reused = random.sample(existing_companies, min(num_reuse, len(existing_companies))) if existing_companies else []
            available_new = [c for c in COMPANIES if c not in existing_companies]
            needed_new = config['responses'] - len(reused)
            new_cos = random.sample(available_new, min(needed_new, len(available_new)))
            campaign_companies = reused + new_cos
            random.shuffle(campaign_companies)
            print(f"  Companies: {len(reused)} reused + {len(new_cos)} new = {len(campaign_companies)} total")

            company_commercial_values = {}
            nps_dist = {"Promoter": 0, "Passive": 0, "Detractor": 0}
            lang = config['language_code']
            nps_bias = config.get('nps_bias', 0)

            print(f"\n  Generating {config['responses']} responses (NPS bias: {nps_bias})...")

            for i in range(config['responses']):
                company = random.choice(campaign_companies)
                participant, cp = get_or_create_participant(
                    ba.id, company, campaign.id, company_commercial_values
                )

                nps_score = generate_nps_score(nps_bias=nps_bias)
                scores = generate_coherent_scores(nps_score)
                nps_category = scores["nps_category"]
                feedback = generate_feedback(nps_category, lang)
                key_themes = generate_key_themes(nps_category, lang)
                churn_factors = generate_churn_risk_factors(nps_category, lang)
                growth_factor, growth_rate, growth_range = generate_growth_data(
                    nps_score, company_commercial_values[company]
                )

                growth_opps = None
                if nps_score >= 7:
                    growth_opps = json.dumps(generate_growth_opportunities(nps_category, lang))

                account_risks = None
                if nps_score < 7:
                    account_risks = json.dumps(generate_account_risk_factors(nps_category, lang))

                response_ts = generate_random_timestamp(config['start_date'], config['end_date'])

                response = SurveyResponse(
                    campaign_id=campaign.id,
                    campaign_participant_id=cp.id,
                    company_name=company,
                    respondent_name=participant.name,
                    respondent_email=participant.email,
                    tenure_with_fc=f"{participant.tenure_years:.0f} years" if participant.tenure_years else "< 1 year",
                    nps_score=nps_score,
                    nps_category=nps_category,
                    satisfaction_rating=scores["satisfaction_rating"],
                    product_value_rating=scores["product_value_rating"],
                    service_rating=scores["service_rating"],
                    pricing_rating=scores["pricing_rating"],
                    support_rating=scores["support_rating"],
                    csat_score=scores["csat_score"],
                    ces_score=scores["ces_score"],
                    loyalty_drivers=scores["loyalty_drivers"],
                    recommendation_status=scores["recommendation_status"],
                    improvement_feedback=feedback,
                    recommendation_reason=generate_feedback(nps_category, lang),
                    additional_comments=generate_feedback(nps_category, lang) if random.random() > 0.4 else None,
                    sentiment_score=scores["sentiment_score"],
                    sentiment_label=scores["sentiment_label"],
                    key_themes=json.dumps(key_themes),
                    churn_risk_score=scores["churn_risk_score"],
                    churn_risk_level=scores["churn_risk_level"],
                    churn_risk_factors=json.dumps(churn_factors),
                    growth_opportunities=growth_opps,
                    account_risk_factors=account_risks,
                    growth_factor=growth_factor,
                    growth_rate=growth_rate,
                    growth_range=growth_range,
                    commercial_value=company_commercial_values[company],
                    source_type=config['survey_type'],
                    created_at=response_ts,
                    analyzed_at=response_ts + timedelta(minutes=random.randint(1, 30)),
                )
                db.session.add(response)
                nps_dist[nps_category] += 1

                if (i + 1) % 100 == 0:
                    print(f"    Progress: {i + 1}/{config['responses']}")

            db.session.commit()

            total = sum(nps_dist.values())
            p_pct = nps_dist["Promoter"] / total * 100
            pa_pct = nps_dist["Passive"] / total * 100
            d_pct = nps_dist["Detractor"] / total * 100
            nps = p_pct - d_pct

            print(f"\n  SUCCESS: Generated {total} responses for '{campaign.name}'")
            print(f"\n  NPS Distribution:")
            print(f"    Promoters:  {nps_dist['Promoter']:>4} ({p_pct:.1f}%)")
            print(f"    Passives:   {nps_dist['Passive']:>4} ({pa_pct:.1f}%)")
            print(f"    Detractors: {nps_dist['Detractor']:>4} ({d_pct:.1f}%)")
            print(f"    NPS Score:  {nps:.1f}")
            print(f"\n  Campaign status: completed (completed_at: {config['completed_at']})")
            print()
            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n  ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False


def delete_campaign(campaign_key):
    config = CAMPAIGN_CONFIGS[campaign_key]

    print(f"\n{'=' * 70}")
    print(f"  Deleting campaign: {config['name']}")
    print(f"{'=' * 70}\n")

    with app.app_context():
        try:
            ba = BusinessAccount.query.filter_by(name=BUSINESS_ACCOUNT_NAME).first()
            if not ba:
                print(f"  ERROR: Business account '{BUSINESS_ACCOUNT_NAME}' not found!")
                return False

            campaign = Campaign.query.filter_by(
                business_account_id=ba.id,
                name=config['name']
            ).first()

            if not campaign:
                print(f"  Campaign '{config['name']}' not found. Nothing to delete.")
                return True

            print(f"  Found campaign: {campaign.name} (ID: {campaign.id})")

            fk_tables = [
                ("survey responses", SurveyResponse, campaign.id),
                ("campaign participants", CampaignParticipant, campaign.id),
                ("executive reports", ExecutiveReport, campaign.id),
                ("email deliveries", EmailDelivery, campaign.id),
                ("active conversations", ActiveConversation, campaign.id),
                ("export jobs", ExportJob, campaign.id),
            ]

            for label, model, cid in fk_tables:
                count = model.query.filter_by(campaign_id=cid).count()
                if count > 0:
                    model.query.filter_by(campaign_id=cid).delete()
                    print(f"    Deleted {count} {label}")

            from sqlalchemy import text
            for raw_table in ['campaign_kpi_snapshots']:
                result = db.session.execute(
                    text(f"DELETE FROM {raw_table} WHERE campaign_id = :cid"),
                    {"cid": campaign.id}
                )
                if result.rowcount > 0:
                    print(f"    Deleted {result.rowcount} {raw_table}")

            if config['survey_type'] == 'classic':
                ClassicSurveyConfig.query.filter_by(campaign_id=campaign.id).delete()
                print(f"    Deleted ClassicSurveyConfig")

            db.session.delete(campaign)
            db.session.commit()
            print(f"\n  SUCCESS: Campaign '{config['name']}' and all related data deleted.")
            print()
            return True

        except Exception as e:
            db.session.rollback()
            print(f"\n  ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False


def _get_existing_companies(business_account_id, exclude_campaign_id):
    query = db.session.query(SurveyResponse.company_name).join(
        Campaign, SurveyResponse.campaign_id == Campaign.id
    ).filter(Campaign.business_account_id == business_account_id)
    if exclude_campaign_id:
        query = query.filter(SurveyResponse.campaign_id != exclude_campaign_id)
    results = query.distinct().all()
    return [r[0] for r in results if r[0]]


def main():
    parser = argparse.ArgumentParser(description='Generate demo data for Archelo Group — ArcheloFlow HRIS')
    parser.add_argument('--campaign', choices=['Q1', 'Q2', 'Q3', 'CLASSIC'], required=True,
                        help='Campaign to generate: Q1 (EN conv), Q2 (EN conv), Q3 (FR conv), CLASSIC (EN classic)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would be generated without making changes')
    parser.add_argument('--delete', action='store_true',
                        help='Delete a previously generated campaign and all its data')

    args = parser.parse_args()

    if args.delete:
        success = delete_campaign(args.campaign)
    else:
        success = generate_campaign(args.campaign, dry_run=args.dry_run)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
