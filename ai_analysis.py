import json
import os
import csv
from datetime import datetime
from typing import Optional
from openai import OpenAI
from textblob import TextBlob
from app import db
from models import SurveyResponse
import logging

# LLM Gateway (provider-agnostic abstraction layer)
from llm_gateway import (
    LLMGateway, LLMRequest, LLMMessage, LLMResponse, LLMConfig,
    is_gateway_enabled, get_gateway
)

logger = logging.getLogger(__name__)

# Influence tier weights — maps role tier key to float multiplier
# Unknown / unrecognized roles fall back to 1.0 (End User equivalent)
INFLUENCE_TIER_WEIGHTS = {
    'c_level':    5.0,
    'vp_director': 3.0,
    'manager':    2.0,
    'team_lead':  1.5,
    'end_user':   1.0,
    'default':    1.0,
}


def resolve_influence_weight(response) -> float:
    """
    Derive the influence multiplier for a survey response.

    Looks up the participant's role via the CampaignParticipant → Participant
    chain if available, then maps it through _map_role_to_tier() (imported from
    prompt_template_service) to obtain the tier key and its multiplier.

    Falls back to 1.0 (End User equivalent) when:
    - The response has no associated CampaignParticipant
    - The participant has no role field
    - The role string is unrecognized
    """
    try:
        from prompt_template_service import _map_role_to_tier

        role_string = None

        # Primary path: follow the FK chain to the Participant record
        if response.campaign_participant_id:
            cp = response.campaign_participant
            if cp and cp.participant:
                role_string = cp.participant.role

        tier = _map_role_to_tier(role_string)
        weight = INFLUENCE_TIER_WEIGHTS.get(tier, 1.0)
        return weight

    except Exception as e:
        logger.warning(f"Could not resolve influence weight for response {getattr(response, 'id', '?')}: {e}")
        return 1.0


# Initialize OpenAI client (fallback when gateway disabled)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# LLM Gateway singleton (initialized lazily)
_llm_gateway: Optional[LLMGateway] = None

def _get_analysis_gateway() -> Optional[LLMGateway]:
    """Get or initialize the LLM gateway for analysis operations."""
    global _llm_gateway
    if _llm_gateway is None and is_gateway_enabled():
        _llm_gateway = get_gateway()
    return _llm_gateway if is_gateway_enabled() else None

def _call_llm_for_analysis(
    system_prompt: str,
    user_prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3,
    json_mode: bool = True,
    max_tokens: Optional[int] = 1500,
    business_account_id: Optional[int] = None
) -> str:
    """
    Unified LLM call for analysis operations with gateway support.
    
    Routes calls through LLM Gateway when enabled, falls back to direct
    OpenAI when gateway is disabled or unavailable.
    
    Args:
        system_prompt: System message for LLM
        user_prompt: User message for LLM
        model: Model to use (default: gpt-4o-mini)
        temperature: Temperature setting (default: 0.3)
        json_mode: Whether to request JSON response format
        max_tokens: Optional max tokens limit
        business_account_id: Optional business account ID for tenant-specific config
    
    Returns:
        LLM response content as string
    """
    gateway = _get_analysis_gateway()
    
    if gateway:
        # Use LLM Gateway (provider-agnostic path)
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=user_prompt)
            ],
            model=model,
            temperature=temperature,
            json_mode=json_mode,
            max_tokens=max_tokens
        )
        
        response = gateway.chat_completion(
            request,
            business_account_id=business_account_id
        )
        return response.content
    else:
        # Direct OpenAI path (production-proven, default)
        if not openai_client:
            raise ValueError("OpenAI client not available")
        
        api_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        
        if json_mode:
            api_params["response_format"] = {"type": "json_object"}
        
        if max_tokens:
            api_params["max_tokens"] = max_tokens
        
        response = openai_client.chat.completions.create(**api_params)
        return response.choices[0].message.content or ""

def analyze_survey_response(response_id):
    """Perform comprehensive AI analysis on a survey response with consolidated OpenAI call"""
    try:
        response = SurveyResponse.query.get(response_id)
        if not response:
            raise ValueError(f"Survey response {response_id} not found")
        
        # Collect all text for analysis (legacy + topic-specific fields)
        text_content = []
        # Topic-specific feedback fields (Jan 2026)
        if response.product_quality_feedback:
            text_content.append(response.product_quality_feedback)
        if response.service_rating_feedback:
            text_content.append(response.service_rating_feedback)
        if response.support_experience_feedback:
            text_content.append(response.support_experience_feedback)
        if response.user_experience_feedback:
            text_content.append(response.user_experience_feedback)
        if response.feature_requests:
            text_content.append(response.feature_requests)
        if response.general_feedback:
            text_content.append(response.general_feedback)
        # Legacy feedback fields
        if response.improvement_feedback:
            text_content.append(response.improvement_feedback)
        if response.recommendation_reason:
            text_content.append(response.recommendation_reason)
        if response.additional_comments:
            text_content.append(response.additional_comments)
        
        combined_text = " ".join(text_content)

        # Resolve influence weight from participant role (before AI analysis so it
        # can be passed into the prompt)
        influence_weight = resolve_influence_weight(response)
        response.influence_weight = influence_weight
        
        # Perform consolidated AI analysis (gateway or direct OpenAI)
        # Check for either gateway availability or OpenAI client
        llm_available = openai_client is not None or _get_analysis_gateway() is not None
        if combined_text.strip() and llm_available:
            analysis_results = perform_consolidated_ai_analysis(response, combined_text)
        else:
            # Fallback for empty text or no LLM provider available
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
        # Resolve participant role label and influence weight for prompt context
        influence_weight = getattr(response, 'influence_weight', None) or 1.0
        participant_role = "Unknown"
        try:
            if response.campaign_participant_id and response.campaign_participant:
                cp = response.campaign_participant
                if cp and cp.participant and cp.participant.role:
                    participant_role = cp.participant.role
        except Exception:
            pass

        # Human-readable influence level description for the prompt
        if influence_weight >= 5.0:
            influence_level_desc = "C-level executive (highest influence — 5×)"
        elif influence_weight >= 3.0:
            influence_level_desc = "VP/Director (high influence — 3×)"
        elif influence_weight >= 2.0:
            influence_level_desc = "Manager (moderate influence — 2×)"
        elif influence_weight >= 1.5:
            influence_level_desc = "Team Lead (moderate-low influence — 1.5×)"
        else:
            influence_level_desc = "End User / individual contributor (baseline influence — 1×)"

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
- Participant Role: {participant_role}
- Influence Level: {influence_level_desc}

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
   - IMPORTANT: Weight churn signals proportionally to the participant's influence level.
     A dissatisfied C-level executive or VP has significantly greater contract-cancellation
     authority than an end user, so their negative signals should produce higher risk scores.

4. GROWTH OPPORTUNITIES:
   - Array of genuine growth opportunities (upsell, cross-sell, expansion)
   - Only include positive signals from satisfied customers
   - Each opportunity: type, description, action
   - DO NOT include problems/issues as opportunities
   - IMPORTANT: Weight growth signals proportionally to the participant's influence level.
     Positive signals from senior stakeholders (C-level, VP) carry more strategic weight
     than those from end users.

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

        # Single LLM API call for all analysis (gateway or direct OpenAI)
        # Model selection via LLMConfig for unified configuration
        llm_config = LLMConfig.from_environment()
        analysis_model = llm_config.get_default_model()
        system_prompt = "You are a comprehensive customer feedback analysis expert. Analyze feedback and provide structured analysis covering sentiment, themes, churn risk, growth opportunities, and account risk factors. Always return valid JSON."
        
        # Get business account ID for tenant-specific config if available
        business_account_id = getattr(response, 'business_account_id', None)
        
        ai_content = _call_llm_for_analysis(
            system_prompt=system_prompt,
            user_prompt=consolidated_prompt,
            model=analysis_model,
            temperature=0.3,
            json_mode=True,
            max_tokens=1500,
            business_account_id=business_account_id
        )
        
        # Parse the consolidated response
        result = json.loads(ai_content)
        
        # Add rule-based enhancements to AI analysis
        result = enhance_analysis_with_rules(result, response, combined_text)
        
        return result
        
    except Exception as e:
        logger.warning(f"Consolidated AI analysis failed: {e}")
        # Fallback to rule-based analysis
        return perform_fallback_analysis(response, combined_text)

def enhance_analysis_with_rules(ai_result, response, text):
    """Enhance AI analysis with rule-based logic for consistency"""
    # Retrieve influence weight (default 1.0 if not yet set)
    influence_weight = getattr(response, 'influence_weight', None) or 1.0

    # NPS-based churn risk floor scaled upward by influence weight.
    # Higher-influence respondents (C-level, VP) have greater contract authority,
    # so their dissatisfaction must produce materially higher churn scores.
    # Base floors: NPS ≤ 3 → 5, NPS 4-6 → 3. Both are multiplied by influence_weight
    # and capped at 10 to keep the score in range.
    high_floor = min(10, round(5 * influence_weight))
    medium_floor = min(10, round(3 * influence_weight))

    if response.nps_score <= 3:
        if ai_result['churn']['risk_score'] < high_floor:
            ai_result['churn']['risk_score'] = high_floor
        ai_result['churn']['risk_level'] = 'High'
        if 'Critical NPS score' not in ai_result['churn']['risk_factors']:
            ai_result['churn']['risk_factors'].append('Critical NPS score')
    elif response.nps_score <= 6:
        if ai_result['churn']['risk_score'] < medium_floor:
            ai_result['churn']['risk_score'] = medium_floor
        if ai_result['churn']['risk_level'] == 'Minimal':
            ai_result['churn']['risk_level'] = 'Medium'

    # Add growth opportunities for high NPS.
    # Advocacy description carries the influence tier so downstream aggregation
    # (via influence_weight on the SurveyResponse) reflects seniority.
    if response.nps_score >= 9:
        advocacy_opportunity = {
            'type': 'advocacy',
            'description': 'High NPS score - potential brand advocate',
            'action': 'Engage for case studies, referrals, or testimonials'
        }
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
    """Fallback churn risk assessment with influence-weighted thresholds"""
    risk_factors = []
    risk_points = 0
    text_lower = text.lower()

    # Retrieve influence weight (default 1.0 if not set)
    influence_weight = getattr(response, 'influence_weight', None) or 1.0

    # Check for churn indicators — base points scaled by influence
    churn_keywords = ['churn', 'leave', 'switch', 'competitor', 'cancel', 'terminate']
    if any(keyword in text_lower for keyword in churn_keywords):
        risk_points += round(5 * influence_weight)
        risk_factors.append("Explicit churn indicators detected")
    
    # NPS-based risk — base points scaled by influence
    if response.nps_score <= 6:
        risk_points += round(3 * influence_weight)
        risk_factors.append("Low NPS score indicating dissatisfaction")
    
    # Convert to risk level using standard thresholds
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
