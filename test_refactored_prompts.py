"""Test script for refactored universal prompt architecture"""
import os
import json
from app import app, db
from models import Campaign, Participant
from prompt_template_service import PromptTemplateService, filter_goals_by_role, _map_role_to_tier, ROLE_METADATA

def test_campaign_45():
    """Test Campaign 45 (French, Manager role, SaaS industry)"""
    with app.app_context():
        campaign = Campaign.query.get(45)
        if not campaign:
            print("ERROR: Campaign 45 not found")
            return
        
        print(f"\n{'='*80}")
        print(f"Testing Campaign 45: {campaign.name}")
        print(f"{'='*80}")
        print(f"Language: {campaign.language_code}")
        print(f"Industry: {campaign.industry or campaign.business_account.industry}")
        print(f"Max Questions: {campaign.max_questions or campaign.business_account.max_questions}")
        print(f"Conversation Tone: {campaign.business_account.conversation_tone or 'professional'}")
        
        # Initialize prompt service
        service = PromptTemplateService(
            business_account_id=campaign.business_account_id,
            campaign_id=campaign.id
        )
        
        # Test 1: Role filtering for Manager
        print(f"\n{'-'*80}")
        print("TEST 1: Role-Based Goal Filtering")
        print(f"{'-'*80}")
        
        # Simulate manager participant data
        manager_data = {
            'name': 'Jean Dupont',
            'email': 'jean.dupont@example.com',
            'role': 'Manager',
            'region': 'Quebec',
            'customer_tier': 'Premium',
            'company_name': 'Test Corp',
            'language': 'fr'
        }
        
        # Map role to tier
        role_tier = _map_role_to_tier('Manager')
        print(f"Role: Manager")
        print(f"Mapped to tier: {role_tier}")
        print(f"Role label: {ROLE_METADATA[role_tier]['label']}")
        print(f"Excluded topics: {ROLE_METADATA[role_tier]['excluded_topics']}")
        
        # Test 2: Survey configuration with role filtering
        print(f"\n{'-'*80}")
        print("TEST 2: Survey Configuration JSON")
        print(f"{'-'*80}")
        
        survey_config = service.build_survey_config_json(manager_data)
        print(f"Company: {survey_config['company_name']}")
        print(f"Max Questions: {survey_config['max_questions']}")
        print(f"Conversation Tone: {survey_config['conversation_tone']}")
        print(f"Industry: {survey_config.get('context', {}).get('industry', 'Not set')}")
        print(f"\nFiltered Goals for Manager role:")
        for goal in survey_config['goals']:
            hint = f" [Hint: {goal['industry_hint']}]" if goal.get('industry_hint') else ""
            print(f"  {goal['priority']}. {goal['topic']}: {goal['description']}{hint}")
        
        # Test 3: Hybrid prompt generation
        print(f"\n{'-'*80}")
        print("TEST 3: Hybrid Prompt Generation")
        print(f"{'-'*80}")
        
        extracted_data = {"nps_score": None}
        conversation_history = ""
        step_count = 1
        
        hybrid_prompt = service._generate_hybrid_prompt(
            extracted_data=extracted_data,
            step_count=step_count,
            conversation_history=conversation_history,
            participant_data=manager_data
        )
        
        # Check for French language instruction
        has_french_instruction = "French" in hybrid_prompt
        print(f"Contains French language instruction: {has_french_instruction}")
        
        # Check for tone parameter
        tone = survey_config['conversation_tone']
        has_tone = tone in hybrid_prompt
        print(f"Contains tone '{tone}': {has_tone}")
        
        # Check for max_questions parameter
        max_q = survey_config['max_questions']
        has_max_q = str(max_q) in hybrid_prompt
        print(f"Contains max_questions '{max_q}': {has_max_q}")
        
        # Print snippet of prompt
        print(f"\nPrompt snippet (first 800 chars):")
        print(hybrid_prompt[:800])
        print("...")
        
        print(f"\n{'-'*80}")
        print("TEST 4: Role Exclusion Testing")
        print(f"{'-'*80}")
        
        # Test End User role (should exclude Pricing)
        test_topics = ["NPS", "Product Value", "Pricing Value", "Support Quality"]
        
        print("\nTest with End User role:")
        end_user_tier = _map_role_to_tier("End User")
        filtered_end_user = filter_goals_by_role(test_topics, end_user_tier)
        print(f"  Original topics: {test_topics}")
        print(f"  Excluded topics: {ROLE_METADATA[end_user_tier]['excluded_topics']}")
        print(f"  Filtered topics: {filtered_end_user}")
        print(f"  Expected: ['NPS', 'Product Value', 'Support Quality'] (no Pricing)")
        print(f"  PASS: {filtered_end_user == ['NPS', 'Product Value', 'Support Quality']}")
        
        print("\nTest with Manager role:")
        manager_tier = _map_role_to_tier("Manager")
        filtered_manager = filter_goals_by_role(test_topics, manager_tier)
        print(f"  Original topics: {test_topics}")
        print(f"  Excluded topics: {ROLE_METADATA[manager_tier]['excluded_topics']}")
        print(f"  Filtered topics: {filtered_manager}")
        print(f"  Expected: {test_topics} (no exclusions)")
        print(f"  PASS: {filtered_manager == test_topics}")
        
        print(f"\n{'='*80}")
        print("Test Complete!")
        print(f"{'='*80}\n")

if __name__ == "__main__":
    test_campaign_45()
