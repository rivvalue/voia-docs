"""
Pytest configuration and shared fixtures for VOÏA test suite.

Provides:
- Flask application fixtures with test configuration
- Database fixtures with transaction rollback
- Mock helpers for AI/LLM and email services
- Authentication helpers
- Sample data factories
"""
import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv('SESSION_SECRET', 'test-secret-key-for-testing')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-openai-key')
    monkeypatch.setenv('TESTING', 'true')
    monkeypatch.setenv('WTF_CSRF_ENABLED', 'false')


@pytest.fixture(scope='session')
def app():
    """Create Flask application for testing."""
    from app import app as flask_app, db
    
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost',
    })
    
    with flask_app.app_context():
        yield flask_app


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Provide application context for tests."""
    with app.app_context():
        yield


@pytest.fixture
def db_session(app):
    """
    Provide database session with automatic rollback after each test.
    This ensures test isolation without polluting the database.
    
    Uses Flask-SQLAlchemy 3.x compatible approach.
    """
    from app import db
    
    with app.app_context():
        yield db.session
        
        db.session.rollback()


@pytest.fixture
def gateway_enabled(monkeypatch):
    """Enable LLM gateway for tests."""
    monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'true')
    monkeypatch.setenv('CLAUDE_ENABLED', 'false')


@pytest.fixture
def gateway_disabled(monkeypatch):
    """Disable LLM gateway for tests."""
    monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'false')


@pytest.fixture
def claude_enabled(monkeypatch):
    """Enable Claude provider for tests."""
    monkeypatch.setenv('LLM_GATEWAY_ENABLED', 'true')
    monkeypatch.setenv('CLAUDE_ENABLED', 'true')
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'test-anthropic-key')


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"test": "response"}'
    return mock_response


@pytest.fixture
def mock_openai():
    """Mock OpenAI client for all tests."""
    with patch('openai.OpenAI') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = '{"nps_score": 10}'
        mock_instance.chat.completions.create.return_value = mock_completion
        
        yield mock_instance


@pytest.fixture
def mock_email_service():
    """Mock email service to prevent sending real emails."""
    with patch('email_service.send_email') as mock_send:
        mock_send.return_value = {'success': True, 'message_id': 'test-123'}
        yield mock_send


@pytest.fixture
def mock_transcript_response():
    """Create a mock transcript analysis response."""
    return '''{
        "NPS Score": 8,
        "NPS Category": "Passive",
        "Satisfaction Rating": 4,
        "Product Value Rating": 4,
        "Service Rating": 5,
        "Pricing Rating": 3,
        "Improvement Feedback": "Better pricing options needed",
        "Recommendation Reason": "Good service but expensive",
        "Additional Comments": "Overall satisfied with the product",
        "Sentiment Score": 0.6,
        "Sentiment Label": "Positive",
        "Key Themes": ["pricing", "service quality", "product value"],
        "Churn Risk Score": 0.3,
        "Churn Risk Level": "Low",
        "Churn Risk Factors": ["pricing concerns"],
        "Growth Opportunities": ["upsell premium features"],
        "Account Risk Factors": [],
        "Growth Factor": 1.5,
        "Growth Rate": "15%",
        "Growth Range": "7-8"
    }'''


class SampleDataFactory:
    """Factory for creating sample test data."""
    
    @staticmethod
    def create_business_account(db_session, **kwargs):
        """Create a sample business account."""
        from models import BusinessAccount
        
        defaults = {
            'name': 'Test Company Inc.',
            'account_type': 'customer',
            'status': 'active',
        }
        defaults.update(kwargs)
        
        account = BusinessAccount(**defaults)
        db_session.add(account)
        db_session.flush()
        return account
    
    @staticmethod
    def create_business_user(db_session, business_account, **kwargs):
        """Create a sample business user."""
        from models import BusinessAccountUser
        from werkzeug.security import generate_password_hash
        
        defaults = {
            'email': 'testuser@example.com',
            'password_hash': generate_password_hash('testpassword123'),
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'admin',
            'is_active_user': True,
            'email_verified': True,
            'business_account_id': business_account.id,
        }
        defaults.update(kwargs)
        
        user = BusinessAccountUser(**defaults)
        db_session.add(user)
        db_session.flush()
        return user
    
    @staticmethod
    def create_campaign(db_session, business_account, **kwargs):
        """Create a sample campaign."""
        from models import Campaign
        
        defaults = {
            'name': 'Test Campaign',
            'description': 'A test campaign for automated testing',
            'status': 'draft',
            'business_account_id': business_account.id,
            'start_date': datetime.utcnow().date(),
            'end_date': (datetime.utcnow() + timedelta(days=30)).date(),
            'created_at': datetime.utcnow(),
        }
        defaults.update(kwargs)
        
        campaign = Campaign(**defaults)
        db_session.add(campaign)
        db_session.flush()
        return campaign
    
    @staticmethod
    def create_participant(db_session, business_account, **kwargs):
        """Create a sample participant."""
        from models import Participant
        import secrets
        
        defaults = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'company_name': 'Client Company',
            'role': 'Manager',
            'survey_token': secrets.token_urlsafe(32),
            'business_account_id': business_account.id,
            'created_at': datetime.utcnow(),
        }
        defaults.update(kwargs)
        
        participant = Participant(**defaults)
        db_session.add(participant)
        db_session.flush()
        return participant
    
    @staticmethod
    def create_survey_response(db_session, campaign=None, participant=None, **kwargs):
        """Create a sample survey response."""
        from models import SurveyResponse
        
        defaults = {
            'company_name': 'Client Company',
            'respondent_name': 'John Doe',
            'respondent_email': 'john.doe@example.com',
            'nps_score': 8,
            'nps_category': 'Passive',
            'satisfaction_rating': 4,
            'source_type': 'conversational',
            'created_at': datetime.utcnow(),
        }
        if campaign:
            defaults['campaign_id'] = campaign.id
        if participant:
            defaults['campaign_participant_id'] = participant.id
            
        defaults.update(kwargs)
        
        response = SurveyResponse(**defaults)
        db_session.add(response)
        db_session.flush()
        return response


@pytest.fixture
def sample_data(db_session):
    """Provide sample data factory for tests."""
    return SampleDataFactory()


@pytest.fixture
def authenticated_client(client, db_session, sample_data):
    """
    Provide an authenticated test client.
    Creates a business account and user, then logs in.
    """
    account = sample_data.create_business_account(db_session)
    user = sample_data.create_business_user(db_session, account, email='test@example.com')
    db_session.commit()
    
    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['business_account_id'] = account.id
        sess['user_email'] = user.email
    
    return client, user, account


class MockLLMResponses:
    """Pre-defined mock responses for LLM calls."""
    
    NPS_EXTRACTION_10 = '{"nps_score": 10}'
    NPS_EXTRACTION_8 = '{"nps_score": 8}'
    PRICING_EXTRACTION_8 = '{"pricing_value_rating": 4}'
    
    QUESTION_GENERATION = "How would you rate your overall experience with our services?"
    
    SENTIMENT_POSITIVE = '{"sentiment_score": 0.8, "sentiment_label": "Positive"}'
    SENTIMENT_NEGATIVE = '{"sentiment_score": 0.2, "sentiment_label": "Negative"}'
    
    @classmethod
    def get_extraction_response(cls, nps=None, pricing=None, service=None):
        """Build a custom extraction response."""
        data = {}
        if nps is not None:
            data['nps_score'] = nps
        if pricing is not None:
            data['pricing_value_rating'] = pricing
        if service is not None:
            data['service_rating'] = service
        
        import json
        return json.dumps(data)


@pytest.fixture
def mock_llm_responses():
    """Provide mock LLM responses for tests."""
    return MockLLMResponses()
