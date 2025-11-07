import json
import os
import csv
from datetime import datetime
from openai import OpenAI
from textblob import TextBlob
from app import db
from models import SurveyResponse
import logging

logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

def analyze_survey_response(response_id):
    """Perform comprehensive AI analysis on a survey response with consolidated OpenAI call"""
    try:
        response = SurveyResponse.query.get(response_id)
        if not response:
            raise ValueError(f"Survey response {response_id} not found")
        
        # Collect all text for analysis
        text_content = []
        if response.improvement_feedback:
            text_content.append(response.improvement_feedback)
        if response.recommendation_reason:
            text_content.append(response.recommendation_reason)
        if response.additional_comments:
            text_content.append(response.additional_comments)
        
        combined_text = " ".join(text_content)
        
        # Perform consolidated AI analysis (single OpenAI call instead of 5)
        if combined_text.strip() and openai_client:
            analysis_results = perform_consolidated_ai_analysis(response, combined_text)
        else:
            # Fallback for empty text or no OpenAI client
            analysis_results = perform_fallback_analysis(response, combined_text)
        
        # Calculate growth factor based on NPS (no OpenAI call needed)
        growth_factor_data = calculate_growth_factor(response.nps_score)
        
        # Update the response with analysis results
        response.sentiment_score = analysis_results['sentiment']['score']
        response.sentiment_label = analysis_results['sentiment']['label']
        response.key_themes = json.dumps(analysis_results['themes'])
        response.churn_risk_score = analysis_results['churn']['risk_score']
        response.churn_risk_level = analysis_results['churn']['risk_level']
        response.churn_risk_factors = json.dumps(analysis_results['churn']['risk_factors'])
        response.growth_opportunities = json.dumps(analysis_results['growth_opportunities'])
        response.account_risk_factors = json.dumps(analysis_results['account_risk_factors'])
        response.growth_factor = growth_factor_data['growth_factor']
        response.growth_rate = growth_factor_data['growth_rate']
        response.growth_range = growth_factor_data['range']
        response.analysis_summary = analysis_results.get('summary')
        response.analysis_reasoning = analysis_results.get('reasoning')
        response.analyzed_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Analysis completed for response {response_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error analyzing response {response_id}: {e}")
        return False

def perform_consolidated_ai_analysis(response, combined_text):
    """Perform all AI analysis in a single OpenAI call for maximum efficiency"""
    try:
        # Build comprehensive context about the response
        response_context = {
            'nps_score': response.nps_score,
            'satisfaction_rating': response.satisfaction_rating,
            'service_rating': response.service_rating,
            'product_value_rating': response.product_value_rating,
            'pricing_rating': response.pricing_rating,
            'company_name': response.company_name,
            'tenure': response.tenure_with_fc
        }
        
        # Create consolidated prompt that handles all analysis types
        consolidated_prompt = f"""You are a comprehensive customer feedback analysis expert. Analyze this customer feedback and provide a complete analysis covering all aspects below.

CUSTOMER FEEDBACK: "{combined_text}"

CONTEXT:
- NPS Score: {response.nps_score}/10
- Company: {response.company_name}
- Tenure: {response.tenure_with_fc}
- Satisfaction Rating: {response.satisfaction_rating}/5
- Service Rating: {response.service_rating}/5  
- Product Value Rating: {response.product_value_rating}/5
- Pricing Rating: {response.pricing_rating}/5

ANALYSIS REQUIREMENTS:
Provide a comprehensive JSON response with the following analysis:

1. SENTIMENT ANALYSIS:
   - score: float from -1.0 (very negative) to 1.0 (very positive)
   - label: "positive", "negative", or "neutral"

2. KEY THEMES:
   - Array of themes found in feedback
   - Each theme should have: theme name, sentiment
   - Focus on product, service, pricing, support, quality, features

3. CHURN RISK ASSESSMENT:
   - risk_level: "Minimal", "Low", "Medium", or "High"  
   - risk_score: integer 0-10
   - risk_factors: array of specific risk indicators found

4. GROWTH OPPORTUNITIES:
   - Array of genuine growth opportunities (upsell, cross-sell, expansion)
   - Only include positive signals from satisfied customers
   - Each opportunity: type, description, action
   - DO NOT include problems/issues as opportunities

5. ACCOUNT RISK FACTORS:
   - Array of account-specific risks (pricing concerns, service issues, etc.)
   - Each factor: type, description, severity, action
   - Focus on business relationship threats

6. EXECUTIVE SUMMARY & REASONING (for transparency and trust):
   - summary: 2-3 sentence plain-language overview of key findings
   - reasoning: 3-4 sentence explanation of WHY the AI reached these specific conclusions
   - Connect the dots: feedback → sentiment → themes → risk assessment
   - Write for non-technical business users in clear, everyday language
   - Focus on building trust by explaining the analysis logic

Return ONLY valid JSON in this exact format:
{{
  "sentiment": {{"score": 0.0, "label": "neutral"}},
  "themes": [{{"theme": "string", "sentiment": "positive/negative/neutral"}}],
  "churn": {{
    "risk_level": "Minimal/Low/Medium/High",
    "risk_score": 0,
    "risk_factors": ["array of strings"]
  }},
  "growth_opportunities": [{{
    "type": "string",
    "description": "string", 
    "action": "string"
  }}],
  "account_risk_factors": [{{
    "type": "string",
    "description": "string",
    "severity": "Low/Medium/High/Critical",
    "action": "string"
  }}],
  "summary": "2-3 sentence plain-language summary",
  "reasoning": "3-4 sentence explanation of analysis logic"
}}"""

        # Single OpenAI API call for all analysis
        # Model selection via environment variable for cost optimization
        analysis_model = os.environ.get('AI_ANALYSIS_MODEL', 'gpt-4o-mini')
        
        ai_response = openai_client.chat.completions.create(
            model=analysis_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a comprehensive customer feedback analysis expert. Analyze feedback and provide structured analysis covering sentiment, themes, churn risk, growth opportunities, and account risk factors. Always return valid JSON."
                },
                {
                    "role": "user", 
                    "content": consolidated_prompt
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=1500,
            temperature=0.3
        )
        
        # Parse the consolidated response
        result = json.loads(ai_response.choices[0].message.content)
        
        # Add rule-based enhancements to AI analysis
        result = enhance_analysis_with_rules(result, response, combined_text)
        
        return result
        
    except Exception as e:
        logger.warning(f"Consolidated AI analysis failed: {e}")
        # Fallback to rule-based analysis
        return perform_fallback_analysis(response, combined_text)

def enhance_analysis_with_rules(ai_result, response, text):
    """Enhance AI analysis with rule-based logic for consistency"""
    # Enhance churn risk with NPS-based rules
    if response.nps_score <= 3 and ai_result['churn']['risk_score'] < 5:
        ai_result['churn']['risk_score'] = max(5, ai_result['churn']['risk_score'])
        ai_result['churn']['risk_level'] = 'High'
        ai_result['churn']['risk_factors'].append('Critical NPS score')
    elif response.nps_score <= 6 and ai_result['churn']['risk_score'] < 3:
        ai_result['churn']['risk_score'] = max(3, ai_result['churn']['risk_score'])
        if ai_result['churn']['risk_level'] == 'Minimal':
            ai_result['churn']['risk_level'] = 'Medium'
    
    # Add growth opportunities for high NPS
    if response.nps_score >= 9:
        advocacy_opportunity = {
            'type': 'advocacy',
            'description': 'High NPS score - potential brand advocate',
            'action': 'Engage for case studies, referrals, or testimonials'
        }
        # Check if similar opportunity already exists
        existing_types = [opp.get('type', '') for opp in ai_result.get('growth_opportunities', [])]
        if 'advocacy' not in existing_types:
            ai_result['growth_opportunities'].append(advocacy_opportunity)
    
    # Add account risk factors for low ratings
    low_ratings = []
    if response.satisfaction_rating and response.satisfaction_rating <= 2:
        low_ratings.append("satisfaction")
    if response.service_rating and response.service_rating <= 2:
        low_ratings.append("service")
    if response.product_value_rating and response.product_value_rating <= 2:
        low_ratings.append("product value")
    if response.pricing_rating and response.pricing_rating <= 2:
        low_ratings.append("pricing")
        
    if low_ratings:
        rating_risk = {
            'type': 'poor_ratings',
            'description': f'Poor ratings in: {", ".join(low_ratings)}',
            'severity': 'High',
            'action': 'Address specific pain points in affected areas'
        }
        ai_result['account_risk_factors'].append(rating_risk)
    
    return ai_result

def perform_fallback_analysis(response, combined_text):
    """Fallback analysis when OpenAI is not available"""
    # Use existing rule-based functions as fallback
    sentiment_data = analyze_business_sentiment(combined_text)
    themes = extract_themes_fallback(combined_text)
    churn_analysis = assess_churn_risk_fallback(response, combined_text)
    growth_opportunities = identify_growth_opportunities_fallback(response)
    account_risk_factors = identify_account_risk_factors_fallback(response, combined_text)
    
    return {
        'sentiment': sentiment_data,
        'themes': themes,
        'churn': churn_analysis,
        'growth_opportunities': growth_opportunities,
        'account_risk_factors': account_risk_factors
    }

def extract_themes_fallback(text):
    """Fallback theme extraction using keywords"""
    keywords = ['product', 'service', 'price', 'pricing', 'support', 'feature', 'quality', 'value', 'team']
    themes = []
    text_lower = text.lower()
    
    for keyword in keywords:
        if keyword in text_lower:
            themes.append({'theme': keyword, 'sentiment': 'neutral'})
    
    return themes

def assess_churn_risk_fallback(response, text):
    """Fallback churn risk assessment"""
    risk_factors = []
    risk_points = 0
    text_lower = text.lower()
    
    # Check for churn indicators
    churn_keywords = ['churn', 'leave', 'switch', 'competitor', 'cancel', 'terminate']
    if any(keyword in text_lower for keyword in churn_keywords):
        risk_points += 5
        risk_factors.append("Explicit churn indicators detected")
    
    # NPS-based risk
    if response.nps_score <= 6:
        risk_points += 3
        risk_factors.append("Low NPS score indicating dissatisfaction")
    
    # Convert to risk level
    if risk_points >= 5:
        risk_level = "High"
    elif risk_points >= 3:
        risk_level = "Medium"
    elif risk_points >= 1:
        risk_level = "Low"
    else:
        risk_level = "Minimal"
    
    return {
        'risk_level': risk_level,
        'risk_score': risk_points,
        'risk_factors': risk_factors
    }

def identify_growth_opportunities_fallback(response):
    """Fallback growth opportunity identification"""
    opportunities = []
    
    if response.nps_score >= 9:
        opportunities.append({
            'type': 'advocacy',
            'description': 'High NPS score - potential brand advocate',
            'action': 'Engage for case studies, referrals, or testimonials'
        })
    
    return opportunities

def identify_account_risk_factors_fallback(response, text):
    """Fallback account risk factor identification"""
    risk_factors = []
    
    if response.nps_score <= 3:
        risk_factors.append({
            'type': 'critical_satisfaction',
            'description': 'Critical NPS score - immediate attention required',
            'severity': 'Critical',
            'action': 'Schedule urgent customer success call within 24 hours'
        })
    
    return risk_factors

def analyze_sentiment(text):
    """Analyze sentiment using both OpenAI and TextBlob"""
    if not text.strip():
        return {'score': 0.0, 'label': 'neutral'}
    
    try:
        # Use OpenAI for advanced sentiment analysis
        if openai_client:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sentiment analysis expert. Analyze the sentiment of customer feedback and provide a score from -1 (very negative) to 1 (very positive) and a label (positive, negative, or neutral). Respond with JSON."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze the sentiment of this customer feedback: {text}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return {
                'score': max(-1, min(1, float(result.get('score', 0)))),
                'label': result.get('label', 'neutral').lower()
            }
    except Exception as e:
        logger.warning(f"OpenAI sentiment analysis failed: {e}")
    
    # Fallback to business-aware sentiment analysis
    try:
        return analyze_business_sentiment(text)
    except Exception as e:
        logger.warning(f"Business sentiment analysis failed: {e}")
        return {'score': 0.0, 'label': 'neutral'}

def analyze_business_sentiment(text):
    """Business-aware sentiment analysis for customer feedback"""
    if not text.strip():
        return {'score': 0.0, 'label': 'neutral'}
    
    text_lower = text.lower()
    
    # Strong negative indicators (customer complaints)
    negative_strong = [
        'disappointed', 'frustrated', 'terrible', 'horrible', 'awful', 'hate',
        'worst', 'useless', 'broken', 'failed', 'failing', 'problem', 'problems',
        'issue', 'issues', 'bug', 'bugs', 'error', 'errors', 'slow', 'expensive',
        'overpriced', 'poor', 'bad', 'lacking', 'lacks', 'missing', 'difficulty',
        'difficulties', 'hard', 'complicated', 'confusing', 'unhappy', 'dissatisfied',
        'cancel', 'cancelled', 'refund', 'compensation', 'credit', 'credits',
        'fix', 'broken', 'not working', 'doesnt work', "doesn't work",
        'churn', 'churning', 'leave', 'leaving', 'switch', 'switching',
        'burden', 'caused us', 'waste', 'wasted', 'delay', 'delayed'
    ]
    
    # Moderate negative indicators (improvement requests)
    negative_moderate = [
        'improve', 'improvement', 'better', 'enhance', 'upgrade', 'update',
        'should', 'need', 'needs', 'require', 'must', 'have to',
        'consider', 'review', 'revise', 'change', 'modify', 'adjust',
        'lower', 'reduce', 'decrease', 'more', 'less', 'faster'
    ]
    
    # Positive indicators
    positive_indicators = [
        'good', 'great', 'excellent', 'amazing', 'awesome', 'love', 'like',
        'satisfied', 'happy', 'pleased', 'impressed', 'recommend', 'perfect',
        'fantastic', 'wonderful', 'outstanding', 'superb', 'brilliant',
        'genuine', 'understand', 'understands', 'evolves', 'meets', 'meet',
        'expectation', 'expectations', 'advanced', 'quality', 'reliable',
        'effective', 'efficient', 'professional', 'responsive', 'helpful'
    ]
    
    # Count indicators with context awareness
    strong_negative_count = sum(1 for word in negative_strong if word in text_lower)
    
    # Context-aware moderate negative counting
    moderate_negative_count = 0
    for word in negative_moderate:
        if word in text_lower:
            # Check context for words like "needs", "require", etc.
            if word in ['need', 'needs', 'require']:
                # Skip if in positive context like "understand our needs"
                positive_context = any(pos_word in text_lower for pos_word in ['understand', 'understands', 'meet', 'meets', 'fulfill', 'address', 'satisfy'])
                if not positive_context:
                    moderate_negative_count += 1
            else:
                moderate_negative_count += 1
    
    positive_count = sum(1 for word in positive_indicators if word in text_lower)
    
    # Calculate score based on business context
    if strong_negative_count > 0:
        score = -0.7 - (strong_negative_count * 0.1)  # Strong negative
        label = 'negative'
    elif moderate_negative_count > 2:
        score = -0.4 - (moderate_negative_count * 0.05)  # Moderate negative
        label = 'negative'
    elif moderate_negative_count > 0 and positive_count == 0:
        score = -0.2 - (moderate_negative_count * 0.05)  # Mild negative
        label = 'negative'
    elif positive_count > moderate_negative_count:
        score = 0.3 + (positive_count * 0.1)  # Positive
        label = 'positive'
    else:
        score = 0.0  # Neutral
        label = 'neutral'
    
    # Ensure score is within bounds
    score = max(-1.0, min(1.0, score))
    
    return {'score': score, 'label': label}

def extract_key_themes(text, nps_score):
    """Extract key themes from customer feedback"""
    if not text.strip():
        return []
    
    try:
        if openai_client:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing customer feedback. Extract the key themes, topics, and concerns from the feedback. Focus on aspects like product quality, service, pricing, features, support, etc. Return a JSON array of themes with their sentiment."
                    },
                    {
                        "role": "user",
                        "content": f"Extract key themes from this customer feedback (NPS score: {nps_score}): {text}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get('themes', [])
    except Exception as e:
        logger.warning(f"OpenAI theme extraction failed: {e}")
    
    # Fallback to basic keyword analysis
    keywords = ['product', 'service', 'price', 'pricing', 'support', 'feature', 'quality', 'value', 'team']
    themes = []
    text_lower = text.lower()
    
    for keyword in keywords:
        if keyword in text_lower:
            themes.append({'theme': keyword, 'sentiment': 'neutral'})
    
    return themes

def assess_churn_risk(response, text):
    """Assess churn risk based on NPS score and feedback"""
    risk_factors = []
    risk_points = 0
    text_lower = text.lower()
    
    # Check for explicit churn mentions first - these trigger immediate high risk
    churn_keywords = ['churn', 'leave', 'switch', 'competitor', 'cancel', 'terminate', 'discontinue', 'end relationship', 'looking elsewhere', 'considering alternatives']
    
    # Additional high-risk indicators
    high_risk_phrases = ['burden', 'caused us', 'issues caused', 'problems caused', 'damage', 'compensation', 'credits', 'refund', 'reimburse', 'waste of money', 'terrible experience', 'worst', 'useless', 'broken', 'unreliable', 'fed up', 'frustrated', 'disappointed', 'unacceptable', 'overpromised', 'overpromise', 'lacking', 'lie', 'lies', 'lying', 'deceived', 'deception', 'mislead', 'misleading', 'false', 'not delivered', 'failed to deliver', 'breach of trust']
    
    churn_detected = any(keyword in text_lower for keyword in churn_keywords)
    high_risk_detected = any(phrase in text_lower for phrase in high_risk_phrases)
    
    if churn_detected or high_risk_detected:
        risk_points += 5  # Immediately trigger high risk
        if churn_detected:
            risk_factors.append("Explicit churn indicators detected in feedback")
        if high_risk_detected:
            risk_factors.append("High-risk language indicating severe dissatisfaction")
    
    if churn_detected:
        risk_points += 5  # Immediately trigger high risk
        risk_factors.append("Explicit churn indicators detected in feedback")
    
    # Base risk from NPS score
    if response.nps_score <= 6:
        risk_points += 3
        risk_factors.append("Low NPS score indicating dissatisfaction")
    elif response.nps_score <= 8:
        risk_points += 2
        risk_factors.append("Neutral NPS score indicating potential churn risk")
    
    # Risk from ratings
    low_ratings = []
    if response.satisfaction_rating and response.satisfaction_rating <= 3:
        risk_points += 1
        low_ratings.append("satisfaction")
    if response.product_value_rating and response.product_value_rating <= 3:
        risk_points += 1
        low_ratings.append("product value")
    if response.service_rating and response.service_rating <= 3:
        risk_points += 1
        low_ratings.append("FC inc service delivery")
    if response.pricing_rating and response.pricing_rating <= 3:
        risk_points += 1
        low_ratings.append("pricing")
    
    if low_ratings:
        risk_factors.append(f"Low ratings in: {', '.join(low_ratings)}")
    
    # AI-based risk assessment
    try:
        if openai_client and text.strip():
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            ai_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a customer success expert. Analyze customer feedback to identify churn risk factors. Look for indicators like frustration, consideration of alternatives, unmet needs, or dissatisfaction. Return JSON with additional risk factors and their severity."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze churn risk from this feedback (NPS: {response.nps_score}): {text}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            ai_result = json.loads(ai_response.choices[0].message.content)
            ai_risk_factors = ai_result.get('risk_factors', [])
            ai_risk_severity = ai_result.get('additional_risk_points', 0)
            
            risk_factors.extend(ai_risk_factors)
            risk_points += int(ai_risk_severity)
    except Exception as e:
        logger.warning(f"AI churn risk assessment failed: {e}")
    
    # Convert risk points to categorical risk level
    if risk_points >= 5:
        risk_level = "High"
    elif risk_points >= 3:
        risk_level = "Medium"
    elif risk_points >= 1:
        risk_level = "Low"
    else:
        risk_level = "Minimal"
    
    return {
        'risk_level': risk_level,
        'risk_score': risk_points,  # Keep numerical for internal calculations
        'risk_factors': risk_factors
    }

def identify_growth_opportunities(response, text):
    """Identify growth opportunities from customer feedback"""
    opportunities = []
    
    # Opportunities from high NPS scores
    if response.nps_score >= 9:
        opportunities.append({
            'type': 'advocacy',
            'description': 'High NPS score - potential brand advocate',
            'action': 'Engage for case studies, referrals, or testimonials'
        })
    
    # Opportunities from high ratings
    high_ratings = []
    if response.satisfaction_rating and response.satisfaction_rating >= 4:
        high_ratings.append("satisfaction")
    if response.product_value_rating and response.product_value_rating >= 4:
        high_ratings.append("product value")
    if response.service_rating and response.service_rating >= 4:
        high_ratings.append("service")
    if response.pricing_rating and response.pricing_rating >= 4:
        high_ratings.append("pricing")
    
    if high_ratings:
        opportunities.append({
            'type': 'upsell',
            'description': f'High satisfaction in: {", ".join(high_ratings)}',
            'action': 'Consider upselling or cross-selling opportunities'
        })
    
    # AI-based opportunity identification
    try:
        if openai_client and text.strip():
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            ai_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business growth expert. Analyze customer feedback to identify GENUINE GROWTH OPPORTUNITIES ONLY - such as upselling, cross-selling, market expansion, or partnership opportunities based on POSITIVE customer sentiment. DO NOT classify problems, issues, complaints, or areas needing improvement as opportunities. If feedback mentions problems, defects, poor service, dissatisfaction, or areas that need fixing, those are RISK FACTORS, not growth opportunities. Only identify positive signals that indicate genuine expansion potential from satisfied customers. Return JSON with opportunities and recommended actions."
                    },
                    {
                        "role": "user",
                        "content": f"Identify growth opportunities from this feedback (NPS: {response.nps_score}): {text}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            ai_result = json.loads(ai_response.choices[0].message.content)
            ai_opportunities = ai_result.get('opportunities', [])
            
            # Filter out opportunities that contain problem/issue keywords
            problem_keywords = ['problem', 'issue', 'poor', 'bad', 'fail', 'broken', 'error', 'bug', 'complaint', 'dissatisfied', 'unhappy', 'frustrat', 'difficult', 'hard', 'confusing', 'wrong', 'missing', 'lack', 'without', 'slow', 'delayed']
            
            filtered_opportunities = []
            for opp in ai_opportunities:
                opp_text = (str(opp.get('type', '')) + ' ' + str(opp.get('description', ''))).lower()
                
                # Skip if this opportunity mentions problems/issues
                if any(keyword in opp_text for keyword in problem_keywords):
                    continue
                
                filtered_opportunities.append(opp)
            
            opportunities.extend(filtered_opportunities)
    except Exception as e:
        logger.warning(f"AI growth opportunity identification failed: {e}")
    
    return opportunities

def identify_account_risk_factors(response, text):
    """Identify account-specific risk factors from customer feedback"""
    risk_factors = []
    
    # Risk factors from low NPS scores
    if response.nps_score <= 3:
        risk_factors.append({
            'type': 'critical_satisfaction',
            'description': 'Critical NPS score - immediate attention required',
            'severity': 'Critical',
            'action': 'Schedule urgent customer success call within 24 hours'
        })
    elif response.nps_score <= 6:
        risk_factors.append({
            'type': 'low_satisfaction',
            'description': 'Low NPS score - customer dissatisfaction',
            'severity': 'High',
            'action': 'Engage customer success team for retention strategy'
        })
    
    # Risk factors from low ratings
    low_ratings = []
    if response.satisfaction_rating and response.satisfaction_rating <= 2:
        low_ratings.append("satisfaction")
    if response.product_value_rating and response.product_value_rating <= 2:
        low_ratings.append("product value")
    if response.service_rating and response.service_rating <= 2:
        low_ratings.append("service")
    if response.pricing_rating and response.pricing_rating <= 2:
        low_ratings.append("pricing")
    
    if low_ratings:
        risk_factors.append({
            'type': 'poor_ratings',
            'description': f'Poor ratings in: {", ".join(low_ratings)}',
            'severity': 'High',
            'action': 'Address specific pain points in affected areas'
        })
    
    # Risk factors from existing churn assessment
    if response.churn_risk_level in ['High', 'Medium']:
        risk_factors.append({
            'type': 'churn_risk',
            'description': f'{response.churn_risk_level} churn risk identified',
            'severity': response.churn_risk_level,
            'action': 'Implement retention measures and regular check-ins'
        })
    
    # AI-based risk factor identification
    try:
        if openai_client and text.strip():
            ai_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a customer success expert. Analyze feedback to identify specific account risk factors such as pricing concerns, service issues, product problems, competitor mentions, contract risks, or relationship threats. Return JSON with risk factors, severity levels, and recommended actions."
                    },
                    {
                        "role": "user",
                        "content": f"Identify account risk factors from this feedback (NPS: {response.nps_score}): {text}"
                    }
                ],
                response_format={"type": "json_object"}
            )
            
            ai_result = json.loads(ai_response.choices[0].message.content)
            ai_risk_factors = ai_result.get('risk_factors', [])
            
            # Ensure consistent data structure - filter out strings and validate objects
            for factor in ai_risk_factors:
                if isinstance(factor, dict) and all(key in factor for key in ['type', 'description', 'severity']):
                    # Ensure action field exists
                    if 'action' not in factor:
                        factor['action'] = 'Review and address this risk factor'
                    risk_factors.append(factor)
                elif isinstance(factor, str):
                    # Convert string to proper object format
                    risk_factors.append({
                        'type': factor.replace('_', ' ').title(),
                        'description': f'{factor.replace("_", " ").title()} identified in customer feedback',
                        'severity': 'Medium',  # Default severity for string factors
                        'action': f'Investigate and address {factor.replace("_", " ")} concerns'
                    })
    except Exception as e:
        logger.warning(f"AI account risk factor identification failed: {e}")
    
    return risk_factors

def calculate_growth_factor(nps_score):
    """Calculate growth factor based on NPS score using lookup table"""
    if nps_score < 0:
        return {'growth_rate': '0%', 'growth_factor': 0.0, 'range': '<0'}
    elif 0 <= nps_score <= 29:
        return {'growth_rate': '5%', 'growth_factor': 0.05, 'range': '0-29'}
    elif 30 <= nps_score <= 49:
        return {'growth_rate': '15%', 'growth_factor': 0.15, 'range': '30-49'}
    elif 50 <= nps_score <= 69:
        return {'growth_rate': '25%', 'growth_factor': 0.25, 'range': '50-69'}
    elif 70 <= nps_score <= 100:
        return {'growth_rate': '40%', 'growth_factor': 0.4, 'range': '70-100'}
    else:
        # Fallback for invalid scores
        return {'growth_rate': '0%', 'growth_factor': 0.0, 'range': 'invalid'}
