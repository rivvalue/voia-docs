"""
Campaign-Participant Token System
Handles token generation and validation for campaign-participant associations
"""

import os
import jwt
from datetime import datetime, timedelta
from models import CampaignParticipant, Campaign, Participant, db
import logging

logger = logging.getLogger(__name__)


def create_campaign_participant_token(association_id):
    """Generate a JWT token for a campaign-participant association"""
    try:
        # Get association with relationships
        association = CampaignParticipant.query.filter_by(id=association_id).first()
        if not association:
            return {
                'success': False,
                'error': 'Association not found'
            }
        
        # Validate campaign is active or ready to receive responses
        campaign = association.campaign
        if campaign.status not in ['ready', 'active']:
            return {
                'success': False,
                'error': f'Campaign is {campaign.status} and cannot accept responses'
            }
        
        # Use the same secret as Flask app - REQUIRED in production
        secret = os.environ.get("SESSION_SECRET")
        if not secret:
            raise ValueError("SESSION_SECRET environment variable is required for token security")
        
        # Create token payload with association data
        payload = {
            'association_id': association.id,
            'campaign_id': association.campaign_id,
            'participant_id': association.participant_id,
            'business_account_id': association.business_account_id,
            'email': association.participant.email.lower().strip(),
            'token_id': association.token,  # Reference the association's token
            'exp': datetime.utcnow() + timedelta(hours=72),  # 3 days for survey completion
            'iat': datetime.utcnow(),
            'iss': 'voia-campaign-participant'
        }
        
        # Generate JWT token
        jwt_token = jwt.encode(payload, secret, algorithm='HS256')
        
        # Update association with invitation timestamp
        if not association.invited_at:
            association.invited_at = datetime.utcnow()
            association.status = 'invited'
            db.session.commit()
        
        return {
            'success': True,
            'jwt_token': jwt_token,
            'association_id': association.id,
            'campaign_id': association.campaign_id,
            'participant_email': association.participant.email,
            'campaign_name': campaign.name,
            'expires_in': 259200  # 72 hours
        }
        
    except Exception as e:
        logger.error(f"Error creating campaign participant token: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def verify_campaign_participant_token(jwt_token):
    """Verify a campaign-participant JWT token and return association data"""
    try:
        if not jwt_token:
            return {'valid': False, 'error': 'No token provided'}
        
        secret = os.environ.get("SESSION_SECRET")
        if not secret:
            raise ValueError("SESSION_SECRET environment variable is required for token security")
        payload = jwt.decode(jwt_token, secret, algorithms=['HS256'])
        
        # Validate required fields in payload
        required_fields = ['association_id', 'campaign_id', 'participant_id', 'business_account_id', 'email']
        for field in required_fields:
            if field not in payload:
                return {'valid': False, 'error': f'Missing {field} in token'}
        
        # Verify association still exists
        association = CampaignParticipant.query.filter_by(id=payload['association_id']).first()
        if not association:
            return {'valid': False, 'error': 'Association not found'}
        
        # Verify token matches association token
        if association.token != payload.get('token_id'):
            return {'valid': False, 'error': 'Token mismatch'}
        
        # Verify campaign status allows responses
        campaign = association.campaign
        if campaign.status not in ['ready', 'active']:
            return {'valid': False, 'error': f'Campaign is {campaign.status} and cannot accept responses'}
        
        # Reject completed associations to prevent token reuse
        if association.status == 'completed':
            return {'valid': False, 'error': 'Survey has already been completed for this campaign'}
        
        # Update association status on first verification
        if association.status == 'invited':
            association.status = 'started'
            association.started_at = datetime.utcnow()
            db.session.commit()
        
        return {
            'valid': True,
            'association_id': association.id,
            'campaign_id': association.campaign_id,
            'participant_id': association.participant_id,
            'business_account_id': association.business_account_id,
            'email': association.participant.email.lower().strip(),
            'campaign_name': campaign.name,
            'participant_name': association.participant.name,
            'company_name': association.participant.company_name
        }
        
    except jwt.ExpiredSignatureError:
        return {'valid': False, 'error': 'Token has expired'}
    except jwt.InvalidTokenError:
        return {'valid': False, 'error': 'Invalid token'}
    except Exception as e:
        logger.error(f"Error verifying campaign participant token: {e}")
        return {'valid': False, 'error': 'Token verification failed'}


def generate_participant_survey_url(association_id, base_url="https://vocsa.replit.app"):
    """Generate a survey URL with campaign-participant token"""
    try:
        token_result = create_campaign_participant_token(association_id)
        if not token_result['success']:
            return {
                'success': False,
                'error': token_result['error']
            }
        
        # Create survey URL with JWT token
        survey_url = f"{base_url}/survey?token={token_result['jwt_token']}"
        conversational_url = f"{base_url}/conversational_survey?token={token_result['jwt_token']}"
        
        return {
            'success': True,
            'survey_url': survey_url,
            'conversational_url': conversational_url,
            'token': token_result['jwt_token'],
            'campaign_name': token_result['campaign_name'],
            'participant_email': token_result['participant_email'],
            'expires_in': token_result['expires_in']
        }
        
    except Exception as e:
        logger.error(f"Error generating participant survey URL: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def mark_survey_completed(association_id, survey_response_id):
    """Mark a campaign-participant association as completed"""
    try:
        association = CampaignParticipant.query.filter_by(id=association_id).first()
        if not association:
            return False
        
        association.status = 'completed'
        association.completed_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Marked association {association_id} as completed with response {survey_response_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error marking survey completed for association {association_id}: {e}")
        return False