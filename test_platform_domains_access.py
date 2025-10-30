#!/usr/bin/env python3
"""
Test script to diagnose platform_email_domains page loading issue
"""

import sys
from app import app, db
from models import BusinessAccount, BusinessAccountUser, EmailConfiguration

def test_platform_domains_route():
    """Test the platform_email_domains route data loading"""
    
    with app.app_context():
        print("=" * 60)
        print("Testing Platform Email Domains Route")
        print("=" * 60)
        
        # Test 1: Check for platform admin users
        print("\n1. Checking for platform admin users:")
        platform_admins = BusinessAccountUser.query.filter_by(is_platform_admin=True).all()
        print(f"   Found {len(platform_admins)} platform admin(s)")
        for admin in platform_admins:
            print(f"   - {admin.email} (Account: {admin.business_account.name if admin.business_account else 'None'})")
        
        # Test 2: Query EmailConfiguration (domains)
        print("\n2. Querying email configurations (domains):")
        try:
            domains = EmailConfiguration.query.filter_by(use_platform_email=True).all()
            print(f"   ✓ Found {len(domains)} domain(s) using platform email")
            for domain in domains:
                print(f"     - Domain: {domain.sender_domain}, Account: {domain.business_account.name if domain.business_account else 'None'}, Verified: {domain.domain_verified}")
        except Exception as e:
            print(f"   ✗ ERROR querying domains: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 3: Query BusinessAccount with filter and order_by
        print("\n3. Querying business accounts (for dropdown):")
        try:
            # This is the exact query from the route
            business_accounts = BusinessAccount.query.filter_by(status='active').order_by(BusinessAccount.name).all()
            print(f"   ✓ Found {len(business_accounts)} active business account(s)")
            for account in business_accounts[:5]:  # Show first 5
                print(f"     - ID: {account.id}, Name: {account.name}, Type: {account.account_type}")
            if len(business_accounts) > 5:
                print(f"     ... and {len(business_accounts) - 5} more")
        except Exception as e:
            print(f"   ✗ ERROR querying business accounts: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 4: Check for potential template issues
        print("\n4. Checking template data requirements:")
        try:
            # Simulate what the route does
            current_user = platform_admins[0] if platform_admins else None
            
            if current_user:
                print(f"   ✓ Current user: {current_user.email}")
                print(f"   ✓ Has business_account: {current_user.business_account is not None}")
                print(f"   ✓ Is platform admin: {current_user.is_platform_admin}")
            else:
                print("   ✗ No platform admin user found for testing")
            
            # Check if domains have business_account relationship
            if domains:
                for i, domain in enumerate(domains[:3]):
                    print(f"   Domain {i+1}:")
                    print(f"     - business_account_id: {domain.business_account_id}")
                    print(f"     - business_account: {domain.business_account}")
                    print(f"     - business_account.name: {domain.business_account.name if domain.business_account else 'N/A'}")
        except Exception as e:
            print(f"   ✗ ERROR checking template data: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 5: Simulate template rendering context
        print("\n5. Simulating template rendering context:")
        try:
            context = {
                'domains': domains,
                'business_accounts': business_accounts,
                'current_user': current_user
            }
            print(f"   ✓ Template context created successfully")
            print(f"     - domains: {len(context['domains'])} items")
            print(f"     - business_accounts: {len(context['business_accounts'])} items")
            print(f"     - current_user: {context['current_user'].email if context['current_user'] else 'None'}")
        except Exception as e:
            print(f"   ✗ ERROR creating template context: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("Test Complete")
        print("=" * 60)
        
        # Return status
        if len(platform_admins) == 0:
            print("\n⚠ WARNING: No platform admin users found")
            print("  To fix: UPDATE business_account_users SET is_platform_admin = true WHERE email = 'your_email';")
        else:
            print("\n✓ Route data loading should work correctly")

if __name__ == "__main__":
    test_platform_domains_route()
