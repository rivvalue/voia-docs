"""
Campaign-Participant Token System
Handles token generation and validation for campaign-participant associations
"""

import os
import jwt
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_jwt_secret():
    """Get JWT secret from Flask app context or environment fallback"""
    try:
        from flask import current_app
        return current_app.secret_key
    except RuntimeError:
        # No app context, fall back to environment
        return os.environ.get("SESSION_SECRET")
    except ImportError:
        # Flask not available, fall back to environment
        return os.environ.get("SESSION_SECRET")


def create_campaign_participant_token(association_id):
    """Generate a JWT token for a campaign-participant association"""
    try:
        # Import models here to avoid circular imports
        from models import CampaignParticipant, db
        
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
            # Return structured error with code for frontend handling
            error_code = 'campaign_completed' if campaign.status == 'completed' else 'campaign_not_started'
            return {
                'success': False,
                'error': f'Campaign is {campaign.status} and cannot accept responses',
                'error_code': error_code,
                'campaign_status': campaign.status
            }
        
        # Use the same secret as Flask app - REQUIRED in production
        secret = get_jwt_secret()
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
            logger.warning("JWT Verification failed: No token provided")
            return {'valid': False, 'error': 'No token provided'}
        
        secret = get_jwt_secret()
        if not secret:
            raise ValueError("SESSION_SECRET environment variable is required for token security")
        
        logger.info("Decoding JWT token...")
        payload = jwt.decode(jwt_token, secret, algorithms=['HS256'], options={'verify_iat': False}, leeway=300)
        logger.info(f"JWT decoded successfully. Payload: {payload}")
        
        # Validate required fields in payload - ONLY require association_id since that's what we have
        if 'association_id' not in payload:
            return {'valid': False, 'error': 'Missing association_id in token'}
        
        # Import models here - we're already in Flask request context
        from models import CampaignParticipant
        from app import db
        
        # Verify association still exists
        association = CampaignParticipant.query.filter_by(id=payload['association_id']).first()
        if not association:
            return {'valid': False, 'error': 'Association not found'}
        
        # JWT signature already provides security - no need to verify UUID token match
        
        # Verify campaign status allows responses
        campaign = association.campaign
        if campaign.status not in ['ready', 'active']:
            # Return structured error with code for frontend handling
            error_code = 'campaign_completed' if campaign.status == 'completed' else 'campaign_not_started'
            return {
                'valid': False,
                'error': f'Campaign is {campaign.status} and cannot accept responses',
                'error_code': error_code,
                'campaign_status': campaign.status,
                'campaign_name': campaign.name,
                'campaign_end_date': campaign.end_date.strftime('%B %d, %Y') if campaign.end_date else None,
                'campaign_start_date': campaign.start_date.strftime('%B %d, %Y') if campaign.start_date else None
            }
        
        # Reject completed associations to prevent token reuse
        if association.status == 'completed':
            return {
                'valid': False,
                'error': 'Survey has already been completed for this campaign',
                'error_code': 'already_completed',
                'campaign_name': campaign.name,
                'completed_at': association.completed_at.strftime('%B %d, %Y') if association.completed_at else None
            }
        
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
        return {'valid': False, 'error': 'Token has expired', 'error_code': 'token_expired'}
    except jwt.InvalidTokenError as e:
        logger.exception(f"JWT decode failed: {e}")
        return {'valid': False, 'error': 'Invalid token', 'error_code': 'invalid_token'}
    except Exception as e:
        logger.error(f"Error verifying campaign participant token: {e}")
        return {'valid': False, 'error': 'Token verification failed', 'error_code': 'invalid_token'}


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


def mark_survey_completed(association_id, survey_response_id, auto_commit=True):
    """
    Mark a campaign-participant association as completed.
    
    Args:
        association_id: CampaignParticipant ID to mark as completed
        survey_response_id: SurveyResponse ID that was created
        auto_commit: If True, commits immediately (legacy behavior). 
                     If False, caller must commit (atomic transaction pattern).
    
    Returns:
        CampaignParticipant object if successful, None otherwise
    """
    try:
        # Import models here to avoid circular imports
        from models import CampaignParticipant, db
        
        association = CampaignParticipant.query.filter_by(id=association_id).first()
        if not association:
            logger.error(f"Association {association_id} not found")
            return None
        
        association.status = 'completed'
        association.completed_at = datetime.utcnow()
        
        if auto_commit:
            db.session.commit()
            logger.info(f"Marked association {association_id} as completed with response {survey_response_id} (auto-commit)")
        else:
            logger.info(f"Marked association {association_id} as completed with response {survey_response_id} (deferred commit)")
        
        return association
        
    except Exception as e:
        logger.error(f"Error marking survey completed for association {association_id}: {e}")
        if auto_commit:
            db.session.rollback()
        return None