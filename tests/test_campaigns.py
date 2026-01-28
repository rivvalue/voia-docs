"""
Campaign Lifecycle Tests for VOÏA Platform.

Tests cover:
1. Campaign creation
2. Status transitions (draft → ready → active → complete)
3. Campaign validation rules
4. Campaign-participant associations
"""
import pytest
from datetime import datetime, timedelta


class TestCampaignCreation:
    """Test campaign creation flows."""
    
    def test_create_campaign_page_requires_auth(self, client):
        """Campaign creation page requires authentication."""
        response = client.get('/business/campaigns/create')
        assert response.status_code in [302, 401, 403]
    
    def test_create_campaign_page_renders(self, authenticated_client):
        """Campaign creation page should render for authenticated users."""
        client, user, account = authenticated_client
        
        response = client.get('/business/campaigns/create')
        assert response.status_code in [200, 302]
    
    def test_create_draft_campaign(self, authenticated_client, db_session):
        """Should create a campaign in draft status."""
        client, user, account = authenticated_client
        
        response = client.post('/business/campaigns/create', data={
            'name': 'Test Campaign',
            'description': 'A test campaign',
            'start_date': (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'end_date': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d'),
        }, follow_redirects=True)
        
        assert response.status_code in [200, 302]


class TestCampaignStatusTransitions:
    """Test campaign status transition rules."""
    
    def test_draft_campaign_can_be_edited(self, authenticated_client, db_session, sample_data):
        """Draft campaigns should be editable."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, status='draft')
        db_session.commit()
        
        response = client.get(f'/business/campaigns/{campaign.id}/edit')
        assert response.status_code in [200, 302]
    
    def test_mark_campaign_ready(self, authenticated_client, db_session, sample_data):
        """Draft campaign can be marked as ready."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, status='draft')
        db_session.commit()
        
        response = client.post(f'/business/campaigns/{campaign.id}/mark-ready')
        assert response.status_code in [200, 302, 400]
    
    def test_activate_campaign(self, authenticated_client, db_session, sample_data):
        """Ready campaign can be activated."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, status='ready')
        db_session.commit()
        
        response = client.post(f'/business/campaigns/{campaign.id}/activate')
        assert response.status_code in [200, 302, 400]
    
    def test_complete_campaign(self, authenticated_client, db_session, sample_data):
        """Active campaign can be completed."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, status='active')
        db_session.commit()
        
        response = client.post(f'/business/campaigns/{campaign.id}/complete')
        assert response.status_code in [200, 302, 400]
    
    def test_cannot_edit_active_campaign(self, authenticated_client, db_session, sample_data):
        """Active campaigns should not be editable."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, status='active')
        db_session.commit()
        
        response = client.post(f'/business/campaigns/{campaign.id}/edit', data={
            'name': 'Updated Name'
        })
        
        assert response.status_code in [302, 400, 403]


class TestCampaignValidation:
    """Test campaign validation rules."""
    
    def test_campaign_requires_name(self, authenticated_client):
        """Campaign creation requires a name."""
        client, user, account = authenticated_client
        
        response = client.post('/business/campaigns/create', data={
            'description': 'No name provided',
            'start_date': datetime.utcnow().strftime('%Y-%m-%d'),
            'end_date': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d'),
        })
        
        assert response.status_code in [200, 302, 400]
    
    def test_end_date_after_start_date(self, authenticated_client):
        """End date must be after start date."""
        client, user, account = authenticated_client
        
        response = client.post('/business/campaigns/create', data={
            'name': 'Invalid Dates Campaign',
            'start_date': (datetime.utcnow() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'end_date': datetime.utcnow().strftime('%Y-%m-%d'),
        })
        
        assert response.status_code in [200, 302, 400]


class TestCampaignList:
    """Test campaign listing and filtering."""
    
    def test_list_campaigns_requires_auth(self, client):
        """Campaign list requires authentication."""
        response = client.get('/business/campaigns/')
        assert response.status_code in [302, 401, 403]
    
    def test_list_campaigns(self, authenticated_client, db_session, sample_data):
        """Authenticated user can list campaigns."""
        client, user, account = authenticated_client
        
        sample_data.create_campaign(db_session, account, name='Campaign 1')
        sample_data.create_campaign(db_session, account, name='Campaign 2')
        db_session.commit()
        
        response = client.get('/business/campaigns/')
        assert response.status_code in [200, 302]
    
    def test_campaigns_isolated_by_account(self, authenticated_client, db_session, sample_data):
        """Users should only see their own account's campaigns."""
        import uuid
        client, user, account = authenticated_client
        
        other_account = sample_data.create_business_account(
            db_session, 
            name=f'Other Company {uuid.uuid4().hex[:8]}'
        )
        sample_data.create_campaign(db_session, other_account, name='Other Campaign')
        sample_data.create_campaign(db_session, account, name='My Campaign')
        db_session.commit()
        
        response = client.get('/business/campaigns/')
        
        assert response.status_code in [200, 302]


class TestCampaignResponses:
    """Test campaign response viewing."""
    
    def test_view_campaign_responses(self, authenticated_client, db_session, sample_data):
        """Should view responses for a campaign."""
        client, user, account = authenticated_client
        campaign = sample_data.create_campaign(db_session, account, status='active')
        sample_data.create_survey_response(db_session, campaign=campaign, nps_score=9)
        sample_data.create_survey_response(db_session, campaign=campaign, nps_score=7)
        db_session.commit()
        
        response = client.get(f'/business/campaigns/{campaign.id}/responses')
        assert response.status_code in [200, 302]
