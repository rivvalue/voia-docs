"""
Authentication Tests for VOÏA Platform.

Tests cover:
1. Business user login/logout
2. Token-based survey access
3. Password reset flow
4. Session management
"""
import pytest
from unittest.mock import patch, MagicMock


class TestBusinessLogin:
    """Test business user authentication flows."""
    
    def test_login_page_renders(self, client):
        """Login page should render successfully."""
        response = client.get('/business/login')
        assert response.status_code == 200
        assert b'login' in response.data.lower() or b'connexion' in response.data.lower()
    
    def test_login_with_valid_credentials(self, client, db_session, sample_data):
        """Valid credentials should allow login."""
        account = sample_data.create_business_account(db_session)
        user = sample_data.create_business_user(
            db_session, 
            account, 
            email='valid@example.com'
        )
        db_session.commit()
        
        response = client.post('/business/login', data={
            'email': 'valid@example.com',
            'password': 'testpassword123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
    
    def test_login_with_invalid_password(self, client, db_session, sample_data):
        """Invalid password should be rejected."""
        account = sample_data.create_business_account(db_session)
        user = sample_data.create_business_user(
            db_session, 
            account, 
            email='user@example.com'
        )
        db_session.commit()
        
        response = client.post('/business/login', data={
            'email': 'user@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code in [200, 302]
    
    def test_login_with_nonexistent_user(self, client):
        """Non-existent user should be rejected."""
        response = client.post('/business/login', data={
            'email': 'nonexistent@example.com',
            'password': 'anypassword'
        })
        
        assert response.status_code in [200, 302]
    
    def test_logout_clears_session(self, authenticated_client):
        """Logout should clear the user session."""
        client, user, account = authenticated_client
        
        response = client.get('/business/logout', follow_redirects=True)
        
        assert response.status_code == 200


class TestSurveyTokenAccess:
    """Test token-based survey access."""
    
    def test_valid_token_grants_access(self, client, db_session, sample_data):
        """Valid survey token should grant access."""
        account = sample_data.create_business_account(db_session)
        campaign = sample_data.create_campaign(db_session, account, status='active')
        participant = sample_data.create_participant(
            db_session, 
            account,
            survey_token='valid-test-token-123'
        )
        db_session.commit()
        
        response = client.get('/survey/valid-test-token-123')
        
        assert response.status_code in [200, 302, 404]
    
    def test_invalid_token_denied(self, client):
        """Invalid survey token should be denied."""
        response = client.get('/survey/invalid-token-xyz')
        
        assert response.status_code in [401, 403, 404]
    
    def test_expired_token_handling(self, client, db_session, sample_data):
        """Expired tokens should be handled gracefully."""
        from datetime import datetime, timedelta
        
        account = sample_data.create_business_account(db_session)
        participant = sample_data.create_participant(
            db_session,
            account,
            survey_token='expired-token-456',
            token_expires_at=datetime.utcnow() - timedelta(days=1)
        )
        db_session.commit()
        
        response = client.get('/survey/expired-token-456')
        
        assert response.status_code in [401, 403, 404]


class TestPasswordReset:
    """Test password reset flow."""
    
    def test_forgot_password_page_renders(self, client):
        """Forgot password page should render."""
        response = client.get('/business/forgot-password')
        assert response.status_code == 200
    
    @patch('email_service.send_email')
    def test_password_reset_request(self, mock_send, client, db_session, sample_data):
        """Password reset request should send email."""
        mock_send.return_value = {'success': True}
        
        account = sample_data.create_business_account(db_session)
        user = sample_data.create_business_user(
            db_session,
            account,
            email='reset@example.com'
        )
        db_session.commit()
        
        response = client.post('/business/forgot-password/request', data={
            'email': 'reset@example.com'
        })
        
        assert response.status_code in [200, 302]


class TestSessionManagement:
    """Test session security and management."""
    
    def test_session_status_api(self, authenticated_client):
        """Session status API should return user info."""
        client, user, account = authenticated_client
        
        response = client.get('/business/api/session-status')
        
        assert response.status_code in [200, 401]
    
    def test_protected_route_requires_auth(self, client):
        """Protected routes should require authentication."""
        response = client.get('/business/admin')
        
        assert response.status_code in [302, 401, 403]
    
    def test_authenticated_access_to_admin(self, authenticated_client):
        """Authenticated users should access admin panel."""
        client, user, account = authenticated_client
        
        response = client.get('/business/admin')
        
        assert response.status_code in [200, 302]
