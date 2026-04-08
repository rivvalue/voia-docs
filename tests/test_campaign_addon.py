"""
Tests for Task #101 — Campaign Slot Editing (simplified approach).

Covers:
1. can_activate_campaign() respects max_campaigns_per_year on the license record
2. get_license_info() exposes campaigns_limit from max_campaigns_per_year
3. Admin edit route GET — loads form correctly
4. Admin edit route POST — updates max_campaigns_per_year and creates audit log
5. Admin edit route POST — rejects value below campaigns used this period
6. Admin edit route POST — rejects non-numeric input
7. Admin edit route POST — rejects value < 1
8. Route requires platform-admin access (non-admin is redirected)
9. Route 404s for unknown business ID
10. Route redirects when no active license
"""
import uuid
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_account(db_session, account_type='customer'):
    from models import BusinessAccount
    account = BusinessAccount(
        name=f'CSlot Test {uuid.uuid4().hex[:6]}',
        account_type=account_type,
        status='active',
    )
    db_session.add(account)
    db_session.flush()
    return account


def _make_user(db_session, account, *, role='admin', email=None):
    from models import BusinessAccountUser
    from werkzeug.security import generate_password_hash
    if email is None:
        email = f'user_{uuid.uuid4().hex[:8]}@example.com'
    user = BusinessAccountUser(
        business_account_id=account.id,
        email=email,
        password_hash=generate_password_hash('Password1!'),
        first_name='Test',
        last_name='Admin',
        role=role,
        is_active_user=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _make_platform_admin_user(db_session):
    """Return the pre-existing admin@voia.com user (a hardcoded platform admin email)."""
    from models import BusinessAccountUser, BusinessAccount
    user = BusinessAccountUser.query.filter_by(email='admin@voia.com').first()
    if user:
        return user, user.business_account
    from werkzeug.security import generate_password_hash
    platform_account = BusinessAccount(
        name=f'Platform {uuid.uuid4().hex[:6]}',
        account_type='platform_owner',
        status='active',
    )
    db_session.add(platform_account)
    db_session.flush()
    user = BusinessAccountUser(
        business_account_id=platform_account.id,
        email='admin@voia.com',
        password_hash=generate_password_hash('Password1!'),
        first_name='Platform',
        last_name='Admin',
        role='platform_admin',
        is_active_user=True,
    )
    db_session.add(user)
    db_session.flush()
    return user, platform_account


def _make_license(db_session, account, license_type='core', max_campaigns=4):
    from models import LicenseHistory
    now = datetime.utcnow()
    lic = LicenseHistory(
        business_account_id=account.id,
        license_type=license_type,
        status='active',
        activated_at=now,
        expires_at=now + timedelta(days=365),
        max_users=10,
        max_campaigns_per_year=max_campaigns,
    )
    db_session.add(lic)
    db_session.flush()
    return lic


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------

class TestCanActivateCampaign:
    def test_within_limit_allowed(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, max_campaigns=4)
        db_session.commit()
        with patch.object(LicenseService, 'get_campaigns_used_in_current_period', return_value=2):
            result = LicenseService.can_activate_campaign(account.id)
        assert result is True

    def test_at_limit_blocked(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, max_campaigns=4)
        db_session.commit()
        with patch.object(LicenseService, 'get_campaigns_used_in_current_period', return_value=4):
            result = LicenseService.can_activate_campaign(account.id)
        assert result is False

    def test_higher_limit_allows_more(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, max_campaigns=10)
        db_session.commit()
        with patch.object(LicenseService, 'get_campaigns_used_in_current_period', return_value=9):
            result = LicenseService.can_activate_campaign(account.id)
        assert result is True

    def test_no_license_falls_back_to_default(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        db_session.commit()
        with patch.object(LicenseService, 'get_campaigns_used_in_current_period', return_value=0):
            result = LicenseService.can_activate_campaign(account.id)
        assert result is True

    def test_high_max_campaigns_allows_many(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, license_type='pro', max_campaigns=100)
        db_session.commit()
        with patch.object(LicenseService, 'get_campaigns_used_in_current_period', return_value=50):
            result = LicenseService.can_activate_campaign(account.id)
        assert result is True


class TestGetLicenseInfo:
    def test_campaigns_limit_reflects_max_campaigns_per_year(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, max_campaigns=7)
        db_session.commit()
        info = LicenseService.get_license_info(account.id)
        assert info['campaigns_limit'] == 7

    def test_no_legacy_addon_fields_present(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, max_campaigns=4)
        db_session.commit()
        info = LicenseService.get_license_info(account.id)
        assert 'campaigns_addon_slots' not in info
        assert 'campaigns_total_limit' not in info


# ---------------------------------------------------------------------------
# Route tests
# ---------------------------------------------------------------------------

@pytest.fixture
def platform_admin_client(db_session, client):
    """Return a test client logged in as a platform admin."""
    user, account = _make_platform_admin_user(db_session)
    db_session.commit()
    with client.session_transaction() as sess:
        sess['business_user_id'] = user.id
        sess['business_account_id'] = account.id
    return client, account, user


class TestEditCampaignSlotsRoute:
    def _make_licensed_account(self, db_session, max_campaigns=4):
        account = _make_account(db_session)
        lic = _make_license(db_session, account, max_campaigns=max_campaigns)
        db_session.commit()
        return account, lic

    def test_get_loads_form(self, platform_admin_client, db_session):
        client, _, _ = platform_admin_client
        account, _ = self._make_licensed_account(db_session)
        resp = client.get(f'/business/admin/licenses/campaign-slots/{account.uuid}')
        assert resp.status_code == 200
        assert b'Edit Campaign Slots' in resp.data

    def test_post_updates_limit(self, platform_admin_client, db_session):
        client, _, _ = platform_admin_client
        account, lic = self._make_licensed_account(db_session, max_campaigns=4)
        with patch('business_auth_routes.LicenseService.get_campaigns_used_in_current_period', return_value=1):
            resp = client.post(
                f'/business/admin/licenses/campaign-slots/{account.uuid}',
                data={'new_limit': '8', 'notes': 'contract ext'},
                follow_redirects=False,
            )
        db_session.refresh(lic)
        assert lic.max_campaigns_per_year == 8
        assert resp.status_code == 302

    def test_post_rejects_below_used(self, platform_admin_client, db_session):
        client, _, _ = platform_admin_client
        account, lic = self._make_licensed_account(db_session, max_campaigns=4)
        with patch('business_auth_routes.LicenseService.get_campaigns_used_in_current_period', return_value=3):
            resp = client.post(
                f'/business/admin/licenses/campaign-slots/{account.uuid}',
                data={'new_limit': '2', 'notes': ''},
                follow_redirects=True,
            )
        db_session.refresh(lic)
        assert lic.max_campaigns_per_year == 4
        assert b'Cannot set limit below' in resp.data

    def test_post_rejects_non_numeric(self, platform_admin_client, db_session):
        client, _, _ = platform_admin_client
        account, lic = self._make_licensed_account(db_session, max_campaigns=4)
        with patch('business_auth_routes.LicenseService.get_campaigns_used_in_current_period', return_value=0):
            resp = client.post(
                f'/business/admin/licenses/campaign-slots/{account.uuid}',
                data={'new_limit': 'abc', 'notes': ''},
                follow_redirects=True,
            )
        db_session.refresh(lic)
        assert lic.max_campaigns_per_year == 4
        assert b'valid positive number' in resp.data

    def test_post_rejects_zero(self, platform_admin_client, db_session):
        client, _, _ = platform_admin_client
        account, lic = self._make_licensed_account(db_session, max_campaigns=4)
        with patch('business_auth_routes.LicenseService.get_campaigns_used_in_current_period', return_value=0):
            resp = client.post(
                f'/business/admin/licenses/campaign-slots/{account.uuid}',
                data={'new_limit': '0', 'notes': ''},
                follow_redirects=True,
            )
        db_session.refresh(lic)
        assert lic.max_campaigns_per_year == 4
        assert b'valid positive number' in resp.data

    def test_non_admin_redirected(self, db_session, client):
        account = _make_account(db_session)
        _make_license(db_session, account)
        regular_user = _make_user(db_session, account, role='admin')
        db_session.commit()
        with client.session_transaction() as sess:
            sess['business_user_id'] = regular_user.id
            sess['business_account_id'] = account.id
        resp = client.get(f'/business/admin/licenses/campaign-slots/{account.uuid}')
        assert resp.status_code in (302, 403)

    def test_unknown_uuid_not_found(self, platform_admin_client, db_session):
        client, _, _ = platform_admin_client
        unknown = str(uuid.uuid4())
        resp = client.get(f'/business/admin/licenses/campaign-slots/{unknown}')
        assert resp.status_code in (302, 404)

    def test_no_license_redirects(self, platform_admin_client, db_session):
        client, _, _ = platform_admin_client
        account = _make_account(db_session)
        db_session.commit()
        resp = client.get(f'/business/admin/licenses/campaign-slots/{account.uuid}')
        assert resp.status_code == 302

    def test_audit_log_queued_on_update(self, platform_admin_client, db_session):
        client, _, _ = platform_admin_client
        account, lic = self._make_licensed_account(db_session, max_campaigns=4)
        with patch('business_auth_routes.LicenseService.get_campaigns_used_in_current_period', return_value=0), \
             patch('business_auth_routes.queue_audit_log') as mock_audit:
            client.post(
                f'/business/admin/licenses/campaign-slots/{account.uuid}',
                data={'new_limit': '6', 'notes': 'test'},
                follow_redirects=False,
            )
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args[1]
        assert call_kwargs['action_type'] == 'campaign_limit_updated'
        assert call_kwargs['details']['old_limit'] == 4
        assert call_kwargs['details']['new_limit'] == 6
