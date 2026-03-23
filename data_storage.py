import json
import re
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import func, case
from app import db, cache
from models import SurveyResponse, Campaign, CampaignKPISnapshot, Participant, CampaignParticipant, ClassicSurveyConfig
from flask import request
from cache_config import cache_config

logger = logging.getLogger(__name__)

# Feature flags for French language support
USE_BILINGUAL_THEMES = os.getenv('USE_BILINGUAL_THEMES', 'true').lower() == 'true'

# Cache for theme mappings loaded from JSON
_theme_mappings_cache = None
_theme_mappings_load_time = None
THEME_MAPPINGS_TTL = 300  # 5 minutes cache

def load_theme_mappings():
    """Load theme mappings from JSON config file with caching and validation"""
    global _theme_mappings_cache, _theme_mappings_load_time
    
    # Check cache validity
    if _theme_mappings_cache is not None and _theme_mappings_load_time is not None:
        if (datetime.utcnow() - _theme_mappings_load_time).total_seconds() < THEME_MAPPINGS_TTL:
            return _theme_mappings_cache
    
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'theme_mappings.json')
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Validate config structure
        if 'mappings' not in config:
            raise ValueError("Theme mappings config missing 'mappings' key")
        
        # Build flat lookup structure for efficient consolidation
        mappings = config['mappings']
        
        # Cache the loaded mappings
        _theme_mappings_cache = mappings
        _theme_mappings_load_time = datetime.utcnow()
        
        logger.info(f"Loaded {len(mappings)} theme mappings from config (version: {config.get('version', 'unknown')})")
        return mappings
        
    except FileNotFoundError:
        logger.warning("Theme mappings config file not found, using legacy English-only mappings")
        return None
    except Exception as e:
        logger.error(f"Error loading theme mappings config: {e}")
        return None

def consolidate_theme_name(theme_name):
    """
    Consolidate similar theme names to reduce duplication.
    Supports bilingual (French/English) theme normalization when USE_BILINGUAL_THEMES=true.
    """
    if not theme_name:
        return 'unknown'
    
    # Convert to lowercase and strip whitespace
    normalized = theme_name.lower().strip()
    
    # Remove common adjectives and determiners (works for both languages)
    normalized = re.sub(r'\b(customer|client|user|our|the|good|bad|great|poor)\s+', '', normalized)
    normalized = re.sub(r'\b(le|la|les|un|une|des|mon|ma|mes|bon|mauvais)\s+', '', normalized)
    
    # Use bilingual mappings if feature flag enabled
    if USE_BILINGUAL_THEMES:
        mappings = load_theme_mappings()
        
        if mappings:
            # Search through all canonical themes and their variations
            for canonical_theme, language_variations in mappings.items():
                # Check English variations
                if 'en' in language_variations:
                    for variation in language_variations['en']:
                        if normalized == variation.lower() or variation.lower() in normalized:
                            return canonical_theme
                
                # Check French variations
                if 'fr' in language_variations:
                    for variation in language_variations['fr']:
                        if normalized == variation.lower() or variation.lower() in normalized:
                            return canonical_theme
    
    # Legacy fallback: English-only hardcoded mappings
    legacy_theme_mappings = {
        'service': ['service', 'services', 'customer service', 'client service', 'support service'],
        'support': ['support', 'customer support', 'tech support', 'technical support', 'help', 'assistance'],
        'product': ['product', 'products', 'offering', 'solution', 'solutions'],
        'pricing': ['pricing', 'price', 'prices', 'cost', 'costs', 'billing', 'payment'],
        'quality': ['quality', 'reliability', 'performance', 'effectiveness'],
        'features': ['features', 'feature', 'functionality', 'capabilities', 'tools'],
        'team': ['team', 'staff', 'personnel', 'employees', 'people'],
        'communication': ['communication', 'response time', 'responsiveness', 'follow-up'],
        'value': ['value', 'worth', 'roi', 'return on investment'],
        'experience': ['experience', 'satisfaction', 'journey', 'interaction']
    }
    
    # Find the canonical theme for this name using legacy mappings
    for canonical_theme, variations in legacy_theme_mappings.items():
        if normalized in variations or any(variation in normalized for variation in variations):
            return canonical_theme
    
    # If no mapping found, return the normalized version (singular form)
    if normalized.endswith('s') and len(normalized) > 3:
        return normalized[:-1]  # Simple singularization
    
    return normalized

def normalize_opportunity_type(opp_type):
    """Normalize opportunity types for better grouping"""
    if not opp_type:
        return 'unknown'
    
    # Convert to lowercase and strip whitespace
    normalized = opp_type.lower().strip()
    
    # Define mapping for similar opportunity types
    type_mappings = {
        'upsell': ['upsell', 'upselling', 'up-sell', 'up-selling'],
        'cross-sell': ['cross-sell', 'cross-selling', 'crosssell', 'crossselling'],
        'advocacy': ['advocacy', 'advocate', 'brand advocacy', 'testimonial'],
        'partnership': ['partnership', 'partnerships', 'partnership opportunities', 'partner'],
        'product_improvement': ['product improvement', 'product enhancement', 'product feedback'],
        'support_enhancement': ['support enhancement', 'support improvement', 'customer support'],
        'feature_request': ['feature request', 'feature requests', 'new features'],
        'retention': ['retention', 'churn prevention', 'customer retention']
    }
    
    # Find the canonical type for this opportunity
    for canonical_type, variations in type_mappings.items():
        if normalized in variations:
            return canonical_type
    
    # If no mapping found, return the normalized version
    return normalized

def normalize_risk_factor_type(risk_type):
    """Normalize risk factor types for better grouping"""
    if not risk_type:
        return 'unknown'
    
    # Convert to lowercase and strip whitespace
    normalized = risk_type.lower().strip()
    
    # Define mapping for similar risk factor types
    type_mappings = {
        'pricing_concern': ['pricing concern', 'pricing concerns', 'price sensitivity', 'cost issues', 'expensive'],
        'service_issue': ['service issue', 'service issues', 'poor service', 'support problem', 'support issues'],
        'product_problem': ['product problem', 'product issues', 'quality issue', 'product quality', 'functionality'],
        'competitor_risk': ['competitor risk', 'competitor mention', 'competitive threat', 'considering alternatives'],
        'satisfaction_risk': ['critical_satisfaction', 'low_satisfaction', 'dissatisfaction', 'unhappy customer'],
        'relationship_risk': ['relationship risk', 'communication issue', 'trust issue', 'poor relationship'],
        'contract_risk': ['contract risk', 'renewal risk', 'contract concerns', 'renewal at risk'],
        'churn_risk': ['churn risk', 'retention risk', 'at risk', 'likely to leave'],
        'poor_ratings': ['poor ratings', 'low ratings', 'rating concerns', 'poor performance']
    }
    
    # Find the canonical type for this risk factor
    for canonical_type, variations in type_mappings.items():
        if normalized in variations:
            return canonical_type
    
    # If no mapping found, return the normalized version
    return normalized


OPPORTUNITY_WEIGHTS = {
    'upsell': 3.0,
    'expansion': 3.0,
    'cross_sell': 2.0,
    'cross sell': 2.0,
    'referral': 1.5,
    'advocacy': 1.5,
    'renewal': 1.0,
}

RISK_SEVERITY_WEIGHTS = {
    'Critical': 3.0,
    'High': 2.0,
    'Medium': 1.0,
    'Low': 0.5,
}

HEALTH_RATIO_HIGH_POTENTIAL = 0.65
HEALTH_RATIO_RISK_HEAVY = 0.35


def calculate_weighted_account_balance(opportunities, risk_factors):
    """
    Weighted scoring for account health balance classification.

    Opportunity score: each opportunity type is weighted by business impact
    (upsell/expansion=3, cross-sell=2, referral/advocacy=1.5, renewal=1,
    unknown defaults to 1).  When an opportunity entry carries a ``count``
    field the weight is multiplied by that count.

    Risk score: each risk factor is weighted by severity
    (Critical=3, High=2, Medium=1, Low=0.5).  ``count`` is honoured the
    same way.

    Health ratio = opportunity_score / (opportunity_score + risk_score).
    * > 0.65 → opportunity_heavy  (High Potential)
    * 0.35 – 0.65 → balanced
    * < 0.35 → risk_heavy

    Returns (balance, opportunity_score, risk_score, health_ratio).
    """

    opp_score = 0.0
    for opp in opportunities:
        opp_type = opp.get('type', '').lower().replace('-', '_')
        weight = OPPORTUNITY_WEIGHTS.get(opp_type, 1.0)
        count = opp.get('count', 1) or 1
        opp_score += weight * count

    risk_score = 0.0
    for risk in risk_factors:
        severity = risk.get('severity', 'Medium')
        weight = RISK_SEVERITY_WEIGHTS.get(severity, 1.0)
        count = risk.get('count', 1) or 1
        risk_score += weight * count

    total = opp_score + risk_score
    health_ratio = (opp_score / total) if total > 0 else 0.5

    if health_ratio >= HEALTH_RATIO_HIGH_POTENTIAL:
        balance = 'opportunity_heavy'
    elif health_ratio <= HEALTH_RATIO_RISK_HEAVY:
        balance = 'risk_heavy'
    else:
        balance = 'balanced'

    return balance, opp_score, risk_score, health_ratio


def get_dashboard_data_cached(campaign_id=None, business_account_id=None):
    """
    Cached wrapper for dashboard data retrieval with performance optimization.
    Uses optimized queries to reduce database round-trips from 20+ to 2-3.
    Cache can be disabled/configured by admins via environment variables.

    Phase 2: 2-hour cache TTL for 10x performance improvement on repeat visits.
    SECURITY: Cache key MUST include business_account_id to prevent cross-tenant data leakage.

    Cache guard: only cache when business_account_id is confirmed non-null to prevent
    stale/demo data being stored under the wrong key (original Nov 2025 bug).
    Active campaigns use a 30-minute TTL; completed campaigns use the full 2-hour TTL.
    """
    import time
    start_time = time.time()

    # Generate TENANT-SCOPED cache key for multi-tenant security
    cache_key = f"dashboard_data_campaign{campaign_id}_tenant{business_account_id}"

    # --- CACHE GUARD ---
    # Only use the cache when business_account_id is resolved and non-null.
    # A null/unresolved ID was the root cause of the original stale-data flash bug
    # (demo data was cached under the wrong key before auth was fully resolved).
    use_cache = cache_config.is_enabled() and business_account_id is not None

    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            cache_config.record_hit()
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"✅ CACHE HIT | Campaign: {campaign_id} | Tenant: {business_account_id} | Time: {elapsed:.0f}ms")
            return cached
        cache_config.record_miss()
        logger.info(f"🔍 CACHE MISS | Campaign: {campaign_id} | Tenant: {business_account_id} | Key: {cache_key}")
    else:
        logger.info(f"⏭️ CACHE SKIPPED | Campaign: {campaign_id} | Tenant: {business_account_id} | Cache enabled: {cache_config.is_enabled()}")

    # --- DATA FETCH ---
    use_optimized = os.environ.get('USE_OPTIMIZED_DASHBOARD', 'true').lower() == 'true'

    result = None
    if use_optimized:
        try:
            from dashboard_query_optimizer import get_optimized_dashboard_data
            logger.info(f"✅ Using OPTIMIZED dashboard queries")
            result = get_optimized_dashboard_data(campaign_id, business_account_id)
        except Exception as e:
            logger.warning(f"⚠️ Optimized queries FAILED, falling back to original: {e}")

    if result is None:
        logger.info(f"⏪ Using ORIGINAL dashboard queries")
        result = get_dashboard_data(campaign_id, business_account_id)

    # --- CACHE STORE ---
    # Determine TTL based on campaign status:
    #   - Completed campaigns: 2-hour TTL (data is immutable)
    #   - Active campaigns: 30-minute TTL (data changes as responses arrive)
    if use_cache and result is not None:
        try:
            campaign_status = None
            if campaign_id:
                campaign_obj = Campaign.query.get(campaign_id)
                if campaign_obj:
                    campaign_status = campaign_obj.status

            if campaign_status == 'completed':
                ttl = cache_config.get_timeout()  # 2-hour TTL from cache_config
            else:
                ttl = 1800  # 30-minute TTL for active campaigns

            cache.set(cache_key, result, timeout=ttl)
            logger.info(f"💾 CACHE SET | Campaign: {campaign_id} | Status: {campaign_status} | TTL: {ttl}s | Tenant: {business_account_id}")
        except Exception as cache_err:
            logger.warning(f"⚠️ Failed to write to cache: {cache_err}")

    execution_time = (time.time() - start_time) * 1000
    logger.info(f"⏱️ Dashboard data generated | Time: {execution_time:.0f}ms | Key: {cache_key}")

    return result


def bust_dashboard_cache(campaign_id, business_account_id, company_name=None):
    """
    Invalidate the dashboard cache for a specific campaign and tenant.
    Call this whenever new survey responses are submitted for an active campaign
    so the next load reflects fresh data.
    
    If company_name is provided, also busts the company detail cache for that company.
    """
    cache_key = f"dashboard_data_campaign{campaign_id}_tenant{business_account_id}"
    try:
        cache.delete(cache_key)
        logger.info(f"🗑️ CACHE BUSTED | Campaign: {campaign_id} | Tenant: {business_account_id} | Key: {cache_key}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to bust dashboard cache: {e}")

    if company_name:
        try:
            bust_company_detail_cache(campaign_id, company_name, business_account_id)
        except Exception as e:
            logger.warning(f"⚠️ Failed to bust company detail cache: {e}")

def get_dashboard_data(campaign_id=None, business_account_id=None):
    """Compile dashboard data for visualization with optional campaign filtering"""
    try:
        # ============================================================================
        # SNAPSHOT CHECK: Use immutable snapshot data for closed campaigns
        # ============================================================================
        if campaign_id:
            # Check if campaign is closed and has a snapshot
            campaign = Campaign.query.get(campaign_id)
            if campaign and campaign.status == 'completed':
                # Look for the most recent snapshot for this campaign
                snapshot = CampaignKPISnapshot.query.filter_by(
                    campaign_id=campaign_id
                ).order_by(CampaignKPISnapshot.snapshot_created_at.desc()).first()
                
                if snapshot:
                    print(f"Using KPI snapshot for closed campaign: {campaign.name} (ID: {campaign_id})")
                    return convert_snapshot_to_dashboard_format(snapshot)
                else:
                    print(f"Warning: Closed campaign {campaign.name} has no snapshot - generating live data")
        
        # ============================================================================
        # LIVE CALCULATION: For active campaigns or campaigns without snapshots
        # ============================================================================
        
        # Build base query with optional campaign filtering
        base_query = SurveyResponse.query
        if campaign_id:
            base_query = base_query.filter(SurveyResponse.campaign_id == campaign_id)
        
        # Basic statistics
        total_responses = base_query.count()
        
        # Count unique companies with campaign filtering
        total_companies_query = db.session.query(
            func.count(func.distinct(SurveyResponse.company_name))
        )
        if campaign_id:
            total_companies_query = total_companies_query.filter(SurveyResponse.campaign_id == campaign_id)
        total_companies = total_companies_query.scalar() or 0
        
        # NPS distribution with campaign filtering
        nps_query = db.session.query(
            SurveyResponse.nps_category,
            func.count(SurveyResponse.id).label('count')
        )
        if campaign_id:
            nps_query = nps_query.filter(SurveyResponse.campaign_id == campaign_id)
        nps_distribution = nps_query.group_by(SurveyResponse.nps_category).all()
        
        # Calculate NPS score with campaign filtering
        promoters_query = db.session.query(func.count(SurveyResponse.id)).filter(
            SurveyResponse.nps_score >= 9
        )
        if campaign_id:
            promoters_query = promoters_query.filter(SurveyResponse.campaign_id == campaign_id)
        promoters = promoters_query.scalar() or 0
        
        detractors_query = db.session.query(func.count(SurveyResponse.id)).filter(
            SurveyResponse.nps_score <= 6
        )
        if campaign_id:
            detractors_query = detractors_query.filter(SurveyResponse.campaign_id == campaign_id)
        detractors = detractors_query.scalar() or 0
        
        nps_score = ((promoters - detractors) / total_responses * 100) if total_responses > 0 else 0
        
        # Recent responses (last 30 days) with campaign filtering
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_query = base_query.filter(
            SurveyResponse.created_at >= thirty_days_ago
        )
        recent_responses = recent_query.count()
        
        # Sentiment distribution with campaign filtering
        sentiment_query = db.session.query(
            SurveyResponse.sentiment_label,
            func.count(SurveyResponse.id).label('count')
        ).filter(
            SurveyResponse.sentiment_label.isnot(None)
        )
        if campaign_id:
            sentiment_query = sentiment_query.filter(SurveyResponse.campaign_id == campaign_id)
        sentiment_distribution = sentiment_query.group_by(SurveyResponse.sentiment_label).all()
        
        # Churn risk distribution
        churn_risk_data = db.session.query(
            SurveyResponse.churn_risk_score,
            SurveyResponse.company_name,
            SurveyResponse.nps_score
        ).filter(
            SurveyResponse.churn_risk_score.isnot(None)
        ).order_by(SurveyResponse.churn_risk_score.desc()).all()
        
        # High risk accounts - grouped by company (case-insensitive) with campaign filtering
        high_risk_by_company = {}
        high_risk_query = SurveyResponse.query.filter(
            SurveyResponse.churn_risk_level.in_(['High', 'Critical'])  # Include Critical risk too
        )
        if campaign_id:
            high_risk_query = high_risk_query.filter(SurveyResponse.campaign_id == campaign_id)
        high_risk_responses = high_risk_query.all()
        
        for response in high_risk_responses:
            if response.company_name:
                company_key = response.company_name.upper()  # Case-insensitive grouping
                
                if company_key not in high_risk_by_company:
                    high_risk_by_company[company_key] = {
                        'company_name': response.company_name,
                        'risk_levels': [],
                        'risk_scores': [],
                        'nps_scores': [],
                        'respondent_count': 0,
                        'latest_response': response.created_at
                    }
                else:
                    # Update display name to most recent case version
                    high_risk_by_company[company_key]['company_name'] = response.company_name
                    # Update latest response date
                    if response.created_at > high_risk_by_company[company_key]['latest_response']:
                        high_risk_by_company[company_key]['latest_response'] = response.created_at
                
                # Add this response's data
                company_data = high_risk_by_company[company_key]
                if response.churn_risk_level:
                    company_data['risk_levels'].append(response.churn_risk_level)
                if response.churn_risk_score is not None:
                    company_data['risk_scores'].append(response.churn_risk_score)
                if response.nps_score is not None:
                    company_data['nps_scores'].append(response.nps_score)
                company_data['respondent_count'] += 1
        
        # Convert to final format with aggregated data
        high_risk_accounts = []
        for company_key, company_data in high_risk_by_company.items():
            # Determine highest risk level for the company
            risk_levels = company_data['risk_levels']
            if 'Critical' in risk_levels:
                max_risk_level = 'Critical'
            elif 'High' in risk_levels:
                max_risk_level = 'High'
            else:
                max_risk_level = 'Medium'  # Fallback
            
            # Calculate average risk score from high-risk responses
            avg_risk_score = sum(company_data['risk_scores']) / len(company_data['risk_scores']) if company_data['risk_scores'] else 0
            
            # Calculate TRUE company NPS from ALL responses in this campaign (not just high-risk ones)
            company_all_responses_query = SurveyResponse.query.filter(
                func.upper(SurveyResponse.company_name) == company_key
            )
            if campaign_id:
                company_all_responses_query = company_all_responses_query.filter(SurveyResponse.campaign_id == campaign_id)
            
            company_all_responses = company_all_responses_query.all()
            
            # Calculate company NPS properly: (Promoters - Detractors) / Total * 100
            total_company_responses = len(company_all_responses)
            promoters = sum(1 for r in company_all_responses if r.nps_score >= 9)
            detractors = sum(1 for r in company_all_responses if r.nps_score <= 6)
            company_nps = round(((promoters - detractors) / total_company_responses) * 100) if total_company_responses > 0 else 0

            # Confidence level based on invited count vs responses (same logic as account_intelligence)
            company_invited_count = 0
            company_response_rate = None
            company_confidence_level = 'insufficient'
            if campaign_id and business_account_id:
                company_invited_count = db.session.query(func.count(CampaignParticipant.id)).join(
                    Participant, CampaignParticipant.participant_id == Participant.id
                ).filter(
                    CampaignParticipant.campaign_id == campaign_id,
                    func.upper(Participant.company_name) == company_key
                ).scalar() or 0
                if company_invited_count > 0:
                    company_response_rate = round((total_company_responses / company_invited_count) * 100, 1)
                    if company_invited_count < 5:
                        company_confidence_level = 'insufficient'
                    elif company_response_rate >= 60 and total_company_responses >= 10:
                        company_confidence_level = 'high'
                    elif (30 <= company_response_rate < 60) or (5 <= total_company_responses < 10):
                        company_confidence_level = 'medium'
                    else:
                        company_confidence_level = 'low'

            high_risk_accounts.append({
                'company_name': company_data['company_name'],
                'risk_level': max_risk_level,
                'risk_score': round(avg_risk_score, 2),
                'nps_score': company_nps,
                'respondent_count': company_data['respondent_count'],
                'latest_response': company_data['latest_response'],
                'invited_count': company_invited_count,
                'response_rate': company_response_rate,
                'confidence_level': company_confidence_level,
            })
        
        # Sort by highest risk first, then by lowest NPS
        high_risk_accounts.sort(key=lambda x: (
            0 if x['risk_level'] == 'Critical' else 1 if x['risk_level'] == 'High' else 2,
            x['nps_score']
        ))
        
        # Growth opportunities summary - grouped by company (case-insensitive) and normalized by type
        growth_opportunities_by_company = {}
        opportunities_query = SurveyResponse.query.filter(
            SurveyResponse.growth_opportunities.isnot(None)
        )
        if campaign_id:
            opportunities_query = opportunities_query.filter(SurveyResponse.campaign_id == campaign_id)
        responses_with_opportunities = opportunities_query.all()
        
        for response in responses_with_opportunities:
            if response.growth_opportunities:
                try:
                    opportunities = json.loads(response.growth_opportunities)
                    company_name = response.company_name
                    company_key = company_name.upper()  # Use uppercase for case-insensitive grouping
                    
                    if company_key not in growth_opportunities_by_company:
                        growth_opportunities_by_company[company_key] = {
                            'display_name': company_name,  # Keep the actual company name for display
                            'opportunities_by_type': {}  # Group by normalized type
                        }
                    else:
                        # Update display name to the most recent case version
                        growth_opportunities_by_company[company_key]['display_name'] = company_name
                    
                    for opp in opportunities:
                        # Skip if opportunity is not a dictionary (defensive coding)
                        if not isinstance(opp, dict):
                            continue
                        # Normalize the opportunity type to group similar ones
                        original_type = opp.get('type', 'unknown')
                        normalized_type = normalize_opportunity_type(original_type)
                        
                        # Group opportunities by normalized type
                        if normalized_type not in growth_opportunities_by_company[company_key]['opportunities_by_type']:
                            growth_opportunities_by_company[company_key]['opportunities_by_type'][normalized_type] = {
                                'type': normalized_type.replace('_', ' ').title(),  # Pretty format for display
                                'descriptions': [],
                                'actions': [],
                                'count': 0
                            }
                        
                        # Add to the grouped opportunity
                        type_group = growth_opportunities_by_company[company_key]['opportunities_by_type'][normalized_type]
                        description = opp.get('description', '')
                        action = opp.get('action', '')
                        
                        if description and description not in type_group['descriptions']:
                            type_group['descriptions'].append(description)
                        if action and action not in type_group['actions']:
                            type_group['actions'].append(action)
                        type_group['count'] += 1
                        
                except json.JSONDecodeError:
                    continue
        
        # Unified Account Intelligence - combine growth opportunities and risk factors by company
        unified_account_intelligence = {}
        
        # Collect all companies that have either opportunities or risk factors
        all_companies = set()
        all_companies.update(growth_opportunities_by_company.keys())
        
        # Process risk factors data
        risk_factors_query = SurveyResponse.query.filter(
            SurveyResponse.account_risk_factors.isnot(None)
        )
        if campaign_id:
            risk_factors_query = risk_factors_query.filter(SurveyResponse.campaign_id == campaign_id)
        responses_with_risk_factors = risk_factors_query.all()
        
        account_risk_factors_by_company = {}
        for response in responses_with_risk_factors:
            if response.account_risk_factors:
                try:
                    risk_factors = json.loads(response.account_risk_factors)
                    company_name = response.company_name
                    company_key = company_name.upper()
                    all_companies.add(company_key)
                    
                    if company_key not in account_risk_factors_by_company:
                        account_risk_factors_by_company[company_key] = {
                            'display_name': company_name,
                            'risk_factors_by_type': {}
                        }
                    else:
                        account_risk_factors_by_company[company_key]['display_name'] = company_name
                    
                    for risk in risk_factors:
                        if not isinstance(risk, dict):
                            continue
                        original_type = risk.get('type', 'unknown')
                        normalized_type = normalize_risk_factor_type(original_type)
                        
                        if normalized_type not in account_risk_factors_by_company[company_key]['risk_factors_by_type']:
                            account_risk_factors_by_company[company_key]['risk_factors_by_type'][normalized_type] = {
                                'type': normalized_type.replace('_', ' ').title(),
                                'descriptions': [],
                                'actions': [],
                                'severities': [],
                                'count': 0
                            }
                        
                        type_group = account_risk_factors_by_company[company_key]['risk_factors_by_type'][normalized_type]
                        description = risk.get('description', '')
                        action = risk.get('action', '')
                        severity = risk.get('severity', 'Medium')
                        
                        if description and description not in type_group['descriptions']:
                            type_group['descriptions'].append(description)
                        if action and action not in type_group['actions']:
                            type_group['actions'].append(action)
                        if severity and severity not in type_group['severities']:
                            type_group['severities'].append(severity)
                        type_group['count'] += 1
                        
                except json.JSONDecodeError:
                    continue
        
        # Create unified account intelligence structure
        account_intelligence = []
        for company_key in all_companies:
            company_name = None
            opportunities = []
            risk_factors = []
            max_tenure = None
            total_commercial_value = 0
            
            # Get opportunities data
            if company_key in growth_opportunities_by_company:
                company_data = growth_opportunities_by_company[company_key]
                company_name = company_data['display_name']
                if company_data['opportunities_by_type']:
                    for type_key, type_data in company_data['opportunities_by_type'].items():
                        opportunities.append({
                            'type': type_data['type'],
                            'description': '; '.join(type_data['descriptions']),
                            'action': '; '.join(type_data['actions']),
                            'count': type_data['count']
                        })
                    opportunities.sort(key=lambda x: (-x['count'], x['type']))
            
            # Get risk factors data
            if company_key in account_risk_factors_by_company:
                company_data = account_risk_factors_by_company[company_key]
                if not company_name:  # If not set from opportunities
                    company_name = company_data['display_name']
                if company_data['risk_factors_by_type']:
                    for type_key, type_data in company_data['risk_factors_by_type'].items():
                        severity_priority = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
                        highest_severity = max(type_data['severities'], 
                                             key=lambda s: severity_priority.get(s, 0)) if type_data['severities'] else 'Medium'
                        
                        risk_factors.append({
                            'type': type_data['type'],
                            'description': '; '.join(type_data['descriptions']),
                            'action': '; '.join(type_data['actions']),
                            'severity': highest_severity,
                            'count': type_data['count']
                        })
                    
                    severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
                    risk_factors.sort(key=lambda x: (severity_order.get(x['severity'], 2), -x['count']))
            
            # Get tenure, commercial value, and NPS data for this company (filtered by campaign)
            company_responses_query = SurveyResponse.query.filter(
                func.upper(SurveyResponse.company_name) == company_key
            )
            if campaign_id:
                company_responses_query = company_responses_query.filter(SurveyResponse.campaign_id == campaign_id)
            company_responses = company_responses_query.all()
            
            # Calculate max tenure and get commercial value (from participants)
            tenure_values = []
            for resp in company_responses:
                if resp.tenure_with_fc:
                    # Extract numeric value from tenure string (e.g., "2-3 years" -> 3)
                    try:
                        tenure_str = resp.tenure_with_fc.lower()
                        # Handle different formats: "2-3 years", "5+ years", "1 year", etc.
                        if '-' in tenure_str:
                            # Take the higher value from range
                            parts = tenure_str.split('-')
                            if len(parts) >= 2:
                                high_val = ''.join(filter(str.isdigit, parts[1]))
                                if high_val:
                                    tenure_values.append(int(high_val))
                        elif '+' in tenure_str:
                            # For "5+ years", take the base number
                            base_val = ''.join(filter(str.isdigit, tenure_str))
                            if base_val:
                                tenure_values.append(int(base_val))
                        else:
                            # For simple "3 years", extract the number
                            num_val = ''.join(filter(str.isdigit, tenure_str))
                            if num_val:
                                tenure_values.append(int(num_val))
                    except (ValueError, AttributeError):
                        pass
            
            max_tenure = max(tenure_values) if tenure_values else None
            
            # Get commercial_value from participant (company-level, manual input only)
            # All participants from same company should have the same value
            commercial_value = None
            
            # Get business_account_id from campaign or from a response
            target_business_account_id = None
            if campaign_id and campaign:
                target_business_account_id = campaign.business_account_id
            elif company_responses:
                # For non-campaign views, get business_account_id from any response's campaign
                for resp in company_responses:
                    if resp.campaign_id:
                        resp_campaign = Campaign.query.get(resp.campaign_id)
                        if resp_campaign:
                            target_business_account_id = resp_campaign.business_account_id
                            break
            
            if target_business_account_id:
                participant_sample = Participant.query.filter(
                    func.upper(Participant.company_name) == company_key,
                    Participant.business_account_id == target_business_account_id
                ).first()
                if participant_sample and participant_sample.company_commercial_value is not None:
                    commercial_value = participant_sample.company_commercial_value
            
            # Calculate company NPS from all responses (campaign-filtered)
            total_company_responses = len(company_responses)
            promoters = sum(1 for r in company_responses if r.nps_score >= 9)
            detractors = sum(1 for r in company_responses if r.nps_score <= 6)
            company_nps = round(((promoters - detractors) / total_company_responses) * 100) if total_company_responses > 0 else 0
            
            # Calculate per-company participation rate (invited vs responded)
            company_invited_count = 0
            company_response_rate = None
            company_confidence_level = 'insufficient'
            
            if campaign_id and target_business_account_id:
                # Count participants invited from this company for this campaign
                company_invited_count = db.session.query(func.count(CampaignParticipant.id)).join(
                    Participant, CampaignParticipant.participant_id == Participant.id
                ).filter(
                    CampaignParticipant.campaign_id == campaign_id,
                    func.upper(Participant.company_name) == company_key
                ).scalar() or 0
                
                if company_invited_count > 0:
                    company_response_rate = round((total_company_responses / company_invited_count) * 100, 1)
                    
                    # Calculate confidence level based on response rate AND sample size
                    # Requirements:
                    # - Insufficient: <5 invited (sample too small to be meaningful)
                    # - High: ≥60% response rate AND ≥10 responses (strong representation)
                    # - Medium: 30-59% response rate OR 5-9 responses (moderate representation)
                    # - Low: <30% response rate AND <5 responses (weak representation)
                    if company_invited_count < 5:
                        company_confidence_level = 'insufficient'
                    elif company_response_rate >= 60 and total_company_responses >= 10:
                        company_confidence_level = 'high'
                    elif (30 <= company_response_rate < 60) or (5 <= total_company_responses < 10):
                        company_confidence_level = 'medium'
                    else:
                        company_confidence_level = 'low'
            
            if opportunities or risk_factors:
                opportunity_count = len(opportunities)
                critical_risk_count = sum(1 for r in risk_factors if r['severity'] == 'Critical')
                risk_count = len(risk_factors)

                balance, opp_score, risk_score, health_ratio = calculate_weighted_account_balance(
                    opportunities, risk_factors
                )
                
                account_intelligence.append({
                    'company_name': company_name,
                    'opportunities': opportunities,
                    'risk_factors': risk_factors,
                    'balance': balance,
                    'opportunity_count': opportunity_count,
                    'risk_count': risk_count,
                    'critical_risks': critical_risk_count,
                    'max_tenure': max_tenure,
                    'commercial_value': commercial_value,
                    'company_nps': company_nps,
                    'invited_count': company_invited_count,
                    'responded_count': total_company_responses,
                    'response_rate': company_response_rate,
                    'confidence_level': company_confidence_level,
                    'opportunity_score': round(opp_score, 1),
                    'risk_score': round(risk_score, 1),
                    'health_ratio': round(health_ratio, 2)
                })
        
        # Sort accounts by priority (most critical risks first, then by balance)
        priority_order = {'risk_heavy': 0, 'balanced': 1, 'opportunity_heavy': 2}
        account_intelligence.sort(key=lambda x: (
            priority_order.get(x['balance'], 1),
            -x['critical_risks'],
            -x['risk_count'],
            -x['opportunity_count']
        ))
        
        # Keep separate structures for backward compatibility (in case other parts still need them)
        growth_opportunities = []
        for company_key, company_data in growth_opportunities_by_company.items():
            if company_data['opportunities_by_type']:
                consolidated_opportunities = []
                for type_key, type_data in company_data['opportunities_by_type'].items():
                    consolidated_opportunities.append({
                        'type': type_data['type'],
                        'description': '; '.join(type_data['descriptions']),
                        'action': '; '.join(type_data['actions']),
                        'count': type_data['count']
                    })
                consolidated_opportunities.sort(key=lambda x: (-x['count'], x['type']))
                growth_opportunities.append({
                    'company_name': company_data['display_name'],
                    'opportunities': consolidated_opportunities
                })
        
        account_risk_factors = []
        for company_key, company_data in account_risk_factors_by_company.items():
            if company_data['risk_factors_by_type']:
                consolidated_risk_factors = []
                for type_key, type_data in company_data['risk_factors_by_type'].items():
                    severity_priority = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
                    highest_severity = max(type_data['severities'], 
                                         key=lambda s: severity_priority.get(s, 0)) if type_data['severities'] else 'Medium'
                    consolidated_risk_factors.append({
                        'type': type_data['type'],
                        'description': '; '.join(type_data['descriptions']),
                        'action': '; '.join(type_data['actions']),
                        'severity': highest_severity,
                        'count': type_data['count']
                    })
                severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
                consolidated_risk_factors.sort(key=lambda x: (severity_order.get(x['severity'], 2), -x['count']))
                account_risk_factors.append({
                    'company_name': company_data['display_name'],
                    'risk_factors': consolidated_risk_factors
                })
        
        # Key themes aggregation
        all_themes = {}
        themes_query = SurveyResponse.query.filter(
            SurveyResponse.key_themes.isnot(None)
        )
        if campaign_id:
            themes_query = themes_query.filter(SurveyResponse.campaign_id == campaign_id)
        responses_with_themes = themes_query.all()
        
        for response in responses_with_themes:
            if response.key_themes:
                try:
                    themes = json.loads(response.key_themes)
                    for theme in themes:
                        # Skip if theme is not a dictionary (defensive coding)
                        if not isinstance(theme, dict):
                            continue
                        original_theme_name = theme.get('theme', 'unknown')
                        consolidated_theme_name = consolidate_theme_name(original_theme_name)
                        if consolidated_theme_name not in all_themes:
                            all_themes[consolidated_theme_name] = {'count': 0, 'sentiments': []}
                        all_themes[consolidated_theme_name]['count'] += 1
                        all_themes[consolidated_theme_name]['sentiments'].append(theme.get('sentiment', 'neutral'))
                except json.JSONDecodeError:
                    continue
        
        # Average ratings with campaign filtering
        satisfaction_query = db.session.query(func.avg(SurveyResponse.satisfaction_rating)).filter(
            SurveyResponse.satisfaction_rating.isnot(None)
        )
        if campaign_id:
            satisfaction_query = satisfaction_query.filter(SurveyResponse.campaign_id == campaign_id)
        avg_satisfaction = satisfaction_query.scalar() or 0
        
        product_value_query = db.session.query(func.avg(SurveyResponse.product_value_rating)).filter(
            SurveyResponse.product_value_rating.isnot(None)
        )
        if campaign_id:
            product_value_query = product_value_query.filter(SurveyResponse.campaign_id == campaign_id)
        avg_product_value = product_value_query.scalar() or 0
        
        service_query = db.session.query(func.avg(SurveyResponse.service_rating)).filter(
            SurveyResponse.service_rating.isnot(None)
        )
        if campaign_id:
            service_query = service_query.filter(SurveyResponse.campaign_id == campaign_id)
        avg_service = service_query.scalar() or 0
        
        pricing_query = db.session.query(func.avg(SurveyResponse.pricing_rating)).filter(
            SurveyResponse.pricing_rating.isnot(None)
        )
        if campaign_id:
            pricing_query = pricing_query.filter(SurveyResponse.campaign_id == campaign_id)
        avg_pricing = pricing_query.scalar() or 0
        
        support_query = db.session.query(func.avg(SurveyResponse.support_rating)).filter(
            SurveyResponse.support_rating.isnot(None)
        )
        if campaign_id:
            support_query = support_query.filter(SurveyResponse.campaign_id == campaign_id)
        avg_support = support_query.scalar() or 0
        
        # Tenure distribution with campaign filtering
        tenure_query = db.session.query(
            SurveyResponse.tenure_with_fc,
            func.count(SurveyResponse.id).label('count')
        ).filter(
            SurveyResponse.tenure_with_fc.isnot(None)
        )
        if campaign_id:
            tenure_query = tenure_query.filter(SurveyResponse.campaign_id == campaign_id)
        tenure_distribution = tenure_query.group_by(SurveyResponse.tenure_with_fc).all()
        
        # Growth factor analysis with campaign filtering
        growth_factor_query = db.session.query(
            SurveyResponse.growth_range,
            SurveyResponse.growth_rate,
            func.count(SurveyResponse.id).label('count'),
            func.avg(SurveyResponse.growth_factor).label('avg_factor')
        ).filter(
            SurveyResponse.growth_factor.isnot(None)
        )
        if campaign_id:
            growth_factor_query = growth_factor_query.filter(SurveyResponse.campaign_id == campaign_id)
        growth_factor_distribution = growth_factor_query.group_by(SurveyResponse.growth_range, SurveyResponse.growth_rate).all()
        
        # Overall growth potential (weighted average) with campaign filtering
        growth_potential_query = db.session.query(
            func.avg(SurveyResponse.growth_factor).label('avg_growth_factor')
        ).filter(
            SurveyResponse.growth_factor.isnot(None)
        )
        if campaign_id:
            growth_potential_query = growth_potential_query.filter(SurveyResponse.campaign_id == campaign_id)
        total_growth_potential = growth_potential_query.scalar() or 0
        
        # Company NPS Data (for Survey Insights tab and snapshots)
        company_nps_query = db.session.query(
            func.max(SurveyResponse.company_name).label('company_name'),
            func.count(SurveyResponse.id).label('total_responses'),
            func.avg(SurveyResponse.nps_score).label('avg_nps'),
            func.count(func.nullif(SurveyResponse.nps_score >= 9, False)).label('promoters'),
            func.count(func.nullif(SurveyResponse.nps_score <= 6, False)).label('detractors')
        ).filter(SurveyResponse.company_name.isnot(None))
        if campaign_id:
            company_nps_query = company_nps_query.filter(SurveyResponse.campaign_id == campaign_id)
        company_nps_query = company_nps_query.group_by(func.upper(SurveyResponse.company_name))
        
        company_nps_data = []
        for company in company_nps_query.all():
            total = company.total_responses
            promoters = company.promoters or 0
            detractors = company.detractors or 0
            company_nps = round(((promoters - detractors) / total) * 100) if total > 0 else 0
            
            company_nps_data.append({
                'company_name': company.company_name,
                'total_responses': total,
                'avg_nps': round(company.avg_nps, 1) if company.avg_nps else 0,
                'company_nps': company_nps,
                'promoters': promoters,
                'detractors': detractors,
                'passives': total - promoters - detractors
            })
        
        # Tenure NPS Data (for Survey Insights tab and snapshots)
        tenure_nps_query = db.session.query(
            SurveyResponse.tenure_with_fc,
            func.count(SurveyResponse.id).label('total_responses'),
            func.avg(SurveyResponse.nps_score).label('avg_nps'),
            func.count(func.nullif(SurveyResponse.nps_score >= 9, False)).label('promoters'),
            func.count(func.nullif(SurveyResponse.nps_score <= 6, False)).label('detractors')
        ).filter(SurveyResponse.tenure_with_fc.isnot(None))
        if campaign_id:
            tenure_nps_query = tenure_nps_query.filter(SurveyResponse.campaign_id == campaign_id)
        tenure_nps_query = tenure_nps_query.group_by(SurveyResponse.tenure_with_fc)
        
        tenure_nps_data = []
        for tenure in tenure_nps_query.all():
            total = tenure.total_responses
            promoters = tenure.promoters or 0
            detractors = tenure.detractors or 0
            tenure_nps = round(((promoters - detractors) / total) * 100) if total > 0 else 0
            
            tenure_nps_data.append({
                'tenure_group': tenure.tenure_with_fc,
                'total_responses': total,
                'avg_nps': round(tenure.avg_nps, 1) if tenure.avg_nps else 0,
                'tenure_nps': tenure_nps,
                'promoters': promoters,
                'detractors': detractors,
                'passives': total - promoters - detractors
            })
        
        return {
            'total_responses': total_responses,
            'total_companies': total_companies,
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
            'account_intelligence': account_intelligence,
            'growth_opportunities': growth_opportunities,
            'account_risk_factors': account_risk_factors,
            'key_themes': [
                {
                    'theme': theme.capitalize(),
                    'count': data['count'],
                    'sentiment_breakdown': {
                        'positive': data['sentiments'].count('positive'),
                        'negative': data['sentiments'].count('negative'),
                        'neutral': data['sentiments'].count('neutral'),
                    }
                }
                for theme, data in sorted(all_themes.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
            ],
            'average_ratings': {
                'satisfaction': float(round(avg_satisfaction, 1)),
                'product_value': float(round(avg_product_value, 1)),
                'service': float(round(avg_service, 1)),
                'pricing': float(round(avg_pricing, 1)),
                'support': float(round(avg_support, 1))
            },
            'tenure_distribution': [
                {'tenure': row.tenure_with_fc, 'count': row.count}
                for row in tenure_distribution
            ],
            'growth_factor_analysis': {
                'total_growth_potential': round(total_growth_potential, 2),
                'distribution': [
                    {
                        'nps_range': row.growth_range, 
                        'growth_rate': row.growth_rate,
                        'count': row.count,
                        'avg_factor': round(float(row.avg_factor), 2)
                    }
                    for row in growth_factor_distribution
                ]
            },
            'company_nps_data': company_nps_data,
            'tenure_nps_data': tenure_nps_data,
            'segmentation_analytics': calculate_segmentation_analytics(campaign_id, business_account_id) if campaign_id else {}
        }
        
    except Exception as e:
        raise Exception(f"Error compiling dashboard data: {e}")

def convert_snapshot_to_dashboard_format(snapshot):
    """Convert CampaignKPISnapshot data to the format expected by the dashboard"""
    try:
        # Parse JSON fields back to Python objects
        nps_distribution = json.loads(snapshot.nps_distribution) if snapshot.nps_distribution else []
        raw_sentiment_distribution = json.loads(snapshot.sentiment_distribution) if snapshot.sentiment_distribution else []
        
        # Convert sentiment distribution format from snapshot to chart format
        sentiment_distribution = []
        for item in raw_sentiment_distribution:
            if 'label' in item:  # Old snapshot format
                sentiment_distribution.append({
                    'sentiment': item['label'],
                    'count': item['count']
                })
            elif 'sentiment' in item:  # New format already
                sentiment_distribution.append(item)
            else:
                sentiment_distribution.append(item)  # Pass through unknown format
        tenure_distribution = json.loads(snapshot.tenure_distribution) if snapshot.tenure_distribution else []
        ratings_distribution = json.loads(snapshot.ratings_distribution) if snapshot.ratings_distribution else []
        key_themes = json.loads(snapshot.key_themes) if snapshot.key_themes else []
        growth_factor_distribution = json.loads(snapshot.growth_factor_distribution) if snapshot.growth_factor_distribution else []
        
        # Convert ratings distribution to expected format
        average_ratings = {
            'satisfaction': float(snapshot.avg_satisfaction_rating or 0),
            'pricing': float(snapshot.avg_pricing_rating or 0),
            'service': float(snapshot.avg_service_rating or 0),
            'product_value': float(snapshot.avg_product_value_rating or 0),
            'support': float(snapshot.avg_support_rating or 0)
        }
        
        # Return comprehensive dashboard data from snapshot
        
        # Enrich account_intelligence with company_nps if missing (for old snapshots)
        account_intelligence = json.loads(snapshot.account_intelligence) if snapshot.account_intelligence else []
        company_nps_data = json.loads(snapshot.company_nps_breakdown) if snapshot.company_nps_breakdown else []
        
        # Build NPS lookup for enrichment
        nps_lookup = {company['company_name'].upper(): company['company_nps'] 
                     for company in company_nps_data if 'company_name' in company and 'company_nps' in company}
        
        # Enrich accounts with correct company_nps (always overwrite to fix old snapshots with 0 values)
        for account in account_intelligence:
            company_key = account.get('company_name', '').upper()
            if company_key in nps_lookup:
                account['company_nps'] = nps_lookup[company_key]
            elif 'company_nps' not in account:
                account['company_nps'] = 0
        
        result = {
            'total_responses': snapshot.total_responses,
            'total_companies': snapshot.total_companies,
            'nps_score': snapshot.nps_score,
            'recent_responses': 0,  # For closed campaigns, this is always 0
            'nps_distribution': nps_distribution,
            'sentiment_distribution': sentiment_distribution,
            'high_risk_accounts': json.loads(snapshot.high_risk_accounts) if snapshot.high_risk_accounts else [],
            'account_intelligence': account_intelligence,
            'growth_opportunities': json.loads(snapshot.growth_opportunities_analysis) if snapshot.growth_opportunities_analysis else {},
            'account_risk_factors': json.loads(snapshot.account_risk_factors_analysis) if snapshot.account_risk_factors_analysis else {},
            'company_nps_data': company_nps_data,
            'tenure_nps_data': json.loads(snapshot.tenure_analysis) if snapshot.tenure_analysis else [],
            'key_themes': key_themes,
            'average_ratings': average_ratings,
            'tenure_distribution': tenure_distribution,
            'growth_factor_analysis': json.loads(snapshot.growth_factor_analysis_detailed) if snapshot.growth_factor_analysis_detailed else {
                'total_growth_potential': snapshot.total_growth_potential or 0,
                'distribution': growth_factor_distribution
            },
            'segmentation_analytics': json.loads(snapshot.segmentation_analytics) if snapshot.segmentation_analytics else {}
        }

        seg_data = result.get('segmentation_analytics', {})
        if 'churn_risk_by_segment' not in seg_data:
            try:
                snap_campaign_id = snapshot.campaign_id
                snap_business_account_id = snapshot.campaign.business_account_id if snapshot.campaign else None
                if snap_campaign_id and snap_business_account_id:
                    fresh_seg = calculate_segmentation_analytics(snap_campaign_id, snap_business_account_id)
                    if fresh_seg:
                        for key in ['churn_risk_by_segment', 'tenure_cohorts', 'sub_metrics_by_role', 'sub_metrics_by_region', 'sub_metrics_by_tier']:
                            if key in fresh_seg:
                                seg_data[key] = fresh_seg[key]
                        result['segmentation_analytics'] = seg_data
            except Exception as e:
                logger.warning(f"Fallback segmentation recalc failed for snapshot {snapshot.id}: {e}")

        snapshot_survey_type = getattr(snapshot, 'survey_type', None) or 'conversational'
        if snapshot_survey_type == 'classic':
            result['classic_analytics_snapshot'] = {
                'total_responses': snapshot.total_responses,
                'csat': {
                    'average': snapshot.avg_csat,
                    'distribution': json.loads(snapshot.csat_distribution) if snapshot.csat_distribution else {},
                    'count': sum(json.loads(snapshot.csat_distribution).values()) if snapshot.csat_distribution else 0
                },
                'ces': {
                    'average': snapshot.avg_ces,
                    'distribution': json.loads(snapshot.ces_distribution) if snapshot.ces_distribution else {},
                    'count': sum(json.loads(snapshot.ces_distribution).values()) if snapshot.ces_distribution else 0
                },
                'drivers': json.loads(snapshot.driver_attribution) if snapshot.driver_attribution else {},
                'features': json.loads(snapshot.feature_analytics) if snapshot.feature_analytics else {},
                'recommendation': json.loads(snapshot.recommendation_distribution) if snapshot.recommendation_distribution else {},
                'correlation': json.loads(snapshot.correlation_data) if getattr(snapshot, 'correlation_data', None) else {'points': [], 'summary': {'avg_ces_by_nps_category': {}, 'nps_csat_alignment_pct': None, 'total_correlated_responses': 0}}
            }
        
        return result
        
    except Exception as e:
        print(f"Error converting snapshot to dashboard format: {e}")
        # Fallback to minimal data structure if conversion fails
        return {
            'total_responses': snapshot.total_responses or 0,
            'nps_score': snapshot.nps_score or 0,
            'recent_responses': 0,
            'nps_distribution': [],
            'sentiment_distribution': [],
            'high_risk_accounts': [],
            'account_intelligence': [],
            'growth_opportunities': [],
            'account_risk_factors': [],
            'key_themes': [],
            'average_ratings': {'satisfaction': 0, 'product_value': 0, 'service': 0, 'pricing': 0},
            'tenure_distribution': [],
            'growth_factor_analysis': {'total_growth_potential': 0, 'distribution': []}
        }

def get_company_nps_data():
    """Get NPS data segregated by company - OPTIMIZED to fix N+1 query problem"""
    try:
        # Get all responses grouped by company (case-insensitive)
        company_stats = db.session.query(
            func.max(SurveyResponse.company_name).label('company_name'),  # Get the latest case version
            func.count(SurveyResponse.id).label('total_responses'),
            func.avg(SurveyResponse.nps_score).label('avg_nps'),
            func.max(SurveyResponse.created_at).label('latest_response'),
            func.count(func.nullif(SurveyResponse.nps_score >= 9, False)).label('promoters'),
            func.count(func.nullif(SurveyResponse.nps_score <= 6, False)).label('detractors')
        ).group_by(func.upper(SurveyResponse.company_name)).all()
        
        # OPTIMIZATION: Get all latest churn risks in ONE query instead of N+1 queries
        # Use subquery to find latest response per company
        from sqlalchemy import and_
        from sqlalchemy.sql import exists
        
        # Create a subquery that gets the latest response ID for each company
        latest_subquery = db.session.query(
            func.upper(SurveyResponse.company_name).label('upper_company'),
            func.max(SurveyResponse.created_at).label('max_created_at')
        ).group_by(func.upper(SurveyResponse.company_name)).subquery()
        
        # Join to get the actual latest responses with churn risk
        latest_responses = db.session.query(
            func.upper(SurveyResponse.company_name).label('upper_company'),
            SurveyResponse.churn_risk_level
        ).join(
            latest_subquery,
            and_(
                func.upper(SurveyResponse.company_name) == latest_subquery.c.upper_company,
                SurveyResponse.created_at == latest_subquery.c.max_created_at
            )
        ).all()
        
        # Create a dictionary for fast lookup: {upper_company_name: churn_risk}
        churn_risk_map = {resp.upper_company: resp.churn_risk_level for resp in latest_responses}
        
        company_nps_list = []
        
        for company in company_stats:
            # Calculate company NPS score
            total = company.total_responses
            promoters = company.promoters or 0
            detractors = company.detractors or 0
            
            if total > 0:
                company_nps = round(((promoters - detractors) / total) * 100)
            else:
                company_nps = 0
            
            # Determine risk level based on NPS and recent feedback
            if company_nps <= -50:
                risk_level = "Critical"
            elif company_nps <= -20:
                risk_level = "High"
            elif company_nps <= 20:
                risk_level = "Medium"
            else:
                risk_level = "Low"
            
            # OPTIMIZED: Get latest churn risk from pre-loaded map (no additional query)
            latest_churn_risk = churn_risk_map.get(company.company_name.upper() if company.company_name else None)
            
            company_nps_list.append({
                'company_name': company.company_name,
                'total_responses': total,
                'avg_nps': round(company.avg_nps, 1) if company.avg_nps else 0,
                'company_nps': company_nps,
                'promoters': promoters,
                'detractors': detractors,
                'passives': total - promoters - detractors,
                'risk_level': risk_level,
                'latest_response': company.latest_response.strftime('%Y-%m-%d') if company.latest_response else None,
                'latest_churn_risk': latest_churn_risk
            })
        
        # Sort by risk level and then by NPS score
        risk_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        company_nps_list.sort(key=lambda x: (risk_order.get(x['risk_level'], 4), -x['company_nps']))
        
        logger.info(f"📊 Company NPS data generated: {len(company_nps_list)} companies, optimized query (no N+1)")
        
        return company_nps_list
        
    except Exception as e:
        print(f"Error getting company NPS data: {e}")
        return []

def get_tenure_nps_data():
    """Get NPS data segregated by customer tenure"""
    try:
        # Get all responses grouped by tenure
        tenure_stats = db.session.query(
            SurveyResponse.tenure_with_fc,
            func.count(SurveyResponse.id).label('total_responses'),
            func.avg(SurveyResponse.nps_score).label('avg_nps'),
            func.max(SurveyResponse.created_at).label('latest_response'),
            func.count(func.nullif(SurveyResponse.nps_score >= 9, False)).label('promoters'),
            func.count(func.nullif(SurveyResponse.nps_score <= 6, False)).label('detractors')
        ).filter(
            SurveyResponse.tenure_with_fc.isnot(None)
        ).group_by(SurveyResponse.tenure_with_fc).all()
        
        tenure_nps_list = []
        
        for tenure in tenure_stats:
            # Calculate tenure NPS score
            total = tenure.total_responses
            promoters = tenure.promoters or 0
            detractors = tenure.detractors or 0
            
            if total > 0:
                tenure_nps = round(((promoters - detractors) / total) * 100)
            else:
                tenure_nps = 0
            
            # Determine risk level based on NPS and sample size
            if total < 2:
                risk_level = "Insufficient Data"
            elif tenure_nps <= -50:
                risk_level = "Critical"
            elif tenure_nps <= -20:
                risk_level = "High"
            elif tenure_nps <= 20:
                risk_level = "Medium"
            else:
                risk_level = "Low"
            
            # Get latest churn risk for this tenure group
            latest_response = SurveyResponse.query.filter(
                SurveyResponse.tenure_with_fc == tenure.tenure_with_fc
            ).order_by(SurveyResponse.created_at.desc()).first()
            
            latest_churn_risk = None
            if latest_response and latest_response.churn_risk_level:
                latest_churn_risk = latest_response.churn_risk_level
            
            tenure_nps_list.append({
                'tenure_group': tenure.tenure_with_fc,
                'total_responses': total,
                'avg_nps': round(tenure.avg_nps, 1) if tenure.avg_nps else 0,
                'tenure_nps': tenure_nps,
                'promoters': promoters,
                'detractors': detractors,
                'passives': total - promoters - detractors,
                'risk_level': risk_level,
                'latest_response': tenure.latest_response.strftime('%Y-%m-%d') if tenure.latest_response else None,
                'latest_churn_risk': latest_churn_risk
            })
        
        # Sort by tenure order (logical progression from new to long-term customers)
        tenure_order = {
            "Less than 1 year": 0,
            "1-2 years": 1, 
            "2-3 years": 2,
            "3-5 years": 3,
            "5-10 years": 4,
            "More than 10 years": 5
        }
        tenure_nps_list.sort(key=lambda x: tenure_order.get(x['tenure_group'], 6))
        
        return tenure_nps_list
        
    except Exception as e:
        print(f"Error getting tenure NPS data: {e}")
        return []

def get_company_trends():
    """Get NPS trends over time by company"""
    try:
        # Get monthly trends for each company (case-insensitive)
        monthly_data = db.session.query(
            func.max(SurveyResponse.company_name).label('company_name'),
            func.date_trunc('month', SurveyResponse.created_at).label('month'),
            func.avg(SurveyResponse.nps_score).label('avg_nps'),
            func.count(SurveyResponse.id).label('response_count')
        ).group_by(
            func.upper(SurveyResponse.company_name),
            func.date_trunc('month', SurveyResponse.created_at)
        ).order_by(
            func.upper(SurveyResponse.company_name),
            func.date_trunc('month', SurveyResponse.created_at)
        ).all()
        
        # Organize by company
        company_trends = {}
        for data in monthly_data:
            company = data.company_name
            if company not in company_trends:
                company_trends[company] = []
            
            company_trends[company].append({
                'month': data.month.strftime('%Y-%m') if data.month else None,
                'avg_nps': round(data.avg_nps, 1) if data.avg_nps else 0,
                'response_count': data.response_count
            })
        
        return company_trends
        
    except Exception as e:
        print(f"Error getting company trends: {e}")
        return {}


def calculate_segmentation_analytics(campaign_id, business_account_id=None):
    """
    Calculate NPS and satisfaction analytics segmented by participant attributes.
    Returns analytics grouped by role, region, customer_tier, and client_industry.
    
    Args:
        campaign_id: Campaign ID to filter responses
        business_account_id: Business account ID to enforce multi-tenant isolation
    """
    try:
        from models import Participant, CampaignParticipant, Campaign
        
        # Get business_account_id from Campaign if not provided
        if campaign_id and not business_account_id:
            campaign = Campaign.query.get(campaign_id)
            if campaign:
                business_account_id = campaign.business_account_id
        
        segmentation_query = db.session.query(
            SurveyResponse.nps_score,
            SurveyResponse.satisfaction_rating,
            SurveyResponse.churn_risk_level,
            SurveyResponse.tenure_with_fc,
            SurveyResponse.product_value_rating,
            SurveyResponse.service_rating,
            SurveyResponse.pricing_rating,
            SurveyResponse.support_rating,
            Participant.role,
            Participant.region,
            Participant.customer_tier,
            Participant.client_industry
        ).outerjoin(
            CampaignParticipant, 
            SurveyResponse.campaign_participant_id == CampaignParticipant.id
        ).outerjoin(
            Participant,
            CampaignParticipant.participant_id == Participant.id
        ).join(
            Campaign,
            SurveyResponse.campaign_id == Campaign.id
        ).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.nps_score.isnot(None)
        )
        
        # SECURITY: Filter by business account through Campaign to prevent cross-tenant data leakage
        if business_account_id:
            segmentation_query = segmentation_query.filter(
                Campaign.business_account_id == business_account_id
            )
        
        logger.info(f"🔍 SEGMENTATION DEBUG: Executing query for campaign_id={campaign_id}, business_account_id={business_account_id}")
        segmentation_results = segmentation_query.all()
        logger.info(f"🔍 SEGMENTATION DEBUG: Query returned {len(segmentation_results)} rows")
        
        if len(segmentation_results) > 0:
            logger.info(f"✅ SEGMENTATION DEBUG: Sample data - Role: {segmentation_results[0].role}, Tier: {segmentation_results[0].customer_tier}")
        
        if not segmentation_results:
            logger.warning(f"⚠️ SEGMENTATION DEBUG: No data found for campaign_id={campaign_id}, business_account_id={business_account_id}")
            return {}
        
        role_segments = {}
        region_segments = {}
        tier_segments = {}
        industry_segments = {}

        churn_by_tier = {}
        churn_by_role = {}
        churn_by_region = {}

        tenure_cohorts = {}

        def _empty_seg():
            return {'nps_scores': [], 'satisfaction_scores': [], 'product': [], 'service': [], 'pricing': [], 'support': []}

        def _tenure_band(tenure_str):
            if not tenure_str:
                return None
            try:
                import re
                nums = re.findall(r'\d+', str(tenure_str))
                if not nums:
                    return None
                years = int(nums[0])
            except (ValueError, TypeError):
                return None
            if years <= 2:
                return '1-2 years'
            elif years <= 5:
                return '3-5 years'
            elif years <= 8:
                return '6-8 years'
            else:
                return '9+ years'

        for response in segmentation_results:
            nps_score = response.nps_score
            satisfaction = response.satisfaction_rating
            role = response.role or 'Unspecified'
            region = response.region or 'Unspecified'
            tier = response.customer_tier or 'Unspecified'
            industry = response.client_industry or 'Unspecified'
            churn_level = response.churn_risk_level
            tenure_str = response.tenure_with_fc

            for dim_key, dim_val, segments in [
                ('role', role, role_segments),
                ('region', region, region_segments),
                ('tier', tier, tier_segments),
                ('industry', industry, industry_segments),
            ]:
                if dim_val not in segments:
                    segments[dim_val] = _empty_seg()
                seg = segments[dim_val]
                seg['nps_scores'].append(nps_score)
                if satisfaction:
                    seg['satisfaction_scores'].append(satisfaction)
                if response.product_value_rating is not None:
                    seg['product'].append(response.product_value_rating)
                if response.service_rating is not None:
                    seg['service'].append(response.service_rating)
                if response.pricing_rating is not None:
                    seg['pricing'].append(response.pricing_rating)
                if response.support_rating is not None:
                    seg['support'].append(response.support_rating)

            if churn_level:
                for dim_store, dim_val in [(churn_by_tier, tier), (churn_by_role, role), (churn_by_region, region)]:
                    if dim_val not in dim_store:
                        dim_store[dim_val] = {'Minimal': 0, 'Low': 0, 'Medium': 0, 'High': 0}
                    effective_level = churn_level if churn_level in ('Minimal', 'Low', 'Medium', 'High') else 'High'
                    dim_store[dim_val][effective_level] += 1

            band = _tenure_band(tenure_str)
            if band:
                if band not in tenure_cohorts:
                    tenure_cohorts[band] = {'nps_scores': [], 'satisfaction_scores': []}
                tenure_cohorts[band]['nps_scores'].append(nps_score)
                if satisfaction:
                    tenure_cohorts[band]['satisfaction_scores'].append(satisfaction)
        
        # Helper function to calculate NPS metrics
        def calculate_nps_metrics(nps_scores):
            if not nps_scores:
                return {}
            total = len(nps_scores)
            promoters = sum(1 for score in nps_scores if score >= 9)
            passives = sum(1 for score in nps_scores if 7 <= score <= 8)
            detractors = sum(1 for score in nps_scores if score <= 6)
            nps = round(((promoters - detractors) / total) * 100) if total > 0 else 0
            avg_nps = round(sum(nps_scores) / total, 1) if total > 0 else 0
            
            return {
                'nps_score': nps,
                'avg_nps': avg_nps,
                'total_responses': total,
                'promoters': promoters,
                'passives': passives,
                'detractors': detractors
            }
        
        def calculate_satisfaction_metrics(satisfaction_scores):
            if not satisfaction_scores:
                return None
            return round(sum(satisfaction_scores) / len(satisfaction_scores), 2)

        def _avg_or_none(scores):
            return round(sum(scores) / len(scores), 2) if scores else None

        def _sub_metrics(seg_data):
            return {
                'product': _avg_or_none(seg_data.get('product', [])),
                'service': _avg_or_none(seg_data.get('service', [])),
                'pricing': _avg_or_none(seg_data.get('pricing', [])),
                'support': _avg_or_none(seg_data.get('support', [])),
            }

        analytics = {
            'nps_by_role': {},
            'nps_by_region': {},
            'nps_by_tier': {},
            'nps_by_industry': {},
            'satisfaction_by_role': {},
            'satisfaction_by_region': {},
            'satisfaction_by_tier': {},
            'satisfaction_by_industry': {},
            'response_distribution': {
                'by_role': {},
                'by_region': {},
                'by_tier': {},
                'by_industry': {}
            },
            'churn_risk_by_segment': {
                'by_tier': churn_by_tier,
                'by_role': churn_by_role,
                'by_region': churn_by_region,
            },
            'sub_metrics_by_role': {},
            'sub_metrics_by_region': {},
            'sub_metrics_by_tier': {},
            'tenure_cohorts': {},
        }

        for role, data in role_segments.items():
            analytics['nps_by_role'][role] = calculate_nps_metrics(data['nps_scores'])
            analytics['satisfaction_by_role'][role] = calculate_satisfaction_metrics(data['satisfaction_scores'])
            analytics['response_distribution']['by_role'][role] = len(data['nps_scores'])
            analytics['sub_metrics_by_role'][role] = _sub_metrics(data)

        for region, data in region_segments.items():
            analytics['nps_by_region'][region] = calculate_nps_metrics(data['nps_scores'])
            analytics['satisfaction_by_region'][region] = calculate_satisfaction_metrics(data['satisfaction_scores'])
            analytics['response_distribution']['by_region'][region] = len(data['nps_scores'])
            analytics['sub_metrics_by_region'][region] = _sub_metrics(data)

        for tier, data in tier_segments.items():
            analytics['nps_by_tier'][tier] = calculate_nps_metrics(data['nps_scores'])
            analytics['satisfaction_by_tier'][tier] = calculate_satisfaction_metrics(data['satisfaction_scores'])
            analytics['response_distribution']['by_tier'][tier] = len(data['nps_scores'])
            analytics['sub_metrics_by_tier'][tier] = _sub_metrics(data)

        for industry, data in industry_segments.items():
            analytics['nps_by_industry'][industry] = calculate_nps_metrics(data['nps_scores'])
            analytics['satisfaction_by_industry'][industry] = calculate_satisfaction_metrics(data['satisfaction_scores'])
            analytics['response_distribution']['by_industry'][industry] = len(data['nps_scores'])

        tenure_order = ['1-2 years', '3-5 years', '6-8 years', '9+ years']
        for band in tenure_order:
            if band in tenure_cohorts:
                tc = tenure_cohorts[band]
                analytics['tenure_cohorts'][band] = {
                    'nps_score': calculate_nps_metrics(tc['nps_scores']).get('nps_score', 0),
                    'avg_satisfaction': calculate_satisfaction_metrics(tc['satisfaction_scores']),
                    'total_responses': len(tc['nps_scores']),
                }

        return analytics
        
    except Exception as e:
        print(f"Error calculating segmentation analytics for campaign {campaign_id}: {e}")
        import traceback
        traceback.print_exc()
        return {}


def generate_campaign_kpi_snapshot(campaign_id):
    """Generate and store immutable KPI snapshot for a closed campaign"""
    try:
        # Get campaign details
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign with ID {campaign_id} not found")
        
        # Check if snapshot already exists
        existing_snapshot = CampaignKPISnapshot.query.filter_by(campaign_id=campaign_id).first()
        if existing_snapshot:
            print(f"KPI snapshot already exists for campaign {campaign_id}")
            return existing_snapshot
        
        print(f"Generating KPI snapshot for campaign: {campaign.name} (ID: {campaign_id})")
        
        # Build base query for this campaign
        base_query = SurveyResponse.query.filter(SurveyResponse.campaign_id == campaign_id)
        
        # Basic statistics
        total_responses = base_query.count()
        if total_responses == 0:
            print(f"No survey responses found for campaign {campaign_id}")
            return None
        
        # Count unique companies
        total_companies = db.session.query(
            func.count(func.distinct(SurveyResponse.company_name))
        ).filter(SurveyResponse.campaign_id == campaign_id).scalar() or 0
        
        # ============================================================================
        # NPS METRICS CALCULATION
        # ============================================================================
        
        # NPS distribution
        nps_distribution_raw = db.session.query(
            SurveyResponse.nps_category,
            func.count(SurveyResponse.id).label('count')
        ).filter(
            SurveyResponse.campaign_id == campaign_id
        ).group_by(SurveyResponse.nps_category).all()
        
        # Convert to JSON format
        nps_distribution = [
            {"category": row.nps_category, "count": row.count}
            for row in nps_distribution_raw
        ]
        
        # Calculate NPS counts
        promoters = db.session.query(func.count(SurveyResponse.id)).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.nps_score >= 9
        ).scalar() or 0
        
        passives = db.session.query(func.count(SurveyResponse.id)).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.nps_score >= 7,
            SurveyResponse.nps_score <= 8
        ).scalar() or 0
        
        detractors = db.session.query(func.count(SurveyResponse.id)).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.nps_score <= 6
        ).scalar() or 0
        
        # Calculate final NPS score
        nps_score = ((promoters - detractors) / total_responses * 100) if total_responses > 0 else 0
        
        # ============================================================================
        # RATINGS CALCULATION
        # ============================================================================
        
        avg_satisfaction = db.session.query(func.avg(SurveyResponse.satisfaction_rating)).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.satisfaction_rating.isnot(None)
        ).scalar() or 0
        
        avg_pricing = db.session.query(func.avg(SurveyResponse.pricing_rating)).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.pricing_rating.isnot(None)
        ).scalar() or 0
        
        avg_service = db.session.query(func.avg(SurveyResponse.service_rating)).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.service_rating.isnot(None)
        ).scalar() or 0
        
        avg_product_value = db.session.query(func.avg(SurveyResponse.product_value_rating)).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.product_value_rating.isnot(None)
        ).scalar() or 0
        
        avg_support = db.session.query(func.avg(SurveyResponse.support_rating)).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.support_rating.isnot(None)
        ).scalar() or 0
        
        # Ratings distribution for charts
        ratings_distribution = [
            {"category": "Satisfaction", "rating": round(float(avg_satisfaction), 2) if avg_satisfaction else 0},
            {"category": "Pricing", "rating": round(float(avg_pricing), 2) if avg_pricing else 0},
            {"category": "Service", "rating": round(float(avg_service), 2) if avg_service else 0},
            {"category": "Product Value", "rating": round(float(avg_product_value), 2) if avg_product_value else 0},
            {"category": "Support", "rating": round(float(avg_support), 2) if avg_support else 0}
        ]
        
        # ============================================================================
        # SENTIMENT ANALYSIS
        # ============================================================================
        
        sentiment_distribution_raw = db.session.query(
            SurveyResponse.sentiment_label,
            func.count(SurveyResponse.id).label('count')
        ).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.sentiment_label.isnot(None)
        ).group_by(SurveyResponse.sentiment_label).all()
        
        # Convert to JSON and calculate percentages
        sentiment_distribution = []
        sentiment_positive_pct = 0
        sentiment_negative_pct = 0
        sentiment_neutral_pct = 0
        
        sentiment_total = sum(row.count for row in sentiment_distribution_raw)
        if sentiment_total > 0:
            for row in sentiment_distribution_raw:
                pct = (row.count / sentiment_total) * 100
                sentiment_distribution.append({
                    "label": row.sentiment_label,
                    "count": row.count,
                    "percentage": round(pct, 1)
                })
                
                if row.sentiment_label and 'positive' in row.sentiment_label.lower():
                    sentiment_positive_pct = round(pct, 1)
                elif row.sentiment_label and 'negative' in row.sentiment_label.lower():
                    sentiment_negative_pct = round(pct, 1)
                elif row.sentiment_label and 'neutral' in row.sentiment_label.lower():
                    sentiment_neutral_pct = round(pct, 1)
        
        # ============================================================================
        # RISK ASSESSMENT
        # ============================================================================
        
        # High risk accounts count
        high_risk_accounts_count = db.session.query(func.count(SurveyResponse.id)).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.churn_risk_level.in_(['High', 'Critical'])
        ).scalar() or 0
        
        # Churn risk distribution
        churn_risk_distribution_raw = db.session.query(
            SurveyResponse.churn_risk_level,
            func.count(SurveyResponse.id).label('count')
        ).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.churn_risk_level.isnot(None)
        ).group_by(SurveyResponse.churn_risk_level).all()
        
        # Calculate churn risk percentages
        churn_total = sum(row.count for row in churn_risk_distribution_raw)
        churn_risk_high_pct = 0
        churn_risk_medium_pct = 0
        churn_risk_low_pct = 0
        churn_risk_minimal_pct = 0
        
        if churn_total > 0:
            for row in churn_risk_distribution_raw:
                pct = (row.count / churn_total) * 100
                if row.churn_risk_level == 'High':
                    churn_risk_high_pct = round(pct, 1)
                elif row.churn_risk_level == 'Medium':
                    churn_risk_medium_pct = round(pct, 1)
                elif row.churn_risk_level == 'Low':
                    churn_risk_low_pct = round(pct, 1)
                elif row.churn_risk_level == 'Minimal':
                    churn_risk_minimal_pct = round(pct, 1)
        
        # High risk accounts details
        high_risk_responses = SurveyResponse.query.filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.churn_risk_level.in_(['High', 'Critical'])
        ).all()
        
        high_risk_accounts = []
        for response in high_risk_responses:
            if response.company_name:
                high_risk_accounts.append({
                    "company": response.company_name,
                    "risk_level": response.churn_risk_level,
                    "nps_score": response.nps_score,
                    "churn_risk_score": response.churn_risk_score
                })
        
        # ============================================================================
        # GROWTH METRICS
        # ============================================================================
        
        avg_growth_factor = db.session.query(func.avg(SurveyResponse.growth_factor)).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.growth_factor.isnot(None)
        ).scalar() or 0
        
        total_growth_potential = avg_growth_factor  # Same as average for snapshot
        
        # Growth factor distribution
        growth_factor_distribution_raw = db.session.query(
            SurveyResponse.growth_range,
            SurveyResponse.growth_rate,
            func.count(SurveyResponse.id).label('count')
        ).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.growth_factor.isnot(None)
        ).group_by(SurveyResponse.growth_range, SurveyResponse.growth_rate).all()
        
        growth_factor_distribution = [
            {
                "nps_range": row.growth_range or "Unknown",
                "growth_rate": row.growth_rate or "0%",
                "count": row.count
            }
            for row in growth_factor_distribution_raw
        ]
        
        # ============================================================================
        # TENURE DISTRIBUTION
        # ============================================================================
        
        tenure_distribution_raw = db.session.query(
            SurveyResponse.tenure_with_fc,
            func.count(SurveyResponse.id).label('count')
        ).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.tenure_with_fc.isnot(None)
        ).group_by(SurveyResponse.tenure_with_fc).all()
        
        tenure_distribution = [
            {"tenure": row.tenure_with_fc, "count": row.count}
            for row in tenure_distribution_raw
        ]
        
        # ============================================================================
        # KEY THEMES
        # ============================================================================
        
        # Extract key themes from all text responses
        all_themes = {}
        responses_with_themes = SurveyResponse.query.filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.key_themes.isnot(None)
        ).all()
        
        print(f"   📝 Processing {len(responses_with_themes)} responses for key themes extraction...")
        
        for response in responses_with_themes:
            if response.key_themes and response.key_themes.strip() and response.key_themes != '[]':
                try:
                    themes = json.loads(response.key_themes)
                    if not themes:  # Skip empty arrays
                        continue
                    for theme in themes:
                        # Extract theme name from theme object (handle both dict and string formats)
                        if isinstance(theme, dict):
                            theme_name = theme.get('theme', 'unknown')
                        else:
                            theme_name = str(theme)
                        
                        consolidated_theme = consolidate_theme_name(theme_name)
                        all_themes[consolidated_theme] = all_themes.get(consolidated_theme, 0) + 1
                except json.JSONDecodeError as e:
                    print(f"   ⚠️ JSON decode error for response {response.id}: {e}")
                    continue
                except Exception as e:
                    print(f"   ⚠️ Error processing themes for response {response.id}: {type(e).__name__}: {e}")
                    continue
        
        # Sort themes by frequency
        sorted_themes = sorted(all_themes.items(), key=lambda x: x[1], reverse=True)
        key_themes = [
            {"theme": theme, "count": count}  # Changed from "frequency" to "count" to match live data format
            for theme, count in sorted_themes[:10]  # Top 10 themes
        ]
        
        print(f"   ✅ Extracted {len(key_themes)} key themes from {len(all_themes)} unique themes")
        
        # ============================================================================
        # COMPANY AGGREGATIONS
        # ============================================================================
        
        # Calculate average company NPS
        company_nps_data = db.session.query(
            SurveyResponse.company_name,
            func.avg(SurveyResponse.nps_score).label('avg_nps')
        ).filter(
            SurveyResponse.campaign_id == campaign_id,
            SurveyResponse.company_name.isnot(None)
        ).group_by(SurveyResponse.company_name).all()
        
        avg_company_nps = sum(float(row.avg_nps) for row in company_nps_data) / len(company_nps_data) if company_nps_data else 0
        
        # ============================================================================
        # CAPTURE COMPREHENSIVE ANALYSIS DATA FOR FULL DASHBOARD RESTORATION
        # ============================================================================
        
        # Generate complete dashboard data to extract all components
        print("📊 Capturing comprehensive analysis data for snapshot...")
        full_dashboard_data = get_dashboard_data(campaign_id=campaign_id)
        
        # Custom JSON serializer to handle datetime and Decimal objects
        def serialize_for_json(obj):
            from decimal import Decimal
            if isinstance(obj, list):
                return [serialize_for_json(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: serialize_for_json(value) for key, value in obj.items()}
            elif isinstance(obj, Decimal):
                return float(obj)
            elif hasattr(obj, 'isoformat'):  # datetime objects
                return obj.isoformat()
            else:
                return obj
        
        # Account Intelligence - Complete analysis by company
        account_intelligence = serialize_for_json(full_dashboard_data.get('account_intelligence', []))
        print(f"   ✅ Account Intelligence: {len(account_intelligence)} companies")
        
        # Growth Opportunities Analysis by company
        growth_opportunities_analysis = serialize_for_json(full_dashboard_data.get('growth_opportunities', {}))
        print(f"   ✅ Growth Opportunities: {len(growth_opportunities_analysis)} companies")
        
        # Account Risk Factors Analysis by company  
        account_risk_factors_analysis = serialize_for_json(full_dashboard_data.get('account_risk_factors', {}))
        print(f"   ✅ Risk Factors: {len(account_risk_factors_analysis)} companies")
        
        # Company NPS Breakdown for Survey Insights tab
        company_nps_breakdown = []
        company_nps_data_detailed = full_dashboard_data.get('company_nps_data', [])
        if company_nps_data_detailed:
            company_nps_breakdown = serialize_for_json(company_nps_data_detailed)
        print(f"   ✅ Company NPS Breakdown: {len(company_nps_breakdown)} companies")
        
        # Tenure Analysis for Survey Insights tab
        tenure_analysis = []
        tenure_nps_data = full_dashboard_data.get('tenure_nps_data', [])
        if tenure_nps_data:
            tenure_analysis = serialize_for_json(tenure_nps_data)
        print(f"   ✅ Tenure Analysis: {len(tenure_analysis)} groups")
        
        # Growth Factor Analysis Detailed
        growth_factor_analysis_detailed = serialize_for_json(full_dashboard_data.get('growth_factor_analysis', {}))
        print(f"   ✅ Growth Factor Analysis: {len(growth_factor_analysis_detailed)} metrics")
        
        # High Risk Accounts (enhanced with details)
        high_risk_accounts = serialize_for_json(full_dashboard_data.get('high_risk_accounts', []))
        print(f"   ✅ High Risk Accounts: {len(high_risk_accounts)} companies")
        
        # Segmentation Analytics
        segmentation_analytics = calculate_segmentation_analytics(campaign_id)
        segmentation_analytics = serialize_for_json(segmentation_analytics)
        segment_count = sum(len(segmentation_analytics.get(key, {})) for key in ['nps_by_role', 'nps_by_region', 'nps_by_tier', 'nps_by_industry'])
        print(f"   ✅ Segmentation Analytics: {segment_count} segments")
        
        # ============================================================================
        # CLASSIC SURVEY-SPECIFIC METRICS (only for classic campaigns)
        # ============================================================================
        
        campaign_survey_type = getattr(campaign, 'survey_type', 'conversational') or 'conversational'
        classic_snapshot_data = {}
        
        if campaign_survey_type == 'classic':
            print("📋 Capturing classic survey-specific metrics...")
            
            responses_list = base_query.all()
            
            csat_scores = [r.csat_score for r in responses_list if r.csat_score is not None]
            csat_dist = {}
            for s in csat_scores:
                csat_dist[str(s)] = csat_dist.get(str(s), 0) + 1
            csat_avg = round(sum(csat_scores) / len(csat_scores), 2) if csat_scores else None
            
            ces_scores = [r.ces_score for r in responses_list if r.ces_score is not None]
            ces_dist = {}
            for s in ces_scores:
                ces_dist[str(s)] = ces_dist.get(str(s), 0) + 1
            ces_avg = round(sum(ces_scores) / len(ces_scores), 2) if ces_scores else None
            
            driver_data = {}
            for r in responses_list:
                if r.loyalty_drivers:
                    drivers_list = r.loyalty_drivers if isinstance(r.loyalty_drivers, list) else []
                    nps_cat = getattr(r, 'nps_category', None) or 'Unknown'
                    for d in drivers_list:
                        if d not in driver_data:
                            driver_data[d] = {'count': 0, 'promoters': 0, 'passives': 0, 'detractors': 0}
                        driver_data[d]['count'] += 1
                        if nps_cat == 'Promoter':
                            driver_data[d]['promoters'] += 1
                        elif nps_cat == 'Passive':
                            driver_data[d]['passives'] += 1
                        elif nps_cat == 'Detractor':
                            driver_data[d]['detractors'] += 1
            
            classic_config = ClassicSurveyConfig.query.filter_by(campaign_id=campaign_id).first()
            driver_label_map = {}
            if classic_config and classic_config.driver_labels:
                for dl in classic_config.driver_labels:
                    driver_label_map[dl['key']] = {
                        'label_en': dl.get('label_en', dl['key']),
                        'label_fr': dl.get('label_fr', dl['key'])
                    }
            
            drivers_with_labels = {}
            for key, dd in driver_data.items():
                labels = driver_label_map.get(key, {'label_en': key, 'label_fr': key})
                drivers_with_labels[key] = {
                    'count': dd['count'],
                    'percentage': round(dd['count'] / total_responses * 100, 1) if total_responses > 0 else 0,
                    'promoters': dd['promoters'],
                    'passives': dd['passives'],
                    'detractors': dd['detractors'],
                    'net_impact': dd['promoters'] - dd['detractors'],
                    'label_en': labels['label_en'],
                    'label_fr': labels['label_fr']
                }
            
            correlation_points = []
            for r in responses_list:
                if r.csat_score is not None and r.ces_score is not None and r.nps_score is not None:
                    nps_cat = getattr(r, 'nps_category', None) or 'Unknown'
                    correlation_points.append({
                        'csat': r.csat_score,
                        'ces': r.ces_score,
                        'nps_score': r.nps_score,
                        'nps_category': nps_cat
                    })
            
            avg_ces_by_nps = {}
            for cat in ['Promoter', 'Passive', 'Detractor']:
                cat_ces = [p['ces'] for p in correlation_points if p['nps_category'] == cat]
                avg_ces_by_nps[cat] = round(sum(cat_ces) / len(cat_ces), 2) if cat_ces else None
            
            high_nps = sum(1 for p in correlation_points if p['nps_score'] >= 9 and p['csat'] >= 4)
            total_high_nps = sum(1 for p in correlation_points if p['nps_score'] >= 9)
            nps_csat_alignment = round(high_nps / total_high_nps * 100, 1) if total_high_nps > 0 else None
            
            correlation_result = {
                'points': correlation_points,
                'summary': {
                    'avg_ces_by_nps_category': avg_ces_by_nps,
                    'nps_csat_alignment_pct': nps_csat_alignment,
                    'total_correlated_responses': len(correlation_points)
                }
            }
            
            feature_data = {}
            feature_label_map = {}
            if classic_config and classic_config.features:
                for f in classic_config.features:
                    feature_label_map[f['key']] = {
                        'name_en': f.get('name_en', f['key']),
                        'name_fr': f.get('name_fr', f['key'])
                    }
            
            for r in responses_list:
                if r.general_feedback:
                    try:
                        evals = json.loads(r.general_feedback) if isinstance(r.general_feedback, str) else r.general_feedback
                        if isinstance(evals, dict):
                            for fkey, fdata in evals.items():
                                if fkey not in feature_data:
                                    f_labels = feature_label_map.get(fkey, {'name_en': fkey, 'name_fr': fkey})
                                    feature_data[fkey] = {
                                        'name_en': f_labels['name_en'],
                                        'name_fr': f_labels['name_fr'],
                                        'usage_yes': 0,
                                        'usage_no': 0,
                                        'satisfaction_scores': []
                                    }
                                fd = feature_data[fkey]
                                usage = fdata.get('usage', '') if isinstance(fdata, dict) else ''
                                if usage == 'yes':
                                    fd['usage_yes'] += 1
                                elif usage and str(usage).startswith('no'):
                                    fd['usage_no'] += 1
                                if isinstance(fdata, dict) and fdata.get('satisfaction') is not None:
                                    fd['satisfaction_scores'].append(fdata['satisfaction'])
                    except (json.JSONDecodeError, AttributeError):
                        pass
            
            features_summary = {}
            for fkey, fd in feature_data.items():
                avg_sat = round(sum(fd['satisfaction_scores']) / len(fd['satisfaction_scores']), 2) if fd['satisfaction_scores'] else None
                total_usage = fd['usage_yes'] + fd['usage_no']
                adoption = round(fd['usage_yes'] / total_usage * 100, 1) if total_usage > 0 else 0
                features_summary[fkey] = {
                    'name_en': fd['name_en'],
                    'name_fr': fd['name_fr'],
                    'adoption_rate': adoption,
                    'usage_yes': fd['usage_yes'],
                    'usage_no': fd['usage_no'],
                    'avg_satisfaction': avg_sat
                }
            
            rec_counts = {}
            for r in responses_list:
                if r.recommendation_status:
                    rec_counts[r.recommendation_status] = rec_counts.get(r.recommendation_status, 0) + 1
            
            classic_snapshot_data = {
                'avg_csat': csat_avg,
                'avg_ces': ces_avg,
                'csat_distribution': json.dumps(csat_dist),
                'ces_distribution': json.dumps(ces_dist),
                'driver_attribution': json.dumps(drivers_with_labels),
                'feature_analytics': json.dumps(features_summary),
                'recommendation_distribution': json.dumps(rec_counts),
                'correlation_data': json.dumps(correlation_result),
            }
            
            print(f"   ✅ CSAT: avg={csat_avg}, {len(csat_scores)} scores")
            print(f"   ✅ CES: avg={ces_avg}, {len(ces_scores)} scores")
            print(f"   ✅ Drivers: {len(drivers_with_labels)} unique")
            print(f"   ✅ Features: {len(features_summary)} evaluated")
            print(f"   ✅ Recommendations: {len(rec_counts)} statuses")
            print(f"   ✅ Correlation: {len(correlation_points)} data points")
        
        # ============================================================================
        # CREATE SNAPSHOT RECORD
        # ============================================================================
        
        snapshot = CampaignKPISnapshot(
            campaign_id=campaign_id,
            survey_type=campaign_survey_type,
            total_responses=total_responses,
            total_companies=total_companies,
            nps_score=round(nps_score, 1),
            promoters_count=promoters,
            passives_count=passives,
            detractors_count=detractors,
            avg_satisfaction_rating=round(float(avg_satisfaction), 2) if avg_satisfaction else None,
            avg_pricing_rating=round(float(avg_pricing), 2) if avg_pricing else None,
            avg_service_rating=round(float(avg_service), 2) if avg_service else None,
            avg_product_value_rating=round(float(avg_product_value), 2) if avg_product_value else None,
            avg_support_rating=round(float(avg_support), 2) if avg_support else None,
            sentiment_positive_pct=sentiment_positive_pct,
            sentiment_negative_pct=sentiment_negative_pct,
            sentiment_neutral_pct=sentiment_neutral_pct,
            high_risk_accounts_count=high_risk_accounts_count,
            churn_risk_high_pct=churn_risk_high_pct,
            churn_risk_medium_pct=churn_risk_medium_pct,
            churn_risk_low_pct=churn_risk_low_pct,
            churn_risk_minimal_pct=churn_risk_minimal_pct,
            avg_growth_factor=round(float(avg_growth_factor), 2) if avg_growth_factor else 0,
            total_growth_potential=round(float(total_growth_potential), 2) if total_growth_potential else 0,
            avg_company_nps=round(float(avg_company_nps), 1) if avg_company_nps else 0,
            nps_distribution=json.dumps(nps_distribution),
            sentiment_distribution=json.dumps(sentiment_distribution),
            tenure_distribution=json.dumps(tenure_distribution),
            ratings_distribution=json.dumps(ratings_distribution),
            growth_factor_distribution=json.dumps(growth_factor_distribution),
            key_themes=json.dumps(key_themes),
            high_risk_accounts=json.dumps(high_risk_accounts),
            account_intelligence=json.dumps(account_intelligence),
            growth_opportunities_analysis=json.dumps(growth_opportunities_analysis),
            account_risk_factors_analysis=json.dumps(account_risk_factors_analysis),
            company_nps_breakdown=json.dumps(company_nps_breakdown),
            tenure_analysis=json.dumps(tenure_analysis),
            growth_factor_analysis_detailed=json.dumps(growth_factor_analysis_detailed),
            segmentation_analytics=json.dumps(segmentation_analytics),
            avg_csat=classic_snapshot_data.get('avg_csat'),
            avg_ces=classic_snapshot_data.get('avg_ces'),
            csat_distribution=classic_snapshot_data.get('csat_distribution'),
            ces_distribution=classic_snapshot_data.get('ces_distribution'),
            driver_attribution=classic_snapshot_data.get('driver_attribution'),
            feature_analytics=classic_snapshot_data.get('feature_analytics'),
            recommendation_distribution=classic_snapshot_data.get('recommendation_distribution'),
            correlation_data=classic_snapshot_data.get('correlation_data'),
            data_period_start=campaign.start_date,
            data_period_end=campaign.end_date
        )
        
        db.session.add(snapshot)
        db.session.commit()
        
        print(f"✅ KPI snapshot created for campaign '{campaign.name}' with {total_responses} responses")
        print(f"   NPS Score: {round(nps_score, 1)}")
        print(f"   Companies: {total_companies}")
        print(f"   High Risk Accounts: {high_risk_accounts_count}")
        
        return snapshot
        
    except Exception as e:
        print(f"Error generating KPI snapshot for campaign {campaign_id}: {str(e)}")
        db.session.rollback()
        raise e


def get_company_detail_data(campaign_id, company_name, business_account_id=None):
    """Aggregate per-company qualitative signals for a single company within a campaign.
    
    Returns dict with: top_themes, sub_metrics, avg_churn_risk_score, analysis_summary,
    nps_summary (company_nps, promoters, passives, detractors, total_responses, risk_level).
    Returns None if no responses found.

    Caching: Uses tenant-scoped cache keys when business_account_id is provided.
    Completed campaigns use 2-hour TTL; active campaigns use 30-minute TTL.
    """
    import time
    start_time = time.time()

    cache_key = f"company_detail_campaign{campaign_id}_company{company_name.upper()}_tenant{business_account_id}"
    use_cache = cache_config.is_enabled() and business_account_id is not None

    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            cache_config.record_hit()
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"✅ COMPANY DETAIL CACHE HIT | Campaign: {campaign_id} | Company: {company_name} | Tenant: {business_account_id} | Time: {elapsed:.0f}ms")
            return cached
        cache_config.record_miss()
        logger.info(f"🔍 COMPANY DETAIL CACHE MISS | Campaign: {campaign_id} | Company: {company_name} | Tenant: {business_account_id}")

    from models import SurveyResponse
    from sqlalchemy import func, case
    import json as json_module

    responses = SurveyResponse.query.filter(
        func.upper(SurveyResponse.company_name) == company_name.upper(),
        SurveyResponse.campaign_id == campaign_id
    ).all()

    if not responses:
        return None

    total = len(responses)
    nps_responses = [r for r in responses if r.nps_score is not None]
    nps_total = len(nps_responses)
    promoters = sum(1 for r in nps_responses if r.nps_score >= 9)
    detractors = sum(1 for r in nps_responses if r.nps_score <= 6)
    passives = nps_total - promoters - detractors

    company_nps = round(((promoters - detractors) / nps_total) * 100) if nps_total > 0 else 0
    if company_nps <= -50:
        risk_level = "Critical"
    elif company_nps <= -20:
        risk_level = "High"
    elif company_nps <= 20:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    theme_counts = {}
    for r in responses:
        if r.key_themes:
            try:
                themes = json_module.loads(r.key_themes) if isinstance(r.key_themes, str) else r.key_themes
                if isinstance(themes, list):
                    for theme in themes:
                        if isinstance(theme, dict):
                            t = (theme.get('theme') or theme.get('name') or '').strip().lower()
                        elif isinstance(theme, str):
                            t = theme.strip().lower()
                        else:
                            t = str(theme).strip().lower()
                        if t:
                            theme_counts[t] = theme_counts.get(t, 0) + 1
                elif isinstance(themes, dict):
                    for key in themes:
                        k = key.strip().lower()
                        if k:
                            theme_counts[k] = theme_counts.get(k, 0) + 1
            except (json_module.JSONDecodeError, TypeError):
                pass

    top_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_themes = [{"theme": t, "count": c} for t, c in top_themes]

    metric_fields = {
        "satisfaction": "satisfaction_rating",
        "service": "service_rating",
        "pricing": "pricing_rating",
        "product_value": "product_value_rating"
    }
    sub_metrics = {}
    for label, field in metric_fields.items():
        values = [getattr(r, field) for r in responses if getattr(r, field) is not None]
        if values:
            sub_metrics[label] = round(sum(values) / len(values), 2)

    weakest_metric = None
    if sub_metrics:
        weakest_metric = min(sub_metrics, key=sub_metrics.get)

    churn_scores = [r.churn_risk_score for r in responses if r.churn_risk_score is not None]
    avg_churn_risk_score = round(sum(churn_scores) / len(churn_scores), 3) if churn_scores else None

    latest_response = max(responses, key=lambda r: r.created_at or datetime.min)
    analysis_summary = latest_response.analysis_summary if latest_response else None

    avg_nps = round(sum(r.nps_score for r in nps_responses) / nps_total, 1) if nps_total > 0 else 0

    latest_churn_risk = latest_response.churn_risk_level if latest_response else None
    latest_response_date = latest_response.created_at.strftime('%Y-%m-%d') if latest_response and latest_response.created_at else None

    result = {
        "nps_summary": {
            "company_nps": company_nps,
            "avg_nps": avg_nps,
            "promoters": promoters,
            "passives": passives,
            "detractors": detractors,
            "total_responses": nps_total,
            "risk_level": risk_level,
            "latest_churn_risk": latest_churn_risk,
            "latest_response": latest_response_date
        },
        "top_themes": top_themes,
        "sub_metrics": sub_metrics,
        "weakest_metric": weakest_metric,
        "avg_churn_risk_score": avg_churn_risk_score,
        "analysis_summary": analysis_summary
    }

    if use_cache and result is not None:
        try:
            campaign_obj = Campaign.query.get(campaign_id)
            campaign_status = campaign_obj.status if campaign_obj else None
            ttl = cache_config.get_timeout() if campaign_status == 'completed' else 1800
            cache.set(cache_key, result, timeout=ttl)
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"💾 COMPANY DETAIL CACHE SET | Campaign: {campaign_id} | Company: {company_name} | Status: {campaign_status} | TTL: {ttl}s | Time: {elapsed:.0f}ms")
        except Exception as cache_err:
            logger.warning(f"⚠️ Failed to cache company detail: {cache_err}")

    return result


def bust_company_detail_cache(campaign_id, company_name, business_account_id):
    """Invalidate the company detail cache for a specific company/campaign/tenant."""
    cache_key = f"company_detail_campaign{campaign_id}_company{company_name.upper()}_tenant{business_account_id}"
    try:
        cache.delete(cache_key)
        logger.info(f"🗑️ COMPANY DETAIL CACHE BUSTED | Campaign: {campaign_id} | Company: {company_name} | Tenant: {business_account_id}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to bust company detail cache: {e}")
