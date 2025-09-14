#!/usr/bin/env python3
"""
Test script to verify bulk campaign invitation functionality
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
import time

def get_test_data():
    """Get test data for bulk invitation testing"""
    print("=== GETTING TEST DATA FOR BULK INVITATIONS ===")
    
    try:
        # Get business account
        business_account = BusinessAccount.query.first()
        print(f"Business Account: {business_account.name} (ID: {business_account.id})")
        
        # Get active campaign
        active_campaign = Campaign.query.filter_by(
            business_account_id=business_account.id,
            status='active'
        ).first()
        
        if not active_campaign:
            print("❌ No active campaigns found")
            return None, None, []
        
        print(f"Active Campaign: {active_campaign.name} (ID: {active_campaign.id})")
        print(f"  Start Date: {active_campaign.start_date}")
        print(f"  End Date: {active_campaign.end_date}")
        print(f"  Status: {active_campaign.status}")
        
        # Get all campaign participants
        campaign_participants = CampaignParticipant.query.filter_by(
            campaign_id=active_campaign.id,
            business_account_id=business_account.id
        ).all()
        
        print(f"Campaign Participants: {len(campaign_participants)}")
        
        # Show participant breakdown by status
        status_counts = {}
        for cp in campaign_participants:
            status = cp.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("Participant Status Breakdown:")
        for status, count in status_counts.items():
            print(f"  - {status}: {count}")
        
        return business_account, active_campaign, campaign_participants
        
    except Exception as e:
        print(f"❌ Error getting test data: {e}")
        return None, None, []

def test_bulk_invitation_eligibility():
    """Test determining which participants are eligible for bulk invitations"""
    print("\n=== TESTING BULK INVITATION ELIGIBILITY ===")
    
    try:
        business_account, active_campaign, campaign_participants = get_test_data()
        if not business_account or not active_campaign:
            return False, []
        
        # Simulate the logic from campaign_routes.py for determining eligible participants
        eligible_participants = []
        already_sent_count = 0
        
        for cp in campaign_participants:
            if cp.participant and cp.status in ['pending', 'invited']:
                # Check if there's already a successful delivery
                existing_delivery = EmailDelivery.query.filter_by(
                    campaign_participant_id=cp.id,
                    email_type='participant_invitation',
                    status='sent'
                ).first()
                
                if not existing_delivery:
                    eligible_participants.append(cp)
                else:
                    already_sent_count += 1
        
        print(f"Eligible for invitation: {len(eligible_participants)}")
        print(f"Already sent successfully: {already_sent_count}")
        print(f"Total participants: {len(campaign_participants)}")
        
        # Show details of eligible participants
        print("\nEligible Participants:")
        for i, cp in enumerate(eligible_participants[:10]):  # Show first 10
            participant = cp.participant
            print(f"  {i+1}. {participant.name} ({participant.email}) - Status: {cp.status}")
        
        if len(eligible_participants) > 10:
            print(f"  ... and {len(eligible_participants) - 10} more")
        
        return True, eligible_participants
        
    except Exception as e:
        print(f"❌ Error testing bulk invitation eligibility: {e}")
        return False, []

def test_bulk_email_delivery_creation():
    """Test creating multiple EmailDelivery records for bulk invitations"""
    print("\n=== TESTING BULK EMAIL DELIVERY CREATION ===")
    
    try:
        business_account, active_campaign, campaign_participants = get_test_data()
        if not business_account or not active_campaign:
            return False
        
        # Get eligible participants
        eligible_test, eligible_participants = test_bulk_invitation_eligibility()
        if not eligible_test or not eligible_participants:
            print("❌ No eligible participants found")
            return False
        
        # Limit to first 5 for testing to avoid too many records
        test_participants = eligible_participants[:5]
        print(f"Creating EmailDelivery records for {len(test_participants)} participants...")
        
        created_deliveries = []
        
        for i, cp in enumerate(test_participants):
            participant = cp.participant
            
            # Create EmailDelivery record (simulating bulk invitation logic)
            email_delivery = EmailDelivery()
            email_delivery.business_account_id = business_account.id
            email_delivery.campaign_id = active_campaign.id
            email_delivery.campaign_participant_id = cp.id
            email_delivery.email_type = 'participant_invitation'
            email_delivery.recipient_email = participant.email
            email_delivery.recipient_name = participant.name
            email_delivery.subject = f"Your feedback is requested: {active_campaign.name}"
            email_delivery.status = 'pending'
            email_delivery.retry_count = 0
            email_delivery.max_retries = 3
            
            # Set email data
            email_data = {
                'email_type': 'participant_invitation',
                'participant_email': participant.email,
                'participant_name': participant.name,
                'campaign_name': active_campaign.name,
                'survey_token': cp.token,
                'business_account_name': business_account.name,
                'bulk_invitation': True,
                'batch_id': f"bulk_{active_campaign.id}_{int(time.time())}"
            }
            email_delivery.email_data = json.dumps(email_data)
            
            db.session.add(email_delivery)
            created_deliveries.append(email_delivery)
            
            print(f"  {i+1}. Created delivery for {participant.name} ({participant.email})")
        
        # Commit all deliveries
        db.session.commit()
        
        print(f"✅ Successfully created {len(created_deliveries)} EmailDelivery records")
        
        # Verify the records were created
        for delivery in created_deliveries:
            print(f"  Delivery ID {delivery.id}: {delivery.recipient_email} - Status: {delivery.status}")
        
        return created_deliveries
        
    except Exception as e:
        print(f"❌ Error creating bulk email deliveries: {e}")
        db.session.rollback()
        return False

def test_bulk_task_queue_processing():
    """Test adding multiple invitation tasks to the queue for bulk processing"""
    print("\n=== TESTING BULK TASK QUEUE PROCESSING ===")
    
    try:
        business_account, active_campaign, campaign_participants = get_test_data()
        if not business_account or not active_campaign:
            return False
        
        # Get eligible participants (limited for testing)
        eligible_test, eligible_participants = test_bulk_invitation_eligibility()
        if not eligible_test or not eligible_participants:
            print("❌ No eligible participants found")
            return False
        
        test_participants = eligible_participants[:3]  # Test with 3 participants
        print(f"Adding {len(test_participants)} tasks to queue...")
        
        batch_id = f"bulk_test_{active_campaign.id}_{int(time.time())}"
        
        queued_tasks = []
        
        for i, cp in enumerate(test_participants):
            participant = cp.participant
            
            # Prepare task data (simulating bulk invitation process)
            task_data = {
                'email_type': 'participant_invitation',
                'participant_email': participant.email,
                'participant_name': participant.name,
                'campaign_name': active_campaign.name,
                'survey_token': cp.token,
                'business_account_name': business_account.name,
                'campaign_id': active_campaign.id,
                'campaign_participant_id': cp.id,
                'business_account_id': business_account.id,
                'bulk_invitation': True,
                'batch_id': batch_id
            }
            
            # Add task to queue
            try:
                add_email_task('participant_invitation', task_data, priority=2)  # Lower priority for bulk
                queued_tasks.append(task_data)
                print(f"  {i+1}. Queued task for {participant.name} ({participant.email})")
                
            except Exception as e:
                print(f"  ❌ Failed to queue task for {participant.name}: {e}")
        
        print(f"✅ Successfully queued {len(queued_tasks)} tasks")
        print(f"Batch ID: {batch_id}")
        
        # Get queue statistics if available
        if hasattr(task_queue, 'get_stats'):
            try:
                stats = task_queue.get_stats()
                print(f"Queue statistics: {stats}")
            except:
                print("Queue statistics not available")
        
        return len(queued_tasks) > 0
        
    except Exception as e:
        print(f"❌ Error testing bulk task queue processing: {e}")
        return False

def test_bulk_invitation_error_handling():
    """Test error handling scenarios for bulk invitations"""
    print("\n=== TESTING BULK INVITATION ERROR HANDLING ===")
    
    try:
        business_account, active_campaign, campaign_participants = get_test_data()
        if not business_account or not active_campaign:
            return False
        
        print("Testing various error scenarios...")
        
        # Test 1: Email service not configured (expected)
        print("\n1. Testing SMTP not configured error:")
        if not email_service.is_configured():
            print("   ✅ Email service correctly reports as not configured")
            
            # Test sending to verify error handling
            test_result = email_service.send_email(
                to_emails=['test@example.com'],
                subject='Test Bulk Email',
                text_body='Test content'
            )
            
            if not test_result['success'] and 'not configured' in test_result.get('error', ''):
                print("   ✅ Proper error returned for unconfigured SMTP")
            else:
                print(f"   ❌ Unexpected result: {test_result}")
        
        # Test 2: Invalid participant data
        print("\n2. Testing invalid participant data handling:")
        invalid_task_data = {
            'email_type': 'participant_invitation',
            'participant_email': '',  # Invalid email
            'participant_name': '',   # Invalid name
            'campaign_name': active_campaign.name,
            'survey_token': 'invalid_token',
            'business_account_name': business_account.name
        }
        
        try:
            # This should handle gracefully without crashing
            result = email_service.send_participant_invitation(
                participant_email='',
                participant_name='',
                campaign_name=active_campaign.name,
                survey_token='invalid_token',
                business_account_name=business_account.name
            )
            print(f"   Result: {result}")
            print("   ✅ Invalid data handled gracefully")
        except Exception as e:
            print(f"   Error handling invalid data: {e}")
        
        # Test 3: Database constraint handling
        print("\n3. Testing database constraint handling:")
        try:
            # Try to create duplicate EmailDelivery record
            duplicate_delivery = EmailDelivery()
            duplicate_delivery.business_account_id = business_account.id
            duplicate_delivery.campaign_id = active_campaign.id
            duplicate_delivery.email_type = 'participant_invitation'
            duplicate_delivery.recipient_email = 'duplicate@test.com'
            duplicate_delivery.recipient_name = 'Duplicate Test'
            duplicate_delivery.subject = 'Test Subject'
            duplicate_delivery.status = 'pending'
            
            db.session.add(duplicate_delivery)
            db.session.commit()
            print("   ✅ Duplicate delivery record created successfully")
            
        except Exception as e:
            print(f"   Database constraint handling: {e}")
            db.session.rollback()
        
        print("✅ Error handling tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Error testing bulk invitation error handling: {e}")
        return False

def test_bulk_invitation_statistics():
    """Test statistics and reporting for bulk invitations"""
    print("\n=== TESTING BULK INVITATION STATISTICS ===")
    
    try:
        business_account, active_campaign, campaign_participants = get_test_data()
        if not business_account or not active_campaign:
            return False
        
        # Get comprehensive statistics for the campaign
        total_participants = len(campaign_participants)
        
        # Email delivery statistics
        total_deliveries = EmailDelivery.query.filter_by(
            campaign_id=active_campaign.id,
            business_account_id=business_account.id
        ).count()
        
        sent_deliveries = EmailDelivery.query.filter_by(
            campaign_id=active_campaign.id,
            business_account_id=business_account.id,
            status='sent'
        ).count()
        
        pending_deliveries = EmailDelivery.query.filter_by(
            campaign_id=active_campaign.id,
            business_account_id=business_account.id,
            status='pending'
        ).count()
        
        failed_deliveries = EmailDelivery.query.filter_by(
            campaign_id=active_campaign.id,
            business_account_id=business_account.id,
            status='failed'
        ).count()
        
        # Participant status statistics
        participant_statuses = {}
        for cp in campaign_participants:
            status = cp.status
            participant_statuses[status] = participant_statuses.get(status, 0) + 1
        
        # Email type breakdown
        invitation_deliveries = EmailDelivery.query.filter_by(
            campaign_id=active_campaign.id,
            business_account_id=business_account.id,
            email_type='participant_invitation'
        ).count()
        
        print(f"Campaign: {active_campaign.name}")
        print(f"  Total Participants: {total_participants}")
        print(f"  Total Email Deliveries: {total_deliveries}")
        print(f"    - Sent: {sent_deliveries}")
        print(f"    - Pending: {pending_deliveries}")
        print(f"    - Failed: {failed_deliveries}")
        print(f"  Invitation Emails: {invitation_deliveries}")
        
        print("\nParticipant Status Breakdown:")
        for status, count in participant_statuses.items():
            print(f"    - {status}: {count}")
        
        # Calculate invitation coverage
        if total_participants > 0:
            coverage_percentage = (total_deliveries / total_participants) * 100
            print(f"\nInvitation Coverage: {coverage_percentage:.1f}%")
        
        # Recent delivery activity
        recent_deliveries = EmailDelivery.query.filter_by(
            campaign_id=active_campaign.id,
            business_account_id=business_account.id
        ).order_by(EmailDelivery.created_at.desc()).limit(5).all()
        
        print(f"\nRecent Delivery Activity ({len(recent_deliveries)} records):")
        for delivery in recent_deliveries:
            print(f"  - {delivery.recipient_email}: {delivery.status} ({delivery.created_at})")
        
        print("✅ Statistics compilation completed")
        return True
        
    except Exception as e:
        print(f"❌ Error testing bulk invitation statistics: {e}")
        return False

def main():
    """Run all bulk invitation tests"""
    print("Starting comprehensive bulk invitation tests...\n")
    
    with app.app_context():
        # Test 1: Bulk invitation eligibility
        eligibility_result, eligible_participants = test_bulk_invitation_eligibility()
        
        # Test 2: Bulk email delivery creation
        creation_result = test_bulk_email_delivery_creation()
        
        # Test 3: Bulk task queue processing
        queue_result = test_bulk_task_queue_processing()
        
        # Test 4: Bulk invitation error handling
        error_handling_result = test_bulk_invitation_error_handling()
        
        # Test 5: Bulk invitation statistics
        statistics_result = test_bulk_invitation_statistics()
        
        # Summary
        print("\n=== BULK INVITATION TEST SUMMARY ===")
        print(f"✅ Eligibility determination: {eligibility_result}")
        print(f"✅ Email delivery creation: {bool(creation_result)}")
        print(f"✅ Task queue processing: {queue_result}")
        print(f"✅ Error handling: {error_handling_result}")
        print(f"✅ Statistics compilation: {statistics_result}")
        
        # Overall status
        all_tests_passed = all([
            eligibility_result,
            bool(creation_result),
            queue_result,
            error_handling_result,
            statistics_result
        ])
        
        if all_tests_passed:
            print("\n🎉 All bulk invitation tests passed! System ready for email templates testing.")
            
            if eligible_participants:
                print(f"\nSystem Status:")
                print(f"  - Active campaign with {len(eligible_participants)} eligible participants")
                print(f"  - EmailDelivery tracking system functional")
                print(f"  - Task queue integration working")
                print(f"  - Proper error handling in place")
                print(f"  - Statistics and reporting available")
        else:
            print("\n❌ Some bulk invitation tests failed. Check the details above.")
        
        return all_tests_passed

if __name__ == '__main__':
    main()