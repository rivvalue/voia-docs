#!/usr/bin/env python3
"""
Test script to verify email service configuration and error handling
"""

import sys
import os
sys.path.insert(0, '.')

from app import app, db
from email_service import email_service
from models import EmailDelivery, Campaign, Participant, CampaignParticipant
import json

def test_email_service_configuration():
    """Test email service configuration status"""
    print("=== EMAIL SERVICE CONFIGURATION TEST ===")
    
    # Test email service configuration status
    is_configured = email_service.is_configured()
    print(f"Email service configured: {is_configured}")
    
    # Print configuration details (without exposing secrets)
    print(f"SMTP Server: {'Set' if email_service.smtp_server else 'Not Set'}")
    print(f"SMTP Port: {'Set' if email_service.smtp_port else 'Not Set'}")
    print(f"SMTP Username: {'Set' if email_service.smtp_username else 'Not Set'}")
    print(f"SMTP Password: {'Set' if email_service.smtp_password else 'Not Set'}")
    print(f"Admin Emails: {len(email_service.admin_emails)} configured")
    
    return is_configured

def test_email_service_error_handling():
    """Test email service error handling when not configured"""
    print("\n=== EMAIL SERVICE ERROR HANDLING TEST ===")
    
    # Test sending email when service is not configured
    try:
        result = email_service.send_email(
            to_emails=['test@example.com'],
            subject='Test Email',
            text_body='This is a test email',
            html_body='<p>This is a test email</p>'
        )
        
        print(f"Send email result: {result}")
        print(f"Success: {result.get('success', False)}")
        print(f"Error: {result.get('error', 'No error')}")
        
        return result
        
    except Exception as e:
        print(f"Exception during email send test: {e}")
        return {'success': False, 'error': str(e)}

def test_email_delivery_tracking():
    """Test EmailDelivery record creation and tracking"""
    print("\n=== EMAIL DELIVERY TRACKING TEST ===")
    
    try:
        # Query existing EmailDelivery records
        email_deliveries = EmailDelivery.query.all()
        print(f"Total EmailDelivery records: {len(email_deliveries)}")
        
        if email_deliveries:
            # Examine the first record
            delivery = email_deliveries[0]
            print(f"Sample delivery record:")
            print(f"  ID: {delivery.id}")
            print(f"  Status: {delivery.status}")
            print(f"  Email Type: {delivery.email_type}")
            print(f"  Recipient: {delivery.recipient_email}")
            print(f"  Subject: {delivery.subject}")
            print(f"  Retry Count: {delivery.retry_count}")
            print(f"  Max Retries: {delivery.max_retries}")
            print(f"  Created: {delivery.created_at}")
            print(f"  Last Error: {delivery.last_error}")
            
            # Test the email_data JSON field
            if delivery.email_data:
                try:
                    email_data = json.loads(delivery.email_data) if isinstance(delivery.email_data, str) else delivery.email_data
                    print(f"  Email Data: {email_data}")
                except Exception as e:
                    print(f"  Email Data (raw): {delivery.email_data}")
                    print(f"  JSON parse error: {e}")
        
        return True
        
    except Exception as e:
        print(f"Error querying EmailDelivery records: {e}")
        return False

def test_campaign_data():
    """Test campaign and participant data for invitation testing"""
    print("\n=== CAMPAIGN AND PARTICIPANT DATA TEST ===")
    
    try:
        # Get active campaigns
        active_campaigns = Campaign.query.filter_by(status='active').all()
        print(f"Active campaigns: {len(active_campaigns)}")
        
        for campaign in active_campaigns:
            print(f"  Campaign: {campaign.name} (ID: {campaign.id})")
            print(f"    Status: {campaign.status}")
            print(f"    Start Date: {campaign.start_date}")
            print(f"    End Date: {campaign.end_date}")
            print(f"    Business Account: {campaign.business_account_id}")
            
            # Get campaign participants
            participants = CampaignParticipant.query.filter_by(campaign_id=campaign.id).all()
            print(f"    Participants: {len(participants)}")
            
            if participants:
                for i, cp in enumerate(participants[:3]):  # Show first 3
                    participant = cp.participant
                    print(f"      {i+1}. {participant.name} ({participant.email}) - Status: {cp.status}")
                if len(participants) > 3:
                    print(f"      ... and {len(participants) - 3} more")
        
        return True
        
    except Exception as e:
        print(f"Error querying campaign data: {e}")
        return False

def main():
    """Run all email service tests"""
    print("Starting comprehensive email service tests...\n")
    
    with app.app_context():
        # Test 1: Email service configuration
        configured = test_email_service_configuration()
        
        # Test 2: Error handling when not configured
        error_result = test_email_service_error_handling()
        
        # Test 3: Email delivery tracking
        tracking_result = test_email_delivery_tracking()
        
        # Test 4: Campaign and participant data
        data_result = test_campaign_data()
        
        # Summary
        print("\n=== TEST SUMMARY ===")
        print(f"Email service configured: {configured}")
        print(f"Error handling working: {not error_result.get('success', True)}")  # We expect failure when not configured
        print(f"Delivery tracking working: {tracking_result}")
        print(f"Campaign data available: {data_result}")
        
        # Overall status
        if not configured and not error_result.get('success') and tracking_result and data_result:
            print("\n✅ All tests passed! Email system ready for SMTP configuration.")
        else:
            print("\n❌ Some tests failed. Check the details above.")

if __name__ == '__main__':
    main()