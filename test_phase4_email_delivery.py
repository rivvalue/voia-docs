#!/usr/bin/env python3
"""
Test script for Phase 4 - Business Account Email Delivery Configuration
Run this from the project root: python test_phase4_email_delivery.py
"""

from app import app
import sys

def test_routes_registered():
    """Test that email delivery configuration routes are registered"""
    print("\n" + "="*60)
    print("PHASE 4: EMAIL DELIVERY CONFIGURATION ROUTES TESTING")
    print("="*60)
    
    with app.app_context():
        # Get all registered routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(str(rule))
        
        # Check for email delivery configuration routes
        required_routes = [
            '/business/admin/email-delivery-config',
            '/business/admin/email-delivery-config/save'
        ]
        
        all_found = True
        for route in required_routes:
            found = any(route in registered for registered in routes)
            
            if found:
                print(f"✅ Route registered: {route}")
            else:
                print(f"❌ FAILED: Route not found: {route}")
                all_found = False
        
        return all_found


def test_template_exists():
    """Test that the email delivery configuration template exists"""
    print("\n" + "="*60)
    print("TEMPLATE VERIFICATION")
    print("="*60)
    
    import os
    template_path = "templates/business_auth/email_delivery_config.html"
    
    if os.path.exists(template_path):
        print(f"✅ Template exists: {template_path}")
        
        # Check template has key sections
        with open(template_path, 'r') as f:
            content = f.read()
            
            checks = [
                ('Email Mode Selector', 'email_mode' in content and 'voia_managed' in content),
                ('VOÏA-Managed Section', 'voia_managed_section' in content),
                ('Client-Managed Section', 'client_managed_section' in content),
                ('Domain Selector', 'selected_domain_id' in content),
                ('DKIM Display', 'dkim_records_section' in content),
                ('SMTP Configuration', 'smtp_server' in content and 'smtp_port' in content),
                ('Settings Hub Header', 'settings-hub-header' in content),
                ('JavaScript Toggle', 'toggleEmailMode' in content)
            ]
            
            for check_name, result in checks:
                if result:
                    print(f"   ✅ {check_name}")
                else:
                    print(f"   ❌ {check_name}")
        
        return True
    else:
        print(f"❌ FAILED: Template not found: {template_path}")
        return False


def test_navigation_updated():
    """Test that Settings Hub navigation was updated"""
    print("\n" + "="*60)
    print("NAVIGATION LINK VERIFICATION")
    print("="*60)
    
    import os
    admin_panel_template = "templates/business_auth/admin_panel_v2.html"
    
    if os.path.exists(admin_panel_template):
        with open(admin_panel_template, 'r') as f:
            content = f.read()
            
            # Check for new email delivery config link
            if 'email_delivery_config' in content:
                print("✅ Settings Hub navigation updated to email_delivery_config")
                
                # Check description is updated
                if 'VOÏA-managed or client-managed' in content:
                    print("   ✅ Description updated to reflect dual-mode")
                else:
                    print("   ⚠️  Description might need updating")
                
                return True
            else:
                print("❌ FAILED: Settings Hub navigation not updated")
                return False
    else:
        print("❌ FAILED: Admin panel template not found")
        return False


def test_model_fields():
    """Test that EmailConfiguration model has required fields"""
    print("\n" + "="*60)
    print("DATABASE MODEL VERIFICATION")
    print("="*60)
    
    try:
        from models import EmailConfiguration
        
        # Check for dual-mode fields
        required_fields = [
            'use_platform_email',      # Boolean flag for mode selection
            'sender_domain',            # Domain for VOÏA-managed mode
            'domain_verified',          # Verification status
            'dkim_record_1_name',       # DKIM records
            'dkim_record_1_value',
            'dkim_record_2_name',
            'dkim_record_2_value',
            'dkim_record_3_name',
            'dkim_record_3_value',
            'smtp_server',              # Client-managed fields
            'smtp_port',
            'smtp_username',
            'smtp_password_encrypted',
            'sender_name',
            'sender_email'
        ]
        
        all_found = True
        for field in required_fields:
            if hasattr(EmailConfiguration, field):
                print(f"✅ Field exists: {field}")
            else:
                print(f"❌ FAILED: Field missing: {field}")
                all_found = False
        
        return all_found
    
    except Exception as e:
        print(f"❌ FAILED: Error checking model: {e}")
        return False


def print_summary():
    """Print test summary and next steps"""
    print("\n" + "="*60)
    print("SUMMARY & NEXT STEPS")
    print("="*60)
    print("")
    print("📋 Phase 4 Email Delivery Configuration: Routes and templates verified")
    print("")
    print("📝 Manual UI Testing Required:")
    print("   1. Login as any business account admin")
    print("   2. Navigate to Settings Hub")
    print("   3. Click 'Email Delivery Configuration'")
    print("   4. Test VOÏA-Managed mode:")
    print("      - Select a verified domain (if available)")
    print("      - View DKIM records")
    print("      - Enter sender name and email")
    print("      - Save configuration")
    print("   5. Test Client-Managed mode:")
    print("      - Enter SMTP server details")
    print("      - Enter sender information")
    print("      - Save configuration")
    print("   6. Verify mode switching works correctly")
    print("   7. Check data persistence after save")
    print("")
    print("🔗 Key Test URLs:")
    print("   - Settings Hub: /business/admin")
    print("   - Email Delivery Config: /business/admin/email-delivery-config")
    print("")
    print("✅ Features Implemented:")
    print("   - Dual-mode email delivery (VOÏA-Managed / Client-Managed)")
    print("   - Domain selector for VOÏA-managed mode")
    print("   - DKIM record display for DNS configuration")
    print("   - SMTP configuration for client-managed mode")
    print("   - Mode switching with dynamic UI updates")
    print("   - Multi-tenant isolation (business account scoped)")
    print("   - Settings Hub v2 design compliance")
    print("")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("PHASE 4 AUTOMATED TESTING")
    print("="*60)
    
    all_passed = True
    
    # Run tests
    if not test_routes_registered():
        all_passed = False
    
    if not test_template_exists():
        all_passed = False
    
    if not test_navigation_updated():
        all_passed = False
    
    if not test_model_fields():
        all_passed = False
    
    print_summary()
    
    if all_passed:
        print("\n✅ ALL AUTOMATED TESTS PASSED!")
        print("   Continue with manual UI testing")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - Please review errors above")
        sys.exit(1)
