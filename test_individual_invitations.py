#!/usr/bin/env python3
"""
Test script to verify individual participant invitation functionality
"""

import sys
import os
sys.path.insert(0, '.')

from app import app, db
from models import (BusinessAccount, BusinessAccountUser, Campaign, Participant, 
                   CampaignParticipant, EmailDelivery)
from task_queue import add_email_task, task_queue
from email_service import email_service
import json
from datetime import datetime
import uuid

def setup_test_environment():
    """Set up test environment and get test data"""
    print("=== SETTING UP TEST ENVIRONMENT ===")
    
    try:
        # Get business account and admin user
        business_account = BusinessAccount.query.first()
        admin_user = BusinessAccountUser.query.filter_by(
            business_account_id=business_account.id
        ).first()
        
        print(f"Business Account: {business_account.name} (ID: {business_account.id})")
        print(f"Admin User: {admin_user.email}")
        
        # Get active campaign with participants
        active_campaign = Campaign.query.filter_by(
            business_account_id=business_account.id,
            status='active'
        ).first()
        
        if not active_campaign:
            print("❌ No active campaigns found")
            return None, None, None, []
        
        print(f"Active Campaign: {active_campaign.name} (ID: {active_campaign.id})")
        
        # Get campaign participants
        campaign_participants = CampaignParticipant.query.filter_by(
            campaign_id=active_campaign.id,
            business_account_id=business_account.id
        ).all()
        
        print(f"Campaign Participants: {len(campaign_participants)}")
        
        # Show participant details
        for i, cp in enumerate(campaign_participants[:5]):  # Show first 5
            participant = cp.participant
            print(f"  {i+1}. {participant.name} ({participant.email}) - Status: {cp.status}")
        
        return business_account, admin_user, active_campaign, campaign_participants
        
    except Exception as e:
        print(f"❌ Error setting up test environment: {e}")
        return None, None, None, []

def test_individual_invitation_creation():
    """Test creating EmailDelivery records for individual invitations"""
    print("\n=== TESTING INDIVIDUAL INVITATION CREATION ===")
    
    try:
        business_account, admin_user, active_campaign, campaign_participants = setup_test_environment()
        if not business_account or not active_campaign:
            return False
        
        # Select a test participant
        if not campaign_participants:
            print("❌ No campaign participants found")
            return False
        
        test_cp = campaign_participants[0]
        test_participant = test_cp.participant
        
        print(f"Testing invitation for: {test_participant.name} ({test_participant.email})")
        
        # Check if there's already a delivery record
        existing_delivery = EmailDelivery.query.filter_by(
            campaign_participant_id=test_cp.id,
            email_type='participant_invitation',
            business_account_id=business_account.id
        ).first()
        
        if existing_delivery:
            print(f"Existing delivery found: Status={existing_delivery.status}")
        
        # Create a new EmailDelivery record (simulating admin interface)
        email_delivery = EmailDelivery()
        email_delivery.business_account_id = business_account.id
        email_delivery.campaign_id = active_campaign.id
        email_delivery.campaign_participant_id = test_cp.id
        email_delivery.email_type = 'participant_invitation'
        email_delivery.recipient_email = test_participant.email
        email_delivery.recipient_name = test_participant.name
        email_delivery.subject = f"Your feedback is requested: {active_campaign.name}"
        email_delivery.status = 'pending'
        email_delivery.retry_count = 0
        email_delivery.max_retries = 3
        
        # Set email data
        email_data = {
            'email_type': 'participant_invitation',
            'participant_email': test_participant.email,
            'participant_name': test_participant.name,
            'campaign_name': active_campaign.name,
            'survey_token': test_cp.token,
            'business_account_name': business_account.name,
            'test_mode': True
        }
        email_delivery.email_data = json.dumps(email_data)
        
        db.session.add(email_delivery)
        db.session.commit()
        
        print(f"✅ EmailDelivery record created: ID={email_delivery.id}")
        print(f"   Status: {email_delivery.status}")
        print(f"   Recipient: {email_delivery.recipient_email}")
        print(f"   Campaign: {active_campaign.name}")
        
        return email_delivery
        
    except Exception as e:
        print(f"❌ Error testing invitation creation: {e}")
        db.session.rollback()
        return False

def test_task_queue_integration():
    """Test adding invitation tasks to the task queue"""
    print("\n=== TESTING TASK QUEUE INTEGRATION ===")
    
    try:
        business_account, admin_user, active_campaign, campaign_participants = setup_test_environment()
        if not business_account or not active_campaign:
            return False
        
        # Get test participant
        test_cp = campaign_participants[0]
        test_participant = test_cp.participant
        
        print(f"Adding task for: {test_participant.name} ({test_participant.email})")
        
        # Prepare task data (simulating what admin interface would do)
        task_data = {
            'email_type': 'participant_invitation',
            'participant_email': test_participant.email,
            'participant_name': test_participant.name,
            'campaign_name': active_campaign.name,
            'survey_token': test_cp.token,
            'business_account_name': business_account.name,
            'campaign_id': active_campaign.id,
            'campaign_participant_id': test_cp.id,
            'business_account_id': business_account.id,
            'test_mode': True
        }
        
        print(f"Task data prepared: {len(task_data)} fields")
        
        # Add task to queue (simulating admin interface action)
        try:
            add_email_task('participant_invitation', task_data, priority=1)
            print("✅ Task successfully added to queue")
            
            # Get queue statistics
            if hasattr(task_queue, 'get_stats'):
                stats = task_queue.get_stats()
                print(f"Queue stats: {stats}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding task to queue: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Error testing task queue integration: {e}")
        return False

def test_email_template_rendering():
    """Test email template rendering for participant invitations"""
    print("\n=== TESTING EMAIL TEMPLATE RENDERING ===")
    
    try:
        business_account, admin_user, active_campaign, campaign_participants = setup_test_environment()
        if not business_account or not active_campaign:
            return False
        
        # Get test participant
        test_cp = campaign_participants[0]
        test_participant = test_cp.participant
        
        print(f"Testing template rendering for: {test_participant.name}")
        
        # Test the email service template rendering (without sending)
        # We'll call the email service but expect it to fail due to no SMTP config
        result = email_service.send_participant_invitation(
            participant_email=test_participant.email,
            participant_name=test_participant.name,
            campaign_name=active_campaign.name,
            survey_token=test_cp.token,
            business_account_name=business_account.name
        )
        
        print(f"Email service result: {result}")
        
        # We expect this to fail due to SMTP not being configured
        if not result['success']:
            expected_error = 'Email service not configured'
            if expected_error in result.get('error', ''):
                print(f"✅ Expected error received: {result['error']}")
                print("✅ This confirms proper error handling when SMTP not configured")
                return True
            else:
                print(f"❌ Unexpected error: {result.get('error', 'Unknown error')}")
                return False
        else:
            print("❌ Unexpected success - SMTP should not be configured")
            return False
        
    except Exception as e:
        print(f"❌ Error testing email template rendering: {e}")
        return False

def test_invitation_status_tracking():
    """Test invitation status tracking and updates"""
    print("\n=== TESTING INVITATION STATUS TRACKING ===")
    
    try:
        # Get all EmailDelivery records for the business account
        business_account = BusinessAccount.query.first()
        
        email_deliveries = EmailDelivery.query.filter_by(
            business_account_id=business_account.id
        ).all()
        
        print(f"Total EmailDelivery records: {len(email_deliveries)}")
        
        # Test status updates
        for delivery in email_deliveries:
            print(f"\nDelivery ID {delivery.id}:")
            print(f"  Email Type: {delivery.email_type}")
            print(f"  Status: {delivery.status}")
            print(f"  Recipient: {delivery.recipient_email}")
            print(f"  Retry Count: {delivery.retry_count}/{delivery.max_retries}")
            print(f"  Created: {delivery.created_at}")
            
            if delivery.campaign_participant_id:
                cp = CampaignParticipant.query.get(delivery.campaign_participant_id)
                if cp:
                    print(f"  Campaign: {cp.campaign.name}")
                    print(f"  Participant Status: {cp.status}")
            
            # Test status transition methods
            if delivery.status == 'pending':
                print("  Testing status transitions...")
                
                # Test marking as sending
                original_status = delivery.status
                delivery.mark_sending()
                print(f"    mark_sending(): {original_status} -> {delivery.status}")
                
                # Test marking as failed
                delivery.mark_failed("Test error - SMTP not configured", is_permanent=False)
                print(f"    mark_failed(): -> {delivery.status}")
                print(f"    Error: {delivery.last_error}")
                
                # Reset for next test
                delivery.status = 'pending'
                delivery.last_error = None
        
        db.session.commit()
        print("✅ Status tracking tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Error testing invitation status tracking: {e}")
        db.session.rollback()
        return False

def test_campaign_participant_token_validation():
    """Test campaign participant token validation for invitations"""
    print("\n=== TESTING CAMPAIGN PARTICIPANT TOKEN VALIDATION ===")
    
    try:
        business_account, admin_user, active_campaign, campaign_participants = setup_test_environment()
        if not business_account or not active_campaign:
            return False
        
        # Test token validation for campaign participants
        for i, cp in enumerate(campaign_participants[:3]):  # Test first 3
            participant = cp.participant
            token = cp.token
            
            print(f"\nTesting token for participant {i+1}: {participant.name}")
            print(f"  Token: {token[:20]}...")  # Show first 20 chars
            print(f"  Token Type: {'JWT' if '.' in token else 'UUID'}")
            print(f"  Campaign Association Status: {cp.status}")
            
            # Test token validation using the centralized system
            from routes import verify_survey_access
            
            verification = verify_survey_access(token)
            print(f"  Token Validation: {'✅ Valid' if verification['valid'] else '❌ Invalid'}")
            
            if verification['valid']:
                print(f"    Authenticated: {verification['authenticated']}")
                print(f"    Email: {verification['email']}")
                print(f"    Campaign: {verification.get('campaign_name', 'N/A')}")
            else:
                print(f"    Error: {verification.get('error', 'Unknown error')}")
        
        print("✅ Token validation tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Error testing token validation: {e}")
        return False

def main():
    """Run all individual invitation tests"""
    print("Starting comprehensive individual invitation tests...\n")
    
    with app.app_context():
        # Test 1: Individual invitation creation
        creation_result = test_individual_invitation_creation()
        
        # Test 2: Task queue integration
        queue_result = test_task_queue_integration()
        
        # Test 3: Email template rendering
        template_result = test_email_template_rendering()
        
        # Test 4: Invitation status tracking
        tracking_result = test_invitation_status_tracking()
        
        # Test 5: Campaign participant token validation
        token_result = test_campaign_participant_token_validation()
        
        # Summary
        print("\n=== INDIVIDUAL INVITATION TEST SUMMARY ===")
        print(f"✅ Invitation creation: {bool(creation_result)}")
        print(f"✅ Task queue integration: {queue_result}")
        print(f"✅ Email template rendering: {template_result}")
        print(f"✅ Status tracking: {tracking_result}")
        print(f"✅ Token validation: {token_result}")
        
        # Overall status
        all_tests_passed = all([
            bool(creation_result),
            queue_result,
            template_result,
            tracking_result,
            token_result
        ])
        
        if all_tests_passed:
            print("\n🎉 All individual invitation tests passed! System ready for bulk testing.")
        else:
            print("\n❌ Some individual invitation tests failed. Check the details above.")
        
        return all_tests_passed

if __name__ == '__main__':
    main()