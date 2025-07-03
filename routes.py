from flask import render_template, request, jsonify, flash, redirect, url_for
from app import app, db
from models import SurveyResponse
from ai_analysis import analyze_survey_response
from data_storage import get_dashboard_data
import json
import logging

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Landing page with survey overview"""
    return render_template('index.html')

@app.route('/survey')
def survey():
    """Main survey page"""
    return render_template('survey.html')

@app.route('/submit_survey', methods=['POST'])
def submit_survey():
    """Handle survey submission and trigger AI analysis"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['company_name', 'respondent_name', 'respondent_email', 'nps_score']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Determine NPS category
        nps_score = int(data['nps_score'])
        if nps_score >= 9:
            nps_category = 'Promoter'
        elif nps_score >= 7:
            nps_category = 'Passive'
        else:
            nps_category = 'Detractor'
        
        # Create survey response
        response = SurveyResponse(
            company_name=data['company_name'],
            respondent_name=data['respondent_name'],
            respondent_email=data['respondent_email'],
            nps_score=nps_score,
            nps_category=nps_category,
            satisfaction_rating=data.get('satisfaction_rating'),
            product_value_rating=data.get('product_value_rating'),
            service_rating=data.get('service_rating'),
            pricing_rating=data.get('pricing_rating'),
            improvement_feedback=data.get('improvement_feedback'),
            recommendation_reason=data.get('recommendation_reason'),
            additional_comments=data.get('additional_comments')
        )
        
        db.session.add(response)
        db.session.commit()
        
        # Perform AI analysis
        try:
            analyze_survey_response(response.id)
            analysis_status = "completed"
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            analysis_status = "failed"
        
        return jsonify({
            'message': 'Survey submitted successfully',
            'response_id': response.id,
            'analysis_status': analysis_status
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
    """API endpoint for survey responses"""
    try:
        responses = SurveyResponse.query.order_by(SurveyResponse.created_at.desc()).all()
        return jsonify([response.to_dict() for response in responses])
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
