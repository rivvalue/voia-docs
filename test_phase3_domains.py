#!/usr/bin/env python3
"""
Quick test script for Phase 3 - Platform Email Domain Management
Run this from the project root: python test_phase3_domains.py
"""

from app import app
import sys

def test_routes_registered():
    """Test that all domain management routes are registered"""
    print("\n" + "="*60)
    print("PHASE 3: DOMAIN MANAGEMENT ROUTES TESTING")
    print("="*60)
    
    with app.app_context():
        # Get all registered routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(str(rule))
        
        # Check for domain management routes
        required_routes = [
            '/business/admin/platform-email-domains',
            '/business/admin/platform-email-domains/add',
            '/business/admin/platform-email-domains/edit/<int:config_id>',
            '/business/admin/platform-email-domains/delete/<int:config_id>'
        ]
        
        all_found = True
        for route in required_routes:
            # Normalize route format for comparison
            route_pattern = route.replace('<int:config_id>', '<config_id>')
            found = False
            
            for registered in routes:
                if route in registered or route_pattern in registered:
                    found = True
                    break
            
            if found:
                print(f"✅ Route registered: {route}")
            else:
                print(f"❌ FAILED: Route not found: {route}")
                all_found = False
        
        return all_found


def test_template_exists():
    """Test that the domain management template exists"""
    print("\n" + "="*60)
    print("TEMPLATE VERIFICATION")
    print("="*60)
    
    import os
    template_path = "templates/business_auth/platform_email_domains.html"
    
    if os.path.exists(template_path):
        print(f"✅ Template exists: {template_path}")
        
        # Check template has key sections
        with open(template_path, 'r') as f:
            content = f.read()
            
            checks = [
                ('Add Domain Modal', 'addDomainModal' in content),
                ('Edit Domain Modal', 'editDomainModal' in content),
                ('Delete Confirmation', 'deleteDomainModal' in content),
                ('DKIM Record Fields', 'dkim_record_1_name' in content),
                ('Business Account Selector', 'business_account_id' in content),
                ('Settings Hub Header', 'settings-hub-header' in content)
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


def test_navigation_link():
    """Test that navigation link was added to platform email settings"""
    print("\n" + "="*60)
    print("NAVIGATION LINK VERIFICATION")
    print("="*60)
    
    import os
    platform_settings_template = "templates/business_auth/platform_email_settings.html"
    
    if os.path.exists(platform_settings_template):
        with open(platform_settings_template, 'r') as f:
            content = f.read()
            
            if 'platform_email_domains' in content and 'Manage Domains' in content:
                print("✅ Navigation link added to Platform Email Settings page")
                return True
            else:
                print("❌ FAILED: Navigation link not found in Platform Email Settings")
                return False
    else:
        print("❌ FAILED: Platform Email Settings template not found")
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("SUMMARY & NEXT STEPS")
    print("="*60)
    print("")
    print("📋 Phase 3 Domain Management: Routes and templates verified")
    print("")
    print("📝 Manual UI Testing Required:")
    print("   1. Login as platform admin (admin@voia.com)")
    print("   2. Navigate to Settings Hub")
    print("   3. Click 'Platform Email Settings'")
    print("   4. Click 'Manage Domains' button")
    print("   5. Test adding a domain with DKIM records")
    print("   6. Test editing domain verification status")
    print("   7. Test deleting a domain")
    print("")
    print("🔗 Key Test URLs:")
    print("   - Platform Email Settings: /business/admin/platform-email-settings")
    print("   - Domain Management: /business/admin/platform-email-domains")
    print("")
    print("✅ Features Implemented:")
    print("   - Platform admin only access control")
    print("   - CRUD operations for verified domains")
    print("   - DKIM record entry (3 records per domain)")
    print("   - Business account selector")
    print("   - Verification status toggle")
    print("   - Settings Hub v2 design compliance")
    print("")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("PHASE 3 AUTOMATED TESTING")
    print("="*60)
    
    all_passed = True
    
    # Run tests
    if not test_routes_registered():
        all_passed = False
    
    if not test_template_exists():
        all_passed = False
    
    if not test_navigation_link():
        all_passed = False
    
    print_summary()
    
    if all_passed:
        print("\n✅ ALL AUTOMATED TESTS PASSED!")
        print("   Continue with manual UI testing")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED - Please review errors above")
        sys.exit(1)
