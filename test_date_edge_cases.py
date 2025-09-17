#!/usr/bin/env python3
"""
Test script for License Template Date Calculation Edge Cases
Author: System Integration Agent
Created: September 17, 2025

This script tests the date calculation fix in the License Template System to ensure:
- Month-end date rollovers are handled safely
- The add_months utility function works correctly for all edge cases
- License expiration dates are calculated properly for problematic start dates
- All edge cases like leap years, month-end dates, and year transitions work correctly
"""

import sys
import os
from datetime import datetime

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from license_templates import add_months, LicenseTemplateManager

def test_add_months_basic():
    """Test basic month addition functionality"""
    print("=== Testing Basic Month Addition ===")
    
    test_cases = [
        # Basic cases (no edge cases)
        (datetime(2025, 1, 15), 1, datetime(2025, 2, 15)),
        (datetime(2025, 6, 10), 3, datetime(2025, 9, 10)),
        (datetime(2025, 11, 5), 2, datetime(2026, 1, 5)),
        (datetime(2025, 12, 20), 1, datetime(2026, 1, 20)),
        
        # Zero months (no change)
        (datetime(2025, 5, 15), 0, datetime(2025, 5, 15)),
        
        # Negative months (going backward)
        (datetime(2025, 3, 15), -1, datetime(2025, 2, 15)),
        (datetime(2025, 1, 15), -1, datetime(2024, 12, 15)),
    ]
    
    for start_date, months, expected in test_cases:
        result = add_months(start_date, months)
        print(f"  {start_date} + {months} months = {result}")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✅ Basic month addition tests passed!\n")

def test_add_months_edge_cases():
    """Test month-end rollover edge cases"""
    print("=== Testing Month-End Edge Cases ===")
    
    edge_cases = [
        # January 31st cases
        (datetime(2025, 1, 31), 1, datetime(2025, 2, 28)),  # Jan 31 -> Feb 28
        (datetime(2024, 1, 31), 1, datetime(2024, 2, 29)),  # Jan 31 -> Feb 29 (leap year)
        (datetime(2025, 1, 31), 2, datetime(2025, 3, 31)),  # Jan 31 -> Mar 31
        (datetime(2025, 1, 31), 3, datetime(2025, 4, 30)),  # Jan 31 -> Apr 30
        
        # March 31st cases
        (datetime(2025, 3, 31), 1, datetime(2025, 4, 30)),  # Mar 31 -> Apr 30
        (datetime(2025, 3, 31), 2, datetime(2025, 5, 31)),  # Mar 31 -> May 31
        (datetime(2025, 3, 31), 6, datetime(2025, 9, 30)),  # Mar 31 -> Sep 30
        
        # May 31st cases
        (datetime(2025, 5, 31), 1, datetime(2025, 6, 30)),  # May 31 -> Jun 30
        (datetime(2025, 5, 31), 6, datetime(2025, 11, 30)), # May 31 -> Nov 30
        
        # December 31st cases (year transition)
        (datetime(2024, 12, 31), 1, datetime(2025, 1, 31)), # Dec 31 -> Jan 31 (next year)
        (datetime(2024, 12, 31), 2, datetime(2025, 2, 28)), # Dec 31 -> Feb 28 (non-leap)
        (datetime(2025, 12, 31), 2, datetime(2026, 2, 28)), # Dec 31 -> Feb 28 (non-leap)
        
        # February edge cases
        (datetime(2025, 2, 28), 1, datetime(2025, 3, 28)),  # Feb 28 -> Mar 28
        (datetime(2024, 2, 29), 1, datetime(2024, 3, 29)),  # Feb 29 -> Mar 29 (leap year)
        (datetime(2024, 2, 29), 12, datetime(2025, 2, 28)), # Feb 29 -> Feb 28 (next year, non-leap)
        
        # Multi-year spans
        (datetime(2023, 1, 31), 13, datetime(2024, 2, 29)), # 13 months: Jan 31 2023 -> Feb 29 2024
        (datetime(2024, 1, 31), 25, datetime(2026, 2, 28)), # 25 months: Jan 31 2024 -> Feb 28 2026
    ]
    
    for start_date, months, expected in edge_cases:
        result = add_months(start_date, months)
        print(f"  {start_date} + {months} months = {result}")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✅ Month-end edge cases tests passed!\n")

def test_license_date_calculation():
    """Test license date calculation using the fixed method"""
    print("=== Testing License Date Calculation ===")
    
    # Test cases with problematic start dates
    problematic_dates = [
        datetime(2025, 1, 31),  # January 31st
        datetime(2025, 3, 31),  # March 31st 
        datetime(2025, 5, 31),  # May 31st
        datetime(2025, 7, 31),  # July 31st
        datetime(2025, 8, 31),  # August 31st
        datetime(2025, 10, 31), # October 31st
        datetime(2025, 12, 31), # December 31st
        datetime(2024, 2, 29),  # Leap year February 29th
        datetime(2025, 2, 28),  # Non-leap year February 28th
    ]
    
    # Test with different license types and durations
    license_configs = [
        ('core', 12),   # Core: 12 months
        ('plus', 12),   # Plus: 12 months  
        ('pro', 12),    # Pro: 12 months
        ('trial', 1),   # Trial: 1 month
        ('core', 6),    # Custom duration: 6 months
        ('core', 24),   # Custom duration: 24 months
    ]
    
    for start_date in problematic_dates:
        print(f"Testing with start date: {start_date}")
        
        for license_type, duration in license_configs:
            try:
                # This should NOT raise a ValueError anymore
                activation_date, expiration_date = LicenseTemplateManager.calculate_license_dates(
                    license_type=license_type,
                    start_date=start_date,
                    duration_months=duration
                )
                
                print(f"  {license_type} ({duration}m): {activation_date} -> {expiration_date}")
                
                # Verify the activation date matches start date
                assert activation_date == start_date, f"Activation date should match start date"
                
                # Verify expiration is after activation
                assert expiration_date > activation_date, f"Expiration should be after activation"
                
                # Verify the month difference is approximately correct
                # (allowing for month-end clamping)
                months_diff = (expiration_date.year - activation_date.year) * 12 + \
                             (expiration_date.month - activation_date.month)
                assert months_diff == duration, f"Should be {duration} months difference, got {months_diff}"
                
            except ValueError as e:
                print(f"  ❌ FAILED for {license_type} ({duration}m): {e}")
                raise
    
    print("✅ License date calculation tests passed!\n")

def test_leap_year_edge_cases():
    """Test specific leap year edge cases"""
    print("=== Testing Leap Year Edge Cases ===")
    
    leap_year_cases = [
        # 2024 is a leap year
        (datetime(2024, 2, 29), 12, datetime(2025, 2, 28)),  # Feb 29 -> Feb 28 (next year)
        (datetime(2024, 1, 31), 1, datetime(2024, 2, 29)),   # Jan 31 -> Feb 29 (leap year)
        (datetime(2023, 2, 28), 12, datetime(2024, 2, 28)),  # Feb 28 -> Feb 28 (leap year)
        
        # 2025 is not a leap year
        (datetime(2025, 1, 31), 1, datetime(2025, 2, 28)),   # Jan 31 -> Feb 28 (non-leap)
        (datetime(2025, 2, 28), 12, datetime(2026, 2, 28)),  # Feb 28 -> Feb 28 (non-leap)
        
        # 4-year cycle test
        (datetime(2024, 2, 29), 48, datetime(2028, 2, 29)),  # Feb 29 -> Feb 29 (4 years later)
    ]
    
    for start_date, months, expected in leap_year_cases:
        result = add_months(start_date, months)
        print(f"  {start_date} + {months} months = {result}")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("✅ Leap year edge cases tests passed!\n")

def test_comprehensive_license_scenarios():
    """Test comprehensive real-world license scenarios"""
    print("=== Testing Real-World License Scenarios ===")
    
    # Simulate real license creation scenarios
    scenarios = [
        {
            'name': 'Enterprise Pro License - Started on Jan 31',
            'start_date': datetime(2025, 1, 31),
            'license_type': 'pro',
            'duration': 24,  # 2 years
            'expected_expiration': datetime(2027, 1, 31)
        },
        {
            'name': 'Monthly Trial - Started on March 31',
            'start_date': datetime(2025, 3, 31),
            'license_type': 'trial',
            'duration': 1,
            'expected_expiration': datetime(2025, 4, 30)  # Clamped to Apr 30
        },
        {
            'name': 'Annual Core License - Started on Leap Day',
            'start_date': datetime(2024, 2, 29),
            'license_type': 'core',
            'duration': 12,
            'expected_expiration': datetime(2025, 2, 28)  # Clamped to Feb 28
        },
        {
            'name': 'Semi-Annual Plus License - Started on Aug 31',
            'start_date': datetime(2025, 8, 31),
            'license_type': 'plus',
            'duration': 6,
            'expected_expiration': datetime(2026, 2, 28)  # Aug 31 + 6m = Feb 28
        }
    ]
    
    for scenario in scenarios:
        print(f"Testing: {scenario['name']}")
        
        activation_date, expiration_date = LicenseTemplateManager.calculate_license_dates(
            license_type=scenario['license_type'],
            start_date=scenario['start_date'],
            duration_months=scenario['duration']
        )
        
        print(f"  Start: {activation_date}")
        print(f"  Expected: {scenario['expected_expiration']}")
        print(f"  Actual: {expiration_date}")
        
        assert activation_date == scenario['start_date']
        assert expiration_date == scenario['expected_expiration'], \
            f"Expected {scenario['expected_expiration']}, got {expiration_date}"
        
        print(f"  ✅ Passed\n")
    
    print("✅ Real-world license scenarios tests passed!\n")

def main():
    """Run all date edge case tests"""
    print("🧪 License Template Date Calculation Test Suite")
    print("=" * 60)
    
    try:
        # Run all test suites
        test_add_months_basic()
        test_add_months_edge_cases()
        test_license_date_calculation()
        test_leap_year_edge_cases()
        test_comprehensive_license_scenarios()
        
        print("🎉 All date edge case tests passed successfully!")
        print("The fix for month-end date calculation is working correctly.")
        
        # Summary of what was tested
        print("\n📋 Test Summary:")
        print("✅ Basic month addition (no edge cases)")
        print("✅ Month-end rollover edge cases (Jan 31, Mar 31, etc.)")
        print("✅ License date calculation with problematic dates")
        print("✅ Leap year handling (Feb 29 scenarios)")
        print("✅ Real-world license scenarios")
        print("✅ Year transitions and multi-year spans")
        print("✅ All license types (Core, Plus, Pro, Trial)")
        print("✅ Custom duration periods")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)