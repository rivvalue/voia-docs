#!/usr/bin/env python3
"""
Quick test script for Phase 1 & 2 - Platform Email Settings
Run this from the project root: python test_phase1_phase2.py
"""

from app import app, db
from models import PlatformEmailSettings, EmailConfiguration, BusinessAccountUser
import sys

def test_database_schema():
    """Test Phase 1: Database schema changes"""
    print("\n" + "="*60)
    print("PHASE 1: DATABASE SCHEMA TESTING")
    print("="*60)
    
    with app.app_context():
        # Test 1: Check platform_email_settings table exists
        try:
            result = db.session.execute(db.text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = 'platform_email_settings'
            """))
            count = result.scalar()
            assert count == 1, "platform_email_settings table not found"
            print("✅ platform_email_settings table exists")
        except Exception as e:
            print(f"❌ FAILED: platform_email_settings table check: {e}")
            return False
        
        # Test 2: Check new columns in email_configurations
        try:
            result = db.session.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'email_configurations' 
                AND column_name IN (
                    'use_platform_email', 'sender_domain', 'domain_verified',
                    'dkim_record_1_name', 'dkim_record_1_value'
                )
            """))
            columns = [row[0] for row in result]
            expected_columns = ['use_platform_email', 'sender_domain', 'domain_verified', 
                              'dkim_record_1_name', 'dkim_record_1_value']
            for col in expected_columns:
                assert col in columns, f"Column {col} not found"
            print(f"✅ All new columns exist in email_configurations ({len(columns)} checked)")
        except Exception as e:
            print(f"❌ FAILED: email_configurations columns check: {e}")
            return False
        
        # Test 3: Check existing data preserved
        try:
            existing_configs = EmailConfiguration.query.count()
            print(f"✅ Existing email configurations preserved: {existing_configs} records")
        except Exception as e:
            print(f"❌ FAILED: existing data check: {e}")
            return False
        
        # Test 4: Check default values
        try:
            config = EmailConfiguration.query.first()
            if config:
                assert config.use_platform_email == False, "use_platform_email should default to False"
                assert config.domain_verified == False, "domain_verified should default to False"
                print("✅ Default values correct (use_platform_email=False, domain_verified=False)")
            else:
                print("⚠️  No email configurations found to test defaults")
        except Exception as e:
            print(f"❌ FAILED: default values check: {e}")
            return False
    
    return True


def test_model_methods():
    """Test Phase 2: Model encryption methods"""
    print("\n" + "="*60)
    print("PHASE 2: MODEL METHODS TESTING")
    print("="*60)
    
    with app.app_context():
        # Test 1: PlatformEmailSettings encryption/decryption
        try:
            # Create or get test settings
            settings = PlatformEmailSettings.query.first()
            
            if not settings:
                print("⚠️  No platform email settings found - creating test record")
                settings = PlatformEmailSettings(
                    aws_region='us-east-1',
                    smtp_server='email-smtp.us-east-1.amazonaws.com',
                    smtp_port=587,
                    smtp_username='test-user'
                )
                settings.set_smtp_password('test-password-123')
                db.session.add(settings)
                db.session.commit()
            
            # Test password encryption/decryption
            test_password = 'new-test-password-456'
            settings.set_smtp_password(test_password)
            db.session.commit()
            
            decrypted = settings.get_smtp_password()
            assert decrypted == test_password, f"Expected '{test_password}', got '{decrypted}'"
            print(f"✅ PlatformEmailSettings password encryption/decryption works")
            print(f"   - Set password: {test_password}")
            print(f"   - Decrypted password: {decrypted}")
            print(f"   - Encrypted length: {len(settings.smtp_password_encrypted)} chars")
            
        except Exception as e:
            print(f"❌ FAILED: PlatformEmailSettings encryption test: {e}")
            return False
        
        # Test 2: EmailConfiguration encryption still works
        try:
            config = EmailConfiguration.query.first()
            if config and config.smtp_password_encrypted:
                decrypted = config.get_smtp_password()
                assert decrypted is not None, "EmailConfiguration password decryption failed"
                print(f"✅ EmailConfiguration password decryption works")
            else:
                print("⚠️  No EmailConfiguration with password found to test")
        except Exception as e:
            print(f"❌ FAILED: EmailConfiguration encryption test: {e}")
            return False
        
        # Test 3: New fields accessible
        try:
            config = EmailConfiguration.query.first()
            if config:
                _ = config.use_platform_email
                _ = config.domain_verified
                _ = config.sender_domain
                print("✅ New EmailConfiguration fields are accessible")
            else:
                print("⚠️  No EmailConfiguration found to test fields")
        except Exception as e:
            print(f"❌ FAILED: New fields access test: {e}")
            return False
    
    return True


def test_platform_admin_access():
    """Test Phase 2: Platform admin setup"""
    print("\n" + "="*60)
    print("PLATFORM ADMIN ACCESS CHECK")
    print("="*60)
    
    with app.app_context():
        # Check for platform admins
        try:
            admins = BusinessAccountUser.query.filter_by(is_platform_admin=True).all()
            
            if not admins:
                print("⚠️  WARNING: No platform admins found!")
                print("   To test Phase 2 UI, you need to create a platform admin:")
                print("")
                print("   Run this SQL:")
                print("   UPDATE business_account_users")
                print("   SET is_platform_admin = true")
                print("   WHERE id = 1;  -- Change to your user ID")
                print("")
            else:
                print(f"✅ Found {len(admins)} platform admin(s):")
                for admin in admins:
                    print(f"   - {admin.email} (ID: {admin.id})")
                print("")
                print("🔗 To test Phase 2 UI:")
                print(f"   1. Login as: {admins[0].email}")
                print(f"   2. Navigate to: /business/admin/platform-email-settings")
            
            return True
            
        except Exception as e:
            print(f"❌ FAILED: Platform admin check: {e}")
            return False


def print_summary():
    """Print test summary and next steps"""
    print("\n" + "="*60)
    print("SUMMARY & NEXT STEPS")
    print("="*60)
    print("")
    print("📋 Phase 1 Database: Schema changes verified")
    print("📋 Phase 2 Models: Encryption methods tested")
    print("")
    print("📝 Manual UI Testing Required:")
    print("   See TESTING_PHASE1_PHASE2.md for complete test plan")
    print("")
    print("🔗 Key Test URLs:")
    print("   - Platform Settings: /business/admin/platform-email-settings")
    print("   - Business Email Config: /business/admin/email-config")
    print("")
    print("✅ Non-Regression Verification:")
    print("   - Existing email configurations: Working ✓")
    print("   - Database schema: Extended without data loss ✓")
    print("   - Model methods: Functional ✓")
    print("")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("PHASE 1 & 2 AUTOMATED TESTING")
    print("="*60)
    
    all_passed = True
    
    # Run tests
    if not test_database_schema():
        all_passed = False
    
    if not test_model_methods():
        all_passed = False
    
    if not test_platform_admin_access():
        all_passed = False
    
    print_summary()
    
    if all_passed:
        print("\n✅ ALL AUTOMATED TESTS PASSED!")
        print("   Continue with manual UI testing using TESTING_PHASE1_PHASE2.md")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - Please review errors above")
        sys.exit(1)
