import json
import re
from datetime import datetime, timedelta
from sqlalchemy import func, case
from app import db
from models import SurveyResponse, Campaign, CampaignKPISnapshot
from flask import request

def consolidate_theme_name(theme_name):
    """Consolidate similar theme names to reduce duplication"""
    if not theme_name:
        return 'unknown'
    
    # Convert to lowercase and strip whitespace
    normalized = theme_name.lower().strip()
    
    # Remove common adjectives and determiners
    normalized = re.sub(r'\b(customer|client|user|our|the|good|bad|great|poor)\s+', '', normalized)
    
    # Define mapping for similar themes
    theme_mappings = {
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
    
    # Find the canonical theme for this name
    for canonical_theme, variations in theme_mappings.items():
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

def get_dashboard_data(campaign_id=None):
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
            
            # Calculate averages for scores
            avg_risk_score = sum(company_data['risk_scores']) / len(company_data['risk_scores']) if company_data['risk_scores'] else 0
            avg_nps_score = sum(company_data['nps_scores']) / len(company_data['nps_scores']) if company_data['nps_scores'] else 0
            
            high_risk_accounts.append({
                'company_name': company_data['company_name'],
                'risk_level': max_risk_level,
                'risk_score': round(avg_risk_score, 2),
                'nps_score': round(avg_nps_score, 1),
                'respondent_count': company_data['respondent_count'],
                'latest_response': company_data['latest_response']
            })
        
        # Sort by highest risk first, then by lowest NPS
        high_risk_accounts.sort(key=lambda x: (
            0 if x['risk_level'] == 'Critical' else 1 if x['risk_level'] == 'High' else 2,
            x['nps_score']
        ))
        
        # Growth opportunities summary - grouped by company (case-insensitive) and normalized by type
        growth_opportunities_by_company = {}
        responses_with_opportunities = SurveyResponse.query.filter(
            SurveyResponse.growth_opportunities.isnot(None)
        ).all()
        
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
        responses_with_risk_factors = SurveyResponse.query.filter(
            SurveyResponse.account_risk_factors.isnot(None)
        ).all()
        
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
            
            # Get tenure and commercial value data for this company
            company_responses = SurveyResponse.query.filter(
                func.upper(SurveyResponse.company_name) == company_key
            ).all()
            
            # Calculate max tenure and total commercial value
            tenure_values = []
            commercial_values = []
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
                
                if resp.commercial_value:
                    commercial_values.append(resp.commercial_value)
            
            max_tenure = max(tenure_values) if tenure_values else None
            total_commercial_value = sum(commercial_values) if commercial_values else 0
            
            # Only include companies with either opportunities or risk factors
            if opportunities or risk_factors:
                # Calculate account balance
                opportunity_count = len(opportunities)
                critical_risk_count = sum(1 for r in risk_factors if r['severity'] == 'Critical')
                high_risk_count = sum(1 for r in risk_factors if r['severity'] == 'High')
                total_risk_score = critical_risk_count * 3 + high_risk_count * 2 + sum(1 for r in risk_factors if r['severity'] in ['Medium', 'Low'])
                
                # Check for critical business risks that prevent "High Potential" classification
                critical_business_risks = sum(1 for r in risk_factors if any(
                    risk_type in r.get('type', '').lower() 
                    for risk_type in ['churn', 'pricing', 'product_problems', 'service_issues']
                ))
                
                # Determine balance with stricter criteria for High Potential
                if critical_risk_count > 0 or total_risk_score > opportunity_count * 2:
                    balance = 'risk_heavy'
                elif critical_business_risks > 0:
                    # Accounts with churn risk, pricing issues, product problems, or service issues cannot be High Potential
                    balance = 'balanced' if opportunity_count > total_risk_score else 'risk_heavy'
                elif opportunity_count > 1 and total_risk_score == 0:
                    # Only accounts with multiple opportunities and NO risk factors can be High Potential
                    balance = 'opportunity_heavy'
                elif opportunity_count > 0 and total_risk_score == 0:
                    # Single opportunity with no risks = Balanced
                    balance = 'balanced'
                else:
                    balance = 'balanced'
                
                account_intelligence.append({
                    'company_name': company_name,
                    'opportunities': opportunities,
                    'risk_factors': risk_factors,
                    'balance': balance,
                    'opportunity_count': opportunity_count,
                    'risk_count': len(risk_factors),
                    'critical_risks': critical_risk_count,
                    'max_tenure': max_tenure,
                    'commercial_value': total_commercial_value
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
        responses_with_themes = SurveyResponse.query.filter(
            SurveyResponse.key_themes.isnot(None)
        ).all()
        
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
            'account_intelligence': account_intelligence,
            'growth_opportunities': growth_opportunities,
            'account_risk_factors': account_risk_factors,
            'key_themes': [
                {'theme': theme.capitalize(), 'count': data['count']}
                for theme, data in sorted(all_themes.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
            ],
            'average_ratings': {
                'satisfaction': round(avg_satisfaction, 1),
                'product_value': round(avg_product_value, 1),
                'service': round(avg_service, 1),
                'pricing': round(avg_pricing, 1)
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
            }
        }
        
    except Exception as e:
        raise Exception(f"Error compiling dashboard data: {e}")

def convert_snapshot_to_dashboard_format(snapshot):
    """Convert CampaignKPISnapshot data to the format expected by the dashboard"""
    try:
        # Parse JSON fields back to Python objects
        nps_distribution = json.loads(snapshot.nps_distribution) if snapshot.nps_distribution else []
        sentiment_distribution = json.loads(snapshot.sentiment_distribution) if snapshot.sentiment_distribution else []
        tenure_distribution = json.loads(snapshot.tenure_distribution) if snapshot.tenure_distribution else []
        ratings_distribution = json.loads(snapshot.ratings_distribution) if snapshot.ratings_distribution else []
        key_themes = json.loads(snapshot.key_themes) if snapshot.key_themes else []
        growth_factor_distribution = json.loads(snapshot.growth_factor_distribution) if snapshot.growth_factor_distribution else []
        
        # Convert ratings distribution to expected format
        average_ratings = {
            'satisfaction': snapshot.avg_satisfaction_rating or 0,
            'pricing': snapshot.avg_pricing_rating or 0,
            'service': snapshot.avg_service_rating or 0,
            'product_value': snapshot.avg_product_value_rating or 0
        }
        
        # For closed campaigns, we don't have dynamic account intelligence data in snapshots
        # These would need to be calculated separately if needed for historical campaigns
        # For now, return empty arrays to maintain compatibility
        
        return {
            'total_responses': snapshot.total_responses,
            'nps_score': snapshot.nps_score,
            'recent_responses': 0,  # For closed campaigns, this is always 0
            'nps_distribution': nps_distribution,
            'sentiment_distribution': sentiment_distribution,
            'high_risk_accounts': [],  # Would need to be stored separately for historical data
            'account_intelligence': [],  # Dynamic data not stored in snapshots
            'growth_opportunities': [],  # Dynamic data not stored in snapshots  
            'account_risk_factors': [],  # Dynamic data not stored in snapshots
            'key_themes': key_themes,
            'average_ratings': average_ratings,
            'tenure_distribution': tenure_distribution,
            'growth_factor_analysis': {
                'total_growth_potential': snapshot.total_growth_potential or 0,
                'distribution': growth_factor_distribution
            }
        }
        
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
    """Get NPS data segregated by company"""
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
            
            # Get latest churn risk for this company (case-insensitive)
            latest_response = SurveyResponse.query.filter(
                func.upper(SurveyResponse.company_name) == func.upper(company.company_name)
            ).order_by(SurveyResponse.created_at.desc()).first()
            
            latest_churn_risk = None
            if latest_response and latest_response.churn_risk_level:
                latest_churn_risk = latest_response.churn_risk_level
            
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
        
        # Ratings distribution for charts
        ratings_distribution = [
            {"category": "Satisfaction", "rating": round(float(avg_satisfaction), 2) if avg_satisfaction else 0},
            {"category": "Pricing", "rating": round(float(avg_pricing), 2) if avg_pricing else 0},
            {"category": "Service", "rating": round(float(avg_service), 2) if avg_service else 0},
            {"category": "Product Value", "rating": round(float(avg_product_value), 2) if avg_product_value else 0}
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
        
        for response in responses_with_themes:
            if response.key_themes:
                try:
                    themes = json.loads(response.key_themes)
                    for theme in themes:
                        consolidated_theme = consolidate_theme_name(theme)
                        all_themes[consolidated_theme] = all_themes.get(consolidated_theme, 0) + 1
                except:
                    continue
        
        # Sort themes by frequency
        sorted_themes = sorted(all_themes.items(), key=lambda x: x[1], reverse=True)
        key_themes = [
            {"theme": theme, "frequency": frequency}
            for theme, frequency in sorted_themes[:10]  # Top 10 themes
        ]
        
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
        # CREATE SNAPSHOT RECORD
        # ============================================================================
        
        snapshot = CampaignKPISnapshot(
            campaign_id=campaign_id,
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
