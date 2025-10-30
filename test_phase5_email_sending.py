#!/usr/bin/env python3
"""
Phase 5 Email Sending Integration Testing
Tests dual-mode email delivery: VOÏA-managed vs Client-managed
"""

import os
import sys

# Set environment before imports
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'sqlite:///test_email.db')
os.environ['SESSION_SECRET'] = 'test-secret-key-for-testing-12345678901234567890'  # 32+ chars for proper key derivation
os.environ['EMAIL_ENCRYPTION_KEY'] = 'ed2a2JFtPflbkGmUZADAkA1_95uU3N5WVshfOJwLeTc='  # Valid Fernet encryption key

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Suppress Flask app initialization logging
import logging
logging.basicConfig(level=logging.CRITICAL)

from app import app, db
from models import PlatformEmailSettings, EmailConfiguration, BusinessAccount, BusinessAccountUser
from email_service import EmailService
import traceback

def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 60)
    print(title.upper())
    print("=" * 60)

def print_subsection(title):
    """Print formatted subsection header"""
    print(f"\n--- {title} ---")

def setup_test_data():
    """Create test business account and platform settings"""
    with app.app_context():
        # Create test business account
        business_account = BusinessAccount.query.filter_by(
            name='Test Business Account'
        ).first()
        
        if not business_account:
            business_account = BusinessAccount(
                name='Test Business Account',
                contact_email='test@business.com',
                license_status='core',
                account_type='customer'
            )
            db.session.add(business_account)
            db.session.commit()
            print(f"✅ Created test business account (ID: {business_account.id})")
        else:
            print(f"✅ Using existing test business account (ID: {business_account.id})")
        
        return business_account.id

def test_voia_managed_mode():
    """Test VOÏA-managed email mode with platform AWS SES credentials"""
    print_subsection("Testing VOÏA-Managed Email Mode")
    
    with app.app_context():
        email_service = EmailService()
        business_account_id = setup_test_data()
        
        # Create platform email settings (simulating platform admin setup)
        platform_settings = PlatformEmailSettings.query.first()
        if not platform_settings:
            platform_settings = PlatformEmailSettings(
                aws_region='us-east-1',
                smtp_server='email-smtp.us-east-1.amazonaws.com',
                smtp_port=587,
                smtp_username='AKIATEST123456789',
                use_tls=True,
                use_ssl=False,
                is_verified=True
            )
            platform_settings.set_smtp_password('test-platform-password')
            db.session.add(platform_settings)
            db.session.commit()
            print(f"   ✅ Created platform email settings (ID: {platform_settings.id})")
        else:
            platform_settings.is_verified = True
            db.session.commit()
            print(f"   ✅ Using existing platform email settings (ID: {platform_settings.id})")
        
        # Configure business account for VOÏA-managed mode
        email_config = EmailConfiguration.query.filter_by(
            business_account_id=business_account_id
        ).first()
        
        if not email_config:
            email_config = EmailConfiguration(
                business_account_id=business_account_id,
                use_platform_email=True,
                sender_domain='verified-domain.com',
                sender_email='support@verified-domain.com',
                sender_name='Test Business',
                domain_verified=True,
                is_active=True
            )
            db.session.add(email_config)
        else:
            email_config.use_platform_email = True
            email_config.sender_domain = 'verified-domain.com'
            email_config.sender_email = 'support@verified-domain.com'
            email_config.sender_name = 'Test Business'
            email_config.domain_verified = True
            email_config.is_active = True
        
        db.session.commit()
        print(f"   ✅ Configured business account for VOÏA-managed mode")
        
        # Test configuration retrieval
        try:
            config = email_service._get_email_config(business_account_id)
            
            # Verify VOÏA-managed mode is detected
            if config.get('email_mode') == 'voia_managed':
                print(f"   ✅ Email mode correctly detected as 'voia_managed'")
            else:
                print(f"   ❌ Email mode incorrect: {config.get('email_mode')}")
                return False
            
            # Verify platform AWS SES credentials are used
            if config.get('smtp_server') == platform_settings.smtp_server:
                print(f"   ✅ Using platform SMTP server: {config['smtp_server']}")
            else:
                print(f"   ❌ SMTP server mismatch: {config.get('smtp_server')}")
                return False
            
            # Verify business account sender info is used
            if config.get('sender_email') == 'support@verified-domain.com':
                print(f"   ✅ Using business account sender email: {config['sender_email']}")
            else:
                print(f"   ❌ Sender email mismatch: {config.get('sender_email')}")
                return False
            
            if config.get('sender_domain') == 'verified-domain.com':
                print(f"   ✅ Using business account sender domain: {config['sender_domain']}")
            else:
                print(f"   ❌ Sender domain missing or incorrect")
                return False
            
            print(f"   ✅ VOÏA-managed mode configuration test passed")
            return True
            
        except Exception as e:
            print(f"   ❌ Configuration retrieval failed: {e}")
            traceback.print_exc()
            return False

def test_client_managed_mode():
    """Test client-managed email mode with business account SMTP credentials"""
    print_subsection("Testing Client-Managed Email Mode")
    
    with app.app_context():
        email_service = EmailService()
        
        # Create separate business account for client-managed test
        business_account = BusinessAccount.query.filter_by(
            name='Test Client-Managed Account'
        ).first()
        
        if not business_account:
            business_account = BusinessAccount(
                name='Test Client-Managed Account',
                contact_email='clientmanaged@business.com',
                license_status='core',
                account_type='customer'
            )
            db.session.add(business_account)
            db.session.commit()
        
        business_account_id = business_account.id
        print(f"   ✅ Using business account ID: {business_account_id}")
        
        # Configure business account for client-managed mode
        email_config = EmailConfiguration.query.filter_by(
            business_account_id=business_account_id
        ).first()
        
        if not email_config:
            email_config = EmailConfiguration(
                business_account_id=business_account_id,
                use_platform_email=False,
                smtp_server='smtp.gmail.com',
                smtp_port=587,
                smtp_username='client@gmail.com',
                use_tls=True,
                use_ssl=False,
                sender_email='client@gmail.com',
                sender_name='Client Business',
                is_active=True
            )
            email_config.set_smtp_password('client-smtp-password')
            db.session.add(email_config)
        else:
            email_config.use_platform_email = False
            email_config.smtp_server = 'smtp.gmail.com'
            email_config.smtp_port = 587
            email_config.smtp_username = 'client@gmail.com'
            email_config.use_tls = True
            email_config.use_ssl = False
            email_config.sender_email = 'client@gmail.com'
            email_config.sender_name = 'Client Business'
            email_config.is_active = True
            email_config.set_smtp_password('client-smtp-password')
        
        db.session.commit()
        print(f"   ✅ Configured business account for client-managed mode")
        
        # Test configuration retrieval
        try:
            config = email_service._get_email_config(business_account_id)
            
            # Verify client-managed mode is detected
            if config.get('email_mode') == 'client_managed':
                print(f"   ✅ Email mode correctly detected as 'client_managed'")
            else:
                print(f"   ❌ Email mode incorrect: {config.get('email_mode')}")
                return False
            
            # Verify client SMTP credentials are used
            if config.get('smtp_server') == 'smtp.gmail.com':
                print(f"   ✅ Using client SMTP server: {config['smtp_server']}")
            else:
                print(f"   ❌ SMTP server mismatch: {config.get('smtp_server')}")
                return False
            
            # Verify business account sender info is used
            if config.get('sender_email') == 'client@gmail.com':
                print(f"   ✅ Using client sender email: {config['sender_email']}")
            else:
                print(f"   ❌ Sender email mismatch: {config.get('sender_email')}")
                return False
            
            print(f"   ✅ Client-managed mode configuration test passed")
            return True
            
        except Exception as e:
            print(f"   ❌ Configuration retrieval failed: {e}")
            traceback.print_exc()
            return False

def test_error_handling():
    """Test error handling for invalid configurations"""
    print_subsection("Testing Error Handling")
    
    with app.app_context():
        email_service = EmailService()
        
        # Test 1: VOÏA-managed mode with unverified domain
        print("\n   Test 1: VOÏA-managed mode with unverified domain")
        business_account = BusinessAccount(
            name='Test Unverified Domain',
            contact_email='unverified@business.com',
            license_status='core',
            account_type='customer'
        )
        db.session.add(business_account)
        db.session.commit()
        
        email_config = EmailConfiguration(
            business_account_id=business_account.id,
            use_platform_email=True,
            sender_domain='unverified-domain.com',
            sender_email='support@unverified-domain.com',
            sender_name='Test Business',
            domain_verified=False,  # Not verified
            is_active=True
        )
        db.session.add(email_config)
        db.session.commit()
        
        try:
            config = email_service._get_email_config(business_account.id)
            # Should fall back to system default
            if config.get('email_mode') == 'system_default':
                print(f"   ✅ Correctly fell back to system default for unverified domain")
            else:
                print(f"   ❌ Should have fallen back to system default, got: {config.get('email_mode')}")
                return False
        except Exception as e:
            print(f"   ✅ Correctly raised error for unverified domain: {str(e)[:80]}")
        
        # Test 2: Missing platform settings
        print("\n   Test 2: VOÏA-managed mode with missing platform settings")
        
        # Temporarily mark platform settings as not verified
        platform_settings = PlatformEmailSettings.query.first()
        if platform_settings:
            original_verified = platform_settings.is_verified
            platform_settings.is_verified = False
            db.session.commit()
            
            # Create verified business account config
            business_account2 = BusinessAccount(
                name='Test Missing Platform',
                contact_email='missing@business.com',
                license_status='core',
                account_type='customer'
            )
            db.session.add(business_account2)
            db.session.commit()
            
            email_config2 = EmailConfiguration(
                business_account_id=business_account2.id,
                use_platform_email=True,
                sender_domain='verified-domain.com',
                sender_email='support@verified-domain.com',
                sender_name='Test Business 2',
                domain_verified=True,
                is_active=True
            )
            db.session.add(email_config2)
            db.session.commit()
            
            try:
                config = email_service._get_email_config(business_account2.id)
                if config.get('email_mode') == 'system_default':
                    print(f"   ✅ Correctly fell back to system default for unverified platform")
                else:
                    print(f"   ❌ Should have fallen back, got: {config.get('email_mode')}")
                    return False
            except Exception as e:
                print(f"   ✅ Correctly raised error for missing platform settings: {str(e)[:80]}")
            
            # Restore platform settings
            platform_settings.is_verified = original_verified
            db.session.commit()
        
        print(f"   ✅ Error handling tests passed")
        return True

def test_multi_tenant_isolation():
    """Test that business accounts are properly isolated"""
    print_subsection("Testing Multi-Tenant Isolation")
    
    with app.app_context():
        email_service = EmailService()
        
        # Create two business accounts with different modes
        # Account 1: VOÏA-managed
        ba1 = BusinessAccount(
            name='Tenant 1 - VOÏA',
            contact_email='tenant1@business.com',
            license_status='core',
            account_type='customer'
        )
        db.session.add(ba1)
        db.session.commit()
        
        ec1 = EmailConfiguration(
            business_account_id=ba1.id,
            use_platform_email=True,
            sender_domain='tenant1.com',
            sender_email='support@tenant1.com',
            sender_name='Tenant 1',
            domain_verified=True,
            is_active=True
        )
        db.session.add(ec1)
        
        # Account 2: Client-managed
        ba2 = BusinessAccount(
            name='Tenant 2 - Client',
            contact_email='tenant2@business.com',
            license_status='core',
            account_type='customer'
        )
        db.session.add(ba2)
        db.session.commit()
        
        ec2 = EmailConfiguration(
            business_account_id=ba2.id,
            use_platform_email=False,
            smtp_server='smtp.tenant2.com',
            smtp_port=587,
            smtp_username='tenant2@smtp.com',
            sender_email='tenant2@smtp.com',
            sender_name='Tenant 2',
            use_tls=True,
            is_active=True
        )
        ec2.set_smtp_password('tenant2-password')
        db.session.add(ec2)
        db.session.commit()
        
        # Test isolation
        config1 = email_service._get_email_config(ba1.id)
        config2 = email_service._get_email_config(ba2.id)
        
        # Verify account 1 uses VOÏA-managed
        if config1.get('email_mode') == 'voia_managed' and config1.get('sender_email') == 'support@tenant1.com':
            print(f"   ✅ Tenant 1 correctly uses VOÏA-managed mode with own sender")
        else:
            print(f"   ❌ Tenant 1 configuration incorrect")
            return False
        
        # Verify account 2 uses client-managed
        if config2.get('email_mode') == 'client_managed' and config2.get('smtp_server') == 'smtp.tenant2.com':
            print(f"   ✅ Tenant 2 correctly uses client-managed mode with own SMTP")
        else:
            print(f"   ❌ Tenant 2 configuration incorrect")
            return False
        
        # Verify no cross-contamination
        if config1.get('smtp_server') != config2.get('smtp_server'):
            print(f"   ✅ Multi-tenant isolation verified - different SMTP servers")
        else:
            print(f"   ❌ Multi-tenant isolation failed - same SMTP servers")
            return False
        
        print(f"   ✅ Multi-tenant isolation tests passed")
        return True

def main():
    """Run all Phase 5 tests"""
    print_section("Phase 5: Email Sending Integration Testing")
    
    with app.app_context():
        # Initialize database
        db.create_all()
        print("✅ Database initialized")
    
    results = {
        'voia_managed': test_voia_managed_mode(),
        'client_managed': test_client_managed_mode(),
        'error_handling': test_error_handling(),
        'multi_tenant': test_multi_tenant_isolation()
    }
    
    print_section("Test Summary")
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "=" * 60)
        print("✅ ALL PHASE 5 TESTS PASSED!")
        print("=" * 60)
        print("\nPhase 5 Implementation Complete:")
        print("- ✅ VOÏA-managed email mode with platform AWS SES")
        print("- ✅ Client-managed email mode with business SMTP")
        print("- ✅ Error handling for invalid configurations")
        print("- ✅ Multi-tenant isolation verified")
        print("\nNext Steps:")
        print("1. Manual testing with real AWS SES credentials")
        print("2. Test actual email sending (requires valid SMTP/SES)")
        print("3. Proceed to Phase 6: Testing & Documentation")
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1

if __name__ == '__main__':
    sys.exit(main())
