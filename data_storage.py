import json
import re
from datetime import datetime, timedelta
from sqlalchemy import func, case
from app import db
from models import SurveyResponse
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
        
        # High risk accounts - grouped by company (case-insensitive)
        high_risk_by_company = {}
        high_risk_responses = SurveyResponse.query.filter(
            SurveyResponse.churn_risk_level.in_(['High', 'Critical'])  # Include Critical risk too
        ).all()
        
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
            
            # Only include companies with either opportunities or risk factors
            if opportunities or risk_factors:
                # Calculate account balance
                opportunity_count = len(opportunities)
                critical_risk_count = sum(1 for r in risk_factors if r['severity'] == 'Critical')
                high_risk_count = sum(1 for r in risk_factors if r['severity'] == 'High')
                total_risk_score = critical_risk_count * 3 + high_risk_count * 2 + sum(1 for r in risk_factors if r['severity'] in ['Medium', 'Low'])
                
                # Determine balance
                if critical_risk_count > 0 or total_risk_score > opportunity_count * 2:
                    balance = 'risk_heavy'
                elif opportunity_count > 0 and total_risk_score <= opportunity_count:
                    balance = 'opportunity_heavy'
                else:
                    balance = 'balanced'
                
                account_intelligence.append({
                    'company_name': company_name,
                    'opportunities': opportunities,
                    'risk_factors': risk_factors,
                    'balance': balance,
                    'opportunity_count': opportunity_count,
                    'risk_count': len(risk_factors),
                    'critical_risks': critical_risk_count
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
        
        # Tenure distribution
        tenure_distribution = db.session.query(
            SurveyResponse.tenure_with_fc,
            func.count(SurveyResponse.id).label('count')
        ).filter(
            SurveyResponse.tenure_with_fc.isnot(None)
        ).group_by(SurveyResponse.tenure_with_fc).all()
        
        # Growth factor analysis
        growth_factor_distribution = db.session.query(
            SurveyResponse.growth_range,
            SurveyResponse.growth_rate,
            func.count(SurveyResponse.id).label('count'),
            func.avg(SurveyResponse.growth_factor).label('avg_factor')
        ).filter(
            SurveyResponse.growth_factor.isnot(None)
        ).group_by(SurveyResponse.growth_range, SurveyResponse.growth_rate).all()
        
        # Overall growth potential (weighted average)
        total_growth_potential = db.session.query(
            func.avg(SurveyResponse.growth_factor).label('avg_growth_factor')
        ).filter(
            SurveyResponse.growth_factor.isnot(None)
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
