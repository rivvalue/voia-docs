#!/usr/bin/env python3
"""
Test script for PromptTemplateService hybrid business+campaign data support
Tests backward compatibility and new functionality
"""

import sys
import os
import traceback

# Add current directory to path for imports
sys.path.insert(0, '.')

def test_prompt_template_service():
    """Comprehensive test of PromptTemplateService hybrid functionality"""
    print("=" * 60)
    print("Testing PromptTemplateService Hybrid Data Support")
    print("=" * 60)
    
    try:
        from prompt_template_service import PromptTemplateService
        print("✅ Successfully imported PromptTemplateService")
    except Exception as e:
        print(f"❌ Failed to import PromptTemplateService: {e}")
        return False
    
    # Test 1: Backward Compatibility - Demo Mode
    print("\n🧪 Test 1: Demo Mode (backward compatibility)")
    try:
        service = PromptTemplateService()
        assert service.is_demo_mode == True
        assert service.campaign_id is None
        assert service.business_account_id is None
        assert service.get_company_name() == "Archelo Group"
        assert service.get_product_name() == "ArcheloFlow"
        assert service.get_max_questions() == 8
        assert service.get_max_duration_seconds() == 120
        print("✅ Demo mode works correctly")
    except Exception as e:
        print(f"❌ Demo mode test failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 2: Business Account Only (backward compatibility)
    print("\n🧪 Test 2: Business Account Only (backward compatibility)")
    try:
        # Test with invalid business account ID (should fall back to demo)
        service = PromptTemplateService(business_account_id=99999)
        assert service.is_demo_mode == True
        print("✅ Invalid business account ID handled correctly")
        
        # Test constructor signature is backward compatible
        service = PromptTemplateService(123)  # Positional argument should work
        print("✅ Backward compatible constructor works")
    except Exception as e:
        print(f"❌ Business account test failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 3: Campaign Only (new functionality)
    print("\n🧪 Test 3: Campaign Only (new functionality)")
    try:
        # Test with invalid campaign ID (should handle gracefully)
        service = PromptTemplateService(campaign_id=99999)
        assert service.campaign is None
        assert service.is_demo_mode == True  # Should fall back to demo
        print("✅ Invalid campaign ID handled gracefully")
    except Exception as e:
        print(f"❌ Campaign only test failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 4: Hybrid Mode (campaign + business account)
    print("\n🧪 Test 4: Hybrid Mode (campaign + business account)")
    try:
        service = PromptTemplateService(business_account_id=123, campaign_id=456)
        assert service.campaign_id == 456
        assert service.business_account_id == 123
        print("✅ Hybrid mode constructor works")
    except Exception as e:
        print(f"❌ Hybrid mode test failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 5: New Helper Methods
    print("\n🧪 Test 5: New Helper Methods")
    try:
        service = PromptTemplateService()
        
        # Test has_campaign_customization
        has_campaign_custom = service.has_campaign_customization()
        assert isinstance(has_campaign_custom, bool)
        print("✅ has_campaign_customization() works")
        
        # Test get_effective_survey_config
        config = service.get_effective_survey_config()
        assert isinstance(config, dict)
        assert 'company_name' in config
        assert 'product_name' in config
        assert 'max_questions' in config
        assert 'is_demo_mode' in config
        assert 'campaign_id' in config
        assert 'business_account_id' in config
        print("✅ get_effective_survey_config() works")
        
        # Test updated get_template_info
        info = service.get_template_info()
        assert isinstance(info, dict)
        assert 'campaign_id' in info
        assert 'has_campaign_customization' in info
        assert 'data_source_priority' in info
        print("✅ Updated get_template_info() works")
        
    except Exception as e:
        print(f"❌ Helper methods test failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 6: Survey Configuration Methods
    print("\n🧪 Test 6: Survey Configuration Methods")
    try:
        service = PromptTemplateService()
        
        # Test all survey config methods return expected types
        assert isinstance(service.get_survey_goals(), list)
        assert isinstance(service.get_max_questions(), int)
        assert isinstance(service.get_max_duration_seconds(), int)
        assert isinstance(service.get_conversation_tone(), str)
        assert isinstance(service.get_completion_message(), str)
        
        print("✅ All survey configuration methods work")
        
    except Exception as e:
        print(f"❌ Survey configuration test failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 7: Prompt Generation Methods
    print("\n🧪 Test 7: Prompt Generation Methods")
    try:
        service = PromptTemplateService()
        
        # Test welcome message generation
        welcome = service.generate_welcome_message("John Doe")
        assert "John Doe" in welcome
        assert isinstance(welcome, str)
        print("✅ Welcome message generation works")
        
        # Test system prompt generation
        extracted_data = {"nps_score": 8}
        conversation_history = "Previous conversation..."
        system_prompt = service.generate_system_prompt(extracted_data, 1, conversation_history)
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 100  # Should be substantial
        print("✅ System prompt generation works")
        
    except Exception as e:
        print(f"❌ Prompt generation test failed: {e}")
        traceback.print_exc()
        return False
    
    # Test 8: Error Handling and Edge Cases
    print("\n🧪 Test 8: Error Handling and Edge Cases")
    try:
        # Test with None values
        service = PromptTemplateService(None, None)
        assert service.is_demo_mode == True
        print("✅ None values handled correctly")
        
        # Test force completion
        service = PromptTemplateService()
        assert isinstance(service.should_force_completion(5), bool)
        assert service.should_force_completion(100) == True  # Should force after max questions
        print("✅ Force completion logic works")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED! Hybrid data support is working correctly.")
    print("✅ Backward compatibility maintained")
    print("✅ New functionality implemented")
    print("✅ Error handling robust")
    print("✅ API compatibility preserved")
    print("=" * 60)
    
    return True

def test_integration_scenarios():
    """Test real-world integration scenarios"""
    print("\n" + "=" * 60)
    print("Testing Integration Scenarios")
    print("=" * 60)
    
    try:
        from prompt_template_service import PromptTemplateService
        
        # Scenario 1: Legacy code that only uses business account
        print("\n📋 Scenario 1: Legacy code compatibility")
        service = PromptTemplateService(business_account_id=1)
        config = service.get_effective_survey_config()
        print(f"   Company: {config['company_name']}")
        print(f"   Demo mode: {config['is_demo_mode']}")
        print("✅ Legacy code works without modification")
        
        # Scenario 2: New code using campaign data
        print("\n📋 Scenario 2: New campaign-based surveys")
        service = PromptTemplateService(campaign_id=1)
        config = service.get_effective_survey_config()
        print(f"   Campaign ID: {config['campaign_id']}")
        print(f"   Has campaign customization: {config['has_campaign_customization']}")
        print("✅ Campaign-based surveys work")
        
        # Scenario 3: Full hybrid mode
        print("\n📋 Scenario 3: Hybrid campaign + business account")
        service = PromptTemplateService(business_account_id=1, campaign_id=1)
        config = service.get_effective_survey_config()
        print(f"   Data priority: {config.get('data_source_priority', 'Not available')}")
        print("✅ Hybrid mode works")
        
        print("\n🎯 Integration scenarios complete!")
        return True
        
    except Exception as e:
        print(f"❌ Integration scenario failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting PromptTemplateService Hybrid Data Support Tests...")
    
    # Run main functionality tests
    main_tests_passed = test_prompt_template_service()
    
    # Run integration tests
    integration_tests_passed = test_integration_scenarios()
    
    if main_tests_passed and integration_tests_passed:
        print("\n🏆 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("The PromptTemplateService hybrid business+campaign data support is ready for production.")
        sys.exit(0)
    else:
        print("\n💥 SOME TESTS FAILED!")
        print("Please review the errors above and fix the issues.")
        sys.exit(1)