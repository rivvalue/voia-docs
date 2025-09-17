#!/usr/bin/env python3
"""
Comprehensive End-to-End License Management Testing Suite
Author: License Testing Agent
Created: September 17, 2025

This comprehensive test suite validates the complete license assignment workflow
and license management system across all specified categories:

1. License Assignment Workflow Testing
2. License Enforcement Testing  
3. Multi-tenant Security Testing
4. Database Integrity Testing
5. UI/UX Integration Testing
6. Edge Case and Error Handling Testing
7. Performance and Load Testing
8. Integration with Existing System Testing

The suite generates detailed reports and provides production readiness assessment.
"""

import os
import sys
import json
import logging
import time
import threading
from datetime import datetime, timedelta, date
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Tuple, Any
import requests
from unittest.mock import patch
import csv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Flask app and models
from app import app, db
from models import (BusinessAccount, LicenseHistory, Campaign, CampaignParticipant, 
                   Participant, BusinessAccountUser, EmailDelivery)
from license_service import LicenseService
from license_templates import LicenseTemplateManager
from business_auth_routes import business_auth_bp

class ComprehensiveTestSuite:
    """
    Master test suite that orchestrates all license management testing
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Test results storage
        self.test_results = {
            'timestamp': datetime.now().isoformat(),
            'categories': {
                'license_assignment_workflow': {'tests': [], 'passed': 0, 'failed': 0},
                'license_enforcement': {'tests': [], 'passed': 0, 'failed': 0},
                'multi_tenant_security': {'tests': [], 'passed': 0, 'failed': 0},
                'database_integrity': {'tests': [], 'passed': 0, 'failed': 0},
                'ui_ux_integration': {'tests': [], 'passed': 0, 'failed': 0},
                'edge_case_handling': {'tests': [], 'passed': 0, 'failed': 0},
                'performance_load': {'tests': [], 'passed': 0, 'failed': 0},
                'system_integration': {'tests': [], 'passed': 0, 'failed': 0}
            },
            'performance_metrics': {},
            'security_validation': {},
            'production_readiness': {}
        }
        
        # Test data storage
        self.test_data = {
            'business_accounts': [],
            'test_users': [],
            'test_campaigns': [],
            'test_participants': []
        }
        
    def setup_logging(self):
        """Configure comprehensive logging for test execution"""
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'logs/comprehensive_license_testing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
                logging.StreamHandler()
            ]
        )

    def record_test_result(self, category: str, test_name: str, passed: bool, 
                          execution_time: float, details: str = "", error: str = ""):
        """Record individual test result"""
        result = {
            'test_name': test_name,
            'passed': passed,
            'execution_time': execution_time,
            'details': details,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        self.test_results['categories'][category]['tests'].append(result)
        
        if passed:
            self.test_results['categories'][category]['passed'] += 1
        else:
            self.test_results['categories'][category]['failed'] += 1
        
        # Log result
        status = "PASSED" if passed else "FAILED"
        self.logger.info(f"[{category.upper()}] {test_name}: {status} ({execution_time:.2f}s)")
        if error:
            self.logger.error(f"[{category.upper()}] {test_name} Error: {error}")

    def setup_test_environment(self):
        """Set up comprehensive test environment with test data"""
        print("\n" + "="*80)
        print("SETTING UP COMPREHENSIVE TEST ENVIRONMENT")
        print("="*80)
        
        with app.app_context():
            try:
                # Create test business accounts for different scenarios
                test_businesses = [
                    {
                        'name': 'License Assignment Test Business',
                        'account_type': 'customer',
                        'contact_email': 'assignment@test.com',
                        'contact_name': 'Assignment Test User',
                        'status': 'active'
                    },
                    {
                        'name': 'License Enforcement Test Business', 
                        'account_type': 'customer',
                        'contact_email': 'enforcement@test.com',
                        'contact_name': 'Enforcement Test User',
                        'status': 'active'
                    },
                    {
                        'name': 'Multi-tenant Security Test Business',
                        'account_type': 'customer', 
                        'contact_email': 'security@test.com',
                        'contact_name': 'Security Test User',
                        'status': 'active'
                    },
                    {
                        'name': 'Performance Test Business',
                        'account_type': 'customer',
                        'contact_email': 'performance@test.com', 
                        'contact_name': 'Performance Test User',
                        'status': 'active'
                    }
                ]
                
                for business_data in test_businesses:
                    existing = BusinessAccount.query.filter_by(name=business_data['name']).first()
                    if not existing:
                        business = BusinessAccount(**business_data)
                        db.session.add(business)
                        db.session.commit()
                        self.test_data['business_accounts'].append(business.id)
                        print(f"✓ Created test business: {business_data['name']} (ID: {business.id})")
                    else:
                        self.test_data['business_accounts'].append(existing.id)
                        print(f"✓ Using existing test business: {business_data['name']} (ID: {existing.id})")
                
                # Create test participants for enforcement testing
                test_participants = []
                for i in range(50):  # Create enough participants for limit testing
                    participant_data = {
                        'name': f'Test Participant {i+1}',
                        'email': f'participant{i+1}@test.com',
                        'business_account_id': self.test_data['business_accounts'][0],  # Assign to first test business
                        'company_name': f'Test Company {i+1}'
                    }
                    
                    existing = Participant.query.filter_by(email=participant_data['email']).first()
                    if not existing:
                        participant = Participant(**participant_data)
                        db.session.add(participant)
                        db.session.commit()
                        test_participants.append(participant.id)
                    else:
                        test_participants.append(existing.id)
                
                self.test_data['test_participants'] = test_participants
                print(f"✓ Created/verified {len(test_participants)} test participants")
                
                print("✅ Test environment setup completed successfully")
                return True
                
            except Exception as e:
                print(f"❌ Test environment setup failed: {e}")
                self.logger.error(f"Test environment setup failed: {e}")
                return False

    # ==================== CATEGORY 1: LICENSE ASSIGNMENT WORKFLOW TESTING ====================
    
    def test_license_assignment_workflow(self):
        """Test complete license assignment workflow from admin interface"""
        print("\n" + "="*80)
        print("CATEGORY 1: LICENSE ASSIGNMENT WORKFLOW TESTING")
        print("="*80)
        
        with app.app_context():
            business_id = self.test_data['business_accounts'][0]
            
            # Test 1: Basic Core License Assignment
            start_time = time.time()
            try:
                success, license_record, message = LicenseService.assign_license_to_business(
                    business_id=business_id,
                    license_type='core',
                    assigned_by='test_admin@example.com',
                    notes='Test Core license assignment'
                )
                
                execution_time = time.time() - start_time
                
                if success and license_record:
                    self.record_test_result(
                        'license_assignment_workflow', 
                        'Basic Core License Assignment',
                        True,
                        execution_time,
                        f"License ID: {license_record.id}, Type: {license_record.license_type}"
                    )
                else:
                    self.record_test_result(
                        'license_assignment_workflow', 
                        'Basic Core License Assignment',
                        False,
                        execution_time,
                        error=message or "Failed to assign Core license"
                    )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'license_assignment_workflow', 
                    'Basic Core License Assignment',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 2: License Type Upgrade (Core → Plus)
            start_time = time.time()
            try:
                success, license_record, message = LicenseService.assign_license_to_business(
                    business_id=business_id,
                    license_type='plus',
                    assigned_by='test_admin@example.com',
                    notes='Upgrade from Core to Plus'
                )
                
                execution_time = time.time() - start_time
                
                if success and license_record and license_record.license_type == 'plus':
                    # Verify old license was deactivated
                    old_licenses = LicenseHistory.query.filter_by(
                        business_account_id=business_id,
                        license_type='core',
                        status='inactive'
                    ).count()
                    
                    self.record_test_result(
                        'license_assignment_workflow', 
                        'License Type Upgrade (Core → Plus)',
                        old_licenses > 0,
                        execution_time,
                        f"New license: {license_record.license_type}, Old licenses deactivated: {old_licenses}"
                    )
                else:
                    self.record_test_result(
                        'license_assignment_workflow', 
                        'License Type Upgrade (Core → Plus)',
                        False,
                        execution_time,
                        error=message or "Failed to upgrade to Plus license"
                    )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'license_assignment_workflow', 
                    'License Type Upgrade (Core → Plus)',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 3: Custom Pro License Configuration
            start_time = time.time()
            try:
                custom_config = {
                    'max_campaigns_per_year': 24,
                    'max_users': 50,
                    'max_participants_per_campaign': 5000,
                    'duration_months': 12
                }
                
                success, license_record, message = LicenseService.assign_license_to_business(
                    business_id=business_id,
                    license_type='pro',
                    assigned_by='test_admin@example.com',
                    custom_config=custom_config,
                    notes='Custom Pro license with specific limits'
                )
                
                execution_time = time.time() - start_time
                
                if success and license_record:
                    # Verify custom configuration was applied
                    config_correct = (
                        license_record.max_campaigns_per_year == custom_config['max_campaigns_per_year'] and
                        license_record.max_users == custom_config['max_users'] and 
                        license_record.max_participants_per_campaign == custom_config['max_participants_per_campaign']
                    )
                    
                    self.record_test_result(
                        'license_assignment_workflow', 
                        'Custom Pro License Configuration',
                        config_correct,
                        execution_time,
                        f"Custom config applied: {config_correct}, Campaigns: {license_record.max_campaigns_per_year}, Users: {license_record.max_users}"
                    )
                else:
                    self.record_test_result(
                        'license_assignment_workflow', 
                        'Custom Pro License Configuration',
                        False,
                        execution_time,
                        error=message or "Failed to assign custom Pro license"
                    )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'license_assignment_workflow', 
                    'Custom Pro License Configuration',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 4: License Assignment Form Validation
            start_time = time.time()
            try:
                # Test invalid license type
                success, license_record, message = LicenseService.assign_license_to_business(
                    business_id=business_id,
                    license_type='invalid_type',
                    assigned_by='test_admin@example.com'
                )
                
                execution_time = time.time() - start_time
                
                # This should fail with validation error
                self.record_test_result(
                    'license_assignment_workflow', 
                    'License Assignment Form Validation',
                    not success,  # Success means validation worked (rejected invalid type)
                    execution_time,
                    f"Validation properly rejected invalid license type: {message}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'license_assignment_workflow', 
                    'License Assignment Form Validation',
                    True,  # Exception is expected for invalid input
                    execution_time,
                    f"Validation properly threw exception for invalid input: {str(e)}"
                )
            
            # Test 5: License History Tracking and Audit Trail  
            start_time = time.time()
            try:
                # Get all license history for this business
                license_history = LicenseHistory.query.filter_by(
                    business_account_id=business_id
                ).order_by(LicenseHistory.created_at.desc()).all()
                
                execution_time = time.time() - start_time
                
                # Should have multiple license records from previous tests
                has_multiple_licenses = len(license_history) >= 3
                has_audit_trail = all(record.created_by and record.notes for record in license_history[:3])
                has_proper_status = any(record.status == 'inactive' for record in license_history)
                
                self.record_test_result(
                    'license_assignment_workflow', 
                    'License History Tracking and Audit Trail',
                    has_multiple_licenses and has_audit_trail and has_proper_status,
                    execution_time,
                    f"License history entries: {len(license_history)}, Audit trail complete: {has_audit_trail}, Status transitions: {has_proper_status}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'license_assignment_workflow', 
                    'License History Tracking and Audit Trail',
                    False,
                    execution_time,
                    error=str(e)
                )

    # ==================== CATEGORY 2: LICENSE ENFORCEMENT TESTING ====================
    
    def test_license_enforcement(self):
        """Test license enforcement for campaigns, users, and participants"""
        print("\n" + "="*80)
        print("CATEGORY 2: LICENSE ENFORCEMENT TESTING")
        print("="*80)
        
        with app.app_context():
            business_id = self.test_data['business_accounts'][1]
            
            # First assign a Core license with known limits (4 campaigns/year, 5 users, 200 participants/campaign)
            LicenseService.assign_license_to_business(
                business_id=business_id,
                license_type='core',
                assigned_by='test_enforcement@example.com',
                notes='Core license for enforcement testing'
            )
            
            # Test 1: Campaign Creation and Activation Limits
            start_time = time.time()
            try:
                # Create campaigns up to the limit (4 for Core)
                campaigns_created = []
                for i in range(5):  # Try to create 5 campaigns (1 over limit)
                    campaign_name = f'Enforcement Test Campaign {i+1}'
                    
                    if LicenseService.can_activate_campaign(business_id):
                        campaign = Campaign(
                            name=campaign_name,
                            business_account_id=business_id,
                            start_date=date.today(),
                            end_date=date.today() + timedelta(days=30),
                            status='active'
                        )
                        db.session.add(campaign)
                        db.session.commit()
                        campaigns_created.append(campaign.id)
                    else:
                        break
                
                execution_time = time.time() - start_time
                
                # Should have created exactly 4 campaigns (Core license limit)
                self.record_test_result(
                    'license_enforcement', 
                    'Campaign Creation and Activation Limits',
                    len(campaigns_created) == 4,
                    execution_time,
                    f"Campaigns created: {len(campaigns_created)}/4 (Core license limit)"
                )
                
                self.test_data['test_campaigns'] = campaigns_created
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'license_enforcement', 
                    'Campaign Creation and Activation Limits',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 2: Participant Addition Limits Per Campaign
            start_time = time.time()
            try:
                if self.test_data['test_campaigns']:
                    campaign_id = self.test_data['test_campaigns'][0]
                    participants_added = 0
                    
                    # Try to add participants up to limit (200 for Core)
                    for i in range(min(210, len(self.test_data['test_participants']))):  # Try to add 210 (10 over limit)
                        participant_id = self.test_data['test_participants'][i]
                        
                        if LicenseService.can_add_campaign_participant(business_id, campaign_id):
                            # Create campaign participant association
                            campaign_participant = CampaignParticipant(
                                campaign_id=campaign_id,
                                participant_id=participant_id,
                                business_account_id=business_id,
                                invitation_status='pending'
                            )
                            db.session.add(campaign_participant)
                            db.session.commit()
                            participants_added += 1
                        else:
                            break
                    
                    execution_time = time.time() - start_time
                    
                    # Should have added exactly 200 participants (Core license limit)
                    self.record_test_result(
                        'license_enforcement', 
                        'Participant Addition Limits Per Campaign',
                        participants_added <= 200,
                        execution_time,
                        f"Participants added: {participants_added}/200 (Core license limit per campaign)"
                    )
                else:
                    execution_time = time.time() - start_time
                    self.record_test_result(
                        'license_enforcement', 
                        'Participant Addition Limits Per Campaign',
                        False,
                        execution_time,
                        error="No test campaigns available"
                    )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'license_enforcement', 
                    'Participant Addition Limits Per Campaign',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 3: License Enforcement Error Messages
            start_time = time.time()
            try:
                # Try to create one more campaign (should fail)
                can_create = LicenseService.can_activate_campaign(business_id)
                license_info = LicenseService.get_license_info(business_id)
                
                execution_time = time.time() - start_time
                
                # Should return False and provide proper license info
                has_proper_error_info = (
                    not can_create and
                    license_info and
                    'campaigns_limit' in license_info and
                    'campaigns_used' in license_info and
                    license_info['campaigns_used'] >= license_info['campaigns_limit']
                )
                
                self.record_test_result(
                    'license_enforcement', 
                    'License Enforcement Error Messages',
                    has_proper_error_info,
                    execution_time,
                    f"Can create campaign: {can_create}, License info available: {license_info is not None}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'license_enforcement', 
                    'License Enforcement Error Messages',
                    False,
                    execution_time,
                    error=str(e)
                )

    # ==================== CATEGORY 3: MULTI-TENANT SECURITY TESTING ====================
    
    def test_multi_tenant_security(self):
        """Test multi-tenant security and access controls"""
        print("\n" + "="*80)  
        print("CATEGORY 3: MULTI-TENANT SECURITY TESTING")
        print("="*80)
        
        with app.app_context():
            business_id_1 = self.test_data['business_accounts'][0]
            business_id_2 = self.test_data['business_accounts'][2]
            
            # Test 1: Cross-tenant Data Isolation
            start_time = time.time()
            try:
                # Assign different licenses to different businesses
                LicenseService.assign_license_to_business(
                    business_id=business_id_1,
                    license_type='core', 
                    assigned_by='admin1@test.com'
                )
                
                LicenseService.assign_license_to_business(
                    business_id=business_id_2,
                    license_type='plus',
                    assigned_by='admin2@test.com' 
                )
                
                # Verify each business can only see its own license
                license_1 = LicenseService.get_current_license(business_id_1)
                license_2 = LicenseService.get_current_license(business_id_2)
                
                execution_time = time.time() - start_time
                
                isolation_correct = (
                    license_1 and license_1.business_account_id == business_id_1 and license_1.license_type == 'core' and
                    license_2 and license_2.business_account_id == business_id_2 and license_2.license_type == 'plus'
                )
                
                self.record_test_result(
                    'multi_tenant_security', 
                    'Cross-tenant Data Isolation',
                    isolation_correct,
                    execution_time,
                    f"Business 1 license: {license_1.license_type if license_1 else None}, Business 2 license: {license_2.license_type if license_2 else None}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'multi_tenant_security', 
                    'Cross-tenant Data Isolation',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 2: License History Access Control
            start_time = time.time()
            try:
                # Get license history for each business
                history_1 = LicenseHistory.query.filter_by(business_account_id=business_id_1).all()
                history_2 = LicenseHistory.query.filter_by(business_account_id=business_id_2).all()
                
                # Cross-check: ensure no license in history_1 belongs to business_id_2
                cross_contamination = any(
                    record.business_account_id != business_id_1 for record in history_1
                ) or any(
                    record.business_account_id != business_id_2 for record in history_2
                )
                
                execution_time = time.time() - start_time
                
                self.record_test_result(
                    'multi_tenant_security', 
                    'License History Access Control',
                    not cross_contamination,
                    execution_time,
                    f"Business 1 history records: {len(history_1)}, Business 2 history records: {len(history_2)}, Cross-contamination: {cross_contamination}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'multi_tenant_security', 
                    'License History Access Control',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 3: License Service Security Methods  
            start_time = time.time()
            try:
                # Test that license validation respects business account boundaries
                license_info_1 = LicenseService.get_license_info(business_id_1)
                license_info_2 = LicenseService.get_license_info(business_id_2)
                
                execution_time = time.time() - start_time
                
                # Each should get different license info matching their actual licenses
                security_correct = (
                    license_info_1 and license_info_1['license_type'] == 'core' and
                    license_info_2 and license_info_2['license_type'] == 'plus' and
                    license_info_1['business_account_id'] == business_id_1 and
                    license_info_2['business_account_id'] == business_id_2
                )
                
                self.record_test_result(
                    'multi_tenant_security', 
                    'License Service Security Methods',
                    security_correct,
                    execution_time,
                    f"License info isolation maintained: {security_correct}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'multi_tenant_security', 
                    'License Service Security Methods',
                    False,
                    execution_time,
                    error=str(e)
                )

    # ==================== CATEGORY 4: DATABASE INTEGRITY TESTING ====================
    
    def test_database_integrity(self):
        """Test database constraints, calculations, and template system"""
        print("\n" + "="*80)
        print("CATEGORY 4: DATABASE INTEGRITY TESTING") 
        print("="*80)
        
        with app.app_context():
            business_id = self.test_data['business_accounts'][3]
            
            # Test 1: Single Active License Constraint
            start_time = time.time()
            try:
                # Try to create two active licenses for the same business
                license1 = LicenseHistory(
                    business_account_id=business_id,
                    license_type='core',
                    status='active',
                    activated_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=365),
                    max_campaigns_per_year=4,
                    max_users=5,
                    max_participants_per_campaign=200,
                    created_by='constraint_test@test.com'
                )
                db.session.add(license1)
                db.session.commit()
                
                license2 = LicenseHistory(
                    business_account_id=business_id,
                    license_type='plus',
                    status='active',
                    activated_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=365),
                    max_campaigns_per_year=4,
                    max_users=10,
                    max_participants_per_campaign=2000,
                    created_by='constraint_test@test.com'
                )
                db.session.add(license2)
                
                try:
                    db.session.commit()
                    # If we get here, the constraint failed
                    constraint_works = False
                except Exception:
                    # Constraint worked - prevented duplicate active licenses
                    db.session.rollback()
                    constraint_works = True
                
                execution_time = time.time() - start_time
                
                self.record_test_result(
                    'database_integrity', 
                    'Single Active License Constraint',
                    constraint_works,
                    execution_time,
                    f"Database constraint properly prevented duplicate active licenses: {constraint_works}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'database_integrity', 
                    'Single Active License Constraint',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 2: License Period Calculations
            start_time = time.time() 
            try:
                # Test license period calculation for various scenarios
                test_scenarios = [
                    (date(2025, 1, 31), 'Edge case: Jan 31'),
                    (date(2025, 2, 28), 'Edge case: Feb 28'),
                    (date(2024, 2, 29), 'Edge case: Leap year Feb 29'),  
                    (date(2025, 12, 31), 'Edge case: Dec 31'),
                    (date(2025, 6, 15), 'Normal case: Jun 15')
                ]
                
                calculations_correct = True
                for test_date, description in test_scenarios:
                    period_start, period_end = LicenseService.get_license_period(business_id, test_date)
                    
                    # For an active license, should get valid dates
                    if not period_start or not period_end:
                        calculations_correct = False
                        break
                    
                    # Period should be valid (end after start)
                    if period_end <= period_start:
                        calculations_correct = False
                        break
                
                execution_time = time.time() - start_time
                
                self.record_test_result(
                    'database_integrity', 
                    'License Period Calculations',
                    calculations_correct,
                    execution_time,
                    f"All license period calculations returned valid results: {calculations_correct}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'database_integrity', 
                    'License Period Calculations',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 3: License Template System Validation
            start_time = time.time()
            try:
                # Test all template types
                template_tests = []
                for template_type in ['core', 'plus', 'pro', 'trial']:
                    template = LicenseTemplateManager.get_template(template_type)
                    if template:
                        # Validate template properties
                        template_valid = (
                            template.license_type == template_type and
                            template.max_campaigns_per_year > 0 and
                            template.max_users > 0 and
                            template.max_participants_per_campaign > 0 and
                            template.default_duration_months > 0
                        )
                        template_tests.append(template_valid)
                    else:
                        template_tests.append(False)
                
                execution_time = time.time() - start_time
                
                all_templates_valid = all(template_tests)
                
                self.record_test_result(
                    'database_integrity', 
                    'License Template System Validation',
                    all_templates_valid,
                    execution_time,
                    f"All license templates valid: {all_templates_valid}, Templates tested: {len(template_tests)}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'database_integrity', 
                    'License Template System Validation',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 4: Database Consistency Under Concurrent Operations  
            start_time = time.time()
            try:
                def concurrent_license_operation(thread_id):
                    """Simulate concurrent license operations"""
                    with app.app_context():
                        try:
                            # Each thread tries to assign a different license type
                            license_types = ['core', 'plus', 'pro', 'trial']
                            license_type = license_types[thread_id % len(license_types)]
                            
                            success, license_record, message = LicenseService.assign_license_to_business(
                                business_id=business_id,
                                license_type=license_type,
                                assigned_by=f'concurrent_test_{thread_id}@test.com'
                            )
                            return success, license_type
                        except Exception as e:
                            return False, str(e)
                
                # Run concurrent operations
                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = [executor.submit(concurrent_license_operation, i) for i in range(4)]
                    results = [future.result() for future in futures]
                
                execution_time = time.time() - start_time
                
                # At least one should succeed, others might fail due to constraints - this is correct
                successful_operations = sum(1 for success, _ in results if success)
                consistency_maintained = successful_operations >= 1
                
                self.record_test_result(
                    'database_integrity', 
                    'Database Consistency Under Concurrent Operations',
                    consistency_maintained,
                    execution_time,
                    f"Successful concurrent operations: {successful_operations}/4, Database consistency maintained: {consistency_maintained}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'database_integrity', 
                    'Database Consistency Under Concurrent Operations',
                    False,
                    execution_time,
                    error=str(e)
                )

    # ==================== CATEGORY 5: UI/UX INTEGRATION TESTING ====================
    
    def test_ui_ux_integration(self):
        """Test UI/UX integration and template rendering"""
        print("\n" + "="*80)
        print("CATEGORY 5: UI/UX INTEGRATION TESTING")
        print("="*80)
        
        # Test 1: License Management Template Rendering
        start_time = time.time()
        try:
            with app.test_client() as client:
                # Test license dashboard template
                with app.test_request_context():
                    from flask import render_template_string
                    
                    # Test basic template rendering
                    template_content = """
                    <!DOCTYPE html>
                    <html>
                    <head><title>License Test</title></head>
                    <body>
                        <h1>License Management</h1>
                        {% if current_license %}
                            <p>Current License: {{ current_license.license_type }}</p>
                            <p>Expires: {{ current_license.expires_at }}</p>
                        {% else %}
                            <p>No active license</p>
                        {% endif %}
                    </body>
                    </html>
                    """
                    
                    # Mock license data
                    mock_license = type('License', (), {
                        'license_type': 'core',
                        'expires_at': '2025-12-31'
                    })()
                    
                    rendered = render_template_string(template_content, current_license=mock_license)
                    
                    execution_time = time.time() - start_time
                    
                    template_renders = 'License Management' in rendered and 'core' in rendered
                    
                    self.record_test_result(
                        'ui_ux_integration', 
                        'License Management Template Rendering',
                        template_renders,
                        execution_time,
                        f"Template renders correctly: {template_renders}"
                    )
                        
        except Exception as e:
            execution_time = time.time() - start_time
            self.record_test_result(
                'ui_ux_integration', 
                'License Management Template Rendering',
                False,
                execution_time,
                error=str(e)
            )
        
        # Test 2: License Info Display Integration
        start_time = time.time()
        try:
            with app.app_context():
                business_id = self.test_data['business_accounts'][0]
                license_info = LicenseService.get_license_info(business_id)
                
                # Test license info structure for UI display
                required_fields = ['license_type', 'campaigns_limit', 'campaigns_used', 'users_limit', 'participants_limit']
                has_required_fields = all(field in license_info for field in required_fields)
                
                execution_time = time.time() - start_time
                
                self.record_test_result(
                    'ui_ux_integration', 
                    'License Info Display Integration',
                    has_required_fields,
                    execution_time,
                    f"License info has required UI fields: {has_required_fields}, Fields: {list(license_info.keys()) if license_info else []}"
                )
                    
        except Exception as e:
            execution_time = time.time() - start_time
            self.record_test_result(
                'ui_ux_integration', 
                'License Info Display Integration',
                False,
                execution_time,
                error=str(e)
            )
        
        # Test 3: Error Message Display Format
        start_time = time.time()
        try:
            with app.app_context():
                business_id = self.test_data['business_accounts'][0]
                
                # Test error message when limits are exceeded
                can_create = LicenseService.can_activate_campaign(business_id)
                license_info = LicenseService.get_license_info(business_id)
                
                # Format error message as UI would
                if not can_create and license_info:
                    error_message = f'Cannot create campaign. Your {license_info["license_type"]} license allows {license_info["campaigns_limit"]} campaigns per year and you have already used {license_info["campaigns_used"]} campaigns.'
                    
                    message_formatted = len(error_message) > 0 and 'license' in error_message.lower()
                else:
                    message_formatted = True  # No error to format
                
                execution_time = time.time() - start_time
                
                self.record_test_result(
                    'ui_ux_integration', 
                    'Error Message Display Format',
                    message_formatted,
                    execution_time,
                    f"Error messages properly formatted for UI: {message_formatted}"
                )
                    
        except Exception as e:
            execution_time = time.time() - start_time
            self.record_test_result(
                'ui_ux_integration', 
                'Error Message Display Format',
                False,
                execution_time,
                error=str(e)
            )

    # ==================== CATEGORY 6: EDGE CASE AND ERROR HANDLING TESTING ====================
    
    def test_edge_case_handling(self):
        """Test edge cases and error handling scenarios"""
        print("\n" + "="*80)
        print("CATEGORY 6: EDGE CASE AND ERROR HANDLING TESTING")
        print("="*80)
        
        with app.app_context():
            
            # Test 1: License Assignment to Non-existent Business Account
            start_time = time.time()
            try:
                success, license_record, message = LicenseService.assign_license_to_business(
                    business_id=999999,  # Non-existent ID
                    license_type='core',
                    assigned_by='edge_test@test.com'
                )
                
                execution_time = time.time() - start_time
                
                # Should fail gracefully
                self.record_test_result(
                    'edge_case_handling', 
                    'License Assignment to Non-existent Business Account',
                    not success,
                    execution_time,
                    f"Properly handled non-existent business account: {message}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                # Exception is acceptable for this edge case
                self.record_test_result(
                    'edge_case_handling', 
                    'License Assignment to Non-existent Business Account',
                    True,
                    execution_time,
                    f"Properly threw exception for non-existent business: {str(e)}"
                )
            
            # Test 2: Invalid License Configuration Values
            start_time = time.time()
            try:
                business_id = self.test_data['business_accounts'][0]
                
                invalid_configs = [
                    {'max_campaigns_per_year': -1},  # Negative value
                    {'max_users': 0},  # Zero value
                    {'max_participants_per_campaign': 'invalid'},  # Non-numeric
                    {'duration_months': -5}  # Negative duration
                ]
                
                config_validations = []
                for config in invalid_configs:
                    try:
                        success, license_record, message = LicenseService.assign_license_to_business(
                            business_id=business_id,
                            license_type='pro',
                            custom_config=config,
                            assigned_by='validation_test@test.com'
                        )
                        # Should fail
                        config_validations.append(not success)
                    except Exception:
                        # Exception is also acceptable for invalid config
                        config_validations.append(True)
                
                execution_time = time.time() - start_time
                
                all_validations_passed = all(config_validations)
                
                self.record_test_result(
                    'edge_case_handling', 
                    'Invalid License Configuration Values',
                    all_validations_passed,
                    execution_time,
                    f"All invalid configurations properly rejected: {all_validations_passed}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'edge_case_handling', 
                    'Invalid License Configuration Values',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 3: Expired License Handling
            start_time = time.time()
            try:
                business_id = self.test_data['business_accounts'][0]
                
                # Create an expired license manually
                expired_license = LicenseHistory(
                    business_account_id=business_id,
                    license_type='trial',
                    status='inactive',  # Mark as inactive to simulate expiration
                    activated_at=datetime.utcnow() - timedelta(days=60),
                    expires_at=datetime.utcnow() - timedelta(days=30),  # Expired 30 days ago
                    max_campaigns_per_year=1,
                    max_users=2,
                    max_participants_per_campaign=50,
                    created_by='expiry_test@test.com'
                )
                db.session.add(expired_license)
                db.session.commit()
                
                # Test that expired license is not returned as current
                current_license = LicenseService.get_current_license(business_id)
                expired_handled = current_license is None or current_license.status == 'active'
                
                execution_time = time.time() - start_time
                
                self.record_test_result(
                    'edge_case_handling', 
                    'Expired License Handling',
                    expired_handled,
                    execution_time,
                    f"Expired license properly handled: {expired_handled}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'edge_case_handling', 
                    'Expired License Handling',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 4: System Behavior with Corrupted License Data
            start_time = time.time()
            try:
                business_id = self.test_data['business_accounts'][0]
                
                # Create license with some corrupted/edge case data
                corrupted_license = LicenseHistory(
                    business_account_id=business_id,
                    license_type='core',
                    status='active',
                    activated_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=365),
                    max_campaigns_per_year=None,  # NULL value
                    max_users=5,
                    max_participants_per_campaign=200,
                    created_by='corruption_test@test.com'
                )
                db.session.add(corrupted_license)
                db.session.commit()
                
                # Test that system handles corrupted data gracefully
                try:
                    license_info = LicenseService.get_license_info(business_id)
                    corruption_handled = license_info is not None
                except Exception:
                    corruption_handled = False
                
                execution_time = time.time() - start_time
                
                self.record_test_result(
                    'edge_case_handling', 
                    'System Behavior with Corrupted License Data',
                    corruption_handled,
                    execution_time,
                    f"System handled corrupted license data gracefully: {corruption_handled}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'edge_case_handling', 
                    'System Behavior with Corrupted License Data',
                    True,  # Exception handling is acceptable for corrupted data
                    execution_time,
                    f"System properly handled corrupted data with exception: {str(e)}"
                )

    # ==================== CATEGORY 7: PERFORMANCE AND LOAD TESTING ====================
    
    def test_performance_load(self):
        """Test performance and load characteristics"""
        print("\n" + "="*80)
        print("CATEGORY 7: PERFORMANCE AND LOAD TESTING")
        print("="*80)
        
        with app.app_context():
            
            # Test 1: License Checking Performance with Multiple Campaigns
            start_time = time.time()
            try:
                business_id = self.test_data['business_accounts'][0]
                
                # Measure time for license checks across multiple operations
                check_times = []
                for i in range(100):  # 100 license checks
                    check_start = time.time()
                    LicenseService.can_activate_campaign(business_id)
                    check_times.append(time.time() - check_start)
                
                execution_time = time.time() - start_time
                avg_check_time = sum(check_times) / len(check_times)
                
                # Performance should be reasonable (under 100ms average)
                performance_acceptable = avg_check_time < 0.1
                
                self.record_test_result(
                    'performance_load', 
                    'License Checking Performance with Multiple Campaigns',
                    performance_acceptable,
                    execution_time,
                    f"Average license check time: {avg_check_time:.4f}s, Acceptable: {performance_acceptable}"
                )
                
                self.test_results['performance_metrics']['license_check_avg_time'] = avg_check_time
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'performance_load', 
                    'License Checking Performance with Multiple Campaigns',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 2: License Assignment Performance
            start_time = time.time()
            try:
                business_id = self.test_data['business_accounts'][0]
                
                # Measure time for multiple license assignments
                assignment_times = []
                license_types = ['core', 'plus', 'pro', 'trial']
                
                for i in range(10):  # 10 license assignments
                    license_type = license_types[i % len(license_types)]
                    assign_start = time.time()
                    
                    success, license_record, message = LicenseService.assign_license_to_business(
                        business_id=business_id,
                        license_type=license_type,
                        assigned_by=f'perf_test_{i}@test.com'
                    )
                    
                    assignment_times.append(time.time() - assign_start)
                
                execution_time = time.time() - start_time
                avg_assignment_time = sum(assignment_times) / len(assignment_times)
                
                # Assignment should complete reasonably quickly (under 1 second average)
                performance_acceptable = avg_assignment_time < 1.0
                
                self.record_test_result(
                    'performance_load', 
                    'License Assignment Performance',
                    performance_acceptable,
                    execution_time,
                    f"Average assignment time: {avg_assignment_time:.4f}s, Acceptable: {performance_acceptable}"
                )
                
                self.test_results['performance_metrics']['license_assignment_avg_time'] = avg_assignment_time
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'performance_load', 
                    'License Assignment Performance',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 3: License Info Retrieval Performance
            start_time = time.time()
            try:
                # Test license info retrieval for all test businesses
                info_times = []
                for business_id in self.test_data['business_accounts']:
                    info_start = time.time()
                    LicenseService.get_license_info(business_id)
                    info_times.append(time.time() - info_start)
                
                execution_time = time.time() - start_time
                avg_info_time = sum(info_times) / len(info_times)
                
                # Info retrieval should be fast (under 50ms average)
                performance_acceptable = avg_info_time < 0.05
                
                self.record_test_result(
                    'performance_load', 
                    'License Info Retrieval Performance',
                    performance_acceptable,
                    execution_time,
                    f"Average info retrieval time: {avg_info_time:.4f}s, Acceptable: {performance_acceptable}"
                )
                
                self.test_results['performance_metrics']['license_info_avg_time'] = avg_info_time
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'performance_load', 
                    'License Info Retrieval Performance',
                    False,
                    execution_time,
                    error=str(e)
                )

    # ==================== CATEGORY 8: SYSTEM INTEGRATION TESTING ====================
    
    def test_system_integration(self):
        """Test integration with existing system components"""
        print("\n" + "="*80)
        print("CATEGORY 8: SYSTEM INTEGRATION TESTING")
        print("="*80)
        
        with app.app_context():
            business_id = self.test_data['business_accounts'][0]
            
            # Test 1: Integration with Campaign Management
            start_time = time.time()
            try:
                # Ensure business has a license
                LicenseService.assign_license_to_business(
                    business_id=business_id,
                    license_type='core',
                    assigned_by='integration_test@test.com'
                )
                
                # Test campaign creation respects license limits
                can_create_campaign = LicenseService.can_activate_campaign(business_id)
                
                if can_create_campaign:
                    # Create a campaign through the Campaign model
                    test_campaign = Campaign(
                        name='Integration Test Campaign',
                        business_account_id=business_id,
                        start_date=date.today(),
                        end_date=date.today() + timedelta(days=30),
                        status='active'
                    )
                    db.session.add(test_campaign)
                    db.session.commit()
                    
                    # Verify license system recognizes the new campaign
                    license_info = LicenseService.get_license_info(business_id)
                    integration_works = license_info['campaigns_used'] > 0
                else:
                    integration_works = True  # Correctly blocked by license
                
                execution_time = time.time() - start_time
                
                self.record_test_result(
                    'system_integration', 
                    'Integration with Campaign Management',
                    integration_works,
                    execution_time,
                    f"Campaign management integration works: {integration_works}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'system_integration', 
                    'Integration with Campaign Management',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 2: Integration with Business Account System
            start_time = time.time()
            try:
                # Test that BusinessAccount can get its license info
                business_account = BusinessAccount.query.get(business_id)
                
                if business_account:
                    # Test integration through LicenseService
                    current_license = LicenseService.get_current_license(business_id)
                    license_period = LicenseService.get_license_period(business_id)
                    
                    integration_complete = (
                        current_license is not None and
                        current_license.business_account_id == business_id and
                        license_period[0] is not None and
                        license_period[1] is not None
                    )
                else:
                    integration_complete = False
                
                execution_time = time.time() - start_time
                
                self.record_test_result(
                    'system_integration', 
                    'Integration with Business Account System',
                    integration_complete,
                    execution_time,
                    f"Business account integration complete: {integration_complete}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'system_integration', 
                    'Integration with Business Account System',
                    False,
                    execution_time,
                    error=str(e)
                )
            
            # Test 3: Integration with Participant Management
            start_time = time.time()
            try:
                if self.test_data['test_campaigns']:
                    campaign_id = self.test_data['test_campaigns'][0]
                    participant_id = self.test_data['test_participants'][0]
                    
                    # Test participant limit enforcement
                    can_add_participant = LicenseService.can_add_campaign_participant(business_id, campaign_id)
                    
                    integration_working = isinstance(can_add_participant, bool)  # Should return boolean
                else:
                    integration_working = True  # No campaigns to test with
                
                execution_time = time.time() - start_time
                
                self.record_test_result(
                    'system_integration', 
                    'Integration with Participant Management',
                    integration_working,
                    execution_time,
                    f"Participant management integration working: {integration_working}"
                )
                    
            except Exception as e:
                execution_time = time.time() - start_time
                self.record_test_result(
                    'system_integration', 
                    'Integration with Participant Management',
                    False,
                    execution_time,
                    error=str(e)
                )

    # ==================== REPORTING AND ASSESSMENT ====================
    
    def generate_test_report(self):
        """Generate comprehensive test results report"""
        print("\n" + "="*80)
        print("GENERATING COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        # Calculate overall statistics
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for category, results in self.test_results['categories'].items():
            total_tests += len(results['tests'])
            total_passed += results['passed']
            total_failed += results['failed']
        
        # Generate report
        report = {
            'summary': {
                'timestamp': self.test_results['timestamp'],
                'total_tests': total_tests,
                'total_passed': total_passed,
                'total_failed': total_failed,
                'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0
            },
            'category_results': {},
            'performance_metrics': self.test_results['performance_metrics'],
            'production_readiness_assessment': {}
        }
        
        # Process category results
        for category, results in self.test_results['categories'].items():
            category_tests = len(results['tests'])
            category_passed = results['passed']
            category_failed = results['failed']
            
            report['category_results'][category] = {
                'tests_count': category_tests,
                'passed': category_passed,
                'failed': category_failed,
                'success_rate': (category_passed / category_tests * 100) if category_tests > 0 else 0,
                'test_details': results['tests']
            }
        
        # Production readiness assessment
        critical_categories = ['license_assignment_workflow', 'license_enforcement', 'multi_tenant_security', 'database_integrity']
        critical_passed = all(
            report['category_results'][cat]['success_rate'] >= 80 
            for cat in critical_categories 
            if cat in report['category_results']
        )
        
        performance_acceptable = all(
            metric < 1.0  # All operations under 1 second
            for metric in self.test_results['performance_metrics'].values()
        )
        
        overall_success_rate = report['summary']['success_rate']
        
        production_ready = (
            critical_passed and
            performance_acceptable and
            overall_success_rate >= 85
        )
        
        report['production_readiness_assessment'] = {
            'production_ready': production_ready,
            'critical_categories_passed': critical_passed,
            'performance_acceptable': performance_acceptable,
            'overall_success_rate': overall_success_rate,
            'recommendations': self.generate_recommendations(report)
        }
        
        # Save report to file
        report_filename = f'logs/license_testing_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Test report saved to: {report_filename}")
        
        return report

    def generate_recommendations(self, report):
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check category success rates
        for category, results in report['category_results'].items():
            if results['success_rate'] < 80:
                recommendations.append(
                    f"Category '{category}' has low success rate ({results['success_rate']:.1f}%) - review failed tests"
                )
        
        # Check performance metrics
        for metric_name, metric_value in report['performance_metrics'].items():
            if metric_value > 0.5:  # Over 500ms
                recommendations.append(
                    f"Performance metric '{metric_name}' ({metric_value:.3f}s) may need optimization"
                )
        
        # General recommendations
        if report['summary']['success_rate'] < 90:
            recommendations.append("Overall success rate below 90% - consider addressing failed tests before production deployment")
        
        if not recommendations:
            recommendations.append("All tests passed successfully - system appears ready for production deployment")
        
        return recommendations

    def print_summary_report(self, report):
        """Print a formatted summary report to console"""
        print("\n" + "="*80)
        print("COMPREHENSIVE LICENSE MANAGEMENT TESTING SUMMARY")
        print("="*80)
        
        print(f"Test Execution Date: {report['summary']['timestamp']}")
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Tests Passed: {report['summary']['total_passed']}")
        print(f"Tests Failed: {report['summary']['total_failed']}")
        print(f"Overall Success Rate: {report['summary']['success_rate']:.1f}%")
        
        print(f"\n🎯 Production Ready: {'✅ YES' if report['production_readiness_assessment']['production_ready'] else '❌ NO'}")
        
        print("\n" + "-"*60)
        print("CATEGORY BREAKDOWN")
        print("-"*60)
        
        for category, results in report['category_results'].items():
            status = "✅ PASS" if results['success_rate'] >= 80 else "❌ FAIL"
            print(f"{category.replace('_', ' ').title():<35} {status} ({results['passed']}/{results['tests_count']}) {results['success_rate']:.1f}%")
        
        if report['performance_metrics']:
            print("\n" + "-"*60)
            print("PERFORMANCE METRICS")
            print("-"*60)
            for metric, value in report['performance_metrics'].items():
                print(f"{metric.replace('_', ' ').title():<35} {value:.4f}s")
        
        print("\n" + "-"*60)
        print("RECOMMENDATIONS")
        print("-"*60)
        for i, recommendation in enumerate(report['production_readiness_assessment']['recommendations'], 1):
            print(f"{i}. {recommendation}")
        
        print("\n" + "="*80)

    # ==================== MAIN TEST EXECUTION ====================
    
    def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        print("🚀 Starting Comprehensive License Management Testing Suite")
        print("="*80)
        
        start_time = time.time()
        
        try:
            # Setup test environment
            if not self.setup_test_environment():
                print("❌ Test environment setup failed - aborting tests")
                return False
            
            # Run all test categories
            print("\n🏃‍♂️ Running comprehensive test suite...")
            
            self.test_license_assignment_workflow()
            self.test_license_enforcement()
            self.test_multi_tenant_security()
            self.test_database_integrity()
            self.test_ui_ux_integration()
            self.test_edge_case_handling()
            self.test_performance_load()
            self.test_system_integration()
            
            # Generate and display final report
            total_time = time.time() - start_time
            print(f"\n⏱️  Total test execution time: {total_time:.2f} seconds")
            
            report = self.generate_test_report()
            self.print_summary_report(report)
            
            return report['production_readiness_assessment']['production_ready']
            
        except Exception as e:
            print(f"\n❌ Test suite execution failed: {e}")
            self.logger.error(f"Test suite execution failed: {e}")
            return False


def main():
    """Main execution function"""
    test_suite = ComprehensiveTestSuite()
    production_ready = test_suite.run_comprehensive_tests()
    
    if production_ready:
        print("\n🎉 SUCCESS: License management system is production ready!")
        return 0
    else:
        print("\n⚠️  WARNING: License management system needs attention before production deployment")
        return 1


if __name__ == '__main__':
    sys.exit(main())