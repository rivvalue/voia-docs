"""
Development-only helper for previewing AI survey prompts
Reuses PromptTemplateService to generate sample prompts for debugging
"""

from typing import Dict, Any, Optional
from prompt_template_service import PromptTemplateService


def build_preview_prompt(
    business_account_id: Optional[int] = None,
    campaign_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate a preview of the AI survey prompt for development/debugging purposes
    
    This reuses the production PromptTemplateService with sample participant data
    to show what prompts will be generated based on current customization settings.
    
    Args:
        business_account_id: ID of business account (for global customization)
        campaign_id: ID of campaign (for campaign-specific customization)
    
    Returns:
        Dict containing:
            - system_prompt: The generated system prompt
            - config: The survey configuration used
            - sample_context: The sample data used for preview
    """
    # Initialize template service (same as production)
    template_service = PromptTemplateService(
        business_account_id=business_account_id,
        campaign_id=campaign_id
    )
    
    # Create sample participant data (deterministic for preview)
    sample_participant_data = {
        'name': 'John Doe',
        'email': 'john.doe@example.com',
        'role': 'Product Manager',
        'region': 'North America',
        'customer_tier': 'Enterprise',
        'language': 'en',
        'company': 'Acme Corporation'
    }
    
    # Sample extracted data (empty at start of survey)
    sample_extracted_data = {}
    
    # Sample conversation state
    step_count = 1
    conversation_history = "Beginning of conversation"
    
    # Generate the system prompt (same method used in production)
    system_prompt = template_service.generate_system_prompt(
        extracted_data=sample_extracted_data,
        step_count=step_count,
        conversation_history=conversation_history,
        participant_data=sample_participant_data
    )
    
    # Build survey config for preview (shows what settings are being used)
    survey_config = template_service.build_survey_config_json(sample_participant_data)
    
    # Return preview data
    return {
        'system_prompt': system_prompt,
        'config': survey_config,
        'sample_context': {
            'participant': sample_participant_data,
            'step_count': step_count,
            'extracted_data': sample_extracted_data,
            'is_demo_mode': template_service.is_demo_mode
        },
        'metadata': {
            'business_account_id': business_account_id,
            'campaign_id': campaign_id,
            'using_campaign_config': template_service.campaign is not None and template_service.has_campaign_customization(),
            'using_business_config': template_service.business_account is not None,
            'fallback_to_demo': template_service.is_demo_mode
        }
    }
