"""
Database Migration: Add Platform Email Support (Phase 1)

This migration adds:
1. PlatformEmailSettings table (new)
2. Domain verification fields to EmailConfiguration (new columns)

Run this migration after deploying new models.py changes.

Usage:
    python migrations/add_platform_email_support.py
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import EmailConfiguration, PlatformEmailSettings


def run_migration():
    """Run the migration to add platform email support"""
    
    print("=" * 60)
    print("Platform Email Support Migration")
    print("=" * 60)
    print()
    
    with app.app_context():
        print("Step 1: Adding new columns to email_configurations table...")
        try:
            # Use raw SQL to add columns - db.create_all() doesn't alter existing tables
            sql_statements = [
                # Platform email mode flag
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS use_platform_email BOOLEAN NOT NULL DEFAULT FALSE;",
                
                # Domain verification fields
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS sender_domain VARCHAR(255);",
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS domain_verified BOOLEAN NOT NULL DEFAULT FALSE;",
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS domain_verification_status VARCHAR(50);",
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS domain_verified_at TIMESTAMP;",
                
                # DKIM records for DNS configuration
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS dkim_record_1_name VARCHAR(500);",
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS dkim_record_1_value VARCHAR(500);",
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS dkim_record_2_name VARCHAR(500);",
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS dkim_record_2_value VARCHAR(500);",
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS dkim_record_3_name VARCHAR(500);",
                "ALTER TABLE email_configurations ADD COLUMN IF NOT EXISTS dkim_record_3_value VARCHAR(500);"
            ]
            
            for sql in sql_statements:
                db.session.execute(db.text(sql))
            
            db.session.commit()
            print("✅ Email configurations table updated successfully")
        except Exception as e:
            print(f"❌ Error updating email_configurations: {e}")
            db.session.rollback()
            return False
        
        print()
        print("Step 2: Creating platform_email_settings table...")
        try:
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS platform_email_settings (
                    id SERIAL PRIMARY KEY,
                    aws_region VARCHAR(50) NOT NULL,
                    smtp_server VARCHAR(255) NOT NULL,
                    smtp_port INTEGER NOT NULL DEFAULT 587,
                    smtp_username VARCHAR(255) NOT NULL,
                    smtp_password_encrypted TEXT NOT NULL,
                    use_tls BOOLEAN NOT NULL DEFAULT TRUE,
                    use_ssl BOOLEAN NOT NULL DEFAULT FALSE,
                    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    last_test_at TIMESTAMP,
                    last_test_result TEXT,
                    configured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    configured_by_user_id INTEGER REFERENCES business_account_users(id),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
            db.session.execute(db.text(create_table_sql))
            db.session.commit()
            print("✅ Platform email settings table created successfully")
        except Exception as e:
            print(f"❌ Error creating platform_email_settings: {e}")
            db.session.rollback()
            return False
        
        print()
        print("Step 3: Verifying migration...")
        try:
            # Check PlatformEmailSettings table exists
            platform_settings = PlatformEmailSettings.query.all()
            print(f"✅ PlatformEmailSettings table accessible ({len(platform_settings)} records)")
            
            # Check new columns on EmailConfiguration
            test_config = EmailConfiguration.query.first()
            if test_config:
                assert hasattr(test_config, 'use_platform_email'), "Missing use_platform_email column"
                assert hasattr(test_config, 'sender_domain'), "Missing sender_domain column"
                assert hasattr(test_config, 'domain_verified'), "Missing domain_verified column"
                assert hasattr(test_config, 'dkim_record_1_name'), "Missing dkim_record_1_name column"
                print("✅ All new columns verified on EmailConfiguration")
            else:
                print("ℹ️  No EmailConfiguration records to verify (empty table)")
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False
        
        print()
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Restart the application")
        print("2. Platform admin can now configure VOÏA AWS SES credentials")
        print("3. Business accounts can choose between platform-managed and client-managed email")
        print()
        
        return True


if __name__ == "__main__":
    print()
    print("⚠️  WARNING: This migration will modify your database schema")
    print("   Make sure you have a database backup before proceeding.")
    print()
    
    response = input("Continue with migration? (yes/no): ").strip().lower()
    
    if response == 'yes':
        success = run_migration()
        sys.exit(0 if success else 1)
    else:
        print("Migration cancelled.")
        sys.exit(1)
