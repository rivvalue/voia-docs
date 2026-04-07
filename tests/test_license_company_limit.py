"""
Tests for Task #69 — License: Client Company Count Limit.

Covers:
1. Service-level unit tests for domain counting
2. Service-level unit tests for can_add_participant_from_domain()
3. License template defaults (Core=20, Plus=100, Pro/Trial=unlimited)
4. Downgrade protection (domain count checked against target tier)
5. Single participant creation hard-blocked when new domain would breach limit
6. Bulk CSV upload rejected upfront when any row would breach limit
7. Campaign participant assignment produces soft warning (no redirect/block)
8. Platform admin bypass on participant creation
9. Consumer email domain constant completeness
"""
import io
import csv
import uuid
import secrets
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_account(db_session, account_type='customer'):
    """Create a fresh, isolated business account for a single test."""
    from models import BusinessAccount
    account = BusinessAccount(
        name=f'Company Test {uuid.uuid4().hex[:6]}',
        account_type=account_type,
        status='active',
    )
    db_session.add(account)
    db_session.flush()
    return account


def _make_user(db_session, account, *, role='admin', email=None):
    """Create a business user with specified role."""
    from models import BusinessAccountUser
    from werkzeug.security import generate_password_hash
    suffix = uuid.uuid4().hex[:8]
    user = BusinessAccountUser(
        email=email or f'user_{suffix}@pytest.example.com',
        password_hash=generate_password_hash('testpass'),
        first_name='Test',
        last_name='User',
        role=role,
        is_active_user=True,
        email_verified=True,
        business_account_id=account.id,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _make_user_session(db_session, user):
    """Create a UserSession DB record and return its session_id string."""
    from models import UserSession
    user_session = UserSession(user_id=user.id, duration_hours=24)
    db_session.add(user_session)
    db_session.flush()
    return user_session.session_id


def _make_license(db_session, account, *, license_type='core', max_client_companies=20):
    """Create an active LicenseHistory record for an account."""
    from models import LicenseHistory
    today = date.today()
    lic = LicenseHistory(
        business_account_id=account.id,
        license_type=license_type,
        status='active',
        activated_at=today,
        expires_at=today + timedelta(days=365),
        max_campaigns_per_year=4,
        max_users=5,
        max_participants_per_campaign=200,
        max_invitations_per_campaign=1000,
        max_client_companies=max_client_companies,
        created_by='pytest',
    )
    db_session.add(lic)
    db_session.flush()
    return lic


def _make_participant(db_session, account, email):
    """Create a participant with a specific email."""
    from models import Participant
    p = Participant(
        name='Test Participant',
        email=email,
        company_name='Test Corp',
        role='Manager',
        token=secrets.token_urlsafe(32),
        business_account_id=account.id,
    )
    db_session.add(p)
    db_session.flush()
    return p


def _csv_bytes(*rows):
    """Build a CSV file as bytes from a list of dicts (headers: email, name, company_name)."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=['email', 'name', 'company_name'])
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode('utf-8')


def _auth_session(client, account_id, user_id, session_id, user_email='user@test.com'):
    """Set up full business auth session including strict-validation session_id."""
    with client.session_transaction() as sess:
        sess['business_account_id'] = account_id
        sess['business_user_id'] = user_id
        sess['business_session_id'] = session_id
        sess['user_email'] = user_email


# ---------------------------------------------------------------------------
# 1. Service unit tests — domain counting
# ---------------------------------------------------------------------------

class TestGetUniqueCompanyDomainCount:
    """Unit tests for LicenseService.get_unique_company_domain_count()."""

    def test_empty_account_returns_zero(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        assert LicenseService.get_unique_company_domain_count(account.id) == 0

    def test_counts_distinct_corporate_domains(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_participant(db_session, account, 'alice@acme.com')
        _make_participant(db_session, account, 'bob@globex.com')
        assert LicenseService.get_unique_company_domain_count(account.id) == 2

    def test_same_domain_counted_once(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_participant(db_session, account, 'alice@acme.com')
        _make_participant(db_session, account, 'bob@acme.com')
        _make_participant(db_session, account, 'carol@acme.com')
        assert LicenseService.get_unique_company_domain_count(account.id) == 1

    def test_consumer_domains_excluded(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        for email in [
            'user@gmail.com', 'user@yahoo.com', 'user@hotmail.com',
            'user@outlook.com', 'user@icloud.com', 'user@protonmail.com',
        ]:
            _make_participant(db_session, account, email)
        assert LicenseService.get_unique_company_domain_count(account.id) == 0

    def test_mix_of_consumer_and_corporate(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_participant(db_session, account, 'user@gmail.com')
        _make_participant(db_session, account, 'user@acme.com')
        assert LicenseService.get_unique_company_domain_count(account.id) == 1

    def test_domain_comparison_is_case_insensitive(self, db_session):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_participant(db_session, account, 'alice@ACME.COM')
        _make_participant(db_session, account, 'bob@acme.com')
        assert LicenseService.get_unique_company_domain_count(account.id) == 1


# ---------------------------------------------------------------------------
# 2. Service unit tests — can_add_participant_from_domain()
#
#    flask.session requires a request context.  We push a test_request_context
#    for each assertion so the inline `from flask import session` works properly
#    without hitting the broad except→True fallback.
# ---------------------------------------------------------------------------

class TestCanAddParticipantFromDomain:
    """Unit tests for LicenseService.can_add_participant_from_domain()."""

    def test_consumer_domain_always_allowed(self, db_session, app):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, max_client_companies=0)
        db_session.commit()

        with app.test_request_context('/'):
            result = LicenseService.can_add_participant_from_domain(
                account.id, 'user@gmail.com'
            )
        assert result is True

    def test_null_limit_means_unlimited(self, db_session, app):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, max_client_companies=None)
        db_session.commit()

        with app.test_request_context('/'):
            result = LicenseService.can_add_participant_from_domain(
                account.id, 'user@newcompany.com'
            )
        assert result is True

    def test_new_domain_allowed_when_below_limit(self, db_session, app):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, max_client_companies=5)
        _make_participant(db_session, account, 'user@existing.com')
        db_session.commit()

        with app.test_request_context('/'):
            result = LicenseService.can_add_participant_from_domain(
                account.id, 'user@new.com'
            )
        assert result is True

    def test_new_domain_blocked_when_at_limit(self, db_session, app):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, max_client_companies=1)
        _make_participant(db_session, account, 'user@existing.com')
        db_session.commit()

        with app.test_request_context('/'):
            result = LicenseService.can_add_participant_from_domain(
                account.id, 'user@new.com'
            )
        assert result is False

    def test_existing_domain_always_passes_at_limit(self, db_session, app):
        from license_service import LicenseService
        account = _make_account(db_session)
        _make_license(db_session, account, max_client_companies=1)
        _make_participant(db_session, account, 'alice@acme.com')
        db_session.commit()

        with app.test_request_context('/'):
            result = LicenseService.can_add_participant_from_domain(
                account.id, 'bob@acme.com'
            )
        assert result is True

    def test_no_license_means_no_limit(self, db_session, app):
        from license_service import LicenseService
        account = _make_account(db_session)
        db_session.commit()

        with app.test_request_context('/'):
            result = LicenseService.can_add_participant_from_domain(
                account.id, 'user@anycompany.com'
            )
        assert result is True


# ---------------------------------------------------------------------------
# 3. License template defaults
# ---------------------------------------------------------------------------

class TestLicenseTemplateDefaults:
    """Verify per-tier max_client_companies defaults match requirements."""

    def test_core_limit_is_20(self):
        from license_templates import LicenseTemplateManager
        tmpl = LicenseTemplateManager.get_template('core')
        assert tmpl is not None
        assert tmpl.max_client_companies == 20

    def test_plus_limit_is_100(self):
        from license_templates import LicenseTemplateManager
        tmpl = LicenseTemplateManager.get_template('plus')
        assert tmpl is not None
        assert tmpl.max_client_companies == 100

    def test_pro_is_unlimited_by_default(self):
        from license_templates import LicenseTemplateManager
        tmpl = LicenseTemplateManager.get_template('pro')
        assert tmpl is not None
        assert tmpl.max_client_companies is None

    def test_trial_is_unlimited(self):
        from license_templates import LicenseTemplateManager
        tmpl = LicenseTemplateManager.get_template('trial')
        assert tmpl is not None
        assert tmpl.max_client_companies is None


# ---------------------------------------------------------------------------
# 4. Downgrade protection
# ---------------------------------------------------------------------------

class TestDowngradeProtection:
    """_validate_downgrade_usage blocks downgrades that exceed domain limit."""

    def test_plus_to_core_blocked_when_domains_exceed_20(self, db_session):
        from license_service import LicenseService
        from license_templates import LicenseTemplateManager

        account = _make_account(db_session)
        current_lic = _make_license(db_session, account, license_type='plus',
                                    max_client_companies=100)
        for i in range(21):
            _make_participant(db_session, account, f'user@company{i:02d}.com')
        db_session.commit()

        target = LicenseTemplateManager.get_template('core')
        success, message = LicenseService._validate_downgrade_usage(
            account.id, current_lic, target
        )
        assert success is False
        assert '21' in message or '20' in message

    def test_plus_to_core_allowed_when_domains_at_or_below_20(self, db_session):
        from license_service import LicenseService
        from license_templates import LicenseTemplateManager

        account = _make_account(db_session)
        current_lic = _make_license(db_session, account, license_type='plus',
                                    max_client_companies=100)
        for i in range(15):
            _make_participant(db_session, account, f'user@smallco{i:02d}.com')
        db_session.commit()

        target = LicenseTemplateManager.get_template('core')
        success, _ = LicenseService._validate_downgrade_usage(
            account.id, current_lic, target
        )
        assert success is True

    def test_downgrade_to_unlimited_tier_never_blocked_on_domains(self, db_session):
        from license_service import LicenseService
        from license_templates import LicenseTemplateManager

        account = _make_account(db_session)
        current_lic = _make_license(db_session, account, license_type='plus',
                                    max_client_companies=100)
        for i in range(50):
            _make_participant(db_session, account, f'user@largeco{i:02d}.com')
        db_session.commit()

        target = LicenseTemplateManager.get_template('trial')
        success, _ = LicenseService._validate_downgrade_usage(
            account.id, current_lic, target
        )
        assert success is True


# ---------------------------------------------------------------------------
# 5. HTTP route: single participant creation
# ---------------------------------------------------------------------------

class TestSingleParticipantCreationLimit:
    """Route-level tests: single participant blocked by company domain limit."""

    def test_participant_blocked_when_new_domain_at_limit(
        self, client, db_session
    ):
        """POST /participants/create returns error when at company limit."""
        account = _make_account(db_session)
        user = _make_user(db_session, account)
        session_id = _make_user_session(db_session, user)
        _make_license(db_session, account, max_client_companies=1)
        _make_participant(db_session, account, 'existing@acme.com')
        db_session.commit()

        _auth_session(client, account.id, user.id, session_id, user.email)

        response = client.post('/business/participants/create', data={
            'email': f'newuser_{uuid.uuid4().hex[:6]}@globex.com',
            'name': 'New User',
            'company_name': 'Globex',
        }, follow_redirects=True)

        assert response.status_code == 200
        data = response.data.decode()
        assert (
            'client compan' in data.lower()
            or 'entreprise' in data.lower()
            or 'cannot add' in data.lower()
        )

    def test_participant_allowed_from_existing_domain_at_limit(
        self, client, db_session
    ):
        """POST /participants/create succeeds for an already-known domain."""
        account = _make_account(db_session)
        user = _make_user(db_session, account)
        session_id = _make_user_session(db_session, user)
        _make_license(db_session, account, max_client_companies=1)
        _make_participant(db_session, account, 'alice@acme.com')
        db_session.commit()

        _auth_session(client, account.id, user.id, session_id, user.email)

        response = client.post('/business/participants/create', data={
            'email': f'bob_{uuid.uuid4().hex[:6]}@acme.com',
            'name': 'Bob Smith',
            'company_name': 'Acme Corp',
        }, follow_redirects=True)

        assert response.status_code in [200, 302]
        data = response.data.decode()
        assert 'cannot add participant' not in data.lower()

    def test_consumer_domain_always_passes_even_at_limit(
        self, client, db_session
    ):
        """Consumer domain (gmail) is never blocked, even at company limit."""
        account = _make_account(db_session)
        user = _make_user(db_session, account)
        session_id = _make_user_session(db_session, user)
        _make_license(db_session, account, max_client_companies=1)
        _make_participant(db_session, account, 'alice@acme.com')
        db_session.commit()

        _auth_session(client, account.id, user.id, session_id, user.email)

        response = client.post('/business/participants/create', data={
            'email': f'consumer_{uuid.uuid4().hex[:6]}@gmail.com',
            'name': 'Consumer User',
            'company_name': 'Personal',
        }, follow_redirects=True)

        assert response.status_code in [200, 302]
        data = response.data.decode()
        assert 'cannot add participant' not in data.lower()


# ---------------------------------------------------------------------------
# 6. HTTP route: bulk CSV upload
# ---------------------------------------------------------------------------

class TestBulkCsvUploadLimit:
    """Route-level tests: CSV rejected upfront when it would breach limit."""

    def test_csv_rejected_when_new_domains_breach_limit(
        self, client, db_session
    ):
        """POST /participants/upload rejects CSV that would push over limit."""
        account = _make_account(db_session)
        user = _make_user(db_session, account)
        session_id = _make_user_session(db_session, user)
        _make_license(db_session, account, max_client_companies=1)
        _make_participant(db_session, account, 'existing@acme.com')
        db_session.commit()

        _auth_session(client, account.id, user.id, session_id, user.email)

        csv_data = _csv_bytes(
            {'email': 'n1@betacorp.com', 'name': 'New 1', 'company_name': 'BetaCorp'},
            {'email': 'n2@gammainc.com', 'name': 'New 2', 'company_name': 'GammaInc'},
        )

        response = client.post('/business/participants/upload', data={
            'csv_file': (io.BytesIO(csv_data), 'participants.csv'),
        }, content_type='multipart/form-data', follow_redirects=True)

        assert response.status_code == 200
        data = response.data.decode()
        assert (
            'client company limit' in data.lower()
            or 'limite' in data.lower()
            or 'rejected' in data.lower()
            or 'rejeté' in data.lower()
        )

    def test_csv_accepted_when_within_limit(self, client, db_session):
        """POST /participants/upload succeeds when new domains stay within limit."""
        account = _make_account(db_session)
        user = _make_user(db_session, account)
        session_id = _make_user_session(db_session, user)
        _make_license(db_session, account, max_client_companies=3)
        db_session.commit()

        _auth_session(client, account.id, user.id, session_id, user.email)

        suffix = uuid.uuid4().hex[:6]
        csv_data = _csv_bytes(
            {'email': f'a@alpha{suffix}.com', 'name': 'Alice', 'company_name': 'Alpha'},
            {'email': f'b@beta{suffix}.com',  'name': 'Bob',   'company_name': 'Beta'},
        )

        response = client.post('/business/participants/upload', data={
            'csv_file': (io.BytesIO(csv_data), 'participants.csv'),
        }, content_type='multipart/form-data', follow_redirects=True)

        assert response.status_code in [200, 302]
        data = response.data.decode()
        assert 'client company limit' not in data.lower()

    def test_csv_rejected_all_or_nothing(self, client, db_session):
        """When CSV is rejected due to limit, NO rows are imported."""
        from models import Participant
        account = _make_account(db_session)
        user = _make_user(db_session, account)
        session_id = _make_user_session(db_session, user)
        _make_license(db_session, account, max_client_companies=1)
        db_session.commit()
        account_id = account.id

        _auth_session(client, account.id, user.id, session_id, user.email)

        suffix = uuid.uuid4().hex[:6]
        csv_data = _csv_bytes(
            {'email': f'ok@first{suffix}.com',  'name': 'OK',   'company_name': 'First'},
            {'email': f'bad@second{suffix}.com', 'name': 'Bad1', 'company_name': 'Second'},
            {'email': f'bad2@third{suffix}.com', 'name': 'Bad2', 'company_name': 'Third'},
        )

        client.post('/business/participants/upload', data={
            'csv_file': (io.BytesIO(csv_data), 'participants.csv'),
        }, content_type='multipart/form-data', follow_redirects=True)

        count = Participant.query.filter_by(business_account_id=account_id).count()
        assert count == 0


# ---------------------------------------------------------------------------
# 7. HTTP route: campaign participant assignment (soft warning only)
# ---------------------------------------------------------------------------

class TestCampaignAssignmentSoftWarning:
    """Invitation count over limit produces a warning but does NOT block."""

    def test_over_invitation_limit_warns_but_proceeds(
        self, client, db_session
    ):
        """Adding participants over invitation guideline shows warning, not hard block."""
        from models import Campaign

        account = _make_account(db_session)
        user = _make_user(db_session, account)
        session_id = _make_user_session(db_session, user)
        _make_license(db_session, account, max_client_companies=None)

        campaign = Campaign(
            name='Test Campaign',
            description='Test',
            status='draft',
            business_account_id=account.id,
            client_identifier=account.name,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )
        db_session.add(campaign)
        db_session.flush()

        participant = _make_participant(
            db_session, account, f'p_{uuid.uuid4().hex[:6]}@acme.com'
        )
        db_session.commit()

        _auth_session(client, account.id, user.id, session_id, user.email)

        with patch('license_service.LicenseService.can_add_participants',
                   return_value=False):
            response = client.post(
                f'/business/participants/campaigns/{campaign.uuid}/participants',
                data={'participant_ids': [str(participant.id)]},
                follow_redirects=True,
            )

        assert response.status_code in [200, 302]
        data = response.data.decode()
        assert (
            'note:' in data.lower()
            or 'warning' in data.lower()
            or 'remarque' in data.lower()
            or response.status_code == 302
        )


# ---------------------------------------------------------------------------
# 8. Platform admin bypass
# ---------------------------------------------------------------------------

class TestPlatformAdminBypass:
    """Platform admins can always add participants regardless of company limit."""

    def test_platform_admin_bypasses_domain_limit(self, db_session, app):
        """can_add_participant_from_domain returns True for platform admin."""
        from models import BusinessAccountUser
        from license_service import LicenseService

        platform_owner_account = _make_account(db_session, account_type='platform_owner')
        admin = _make_user(db_session, platform_owner_account, role='platform_admin')

        target_account = _make_account(db_session)
        _make_license(db_session, target_account, max_client_companies=1)
        _make_participant(db_session, target_account, 'existing@acme.com')
        db_session.commit()

        admin_id = admin.id
        target_account_id = target_account.id

        with app.test_request_context('/'):
            from flask import session as flask_session
            flask_session['business_user_id'] = admin_id
            result = LicenseService.can_add_participant_from_domain(
                target_account_id, 'newdomain@anynewcompany.com'
            )
        assert result is True

    def test_regular_admin_does_not_bypass(self, db_session, app):
        """Regular admin is subject to the domain limit."""
        from license_service import LicenseService

        account = _make_account(db_session)
        regular_user = _make_user(db_session, account, role='admin')
        _make_license(db_session, account, max_client_companies=1)
        _make_participant(db_session, account, 'existing@acme.com')
        db_session.commit()

        user_id = regular_user.id
        account_id = account.id

        with app.test_request_context('/'):
            from flask import session as flask_session
            flask_session['business_user_id'] = user_id
            result = LicenseService.can_add_participant_from_domain(
                account_id, 'blocked@anothercompany.com'
            )
        assert result is False


# ---------------------------------------------------------------------------
# 9. Consumer domain constant completeness
# ---------------------------------------------------------------------------

class TestConsumerEmailDomains:
    """Verify the CONSUMER_EMAIL_DOMAINS constant covers expected providers."""

    def test_known_consumer_domains_are_excluded(self):
        from license_service import LicenseService
        for domain in [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'live.com', 'icloud.com', 'me.com', 'msn.com',
            'aol.com', 'protonmail.com',
        ]:
            assert domain in LicenseService.CONSUMER_EMAIL_DOMAINS, (
                f"Expected {domain!r} to be in CONSUMER_EMAIL_DOMAINS"
            )

    def test_corporate_domain_not_in_consumer_list(self):
        from license_service import LicenseService
        for corporate in ['acme.com', 'globex.com', 'initech.com']:
            assert corporate not in LicenseService.CONSUMER_EMAIL_DOMAINS
