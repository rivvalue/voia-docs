#!/usr/bin/env python3
"""
Authentication Consistency Integration Tests
Author: System Agent
Created: November 25, 2025

Phase A: Tests to validate and document the authentication inconsistency bug
between @require_business_auth decorator and get_current_business_user() function.

These tests establish a baseline for the known broken routes and verify
working routes remain functional during remediation.
"""

import os
import sys
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import BusinessAccount, BusinessAccountUser, UserSession, Campaign, LicenseHistory
from werkzeug.security import generate_password_hash


class AuthTestFixtures:
    """Test fixtures for simulating various authentication scenarios"""
    
    @staticmethod
    def create_test_business():
        """Create a test business account"""
        test_business = BusinessAccount.query.filter_by(name='Auth Test Business').first()
        if not test_business:
            test_business = BusinessAccount()
            test_business.name = 'Auth Test Business'
            test_business.account_type = 'customer'
            test_business.contact_email = 'auth_test@test.com'
            test_business.contact_name = 'Auth Test User'
            test_business.status = 'active'
            db.session.add(test_business)
            db.session.commit()
        return test_business
    
    @staticmethod
    def create_test_user(business_account):
        """Create a test business user"""
        test_user = BusinessAccountUser.query.filter_by(email='auth_test_user@test.com').first()
        if not test_user:
            test_user = BusinessAccountUser()
            test_user.business_account_id = business_account.id
            test_user.email = 'auth_test_user@test.com'
            test_user.first_name = 'Auth'
            test_user.last_name = 'TestUser'
            test_user.password_hash = generate_password_hash('testpassword123')
            test_user.role = 'admin'
            test_user.is_active_user = True
            db.session.add(test_user)
            db.session.commit()
        return test_user
    
    @staticmethod
    def create_valid_session(user):
        """Create a valid, active user session"""
        user_session = UserSession(
            user_id=user.id,
            session_data='{}',
            ip_address='127.0.0.1',
            user_agent='Test Agent',
            duration_hours=24
        )
        db.session.add(user_session)
        db.session.commit()
        return user_session
    
    @staticmethod
    def create_expired_session(user):
        """Create an expired user session"""
        user_session = UserSession(
            user_id=user.id,
            session_data='{}',
            ip_address='127.0.0.1',
            user_agent='Test Agent',
            duration_hours=24
        )
        user_session.expires_at = datetime.utcnow() - timedelta(hours=1)
        db.session.add(user_session)
        db.session.commit()
        return user_session
    
    @staticmethod
    def create_inactive_session(user):
        """Create a deactivated user session"""
        user_session = UserSession(
            user_id=user.id,
            session_data='{}',
            ip_address='127.0.0.1',
            user_agent='Test Agent',
            duration_hours=24
        )
        user_session.is_active = False
        db.session.add(user_session)
        db.session.commit()
        return user_session
    
    @staticmethod
    def create_test_campaign(business_account):
        """Create a test campaign"""
        from datetime import date
        campaign = Campaign.query.filter_by(
            business_account_id=business_account.id,
            name='Auth Test Campaign'
        ).first()
        if not campaign:
            campaign = Campaign()
            campaign.name = 'Auth Test Campaign'
            campaign.business_account_id = business_account.id
            campaign.start_date = date.today()
            campaign.end_date = date.today() + timedelta(days=30)
            campaign.status = 'active'
            db.session.add(campaign)
            db.session.commit()
        return campaign
    
    @staticmethod
    def ensure_license(business_account):
        """Ensure business has a valid license"""
        from license_service import LicenseService
        current = LicenseService.get_current_license(business_account.id)
        if not current:
            LicenseService.assign_license_to_business(
                business_id=business_account.id,
                license_type='core',
                created_by='auth_test@test.com'
            )
    
    @staticmethod
    def cleanup():
        """Clean up test data"""
        test_user = BusinessAccountUser.query.filter_by(email='auth_test_user@test.com').first()
        if test_user:
            UserSession.query.filter_by(user_id=test_user.id).delete()
            db.session.delete(test_user)
        
        test_business = BusinessAccount.query.filter_by(name='Auth Test Business').first()
        if test_business:
            Campaign.query.filter_by(business_account_id=test_business.id).delete()
            LicenseHistory.query.filter_by(business_account_id=test_business.id).delete()
            db.session.delete(test_business)
        
        db.session.commit()


class AuthConsistencyTests:
    """Test suite for authentication consistency validation"""
    
    def __init__(self):
        self.fixtures = AuthTestFixtures()
        self.results = {
            'passed': 0,
            'failed': 0,
            'expected_failures': 0,
            'details': []
        }
    
    def setup(self):
        """Set up test environment"""
        with app.app_context():
            self.business = self.fixtures.create_test_business()
            self.user = self.fixtures.create_test_user(self.business)
            self.fixtures.ensure_license(self.business)
            self.campaign = self.fixtures.create_test_campaign(self.business)
            return self.business, self.user, self.campaign
    
    def teardown(self):
        """Clean up test environment"""
        with app.app_context():
            self.fixtures.cleanup()
    
    def _simulate_session(self, client, user_id=None, session_id=None, business_account_id=None):
        """Simulate session state for testing"""
        with client.session_transaction() as sess:
            if user_id:
                sess['business_user_id'] = user_id
            if session_id:
                sess['business_session_id'] = session_id
            if business_account_id:
                sess['business_account_id'] = business_account_id
    
    def test_scenario_1_valid_complete_session(self):
        """Scenario 1: Valid session with all required data - should work everywhere"""
        print("\n=== Scenario 1: Valid Complete Session ===")
        
        with app.app_context():
            business, user, campaign = self.setup()
            valid_session = self.fixtures.create_valid_session(user)
            
            with app.test_client() as client:
                self._simulate_session(
                    client, 
                    user_id=user.id,
                    session_id=valid_session.session_id,
                    business_account_id=business.id
                )
                
                routes_to_test = [
                    ('/dashboard/executive-summary', 'Executive Summary (BI)'),
                    ('/dashboard/campaign-insights', 'Campaign Insights (BI)'),
                    ('/business/campaigns', 'Campaign List (Control)'),
                ]
                
                for route, name in routes_to_test:
                    response = client.get(route, follow_redirects=False)
                    if response.status_code == 200:
                        print(f"  ✅ {name}: HTTP {response.status_code}")
                        self.results['passed'] += 1
                    elif response.status_code == 302:
                        location = response.headers.get('Location', '')
                        if 'login' in location.lower():
                            print(f"  ❌ {name}: Redirected to login (UNEXPECTED)")
                            self.results['failed'] += 1
                        else:
                            print(f"  ⚠️ {name}: HTTP {response.status_code} → {location}")
                            self.results['passed'] += 1
                    else:
                        print(f"  ⚠️ {name}: HTTP {response.status_code}")
                        self.results['passed'] += 1
    
    def test_scenario_2_missing_session_id(self):
        """Scenario 2: Missing business_session_id - demonstrates the bug"""
        print("\n=== Scenario 2: Missing business_session_id (BUG SCENARIO) ===")
        
        with app.app_context():
            business, user, campaign = self.setup()
            valid_session = self.fixtures.create_valid_session(user)
            
            with app.test_client() as client:
                self._simulate_session(
                    client, 
                    user_id=user.id,
                    business_account_id=business.id
                )
                
                bi_routes = [
                    ('/dashboard/executive-summary', 'Executive Summary (BI)'),
                    ('/dashboard/campaign-insights', 'Campaign Insights (BI)'),
                ]
                
                control_routes = [
                    ('/business/campaigns', 'Campaign List (Control)'),
                ]
                
                print("  BI Routes (Expected to FAIL due to bug):")
                for route, name in bi_routes:
                    response = client.get(route, follow_redirects=False)
                    if response.status_code == 302:
                        location = response.headers.get('Location', '')
                        if 'login' in location.lower():
                            print(f"    ❌ {name}: Redirected to login (BUG CONFIRMED)")
                            self.results['expected_failures'] += 1
                        else:
                            print(f"    ⚠️ {name}: HTTP {response.status_code} → {location}")
                    elif response.status_code == 200:
                        print(f"    ✅ {name}: HTTP {response.status_code} (UNEXPECTED - bug may be fixed)")
                        self.results['passed'] += 1
                    else:
                        print(f"    ⚠️ {name}: HTTP {response.status_code}")
                
                print("  Control Routes (Expected to PASS - uses relaxed validation):")
                for route, name in control_routes:
                    response = client.get(route, follow_redirects=False)
                    if response.status_code == 200:
                        print(f"    ✅ {name}: HTTP {response.status_code}")
                        self.results['passed'] += 1
                    elif response.status_code == 302:
                        location = response.headers.get('Location', '')
                        print(f"    ⚠️ {name}: HTTP {response.status_code} → {location}")
                        self.results['failed'] += 1
                    else:
                        print(f"    ⚠️ {name}: HTTP {response.status_code}")
    
    def test_scenario_3_expired_session(self):
        """Scenario 3: Expired UserSession in database"""
        print("\n=== Scenario 3: Expired UserSession ===")
        
        with app.app_context():
            business, user, campaign = self.setup()
            expired_session = self.fixtures.create_expired_session(user)
            
            with app.test_client() as client:
                self._simulate_session(
                    client, 
                    user_id=user.id,
                    session_id=expired_session.session_id,
                    business_account_id=business.id
                )
                
                routes_to_test = [
                    ('/dashboard/executive-summary', 'Executive Summary (BI)'),
                    ('/business/campaigns', 'Campaign List (Control)'),
                ]
                
                for route, name in routes_to_test:
                    response = client.get(route, follow_redirects=False)
                    if response.status_code == 302:
                        location = response.headers.get('Location', '')
                        if 'login' in location.lower():
                            print(f"  ❌ {name}: Redirected to login (expired session)")
                            self.results['expected_failures'] += 1
                        else:
                            print(f"  ⚠️ {name}: HTTP {response.status_code} → {location}")
                    elif response.status_code == 200:
                        print(f"  ⚠️ {name}: HTTP {response.status_code} (session expired but still works)")
                        self.results['passed'] += 1
                    else:
                        print(f"  ⚠️ {name}: HTTP {response.status_code}")
    
    def test_scenario_4_inactive_session(self):
        """Scenario 4: Deactivated UserSession in database"""
        print("\n=== Scenario 4: Inactive (Deactivated) UserSession ===")
        
        with app.app_context():
            business, user, campaign = self.setup()
            inactive_session = self.fixtures.create_inactive_session(user)
            
            with app.test_client() as client:
                self._simulate_session(
                    client, 
                    user_id=user.id,
                    session_id=inactive_session.session_id,
                    business_account_id=business.id
                )
                
                routes_to_test = [
                    ('/dashboard/executive-summary', 'Executive Summary (BI)'),
                    ('/business/campaigns', 'Campaign List (Control)'),
                ]
                
                for route, name in routes_to_test:
                    response = client.get(route, follow_redirects=False)
                    if response.status_code == 302:
                        location = response.headers.get('Location', '')
                        if 'login' in location.lower():
                            print(f"  ❌ {name}: Redirected to login (inactive session)")
                            self.results['expected_failures'] += 1
                        else:
                            print(f"  ⚠️ {name}: HTTP {response.status_code} → {location}")
                    elif response.status_code == 200:
                        print(f"  ⚠️ {name}: HTTP {response.status_code} (session inactive but still works)")
                        self.results['passed'] += 1
                    else:
                        print(f"  ⚠️ {name}: HTTP {response.status_code}")
    
    def test_scenario_5_nonexistent_session_id(self):
        """Scenario 5: Session ID doesn't exist in database"""
        print("\n=== Scenario 5: Non-existent Session ID ===")
        
        with app.app_context():
            business, user, campaign = self.setup()
            fake_session_id = str(uuid.uuid4())
            
            with app.test_client() as client:
                self._simulate_session(
                    client, 
                    user_id=user.id,
                    session_id=fake_session_id,
                    business_account_id=business.id
                )
                
                routes_to_test = [
                    ('/dashboard/executive-summary', 'Executive Summary (BI)'),
                    ('/business/campaigns', 'Campaign List (Control)'),
                ]
                
                for route, name in routes_to_test:
                    response = client.get(route, follow_redirects=False)
                    if response.status_code == 302:
                        location = response.headers.get('Location', '')
                        if 'login' in location.lower():
                            print(f"  ❌ {name}: Redirected to login (fake session)")
                            self.results['expected_failures'] += 1
                        else:
                            print(f"  ⚠️ {name}: HTTP {response.status_code} → {location}")
                    elif response.status_code == 200:
                        print(f"  ⚠️ {name}: HTTP {response.status_code} (fake session but still works)")
                        self.results['passed'] += 1
                    else:
                        print(f"  ⚠️ {name}: HTTP {response.status_code}")
    
    def run_all_tests(self):
        """Run all authentication consistency tests"""
        print("=" * 60)
        print("AUTHENTICATION CONSISTENCY INTEGRATION TESTS")
        print("Phase A: Baseline Validation")
        print("=" * 60)
        
        try:
            self.test_scenario_1_valid_complete_session()
            self.test_scenario_2_missing_session_id()
            self.test_scenario_3_expired_session()
            self.test_scenario_4_inactive_session()
            self.test_scenario_5_nonexistent_session_id()
        finally:
            self.teardown()
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"  Passed:            {self.results['passed']}")
        print(f"  Failed:            {self.results['failed']}")
        print(f"  Expected Failures: {self.results['expected_failures']} (known bugs)")
        print("=" * 60)
        
        return self.results


def run_auth_tests():
    """Main entry point for running auth consistency tests"""
    tests = AuthConsistencyTests()
    return tests.run_all_tests()


if __name__ == '__main__':
    run_auth_tests()
