from flask import render_template, request, jsonify, flash, redirect, url_for, g, session
from app import app, db
from models import SurveyResponse, Campaign
from models_auth import AuthToken
from task_queue import add_analysis_task, get_queue_stats
from rate_limiter import rate_limit
from auth_system import require_auth, generate_user_token, require_admin_auth
from conversational_survey import start_conversational_survey, process_conversation_response, finalize_conversational_survey
from ai_conversational_survey import start_ai_conversational_survey, process_ai_conversation_response, finalize_ai_conversational_survey
from datetime import datetime, timedelta, date
import json
import logging
import re
import uuid

logger = logging.getLogger(__name__)

def normalize_company_name(company_name):
    """Normalize company name for case-insensitive comparison"""
    if not company_name:
        return company_name
    # Convert to title case for consistent display (first letter caps, rest lowercase)
    return company_name.strip().title()

@app.route('/')
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
    return render_template('server_auth.html', user_email=None)

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
            return render_template('server_auth.html', token_result=token_result)
        
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
        return render_template('server_auth.html', token_result=token_result)
        
    except Exception as e:
        app.logger.error(f"Server-side token generation failed: {e}")
        token_result = {
            'success': False,
            'error': f'Token generation failed: {str(e)}'
        }
        return render_template('server_auth.html', token_result=token_result)

@app.route('/survey')
def survey():
    """Main survey page - check for token in URL"""
    token = request.args.get('token')
    if token:
        # Verify token and store in session for form submission
        import simple_token_system
        verification = simple_token_system.verify_simple_token(token)
        if verification.get('valid'):
            email = verification.get('email')
            
            # Allow response updates - don't block existing responses
            # existing_response = SurveyResponse.query.filter_by(respondent_email=email).first()
            # if existing_response:
            #     # Show completion message instead of survey form
            #     return render_template('survey_completed.html', 
            #                          email=email,
            #                          user_email=email,
            #                          completion_date=existing_response.created_at.strftime("%B %d, %Y"),
            #                          show_alternatives=True)
            
            session['auth_token'] = token
            session['auth_email'] = email
            return render_template('survey.html', authenticated=True, email=email, user_email=email)
        else:
            return render_template('survey.html', authenticated=False, error="Invalid or expired token", user_email=None)
    else:
        # Check if already authenticated via session
        if session.get('auth_token'):
            email = session.get('auth_email')
            
            # Allow response updates - don't block existing responses
            # existing_response = SurveyResponse.query.filter_by(respondent_email=email).first()
            # if existing_response:
            #     # Show completion message instead of survey form
            #     return render_template('survey_completed.html', 
            #                          email=email,
            #                          user_email=email,
            #                          completion_date=existing_response.created_at.strftime("%B %d, %Y"),
            #                          show_alternatives=True)
                                     
            return render_template('survey.html', authenticated=True, email=email, user_email=email)
        else:
            # Redirect unauthenticated users to auth page instead of showing broken page
            return redirect(url_for('server_auth'))

@app.route('/submit_survey_form', methods=['POST'])
@rate_limit(limit=10)
def submit_survey_form():
    """Handle server-side form submission (no JavaScript required)"""
    try:
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
        
        # Get active campaign for automatic assignment
        active_campaign = Campaign.get_active_campaign('archelo_group')
        campaign_id = active_campaign.id if active_campaign else None
        
        # Create survey response with normalized company name and campaign assignment
        response = SurveyResponse(
            company_name=normalize_company_name(data['company_name']),
            respondent_name=data['respondent_name'],
            respondent_email=authenticated_email,
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
            campaign_id=campaign_id
        )
        
        db.session.add(response)
        db.session.commit()
        
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
        
        # Redirect to success page showing token was invalidated
        return render_template('survey_success.html', 
                             response_id=response.id,
                             analysis_status=analysis_status,
                             email=authenticated_email)
        
    except Exception as e:
        logger.error(f"Error in form survey submission: {e}")
        return render_template('survey.html', authenticated=True, email=session.get('auth_email'), 
                             error=f'Survey submission failed: {str(e)}')

@app.route('/submit_survey', methods=['POST'])
@rate_limit(limit=10)  # 10 survey submissions per minute per IP
def submit_survey():
    """Handle authenticated survey submission and prevent duplicates"""
    try:
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
        if nps_score >= 9:
            nps_category = 'Promoter'
        elif nps_score >= 7:
            nps_category = 'Passive'
        else:
            nps_category = 'Detractor'
        
        # Get active campaign for automatic assignment
        active_campaign = Campaign.get_active_campaign('archelo_group')
        campaign_id = active_campaign.id if active_campaign else None
        
        # Check for existing response to update instead of creating duplicate
        existing_response = SurveyResponse.query.filter_by(
            respondent_email=authenticated_email
        ).first()
        
        if existing_response:
            # Update existing response (preserve campaign if no active campaign)
            existing_response.company_name = normalize_company_name(data['company_name'])
            existing_response.respondent_name = data['respondent_name']
            existing_response.tenure_with_fc = data.get('tenure_with_fc')
            existing_response.nps_score = nps_score
            existing_response.nps_category = nps_category
            existing_response.satisfaction_rating = int(data['satisfaction_rating']) if data.get('satisfaction_rating') else None
            existing_response.product_value_rating = int(data['product_value_rating']) if data.get('product_value_rating') else None
            existing_response.service_rating = int(data['service_rating']) if data.get('service_rating') else None
            existing_response.pricing_rating = int(data['pricing_rating']) if data.get('pricing_rating') else None
            existing_response.improvement_feedback = data.get('improvement_feedback')
            existing_response.recommendation_reason = data.get('recommendation_reason')
            existing_response.additional_comments = data.get('additional_comments')
            # Update campaign if there's an active one, otherwise preserve existing
            if campaign_id:
                existing_response.campaign_id = campaign_id

            response = existing_response
        else:
            # Create new survey response with authenticated email, normalized company name, and campaign assignment
            response = SurveyResponse(
                company_name=normalize_company_name(data['company_name']),
                respondent_name=data['respondent_name'],
                respondent_email=authenticated_email,  # Use authenticated email
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
                campaign_id=campaign_id
            )
            db.session.add(response)
        db.session.commit()
        
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
        active_campaign = Campaign.get_active_campaign('archelo_group')
        campaign_id = active_campaign.id if active_campaign else None
        
        if existing_response:
            # Update existing response with campaign assignment
            existing_response.company_name = normalize_company_name(data['company_name'])
            existing_response.respondent_name = data['respondent_name']
            existing_response.tenure_with_fc = data.get('tenure_with_fc')
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
            # Create new response with campaign assignment
            response = SurveyResponse(
                company_name=normalize_company_name(data['company_name']),
                respondent_name=data['respondent_name'],
                respondent_email=authenticated_email,
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
                campaign_id=campaign_id
            )
            db.session.add(response)
            action = "created"
        
        db.session.commit()
        
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

@app.route('/dashboard')
def dashboard():
    """Dashboard showing survey results and insights"""
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
    return render_template('dashboard.html', company_nps_data=company_nps_data, user_email=user_email)

@app.route('/api/dashboard_data')
def dashboard_data():
    """API endpoint for dashboard data"""
    try:
        from data_storage import get_dashboard_data
        data = get_dashboard_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500

@app.route('/api/survey_responses')
def survey_responses():
    """API endpoint for survey responses with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Max 100 per page
        
        pagination = SurveyResponse.query.order_by(
            SurveyResponse.created_at.desc()
        ).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False,
            max_per_page=100
        )
        
        return jsonify({
            'responses': [response.to_dict() for response in pagination.items],
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
    except Exception as e:
        logger.error(f"Error fetching survey responses: {e}")
        return jsonify({'error': 'Failed to fetch survey responses'}), 500

@app.route('/api/export_data')
@require_admin_auth()
def export_data():
    """Export survey data as JSON - Admin access required"""
    try:
        responses = SurveyResponse.query.all()
        data = [response.to_dict() for response in responses]
        
        # Log admin access
        admin_email = g.authenticated_email
        logger.info(f"Admin data export accessed by {admin_email}")
        
        return jsonify({
            'data': data,
            'export_info': {
                'total_responses': len(data),
                'exported_by': admin_email,
                'export_timestamp': datetime.utcnow().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        return jsonify({'error': 'Failed to export data'}), 500

@app.route('/api/queue_status')
def queue_status():
    """Get task queue status for monitoring"""
    try:
        stats = get_queue_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return jsonify({'error': 'Failed to get queue status'}), 500

# Campaign Management API Routes
@app.route('/api/campaigns', methods=['GET'])
@require_admin_auth()
def list_campaigns():
    """List all campaigns for the client"""
    try:
        client_identifier = 'archelo_group'  # Current single-client setup
        
        campaigns = Campaign.query.filter_by(
            client_identifier=client_identifier
        ).order_by(Campaign.created_at.desc()).all()
        
        return jsonify({
            'campaigns': [campaign.to_dict() for campaign in campaigns],
            'total_campaigns': len(campaigns),
            'remaining_campaigns': 4 - len(campaigns),
            'can_create_more': Campaign.can_create_campaign(client_identifier)
        })
        
    except Exception as e:
        logger.error(f"Error listing campaigns: {e}")
        return jsonify({'error': 'Failed to fetch campaigns'}), 500

@app.route('/api/campaigns', methods=['POST'])
@require_admin_auth()
def create_campaign():
    """Create a new campaign"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['name', 'start_date', 'end_date']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        client_identifier = 'archelo_group'  # Current single-client setup
        
        # Check campaign limit
        if not Campaign.can_create_campaign(client_identifier):
            return jsonify({
                'error': 'Campaign limit reached. Maximum 4 campaigns allowed per year.',
                'code': 'CAMPAIGN_LIMIT_EXCEEDED'
            }), 400
        
        # Parse dates
        try:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'error': 'Invalid date format. Use YYYY-MM-DD format.',
                'code': 'INVALID_DATE_FORMAT'
            }), 400
        
        # Validate date logic
        if start_date > end_date:
            return jsonify({
                'error': 'Start date must be before end date',
                'code': 'INVALID_DATE_RANGE'
            }), 400
        
        # Check for overlapping campaigns
        if Campaign.has_overlapping_campaign(start_date, end_date, client_identifier):
            return jsonify({
                'error': 'Campaign dates overlap with an existing active campaign',
                'code': 'OVERLAPPING_CAMPAIGN'
            }), 400
        
        # Create campaign
        campaign = Campaign(
            name=data['name'].strip(),
            description=data.get('description', '').strip(),
            start_date=start_date,
            end_date=end_date,
            client_identifier=client_identifier,
            status='active'
        )
        
        db.session.add(campaign)
        db.session.commit()
        
        logger.info(f"Campaign created: {campaign.name} (ID: {campaign.id}) by {g.authenticated_email}")
        
        return jsonify({
            'message': 'Campaign created successfully',
            'campaign': campaign.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create campaign'}), 500

@app.route('/api/campaigns/<int:campaign_id>/close', methods=['POST'])
@require_admin_auth()
def close_campaign(campaign_id):
    """Close a campaign manually"""
    try:
        client_identifier = 'archelo_group'  # Current single-client setup
        
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            client_identifier=client_identifier
        ).first()
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        if campaign.status == 'completed':
            return jsonify({
                'error': 'Campaign is already completed',
                'code': 'ALREADY_COMPLETED'
            }), 400
        
        # Close the campaign
        campaign.close_campaign()
        db.session.commit()
        
        logger.info(f"Campaign manually closed: {campaign.name} (ID: {campaign.id}) by {g.authenticated_email}")
        
        return jsonify({
            'message': 'Campaign closed successfully',
            'campaign': campaign.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error closing campaign: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to close campaign'}), 500

@app.route('/api/campaigns/active', methods=['GET'])
def get_active_campaign():
    """Get the currently active campaign"""
    try:
        client_identifier = 'archelo_group'  # Current single-client setup
        
        campaign = Campaign.get_active_campaign(client_identifier)
        
        if campaign:
            return jsonify({
                'active_campaign': campaign.to_dict(),
                'has_active_campaign': True
            })
        else:
            return jsonify({
                'active_campaign': None,
                'has_active_campaign': False,
                'message': 'No active campaign found'
            })
        
    except Exception as e:
        logger.error(f"Error getting active campaign: {e}")
        return jsonify({'error': 'Failed to get active campaign'}), 500

@app.route('/api/campaigns/stats', methods=['GET'])
@require_admin_auth()
def campaign_stats():
    """Get campaign statistics"""
    try:
        client_identifier = 'archelo_group'  # Current single-client setup
        
        total_campaigns = Campaign.count_client_campaigns(client_identifier)
        active_campaign = Campaign.get_active_campaign(client_identifier)
        can_create = Campaign.can_create_campaign(client_identifier)
        
        # Get campaign response counts
        campaigns_with_responses = db.session.query(
            Campaign.id,
            Campaign.name,
            Campaign.status,
            db.func.count(SurveyResponse.id).label('response_count')
        ).outerjoin(
            SurveyResponse, Campaign.id == SurveyResponse.campaign_id
        ).filter(
            Campaign.client_identifier == client_identifier
        ).group_by(Campaign.id, Campaign.name, Campaign.status).all()
        
        return jsonify({
            'total_campaigns': total_campaigns,
            'remaining_campaigns': 4 - total_campaigns,
            'can_create_campaign': can_create,
            'active_campaign': active_campaign.to_dict() if active_campaign else None,
            'campaign_responses': [
                {
                    'campaign_id': c.id,
                    'campaign_name': c.name,
                    'status': c.status,
                    'response_count': c.response_count
                }
                for c in campaigns_with_responses
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting campaign stats: {e}")
        return jsonify({'error': 'Failed to get campaign statistics'}), 500

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
    """API endpoint for company-segregated NPS data with pagination"""
    try:
        from data_storage import get_company_nps_data
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Max 100 per page
        
        # Get all company data
        all_company_data = get_company_nps_data()
        total_companies = len(all_company_data)
        
        # Calculate pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        company_data = all_company_data[start_idx:end_idx]
        
        # Calculate pagination info
        total_pages = (total_companies + per_page - 1) // per_page
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
    """API endpoint for tenure-segregated NPS data with pagination"""
    try:
        from data_storage import get_tenure_nps_data
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Max 100 per page
        
        # Get all tenure data
        all_tenure_data = get_tenure_nps_data()
        total_tenure_groups = len(all_tenure_data)
        
        # Calculate pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        tenure_data = all_tenure_data[start_idx:end_idx]
        
        # Calculate pagination info
        total_pages = (total_tenure_groups + per_page - 1) // per_page
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

# Conversational Survey Routes
@app.route('/conversational_survey')
def conversational_survey():
    """AI-powered conversational survey page - check for token in URL"""
    token = request.args.get('token')
    if token:
        # Verify token and store in session for survey submission
        import simple_token_system
        verification = simple_token_system.verify_simple_token(token)
        if verification.get('valid'):
            email = verification.get('email')
            
            # Allow response updates - don't block existing responses
            # existing_response = SurveyResponse.query.filter_by(respondent_email=email).first()
            # if existing_response:
            #     # Show completion message instead of survey form
            #     return render_template('conversational_survey_completed.html', 
            #                          email=email,
            #                          user_email=email,
            #                          completion_date=existing_response.created_at.strftime("%B %d, %Y"),
            #                          show_alternatives=True)
            
            session['auth_token'] = token
            session['auth_email'] = email
            return render_template('conversational_survey.html', authenticated=True, email=email, user_email=email)
        else:
            return render_template('conversational_survey.html', authenticated=False, error="Invalid or expired token", user_email=None)
    else:
        # Check if already authenticated via session
        if session.get('auth_token'):
            email = session.get('auth_email')
            
            # Allow response updates - don't block existing responses
            # existing_response = SurveyResponse.query.filter_by(respondent_email=email).first()
            # if existing_response:
            #     # Show completion message instead of survey form
            #     return render_template('conversational_survey_completed.html', 
            #                          email=email,
            #                          user_email=email,
            #                          completion_date=existing_response.created_at.strftime("%B %d, %Y"),
            #                          show_alternatives=True)
                                     
            return render_template('conversational_survey.html', authenticated=True, email=email, user_email=email)
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
        tenure_with_fc = data.get('tenure_with_fc', '').strip()
        
        if not company_name or not respondent_name or not respondent_email or not tenure_with_fc:
            return jsonify({'error': 'All fields are required'}), 400
        
        # Debug logging
        logger.info(f"Starting conversation for {respondent_name} with tenure: {tenure_with_fc}")
        
        # Start conversation with AI, passing the tenure data
        conversation_response = start_ai_conversational_survey(company_name, respondent_name, tenure_with_fc)
        
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
        
        # Process response with AI
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
        
        # Add authenticated email and conversation ID to survey data
        survey_data['respondent_email'] = authenticated_email
        survey_data['conversation_id'] = conversation_id
        survey_data['conversation_history'] = json.dumps(messages)
        
        # Convert conversational data to structured survey format
        structured_data = finalize_ai_conversational_survey(survey_data)
        
        # Get active campaign for automatic assignment
        active_campaign = Campaign.get_active_campaign('archelo_group')
        campaign_id = active_campaign.id if active_campaign else None
        
        # Check for existing response to update instead of creating duplicate
        existing_response = SurveyResponse.query.filter_by(
            respondent_email=authenticated_email
        ).first()
        
        if existing_response:
            # Update existing response with campaign assignment
            existing_response.company_name = normalize_company_name(structured_data.get('company_name'))
            existing_response.respondent_name = structured_data.get('respondent_name')
            existing_response.tenure_with_fc = structured_data.get('tenure_with_fc')
            existing_response.nps_score = structured_data.get('nps_score')
            existing_response.satisfaction_rating = structured_data.get('satisfaction_rating')
            existing_response.product_value_rating = structured_data.get('product_value_rating')
            existing_response.service_rating = structured_data.get('service_rating')
            existing_response.pricing_rating = structured_data.get('pricing_rating')
            existing_response.improvement_feedback = structured_data.get('improvement_feedback')
            existing_response.recommendation_reason = structured_data.get('recommendation_reason')
            existing_response.additional_comments = structured_data.get('additional_comments')
            # Update campaign if there's an active one, otherwise preserve existing
            if campaign_id:
                existing_response.campaign_id = campaign_id

            response = existing_response
        else:
            # Create survey response record with normalized company name and campaign assignment
            response = SurveyResponse(
                company_name=normalize_company_name(structured_data.get('company_name')),
                respondent_name=structured_data.get('respondent_name'),
                respondent_email=authenticated_email,
                tenure_with_fc=structured_data.get('tenure_with_fc'),
                nps_score=structured_data.get('nps_score'),
                satisfaction_rating=structured_data.get('satisfaction_rating'),
                product_value_rating=structured_data.get('product_value_rating'),
                service_rating=structured_data.get('service_rating'),
                pricing_rating=structured_data.get('pricing_rating'),
                improvement_feedback=structured_data.get('improvement_feedback'),
                recommendation_reason=structured_data.get('recommendation_reason'),
                additional_comments=structured_data.get('additional_comments'),
                campaign_id=campaign_id
            )
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
        user_responses = SurveyResponse.query.filter_by(
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
