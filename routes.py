from flask import render_template, request, jsonify, flash, redirect, url_for, g, session, send_file
from app import app, db, cache
# Models imported inside functions to avoid circular imports
from models import SurveyResponse, Participant, CampaignParticipant, Campaign, BusinessAccount
from data_storage import get_dashboard_data
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, or_

# Root route already exists - removed duplicate
from models_auth import AuthToken
from task_queue import add_analysis_task, get_queue_stats, add_export_task, get_export_job_status
from rate_limiter import rate_limit
from auth_system import require_auth, generate_user_token
from business_auth_routes import require_business_auth, require_permission, get_current_business_account, get_current_business_user
from feature_flags import feature_flags
from conversational_survey import start_conversational_survey, process_conversation_response, finalize_conversational_survey
from ai_conversational_survey import start_ai_conversational_survey, process_ai_conversation_response, finalize_ai_conversational_survey
from ai_conversational_survey_v2 import start_ai_conversational_survey_v2, process_ai_conversation_response_v2, finalize_ai_conversational_survey_v2
from audit_utils import queue_audit_log
from datetime import datetime, timedelta, date
import json
import logging
import os
import re
import uuid

logger = logging.getLogger(__name__)

# Anonymization utility function
def anonymize_response_data(campaign, response_data):
    """
    Anonymize response data if campaign requires it
    
    Args:
        campaign: Campaign object with anonymize_responses setting
        response_data: Dictionary with response data (company_name, respondent_name, respondent_email)
    
    Returns:
        dict: Modified response data with anonymized values if needed
    """
    if campaign and campaign.anonymize_responses:
        import hashlib
        
        # Create consistent hash from email for participant tracking
        email_hash = hashlib.sha256(response_data['respondent_email'].encode()).hexdigest()[:8]
        
        # Anonymize identifying information
        response_data.update({
            'respondent_name': f"Participant-{email_hash}",
            'respondent_email': f"participant-{email_hash}@anonymous.local",
            'company_name': "Anonymous Company"
        })
        
        logger.info(f"Response data anonymized for campaign {campaign.id}: {email_hash}")
    
    return response_data

def lookup_association_id_fallback(authenticated_email: str, campaign_id: int):
    """
    Fallback mechanism to find campaign_participant association_id when missing from session.
    
    Args:
        authenticated_email: The participant's email
        campaign_id: The campaign ID
        
    Returns:
        association_id if found, None otherwise
    """
    try:
        # Find the participant by email
        participant = Participant.query.filter_by(email=authenticated_email).first()
        if not participant:
            logger.warning(f"Fallback: No participant found for email {authenticated_email}")
            return None
        
        # Find the campaign participant association
        association = CampaignParticipant.query.filter_by(
            campaign_id=campaign_id,
            participant_id=participant.id
        ).first()
        
        if association:
            logger.info(f"Fallback: Found association_id {association.id} for {authenticated_email} in campaign {campaign_id}")
            return association.id
        else:
            logger.warning(f"Fallback: No association found for {authenticated_email} in campaign {campaign_id}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to lookup association_id: {e}")
        return None

# Health check endpoint to prevent 404 flood
@app.route('/api', methods=['GET', 'HEAD'])
def api_health_check():
    """Simple API health check endpoint"""
    from performance_monitor import performance_monitor
    
    # Enable monitoring and track this request manually
    if performance_monitor.is_monitoring_enabled():
        import time
        start_time = time.time()
        
        try:
            result = jsonify({'status': 'ok', 'service': 'voia'})
            
            # Manually track the request
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms
            
            with performance_monitor.lock:
                performance_monitor.response_times.append(response_time)
                performance_monitor.error_count.append(0)  # No error
                performance_monitor.request_count += 1
                
            return result
        except Exception as e:
            # Track error
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            with performance_monitor.lock:
                performance_monitor.response_times.append(response_time)
                performance_monitor.error_count.append(1)  # Error occurred
                performance_monitor.request_count += 1
                performance_monitor.error_total += 1
            
            raise
    else:
        return jsonify({'status': 'ok', 'service': 'voia'})

def get_branding_context(business_account_id=None):
    """
    Get branding context for templates including company name and logo URL.
    
    Args:
        business_account_id: ID of the business account, if None will try to get from session
    
    Returns:
        dict: Branding context with company_name, logo_url, and has_branding flag
    """
    branding_context = {
        'company_name': 'VOÏA - Voice Of Client Agent',  # Default fallback
        'logo_url': None,
        'has_branding': False,
        'branding_config': None
    }
    
    try:
        # Try to get business_account_id from parameter or session
        if not business_account_id:
            business_account_id = session.get('business_account_id')
        
        if business_account_id:
            from models import BrandingConfig
            branding_config = BrandingConfig.query.filter_by(business_account_id=business_account_id).first()
            
            if branding_config:
                # Update context with custom branding
                branding_context.update({
                    'company_name': branding_config.get_company_display_name(),
                    'logo_url': branding_config.get_logo_url(),
                    'has_branding': branding_config.has_logo(),
                    'branding_config': branding_config
                })
                
                logger.info(f"Loaded branding for business account {business_account_id}: {branding_context['company_name']}")
            else:
                logger.info(f"No branding config found for business account {business_account_id}, using defaults")
    
    except Exception as e:
        logger.warning(f"Error loading branding context: {e}")
        # Keep default fallback values
    
    return branding_context

def is_jwt_token(token):
    """Check if token is in JWT format (contains dots) vs UUID format"""
    return '.' in token and len(token.split('.')) == 3

def verify_survey_access(token):
    """
    Centralized token verification for survey access.
    Returns verification result with user data or error details.
    
    Language Strategy:
    - Anonymous + campaign token: reset, use campaign.language_code
    - Anonymous + simple token: reset, use "en"
    - Dashboard user: preserve existing session['language'], restore on errors
    """
    # Reset language for all survey token access (anonymous prevents contamination, dashboard gets temporary override)
    # Dashboard routes will restore user language preference when navigating back from survey
    is_dashboard_user = 'business_user_id' in session
    if not is_dashboard_user:
        session.pop('language', None)  # Only clear for anonymous to prevent cross-survey contamination
    
    if not token:
        return {
            'valid': False,
            'error': 'No token provided',
            'authenticated': False
        }
    
    # Try CampaignParticipant token first (new system) - only if it looks like JWT
    if is_jwt_token(token):
        import campaign_participant_token_system
        verification = campaign_participant_token_system.verify_campaign_participant_token(token)
        if verification.get('valid'):
            # Store campaign-participant association data in session
            session['auth_token'] = token
            session['auth_email'] = verification.get('email')
            session['association_id'] = verification.get('association_id')
            session['campaign_id'] = verification.get('campaign_id')
            session['participant_id'] = verification.get('participant_id')
            session['business_account_id'] = verification.get('business_account_id')
            
            # Set campaign language for Flask-Babel (temporarily for surveys, dashboard routes will restore user preference)
            campaign_id = verification.get('campaign_id')
            if campaign_id:
                try:
                    from models import Campaign
                    campaign = Campaign.query.get(campaign_id)
                    if campaign and hasattr(campaign, 'language_code') and campaign.language_code:
                        # Validate language is supported
                        supported_languages = ['en', 'fr']
                        if campaign.language_code in supported_languages:
                            session['language'] = campaign.language_code
                            logger.info(f"Set survey language to {campaign.language_code} for campaign {campaign_id}")
                        else:
                            logger.warning(f"Unsupported campaign language '{campaign.language_code}', falling back to English")
                            session['language'] = 'en'
                    else:
                        # Campaign exists but has no language - use English
                        session['language'] = 'en'
                except Exception as e:
                    logger.warning(f"Failed to load campaign language: {e}")
                    session['language'] = 'en'
            else:
                # No campaign_id - use English
                session['language'] = 'en'
            
            return {
                'valid': True,
                'authenticated': True,
                'email': verification.get('email'),
                'user_email': verification.get('email'),
                'participant_name': verification.get('participant_name'),
                'participant_company': verification.get('company_name'),
                'campaign_name': verification.get('campaign_name'),
                'token': token,
                'campaign_id': verification.get('campaign_id'),
                'participant_id': verification.get('participant_id'),
                'business_account_id': verification.get('business_account_id'),
                'association_id': verification.get('association_id')
            }
    
    # Fallback to simple token system for backward compatibility
    import simple_token_system
    fallback_verification = simple_token_system.verify_simple_token(token)
    if fallback_verification.get('valid'):
        email = fallback_verification.get('email')
        session['auth_token'] = token
        session['auth_email'] = email
        # Simple token users use English
        session['language'] = 'en'
        return {
            'valid': True,
            'authenticated': True,
            'email': email,
            'user_email': email,
            'participant_name': None,
            'participant_company': None,
            'campaign_name': None,
            'token': token
        }
    
    # Final fallback: Check if token is a UUID from the database
    from models import CampaignParticipant, Participant, Campaign
    from datetime import datetime
    from app import db
    
    # Try campaign-participant token first
    uuid_participant = CampaignParticipant.query.filter_by(token=token).first()
    if uuid_participant and uuid_participant.campaign.status in ['ready', 'active']:
        # Found valid UUID token from campaign_participants table
        participant = uuid_participant.participant
        campaign = uuid_participant.campaign
        
        # Store session data
        session['auth_token'] = token
        session['auth_email'] = participant.email
        session['association_id'] = uuid_participant.id
        session['campaign_id'] = campaign.id
        session['participant_id'] = participant.id
        session['business_account_id'] = uuid_participant.business_account_id
        
        # Set campaign language for Flask-Babel (with validation)
        if hasattr(campaign, 'language_code') and campaign.language_code:
            supported_languages = ['en', 'fr']
            if campaign.language_code in supported_languages:
                session['language'] = campaign.language_code
                logger.info(f"Set survey language to {campaign.language_code} for campaign {campaign.id}")
            else:
                logger.warning(f"Unsupported campaign language '{campaign.language_code}', falling back to English")
                session['language'] = 'en'
        else:
            session['language'] = 'en'  # Explicit default for campaigns without language
        
        # Update status if first access
        if uuid_participant.status == 'invited':
            uuid_participant.status = 'started'
            uuid_participant.started_at = datetime.utcnow()
            db.session.commit()
        
        logger.info(f"Campaign-participant UUID token authentication successful for {participant.email}")
        return {
            'valid': True,
            'authenticated': True,
            'email': participant.email,
            'user_email': participant.email,
            'participant_name': participant.name,
            'participant_company': participant.company_name,
            'campaign_name': campaign.name,
            'business_account_id': uuid_participant.business_account_id,
            'campaign_id': campaign.id,
            'participant_id': participant.id,
            'association_id': uuid_participant.id,
            'token': token
        }
    
    # Token verification failed
    error_msg = 'Invalid or expired token'
    if is_jwt_token(token):
        # Only show JWT-specific error for JWT tokens to avoid confusion
        verification_result = campaign_participant_token_system.verify_campaign_participant_token(token)
        error_msg = verification_result.get('error', error_msg)
    
    return {
        'valid': False,
        'authenticated': False,
        'error': error_msg,
        'token': token
    }

def normalize_company_name(company_name):
    """Normalize company name for case-insensitive comparison"""
    if not company_name:
        return company_name
    # Convert to title case for consistent display (first letter caps, rest lowercase)
    return company_name.strip().title()

from tenure_utils import map_tenure_years_to_category  # noqa: F401 (re-exported for callers)

def ensure_trial_participant(email, name, company_name, campaign_id):
    """
    Ensure a trial participant exists and is associated with the campaign.
    Creates participant with source='trial' if not exists, ensures campaign association.
    Returns (participant, campaign_participant_association)
    """
    from models import Participant, CampaignParticipant, Campaign
    from sqlalchemy import func
    
    # Normalize inputs
    email = email.strip().lower()
    company_name = normalize_company_name(company_name) if company_name else None
    name = name.strip() if name else email.split('@')[0]
    
    # Get campaign to check business_account_id
    campaign = Campaign.query.get(campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {campaign_id} not found")
    
    # Look for existing participant by email (case-insensitive)
    existing_participant = Participant.query.filter(
        func.lower(Participant.email) == email
    ).first()
    
    if existing_participant:
        # Use existing participant if business_account_id matches campaign or participant is trial user
        if (existing_participant.business_account_id == campaign.business_account_id or 
            existing_participant.business_account_id is None):
            participant = existing_participant
        else:
            # Different business context - create new trial participant
            participant = None
    else:
        participant = None
    
    # Create new trial participant if needed
    if not participant:
        participant = Participant(
            email=email,
            name=name,
            company_name=company_name,
            source='trial',
            business_account_id=None,  # Trial users have NULL business_account_id
            status='invited'
        )
        
        # Generate unique token for participant
        participant.generate_token()
        
        db.session.add(participant)
        db.session.flush()  # Get the participant ID
        
        logger.info(f"Created trial participant: {email} (ID: {participant.id})")
    
    # Ensure campaign association exists
    campaign_association = CampaignParticipant.query.filter_by(
        campaign_id=campaign_id,
        participant_id=participant.id
    ).first()
    
    if not campaign_association:
        campaign_association = CampaignParticipant(
            campaign_id=campaign_id,
            participant_id=participant.id,
            business_account_id=campaign.business_account_id,
            status='started'  # Will be updated to 'completed' when survey is submitted
        )
        
        db.session.add(campaign_association)
        db.session.flush()  # Get the association ID
        
        logger.info(f"Created campaign association: participant {participant.id} -> campaign {campaign_id}")
    
    return participant, campaign_association

@app.route('/')
@cache.cached(timeout=300, key_prefix=lambda: f"index_{session.get('language', 'en')}", unless=lambda: bool(session.get('auth_token')))
def index():
    """Landing page with survey overview"""
    # Pass authentication status to template
    auth_email = session.get('auth_email')
    auth_token = session.get('auth_token')
    is_authenticated = bool(auth_token)
    # Only show user email if there's both token and email (active session)
    user_email = auth_email if (auth_token and auth_email) else None
    return render_template('index.html', authenticated=is_authenticated, email=auth_email, user_email=user_email)

@app.route('/demo')
def demo_intro():
    """Demo introduction page with Archelo Group context"""
    return render_template('demo_intro.html')

@app.route('/auth/request-token', methods=['POST'])
@rate_limit(limit=5)  # 5 token requests per minute per IP
def request_token():
    """Generate authentication token for email address"""
    try:
        logger.info(f"Token request received - Method: {request.method}")
        logger.info(f"Token request headers: {dict(request.headers)}")
        logger.info(f"Token request content type: {request.content_type}")
        
        data = request.json
        logger.info(f"Token request data: {data}")
        
        if not data or 'email' not in data:
            logger.warning("Token request missing email data")
            return jsonify({
                'error': 'Email address is required',
                'code': 'MISSING_EMAIL'
            }), 400
        
        email = data['email'].lower().strip()
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({
                'error': 'Invalid email format',
                'code': 'INVALID_EMAIL'
            }), 400
        
        # Generate token
        token = generate_user_token(email)
        
        # Store token metadata for audit
        # Get IP address and truncate to fit database column (45 chars max)
        raw_ip = request.environ.get('HTTP_X_FORWARDED_FOR', 
                                   request.environ.get('REMOTE_ADDR', ''))
        # Take first IP if multiple IPs, and truncate to 45 chars
        ip_address = raw_ip.split(',')[0].strip()[:45] if raw_ip else ''
        
        token_record = AuthToken(
            email=email,
            token_id=token[-16:],  # Use last 16 chars as token ID
            expires_at=datetime.utcnow() + timedelta(hours=24),
            ip_address=ip_address,
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        
        db.session.add(token_record)
        db.session.commit()
        
        logger.info(f"Generated authentication token for {email}")
        
        return jsonify({
            'message': 'Authentication token generated successfully',
            'token': token,
            'expires_in': 24 * 3600,  # 24 hours in seconds
            'email': email
        })
        
    except Exception as e:
        logger.error(f"Error generating token: {e}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception args: {e.args}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({
            'error': 'Failed to generate authentication token',
            'code': 'TOKEN_GENERATION_FAILED',
            'debug_info': str(e) if app.debug else None
        }), 500

@app.route('/auth/verify-token', methods=['POST'])
def verify_token():
    """Verify if a token is valid and check admin status"""
    try:
        # Support both Authorization header and JSON body
        token = None
        if request.headers.get('Authorization'):
            token = request.headers.get('Authorization')
        elif request.json and 'token' in request.json:
            token = request.json['token']
        
        if not token:
            return jsonify({
                'valid': False,
                'error': 'No token provided'
            }), 400
        
        from auth_system import auth_system
        
        # Get full payload to check admin status
        payload = auth_system.verify_token(token, return_payload=True)
        
        if payload:
            email = payload.get('email')
            is_admin = payload.get('is_admin', False)
            # Double-check admin status against current admin list
            is_admin_verified = email in auth_system.admin_emails
            
            return jsonify({
                'valid': True,
                'email': email,
                'is_admin': is_admin_verified,
                'message': 'Token is valid'
            })
        else:
            return jsonify({
                'valid': False,
                'error': 'Invalid token'
            }), 401
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 401

@app.route('/auth')
def auth():
    """Authentication page - redirect to server-side auth"""
    return redirect(url_for('server_auth'))

@app.route('/test-token')
def test_token():
    """Test page for token generation debugging"""
    return render_template('test_token.html')

@app.route('/simple-auth')
def simple_auth():
    """Simple authentication test page"""
    return render_template('simple_auth.html')

@app.route('/server-auth', methods=['GET', 'POST'])
def server_auth():
    """Server-side authentication - no JavaScript required"""
    # Get demo branding for trial users
    branding_context = get_branding_context(business_account_id=1)
    return render_template('server_auth.html', 
                         user_email=None,
                         branding_context=branding_context,
                         is_business_authenticated=False)

@app.route('/server-auth/generate', methods=['POST'])
def server_auth_generate():
    """Server-side token generation"""
    try:
        email = request.form.get('email', '').strip().lower()
        survey_type = request.form.get('survey_type', 'conversational')
        
        if not email:
            token_result = {
                'success': False,
                'error': 'Email address is required'
            }
            # Get demo branding for trial users
            branding_context = get_branding_context(business_account_id=1)
            return render_template('server_auth.html', 
                                 token_result=token_result,
                                 branding_context=branding_context,
                                 is_business_authenticated=False)
        
        # Use ultra-simple token system to avoid all import issues
        import simple_token_system
        token_data = simple_token_system.create_simple_token(email)
        
        if token_data['success']:
            token_result = {
                'success': True,
                'email': token_data['email'],
                'token': token_data['token'],
                'expires_in': token_data['expires_in'],
                'survey_type': survey_type
            }
        else:
            token_result = {
                'success': False,
                'error': token_data['error']
            }
        
        app.logger.info(f"Server-side token generated for {email}")
        # Get demo branding for trial users
        branding_context = get_branding_context(business_account_id=1)
        return render_template('server_auth.html', 
                             token_result=token_result,
                             branding_context=branding_context,
                             is_business_authenticated=False)
        
    except Exception as e:
        app.logger.error(f"Server-side token generation failed: {e}")
        token_result = {
            'success': False,
            'error': f'Token generation failed: {str(e)}'
        }
        # Get demo branding for trial users
        branding_context = get_branding_context(business_account_id=1)
        return render_template('server_auth.html', 
                             token_result=token_result,
                             branding_context=branding_context,
                             is_business_authenticated=False)

@app.route('/survey/<token>')
def survey_with_token(token):
    """Survey route variant for /survey/<token> format - redirects to query parameter format"""
    logger.info(f"Survey route variant accessed: /survey/{token}")
    # Redirect to standard format with 302 (temporary redirect)
    return redirect(url_for('survey', token=token), code=302)

@app.route('/survey<path:encoded_params>')
def survey_url_encoded_flexible(encoded_params):
    """Handle URL-encoded survey links where query parameters are encoded in the path"""
    logger.info(f"URL-encoded survey route accessed: /survey{encoded_params}")
    
    # Flask automatically URL-decodes the path, so %3F becomes ? by the time we see it
    # Check if this looks like query string parameters (starts with ?)
    if encoded_params.startswith('?'):
        logger.info(f"Detected query parameters in path: {encoded_params}")
        
        # Extract token from parameters (should be like "?token=abc123")
        if encoded_params.startswith('?token='):
            token = encoded_params[7:]  # Remove "?token=" prefix
            
            # Handle additional parameters if present
            if '&' in token:
                token = token.split('&')[0]
            
            logger.info(f"Extracted token from URL-encoded path: {token}")
            
            # Redirect to standard format with 302 (temporary redirect)
            return redirect(url_for('survey', token=token), code=302)
        
        # If not a token parameter, fall through to 404
        logger.warning(f"URL-encoded path doesn't contain token parameter: {encoded_params}")
    
    # If this doesn't look like query parameters, return 404
    logger.warning(f"Unrecognized URL-encoded path pattern: {encoded_params}")
    from flask import abort
    abort(404)

@app.route('/survey')
def survey():
    """Main survey choice page - shows AI conversational vs traditional form options"""
    token = request.args.get('token')
    
    if token:
        # Use centralized token verification
        verification = verify_survey_access(token)
        if verification['valid']:
            # Check if this is a business participant (invited via campaign)
            participant_name = verification.get('participant_name')
            campaign_name = verification.get('campaign_name')
            
            if participant_name and campaign_name:
                # Business participant - check survey type for routing
                campaign_id = session.get('campaign_id')
                if campaign_id:
                    from models import Campaign
                    campaign = Campaign.query.get(campaign_id)
                    if campaign and campaign.survey_type == 'classic':
                        logger.info(f"Business participant detected, redirecting to classic survey: {participant_name}")
                        return redirect(url_for('classic_survey', token=token))
                
                # Default: conversational survey (VOÏA)
                logger.info(f"Business participant detected, redirecting to conversational survey: {participant_name}")
                return redirect(url_for('conversational_survey', token=token))
            else:
                # Demo user - show choice page
                branding = get_branding_context(verification.get('business_account_id'))
                return render_template('survey_choice.html', 
                                     authenticated=verification['authenticated'],
                                     email=verification['email'], 
                                     user_email=verification['user_email'],
                                     participant_name=participant_name,
                                     participant_company=verification['participant_company'],
                                     campaign_name=campaign_name,
                                     branding=branding)
        else:
            # Token verification failed - render error page
            error_code = verification.get('error_code', 'invalid_token')
            branding = get_branding_context()
            return render_template('survey_unavailable.html',
                                 error_code=error_code,
                                 error_message=verification.get('error'),
                                 campaign_name=verification.get('campaign_name'),
                                 campaign_end_date=verification.get('campaign_end_date'),
                                 campaign_start_date=verification.get('campaign_start_date'),
                                 completed_at=verification.get('completed_at'),
                                 show_contact_info=True,
                                 branding=branding)
    else:
        # Check if already authenticated via session
        if session.get('auth_token'):
            email = session.get('auth_email')
            # Get branding context from session
            branding = get_branding_context()
            # For session-based access, we may not have all participant details
            return render_template('survey_choice.html', 
                                 authenticated=True, 
                                 email=email, 
                                 user_email=email,
                                 participant_name=None,
                                 participant_company=None,
                                 campaign_name=None,
                                 branding=branding)
        else:
            # Redirect unauthenticated users to auth page instead of showing broken page
            return redirect(url_for('server_auth'))

@app.route('/survey_form')
def survey_form():
    """Traditional survey form page with pre-populated data"""
    token = request.args.get('token')
    
    if token:
        # Use centralized token verification
        verification = verify_survey_access(token)
        if verification['valid']:
            # Check if this is a business participant
            business_account_id = verification.get('business_account_id')
            is_business_authenticated = business_account_id is not None and business_account_id != 1
            
            # Get branding context
            if is_business_authenticated:
                branding_context = get_branding_context(business_account_id)
            else:
                # Trial user - get demo branding
                branding_context = get_branding_context(business_account_id=1)
            
            return render_template('survey.html', 
                                 authenticated=verification['authenticated'],
                                 email=verification['email'], 
                                 user_email=verification['user_email'],
                                 participant_name=verification['participant_name'],
                                 participant_company=verification['participant_company'],
                                 campaign_name=verification['campaign_name'],
                                 branding=branding_context,
                                 branding_context=branding_context,
                                 is_business_authenticated=is_business_authenticated)
        else:
            # Token verification failed - render error page
            error_code = verification.get('error_code', 'invalid_token')
            branding_context = get_branding_context(business_account_id=1)
            return render_template('survey_unavailable.html',
                                 error_code=error_code,
                                 error_message=verification.get('error'),
                                 campaign_name=verification.get('campaign_name'),
                                 campaign_end_date=verification.get('campaign_end_date'),
                                 campaign_start_date=verification.get('campaign_start_date'),
                                 completed_at=verification.get('completed_at'),
                                 show_contact_info=True,
                                 branding=branding_context)
    else:
        # Check if already authenticated via session
        if session.get('auth_token'):
            email = session.get('auth_email')
            # Get demo branding for trial users (session-based access)
            branding_context = get_branding_context(business_account_id=1)
            # For session-based access, we may not have all participant details
            return render_template('survey.html', 
                                 authenticated=True, 
                                 email=email, 
                                 user_email=email,
                                 participant_name=None,
                                 participant_company=None,
                                 campaign_name=None,
                                 branding=branding_context,
                                 branding_context=branding_context,
                                 is_business_authenticated=False)
        else:
            # Redirect unauthenticated users to auth page instead of showing broken page
            return redirect(url_for('server_auth'))

@app.route('/submit_survey_form', methods=['POST'])
@rate_limit(limit=10)
def submit_survey_form():
    """Handle server-side form submission (no JavaScript required)"""
    try:
        # Import models to avoid circular imports
        from models import SurveyResponse, Campaign
        
        print("=== FORM SUBMISSION RECEIVED ===")
        
        # Check if user is authenticated via session
        if not session.get('auth_token'):
            return render_template('survey.html', authenticated=False, error='Authentication required')
            
        # Get form data
        data = request.form.to_dict()
        print(f"Form data received: {data}")
        
        # Get authenticated email from session
        authenticated_email = session.get('auth_email')
        print(f"Authenticated email: {authenticated_email}")
        
        if not authenticated_email:
            return render_template('survey.html', authenticated=False, error='Authentication session expired')
        
        # Validate required fields
        required_fields = ['company_name', 'respondent_name', 'nps_score']
        for field in required_fields:
            if field not in data or not data[field]:
                return render_template('survey.html', authenticated=True, email=authenticated_email, 
                                     error=f'Missing required field: {field}')
        
        # Process survey submission (same logic as AJAX version)
        nps_score = int(data['nps_score'])
        if nps_score >= 9:
            nps_category = 'Promoter'
        elif nps_score >= 7:
            nps_category = 'Passive'
        else:
            nps_category = 'Detractor'
        
        # Get campaign and association data from session (new system)
        association_id = session.get('association_id')
        campaign_id = session.get('campaign_id')
        
        # Fallback to active campaign for backward compatibility (old system)
        campaign = None
        if not campaign_id:
            demo_account = BusinessAccount.query.filter_by(name='Archelo Group inc').first()
            if demo_account:
                active_campaigns = Campaign.get_active_campaigns(demo_account.id)
                active_campaign = active_campaigns[0] if active_campaigns else None
            else:
                active_campaign = None
            campaign_id = active_campaign.id if active_campaign else None
            campaign = active_campaign
        else:
            campaign = Campaign.query.get(campaign_id)
        
        # Prepare response data for potential anonymization
        response_data = {
            'company_name': normalize_company_name(data['company_name']),
            'respondent_name': data['respondent_name'],
            'respondent_email': authenticated_email
        }
        
        # Apply anonymization if campaign requires it
        response_data = anonymize_response_data(campaign, response_data)
        
        # Create survey response with potentially anonymized data
        response = SurveyResponse(
            company_name=response_data['company_name'],
            respondent_name=response_data['respondent_name'],
            respondent_email=response_data['respondent_email'],
            tenure_with_fc=data.get('tenure_with_fc'),
            nps_score=nps_score,
            nps_category=nps_category,
            satisfaction_rating=int(data['satisfaction_rating']) if data.get('satisfaction_rating') else None,
            product_value_rating=int(data['product_value_rating']) if data.get('product_value_rating') else None,
            service_rating=int(data['service_rating']) if data.get('service_rating') else None,
            pricing_rating=int(data['pricing_rating']) if data.get('pricing_rating') else None,
            improvement_feedback=data.get('improvement_feedback'),
            recommendation_reason=data.get('recommendation_reason'),
            additional_comments=data.get('additional_comments'),
            campaign_id=campaign_id,
            campaign_participant_id=association_id  # Link to campaign-participant association
        )
        
        # Ensure trial participant exists and is associated with campaign
        if campaign_id and not association_id:
            # This is a trial user completing via public survey - create participant record
            try:
                participant, campaign_association = ensure_trial_participant(
                    email=authenticated_email,
                    name=data['respondent_name'],
                    company_name=data['company_name'],
                    campaign_id=campaign_id
                )
                
                # Link response to the campaign participant association
                response.campaign_participant_id = campaign_association.id
                
                # Mark association as completed
                campaign_association.status = 'completed'
                campaign_association.completed_at = datetime.utcnow()
                
                logger.info(f"Trial participant created and linked: {participant.email} -> campaign {campaign_id}")
                
            except Exception as e:
                logger.error(f"Failed to create trial participant: {e}")
                # Continue without participant linkage to maintain backward compatibility
        
        db.session.add(response)
        db.session.commit()
        
        # Bust dashboard cache so the next Executive Summary load reflects fresh data
        if campaign_id:
            try:
                from data_storage import bust_dashboard_cache
                campaign_ba_id = campaign.business_account_id if campaign else None
                if campaign_ba_id:
                    bust_dashboard_cache(campaign_id, campaign_ba_id, company_name=response.company_name)
            except Exception as cache_bust_err:
                logger.warning(f"Cache bust failed after form survey submit: {cache_bust_err}")
        
        # Mark association as completed if using new token system
        # Fallback: Look up association_id from database if missing from session
        if not association_id and campaign_id and authenticated_email:
            association_id = lookup_association_id_fallback(authenticated_email, campaign_id)
            if association_id:
                # Also link the response to the association
                response.campaign_participant_id = association_id
                db.session.commit()
        
        if association_id:
            try:
                import campaign_participant_token_system
                campaign_participant_token_system.mark_survey_completed(association_id, response.id)
            except Exception as e:
                logger.error(f"Failed to mark association completed: {e}")
        
        # Queue AI analysis
        try:
            add_analysis_task(response.id)
            analysis_status = "queued"
        except Exception as e:
            logger.error(f"Failed to queue AI analysis: {e}")
            analysis_status = "failed"
        
        # AUTOMATIC TOKEN INVALIDATION
        session.pop('auth_token', None)
        session.pop('auth_email', None)
        session.permanent = False
        print(f"=== TOKEN INVALIDATED FOR {authenticated_email} ===")
        logger.info(f"Form survey submitted by {authenticated_email} - Token invalidated")
        
        # Get branding context for success page
        branding = get_branding_context()
        
        # Redirect to success page showing token was invalidated
        return render_template('survey_success.html', 
                             response_id=response.id,
                             analysis_status=analysis_status,
                             email=authenticated_email,
                             branding=branding)
        
    except Exception as e:
        logger.error(f"Error in form survey submission: {e}")
        return render_template('survey.html', authenticated=True, email=session.get('auth_email'), 
                             error=f'Survey submission failed: {str(e)}')

@app.route('/classic_survey')
def classic_survey():
    """Classic structured survey form for business participants"""
    token = request.args.get('token')
    
    if not token:
        if session.get('auth_token'):
            token = session.get('auth_token')
        else:
            return redirect(url_for('server_auth'))
    
    # Use centralized token verification (sets session['language'] from campaign.language_code)
    verification = verify_survey_access(token)
    
    # Force Babel to re-evaluate locale now that session['language'] is set
    # Without this, Babel may have cached a locale from the browser Accept-Language header
    from flask_babel import refresh as babel_refresh
    babel_refresh()
    
    if not verification['valid']:
        error_code = verification.get('error_code', 'invalid_token')
        branding = get_branding_context()
        return render_template('survey_unavailable.html',
                             error_code=error_code,
                             error_message=verification.get('error'),
                             campaign_name=verification.get('campaign_name'),
                             campaign_end_date=verification.get('campaign_end_date'),
                             campaign_start_date=verification.get('campaign_start_date'),
                             completed_at=verification.get('completed_at'),
                             show_contact_info=True,
                             branding=branding)
    
    # Get campaign and classic survey config
    campaign_id = session.get('campaign_id')
    campaign = None
    classic_config = None
    
    if campaign_id:
        from models import Campaign, ClassicSurveyConfig
        campaign = Campaign.query.get(campaign_id)
        if campaign:
            classic_config = ClassicSurveyConfig.query.filter_by(campaign_id=campaign.id).first()
    
    if not campaign or campaign.survey_type != 'classic':
        return redirect(url_for('conversational_survey', token=token))
    
    # Get branding context
    business_account_id = verification.get('business_account_id') or session.get('business_account_id')
    branding = get_branding_context(business_account_id)
    
    # Determine language
    lang = session.get('language', 'en')
    
    # Prepare driver labels from config
    driver_labels = []
    if classic_config and classic_config.driver_labels:
        driver_labels = classic_config.driver_labels
    
    # Prepare features from config  
    features = []
    if classic_config and classic_config.features:
        features = classic_config.features
    
    # Prepare sections enabled
    sections_enabled = {'section_1': True, 'section_2': True, 'section_3': True}
    if classic_config and classic_config.sections_enabled:
        sections_enabled = classic_config.sections_enabled
    
    return render_template('classic_survey.html',
                         authenticated=verification['authenticated'],
                         email=verification['email'],
                         participant_name=verification.get('participant_name'),
                         participant_company=verification.get('participant_company'),
                         campaign_name=verification.get('campaign_name'),
                         campaign_description=campaign.description if campaign else None,
                         campaign_start_date=campaign.start_date if campaign else None,
                         campaign_end_date=campaign.end_date if campaign else None,
                         campaign=campaign,
                         classic_config=classic_config,
                         driver_labels=driver_labels,
                         features=features,
                         sections_enabled=sections_enabled,
                         lang=lang,
                         branding=branding,
                         token=token)

@app.route('/submit_classic_survey', methods=['POST'])
@rate_limit(limit=10)
def submit_classic_survey():
    """Handle classic survey form submission"""
    try:
        from models import SurveyResponse, Campaign, CampaignParticipant
        import json
        
        # Check authentication
        if not session.get('auth_token'):
            flash('Authentication required', 'error')
            return redirect(url_for('server_auth'))
        
        authenticated_email = session.get('auth_email')
        if not authenticated_email:
            flash('Authentication session expired', 'error')
            return redirect(url_for('server_auth'))
        
        data = request.form.to_dict()
        
        # Get campaign data from session
        association_id = session.get('association_id')
        campaign_id = session.get('campaign_id')
        campaign = Campaign.query.get(campaign_id) if campaign_id else None
        
        # === Section 1: NPS & Driver Attribution ===
        if not data.get('nps_score') and data.get('nps_score') != '0':
            flash('NPS score is required.', 'error')
            token = session.get('auth_token', request.form.get('token', ''))
            return redirect(url_for('classic_survey', token=token))
        
        nps_score = int(data.get('nps_score', 0))
        if nps_score < 0 or nps_score > 10:
            flash('NPS score must be between 0 and 10.', 'error')
            token = session.get('auth_token', request.form.get('token', ''))
            return redirect(url_for('classic_survey', token=token))
        
        if nps_score >= 9:
            nps_category = 'Promoter'
        elif nps_score >= 7:
            nps_category = 'Passive'
        else:
            nps_category = 'Detractor'
        
        # Collect selected drivers (checkboxes come as separate form fields)
        selected_drivers = request.form.getlist('drivers')
        other_driver = data.get('driver_other_text', '').strip()
        if other_driver:
            selected_drivers.append(f'other:{other_driver}')
        
        # Open text fields
        driver_explanation = data.get('driver_explanation', '').strip()
        improvement_feedback = data.get('improvement_feedback', '').strip()
        
        # CSAT and CES
        csat_score = int(data.get('csat_score', 0)) if data.get('csat_score') else None
        ces_score = int(data.get('ces_score', 0)) if data.get('ces_score') else None
        
        # === Section 2: Feature Evaluation ===
        feature_evaluations = {}
        feature_keys = [k.replace('feature_usage_', '') for k in data.keys() if k.startswith('feature_usage_')]
        for fkey in feature_keys:
            feature_evaluations[fkey] = {
                'usage': data.get(f'feature_usage_{fkey}'),
                'frequency': data.get(f'feature_frequency_{fkey}'),
                'importance': data.get(f'feature_importance_{fkey}'),
                'satisfaction': int(data.get(f'feature_satisfaction_{fkey}', 0)) if data.get(f'feature_satisfaction_{fkey}') else None
            }
        
        # === Section 3: Additional Insights ===
        most_valuable_feature = data.get('most_valuable_feature', '').strip()
        most_improvement_needed = data.get('most_improvement_needed', '').strip()
        biggest_pain_point = data.get('biggest_pain_point', '').strip()
        missing_features = data.get('missing_features', '').strip()
        recommendation_status = data.get('recommendation_status', '').strip() or None
        recommendation_blocker = data.get('recommendation_blocker', '').strip()
        
        # Prepare response data for potential anonymization
        response_data = {
            'company_name': normalize_company_name(data.get('participant_company', '')),
            'respondent_name': data.get('participant_name', ''),
            'respondent_email': authenticated_email
        }
        
        # Apply anonymization if campaign requires it
        response_data = anonymize_response_data(campaign, response_data)
        
        # Build additional_comments as combined Section 3 insights
        section_3_parts = []
        if most_valuable_feature:
            section_3_parts.append(f"Most valuable feature: {most_valuable_feature}")
        if most_improvement_needed:
            section_3_parts.append(f"Needs most improvement: {most_improvement_needed}")
        if biggest_pain_point:
            section_3_parts.append(f"Biggest pain point: {biggest_pain_point}")
        if missing_features:
            section_3_parts.append(f"Missing features: {missing_features}")
        if recommendation_blocker:
            section_3_parts.append(f"Recommendation blocker: {recommendation_blocker}")
        additional_comments = '\n\n'.join(section_3_parts) if section_3_parts else None
        
        # Get participant tenure from database
        participant_id = session.get('participant_id')
        tenure_category = None
        if participant_id:
            from models import Participant
            participant = Participant.query.get(participant_id)
            if participant and hasattr(participant, 'tenure_years') and participant.tenure_years is not None:
                tenure_category = map_tenure_years_to_category(participant.tenure_years)
        
        # Ensure association_id is available (fallback lookup for re-entry via fresh session)
        if not association_id and campaign_id and authenticated_email:
            association_id = lookup_association_id_fallback(authenticated_email, campaign_id)
            if association_id:
                session['association_id'] = association_id
                logger.info(f"Classic survey: recovered association_id {association_id} via fallback lookup")
        
        # Upsert: look up existing response to update instead of creating duplicates
        existing_response = None
        if association_id:
            existing_response = SurveyResponse.query.filter_by(
                campaign_participant_id=association_id
            ).first()
        if not existing_response and campaign_id and authenticated_email:
            existing_response = SurveyResponse.query.filter_by(
                respondent_email=authenticated_email,
                campaign_id=campaign_id
            ).first()
        
        if existing_response:
            logger.info(f"Classic survey: updating existing response {existing_response.id} (resubmission)")
            existing_response.company_name = response_data['company_name']
            existing_response.respondent_name = response_data['respondent_name']
            existing_response.respondent_email = response_data['respondent_email']
            existing_response.tenure_with_fc = tenure_category
            existing_response.nps_score = nps_score
            existing_response.nps_category = nps_category
            existing_response.source_type = 'traditional'
            existing_response.satisfaction_rating = csat_score
            existing_response.csat_score = csat_score
            existing_response.ces_score = ces_score
            existing_response.loyalty_drivers = selected_drivers
            existing_response.recommendation_status = recommendation_status
            existing_response.recommendation_reason = driver_explanation
            existing_response.improvement_feedback = improvement_feedback
            existing_response.additional_comments = additional_comments
            existing_response.general_feedback = json.dumps(feature_evaluations) if feature_evaluations else None
            if campaign_id:
                existing_response.campaign_id = campaign_id
            if association_id:
                existing_response.campaign_participant_id = association_id
            existing_response.updated_at = datetime.utcnow()
            existing_response.analyzed_at = None
            response = existing_response
        else:
            response = SurveyResponse(
                company_name=response_data['company_name'],
                respondent_name=response_data['respondent_name'],
                respondent_email=response_data['respondent_email'],
                tenure_with_fc=tenure_category,
                nps_score=nps_score,
                nps_category=nps_category,
                source_type='traditional',
                satisfaction_rating=csat_score,
                csat_score=csat_score,
                ces_score=ces_score,
                loyalty_drivers=selected_drivers,
                recommendation_status=recommendation_status,
                recommendation_reason=driver_explanation,
                improvement_feedback=improvement_feedback,
                additional_comments=additional_comments,
                general_feedback=json.dumps(feature_evaluations) if feature_evaluations else None,
                campaign_id=campaign_id,
                campaign_participant_id=association_id
            )
            db.session.add(response)
        
        db.session.commit()
        
        # Bust dashboard cache so the next Executive Summary load reflects fresh data
        if campaign_id:
            try:
                from data_storage import bust_dashboard_cache
                classic_ba_id = campaign.business_account_id if campaign else None
                if classic_ba_id:
                    bust_dashboard_cache(campaign_id, classic_ba_id, company_name=response.company_name)
            except Exception as cache_bust_err:
                logger.warning(f"Cache bust failed after classic survey submit: {cache_bust_err}")
        
        # Mark association as completed
        if association_id:
            try:
                import campaign_participant_token_system
                campaign_participant_token_system.mark_survey_completed(association_id, response.id)
            except Exception as e:
                logger.error(f"Failed to mark association completed: {e}")
        
        # Queue AI analysis
        try:
            add_analysis_task(response.id)
            analysis_status = "queued"
        except Exception as e:
            logger.error(f"Failed to queue AI analysis for classic survey: {e}")
            analysis_status = "failed"
        
        # Capture context before invalidating session
        business_account_id = session.get('business_account_id')
        participant_name = data.get('participant_name', '').strip()
        campaign_name_display = campaign.name if campaign else None
        custom_end_message = campaign.custom_end_message if campaign and hasattr(campaign, 'custom_end_message') else None
        campaign_lang = campaign.language_code if campaign and hasattr(campaign, 'language_code') else 'en'
        branding = get_branding_context(business_account_id)
        
        # Explicitly set locale to campaign language for the completion page
        session['language'] = campaign_lang
        from flask_babel import refresh as babel_refresh
        babel_refresh()
        
        # Invalidate token
        session.pop('auth_token', None)
        session.pop('auth_email', None)
        session.permanent = False
        logger.info(f"Classic survey submitted by {authenticated_email} - Token invalidated")
        
        return render_template('classic_survey.html',
                             survey_completed=True,
                             participant_name=participant_name,
                             campaign_name=campaign_name_display,
                             custom_end_message=custom_end_message,
                             branding=branding,
                             authenticated=False,
                             email=authenticated_email,
                             campaign=campaign,
                             classic_config=None,
                             driver_labels=[],
                             features=[],
                             sections_enabled={'section_1': False, 'section_2': False, 'section_3': False},
                             lang=campaign_lang,
                             token=None,
                             preview_mode=False)
        
    except Exception as e:
        logger.error(f"Error in classic survey submission: {e}")
        db.session.rollback()
        flash(f'Survey submission failed. Please try again.', 'error')
        token = session.get('auth_token', request.form.get('token', ''))
        return redirect(url_for('classic_survey', token=token))

@app.route('/submit_survey', methods=['POST'])
@rate_limit(limit=10)  # 10 survey submissions per minute per IP
def submit_survey():
    """Handle authenticated survey submission and prevent duplicates"""
    try:
        # Import models to avoid circular imports
        from models import SurveyResponse, Campaign
        # Check if user is authenticated via session
        if not session.get('auth_token'):
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_ERROR'}), 401
            
        # Accept both JSON and form data
        if request.content_type and 'application/json' in request.content_type:
            data = request.json
        else:
            data = request.form.to_dict()
            
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get authenticated email from session
        authenticated_email = session.get('auth_email')
        
        if not authenticated_email:
            return jsonify({'error': 'Authentication failed'}), 401
        
        # Validate required fields
        required_fields = ['company_name', 'respondent_name', 'nps_score']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Determine NPS category
        nps_score = int(data['nps_score'])
        satisfaction_rating_value = data.get('satisfaction_rating')
        
        # CRITICAL DEBUG LOGGING - Track potential data swap bug
        logger.critical(f"🔍 SUBMIT_SURVEY - NPS received: {nps_score}, Satisfaction received: {satisfaction_rating_value}")
        logger.critical(f"🔍 SUBMIT_SURVEY - Full data: {data}")
        
        if nps_score >= 9:
            nps_category = 'Promoter'
        elif nps_score >= 7:
            nps_category = 'Passive'
        else:
            nps_category = 'Detractor'
        
        # Get campaign and association data from session (new system)
        association_id = session.get('association_id')
        campaign_id = session.get('campaign_id')
        
        # Fallback to active campaign for backward compatibility (old system)
        campaign = None
        if not campaign_id:
            demo_account = BusinessAccount.query.filter_by(name='Archelo Group inc').first()
            if demo_account:
                active_campaigns = Campaign.get_active_campaigns(demo_account.id)
                active_campaign = active_campaigns[0] if active_campaigns else None
            else:
                active_campaign = None
            campaign_id = active_campaign.id if active_campaign else None
            campaign = active_campaign
        else:
            campaign = Campaign.query.get(campaign_id)
        
        # Prepare response data for potential anonymization
        response_data = {
            'company_name': normalize_company_name(data['company_name']),
            'respondent_name': data['respondent_name'],
            'respondent_email': authenticated_email
        }
        
        # Apply anonymization if campaign requires it
        response_data = anonymize_response_data(campaign, response_data)
        
        # CRITICAL FIX: Smart lookup to prevent cross-campaign corruption while preserving analytics
        # Priority: campaign_participant_id (durable invite ID) > (email, campaign_id) for legacy
        existing_response = None
        if association_id:
            # New system: Use campaign_participant_id (one response per invitation)
            existing_response = SurveyResponse.query.filter_by(
                campaign_participant_id=association_id
            ).first()
        elif campaign_id:
            # Legacy system: Use (email, campaign_id) to prevent cross-campaign corruption
            existing_response = SurveyResponse.query.filter_by(
                respondent_email=authenticated_email,
                campaign_id=campaign_id
            ).first()
        
        # Resolve tenure: use form-submitted value; fall back to participant profile
        tenure_with_fc_route2 = data.get('tenure_with_fc')
        if not tenure_with_fc_route2:
            participant_id_route2 = session.get('participant_id')
            if participant_id_route2:
                from models import Participant
                participant_route2 = Participant.query.get(participant_id_route2)
                if participant_route2 and hasattr(participant_route2, 'tenure_years') and participant_route2.tenure_years is not None:
                    tenure_with_fc_route2 = map_tenure_years_to_category(participant_route2.tenure_years)

        if existing_response:
            # Update existing response (maintains one-row-per-campaign for analytics)
            existing_response.company_name = response_data['company_name']
            existing_response.respondent_name = response_data['respondent_name']
            existing_response.tenure_with_fc = tenure_with_fc_route2
            existing_response.nps_score = nps_score
            existing_response.nps_category = nps_category
            existing_response.satisfaction_rating = int(data['satisfaction_rating']) if data.get('satisfaction_rating') else None
            existing_response.product_value_rating = int(data['product_value_rating']) if data.get('product_value_rating') else None
            existing_response.service_rating = int(data['service_rating']) if data.get('service_rating') else None
            existing_response.pricing_rating = int(data['pricing_rating']) if data.get('pricing_rating') else None
            existing_response.improvement_feedback = data.get('improvement_feedback')
            existing_response.recommendation_reason = data.get('recommendation_reason')
            existing_response.additional_comments = data.get('additional_comments')
            if association_id:
                existing_response.campaign_participant_id = association_id
            existing_response.updated_at = datetime.utcnow()
            response = existing_response
        else:
            # Create new response
            response = SurveyResponse(
                company_name=response_data['company_name'],
                respondent_name=response_data['respondent_name'],
                respondent_email=response_data['respondent_email'],
                tenure_with_fc=tenure_with_fc_route2,
                nps_score=nps_score,
                nps_category=nps_category,
                satisfaction_rating=int(data['satisfaction_rating']) if data.get('satisfaction_rating') else None,
                product_value_rating=int(data['product_value_rating']) if data.get('product_value_rating') else None,
                service_rating=int(data['service_rating']) if data.get('service_rating') else None,
                pricing_rating=int(data['pricing_rating']) if data.get('pricing_rating') else None,
                improvement_feedback=data.get('improvement_feedback'),
                recommendation_reason=data.get('recommendation_reason'),
                additional_comments=data.get('additional_comments'),
                campaign_id=campaign_id,
                campaign_participant_id=association_id
            )
            
            # Ensure trial participant exists and is associated with campaign
            if campaign_id and not association_id:
                # This is a trial user completing via public survey - create participant record
                try:
                    participant, campaign_association = ensure_trial_participant(
                        email=authenticated_email,
                        name=data['respondent_name'],
                        company_name=data['company_name'],
                        campaign_id=campaign_id
                    )
                    
                    # Link response to the campaign participant association
                    response.campaign_participant_id = campaign_association.id
                    
                    # Mark association as completed
                    campaign_association.status = 'completed'
                    campaign_association.completed_at = datetime.utcnow()
                    
                    logger.info(f"Trial participant created and linked: {participant.email} -> campaign {campaign_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to create trial participant: {e}")
                    # Continue without participant linkage to maintain backward compatibility
            
            db.session.add(response)
        
        # Mark association as completed if using new token system (BEFORE commit for atomicity)
        # Fallback: Look up association_id from database if missing from session
        if not association_id and campaign_id and authenticated_email:
            association_id = lookup_association_id_fallback(authenticated_email, campaign_id)
            if association_id:
                # Also link the response to the association
                response.campaign_participant_id = association_id
        
        # Update association status BEFORE commit (atomic transaction like trial users)
        # Use helper function with auto_commit=False to preserve audit trail and future extensibility
        if association_id:
            try:
                import campaign_participant_token_system
                campaign_participant_token_system.mark_survey_completed(
                    association_id, 
                    response.id, 
                    auto_commit=False  # Atomic: commit together with response
                )
            except Exception as e:
                logger.error(f"Failed to mark association completed: {e}")
        
        # Single atomic commit for both response and status update
        db.session.commit()
        
        # Bust dashboard cache so the next Executive Summary load reflects fresh data
        if campaign_id:
            try:
                from data_storage import bust_dashboard_cache
                campaign_ba_id = campaign.business_account_id if campaign else None
                if campaign_ba_id:
                    bust_dashboard_cache(campaign_id, campaign_ba_id, company_name=response.company_name)
            except Exception as cache_bust_err:
                logger.warning(f"Cache bust failed after survey submit: {cache_bust_err}")
        
        # Queue AI analysis for background processing
        try:
            add_analysis_task(response.id)
            analysis_status = "queued"
        except Exception as e:
            logger.error(f"Failed to queue AI analysis: {e}")
            analysis_status = "failed"
        
        # AUTOMATIC TOKEN INVALIDATION - Clear session to prevent survey restarts
        # But preserve email for export functionality
        session['export_email'] = authenticated_email  # Preserve for export
        session.pop('auth_token', None)
        session.pop('auth_email', None)
        session.permanent = False  # Force session to be non-permanent for immediate effect
        print(f"=== TOKEN INVALIDATED FOR {authenticated_email} ===")
        logger.info(f"Survey submitted by authenticated user: {authenticated_email} - Token invalidated")
        
        return jsonify({
            'message': 'Survey submitted successfully - Token invalidated to prevent restart',
            'response_id': response.id,
            'analysis_status': analysis_status,
            'authenticated_email': authenticated_email,
            'token_invalidated': True
        })
        
    except Exception as e:
        logger.error(f"Error submitting survey: {e}")
        return jsonify({'error': 'Failed to submit survey'}), 500

@app.route('/submit_survey_overwrite', methods=['POST'])
@require_auth(allow_overwrite=True)  # Allow overwriting previous responses
@rate_limit(limit=5)  # Stricter limit for overwrites
def submit_survey_overwrite():
    """Handle survey submission with overwrite capability"""
    try:
        # Import models to avoid circular imports
        from models import SurveyResponse, Campaign
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Get authenticated email and existing response from Flask's g object
        authenticated_email = getattr(g, 'authenticated_email', None)
        existing_response = getattr(g, 'existing_response', None)
        
        if not authenticated_email:
            return jsonify({'error': 'Authentication failed'}), 401
        
        # Validate required fields
        required_fields = ['company_name', 'respondent_name', 'nps_score']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Determine NPS category
        nps_score = int(data['nps_score'])
        if nps_score >= 9:
            nps_category = 'Promoter'
        elif nps_score >= 7:
            nps_category = 'Passive'
        else:
            nps_category = 'Detractor'
        
        # Get active campaign for automatic assignment
        demo_account = BusinessAccount.query.filter_by(name='Archelo Group inc').first()
        if demo_account:
            active_campaigns = Campaign.get_active_campaigns(demo_account.id)
            active_campaign = active_campaigns[0] if active_campaigns else None
        else:
            active_campaign = None
        campaign_id = active_campaign.id if active_campaign else None
        
        # Prepare response data for potential anonymization
        response_data = {
            'company_name': normalize_company_name(data['company_name']),
            'respondent_name': data['respondent_name'],
            'respondent_email': authenticated_email
        }
        
        # Apply anonymization if campaign requires it
        response_data = anonymize_response_data(active_campaign, response_data)
        
        # Resolve tenure: use form-submitted value; fall back to participant profile
        tenure_with_fc_route3 = data.get('tenure_with_fc')
        if not tenure_with_fc_route3:
            participant_id_route3 = session.get('participant_id')
            if participant_id_route3:
                from models import Participant
                participant_route3 = Participant.query.get(participant_id_route3)
                if participant_route3 and hasattr(participant_route3, 'tenure_years') and participant_route3.tenure_years is not None:
                    tenure_with_fc_route3 = map_tenure_years_to_category(participant_route3.tenure_years)

        if existing_response:
            # Update existing response with potentially anonymized data
            existing_response.company_name = response_data['company_name']
            existing_response.respondent_name = response_data['respondent_name']
            existing_response.tenure_with_fc = tenure_with_fc_route3
            existing_response.nps_score = nps_score
            existing_response.nps_category = nps_category
            existing_response.satisfaction_rating = int(data['satisfaction_rating']) if data.get('satisfaction_rating') else None
            existing_response.product_value_rating = int(data['product_value_rating']) if data.get('product_value_rating') else None
            existing_response.service_rating = int(data['service_rating']) if data.get('service_rating') else None
            existing_response.pricing_rating = int(data['pricing_rating']) if data.get('pricing_rating') else None
            existing_response.improvement_feedback = data.get('improvement_feedback')
            existing_response.recommendation_reason = data.get('recommendation_reason')
            existing_response.additional_comments = data.get('additional_comments')
            existing_response.created_at = datetime.utcnow()  # Update timestamp
            existing_response.analyzed_at = None  # Reset analysis
            # Update campaign if there's an active one, otherwise preserve existing
            if campaign_id:
                existing_response.campaign_id = campaign_id
            
            response = existing_response
            action = "updated"
        else:
            # Create new response with potentially anonymized data
            response = SurveyResponse(
                company_name=response_data['company_name'],
                respondent_name=response_data['respondent_name'],
                respondent_email=response_data['respondent_email'],
                tenure_with_fc=tenure_with_fc_route3,
                nps_score=nps_score,
                nps_category=nps_category,
                satisfaction_rating=int(data['satisfaction_rating']) if data.get('satisfaction_rating') else None,
                product_value_rating=int(data['product_value_rating']) if data.get('product_value_rating') else None,
                service_rating=int(data['service_rating']) if data.get('service_rating') else None,
                pricing_rating=int(data['pricing_rating']) if data.get('pricing_rating') else None,
                improvement_feedback=data.get('improvement_feedback'),
                recommendation_reason=data.get('recommendation_reason'),
                additional_comments=data.get('additional_comments'),
                campaign_id=campaign_id
            )
            db.session.add(response)
            action = "created"
        
        db.session.commit()
        
        # Bust dashboard cache so the next Executive Summary load reflects fresh data
        if campaign_id:
            try:
                from data_storage import bust_dashboard_cache
                ow_campaign = active_campaign if active_campaign else Campaign.query.get(campaign_id)
                ow_ba_id = ow_campaign.business_account_id if ow_campaign else None
                if ow_ba_id:
                    bust_dashboard_cache(campaign_id, ow_ba_id, company_name=response.company_name)
            except Exception as cache_bust_err:
                logger.warning(f"Cache bust failed after overwrite survey submit: {cache_bust_err}")
        
        # Queue AI analysis for background processing
        try:
            add_analysis_task(response.id)
            analysis_status = "queued"
        except Exception as e:
            logger.error(f"Failed to queue AI analysis: {e}")
            analysis_status = "failed"
        
        logger.info(f"Survey {action} by authenticated user: {authenticated_email}")
        
        return jsonify({
            'message': f'Survey {action} successfully',
            'response_id': response.id,
            'analysis_status': analysis_status,
            'action': action,
            'authenticated_email': authenticated_email
        })
        
    except Exception as e:
        logger.error(f"Error submitting survey: {e}")
        return jsonify({'error': 'Failed to submit survey'}), 500

@app.route('/survey-response/<int:response_id>')
def public_survey_response(response_id):
    """Public route for viewing trial survey response details"""
    try:
        # Import models to avoid circular imports
        from models import SurveyResponse
        
        # Get the survey response by ID
        response = SurveyResponse.query.get_or_404(response_id)
        
        # Security check: Check if user is authenticated as business user first
        current_business_user = get_current_business_user()
        if current_business_user and response.campaign_participant_id is not None:
            # Business user trying to access a business response - verify ownership
            if response.campaign and response.campaign.business_account_id == current_business_user.business_account_id:
                # Business user owns this campaign - grant access
                logger.info(f"Business user {current_business_user.email} granted access to response {response_id}")
                response_data = response.to_dict()
                
                # DEBUG: Log what fields are in response_data
                logger.info(f"DEBUG response_data keys: {list(response_data.keys())}")
                logger.info(f"DEBUG analysis_summary present: {'analysis_summary' in response_data}")
                logger.info(f"DEBUG analysis_summary value: {response_data.get('analysis_summary')}")
                
                # Get business account branding
                business_account_id = current_business_user.business_account_id
                branding_context = get_branding_context(business_account_id)
                
                # Determine breadcrumb based on session or default to Campaign Insights for business users
                last_bi_page = session.get('last_bi_page', url_for('campaign_insights'))
                
                # Determine breadcrumb label based on the URL
                if 'executive-summary' in last_bi_page:
                    bi_label = 'Executive Summary'
                elif 'campaign-insights' in last_bi_page:
                    bi_label = 'Campaign Insights'
                else:
                    bi_label = 'Business Intelligence'
                
                # Get campaign information
                campaign_name = response.campaign.name if response.campaign else 'Unknown Campaign'
                
                return render_template('public_survey_response.html', 
                                     response=response_data,
                                     branding=branding_context,
                                     branding_context=branding_context,
                                     is_business_authenticated=True,
                                     bi_url=last_bi_page,
                                     bi_label=bi_label,
                                     campaign_name=campaign_name)
            else:
                # Business user doesn't own this campaign
                logger.warning(f"Business user {current_business_user.email} denied access to response {response_id} - not their campaign")
                flash('Vous n’avez pas l’autorisation d’afficher cette réponse à l’enquête.', 'error')
                return redirect(url_for('business_auth.business_analytics'))
        
        # Check if this is a trial response (public access allowed)
        if response.campaign_participant_id is not None:
            # This is a business response and user is not authenticated - redirect to login
            logger.warning(f"Access denied to business response {response_id} - redirecting to login")
            flash('Cette réponse à l’enquête nécessite une authentification. Veuillez vous connecter pour la consulter.', 'info')
            return redirect(url_for('business_auth.login'))
        
        # This is a trial response - allow public access
        logger.info(f"Public access granted to trial response {response_id}")
        
        # Convert response to dict for template
        response_data = response.to_dict()
        
        # DEBUG: Log what fields are in response_data
        logger.info(f"DEBUG response_data keys: {list(response_data.keys())}")
        logger.info(f"DEBUG analysis_summary present: {'analysis_summary' in response_data}")
        logger.info(f"DEBUG analysis_summary value: {response_data.get('analysis_summary')}")
        
        # Get demo branding for public view (Archelo Group - ID 1)
        branding_context = get_branding_context(business_account_id=1)
        
        # Determine breadcrumb based on session or default to Dashboard for trial users
        last_bi_page = session.get('last_bi_page', url_for('dashboard'))
        
        # Determine breadcrumb label based on the URL
        if 'executive-summary' in last_bi_page:
            bi_label = 'Executive Summary'
        elif 'campaign-insights' in last_bi_page:
            bi_label = 'Campaign Insights'
        else:
            bi_label = 'Business Intelligence'
        
        # For trial responses, campaign is None
        campaign_name = 'Trial Survey'
        
        return render_template('public_survey_response.html', 
                             response=response_data,
                             branding=branding_context,
                             branding_context=branding_context,
                             is_business_authenticated=False,
                             bi_url=last_bi_page,
                             bi_label=bi_label,
                             campaign_name=campaign_name)
    
    except Exception as e:
        logger.error(f"Error accessing survey response {response_id}: {e}")
        flash('Réponse à l’enquête introuvable ou indisponible.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Dashboard showing survey results and insights (unauthenticated demo users only)"""
    # Redirect authenticated users to Executive Summary
    current_business_user = get_current_business_user()
    if current_business_user is not None:
        logger.info(f"Authenticated user {current_business_user.email} redirected from /dashboard to /executive-summary")
        return redirect(url_for('executive_summary'))
    
    # Store this page as the last BI page for back navigation
    session['last_bi_page'] = url_for('dashboard')
    
    try:
        from data_storage import get_company_nps_data
        company_nps_data = get_company_nps_data()
    except Exception as e:
        logger.error(f"Error loading company NPS data for dashboard: {e}")
        company_nps_data = []
    
    # Only show user email if there's both token and email (active session)
    auth_email = session.get('auth_email')
    auth_token = session.get('auth_token')
    user_email = auth_email if (auth_token and auth_email) else None
    
    # This route is only for unauthenticated users (authenticated users redirected above)
    is_business_authenticated = False
    business_user_name = None
    
    # Unauthenticated demo user - get demo branding (Archelo Group - ID 1)
    branding_context = get_branding_context(business_account_id=1)
    
    return render_template('dashboard.html', 
                         company_nps_data=company_nps_data, 
                         user_email=user_email,
                         is_business_authenticated=is_business_authenticated,
                         business_user_name=business_user_name,
                         branding_context=branding_context)

@app.route('/dashboard/executive-summary')
@require_business_auth
def executive_summary():
    """Executive Summary - Strategic overview across all campaigns (Business users only)"""
    # Store this page as the last BI page for back navigation
    session['last_bi_page'] = url_for('executive_summary')
    
    # Get current business user
    current_business_user = get_current_business_user()
    if not current_business_user:
        logger.error("executive_summary: current_business_user is None despite @require_business_auth")
        # Phase B: Show clean session expired page instead of redirect
        from feature_flags import feature_flags
        if feature_flags.auth_soft_fallback_enabled:
            logger.warning("AUTH_SOFT_FALLBACK: Showing session expired page for executive_summary")
            return render_template('session_expired.html'), 401
        return redirect(url_for('business_auth.login'))
    
    business_user_name = f"{current_business_user.first_name} {current_business_user.last_name}"
    
    # Get branding context for authenticated business user
    business_account_id = current_business_user.business_account_id
    branding_context = get_branding_context(business_account_id)
    
    return render_template('executive_summary.html',
                         is_business_authenticated=True,
                         business_user_name=business_user_name,
                         business_user_id=current_business_user.id,
                         business_account_id=business_account_id,
                         branding_context=branding_context)

@app.route('/dashboard/campaign-insights')
@require_business_auth
def campaign_insights():
    """Campaign Insights - Operational analytics with campaign filtering (Business users only)"""
    # Store this page as the last BI page for back navigation
    campaign_id = request.args.get('campaign_id')
    if campaign_id:
        session['last_bi_page'] = url_for('campaign_insights') + f'?campaign_id={campaign_id}'
    else:
        session['last_bi_page'] = url_for('campaign_insights')
    
    try:
        from data_storage import get_company_nps_data
        company_nps_data = get_company_nps_data()
    except Exception as e:
        logger.error(f"Error loading company NPS data for campaign insights: {e}")
        company_nps_data = []
    
    # Get current business user
    current_business_user = get_current_business_user()
    if not current_business_user:
        logger.error("campaign_insights: current_business_user is None despite @require_business_auth")
        # Phase B: Show clean session expired page instead of redirect
        from feature_flags import feature_flags
        if feature_flags.auth_soft_fallback_enabled:
            logger.warning("AUTH_SOFT_FALLBACK: Showing session expired page for campaign_insights")
            return render_template('session_expired.html'), 401
        return redirect(url_for('business_auth.login'))
    
    business_user_name = f"{current_business_user.first_name} {current_business_user.last_name}"
    
    # Get branding context for authenticated business user
    business_account_id = current_business_user.business_account_id
    branding_context = get_branding_context(business_account_id)
    
    return render_template('campaign_insights.html',
                         company_nps_data=company_nps_data,
                         is_business_authenticated=True,
                         business_user_name=business_user_name,
                         business_user_id=current_business_user.id,
                         business_account_id=business_account_id,
                         branding_context=branding_context)

@app.route('/api/dashboard_data')
def dashboard_data():
    """API endpoint for dashboard data with optional campaign filtering"""
    try:
        # Import models to avoid circular imports
        from models import Campaign
        from data_storage import get_dashboard_data_cached
        from business_auth_routes import get_current_business_account
        
        # Get campaign filter parameter
        campaign_id = request.args.get('campaign_id', type=int)
        
        # Determine target business account: authenticated users see their data, public users see demo data
        current_account = get_current_business_account()
        if current_account:
            # Business user: scope to their account
            target_business_account_id = current_account.id
            account_context = f"business account {current_account.name}"
            logger.info(f"✅ Authenticated request - Business Account: {current_account.name} (ID: {target_business_account_id})")
        else:
            # Public user: scope to demo account (Archelo Group - ID 1)
            target_business_account_id = 1
            account_context = "demo account"
            logger.info(f"⚠️ Unauthenticated request - Defaulting to demo account (ID: 1)")
        
        # If campaign_id provided, validate it belongs to target business account
        if campaign_id:
            campaign = Campaign.query.filter_by(
                id=campaign_id, 
                business_account_id=target_business_account_id
            ).first()
            if not campaign:
                return jsonify({'error': 'Campaign not found or access denied'}), 404
        
        # If no campaign specified, default to active campaign for target business account
        if campaign_id is None:
            active_campaign = Campaign.query.filter_by(
                business_account_id=target_business_account_id,
                status='active'
            ).order_by(Campaign.id.desc()).first()
            if active_campaign:
                campaign_id = active_campaign.id
                logger.info(f"Survey Insights defaulting to {account_context} active campaign: {active_campaign.name} (ID: {campaign_id})")
        
        # SECURITY: Only call get_dashboard_data_cached with a valid campaign_id to prevent cross-account data leakage
        if campaign_id is not None:
            data = get_dashboard_data_cached(campaign_id=campaign_id, business_account_id=target_business_account_id)
        else:
            # No active campaign found - return empty dashboard data
            logger.info(f"No active campaign found for {account_context} - returning empty dashboard")
            data = {
                'total_responses': 0,
                'nps_score': 0,
                'promoters': 0,
                'passives': 0,
                'detractors': 0,
                'recent_responses': 0,
                'sentiment_distribution': [],
                'nps_distribution': [],
                'top_themes': [],
                'theme_trends': [],
                'churn_risk_data': [],
                'tenure_nps_data': [],
                'growth_factors': []
            }
        
        # Add campaign context to response for UI display
        if campaign_id:
            campaign = Campaign.query.filter_by(
                id=campaign_id,
                business_account_id=target_business_account_id
            ).first()
            if campaign:
                data['active_campaign'] = {
                    'id': campaign.id,
                    'name': campaign.name,
                    'status': campaign.status,
                    'start_date': campaign.start_date.isoformat(),
                    'end_date': campaign.end_date.isoformat(),
                    'days_remaining': campaign.days_remaining(),
                    'days_since_ended': campaign.days_since_ended(),
                    'survey_type': getattr(campaign, 'survey_type', 'conversational')
                }
        
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500

@app.route('/api/survey_responses')
def survey_responses():
    """API endpoint for survey responses with pagination and search (supports public demo mode)"""
    try:
        # Import models to avoid circular imports
        from models import SurveyResponse, Campaign
        from business_auth_routes import get_current_business_account
        
        # Determine target business account: authenticated users see their data, public users see demo data
        current_account = get_current_business_account()
        if current_account:
            # Business user: scope to their account
            target_business_account_id = current_account.id
        else:
            # Public user: scope to demo account (Archelo Group - ID 1)
            target_business_account_id = 1
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Max 100 per page
        search_query = request.args.get('search', '').strip()
        nps_category = request.args.get('nps_category', '').strip().lower()
        campaign_id = request.args.get('campaign', type=int)
        
        logger.info(f"📊 /api/survey_responses called - campaign_id: {campaign_id}, page: {page}, search: '{search_query}'")
        
        # Base query with business account scoping via campaign relationship
        query = SurveyResponse.query.join(Campaign).filter(
            Campaign.business_account_id == target_business_account_id
        ).options(
            joinedload(SurveyResponse.campaign)
        )
        
        # Apply campaign filter (CRITICAL: NPS must be campaign-specific)
        if campaign_id:
            query = query.filter(SurveyResponse.campaign_id == campaign_id)
        
        # Apply search filter if provided
        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                db.or_(
                    SurveyResponse.company_name.ilike(search_term),
                    SurveyResponse.respondent_name.ilike(search_term),
                    SurveyResponse.respondent_email.ilike(search_term)
                )
            )
        
        # Apply NPS category filter if provided
        if nps_category:
            if nps_category == 'promoters':
                query = query.filter(SurveyResponse.nps_score >= 9)
            elif nps_category == 'passives':
                query = query.filter(SurveyResponse.nps_score.between(7, 8))
            elif nps_category == 'detractors':
                query = query.filter(SurveyResponse.nps_score <= 6)
        
        pagination = query.order_by(
            SurveyResponse.created_at.desc()
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False,
            max_per_page=100
        )
        
        # Convert responses to dict and add can_view flag
        responses_data = []
        for response in pagination.items:
            response_dict = response.to_dict()
            
            # Determine if current user can view this response
            if current_account:
                # Business user can view all responses from their campaigns
                response_dict['can_view'] = True
            elif response.campaign_participant_id is None:
                # Public user can view trial responses only
                response_dict['can_view'] = True
            else:
                # Public user cannot view business responses
                response_dict['can_view'] = False
            
            responses_data.append(response_dict)
        
        return jsonify({
            'responses': responses_data,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'search_query': search_query
        })
    except Exception as e:
        logger.error(f"Error fetching survey responses: {e}")
        return jsonify({'error': 'Failed to fetch survey responses'}), 500

@app.route('/api/export_data')
@require_business_auth
@require_permission('export_data')
def export_data():
    """Export survey data as JSON - Admin access required, scoped to current business account"""
    try:
        # Get current business account
        current_account = get_current_business_account()
        if not current_account:
            logger.error("Export failed: Business account not found in session")
            return jsonify({'error': 'Business account not found'}), 401
        
        logger.info(f"Export initiated by business account {current_account.id} ({current_account.name})")
        
        # Query responses filtered by business account via campaign relationship
        responses = SurveyResponse.query.join(
            Campaign, SurveyResponse.campaign_id == Campaign.id
        ).filter(
            Campaign.business_account_id == current_account.id
        ).options(
            joinedload(SurveyResponse.campaign)
        ).all()
        
        logger.info(f"Export query returned {len(responses)} responses for business account {current_account.id}")
        
        data = [response.to_dict() for response in responses]
        
        # Get current user info
        current_user = get_current_business_user()
        admin_email = current_user.email if current_user else session.get('business_email', 'unknown')
        admin_name = current_user.get_full_name() if current_user else 'Unknown'
        
        # Create audit trail entry
        try:
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='data_exported',
                resource_type='survey_responses',
                resource_name='All Survey Data',
                user_email=admin_email,
                user_name=admin_name,
                details={
                    'total_responses': len(data),
                    'export_format': 'JSON',
                    'export_timestamp': datetime.utcnow().isoformat()
                }
            )
        except Exception as audit_error:
            logger.error(f"Failed to create audit log for data export: {audit_error}")
        
        logger.info(f"Admin data export completed by {admin_email} for business account {current_account.id}")
        
        return jsonify({
            'data': data,
            'export_info': {
                'total_responses': len(data),
                'business_account': current_account.name,
                'exported_by': admin_email,
                'export_timestamp': datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}", exc_info=True)
        return jsonify({'error': f'Failed to export data: {str(e)}'}), 500

@app.route('/api/queue_status')
def queue_status():
    """Get task queue status for monitoring"""
    try:
        stats = get_queue_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return jsonify({'error': 'Failed to get queue status'}), 500

# Campaign Export API Routes
@app.route('/api/campaigns/<int:campaign_id>/export', methods=['POST'])
@require_business_auth
def start_campaign_export(campaign_id):
    """Start asynchronous export for a campaign - Business users can export their own campaign data"""
    try:
        # Get current business account
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        # Verify campaign belongs to this business account
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Queue export task
        job_id = add_export_task(campaign_id, current_account.id)
        
        logger.info(f"Export started for campaign {campaign_id} by business account {current_account.id} (job_id: {job_id})")
        
        # Add audit log for export initiation
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='campaign_export_started',
                resource_type='campaign',
                resource_id=campaign_id,
                resource_name=campaign.name,
                details={
                    'job_id': job_id,
                    'export_type': 'campaign_data'
                }
            )
        except Exception as e:
            logger.error(f"Failed to log export audit event: {e}")
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Export started successfully',
            'campaign_name': campaign.name
        })
        
    except Exception as e:
        logger.error(f"Error starting campaign export: {e}")
        return jsonify({'error': 'Failed to start export'}), 500

@app.route('/api/export-jobs/<job_id>/status', methods=['GET'])
@require_business_auth
def get_export_status(job_id):
    """Get status of an export job"""
    try:
        # Get current business account
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        # Get job status
        job_status = get_export_job_status(job_id)
        
        if not job_status:
            return jsonify({'error': 'Export job not found'}), 404
        
        # Verify job belongs to this business account
        if job_status['business_account_id'] != current_account.id:
            return jsonify({'error': 'Export job not found'}), 404
        
        # Prepare response data (dates are already ISO formatted from to_dict())
        response_data = {
            'job_id': job_status['job_id'],
            'status': job_status['status'],
            'created_at': job_status['created_at'],
            'updated_at': job_status['updated_at'],
            'progress': job_status.get('progress'),
            'error': job_status.get('error')
        }
        
        # Add download URL if completed
        if job_status['status'] == 'completed' and job_status.get('file_path'):
            response_data['download_url'] = url_for('download_export_file', job_id=job_id)
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting export status: {e}")
        return jsonify({'error': 'Failed to get export status'}), 500

@app.route('/api/export-files/<job_id>/download', methods=['GET'])
@require_business_auth
def download_export_file(job_id):
    """Download completed export file"""
    try:
        # Get current business account
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        # Get job status
        job_status = get_export_job_status(job_id)
        
        if not job_status:
            return jsonify({'error': 'Export job not found'}), 404
        
        # Verify job belongs to this business account
        if job_status['business_account_id'] != current_account.id:
            return jsonify({'error': 'Export job not found'}), 404
        
        # Check if export is completed
        if job_status['status'] != 'completed':
            return jsonify({'error': f"Export not ready. Status: {job_status['status']}"}), 400
        
        # Check if file exists
        file_path = job_status.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'Export file not found'}), 404
        
        # Get campaign name for filename
        campaign = Campaign.query.filter_by(
            id=job_status['campaign_id'],
            business_account_id=current_account.id
        ).first()
        
        campaign_name = campaign.name if campaign else f"campaign_{job_status['campaign_id']}"
        
        # Create safe filename
        safe_campaign_name = re.sub(r'[^\w\s-]', '', campaign_name).strip()
        safe_campaign_name = re.sub(r'[-\s]+', '-', safe_campaign_name)
        download_filename = f"campaign_export_{safe_campaign_name}_{job_id[:8]}.json"
        
        logger.info(f"Export file downloaded: {file_path} by business account {current_account.id}")
        
        # Add audit log for export download
        try:
            from audit_utils import queue_audit_log
            queue_audit_log(
                business_account_id=current_account.id,
                action_type='campaign_export_downloaded',
                resource_type='campaign',
                resource_id=job_status['campaign_id'],
                resource_name=campaign_name,
                details={
                    'job_id': job_id,
                    'file_name': download_filename,
                    'export_type': 'campaign_data'
                }
            )
        except Exception as e:
            logger.error(f"Failed to log export download audit event: {e}")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/json'
        )
        
    except Exception as e:
        logger.error(f"Error downloading export file: {e}")
        return jsonify({'error': 'Failed to download export file'}), 500

@app.route('/api/campaigns/active', methods=['GET'])
def get_active_campaign():
    """Get the currently active campaign(s).
    
    Returns single campaign for backward compatibility.
    When business_account_id is provided and account has parallel campaigns enabled,
    also includes all_active_campaigns list.
    """
    try:
        client_identifier = 'archelo_group'  # Current single-client setup
        business_account_id = request.args.get('business_account_id', type=int)
        
        # Get single active campaign (backward compatible)
        campaign = Campaign.get_active_campaign(client_identifier)
        
        response_data = {
            'active_campaign': campaign.to_dict() if campaign else None,
            'has_active_campaign': campaign is not None
        }
        
        # If business_account_id provided, check for parallel campaigns support
        if business_account_id:
            account = BusinessAccount.query.get(business_account_id)
            if account and account.allow_parallel_campaigns:
                all_active = Campaign.get_active_campaigns(business_account_id)
                response_data['all_active_campaigns'] = [c.to_dict() for c in all_active]
                response_data['parallel_campaigns_enabled'] = True
                response_data['active_campaign_count'] = len(all_active)
        
        if not campaign:
            response_data['message'] = 'No active campaign found'
            
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error getting active campaign: {e}")
        return jsonify({'error': 'Failed to get active campaign'}), 500


@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connectivity
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        
        # Check task queue
        queue_stats = get_queue_stats()
        
        # Basic metrics
        total_responses = SurveyResponse.query.count()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'database': 'connected',
            'task_queue': queue_stats,
            'total_responses': total_responses,
            'version': '1.0.0'
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@app.route('/api/company_nps')
@rate_limit(limit=100)
def api_company_nps():
    """API endpoint for company-segregated NPS data with pagination, search, and filtering - OPTIMIZED to eliminate N+1 queries"""
    try:
        from models import SurveyResponse, Campaign
        from sqlalchemy import func, case
        from sqlalchemy.sql import label
        from business_auth_routes import get_current_business_account
        
        # Get pagination and filter parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Max 100 per page
        search_query = request.args.get('search', '').strip()
        nps_category = request.args.get('nps_category', '').strip().lower()
        campaign_id = request.args.get('campaign', type=int)
        
        logger.info(f"📊 /api/company_nps called - campaign_id: {campaign_id}, page: {page}, search: '{search_query}'")
        
        # SECURITY: Determine target business account to enforce multi-tenant isolation
        current_account = get_current_business_account()
        if current_account:
            target_business_account_id = current_account.id
            account_context = f"business account {current_account.name}"
        else:
            target_business_account_id = 1
            account_context = "demo account"
        
        # SECURITY: If no campaign specified, default to active campaign for target business account
        if campaign_id is None:
            active_campaign = Campaign.query.filter_by(
                business_account_id=target_business_account_id,
                status='active'
            ).order_by(Campaign.id.desc()).first()
            if active_campaign:
                campaign_id = active_campaign.id
                logger.info(f"📊 /api/company_nps defaulting to {account_context} active campaign: {active_campaign.name} (ID: {campaign_id})")
            else:
                logger.info(f"📊 /api/company_nps - No active campaign for {account_context}, returning empty data")
                return jsonify({
                    'success': True,
                    'data': [],
                    'pagination': {
                        'page': 1,
                        'per_page': per_page,
                        'total': 0,
                        'pages': 1,
                        'has_prev': False,
                        'has_next': False
                    }
                })
        
        # SECURITY: Validate campaign belongs to target business account (runs AFTER defaulting)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=target_business_account_id
        ).first()
        if not campaign:
            logger.warning(f"🔒 /api/company_nps - Campaign {campaign_id} access denied for {account_context}")
            return jsonify({'error': 'Campaign not found or access denied'}), 404
        
        # Step 1: Create subquery to get latest churn risk per company (SINGLE QUERY)
        # SECURITY: campaign_id is guaranteed to be set by security check above
        latest_churn_subquery = db.session.query(
            func.upper(SurveyResponse.company_name).label('company_upper'),
            SurveyResponse.churn_risk_level,
            func.row_number().over(
                partition_by=func.upper(SurveyResponse.company_name),
                order_by=SurveyResponse.created_at.desc()
            ).label('rn')
        ).filter(
            SurveyResponse.company_name.isnot(None),
            SurveyResponse.campaign_id == campaign_id
        )
        
        latest_churn_subquery = latest_churn_subquery.subquery()
        
        # Step 2: Filter to get only latest (rn=1) records
        latest_churn = db.session.query(
            latest_churn_subquery.c.company_upper,
            latest_churn_subquery.c.churn_risk_level.label('latest_churn_risk')
        ).filter(
            latest_churn_subquery.c.rn == 1
        ).subquery()
        
        # Step 3: Build main query with aggregations
        # SECURITY: campaign_id is guaranteed to be set and validated against business account
        base_query = db.session.query(
            func.max(SurveyResponse.company_name).label('company_name'),
            func.upper(SurveyResponse.company_name).label('company_upper'),
            func.count(SurveyResponse.id).label('total_responses'),
            func.avg(SurveyResponse.nps_score).label('avg_nps'),
            func.max(SurveyResponse.created_at).label('latest_response'),
            func.count(func.nullif(SurveyResponse.nps_score >= 9, False)).label('promoters'),
            func.count(func.nullif(SurveyResponse.nps_score <= 6, False)).label('detractors')
        ).filter(
            SurveyResponse.company_name.isnot(None),
            SurveyResponse.campaign_id == campaign_id
        )
        
        # Apply search filter at database level
        if search_query:
            base_query = base_query.filter(
                func.upper(SurveyResponse.company_name).like(f'%{search_query.upper()}%')
            )
        
        # Apply NPS category filter at database level
        if nps_category:
            if nps_category == 'promoters':
                base_query = base_query.filter(SurveyResponse.nps_score >= 9)
            elif nps_category == 'passives':
                base_query = base_query.filter(SurveyResponse.nps_score.between(7, 8))
            elif nps_category == 'detractors':
                base_query = base_query.filter(SurveyResponse.nps_score <= 6)
        
        # Group by company
        base_query = base_query.group_by(func.upper(SurveyResponse.company_name))
        
        # Create subquery once
        company_stats_subq = base_query.subquery()
        
        # Step 4: Join with latest churn risk (LEFT JOIN to handle companies without churn risk)
        company_query = db.session.query(
            company_stats_subq.c.company_name,
            company_stats_subq.c.total_responses,
            company_stats_subq.c.avg_nps,
            company_stats_subq.c.latest_response,
            company_stats_subq.c.promoters,
            company_stats_subq.c.detractors,
            latest_churn.c.latest_churn_risk
        ).select_from(company_stats_subq).outerjoin(
            latest_churn,
            company_stats_subq.c.company_upper == latest_churn.c.company_upper
        )
        
        # Get all results in ONE QUERY
        company_stats = company_query.all()
        
        # Process results
        company_nps_list = []
        for company in company_stats:
            total = company.total_responses
            promoters = company.promoters or 0
            detractors = company.detractors or 0
            
            # Calculate company NPS
            company_nps = round(((promoters - detractors) / total) * 100) if total > 0 else 0
            
            # Determine risk level
            if company_nps <= -50:
                risk_level = "Critical"
            elif company_nps <= -20:
                risk_level = "High"
            elif company_nps <= 20:
                risk_level = "Medium"
            else:
                risk_level = "Low"
            
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
                'latest_churn_risk': company.latest_churn_risk
            })
        
        # Sort by risk level and NPS
        risk_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        company_nps_list.sort(key=lambda x: (risk_order.get(x['risk_level'], 4), -x['company_nps']))
        
        # Apply pagination
        total_companies = len(company_nps_list)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        company_data = company_nps_list[start_idx:end_idx]
        
        # Calculate pagination info
        total_pages = (total_companies + per_page - 1) // per_page if total_companies > 0 else 1
        has_prev = page > 1
        has_next = page < total_pages
        
        return jsonify({
            'success': True,
            'data': company_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_companies,
                'pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next
            }
        })
    except Exception as e:
        logger.error(f"Error getting company NPS data: {e}")
        return jsonify({'error': 'Failed to get company NPS data'}), 500

@app.route('/api/company_trends')
@rate_limit(limit=100) 
def api_company_trends():
    """API endpoint for company NPS trends"""
    try:
        from data_storage import get_company_trends
        company_trends = get_company_trends()
        return jsonify({
            'success': True,
            'data': company_trends
        })
    except Exception as e:
        logger.error(f"Error getting company trends: {e}")
        return jsonify({'error': 'Failed to get company trends'}), 500

@app.route('/api/tenure_nps')
@rate_limit(limit=100)
def api_tenure_nps():
    """API endpoint for tenure-segregated NPS data with pagination - OPTIMIZED to eliminate N+1 queries"""
    try:
        from models import SurveyResponse, Campaign
        from sqlalchemy import func
        from business_auth_routes import get_current_business_account
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Max 100 per page
        campaign_id = request.args.get('campaign', type=int)
        
        logger.info(f"📊 /api/tenure_nps called - campaign_id: {campaign_id}, page: {page}")
        
        # SECURITY: Determine target business account to enforce multi-tenant isolation
        current_account = get_current_business_account()
        if current_account:
            target_business_account_id = current_account.id
            account_context = f"business account {current_account.name}"
        else:
            target_business_account_id = 1
            account_context = "demo account"
        
        # SECURITY: If no campaign specified, default to active campaign for target business account
        if campaign_id is None:
            active_campaign = Campaign.query.filter_by(
                business_account_id=target_business_account_id,
                status='active'
            ).order_by(Campaign.id.desc()).first()
            if active_campaign:
                campaign_id = active_campaign.id
                logger.info(f"📊 /api/tenure_nps defaulting to {account_context} active campaign: {active_campaign.name} (ID: {campaign_id})")
            else:
                logger.info(f"📊 /api/tenure_nps - No active campaign for {account_context}, returning empty data")
                return jsonify({
                    'success': True,
                    'data': [],
                    'pagination': {
                        'page': 1,
                        'per_page': per_page,
                        'total': 0,
                        'pages': 1,
                        'has_prev': False,
                        'has_next': False
                    }
                })
        
        # SECURITY: Validate campaign belongs to target business account (runs AFTER defaulting)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=target_business_account_id
        ).first()
        if not campaign:
            logger.warning(f"🔒 /api/tenure_nps - Campaign {campaign_id} access denied for {account_context}")
            return jsonify({'error': 'Campaign not found or access denied'}), 404
        
        # Step 1: Create subquery to get latest churn risk per tenure group (SINGLE QUERY)
        # SECURITY: campaign_id is guaranteed to be set by security check above
        latest_churn_subquery = db.session.query(
            SurveyResponse.tenure_with_fc,
            SurveyResponse.churn_risk_level,
            func.row_number().over(
                partition_by=SurveyResponse.tenure_with_fc,
                order_by=SurveyResponse.created_at.desc()
            ).label('rn')
        ).filter(
            SurveyResponse.tenure_with_fc.isnot(None),
            SurveyResponse.campaign_id == campaign_id
        )
        
        latest_churn_subquery = latest_churn_subquery.subquery()
        
        # Step 2: Filter to get only latest (rn=1) records
        latest_churn = db.session.query(
            latest_churn_subquery.c.tenure_with_fc,
            latest_churn_subquery.c.churn_risk_level.label('latest_churn_risk')
        ).filter(
            latest_churn_subquery.c.rn == 1
        ).subquery()
        
        # Step 3: Build main query with aggregations
        # SECURITY: campaign_id is guaranteed to be set and validated against business account
        tenure_stats_query = db.session.query(
            SurveyResponse.tenure_with_fc,
            func.count(SurveyResponse.id).label('total_responses'),
            func.avg(SurveyResponse.nps_score).label('avg_nps'),
            func.max(SurveyResponse.created_at).label('latest_response'),
            func.count(func.nullif(SurveyResponse.nps_score >= 9, False)).label('promoters'),
            func.count(func.nullif(SurveyResponse.nps_score <= 6, False)).label('detractors')
        ).filter(
            SurveyResponse.tenure_with_fc.isnot(None),
            SurveyResponse.campaign_id == campaign_id
        )
        
        tenure_stats_subq = tenure_stats_query.group_by(SurveyResponse.tenure_with_fc).subquery()
        
        # Step 4: Join with latest churn risk (LEFT JOIN to handle tenure groups without churn risk)
        tenure_query = db.session.query(
            tenure_stats_subq.c.tenure_with_fc,
            tenure_stats_subq.c.total_responses,
            tenure_stats_subq.c.avg_nps,
            tenure_stats_subq.c.latest_response,
            tenure_stats_subq.c.promoters,
            tenure_stats_subq.c.detractors,
            latest_churn.c.latest_churn_risk
        ).select_from(tenure_stats_subq).outerjoin(
            latest_churn,
            tenure_stats_subq.c.tenure_with_fc == latest_churn.c.tenure_with_fc
        )
        
        # Get all results in ONE QUERY
        tenure_stats = tenure_query.all()
        
        # Process results
        tenure_nps_list = []
        for tenure in tenure_stats:
            total = tenure.total_responses
            promoters = tenure.promoters or 0
            detractors = tenure.detractors or 0
            
            # Calculate tenure NPS score
            tenure_nps = round(((promoters - detractors) / total) * 100) if total > 0 else 0
            
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
                'latest_churn_risk': tenure.latest_churn_risk
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
        
        # Apply pagination
        total_tenure_groups = len(tenure_nps_list)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        tenure_data = tenure_nps_list[start_idx:end_idx]
        
        # Calculate pagination info
        total_pages = (total_tenure_groups + per_page - 1) // per_page if total_tenure_groups > 0 else 1
        has_prev = page > 1
        has_next = page < total_pages
        
        return jsonify({
            'success': True,
            'data': tenure_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_tenure_groups,
                'pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next
            }
        })
    except Exception as e:
        logger.error(f"Error getting tenure NPS data: {e}")
        return jsonify({'error': 'Failed to get tenure NPS data'}), 500

@app.route('/api/account_intelligence')
@rate_limit(limit=100)
def api_account_intelligence():
    """API endpoint for Account Intelligence with pagination, search, and filtering"""
    try:
        from models import Campaign
        from data_storage import get_dashboard_data_cached
        from business_auth_routes import get_current_business_account
        
        # Get pagination and filter parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        search_query = request.args.get('search', '').strip().lower()
        balance_filter = request.args.get('balance', '').strip().lower()
        risk_level_filter = request.args.get('risk_level', '').strip().lower()
        has_opportunities = request.args.get('has_opportunities', '').strip().lower()
        has_risks = request.args.get('has_risks', '').strip().lower()
        min_responses = request.args.get('min_responses', type=int)
        campaign_id = request.args.get('campaign', type=int)
        
        logger.info(f"📊 /api/account_intelligence called - campaign_id: {campaign_id}, page: {page}")
        
        # SECURITY: Determine target business account to enforce multi-tenant isolation
        current_account = get_current_business_account()
        if current_account:
            target_business_account_id = current_account.id
            account_context = f"business account {current_account.name}"
        else:
            target_business_account_id = 1
            account_context = "demo account"
        
        # SECURITY: If no campaign specified, default to active campaign for target business account
        if campaign_id is None:
            active_campaign = Campaign.query.filter_by(
                business_account_id=target_business_account_id,
                status='active'
            ).order_by(Campaign.id.desc()).first()
            if active_campaign:
                campaign_id = active_campaign.id
                logger.info(f"📊 /api/account_intelligence defaulting to {account_context} active campaign: {active_campaign.name} (ID: {campaign_id})")
            else:
                logger.info(f"📊 /api/account_intelligence - No active campaign for {account_context}, returning empty data")
                return jsonify({
                    'success': True,
                    'data': [],
                    'pagination': {
                        'page': 1,
                        'per_page': per_page,
                        'total': 0,
                        'pages': 1,
                        'has_prev': False,
                        'has_next': False
                    }
                })
        
        # SECURITY: Validate campaign belongs to target business account (runs AFTER defaulting)
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=target_business_account_id
        ).first()
        if not campaign:
            logger.warning(f"🔒 /api/account_intelligence - Campaign {campaign_id} access denied for {account_context}")
            return jsonify({'error': 'Campaign not found or access denied'}), 404
        
        # Get dashboard data which includes account_intelligence (campaign_id now guaranteed and validated)
        # SECURITY: Pass business_account_id to enable segmentation analytics filtering
        dashboard_data = get_dashboard_data_cached(campaign_id=campaign_id, business_account_id=target_business_account_id)
        all_accounts = dashboard_data.get('account_intelligence', [])
        
        # Apply filters
        filtered_accounts = []
        for account in all_accounts:
            # Search filter - search company name, opportunities, and risk factors
            if search_query:
                company_match = search_query in account.get('company_name', '').lower()
                
                # Search in opportunities
                opp_match = any(
                    search_query in opp.get('type', '').lower()
                    for opp in account.get('opportunities', [])
                )
                
                # Search in risk factors
                risk_match = any(
                    search_query in risk.get('type', '').lower()
                    for risk in account.get('risk_factors', [])
                )
                
                if not (company_match or opp_match or risk_match):
                    continue
            
            # Balance filter
            if balance_filter and account.get('balance') != balance_filter:
                continue
            
            # Risk level filter (based on critical_risks count)
            if risk_level_filter:
                critical_count = account.get('critical_risks', 0)
                if risk_level_filter == 'critical' and critical_count == 0:
                    continue
                elif risk_level_filter == 'high' and critical_count < 2:
                    continue
                elif risk_level_filter == 'medium' and (critical_count > 1 or account.get('risk_count', 0) == 0):
                    continue
                elif risk_level_filter == 'low' and account.get('risk_count', 0) > 0:
                    continue
            
            # Has opportunities filter
            if has_opportunities == 'yes' and account.get('opportunity_count', 0) == 0:
                continue
            elif has_opportunities == 'no' and account.get('opportunity_count', 0) > 0:
                continue
            
            # Has risks filter
            if has_risks == 'yes' and account.get('risk_count', 0) == 0:
                continue
            elif has_risks == 'no' and account.get('risk_count', 0) > 0:
                continue
            
            # Minimum responses filter (if applicable)
            # Note: current structure doesn't have response count per company, skip for now
            
            filtered_accounts.append(account)
        
        # Apply pagination
        total_accounts = len(filtered_accounts)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_accounts = filtered_accounts[start_idx:end_idx]
        
        # Calculate pagination info
        total_pages = (total_accounts + per_page - 1) // per_page if total_accounts > 0 else 1
        has_prev = page > 1
        has_next = page < total_pages
        
        return jsonify({
            'success': True,
            'data': paginated_accounts,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_accounts,
                'pages': total_pages,
                'has_prev': has_prev,
                'has_next': has_next
            },
            'filters_applied': {
                'search': search_query if search_query else None,
                'balance': balance_filter if balance_filter else None,
                'risk_level': risk_level_filter if risk_level_filter else None,
                'has_opportunities': has_opportunities if has_opportunities else None,
                'has_risks': has_risks if has_risks else None
            }
        })
    except Exception as e:
        logger.error(f"Error getting account intelligence data: {e}")
        return jsonify({'error': 'Failed to get account intelligence data'}), 500

# Conversational Survey Routes
@app.route('/conversational_survey')
def conversational_survey():
    """AI-powered conversational survey page - check for token in URL"""
    token = request.args.get('token')
    if token:
        # Use centralized token verification (same as traditional survey)
        verification = verify_survey_access(token)
        if verification['valid']:
            # Store authentication data in session
            session['auth_token'] = token
            session['auth_email'] = verification['email']
            session['association_id'] = verification.get('association_id')
            session['campaign_id'] = verification.get('campaign_id')
            session['participant_id'] = verification.get('participant_id')
            session['business_account_id'] = verification.get('business_account_id')
            session['participant_name'] = verification.get('participant_name')
            session['campaign_name'] = verification.get('campaign_name')
            session['participant_company'] = verification.get('participant_company')
            
            # Route to appropriate template based on participant type
            participant_name = verification.get('participant_name')
            campaign_name = verification.get('campaign_name')
            business_account_id = verification.get('business_account_id')
            
            # Determine if this is a business participant
            is_business_authenticated = business_account_id is not None and business_account_id != 1
            
            # Get branding context
            if is_business_authenticated:
                branding_context = get_branding_context(business_account_id)
            else:
                # Trial user - get demo branding
                branding_context = get_branding_context(business_account_id=1)
            
            logger.info(f"Routing decision - participant_name: {participant_name}, campaign_name: {campaign_name}")
            
            if participant_name and campaign_name:
                # Business participant - use dedicated business template
                logger.info(f"✅ Using BUSINESS template for {participant_name}")
                # Get campaign details including dates and custom_end_message
                custom_end_message = None
                campaign_description = None
                campaign_start_date = None
                campaign_end_date = None
                campaign_id = session.get('campaign_id')
                if campaign_id:
                    from models import Campaign
                    campaign = Campaign.query.get(campaign_id)
                    if campaign:
                        custom_end_message = campaign.custom_end_message
                        campaign_description = campaign.description
                        campaign_start_date = campaign.start_date
                        campaign_end_date = campaign.end_date
                
                logger.info(f"🟢 RETURNING BUSINESS TEMPLATE NOW for {participant_name}")
                return render_template('conversational_survey_business.html',
                                     authenticated=verification['authenticated'],
                                     email=verification['email'],
                                     user_email=verification['email'],
                                     participant_name=participant_name,
                                     participant_company=verification.get('participant_company'),
                                     campaign_name=campaign_name,
                                     campaign_description=campaign_description,
                                     campaign_start_date=campaign_start_date,
                                     campaign_end_date=campaign_end_date,
                                     custom_end_message=custom_end_message,
                                     branding=branding_context,
                                     branding_context=branding_context,
                                     is_business_authenticated=is_business_authenticated)
            else:
                # Demo user - use existing template
                logger.info("🔴 RETURNING DEMO TEMPLATE NOW (no participant/campaign)")
                # Get campaign details for demo users too
                campaign_description = None
                campaign_end_date = None
                campaign_id = session.get('campaign_id')
                if campaign_id:
                    from models import Campaign
                    campaign = Campaign.query.get(campaign_id)
                    if campaign:
                        campaign_description = campaign.description
                        campaign_end_date = campaign.end_date
                
                return render_template('conversational_survey.html', 
                                     authenticated=verification['authenticated'], 
                                     email=verification['email'], 
                                     user_email=verification['email'],
                                     participant_name=participant_name,
                                     participant_company=verification.get('participant_company'),
                                     campaign_name=campaign_name,
                                     campaign_description=campaign_description,
                                     campaign_end_date=campaign_end_date,
                                     branding=branding_context,
                                     branding_context=branding_context,
                                     is_business_authenticated=False)
        else:
            # Fallback to simple token system for backward compatibility
            import simple_token_system
            fallback_verification = simple_token_system.verify_simple_token(token)
            if fallback_verification.get('valid'):
                email = fallback_verification.get('email')
                session['auth_token'] = token
                session['auth_email'] = email
                # Get demo branding for trial users
                branding_context = get_branding_context(business_account_id=1)
                return render_template('conversational_survey.html', 
                                     authenticated=True, 
                                     email=email, 
                                     user_email=email, 
                                     branding=branding_context,
                                     branding_context=branding_context,
                                     is_business_authenticated=False)
            else:
                # Token verification failed - render error page
                error_code = verification.get('error_code', 'invalid_token')
                branding_context = get_branding_context(business_account_id=1)
                return render_template('survey_unavailable.html',
                                     error_code=error_code,
                                     error_message=verification.get('error'),
                                     campaign_name=verification.get('campaign_name'),
                                     campaign_end_date=verification.get('campaign_end_date'),
                                     campaign_start_date=verification.get('campaign_start_date'),
                                     completed_at=verification.get('completed_at'),
                                     show_contact_info=True,
                                     branding=branding_context)
    else:
        # Check if already authenticated via session
        if session.get('auth_token'):
            email = session.get('auth_email')
            participant_name = session.get('participant_name')
            campaign_name = session.get('campaign_name')
            
            # Allow response updates - don't block existing responses
            # existing_response = SurveyResponse.query.filter_by(respondent_email=email).first()
            # if existing_response:
            #     # Show completion message instead of survey form
            #     # return render_template('conversational_survey_completed.html', 
            #                          email=email,
            #                          user_email=email,
            #                          completion_date=existing_response.created_at.strftime("%B %d, %Y"),
            #                          show_alternatives=True)
                                     
            # Determine if this is a business participant
            business_account_id = session.get('business_account_id')
            is_business_authenticated = business_account_id is not None and business_account_id != 1
            
            # Get branding context
            if is_business_authenticated:
                branding_context = get_branding_context(business_account_id)
            else:
                # Trial user - get demo branding
                branding_context = get_branding_context(business_account_id=1)
            
            # Route to appropriate template based on session data
            if participant_name and campaign_name:
                # Business participant - use dedicated business template
                logger.info(f"✅ Session-based: Using BUSINESS template for {participant_name}")
                # Get campaign details
                custom_end_message = None
                campaign_start_date = None
                campaign_end_date = None
                campaign_id = session.get('campaign_id')
                if campaign_id:
                    from models import Campaign
                    campaign = Campaign.query.get(campaign_id)
                    if campaign:
                        custom_end_message = campaign.custom_end_message
                        campaign_start_date = campaign.start_date
                        campaign_end_date = campaign.end_date
                
                return render_template('conversational_survey_business.html',
                                     authenticated=True,
                                     email=email,
                                     user_email=email,
                                     participant_name=participant_name,
                                     participant_company=session.get('participant_company'),
                                     campaign_name=campaign_name,
                                     campaign_start_date=campaign_start_date,
                                     campaign_end_date=campaign_end_date,
                                     custom_end_message=custom_end_message,
                                     branding=branding_context,
                                     branding_context=branding_context,
                                     is_business_authenticated=is_business_authenticated)
            else:
                # Demo user - use existing template
                logger.info("Session-based: Using DEMO template")
                return render_template('conversational_survey.html', 
                                     authenticated=True, 
                                     email=email, 
                                     user_email=email, 
                                     branding=branding_context,
                                     branding_context=branding_context,
                                     is_business_authenticated=False)
        else:
            # Redirect unauthenticated users to auth page instead of showing broken page
            return redirect(url_for('server_auth'))

@app.route('/api/start_conversation', methods=['POST'])
@rate_limit(limit=10)
def start_conversation():
    """Start a new conversational survey session"""
    try:
        # Check if user is authenticated via session
        if not session.get('auth_token'):
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_ERROR'}), 401
            
        data = request.get_json()
        company_name = data.get('company_name', '').strip()
        respondent_name = data.get('respondent_name', '').strip()
        respondent_email = data.get('respondent_email', '').strip()
        
        # Tenure is no longer required from form - will be looked up from participant data
        if not company_name or not respondent_name or not respondent_email:
            return jsonify({'error': 'Company name, name, and email are required'}), 400
        
        # Get business account ID and campaign ID from session for PromptTemplateService integration
        business_account_id = session.get('business_account_id')
        campaign_id = session.get('campaign_id')
        participant_id = session.get('participant_id')

        # Fallback for demo/simple-token users who have no campaign context in session
        # (simple_token_system only sets auth_token/auth_email — never campaign_id or business_account_id)
        if not business_account_id or not campaign_id:
            demo_account = BusinessAccount.query.filter_by(name='Archelo Group inc').first()
            if demo_account:
                if not business_account_id:
                    business_account_id = demo_account.id
                if not campaign_id:
                    active = Campaign.get_active_campaigns(demo_account.id)
                    campaign_id = active[0].id if active else None
            logger.info(f"Demo fallback applied — business_account_id: {business_account_id}, campaign_id: {campaign_id}")

        # Look up participant data if participant_id is available
        participant_data = None
        tenure_with_fc = None

        # Simulation mode: use session-stored participant_data instead of DB lookup
        if session.get('is_simulation') and session.get('participant_data'):
            participant_data = session.get('participant_data')
            logger.info(f"Simulation: loaded participant_data from session, role={participant_data.get('role')}")
        elif participant_id:
            participant = Participant.query.get(participant_id)
            if participant:
                # Build participant_data dictionary with segmentation attributes
                # FIX (Nov 23, 2025): Use participant_name/participant_company (token schema keys)
                # to match finalization expectations
                participant_data = {
                    'participant_name': participant.name,          # Token schema key
                    'participant_company': participant.company_name,  # Token schema key
                    'name': participant.name,                      # Legacy fallback
                    'email': participant.email,
                    'company_name': participant.company_name,      # Legacy fallback
                    'role': participant.role,
                    'region': participant.region,
                    'customer_tier': participant.customer_tier,
                    'language': participant.language
                }
                
                # Map tenure_years to categorical string if available
                if participant.tenure_years is not None:
                    tenure_with_fc = map_tenure_years_to_category(participant.tenure_years)
                    participant_data['tenure_with_fc'] = tenure_with_fc
                    logger.info(f"Pre-populated tenure from participant: {participant.tenure_years} years → '{tenure_with_fc}'")
                else:
                    logger.info(f"Participant {participant_id} has no tenure_years - AI will ask during conversation")
        
        # Debug logging
        logger.info(f"Starting conversation for {respondent_name}, business_account_id: {business_account_id}, campaign_id: {campaign_id}, participant_data: {bool(participant_data)}")
        
        # FEATURE FLAG: Deterministic Survey Flow V2  
        # Use module-level feature_flags instance for consistency across requests
        use_deterministic_v2 = feature_flags.is_feature_enabled('deterministic_survey_flow')
        
        if use_deterministic_v2:
            logger.info(f"🎯 Using DETERMINISTIC V2 controller for conversation")
            conversation_response = start_ai_conversational_survey_v2(
                company_name, 
                respondent_name, 
                tenure_with_fc, 
                business_account_id=business_account_id, 
                campaign_id=campaign_id,
                participant_data=participant_data
            )
        else:
            logger.info(f"Using legacy V1 controller for conversation")
            conversation_response = start_ai_conversational_survey(
                company_name, 
                respondent_name, 
                tenure_with_fc, 
                business_account_id=business_account_id, 
                campaign_id=campaign_id,
                participant_data=participant_data
            )
        
        return jsonify({
            'conversation_id': conversation_response['conversation_id'],
            'message': conversation_response['message'],
            'step': conversation_response['step'],
            'progress': conversation_response['progress'],
            'extracted_data': conversation_response.get('extracted_data', {}),
            'is_complete': conversation_response.get('is_complete', False)
        })
        
    except Exception as e:
        logger.error(f"Error starting conversation: {e}")
        return jsonify({'error': 'Failed to start conversation'}), 500

@app.route('/api/conversation_response', methods=['POST'])
@rate_limit(limit=50)
def conversation_response():
    """Process conversational survey response"""
    try:
        # Check if user is authenticated via session
        if not session.get('auth_token'):
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_ERROR'}), 401
            
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        user_input = data.get('user_input', '').strip()
        survey_data = data.get('survey_data', {})
        
        if not conversation_id or not user_input:
            return jsonify({'error': 'Conversation ID and user input are required'}), 400
        
        # Get authenticated email from session
        authenticated_email = session.get('auth_email')
        if not authenticated_email:
            return jsonify({'error': 'Authentication session expired', 'code': 'AUTH_ERROR'}), 401
        
        # Add authenticated email and conversation_id to survey data
        survey_data['respondent_email'] = authenticated_email
        survey_data['conversation_id'] = conversation_id
        # Add business_account_id and campaign_id for PromptTemplateService integration
        survey_data['business_account_id'] = session.get('business_account_id')
        survey_data['campaign_id'] = session.get('campaign_id')
        
        # FEATURE FLAG: Deterministic Survey Flow V2
        # Use module-level feature_flags instance for consistency across requests
        use_deterministic_v2 = feature_flags.is_feature_enabled('deterministic_survey_flow')
        
        if use_deterministic_v2:
            logger.debug(f"🎯 Using DETERMINISTIC V2 controller for response processing")
            ai_response = process_ai_conversation_response_v2(user_input, survey_data)
        else:
            logger.debug(f"Using legacy V1 controller for response processing")
            ai_response = process_ai_conversation_response(user_input, survey_data)
        
        return jsonify(ai_response)
        
    except Exception as e:
        logger.error(f"Error processing conversation response: {e}")
        return jsonify({'error': 'Failed to process response'}), 500

@app.route('/api/finalize_conversation', methods=['POST'])
@rate_limit(limit=20)
def finalize_conversation():
    """Finalize conversational survey and save to database"""
    try:
        # Import models to avoid circular imports
        from models import SurveyResponse, Campaign
        # Check if user is authenticated via session
        if not session.get('auth_token'):
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_ERROR'}), 401
            
        data = request.get_json()
        conversation_id = data.get('conversation_id')
        survey_data = data.get('survey_data', {})
        messages = data.get('messages', [])
        
        # Get authenticated email from session
        authenticated_email = session.get('auth_email')
        if not authenticated_email:
            return jsonify({'error': 'Authentication session expired', 'code': 'AUTH_ERROR'}), 401
        
        if not conversation_id:
            return jsonify({'error': 'Conversation ID is required'}), 400

        # SIMULATION MODE GUARD — no data written to survey_responses
        if session.get('is_simulation') is True:
            logger.info(f"Simulation finalization: running extraction only (no DB write) for {conversation_id}")

            survey_data['respondent_email'] = authenticated_email
            survey_data['conversation_id'] = conversation_id
            survey_data['conversation_history'] = json.dumps(messages)

            # Determine controller version from ActiveConversation
            from models import ActiveConversation
            sim_active_conv = ActiveConversation.query.filter_by(conversation_id=conversation_id).first()
            sim_controller_version = 'v1'
            if sim_active_conv and sim_active_conv.survey_data:
                try:
                    sim_persisted = json.loads(sim_active_conv.survey_data)
                    sim_controller_version = sim_persisted.get('controller_version', 'v1')
                except json.JSONDecodeError:
                    pass

            try:
                if sim_controller_version == 'v2_deterministic':
                    sim_structured = finalize_ai_conversational_survey_v2(survey_data)
                else:
                    sim_structured = finalize_ai_conversational_survey(survey_data)
            except Exception as sim_err:
                logger.error(f"Simulation extraction error: {sim_err}")
                sim_structured = {}

            # Delete the ActiveConversation record (no analytics footprint)
            if sim_active_conv:
                try:
                    db.session.delete(sim_active_conv)
                    db.session.commit()
                except Exception as del_err:
                    logger.warning(f"Simulation: could not delete ActiveConversation: {del_err}")
                    db.session.rollback()

            # Clear simulation session flag
            session.pop('is_simulation', None)
            session.pop('auth_token', None)
            session.pop('auth_email', None)

            nps_score = sim_structured.get('nps_score')
            nps_category = None
            if nps_score is not None:
                if nps_score >= 9:
                    nps_category = 'Promoter'
                elif nps_score >= 7:
                    nps_category = 'Passive'
                else:
                    nps_category = 'Detractor'

            return jsonify({
                'is_simulation': True,
                'simulation_complete': True,
                'extraction': {
                    'nps_score': nps_score,
                    'nps_category': nps_category,
                    'satisfaction_rating': sim_structured.get('satisfaction_rating'),
                    'service_rating': sim_structured.get('service_rating'),
                    'product_value_rating': sim_structured.get('product_value_rating'),
                    'pricing_rating': sim_structured.get('pricing_rating'),
                    'tenure_with_fc': sim_structured.get('tenure_with_fc'),
                    'product_quality_feedback': sim_structured.get('product_quality_feedback'),
                    'support_experience_feedback': sim_structured.get('support_experience_feedback'),
                    'service_rating_feedback': sim_structured.get('service_rating_feedback'),
                    'user_experience_feedback': sim_structured.get('user_experience_feedback'),
                    'improvement_feedback': sim_structured.get('improvement_feedback'),
                    'additional_comments': sim_structured.get('additional_comments'),
                    'recommendation_reason': sim_structured.get('recommendation_reason'),
                    'is_complete': sim_structured.get('is_complete', False)
                }
            })
        
        # Add authenticated email and conversation ID to survey data
        survey_data['respondent_email'] = authenticated_email
        survey_data['conversation_id'] = conversation_id
        survey_data['conversation_history'] = json.dumps(messages)
        
        # FEATURE FLAG: Deterministic Survey Flow V2
        # FIX (Nov 23, 2025): Load controller_version from ActiveConversation if not in survey_data
        # Frontend doesn't always send controller_version, so check database
        from models import ActiveConversation
        controller_version = survey_data.get('controller_version')
        if not controller_version:
            # Load from ActiveConversation if not provided
            active_conv = ActiveConversation.query.filter_by(conversation_id=conversation_id).first()
            if active_conv and active_conv.survey_data:
                try:
                    persisted_survey_data = json.loads(active_conv.survey_data)
                    controller_version = persisted_survey_data.get('controller_version', 'v1')
                    logger.debug(f"Loaded controller_version from ActiveConversation: {controller_version}")
                except json.JSONDecodeError:
                    controller_version = 'v1'
            else:
                controller_version = 'v1'
        
        use_deterministic_v2 = (controller_version == 'v2_deterministic')
        
        # Convert conversational data to structured survey format
        # V2 uses dedicated finalization handler for deterministic state
        if use_deterministic_v2:
            logger.info(f"✅ Finalizing V2 deterministic conversation: {conversation_id}")
            try:
                structured_data = finalize_ai_conversational_survey_v2(survey_data)
            except ValueError as e:
                logger.error(f"V2 finalization failed: {str(e)}, falling back to V1")
                # Fallback to V1 finalization if V2 state corrupted
                structured_data = finalize_ai_conversational_survey(survey_data)
        else:
            logger.debug(f"Finalizing V1 conversation: {conversation_id}")
            structured_data = finalize_ai_conversational_survey(survey_data)
        
        # GUARD: Validate required fields to prevent NotNullViolation
        # If NPS score extraction failed (Claude parsing issues), log and fail gracefully
        if structured_data.get('nps_score') is None:
            logger.error(f"❌ Missing required field: nps_score is None. Extraction may have failed.")
            logger.info(f"Available fields in structured_data: {list(structured_data.keys())}")
            # Return error to user instead of crashing with DB constraint violation
            return jsonify({
                'error': 'Survey data extraction incomplete - NPS score missing. Please try again.',
                'missing_field': 'nps_score',
                'hint': 'If this persists, please contact support.'
            }), 422
        
        # Get campaign and association data from session (new system)
        association_id = session.get('association_id')
        campaign_id = session.get('campaign_id')
        
        # Fallback to active campaign for backward compatibility (old system)
        campaign = None
        if not campaign_id:
            demo_account = BusinessAccount.query.filter_by(name='Archelo Group inc').first()
            if demo_account:
                active_campaigns = Campaign.get_active_campaigns(demo_account.id)
                active_campaign = active_campaigns[0] if active_campaigns else None
            else:
                active_campaign = None
            campaign_id = active_campaign.id if active_campaign else None
            campaign = active_campaign
        else:
            campaign = Campaign.query.get(campaign_id)
        
        # Ensure association_id is available (fallback lookup for re-entry via fresh session)
        if not association_id and campaign_id and authenticated_email:
            association_id = lookup_association_id_fallback(authenticated_email, campaign_id)
            if association_id:
                session['association_id'] = association_id
                logger.info(f"Conversational survey: recovered association_id {association_id} via fallback lookup")
        
        # Prepare response data for potential anonymization
        response_data = {
            'company_name': normalize_company_name(structured_data.get('company_name')),
            'respondent_name': structured_data.get('respondent_name'),
            'respondent_email': authenticated_email
        }
        
        # Apply anonymization if campaign requires it
        response_data = anonymize_response_data(campaign, response_data)
        
        # CRITICAL FIX: Smart lookup to prevent cross-campaign corruption while preserving analytics
        # Priority: campaign_participant_id (durable invite ID) > (email, campaign_id) for legacy
        existing_response = None
        if association_id:
            # New system: Use campaign_participant_id (one response per invitation)
            existing_response = SurveyResponse.query.filter_by(
                campaign_participant_id=association_id
            ).first()
        if not existing_response and campaign_id:
            # Fallback: Use (email, campaign_id) to catch cases where association_id wasn't linked
            existing_response = SurveyResponse.query.filter_by(
                respondent_email=authenticated_email,
                campaign_id=campaign_id
            ).first()
        
        # Resolve tenure: AI extraction takes precedence; fall back to participant profile
        tenure_with_fc_voia = structured_data.get('tenure_with_fc')
        if not tenure_with_fc_voia:
            participant_id_voia = session.get('participant_id')
            if participant_id_voia:
                from models import Participant
                participant_voia = Participant.query.get(participant_id_voia)
                if participant_voia and hasattr(participant_voia, 'tenure_years') and participant_voia.tenure_years is not None:
                    tenure_with_fc_voia = map_tenure_years_to_category(participant_voia.tenure_years)

        if existing_response:
            # Update existing response (maintains one-row-per-campaign for analytics)
            existing_response.company_name = response_data['company_name']
            existing_response.respondent_name = response_data['respondent_name']
            existing_response.tenure_with_fc = tenure_with_fc_voia
            existing_response.nps_score = structured_data.get('nps_score')
            existing_response.satisfaction_rating = structured_data.get('satisfaction_rating')
            existing_response.product_value_rating = structured_data.get('product_value_rating')
            existing_response.service_rating = structured_data.get('service_rating')
            existing_response.pricing_rating = structured_data.get('pricing_rating')
            existing_response.improvement_feedback = structured_data.get('improvement_feedback')
            existing_response.recommendation_reason = structured_data.get('recommendation_reason')
            existing_response.additional_comments = structured_data.get('additional_comments')
            # 🔧 CRITICAL FIX: Save conversation transcript
            existing_response.conversation_history = survey_data.get('conversation_history')
            existing_response.ai_prompts_log = structured_data.get('ai_prompts_log')  # 🔧 DEBUG: Save AI prompts for debugging
            existing_response.deflection_summary = structured_data.get('deflection_summary')  # Phase 6: Save deflection analytics
            # Option B (Dec 11, 2025): Topic-specific feedback from summary extraction
            existing_response.product_quality_feedback = structured_data.get('product_quality_feedback')
            existing_response.support_experience_feedback = structured_data.get('support_experience_feedback')
            existing_response.service_rating_feedback = structured_data.get('service_rating_feedback')
            existing_response.user_experience_feedback = structured_data.get('user_experience_feedback')
            existing_response.source_type = 'conversational'
            # Update campaign if there's an active one, otherwise preserve existing
            if campaign_id:
                existing_response.campaign_id = campaign_id
            # Update association if available (new system)
            if association_id:
                existing_response.campaign_participant_id = association_id
            # Track when response was last updated and reset analysis for re-processing
            existing_response.updated_at = datetime.utcnow()
            existing_response.analyzed_at = None
            logger.info(f"Conversational survey: updating existing response {existing_response.id} (resubmission)")

            response = existing_response
        else:
            # Create survey response record with potentially anonymized data
            response = SurveyResponse(
                company_name=response_data['company_name'],
                respondent_name=response_data['respondent_name'],
                respondent_email=response_data['respondent_email'],
                tenure_with_fc=tenure_with_fc_voia,
                nps_score=structured_data.get('nps_score'),
                satisfaction_rating=structured_data.get('satisfaction_rating'),
                product_value_rating=structured_data.get('product_value_rating'),
                service_rating=structured_data.get('service_rating'),
                pricing_rating=structured_data.get('pricing_rating'),
                improvement_feedback=structured_data.get('improvement_feedback'),
                recommendation_reason=structured_data.get('recommendation_reason'),
                additional_comments=structured_data.get('additional_comments'),
                conversation_history=survey_data.get('conversation_history'),  # 🔧 CRITICAL FIX: Save conversation transcript
                ai_prompts_log=structured_data.get('ai_prompts_log'),  # 🔧 DEBUG: Save AI prompts for debugging
                deflection_summary=structured_data.get('deflection_summary'),  # Phase 6: Save deflection analytics
                # Option B (Dec 11, 2025): Topic-specific feedback from summary extraction
                product_quality_feedback=structured_data.get('product_quality_feedback'),
                support_experience_feedback=structured_data.get('support_experience_feedback'),
                service_rating_feedback=structured_data.get('service_rating_feedback'),
                user_experience_feedback=structured_data.get('user_experience_feedback'),
                source_type='conversational',  # 🔧 CRITICAL FIX: Mark as conversational survey
                campaign_id=campaign_id,
                campaign_participant_id=association_id  # Link to campaign-participant association
            )
            
            # Ensure trial participant exists and is associated with campaign
            if campaign_id and not association_id:
                # This is a trial user completing via public conversational survey - create participant record
                try:
                    participant, campaign_association = ensure_trial_participant(
                        email=authenticated_email,
                        name=structured_data.get('respondent_name'),
                        company_name=structured_data.get('company_name'),
                        campaign_id=campaign_id
                    )
                    
                    # Link response to the campaign participant association
                    response.campaign_participant_id = campaign_association.id
                    
                    # Mark association as completed
                    campaign_association.status = 'completed'
                    campaign_association.completed_at = datetime.utcnow()
                    
                    logger.info(f"Trial participant created and linked (conversational): {participant.email} -> campaign {campaign_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to create trial participant (conversational): {e}")
                    # Continue without participant linkage to maintain backward compatibility
            
            db.session.add(response)
        
        # Calculate NPS category
        if response.nps_score is not None:
            if response.nps_score >= 9:
                response.nps_category = "Promoter"
            elif response.nps_score >= 7:
                response.nps_category = "Passive"
            else:
                response.nps_category = "Detractor"
        db.session.commit()
        
        # Bust dashboard cache so the next Executive Summary load reflects fresh data
        if campaign_id:
            try:
                from data_storage import bust_dashboard_cache
                conv_campaign = Campaign.query.get(campaign_id)
                conv_ba_id = conv_campaign.business_account_id if conv_campaign else None
                if conv_ba_id:
                    bust_dashboard_cache(campaign_id, conv_ba_id, company_name=response.company_name)
            except Exception as cache_bust_err:
                logger.warning(f"Cache bust failed after conversational survey submit: {cache_bust_err}")
        
        # Mark association as completed if using new token system
        # Fallback: Look up association_id from database if missing from session
        if not association_id and campaign_id and authenticated_email:
            association_id = lookup_association_id_fallback(authenticated_email, campaign_id)
            if association_id:
                # Also link the response to the association
                response.campaign_participant_id = association_id
                db.session.commit()
        
        if association_id:
            import campaign_participant_token_system
            campaign_participant_token_system.mark_survey_completed(association_id, response.id)
        
        # Queue AI analysis
        add_analysis_task(response.id)
        
        # AUTOMATIC TOKEN INVALIDATION - Clear session to prevent survey restarts
        # But preserve email for export functionality
        session['export_email'] = authenticated_email  # Preserve for export
        session.pop('auth_token', None)
        session.pop('auth_email', None)
        session.permanent = False  # Force session to be non-permanent for immediate effect
        print(f"=== CONVERSATIONAL TOKEN INVALIDATED FOR {authenticated_email} ===")
        logger.info(f"Conversational survey completed by {authenticated_email} - Token invalidated")
        
        return jsonify({
            'message': 'Survey completed successfully - Token invalidated to prevent restart',
            'response_id': response.id,
            'analysis_status': 'queued',
            'authenticated_email': authenticated_email,
            'token_invalidated': True
        })
        
    except Exception as e:
        logger.error(f"Error finalizing conversation: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to finalize survey'}), 500

@app.route('/api/logout_session', methods=['POST'])
def logout_session():
    """Clear session authentication after survey completion"""
    try:
        # Clear session data
        session.pop('auth_token', None)
        session.pop('auth_email', None)
        session.clear()
        
        return jsonify({'message': 'Session cleared successfully'})
        
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        return jsonify({'error': 'Failed to clear session'}), 500

@app.route('/api/export_user_data', methods=['GET', 'POST'])
def export_user_data():
    """Export survey data for current user only (no admin required)"""
    try:
        # Try to get user email from session first (auth_email for active sessions, export_email for post-completion)
        user_email = session.get('auth_email') or session.get('export_email')
        
        # If no session, try to get from request body (POST) or query params (GET)
        if not user_email:
            if request.method == 'POST':
                data = request.get_json()
                user_email = data.get('email') if data else None
            else:
                user_email = request.args.get('email')
        
        if not user_email:
            return jsonify({
                'success': False,
                'message': 'Email address required. Please provide your email address.',
                'code': 'EMAIL_REQUIRED'
            }), 400
        
        # Query only responses from this specific user
        user_responses = SurveyResponse.query.options(
            joinedload(SurveyResponse.campaign)
        ).filter_by(
            respondent_email=user_email
        ).all()
        
        if not user_responses:
            return jsonify({
                'success': False,
                'message': 'No survey responses found for your email address.'
            }), 404
        
        # Convert responses to dict format
        export_data = []
        for response in user_responses:
            response_dict = response.to_dict()
            # Remove sensitive fields that user doesn't need
            if 'id' in response_dict:
                del response_dict['id']
            export_data.append(response_dict)
        
        return jsonify({
            'success': True,
            'data': export_data,
            'export_info': {
                'export_type': 'user_responses',
                'exported_by': user_email,
                'export_date': datetime.utcnow().isoformat(),
                'total_responses': len(export_data)
            }
        })
        
    except Exception as e:
        logger.error(f"Error exporting user data: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to export user data'
        }), 500

@app.route('/api/campaigns/filter-options')
def get_campaign_filter_options():
    """Get campaigns for analytics filtering (secure business user authentication)"""
    try:
        # Import models to avoid circular imports
        from models import Campaign
        # Check if this is a business user session (not participant)
        current_business_user = get_current_business_user()
        
        if current_business_user:
            # Business user - return their active/completed campaigns only (exclude drafts)
            business_account_id = current_business_user.business_account_id
            campaigns = Campaign.query.filter(
                Campaign.business_account_id == business_account_id,
                Campaign.status.in_(['active', 'completed'])
            ).order_by(Campaign.start_date.desc()).all()
        else:
            # Public/participant user - return demo campaigns only (ExecutiveSummary access)
            from models import BusinessAccount
            demo_account = BusinessAccount.query.filter_by(name='Archelo Group inc').first()
            if demo_account:
                campaigns = Campaign.query.filter(
                    Campaign.business_account_id == demo_account.id,
                    Campaign.status.in_(['active', 'completed'])
                ).order_by(Campaign.start_date.desc()).all()
            else:
                # No demo account found - return empty campaigns list
                campaigns = []
        return jsonify({
            'campaigns': [
                {
                    'id': campaign.id,
                    'name': campaign.name,
                    'start_date': campaign.start_date.isoformat(),
                    'end_date': campaign.end_date.isoformat(),
                    'status': campaign.status,
                    'description': campaign.description,
                    'survey_type': getattr(campaign, 'survey_type', 'conversational')
                }
                for campaign in campaigns
            ]
        })
    except Exception as e:
        logger.error(f"Error getting campaign filter options: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/classic_survey_analytics')
def classic_survey_analytics():
    """API endpoint for classic survey-specific analytics (CSAT, CES, drivers, features, recommendation)"""
    try:
        from models import Campaign, SurveyResponse, ClassicSurveyConfig, CampaignKPISnapshot
        from business_auth_routes import get_current_business_account
        import json as json_module

        campaign_id = request.args.get('campaign_id', type=int)
        if not campaign_id:
            return jsonify({'error': 'campaign_id required'}), 400

        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Authentication required'}), 401

        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=current_account.id
        ).first()
        if not campaign or campaign.survey_type != 'classic':
            return jsonify({'error': 'Classic campaign not found'}), 404

        if campaign.status == 'completed':
            snapshot = CampaignKPISnapshot.query.filter_by(campaign_id=campaign_id).first()
            if snapshot and snapshot.csat_distribution:
                return jsonify({
                    'total_responses': snapshot.total_responses,
                    'csat': {
                        'average': snapshot.avg_csat,
                        'distribution': json_module.loads(snapshot.csat_distribution) if snapshot.csat_distribution else {},
                        'count': sum(json_module.loads(snapshot.csat_distribution).values()) if snapshot.csat_distribution else 0
                    },
                    'ces': {
                        'average': snapshot.avg_ces,
                        'distribution': json_module.loads(snapshot.ces_distribution) if snapshot.ces_distribution else {},
                        'count': sum(json_module.loads(snapshot.ces_distribution).values()) if snapshot.ces_distribution else 0
                    },
                    'drivers': json_module.loads(snapshot.driver_attribution) if snapshot.driver_attribution else {},
                    'features': json_module.loads(snapshot.feature_analytics) if snapshot.feature_analytics else {},
                    'recommendation': json_module.loads(snapshot.recommendation_distribution) if snapshot.recommendation_distribution else {},
                    'correlation': json_module.loads(snapshot.correlation_data) if getattr(snapshot, 'correlation_data', None) else {'points': [], 'summary': {'avg_ces_by_nps_category': {}, 'nps_csat_alignment_pct': None, 'total_correlated_responses': 0}}
                })

        responses = SurveyResponse.query.filter_by(campaign_id=campaign_id).all()
        total = len(responses)

        if total == 0:
            return jsonify({
                'total_responses': 0,
                'csat': {'average': None, 'distribution': {}},
                'ces': {'average': None, 'distribution': {}},
                'drivers': {},
                'features': {},
                'recommendation': {},
                'correlation': {'points': [], 'summary': {'avg_ces_by_nps_category': {}, 'nps_csat_alignment_pct': None, 'total_correlated_responses': 0}}
            })

        csat_scores = [r.csat_score for r in responses if r.csat_score is not None]
        csat_dist = {}
        for s in csat_scores:
            csat_dist[str(s)] = csat_dist.get(str(s), 0) + 1
        csat_avg = round(sum(csat_scores) / len(csat_scores), 2) if csat_scores else None

        ces_scores = [r.ces_score for r in responses if r.ces_score is not None]
        ces_dist = {}
        for s in ces_scores:
            ces_dist[str(s)] = ces_dist.get(str(s), 0) + 1
        ces_avg = round(sum(ces_scores) / len(ces_scores), 2) if ces_scores else None

        driver_data = {}
        for r in responses:
            if r.loyalty_drivers:
                drivers = r.loyalty_drivers if isinstance(r.loyalty_drivers, list) else []
                nps_cat = getattr(r, 'nps_category', None) or 'Unknown'
                for d in drivers:
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
                'percentage': round(dd['count'] / total * 100, 1),
                'promoters': dd['promoters'],
                'passives': dd['passives'],
                'detractors': dd['detractors'],
                'net_impact': dd['promoters'] - dd['detractors'],
                'label_en': labels['label_en'],
                'label_fr': labels['label_fr']
            }

        correlation_points = []
        for r in responses:
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

        correlation_summary = {
            'avg_ces_by_nps_category': avg_ces_by_nps,
            'nps_csat_alignment_pct': nps_csat_alignment,
            'total_correlated_responses': len(correlation_points)
        }

        feature_data = {}
        feature_label_map = {}
        if classic_config and classic_config.features:
            for f in classic_config.features:
                feature_label_map[f['key']] = {
                    'name_en': f.get('name_en', f['key']),
                    'name_fr': f.get('name_fr', f['key'])
                }

        for r in responses:
            if r.general_feedback:
                try:
                    evals = json_module.loads(r.general_feedback) if isinstance(r.general_feedback, str) else r.general_feedback
                    for fkey, fdata in evals.items():
                        if fkey not in feature_data:
                            labels = feature_label_map.get(fkey, {'name_en': fkey, 'name_fr': fkey})
                            feature_data[fkey] = {
                                'name_en': labels['name_en'],
                                'name_fr': labels['name_fr'],
                                'usage_yes': 0,
                                'usage_no': 0,
                                'satisfaction_scores': [],
                                'importance_counts': {},
                                'frequency_counts': {}
                            }
                        fd = feature_data[fkey]
                        usage = fdata.get('usage', '')
                        if usage == 'yes':
                            fd['usage_yes'] += 1
                        elif usage and usage.startswith('no'):
                            fd['usage_no'] += 1
                        if fdata.get('satisfaction') is not None:
                            fd['satisfaction_scores'].append(fdata['satisfaction'])
                        if fdata.get('importance'):
                            fd['importance_counts'][fdata['importance']] = fd['importance_counts'].get(fdata['importance'], 0) + 1
                        if fdata.get('frequency'):
                            fd['frequency_counts'][fdata['frequency']] = fd['frequency_counts'].get(fdata['frequency'], 0) + 1
                except (json_module.JSONDecodeError, AttributeError):
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
                'avg_satisfaction': avg_sat,
                'importance': fd['importance_counts'],
                'frequency': fd['frequency_counts']
            }

        rec_counts = {}
        for r in responses:
            if r.recommendation_status:
                rec_counts[r.recommendation_status] = rec_counts.get(r.recommendation_status, 0) + 1

        return jsonify({
            'total_responses': total,
            'csat': {'average': csat_avg, 'distribution': csat_dist, 'count': len(csat_scores)},
            'ces': {'average': ces_avg, 'distribution': ces_dist, 'count': len(ces_scores)},
            'drivers': drivers_with_labels,
            'features': features_summary,
            'recommendation': rec_counts,
            'correlation': {
                'points': correlation_points,
                'summary': correlation_summary
            }
        })

    except Exception as e:
        logger.error(f"Error in classic survey analytics: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/campaigns/comparison')
def get_campaign_comparison():
    """Get comparison data between two campaigns (secure business user authentication)"""
    try:
        # Import models to avoid circular imports
        from models import Campaign
        
        campaign1_id = request.args.get('campaign1', type=int)
        campaign2_id = request.args.get('campaign2', type=int)
        
        if not campaign1_id or not campaign2_id:
            return jsonify({'error': 'Both campaign1 and campaign2 IDs required'}), 400
        
        # Check if this is a business user session (not participant)
        current_business_user = get_current_business_user()
        
        if current_business_user:
            # Business user - verify both campaigns belong to their account
            business_account_id = current_business_user.business_account_id
            campaign1 = Campaign.query.filter_by(id=campaign1_id, business_account_id=business_account_id).first()
            campaign2 = Campaign.query.filter_by(id=campaign2_id, business_account_id=business_account_id).first()
        else:
            # Public/participant user - only allow demo account campaigns (ExecutiveSummary access)
            from models import BusinessAccount
            demo_account = BusinessAccount.query.filter_by(name='Archelo Group inc').first()
            if demo_account:
                campaign1 = Campaign.query.filter_by(id=campaign1_id, business_account_id=demo_account.id).first()
                campaign2 = Campaign.query.filter_by(id=campaign2_id, business_account_id=demo_account.id).first()
            else:
                # No demo account found - return error
                return jsonify({'error': 'Demo account not available'}), 404
        
        if not campaign1 or not campaign2:
            return jsonify({'error': 'One or both campaigns not found or not accessible'}), 404
            
        # Get dashboard data for both campaigns using optimized cached path
        from data_storage import get_dashboard_data_cached
        
        # Determine business account ID for proper data scoping
        if current_business_user:
            business_account_id = current_business_user.business_account_id
        else:
            from models import BusinessAccount
            demo_account = BusinessAccount.query.filter_by(name='Archelo Group inc').first()
            business_account_id = demo_account.id if demo_account else None
        
        data1 = get_dashboard_data_cached(campaign_id=campaign1_id, business_account_id=business_account_id)
        data2 = get_dashboard_data_cached(campaign_id=campaign2_id, business_account_id=business_account_id)
        
        # Build comparison data
        comparison = {
            'campaign1': {
                'id': campaign1.id,
                'name': campaign1.name,
                'status': campaign1.status,
                'survey_type': getattr(campaign1, 'survey_type', 'conversational'),
                'start_date': campaign1.start_date.isoformat() if campaign1.start_date else None,
                'end_date': campaign1.end_date.isoformat() if campaign1.end_date else None,
                'data': {
                    'total_responses': data1.get('total_responses', 0),
                    'nps_score': data1.get('nps_score', 0),
                    'companies_analyzed': data1.get('total_companies', 0),
                    'critical_risk_companies': sum(1 for company in data1.get('account_intelligence', []) if company.get('critical_risks', 0) > 0),
                    'risk_heavy_accounts': sum(1 for company in data1.get('account_intelligence', []) if company.get('balance') == 'risk_heavy'),
                    'opportunity_heavy_accounts': sum(1 for company in data1.get('account_intelligence', []) if company.get('balance') == 'opportunity_heavy'),
                    'balanced_accounts': sum(1 for company in data1.get('account_intelligence', []) if company.get('balance') == 'balanced'),
                    'total_risks': sum(company.get('risk_count', 0) for company in data1.get('account_intelligence', [])),
                    'total_opportunities': sum(company.get('opportunity_count', 0) for company in data1.get('account_intelligence', [])),
                    'average_ratings': data1.get('average_ratings', {'satisfaction': 0, 'product_value': 0, 'pricing': 0, 'service': 0})
                }
            },
            'campaign2': {
                'id': campaign2.id,
                'name': campaign2.name,
                'status': campaign2.status,
                'survey_type': getattr(campaign2, 'survey_type', 'conversational'),
                'start_date': campaign2.start_date.isoformat() if campaign2.start_date else None,
                'end_date': campaign2.end_date.isoformat() if campaign2.end_date else None,
                'data': {
                    'total_responses': data2.get('total_responses', 0),
                    'nps_score': data2.get('nps_score', 0),
                    'companies_analyzed': data2.get('total_companies', 0),
                    'critical_risk_companies': sum(1 for company in data2.get('account_intelligence', []) if company.get('critical_risks', 0) > 0),
                    'risk_heavy_accounts': sum(1 for company in data2.get('account_intelligence', []) if company.get('balance') == 'risk_heavy'),
                    'opportunity_heavy_accounts': sum(1 for company in data2.get('account_intelligence', []) if company.get('balance') == 'opportunity_heavy'),
                    'balanced_accounts': sum(1 for company in data2.get('account_intelligence', []) if company.get('balance') == 'balanced'),
                    'total_risks': sum(company.get('risk_count', 0) for company in data2.get('account_intelligence', [])),
                    'total_opportunities': sum(company.get('opportunity_count', 0) for company in data2.get('account_intelligence', [])),
                    'average_ratings': data2.get('average_ratings', {'satisfaction': 0, 'product_value': 0, 'pricing': 0, 'service': 0})
                }
            },
            'company_details': []
        }
        
        # Build company-by-company comparison
        ai1 = data1.get('account_intelligence', [])
        ai2 = data2.get('account_intelligence', [])
        
        # Create lookup maps
        companies1 = {company.get('company_name', '').upper(): company for company in ai1}
        companies2 = {company.get('company_name', '').upper(): company for company in ai2}
        
        # Get all unique companies
        all_companies = set(companies1.keys()) | set(companies2.keys())
        
        for company_key in sorted(all_companies):
            c1 = companies1.get(company_key, {})
            c2 = companies2.get(company_key, {})
            
            # Use the most recent company name version
            display_name = c1.get('company_name') or c2.get('company_name', company_key.title())
            
            # Determine if company participated in each campaign
            c1_participated = bool(c1)
            c2_participated = bool(c2)
            
            comparison['company_details'].append({
                'company_name': display_name,
                'campaign1': {
                    'risk_count': c1.get('risk_count') if c1_participated else None,
                    'opportunity_count': c1.get('opportunity_count') if c1_participated else None,
                    'balance': c1.get('balance') if c1_participated else None,
                    'critical_risks': c1.get('critical_risks') if c1_participated else None,
                    'participated': c1_participated
                },
                'campaign2': {
                    'risk_count': c2.get('risk_count') if c2_participated else None,
                    'opportunity_count': c2.get('opportunity_count') if c2_participated else None,
                    'balance': c2.get('balance') if c2_participated else None,
                    'critical_risks': c2.get('critical_risks') if c2_participated else None,
                    'participated': c2_participated
                }
            })
        
        return jsonify(comparison)
        
    except Exception as e:
        logger.error(f"Error getting campaign comparison: {e}")
        return jsonify({'error': 'Failed to load comparison data'}), 500

@app.route('/api/campaigns/<int:campaign_id>/companies/<company_name>/responses')
def get_company_responses(campaign_id, company_name):
    """Get all responses for a specific company in a campaign with pagination and filtering"""
    try:
        from models import Campaign, SurveyResponse
        
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Search/filter parameters
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Validate per_page limits
        per_page = min(per_page, 100)
        
        # Check if this is a business user session (not participant)
        current_business_user = get_current_business_user()
        
        if current_business_user:
            # Business user - verify campaign belongs to their account
            business_account_id = current_business_user.business_account_id
            campaign = Campaign.query.filter_by(id=campaign_id, business_account_id=business_account_id).first()
        else:
            # Public/participant user - only allow demo account campaigns
            from models import BusinessAccount
            demo_account = BusinessAccount.query.filter_by(name='Archelo Group inc').first()
            if demo_account:
                campaign = Campaign.query.filter_by(id=campaign_id, business_account_id=demo_account.id).first()
            else:
                return jsonify({'error': 'Demo account not available'}), 404
        
        if not campaign:
            return jsonify({'error': 'Campaign not found or not accessible'}), 404
        
        # Build base query for responses
        query = SurveyResponse.query.filter_by(
            campaign_id=campaign_id,
            company_name=company_name
        )
        
        # Apply search filter if provided
        if search:
            query = query.filter(
                or_(
                    SurveyResponse.respondent_name.ilike(f'%{search}%'),
                    SurveyResponse.respondent_email.ilike(f'%{search}%')
                )
            )
        
        # Apply sorting
        sort_column = getattr(SurveyResponse, sort_by, SurveyResponse.created_at)
        if sort_order == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        responses = query.limit(per_page).offset(offset).all()
        
        # Build response data
        response_list = []
        for response in responses:
            # Create response data dict
            response_data = {
                'company_name': response.company_name,
                'respondent_name': response.respondent_name,
                'respondent_email': response.respondent_email
            }
            
            # Apply anonymization if needed
            if campaign.anonymize_responses:
                response_data = anonymize_response_data(campaign, response_data)
            
            # Determine if current user can view this response
            if current_business_user:
                # Business user can view all responses from their campaigns
                can_view = True
            elif response.campaign_participant_id is None:
                # Public user can view trial responses only
                can_view = True
            else:
                # Public user cannot view business responses
                can_view = False
            
            response_list.append({
                'id': response.id,
                'respondent_name': response_data['respondent_name'],
                'nps_score': response.nps_score,
                'satisfaction_rating': response.satisfaction_rating,
                'product_value_rating': response.product_value_rating,
                'service_rating': response.service_rating,
                'pricing_rating': response.pricing_rating,
                'created_at': response.created_at.isoformat() if response.created_at else None,
                'campaign_participant_id': response.campaign_participant_id,
                'can_view': can_view
            })
        
        # Calculate pagination metadata
        total_pages = (total_count + per_page - 1) // per_page
        
        return jsonify({
            'responses': response_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'campaign': {
                'id': campaign.id,
                'name': campaign.name
            },
            'company_name': company_name
        })
        
    except Exception as e:
        logger.error(f"Error getting company responses: {e}")
        return jsonify({'error': 'Failed to load company responses'}), 500

# Error handlers for routing diagnostics
@app.errorhandler(404)
def handle_404(e):
    """404 error handler with diagnostic logging for routing debugging"""
    # Get detailed request information
    request_path = request.path
    full_url = request.url
    method = request.method
    referer = request.headers.get('Referer', 'No referer')
    user_agent = request.headers.get('User-Agent', 'No user agent')
    
    # Log detailed 404 information for debugging
    logger.warning(f"404 Error - Path: {request_path} | Full URL: {full_url} | Method: {method} | Referer: {referer} | User-Agent: {user_agent[:100]}...")
    
    # Return a proper 404 response
    return render_template('404.html' if app.config.get('TEMPLATES_404_ENABLED') else 'index.html', 
                          error="Page not found", 
                          requested_path=request_path), 404


@app.route('/dashboard/company-responses/<company_name>')
def company_responses_page(company_name):
    """Dedicated page for viewing all responses from a specific company"""
    try:
        from models import Campaign
        
        # Get campaign ID from query parameter
        campaign_id = request.args.get('campaign', type=int)
        if not campaign_id:
            flash('L’identifiant de la campagne est requis.', 'error')
            # Redirect based on auth status
            current_user_check = get_current_business_user()
            return redirect(url_for('executive_summary') if current_user_check else url_for('dashboard'))
        
        # Check authentication and get campaign
        current_business_user = get_current_business_user()
        
        if current_business_user:
            # Business user - verify campaign belongs to their account
            business_account_id = current_business_user.business_account_id
            campaign = Campaign.query.filter_by(id=campaign_id, business_account_id=business_account_id).first()
        else:
            # Public user - only allow demo account campaigns
            from models import BusinessAccount
            demo_account = BusinessAccount.query.filter_by(name='Archelo Group inc').first()
            if demo_account:
                campaign = Campaign.query.filter_by(id=campaign_id, business_account_id=demo_account.id).first()
            else:
                flash('Compte de démonstration non disponible.', 'error')
                return redirect(url_for('dashboard'))  # Public users only reach here
        
        if not campaign:
            flash('Campagne introuvable ou inaccessible.', 'error')
            return redirect(url_for('executive_summary') if current_business_user else url_for('dashboard'))
        
        # Check if user is authenticated as business user
        is_business_authenticated = current_business_user is not None
        
        # Get branding context based on authentication
        if is_business_authenticated and current_business_user:
            # Authenticated business user - get their branding
            business_account_id = current_business_user.business_account_id
            branding_context = get_branding_context(business_account_id)
        else:
            # Trial/demo user - get demo branding (Archelo Group - ID 1)
            branding_context = get_branding_context(business_account_id=1)
        
        # Determine breadcrumb based on session or default based on user type
        if is_business_authenticated:
            last_bi_page = session.get('last_bi_page', url_for('campaign_insights'))
        else:
            last_bi_page = session.get('last_bi_page', url_for('dashboard'))
        
        # Determine breadcrumb label based on the URL
        if 'executive-summary' in last_bi_page:
            bi_label = 'Executive Summary'
        elif 'campaign-insights' in last_bi_page:
            bi_label = 'Campaign Insights'
        else:
            bi_label = 'Business Intelligence'
        
        from data_storage import get_company_detail_data
        detail_ba_id = current_business_user.business_account_id if current_business_user else 1
        account_insights = get_company_detail_data(campaign_id, company_name, business_account_id=detail_ba_id)

        return render_template('company_responses.html',
                             company_name=company_name,
                             campaign=campaign,
                             campaign_id=campaign_id,
                             branding_context=branding_context,
                             is_business_authenticated=is_business_authenticated,
                             bi_url=last_bi_page,
                             bi_label=bi_label,
                             account_insights=account_insights)
    
    except Exception as e:
        logger.error(f"Error loading company responses page: {e}")
        flash('Erreur lors du chargement des réponses de l’entreprise.', 'error')
        # Redirect based on authentication  
        current_user_check = get_current_business_user()
        return redirect(url_for('executive_summary') if current_user_check else url_for('dashboard'))

@app.route('/api/company_detail')
@rate_limit(limit=100)
def api_company_detail():
    """API endpoint for aggregated per-company qualitative signals (themes, sub-metrics, churn risk, AI summary)"""
    try:
        from models import Campaign
        from business_auth_routes import get_current_business_account
        from data_storage import get_company_detail_data

        campaign_id = request.args.get('campaign', type=int)
        company_name = request.args.get('company', '').strip()

        if not campaign_id or not company_name:
            return jsonify({'error': 'campaign and company parameters are required'}), 400

        current_account = get_current_business_account()
        if current_account:
            target_business_account_id = current_account.id
        else:
            target_business_account_id = 1

        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=target_business_account_id
        ).first()
        if not campaign:
            return jsonify({'error': 'Campaign not found or access denied'}), 404

        detail = get_company_detail_data(campaign_id, company_name, business_account_id=target_business_account_id)
        if detail is None:
            return jsonify({
                'success': True,
                'data': {
                    'nps_summary': None,
                    'top_themes': [],
                    'sub_metrics': {},
                    'weakest_metric': None,
                    'avg_churn_risk_score': None,
                    'analysis_summary': None
                }
            })

        return jsonify({'success': True, 'data': detail})
    except Exception as e:
        logger.error(f"Error getting company detail data: {e}")
        return jsonify({'error': 'Failed to get company detail data'}), 500

@app.route('/admin/regenerate-survey-tokens', methods=['GET'])
def regenerate_all_survey_tokens():
    """Admin endpoint to regenerate all campaign participant tokens from within the running app"""
    # Import models inside function to avoid circular imports
    from models import CampaignParticipant, Participant, Campaign
    import campaign_participant_token_system
    
    try:
        # TODO: Re-enable auth check for production
        # authenticated_email = session.get('auth_email')
        # business_user_id = session.get('business_user_id')
        # if not (authenticated_email and business_user_id):
        #     return jsonify({'error': 'Admin authentication required'}), 401
        
        # Get all campaign participants
        participants = CampaignParticipant.query.join(Participant).join(Campaign).all()
        
        regenerated_links = []
        success_count = 0
        error_count = 0
        
        for cp in participants:
            participant = cp.participant
            campaign = cp.campaign
            
            try:
                # Use the token creation function that runs inside the app context
                result = campaign_participant_token_system.create_campaign_participant_token(cp.id)
                
                if result['success']:
                    survey_link = f"http://localhost:5000/survey?token={result['jwt_token']}"
                    
                    regenerated_links.append({
                        'participant': participant.name,
                        'email': participant.email,
                        'campaign': campaign.name,
                        'association_id': cp.id,
                        'status': cp.status,
                        'survey_link': survey_link,
                        'jwt_token': result['jwt_token']
                    })
                    success_count += 1
                else:
                    logger.error(f"Failed to regenerate token for {participant.name}: {result['error']}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"Error regenerating token for {participant.name}: {e}")
                error_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Successfully regenerated {success_count} survey tokens',
            'total_participants': len(participants),
            'success_count': success_count,
            'error_count': error_count,
            'regenerated_links': regenerated_links
        })
        
    except Exception as e:
        logger.error(f"Error regenerating survey tokens: {e}")
        return jsonify({'error': 'Failed to regenerate tokens'}), 500


# ============================================================================
# NOTIFICATION CENTER API ENDPOINTS
# ============================================================================

@app.route('/api/notifications/count', methods=['GET'])
@require_business_auth
def get_notification_count():
    """Get count of unread notifications"""
    try:
        from notification_utils import get_unread_count
        
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        user_id = session.get('business_user_id')
        count = get_unread_count(current_account.id, user_id)
        
        response = jsonify({'unread_count': count})
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        logger.error(f"Error getting notification count: {e}")
        return jsonify({'error': 'Failed to get notification count'}), 500


@app.route('/api/notifications', methods=['GET'])
@require_business_auth
def get_notifications():
    """Get recent notifications"""
    try:
        from models import Notification
        from datetime import timedelta
        from notification_utils import cleanup_old_notifications
        
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        user_id = session.get('business_user_id')
        limit = int(request.args.get('limit', 20))
        since_days = request.args.get('since_days', type=int)
        
        import random
        if random.random() < 0.01:
            cleanup_old_notifications(days=90)
        
        query = Notification.query.filter_by(
            business_account_id=current_account.id
        )
        
        if user_id:
            query = query.filter(
                (Notification.user_id == user_id) | (Notification.user_id.is_(None))
            )
        
        if since_days:
            cutoff = datetime.utcnow() - timedelta(days=since_days)
            query = query.filter(Notification.created_at >= cutoff)
        
        notifications = query.order_by(
            Notification.created_at.desc()
        ).limit(limit).all()
        
        response = jsonify({
            'notifications': [n.to_dict() for n in notifications],
            'total': len(notifications)
        })
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        return jsonify({'error': 'Failed to get notifications'}), 500


@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@require_business_auth
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        from notification_utils import mark_as_read
        
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        success = mark_as_read(notification_id, current_account.id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Notification not found'}), 404
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return jsonify({'error': 'Failed to mark notification as read'}), 500


@app.route('/api/notifications/mark-all-read', methods=['POST'])
@require_business_auth
def mark_all_notifications_read():
    """Mark all notifications as read"""
    try:
        from notification_utils import mark_all_as_read
        
        current_account = get_current_business_account()
        if not current_account:
            return jsonify({'error': 'Business account not found'}), 401
        
        user_id = session.get('business_user_id')
        count = mark_all_as_read(current_account.id, user_id)
        
        return jsonify({
            'success': True,
            'marked_count': count
        })
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({'error': 'Failed to mark all notifications as read'}), 500



