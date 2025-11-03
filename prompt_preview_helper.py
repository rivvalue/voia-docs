"""
Development-only helper for previewing AI survey prompts
Reuses PromptTemplateService to generate sample prompts for debugging
"""

from typing import Dict, Any, Optional
from prompt_template_service import PromptTemplateService


def _apply_config_overrides(service: PromptTemplateService, overrides: Dict[str, Any]):
    """
    Apply form-based configuration overrides to the template service
    This allows previewing prompts with unsaved form values
    
    Modifies the service object in-place (preview only, never saved to database)
    
    Returns:
        The modified entity (for cleanup)
    """
    # Determine which entity to override (campaign takes precedence)
    target = service.campaign if service.campaign else service.business_account
    
    if not target:
        return None  # Demo mode, no overrides applicable
    
    # Apply text field overrides
    text_fields = [
        'industry', 'conversation_tone', 'company_description',
        'product_description', 'target_clients_description',
        'custom_end_message', 'custom_system_prompt'
    ]
    
    for field in text_fields:
        if field in overrides and overrides[field] is not None:
            setattr(target, field, overrides[field])
    
    # Apply numeric field overrides
    numeric_fields = ['max_questions', 'max_duration_seconds', 'max_follow_ups_per_topic']
    
    for field in numeric_fields:
        if field in overrides and overrides[field] is not None:
            setattr(target, field, int(overrides[field]))
    
    # Apply array field overrides (stored as JSON in database)
    array_fields = ['survey_goals', 'prioritized_topics', 'optional_topics']
    
    for field in array_fields:
        if field in overrides and isinstance(overrides[field], list):
            setattr(target, field, overrides[field])
    
    return target


def build_preview_prompt(
    business_account_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    config_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a preview of the AI survey prompt for development/debugging purposes
    
    This reuses the production PromptTemplateService with sample participant data
    to show what prompts will be generated based on current customization settings.
    
    Args:
        business_account_id: ID of business account (for global customization)
        campaign_id: ID of campaign (for campaign-specific customization)
        config_overrides: Optional dict of form values to preview before saving to database
    
    Returns:
        Dict containing:
            - system_prompt: The generated system prompt
            - config: The survey configuration used
            - sample_context: The sample data used for preview
    """
    from models import db
    
    # Initialize template service (same as production)
    template_service = PromptTemplateService(
        business_account_id=business_account_id,
        campaign_id=campaign_id
    )
    
    # Track which object was modified for cleanup
    modified_entity = None
    
    # Apply config overrides if provided (for pre-save validation)
    if config_overrides:
        modified_entity = _apply_config_overrides(template_service, config_overrides)
    
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
    
    # CRITICAL: Expunge modified entity from session to prevent accidental persistence
    # Preview-only changes should NEVER be auto-flushed to the database
    if modified_entity:
        db.session.expunge(modified_entity)
    
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
