"""Detailed test to verify SURVEY GOALS section is present in hybrid prompt"""
import os
from app import app
from models import Campaign
from prompt_template_service import PromptTemplateService

def test_prompt_has_goals_section():
    """Verify hybrid prompt contains explicit SURVEY GOALS section with field mappings"""
    with app.app_context():
        campaign = Campaign.query.get(45)
        
        service = PromptTemplateService(
            business_account_id=campaign.business_account_id,
            campaign_id=campaign.id
        )
        
        manager_data = {
            'name': 'Jean Dupont',
            'role': 'Manager',
            'region': 'Quebec',
            'customer_tier': 'Premium',
            'company_name': 'Test Corp',
            'language': 'fr'
        }
        
        extracted_data = {"nps_score": None}
        conversation_history = ""
        
        hybrid_prompt = service._generate_hybrid_prompt(
            extracted_data=extracted_data,
            step_count=1,
            conversation_history=conversation_history,
            participant_data=manager_data
        )
        
        print("="*80)
        print("VERIFICATION: SURVEY GOALS Section Presence")
        print("="*80)
        
        # Check for critical sections
        checks = {
            "Has 'SURVEY GOALS' header": "SURVEY GOALS" in hybrid_prompt,
            "Has 'Fields to collect:' labels": "Fields to collect:" in hybrid_prompt,
            "Has industry hints": "[Industry focus:" in hybrid_prompt,
            "Has 'CONTEXT USAGE' section": "CONTEXT USAGE" in hybrid_prompt,
            "Has dynamic context (no 'Not specified')": "Not specified" not in hybrid_prompt,
            "Has French language instruction": "French" in hybrid_prompt,
            "Has CONVERSATION FLOW section": "CONVERSATION FLOW" in hybrid_prompt
        }
        
        for check_name, result in checks.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {check_name}")
        
        print("\n" + "="*80)
        print("FULL HYBRID PROMPT OUTPUT")
        print("="*80)
        print(hybrid_prompt)
        print("\n" + "="*80)
        
        all_passed = all(checks.values())
        if all_passed:
            print("\n✅ ALL CHECKS PASSED - Prompt architecture is correct!")
        else:
            print("\n❌ SOME CHECKS FAILED - See output above")
        
        return all_passed

if __name__ == "__main__":
    test_prompt_has_goals_section()
