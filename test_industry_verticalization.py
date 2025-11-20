"""
Test Industry-Specific Topic Hints Verticalization

This script demonstrates how industry selection customizes AI prompt focus areas
by comparing EMS vs Healthcare examples.
"""

from industry_topic_hints_config import get_industry_hints, get_available_industries

def test_industry_hints():
    """Test that different industries produce different topic hints"""
    print("=" * 80)
    print("INDUSTRY-SPECIFIC TOPIC HINTS VERTICALIZATION TEST")
    print("=" * 80)
    
    # Show available industries
    print("\n📋 Available Industries:")
    industries = get_available_industries()
    for i, industry in enumerate(industries, 1):
        print(f"  {i}. {industry}")
    
    # Test EMS industry
    print("\n" + "=" * 80)
    print("🏭 EMS (Electronics Manufacturing Services) Industry")
    print("=" * 80)
    ems_hints = get_industry_hints("EMS")
    print("\n🎯 Topic Hints for EMS:")
    for topic, hint in ems_hints.items():
        print(f"\n  Topic: {topic}")
        print(f"  Focus: {hint}")
    
    # Test Healthcare industry
    print("\n" + "=" * 80)
    print("🏥 Healthcare Industry")
    print("=" * 80)
    healthcare_hints = get_industry_hints("Healthcare")
    print("\n🎯 Topic Hints for Healthcare:")
    for topic, hint in healthcare_hints.items():
        print(f"\n  Topic: {topic}")
        print(f"  Focus: {hint}")
    
    # Direct comparison for Product Quality
    print("\n" + "=" * 80)
    print("🔍 DIRECT COMPARISON: Product Quality")
    print("=" * 80)
    print(f"\n  EMS Focus:")
    print(f"  '{ems_hints['Product Quality']}'")
    print(f"\n  Healthcare Focus:")
    print(f"  '{healthcare_hints['Product Quality']}'")
    
    # Verify they are different
    if ems_hints['Product Quality'] != healthcare_hints['Product Quality']:
        print("\n✅ SUCCESS: Industry verticalization is working!")
        print("   Different industries produce different focus areas for the same topic.")
        return True
    else:
        print("\n❌ FAILED: Industry hints are not differentiated")
        return False

if __name__ == '__main__':
    try:
        success = test_industry_hints()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
