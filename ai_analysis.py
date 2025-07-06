import json
import os
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
    """Perform comprehensive AI analysis on a survey response"""
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
        
        # Perform sentiment analysis
        sentiment_data = analyze_sentiment(combined_text)
        
        # Extract key themes
        themes = extract_key_themes(combined_text, response.nps_score)
        
        # Assess churn risk
        churn_analysis = assess_churn_risk(response, combined_text)
        
        # Identify growth opportunities
        growth_opportunities = identify_growth_opportunities(response, combined_text)
        
        # Update the response with analysis results
        response.sentiment_score = sentiment_data['score']
        response.sentiment_label = sentiment_data['label']
        response.key_themes = json.dumps(themes)
        response.churn_risk_score = churn_analysis['risk_score']
        response.churn_risk_level = churn_analysis['risk_level']
        response.churn_risk_factors = json.dumps(churn_analysis['risk_factors'])
        response.growth_opportunities = json.dumps(growth_opportunities)
        response.analyzed_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Analysis completed for response {response_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error analyzing response {response_id}: {e}")
        return False

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
    
    # Fallback to TextBlob
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.1:
            label = 'positive'
        elif polarity < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
            
        return {'score': polarity, 'label': label}
    except Exception as e:
        logger.warning(f"TextBlob sentiment analysis failed: {e}")
        return {'score': 0.0, 'label': 'neutral'}

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
    high_risk_phrases = ['burden', 'caused us', 'issues caused', 'problems caused', 'damage', 'compensation', 'credits', 'refund', 'reimburse', 'waste of money', 'terrible experience', 'worst', 'useless', 'broken', 'unreliable', 'fed up', 'frustrated', 'disappointed', 'unacceptable']
    
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
                        "content": "You are a business growth expert. Analyze customer feedback to identify growth opportunities such as upselling, cross-selling, feature requests, market expansion, or partnership opportunities. Return JSON with opportunities and recommended actions."
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
            opportunities.extend(ai_opportunities)
    except Exception as e:
        logger.warning(f"AI growth opportunity identification failed: {e}")
    
    return opportunities
