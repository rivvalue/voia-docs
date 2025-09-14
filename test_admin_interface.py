#!/usr/bin/env python3
"""
Test script to verify admin interface functionality and email statistics
"""

import sys
import os
sys.path.insert(0, '.')

from app import app, db
from models import BusinessAccount, BusinessAccountUser, Campaign, Participant, CampaignParticipant, EmailDelivery
from business_auth_routes import get_current_business_account
from werkzeug.security import check_password_hash
import json
from datetime import datetime

def get_admin_credentials():
    """Get the admin user credentials for testing"""
    print("=== ADMIN CREDENTIALS CHECK ===")
    
    try:
        # Get business account
        business_account = BusinessAccount.query.first()
        if not business_account:
            print("❌ No business accounts found")
            return None, None
        
        print(f"Business Account: {business_account.name} (ID: {business_account.id})")
        print(f"Status: {business_account.status}")
        print(f"Account Type: {business_account.account_type}")
        print(f"Contact Email: {business_account.contact_email}")
        
        # Get admin users
        admin_users = BusinessAccountUser.query.filter_by(
            business_account_id=business_account.id
        ).all()
        
        print(f"Admin Users: {len(admin_users)}")
        for user in admin_users:
            print(f"  - {user.email} (Role: {user.role}, Active: {user.is_active})")
        
        if admin_users:
            admin_user = admin_users[0]  # Use first admin user
            return business_account, admin_user
        else:
            print("❌ No admin users found")
            return business_account, None
            
    except Exception as e:
        print(f"❌ Error getting admin credentials: {e}")
        return None, None

def test_admin_campaign_statistics():
    """Test admin campaign statistics functionality"""
    print("\n=== ADMIN CAMPAIGN STATISTICS TEST ===")
    
    try:
        business_account, admin_user = get_admin_credentials()
        if not business_account or not admin_user:
            return False
        
        # Get campaign statistics for the business account
        campaigns = Campaign.query.filter_by(
            business_account_id=business_account.id
        ).all()
        
        print(f"Total Campaigns: {len(campaigns)}")
        
        campaign_stats = {}
        for campaign in campaigns:
            # Get participants count
            participants_count = CampaignParticipant.query.filter_by(
                campaign_id=campaign.id,
                business_account_id=business_account.id
            ).count()
            
            # Get email delivery statistics
            total_deliveries = EmailDelivery.query.filter_by(
                campaign_id=campaign.id,
                business_account_id=business_account.id
            ).count()
            
            sent_deliveries = EmailDelivery.query.filter_by(
                campaign_id=campaign.id,
                business_account_id=business_account.id,
                status='sent'
            ).count()
            
            pending_deliveries = EmailDelivery.query.filter_by(
                campaign_id=campaign.id,
                business_account_id=business_account.id,
                status='pending'
            ).count()
            
            failed_deliveries = EmailDelivery.query.filter_by(
                campaign_id=campaign.id,
                business_account_id=business_account.id,
                status='failed'
            ).count()
            
            campaign_stats[campaign.id] = {
                'name': campaign.name,
                'status': campaign.status,
                'participants': participants_count,
                'total_deliveries': total_deliveries,
                'sent_deliveries': sent_deliveries,
                'pending_deliveries': pending_deliveries,
                'failed_deliveries': failed_deliveries
            }
            
            print(f"\nCampaign: {campaign.name} (Status: {campaign.status})")
            print(f"  Participants: {participants_count}")
            print(f"  Email Deliveries: {total_deliveries} total")
            print(f"    - Sent: {sent_deliveries}")
            print(f"    - Pending: {pending_deliveries}")
            print(f"    - Failed: {failed_deliveries}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting campaign statistics: {e}")
        return False

def test_admin_email_statistics():
    """Test admin email statistics functionality"""
    print("\n=== ADMIN EMAIL STATISTICS TEST ===")
    
    try:
        business_account, admin_user = get_admin_credentials()
        if not business_account or not admin_user:
            return False
        
        # Get overall email statistics for the business account
        total_emails = EmailDelivery.query.filter_by(
            business_account_id=business_account.id
        ).count()
        
        sent_emails = EmailDelivery.query.filter_by(
            business_account_id=business_account.id,
            status='sent'
        ).count()
        
        pending_emails = EmailDelivery.query.filter_by(
            business_account_id=business_account.id,
            status='pending'
        ).count()
        
        failed_emails = EmailDelivery.query.filter_by(
            business_account_id=business_account.id,
            status='failed'
        ).count()
        
        sending_emails = EmailDelivery.query.filter_by(
            business_account_id=business_account.id,
            status='sending'
        ).count()
        
        print(f"Total Email Deliveries: {total_emails}")
        print(f"  - Sent: {sent_emails}")
        print(f"  - Pending: {pending_emails}")
        print(f"  - Failed: {failed_emails}")
        print(f"  - Sending: {sending_emails}")
        
        # Get email type breakdown
        invitation_emails = EmailDelivery.query.filter_by(
            business_account_id=business_account.id,
            email_type='participant_invitation'
        ).count()
        
        notification_emails = EmailDelivery.query.filter_by(
            business_account_id=business_account.id,
            email_type='campaign_notification'
        ).count()
        
        print(f"\nEmail Type Breakdown:")
        print(f"  - Participant Invitations: {invitation_emails}")
        print(f"  - Campaign Notifications: {notification_emails}")
        
        # Get recent email deliveries
        recent_deliveries = EmailDelivery.query.filter_by(
            business_account_id=business_account.id
        ).order_by(EmailDelivery.created_at.desc()).limit(5).all()
        
        print(f"\nRecent Email Deliveries ({len(recent_deliveries)}):")
        for delivery in recent_deliveries:
            print(f"  - {delivery.email_type} to {delivery.recipient_email}")
            print(f"    Status: {delivery.status}, Created: {delivery.created_at}")
            if delivery.last_error:
                print(f"    Last Error: {delivery.last_error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error getting email statistics: {e}")
        return False

def test_admin_participant_management():
    """Test admin participant management functionality"""
    print("\n=== ADMIN PARTICIPANT MANAGEMENT TEST ===")
    
    try:
        business_account, admin_user = get_admin_credentials()
        if not business_account or not admin_user:
            return False
        
        # Get participants for the business account
        participants = Participant.query.filter_by(
            business_account_id=business_account.id
        ).all()
        
        print(f"Total Participants: {len(participants)}")
        
        # Status breakdown
        status_counts = {}
        for participant in participants:
            status = participant.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("Participant Status Breakdown:")
        for status, count in status_counts.items():
            print(f"  - {status}: {count}")
        
        # Source breakdown
        source_counts = {}
        for participant in participants:
            source = participant.source or 'unknown'
            source_counts[source] = source_counts.get(source, 0) + 1
        
        print("Participant Source Breakdown:")
        for source, count in source_counts.items():
            print(f"  - {source}: {count}")
        
        # Campaign associations
        total_associations = CampaignParticipant.query.filter_by(
            business_account_id=business_account.id
        ).count()
        
        print(f"Total Campaign Associations: {total_associations}")
        
        # Get participants with campaign associations
        participants_with_campaigns = []
        for participant in participants[:5]:  # Show first 5
            campaigns = CampaignParticipant.query.filter_by(
                participant_id=participant.id,
                business_account_id=business_account.id
            ).all()
            
            if campaigns:
                participants_with_campaigns.append({
                    'participant': participant,
                    'campaigns': len(campaigns)
                })
        
        print(f"\nSample Participants with Campaign Associations:")
        for item in participants_with_campaigns:
            participant = item['participant']
            print(f"  - {participant.name} ({participant.email})")
            print(f"    Status: {participant.status}, Campaigns: {item['campaigns']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing participant management: {e}")
        return False

def test_admin_permissions():
    """Test admin permission system"""
    print("\n=== ADMIN PERMISSIONS TEST ===")
    
    try:
        business_account, admin_user = get_admin_credentials()
        if not business_account or not admin_user:
            return False
        
        print(f"Admin User: {admin_user.email}")
        print(f"Role: {admin_user.role}")
        print(f"Active: {admin_user.is_active}")
        print(f"Email Verified: {admin_user.email_verified}")
        
        # Check if user has permissions based on role
        is_admin = admin_user.role == 'admin'
        print(f"Is Admin: {is_admin}")
        
        # Check specific permissions (based on role)
        required_permissions = ['manage_participants', 'manage_campaigns', 'admin']
        for permission in required_permissions:
            has_permission = is_admin  # Admin role has all permissions
            status = "✅" if has_permission else "❌"
            print(f"  {status} {permission}: {has_permission}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing admin permissions: {e}")
        return False

def main():
    """Run all admin interface tests"""
    print("Starting comprehensive admin interface tests...\n")
    
    with app.app_context():
        # Test 1: Admin credentials
        business_account, admin_user = get_admin_credentials()
        credentials_ok = business_account is not None and admin_user is not None
        
        # Test 2: Campaign statistics
        campaign_stats_ok = test_admin_campaign_statistics()
        
        # Test 3: Email statistics
        email_stats_ok = test_admin_email_statistics()
        
        # Test 4: Participant management
        participant_mgmt_ok = test_admin_participant_management()
        
        # Test 5: Admin permissions
        permissions_ok = test_admin_permissions()
        
        # Summary
        print("\n=== ADMIN INTERFACE TEST SUMMARY ===")
        print(f"✅ Admin credentials available: {credentials_ok}")
        print(f"✅ Campaign statistics working: {campaign_stats_ok}")
        print(f"✅ Email statistics working: {email_stats_ok}")
        print(f"✅ Participant management working: {participant_mgmt_ok}")
        print(f"✅ Admin permissions working: {permissions_ok}")
        
        # Overall status
        all_tests_passed = all([
            credentials_ok,
            campaign_stats_ok,
            email_stats_ok,
            participant_mgmt_ok,
            permissions_ok
        ])
        
        if all_tests_passed:
            print("\n🎉 All admin interface tests passed! Ready for invitation testing.")
        else:
            print("\n❌ Some admin interface tests failed. Check the details above.")
        
        return all_tests_passed

if __name__ == '__main__':
    main()