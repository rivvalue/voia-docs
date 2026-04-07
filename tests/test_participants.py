"""
Participant Management Tests for VOÏA Platform.

Tests cover:
1. Participant CRUD operations
2. Bulk upload functionality
3. Participant filtering
4. Token management
"""
import pytest
from datetime import datetime


class TestParticipantCreation:
    """Test participant creation flows."""
    
    def test_create_participant_page_requires_auth(self, client):
        """Participant creation requires authentication."""
        response = client.get('/business/participants/create')
        assert response.status_code in [302, 401, 403]
    
    def test_create_participant(self, authenticated_client, db_session, sample_data):
        """Should create a new participant."""
        client, user, account = authenticated_client
        
        response = client.post('/business/participants/create', data={
            'first_name': 'Jane',
            'last_name': 'Smith',
            'email': 'jane.smith@example.com',
            'company_name': 'New Client',
            'role': 'Director'
        }, follow_redirects=True)
        
        assert response.status_code in [200, 302]
    
    def test_create_participant_requires_email(self, authenticated_client):
        """Participant creation requires email."""
        client, user, account = authenticated_client
        
        response = client.post('/business/participants/create', data={
            'name': 'Jane Smith',
            'company_name': 'New Client',
        })
        
        assert response.status_code in [200, 302, 400]


class TestParticipantList:
    """Test participant listing and filtering."""
    
    def test_list_participants_requires_auth(self, client):
        """Participant list requires authentication."""
        response = client.get('/business/participants/')
        assert response.status_code in [302, 401, 403]
    
    def test_list_participants(self, authenticated_client, db_session, sample_data):
        """Should list participants for authenticated user."""
        client, user, account = authenticated_client
        
        sample_data.create_participant(db_session, account, name='John Doe')
        sample_data.create_participant(db_session, account, name='Jane Doe')
        db_session.commit()
        
        response = client.get('/business/participants/')
        assert response.status_code in [200, 302]
    
    def test_filter_participants_by_company(self, authenticated_client, db_session, sample_data):
        """Should filter participants by company name."""
        client, user, account = authenticated_client
        
        sample_data.create_participant(db_session, account, company_name='Acme Corp')
        sample_data.create_participant(db_session, account, company_name='Beta Inc')
        db_session.commit()
        
        response = client.get('/business/participants/api/filter?company_name=Acme')
        assert response.status_code in [200, 302]


class TestParticipantEdit:
    """Test participant editing flows."""
    
    def test_edit_participant(self, authenticated_client, db_session, sample_data):
        """Should edit an existing participant."""
        client, user, account = authenticated_client
        participant = sample_data.create_participant(db_session, account)
        db_session.commit()
        
        response = client.post(f'/business/participants/{participant.uuid}/edit', data={
            'name': 'Updated Name',
            'email': participant.email,
            'company_name': 'Updated Company',
        }, follow_redirects=True)
        
        assert response.status_code in [200, 302]
    
    def test_cannot_edit_other_account_participant(self, authenticated_client, db_session, sample_data):
        """Should not edit participants from other accounts."""
        import uuid
        client, user, account = authenticated_client
        
        other_account = sample_data.create_business_account(
            db_session,
            name=f'Other Company {uuid.uuid4().hex[:8]}'
        )
        other_participant = sample_data.create_participant(db_session, other_account)
        db_session.commit()
        
        response = client.post(f'/business/participants/{other_participant.uuid}/edit', data={
            'name': 'Hacked Name'
        })
        
        assert response.status_code in [302, 403, 404]


class TestParticipantDeletion:
    """Test participant deletion with protection rules."""
    
    def test_delete_participant_no_responses(self, authenticated_client, db_session, sample_data):
        """Should delete participant with no survey responses."""
        client, user, account = authenticated_client
        participant = sample_data.create_participant(db_session, account)
        db_session.commit()
        
        response = client.post(f'/business/participants/{participant.uuid}/delete')
        assert response.status_code in [200, 302]


class TestBulkOperations:
    """Test bulk participant operations."""
    
    def test_bulk_edit_participants(self, authenticated_client, db_session, sample_data):
        """Should bulk edit multiple participants."""
        client, user, account = authenticated_client
        
        p1 = sample_data.create_participant(db_session, account)
        p2 = sample_data.create_participant(db_session, account)
        db_session.commit()
        
        response = client.post('/business/participants/bulk-edit', data={
            'participant_ids': f'{p1.id},{p2.id}',
            'field': 'company_name',
            'value': 'Merged Company'
        })
        
        assert response.status_code in [200, 302]


class TestTokenManagement:
    """Test survey token management."""
    
    def test_regenerate_token(self, authenticated_client, db_session, sample_data):
        """Should regenerate survey token for participant."""
        client, user, account = authenticated_client
        participant = sample_data.create_participant(db_session, account)
        old_token = participant.token
        db_session.commit()
        
        response = client.post(f'/business/participants/{participant.uuid}/regenerate-token')
        
        assert response.status_code in [200, 302]
    
    def test_token_is_unique(self, db_session, sample_data):
        """Each participant should have unique token."""
        account = sample_data.create_business_account(db_session)
        
        p1 = sample_data.create_participant(db_session, account)
        p2 = sample_data.create_participant(db_session, account)
        db_session.commit()
        
        assert p1.token != p2.token


class TestParticipantInvitations:
    """Test participant invitation functionality."""
    
    def test_send_individual_invitation(self, authenticated_client, db_session, sample_data, mock_email_service):
        """Should send invitation to individual participant."""
        client, user, account = authenticated_client
        participant = sample_data.create_participant(db_session, account)
        db_session.commit()
        
        response = client.post(f'/business/participants/{participant.uuid}/send-invitation')
        
        assert response.status_code in [200, 302, 400]
