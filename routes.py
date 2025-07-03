from flask import render_template, request, jsonify, flash, redirect, url_for, g
from app import app, db
from models import SurveyResponse
from models_auth import AuthToken
from data_storage import get_dashboard_data
from task_queue import add_analysis_task, get_queue_stats
from rate_limiter import rate_limit
from auth_system import require_auth, generate_user_token
from datetime import datetime, timedelta
import json
import logging
import re

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Landing page with survey overview"""
    return render_template('index.html')

@app.route('/auth/request-token', methods=['POST'])
@rate_limit(limit=5)  # 5 token requests per minute per IP
def request_token():
    """Generate authentication token for email address"""
    try:
        data = request.json
        if not data or 'email' not in data:
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
        token_record = AuthToken(
            email=email,
            token_id=token[-16:],  # Use last 16 chars as token ID
            expires_at=datetime.utcnow() + timedelta(hours=24),
            ip_address=request.environ.get('HTTP_X_FORWARDED_FOR', 
                                         request.environ.get('REMOTE_ADDR')),
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
        return jsonify({
            'error': 'Failed to generate authentication token',
            'code': 'TOKEN_GENERATION_FAILED'
        }), 500

@app.route('/auth/verify-token', methods=['POST'])
def verify_token():
    """Verify if a token is valid"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'valid': False,
                'error': 'No authorization header provided'
            }), 400
        
        from auth_system import verify_user_token
        email = verify_user_token(auth_header)
        
        return jsonify({
            'valid': True,
            'email': email,
            'message': 'Token is valid'
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 401

@app.route('/auth')
def auth():
    """Authentication page for token generation"""
    return render_template('auth.html')

@app.route('/survey')
def survey():
    """Main survey page"""
    return render_template('survey.html')

@app.route('/submit_survey', methods=['POST'])
@require_auth(allow_overwrite=False)  # Require authentication, no overwrites by default
@rate_limit(limit=10)  # 10 survey submissions per minute per IP
def submit_survey():
    """Handle authenticated survey submission and prevent duplicates"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Get authenticated email from Flask's g object
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
        
        # Handle existing response (this should not happen with allow_overwrite=False)
        if existing_response:
            return jsonify({
                'error': 'You have already submitted a response',
                'existing_response_id': existing_response.id,
                'submitted_at': existing_response.created_at.isoformat()
            }), 409
        
        # Create new survey response with authenticated email
        response = SurveyResponse(
            company_name=data['company_name'],
            respondent_name=data['respondent_name'],
            respondent_email=authenticated_email,  # Use authenticated email
            nps_score=nps_score,
            nps_category=nps_category,
            satisfaction_rating=int(data['satisfaction_rating']) if data.get('satisfaction_rating') else None,
            product_value_rating=int(data['product_value_rating']) if data.get('product_value_rating') else None,
            service_rating=int(data['service_rating']) if data.get('service_rating') else None,
            pricing_rating=int(data['pricing_rating']) if data.get('pricing_rating') else None,
            improvement_feedback=data.get('improvement_feedback'),
            recommendation_reason=data.get('recommendation_reason'),
            additional_comments=data.get('additional_comments')
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
        
        logger.info(f"Survey submitted by authenticated user: {authenticated_email}")
        
        return jsonify({
            'message': 'Survey submitted successfully',
            'response_id': response.id,
            'analysis_status': analysis_status,
            'authenticated_email': authenticated_email
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
        
        if existing_response:
            # Update existing response
            existing_response.company_name = data['company_name']
            existing_response.respondent_name = data['respondent_name']
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
            
            response = existing_response
            action = "updated"
        else:
            # Create new response
            response = SurveyResponse(
                company_name=data['company_name'],
                respondent_name=data['respondent_name'],
                respondent_email=authenticated_email,
                nps_score=nps_score,
                nps_category=nps_category,
                satisfaction_rating=int(data['satisfaction_rating']) if data.get('satisfaction_rating') else None,
                product_value_rating=int(data['product_value_rating']) if data.get('product_value_rating') else None,
                service_rating=int(data['service_rating']) if data.get('service_rating') else None,
                pricing_rating=int(data['pricing_rating']) if data.get('pricing_rating') else None,
                improvement_feedback=data.get('improvement_feedback'),
                recommendation_reason=data.get('recommendation_reason'),
                additional_comments=data.get('additional_comments')
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
    return render_template('dashboard.html')

@app.route('/api/dashboard_data')
def dashboard_data():
    """API endpoint for dashboard data"""
    try:
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
def export_data():
    """Export survey data as JSON"""
    try:
        responses = SurveyResponse.query.all()
        data = [response.to_dict() for response in responses]
        return jsonify(data)
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
