#!/usr/bin/env python3
"""
Test script for license period calculation fix

This script tests the new anniversary-based license period logic
to ensure it works correctly across various scenarios.
"""

import sys
import os
from datetime import datetime, date, timedelta

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import BusinessAccount, Campaign

def test_license_period_calculations():
    """Test various license period calculation scenarios"""
    
    print("🧪 Testing License Period Calculations")
    print("=" * 50)
    
    with app.app_context():
        # Test Case 1: License activated March 15, 2025
        print("\n📅 Test Case 1: March 15, 2025 activation")
        account1 = BusinessAccount()
        account1.license_activated_at = datetime(2025, 3, 15)
        account1.license_expires_at = datetime(2026, 3, 15)
        
        period_start, period_end = account1.get_license_period(date(2025, 6, 1))
        print(f"   License Period: {period_start} to {period_end}")
        
        # Should return March 15, 2025 to March 15, 2026
        expected_start = date(2025, 3, 15)
        expected_end = date(2026, 3, 15)
        assert period_start == expected_start, f"Expected {expected_start}, got {period_start}"
        assert period_end == expected_end, f"Expected {expected_end}, got {period_end}"
        print("   ✅ PASS: Correct license period calculated")
        
        
        # Test Case 2: Leap year edge case (Feb 29, 2024 activation)
        print("\n📅 Test Case 2: Leap year Feb 29, 2024 activation")
        account2 = BusinessAccount()
        account2.license_activated_at = datetime(2024, 2, 29)  # Leap year
        account2.license_expires_at = datetime(2025, 2, 28)   # Non-leap year
        
        period_start, period_end = account2.get_license_period(date(2024, 6, 1))
        print(f"   License Period: {period_start} to {period_end}")
        
        expected_start = date(2024, 2, 29)
        expected_end = date(2025, 2, 28)
        assert period_start == expected_start, f"Expected {expected_start}, got {period_start}"
        assert period_end == expected_end, f"Expected {expected_end}, got {period_end}"
        print("   ✅ PASS: Leap year edge case handled correctly")
        
        
        # Test Case 3: Inferred activation from expiration (legacy account)
        print("\n📅 Test Case 3: Legacy account with only expiration date")
        account3 = BusinessAccount()
        account3.license_activated_at = None  # No activation date
        account3.license_expires_at = datetime(2025, 12, 31)  # Only expiration
        
        period_start, period_end = account3.get_license_period(date(2025, 6, 1))
        print(f"   License Period: {period_start} to {period_end}")
        
        expected_start = date(2024, 12, 31)  # Inferred as 1 year prior
        expected_end = date(2025, 12, 31)
        assert period_start == expected_start, f"Expected {expected_start}, got {period_start}"
        assert period_end == expected_end, f"Expected {expected_end}, got {period_end}"
        print("   ✅ PASS: Legacy account activation correctly inferred")
        
        
        # Test Case 4: Trial account (no license dates)
        print("\n📅 Test Case 4: Trial account with no license dates")
        account4 = BusinessAccount()
        account4.license_activated_at = None
        account4.license_expires_at = None
        account4.license_status = 'trial'
        
        period_start, period_end = account4.get_license_period(date(2025, 6, 1))
        print(f"   License Period: {period_start} to {period_end}")
        
        # Should return None for both (handled by can_activate_campaign fallback)
        assert period_start is None, f"Expected None, got {period_start}"
        assert period_end is None, f"Expected None, got {period_end}"
        print("   ✅ PASS: Trial account returns None periods (fallback to calendar year)")


def test_campaign_counting_logic():
    """Test the updated can_activate_campaign method"""
    
    print("\n\n🎯 Testing Campaign Counting Logic")
    print("=" * 50)
    
    with app.app_context():
        # Clean up any existing test data
        Campaign.query.filter(Campaign.business_account_id.in_([999, 998])).delete()
        BusinessAccount.query.filter(BusinessAccount.id.in_([999, 998])).delete()
        db.session.commit()
        
        # Test Case 1: Account with 3 campaigns in license period
        print("\n🎯 Test Case 1: Account with 3 campaigns in license period")
        
        account = BusinessAccount(
            id=999,
            name="Test Account 1",
            license_activated_at=datetime(2025, 3, 15),
            license_expires_at=datetime(2026, 3, 15)
        )
        db.session.add(account)
        db.session.flush()
        
        # Add 3 campaigns within the license period
        campaigns = [
            Campaign(
                name=f"Test Campaign {i}",
                business_account_id=999,
                start_date=date(2025, 4, 1),
                end_date=date(2025, 4, 30),
                status='completed'
            ) for i in range(1, 4)
        ]
        
        for campaign in campaigns:
            db.session.add(campaign)
        db.session.commit()
        
        # Should be able to create 1 more campaign (3 < 4)
        can_activate = account.can_activate_campaign()
        print(f"   Can activate campaign: {can_activate}")
        assert can_activate == True, "Should be able to activate 4th campaign"
        print("   ✅ PASS: Can activate 4th campaign in license period")
        
        
        # Test Case 2: Account with 4 campaigns (at limit)
        print("\n🎯 Test Case 2: Account with 4 campaigns (at limit)")
        
        # Add 4th campaign
        campaign4 = Campaign(
            name="Test Campaign 4",
            business_account_id=999,
            start_date=date(2025, 5, 1),
            end_date=date(2025, 5, 30),
            status='completed'
        )
        db.session.add(campaign4)
        db.session.commit()
        
        # Should NOT be able to create another campaign (4 >= 4)
        can_activate = account.can_activate_campaign()
        print(f"   Can activate campaign: {can_activate}")
        assert can_activate == False, "Should NOT be able to activate 5th campaign"
        print("   ✅ PASS: Cannot activate 5th campaign (limit reached)")
        
        
        # Test Case 3: Trial account fallback to calendar year
        print("\n🎯 Test Case 3: Trial account fallback to calendar year")
        
        trial_account = BusinessAccount(
            id=998,
            name="Trial Account",
            license_activated_at=None,
            license_expires_at=None,
            license_status='trial'
        )
        db.session.add(trial_account)
        db.session.commit()
        
        # Should use calendar year fallback
        can_activate = trial_account.can_activate_campaign()
        print(f"   Can activate campaign: {can_activate}")
        assert can_activate == True, "Trial account should be able to create campaigns"
        print("   ✅ PASS: Trial account uses calendar year fallback")
        
        
        # Clean up test data
        Campaign.query.filter(Campaign.business_account_id.in_([999, 998])).delete()
        BusinessAccount.query.filter(BusinessAccount.id.in_([999, 998])).delete()
        db.session.commit()


def test_cross_year_scenarios():
    """Test scenarios that cross calendar years"""
    
    print("\n\n📈 Testing Cross-Year Scenarios")
    print("=" * 50)
    
    with app.app_context():
        # Test Case: License from Nov 2024 to Nov 2025
        print("\n📈 Test Case: License crosses calendar years (Nov 2024 - Nov 2025)")
        
        account = BusinessAccount()
        account.license_activated_at = datetime(2024, 11, 1)
        account.license_expires_at = datetime(2025, 11, 1)
        
        # Check period for date in 2025 (should still use 2024-2025 license period)
        period_start, period_end = account.get_license_period(date(2025, 6, 1))
        print(f"   License Period: {period_start} to {period_end}")
        
        expected_start = date(2024, 11, 1)
        expected_end = date(2025, 11, 1)
        assert period_start == expected_start, f"Expected {expected_start}, got {period_start}"
        assert period_end == expected_end, f"Expected {expected_end}, got {period_end}"
        print("   ✅ PASS: Cross-year license period calculated correctly")
        
        print("\n   This demonstrates the fix:")
        print("   - OLD LOGIC: Would count campaigns from Jan 1, 2025 to Dec 31, 2025")
        print("   - NEW LOGIC: Counts campaigns from Nov 1, 2024 to Nov 1, 2025")
        print("   - BENEFIT: Customer gets full 4 campaigns across their license period")


if __name__ == "__main__":
    print("🚀 License Period Calculation Test Suite")
    print("Testing the anniversary-based license calculation fix")
    print("=" * 60)
    
    try:
        test_license_period_calculations()
        test_campaign_counting_logic()
        test_cross_year_scenarios()
        
        print("\n\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("✅ License period calculation is working correctly")
        print("✅ Campaign counting logic uses anniversary periods")
        print("✅ Edge cases (leap years, trial accounts) handled properly")
        print("✅ Cross-year scenarios work as expected")
        print("\n💡 The critical business logic fix has been successfully implemented!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)