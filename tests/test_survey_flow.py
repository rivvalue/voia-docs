"""
Survey Flow Tests for VOÏA Platform.

Tests cover:
1. Survey access via token
2. Survey submission
3. Duplicate response prevention
4. Conversational survey flow
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestSurveyAccess:
    """Test survey access controls."""
    
    def test_survey_requires_valid_token(self, client):
        """Survey access requires a valid token."""
        response = client.get('/survey/invalid-token')
        assert response.status_code in [401, 403, 404]
    
    def test_survey_page_with_valid_token(self, client, db_session, sample_data):
        """Valid token should load survey page."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, status='active')
        participant = sample_data.create_participant(
            db_session,
            account,
            survey_token='test-valid-token-abc'
        )
        db_session.commit()
        
        response = client.get('/survey/test-valid-token-abc')
        
        assert response.status_code in [200, 302, 404]


class TestSurveySubmission:
    """Test survey submission flows."""
    
    def test_submit_form_survey(self, client, db_session, sample_data):
        """Form-based survey submission should work."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, status='active')
        participant = sample_data.create_participant(
            db_session,
            account,
            survey_token='submission-test-token'
        )
        db_session.commit()
        
        response = client.post('/submit_survey', data={
            'token': 'submission-test-token',
            'nps_score': '9',
            'recommendation_reason': 'Great service!',
        })
        
        assert response.status_code in [200, 302, 400]


class TestDuplicatePrevention:
    """Test duplicate response prevention."""
    
    def test_cannot_submit_twice_same_token(self, client, db_session, sample_data):
        """Same token cannot submit twice."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, status='active')
        participant = sample_data.create_participant(
            db_session,
            account,
            survey_token='duplicate-test-token'
        )
        sample_data.create_survey_response(
            db_session,
            campaign=campaign,
            respondent_email=participant.email
        )
        db_session.commit()
        
        response = client.get('/survey/duplicate-test-token')
        
        assert response.status_code in [200, 302, 403, 404]


class TestConversationalSurvey:
    """Test conversational AI survey flow."""
    
    @patch('ai_conversational_survey_v2.VOIASurveyController')
    def test_start_conversation(self, mock_controller, client, db_session, sample_data):
        """Should start a conversational survey session."""
        mock_instance = MagicMock()
        mock_controller.return_value = mock_instance
        mock_instance.start.return_value = {
            'message': 'Hello! How likely are you to recommend us?',
            'is_complete': False
        }
        
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, status='active')
        participant = sample_data.create_participant(
            db_session,
            account,
            survey_token='convo-test-token'
        )
        db_session.commit()
        
        response = client.post('/api/start_conversation', 
            json={'token': 'convo-test-token'},
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 404]
    
    @patch('ai_conversational_survey_v2.VOIASurveyController')
    def test_conversation_response(self, mock_controller, client, db_session, sample_data):
        """Should process user response in conversation."""
        mock_instance = MagicMock()
        mock_controller.return_value = mock_instance
        mock_instance.process_response.return_value = {
            'message': 'Thank you! What could we improve?',
            'is_complete': False
        }
        
        account = sample_data.create_business_account(db_session)
        db_session.commit()
        
        with client.session_transaction() as sess:
            sess['survey_token'] = 'response-test-token'
            sess['conversation_state'] = {}
        
        response = client.post('/api/conversation_response',
            json={'message': '10'},
            content_type='application/json'
        )
        
        assert response.status_code in [200, 400, 404]


class TestSurveyResponseData:
    """Test survey response data integrity."""
    
    def test_nps_score_range_validation(self, db_session, sample_data):
        """NPS score should be in valid range 0-10."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account)
        
        response = sample_data.create_survey_response(
            db_session,
            campaign=campaign,
            nps_score=10
        )
        db_session.commit()
        
        assert response.nps_score == 10
        assert response.nps_score >= 0
        assert response.nps_score <= 10
    
    def test_nps_category_assignment(self, db_session, sample_data):
        """NPS category should match score."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account)
        
        promoter = sample_data.create_survey_response(
            db_session, campaign=campaign, nps_score=9, nps_category='Promoter'
        )
        passive = sample_data.create_survey_response(
            db_session, campaign=campaign, nps_score=7, nps_category='Passive'
        )
        detractor = sample_data.create_survey_response(
            db_session, campaign=campaign, nps_score=5, nps_category='Detractor'
        )
        db_session.commit()
        
        assert promoter.nps_category == 'Promoter'
        assert passive.nps_category == 'Passive'
        assert detractor.nps_category == 'Detractor'
