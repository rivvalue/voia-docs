"""
Prompt Template Service for VOÏA Conversational Surveys
Handles dynamic prompt generation based on BusinessAccount customization settings
Supports dual-mode operation: demo (hardcoded) vs customer (customized)
Hybrid Prompt Architecture: Structured JSON configuration + conversation guidance
"""

import json
from typing import Dict, Any, Optional, List
from models import BusinessAccount, Campaign


def _parse_json_list(value: Any) -> Optional[List]:
    """
    Safely parse a value that should be a list, handling JSON strings.
    
    SQLAlchemy may return JSON fields as strings that need parsing.
    This helper ensures we always get a proper Python list.
    
    Args:
        value: Could be a list, JSON string, or None
        
    Returns:
        Parsed list or None if invalid
    """
    if value is None:
        return None
    
    # Already a list - return copy to avoid mutation
    if isinstance(value, list):
        return list(value)
    
    # String - try to parse as JSON
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    
    return None


# Topic-to-Field Mapping for AI Response Validation and Analytics
# CRITICAL: Each topic MUST have unique fields to enable backend-controlled survey completion
TOPIC_FIELD_MAP = {
    "NPS": ["nps_score", "nps_reasoning"],
    "Business Relationship Tenure": ["tenure_with_fc"],
    "Overall Satisfaction": ["satisfaction_rating"],
    "Professional Services Quality": ["service_rating"],
    "Product Value": ["product_value_rating"],
    "Pricing Value": ["pricing_rating"],
    "Support Quality": ["support_rating"],
    "Improvement Suggestions": ["improvement_feedback"],
    "Additional Feedback": ["additional_comments"],
    # New unique fields for common campaign topics
    "Product Quality": ["product_quality_feedback"],
    "Support Experience": ["support_experience_feedback"],
    "Service Rating": ["service_rating_feedback"],
    "User Experience": ["user_experience_feedback"],
    "Feature Requests": ["feature_requests"],
    "General Feedback": ["general_feedback"]
}

# Universal Guidelines Template (Parameterized)
# Parameters: {tone}, {max_questions}
# Note: Context fields are built dynamically in prompt generation to avoid "Not specified" placeholders
UNIVERSAL_GUIDELINES = """
==========================
COMPLETION RULES (CRITICAL)
==========================

YOU ARE NOT ALLOWED TO DECIDE WHEN THE SURVEY ENDS.
- The backend system controls completion by checking if all goals are satisfied
- You MUST ALWAYS set "is_complete": false in your response
- DO NOT write closing/farewell messages like "merci pour votre temps" or "cela conclut le questionnaire"
- The backend will stop calling you when all goals are complete - you will never see that happen
- Your ONLY role: ask the next question based on missing fields

==========================
CONVERSATION FLOW
==========================

At each step:
1. Review SURVEY DATA COLLECTED SO FAR to identify missing fields
2. Select the highest-priority goal with missing fields from the SURVEY GOALS section below
3. Ask ONE clear question about the missing field
4. After the response, extract data and move to the next priority
5. Keep questions concise, {tone}, and natural

==========================
YOUR RESPONSIBILITIES
==========================

1. Follow SURVEY GOALS in priority order - complete each topic before moving to the next
2. Ask ONE question at a time in a {tone} conversational style
3. Before asking any question, check SURVEY DATA COLLECTED SO FAR - only ask for MISSING fields
4. NEVER decide to end the survey - always return "is_complete": false
5. Use context provided above to make questions relevant to the participant's situation
6. Maintain natural conversation flow while respecting all structural constraints
7. If a participant provides multiple pieces of information, acknowledge all but focus your next question on the current priority goal

==========================
GOAL COVERAGE REQUIREMENT
==========================

- You MUST treat every goal in SURVEY GOALS as mandatory
- For EACH goal, you MUST ensure that all its fields have been collected at least once
- When choosing the next question: Always pick the highest-priority goal with at least one missing field
- Never assume the survey is finished while there is any goal with missing fields

==========================
INDUSTRY-SPECIFIC VOCABULARY
==========================

When forming a question for a topic with an [Industry focus] hint:
- Use the industry-specific keywords and focus areas to choose vocabulary and examples relevant to the participant's operational reality
- Adapt your phrasing to match their industry context (e.g., "line reliability" for EMS, "workflow accuracy" for Healthcare)
- DO NOT change or rename the topic itself - only adapt the question phrasing and examples
- This helps participants recognize familiar concepts and provide more specific, valuable feedback

Be empathetic, adapt to user communication style, and keep the conversation natural while respecting all constraints.

RESPONSE FORMAT: Return JSON with fields: message, message_type, step, topic, progress, is_complete
CRITICAL: "is_complete" MUST ALWAYS BE false
"""

# Role-Based Metadata for Conversational Surveys
# Defines role labels and topic exclusions for persona-based goal filtering
ROLE_METADATA = {
    'c_level': {
        'label': 'C-level executive',
        'excluded_topics': []  # All topics visible
    },
    'vp_director': {
        'label': 'VP/Director-level leader',
        'excluded_topics': []  # All topics visible
    },
    'manager': {
        'label': 'Manager',
        'excluded_topics': []  # All topics visible
    },
    'team_lead': {
        'label': 'Team Lead/Supervisor',
        'excluded_topics': ['Pricing Value']  # Limited pricing visibility
    },
    'end_user': {
        'label': 'End User',
        'excluded_topics': ['Pricing Value']  # Limited pricing visibility
    },
    'default': {
        'label': 'Participant',
        'excluded_topics': []  # No exclusions - safe fallback shows all campaign topics
    }
}


def filter_goals_by_role(campaign_priorities: List[str], role_tier: str) -> List[str]:
    """
    Filter campaign priority topics by role-based exclusions
    
    Args:
        campaign_priorities: Ordered list of topics from campaign configuration
        role_tier: Persona tier (c_level, manager, end_user, etc.)
    
    Returns:
        Filtered list maintaining campaign priority order, excluding role-inappropriate topics
    
    Example:
        campaign_priorities = ["NPS", "Product Value", "Pricing Value", "Support Quality"]
        role_tier = "end_user"
        returns: ["NPS", "Product Value", "Support Quality"]  # Pricing excluded
    """
    if not campaign_priorities:
        return []
    
    # Get excluded topics for this role tier
    role_metadata = ROLE_METADATA.get(role_tier, ROLE_METADATA['default'])
    excluded_topics = role_metadata['excluded_topics']
    
    # Filter out excluded topics while maintaining campaign priority order
    filtered_topics = [topic for topic in campaign_priorities if topic not in excluded_topics]
    
    return filtered_topics


def _map_role_to_tier(role_string: Optional[str]) -> str:
    """
    Map participant role to persona tier with normalized matching
    
    Args:
        role_string: Raw role string from participant data
        
    Returns:
        Persona tier key (c_level, vp_director, manager, team_lead, end_user, default)
    """
    if not role_string:
        return 'default'  # Safe fallback - shows all campaign topics when role is unknown
    
    normalized = role_string.lower().strip()
    
    # C-Level patterns - use word boundary checks to avoid false matches
    # (e.g., "director" shouldn't match "cto" from "director")
    c_level_titles = ['ceo', 'cfo', 'coo', 'cto', 'chief']
    for title in c_level_titles:
        # Check if title appears as a complete word (with word boundaries)
        if f' {title} ' in f' {normalized} ' or normalized.startswith(f'{title} ') or normalized.endswith(f' {title}') or normalized == title:
            return 'c_level'
    
    # Check for "president" (but not "vice president") or "executive director"
    if ' president' in normalized or normalized == 'president':
        if 'vice' not in normalized:
            return 'c_level'
    if 'executive director' in normalized:
        return 'c_level'
    
    # VP/Director patterns
    vp_director_patterns = ['vp', 'vice president', 'director', 'head of', 'senior director']
    if any(pattern in normalized for pattern in vp_director_patterns):
        return 'vp_director'
    
    # Manager patterns (but not "team lead manager")
    manager_patterns = ['manager', 'product manager', 'project manager', 'program manager']
    if any(pattern in normalized for pattern in manager_patterns) and 'lead' not in normalized:
        return 'manager'
    
    # Team Lead patterns
    team_lead_patterns = ['team lead', 'supervisor', 'lead', 'coordinator']
    if any(pattern in normalized for pattern in team_lead_patterns):
        return 'team_lead'
    
    # End User / IC - conservative default
    return 'end_user'


class PromptTemplateService:
    """Service for generating dynamic survey prompts based on business account configuration"""
    
    def __init__(
        self, 
        business_account_id: Optional[int] = None, 
        campaign_id: Optional[int] = None,
        campaign: Optional[Any] = None,
        language: Optional[str] = None
    ):
        """
        Initialize prompt template service with hybrid business+campaign data support
        
        SOLUTION 4 (Hybrid Hot/Cold Path):
        - Hot path attributes (high frequency): Extracted to primitives at init (no session issues)
        - Cold path attributes (rare): Lazy-loaded via ID lookup when needed
        
        FIX (Nov 23, 2025): Accept campaign object to avoid session detachment issues
        
        Args:
            business_account_id: ID of business account for customized prompts, 
                               None for demo mode
            campaign_id: ID of campaign for campaign-specific customization,
                        takes precedence over business account data
            campaign: Optional Campaign object (preferred over campaign_id to avoid session issues)
            language: Optional language override (e.g., 'en', 'fr')
        """
        # Store IDs for cold path lazy reload
        self.business_account_id = business_account_id
        self.campaign_id = campaign_id
        self.language_override = language  # Store language override for AI prompts
        
        # Load ORM objects ONCE for hot path extraction
        # PREFER passed campaign object over database lookup
        business_account = None
        
        if campaign is None and campaign_id:
            try:
                campaign = Campaign.query.get(campaign_id)
                if not campaign:
                    import logging
                    logging.warning(f"Campaign ID {campaign_id} not found, falling back to business account only")
                elif campaign.business_account_id:
                    self.business_account_id = campaign.business_account_id
                    business_account_id = campaign.business_account_id
            except Exception as e:
                import logging
                logging.error(f"Error loading campaign {campaign_id}: {e}")
                campaign = None
        elif campaign:
            # Use passed campaign object (avoids session issues)
            self.campaign_id = campaign.id
            if campaign.business_account_id:
                self.business_account_id = campaign.business_account_id
                business_account_id = campaign.business_account_id
        
        if business_account_id:
            business_account = BusinessAccount.query.get(business_account_id)
        
        # === HOT PATH: Extract frequently-accessed attributes as primitives ===
        # These are accessed 2+ times or critical for hybrid prompt mode
        
        # Campaign hot path attributes (12 attributes - added name, description for welcome message)
        # Use _parse_json_list for list fields to handle JSON strings from SQLAlchemy
        self._campaign_name = campaign.name if campaign else None  # FIX (Dec 11, 2025): For campaign-aware welcome
        self._campaign_description = campaign.description if campaign else None  # FIX (Dec 11, 2025): For campaign-aware welcome
        self._campaign_prioritized_topics = _parse_json_list(campaign.prioritized_topics if campaign else None)
        self._campaign_optional_topics = _parse_json_list(campaign.optional_topics if campaign else None)  # V2 enhancement
        self._campaign_product_description = campaign.product_description if campaign else None
        self._campaign_target_clients_description = campaign.target_clients_description if campaign else None
        self._campaign_max_questions = campaign.max_questions if campaign else None
        self._campaign_max_duration_seconds = campaign.max_duration_seconds if campaign else None
        self._campaign_custom_end_message = campaign.custom_end_message if campaign else None
        self._campaign_anonymize_responses = campaign.anonymize_responses if campaign else False
        self._campaign_language_code = campaign.language_code if campaign and hasattr(campaign, 'language_code') else 'en'
        self._campaign_industry = campaign.industry if campaign and hasattr(campaign, 'industry') else None
        
        # BusinessAccount hot path attributes (11 attributes - added industry_topic_hints, removed survey_goals)
        # Use _parse_json_list for list fields to handle JSON strings from SQLAlchemy
        self._ba_name = business_account.name if business_account else None
        self._ba_account_type = business_account.account_type if business_account else None
        self._ba_target_clients_description = business_account.target_clients_description if business_account else None
        self._ba_product_description = business_account.product_description if business_account else None
        self._ba_industry = business_account.industry if business_account else None
        self._ba_company_description = business_account.company_description if business_account else None
        self._ba_prioritized_topics = _parse_json_list(business_account.prioritized_topics if business_account else None)
        self._ba_conversation_tone = business_account.conversation_tone if business_account else None
        self._ba_max_questions = business_account.max_questions if business_account else None
        self._ba_max_duration_seconds = business_account.max_duration_seconds if business_account else None
        self._ba_custom_end_message = business_account.custom_end_message if business_account else None
        
        # Industry topic hints for prompt verticalization (Phase 2)
        # Parse JSON dict for custom topic hint overrides
        self._ba_industry_topic_hints = None
        if business_account and hasattr(business_account, 'industry_topic_hints') and business_account.industry_topic_hints:
            if isinstance(business_account.industry_topic_hints, dict):
                self._ba_industry_topic_hints = business_account.industry_topic_hints
            elif isinstance(business_account.industry_topic_hints, str):
                try:
                    parsed = json.loads(business_account.industry_topic_hints)
                    if isinstance(parsed, dict):
                        self._ba_industry_topic_hints = parsed
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Determine demo mode based on extracted primitives
        self.is_demo_mode = not (
            (campaign and self._has_campaign_customization_from_primitives()) or 
            (self._ba_account_type and self._ba_account_type != 'demo')
        )
    
    def _has_campaign_customization_from_primitives(self) -> bool:
        """Check if campaign has customization using extracted primitives"""
        return bool(
            self._campaign_product_description or
            self._campaign_target_clients_description or
            (self._campaign_max_questions and self._campaign_max_questions != 8) or
            (self._campaign_max_duration_seconds and self._campaign_max_duration_seconds != 120) or
            self._campaign_prioritized_topics or
            self._campaign_custom_end_message
        )
    
    def _has_customization(self) -> bool:
        """Check if business account or campaign has meaningful customization data"""
        # Check campaign customization first using primitives
        if self._has_campaign_customization_from_primitives():
            return True
            
        # Check business account customization using primitives
        return bool(
            self._ba_industry or
            self._ba_company_description or
            self._ba_product_description or
            self._ba_target_clients_description
        )
    
    def get_company_name(self) -> str:
        """Get company name for survey context (HOT PATH - uses cached primitive)"""
        if self.is_demo_mode:
            return "Archelo Group"
        
        if self._ba_name:
            return self._ba_name
        
        return "Archelo Group"  # Fallback
    
    def get_product_name(self) -> str:
        """Get product/service name for survey context (HOT PATH - uses cached primitives)"""
        if self.is_demo_mode:
            return "ArcheloFlow"
        
        # Check campaign product description first (cached primitive)
        if self._campaign_product_description:
            product_desc = self._campaign_product_description.strip()
            words = product_desc.split()
            if len(words) <= 5:
                return product_desc
            else:
                return " ".join(words[:3]) + "..."
        
        # Fall back to business account product description (cached primitive)
        if self._ba_product_description:
            product_desc = self._ba_product_description.strip()
            words = product_desc.split()
            if len(words) <= 5:
                return product_desc
            else:
                return " ".join(words[:3]) + "..."
        
        # Use company name + "services" as fallback
        company_name = self.get_company_name()
        if company_name != "Archelo Group":
            return f"{company_name} services"
        
        return "ArcheloFlow"  # Ultimate fallback
    
    def has_campaign_customization(self) -> bool:
        """Check if campaign has meaningful customization data (uses cached primitives)"""
        if not self.campaign_id:
            return False
        
        # Check hot path attributes first
        if self._has_campaign_customization_from_primitives():
            return True
        
        # Check cold path attributes (rare, lazy reload)
        campaign = Campaign.query.get(self.campaign_id)
        if not campaign:
            return False
        
        return bool(
            campaign.max_follow_ups_per_topic != 2 or
            campaign.optional_topics or
            campaign.custom_system_prompt
        )
    
    def get_conversation_tone(self) -> str:
        """Get conversation tone setting (HOT PATH - uses cached primitive)"""
        if self.is_demo_mode:
            return "professional"
        
        if self._ba_conversation_tone:
            return self._ba_conversation_tone
        
        return "professional"  # Default
    
    def get_language_code(self) -> str:
        """Get campaign language code for fallback questions (HOT PATH - uses cached primitive)"""
        return self._campaign_language_code
    
    def get_effective_industry(self) -> Optional[str]:
        """Get effective industry for topic hints (HOT PATH - uses cached primitives)
        
        Priority: Campaign.industry > BusinessAccount.industry > "Generic" fallback
        
        Demo mode campaigns can have specific industries set for testing purposes.
        
        Returns:
            Industry name (never None, defaults to "Generic")
        """
        # Campaign industry override takes precedence (cached primitive)
        # Works for both demo and production campaigns
        if self._campaign_industry:
            return self._campaign_industry
        
        # Fall back to business account industry (cached primitive)
        # Demo accounts can have industries set for testing
        if self._ba_industry:
            return self._ba_industry
        
        # Final fallback to Generic for accounts with no industry specified
        return "Generic"
    
    def get_topic_hints_for_industry(self) -> Dict[str, str]:
        """Get merged topic hints combining platform defaults with custom overrides
        
        Architecture:
        - Platform defaults from industry_topic_hints_config.py
        - Custom overrides from BusinessAccount.industry_topic_hints JSON
        - Merged result: custom overrides take precedence
        
        Returns:
            Dict mapping topic names to hint keywords (e.g., {"Product Quality": "defects, throughput"})
        """
        from industry_topic_hints_config import get_industry_hints, merge_custom_hints
        
        industry = self.get_effective_industry()
        
        # Get platform defaults for this industry
        platform_hints = get_industry_hints(industry)
        
        # If no custom hints, return platform defaults
        if not self._ba_industry_topic_hints:
            return platform_hints
        
        # Merge custom hints with platform defaults (custom overrides platform)
        return merge_custom_hints(industry, self._ba_industry_topic_hints)
    
    def get_max_questions(self) -> int:
        """Get maximum questions limit (HOT PATH - uses cached primitives)"""
        if self.is_demo_mode:
            return 8  # Demo default
        
        # Check campaign max questions first (cached primitive)
        if self._campaign_max_questions:
            return self._campaign_max_questions
        
        # Fall back to business account (cached primitive)
        if self._ba_max_questions:
            return self._ba_max_questions
        
        return 8  # Default
    
    def get_max_duration_seconds(self) -> int:
        """Get maximum survey duration in seconds (HOT PATH - uses cached primitives)"""
        if self.is_demo_mode:
            return 120  # 2 minutes default
        
        # Check campaign max duration first (cached primitive)
        if self._campaign_max_duration_seconds:
            return self._campaign_max_duration_seconds
        
        # Fall back to business account (cached primitive)
        if self._ba_max_duration_seconds:
            return self._ba_max_duration_seconds
        
        return 120  # Default
    
    def _select_persona_template(self, participant_data: Optional[Dict[str, Any]] = None, anonymize: bool = False) -> str:
        """
        Get role label for participant based on their role tier
        
        Args:
            participant_data: Dictionary with participant info including role
            anonymize: Whether anonymization is enabled for this campaign
            
        Returns:
            Role label from ROLE_METADATA (e.g., "Manager", "C-level executive")
        """
        # Use default persona if anonymization is enabled OR participant data is missing
        if anonymize or not participant_data:
            return ROLE_METADATA['default']['label']
        
        # Extract role and map to tier
        role = participant_data.get('role')
        tier = _map_role_to_tier(role)
        
        # Get role label from metadata
        return ROLE_METADATA.get(tier, ROLE_METADATA['default'])['label']
    
    def generate_welcome_message(self, respondent_name: str) -> str:
        """Generate personalized welcome message with language and campaign-awareness support
        
        FIX (Dec 11, 2025): Now uses campaign.description to customize survey purpose
        instead of generic "what's working, what's not" messaging.
        """
        company_name = self.get_company_name()
        product_name = self.get_product_name()
        campaign_language = self._campaign_language_code
        
        if self.is_demo_mode:
            # Use original hardcoded message for demo mode
            return f"Hi {respondent_name}, we'd love to hear from you.\n\nArchelo is on a mission to make workplace tools less painful, and your feedback makes us better.\n\nThis short conversation will help us understand what's working, what's not, and how to improve your experience with ArcheloFlow.\n\nOn a scale of 0-10, how likely are you to recommend Archelo Group to a friend or colleague?"
        
        # Generate customized welcome message (uses cached primitive)
        company_description = ""
        if self._ba_company_description:
            company_description = f"\n\n{self._ba_company_description}"
        
        # FIX (Dec 11, 2025): Use campaign description for survey purpose if available
        # This makes the welcome message reflect the actual campaign intent
        survey_purpose = self._get_campaign_aware_survey_purpose(product_name, campaign_language)
        
        # LANGUAGE-AWARE: Generate message in campaign language
        if campaign_language == 'fr':
            # French welcome message
            return f"Bonjour {respondent_name}, nous aimerions connaître votre avis.{company_description}\n\n{survey_purpose}\n\nSur une échelle de 0 à 10, quelle est la probabilité que vous recommandiez {company_name} à un ami ou collègue?"
        else:
            # English welcome message (default)
            return f"Hi {respondent_name}, we'd love to hear from you.{company_description}\n\n{survey_purpose}\n\nOn a scale of 0-10, how likely are you to recommend {company_name} to a friend or colleague?"
    
    def _get_campaign_aware_survey_purpose(self, product_name: str, language: str) -> str:
        """Generate survey purpose statement based on campaign description
        
        FIX (Dec 11, 2025): Uses campaign.description to create a purpose statement
        that reflects the campaign's actual intent (e.g., year-end appreciation,
        product feedback, relationship review).
        
        Args:
            product_name: Product/service name for fallback
            language: Language code ('en', 'fr', etc.)
        
        Returns:
            Survey purpose statement in the appropriate language
        """
        # Check if campaign has a meaningful description
        if self._campaign_description and len(self._campaign_description.strip()) > 10:
            campaign_desc = self._campaign_description.strip()
            
            # Generate purpose based on campaign description
            if language == 'fr':
                return f"Cette conversation s'inscrit dans le cadre de notre initiative : {campaign_desc}. Votre retour est précieux pour nous aider à mieux vous servir."
            else:
                return f"This conversation is part of our initiative: {campaign_desc}. Your feedback is valuable in helping us serve you better."
        
        # Fallback to generic purpose if no campaign description
        if language == 'fr':
            return f"Cette courte conversation nous aidera à comprendre ce qui fonctionne bien, ce qui pourrait être amélioré, et comment optimiser votre expérience avec {product_name}."
        else:
            return f"This short conversation will help us understand what's working, what's not, and how to improve your experience with {product_name}."
    
    def generate_system_prompt(self, extracted_data: Dict[str, Any], step_count: int, conversation_history: str, participant_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate system prompt for OpenAI conversation with hybrid prompt support"""
        import os
        
        # Feature flag for hybrid prompt architecture
        use_hybrid_prompt = os.getenv('VOIA_USE_HYBRID_PROMPT', 'false').lower() == 'true'
        
        if use_hybrid_prompt:
            return self._generate_hybrid_prompt(extracted_data, step_count, conversation_history, participant_data)
        else:
            return self._generate_legacy_prompt(extracted_data, step_count, conversation_history)
    
    def _generate_hybrid_prompt(self, extracted_data: Dict[str, Any], step_count: int, conversation_history: str, participant_data: Optional[Dict[str, Any]] = None) -> str:
        """Generate hybrid prompt with universal parameterized sections and explicit goal enumeration"""
        survey_config = self.build_survey_config_json(participant_data)
        
        # Get universal parameters
        company_name = survey_config['company_name']
        conversation_tone = survey_config['conversation_tone'] or 'professional'
        max_questions = survey_config['max_questions']
        campaign_language = self._campaign_language_code or 'en'
        
        # Get participant role label for context
        anonymize = self._campaign_anonymize_responses
        role_label = self._select_persona_template(participant_data, anonymize)
        
        # Universal opening statement
        universal_opening = f"""You are VOÏA, an AI-powered customer feedback specialist conducting a survey for {company_name}.

You are speaking with a {role_label} at {company_name}."""
        
        # Universal language instruction with comprehensive language mapping
        language_instruction = ""
        if campaign_language and campaign_language != 'en':
            # Comprehensive language mapping for all supported locales
            language_map = {
                'fr': 'French',
                'es': 'Spanish',
                'de': 'German',
                'pt': 'Portuguese',
                'it': 'Italian',
                'nl': 'Dutch',
                'pl': 'Polish',
                'ru': 'Russian',
                'zh': 'Chinese',
                'ja': 'Japanese',
                'ko': 'Korean',
                'ar': 'Arabic'
            }
            language_name = language_map.get(campaign_language)
            
            if not language_name:
                # Log unsupported language and default to campaign code
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Unsupported campaign language code: {campaign_language}. Using code directly.")
                language_name = campaign_language.upper()
            
            language_instruction = f"\n\nIMPORTANT: Conduct this entire conversation in {language_name}. Ask questions and respond in {language_name}."
        
        # Universal tone instruction
        tone_instruction = f"\n\nUse {conversation_tone} tone throughout the conversation."
        
        # Build dynamic context usage section (only include available fields)
        context_fields = [f"- Company: {company_name}"]
        
        if survey_config.get('context'):
            context = survey_config['context']
            if context.get('industry'):
                context_fields.append(f"- Industry: {context['industry']}")
            if context.get('product_description'):
                context_fields.append(f"- Product: {context['product_description']}")
            if context.get('target_clients'):
                context_fields.append(f"- Target clients: {context['target_clients']}")
        
        if survey_config.get('participant_profile'):
            profile = survey_config['participant_profile']
            if profile.get('role'):
                context_fields.append(f"- Participant role: {profile['role']}")
            if profile.get('customer_tier'):
                context_fields.append(f"- Customer tier: {profile['customer_tier']}")
        
        context_usage_section = f"""
==========================
CONTEXT USAGE
==========================

Use the following context to personalize examples or framing:
{chr(10).join(context_fields)}

IMPORTANT: Use context for relevance, not verbosity. Never restate long descriptions.
"""
        
        # Build explicit SURVEY GOALS section with descriptions, field mappings, and industry hints
        goals_section = """
==========================
SURVEY GOALS
==========================

Complete these goals in priority order. For each goal, collect the specified fields:

"""
        for goal in survey_config['goals']:
            # Build field list
            fields_list = ", ".join(goal['fields'])
            
            # Add industry hint if present
            hint_info = ""
            if goal.get('industry_hint'):
                hint_info = f"\n     [Industry focus: {goal['industry_hint']}]"
            
            goals_section += f"""  {goal['priority']}. {goal['topic']}: {goal['description']}
     Fields to collect: {fields_list}{hint_info}

"""
        
        # Format universal guidelines with parameters (only tone and max_questions)
        guidelines_formatted = UNIVERSAL_GUIDELINES.format(
            tone=conversation_tone,
            max_questions=max_questions
        )
        
        return f"""SURVEY CONFIGURATION:
{json.dumps(survey_config, indent=2)}

CONVERSATION HISTORY:
{conversation_history}

SURVEY DATA COLLECTED SO FAR:
{json.dumps(extracted_data, indent=2)}

CONVERSATION STEP: {step_count} / {max_questions}

{universal_opening}{tone_instruction}
{context_usage_section}{goals_section}{guidelines_formatted}

{language_instruction}"""
    
    def _generate_legacy_prompt(self, extracted_data: Dict[str, Any], step_count: int, conversation_history: str) -> str:
        """Generate legacy system prompt (current implementation)"""
        company_name = self.get_company_name()
        product_name = self.get_product_name()
        tone = self.get_conversation_tone()
        
        if self.is_demo_mode:
            # Use original hardcoded prompt for demo mode
            return self._get_demo_system_prompt(extracted_data, step_count, conversation_history)
        
        # Generate customized system prompt (uses cached primitives)
        business_context = ""
        if self._ba_industry:
            business_context += f"\n- Industry: {self._ba_industry}"
        if self._ba_target_clients_description:
            business_context += f"\n- Target Clients: {self._ba_target_clients_description}"
        
        prioritized_topics = self._get_prioritized_topics()
        
        # Language instruction based on campaign language
        campaign_language = self._campaign_language_code
        language_instruction = ""
        if campaign_language and campaign_language != 'en':
            language_map = {'fr': 'French', 'es': 'Spanish', 'de': 'German'}
            language_name = language_map.get(campaign_language, campaign_language.upper())
            language_instruction = f"\n\nIMPORTANT: Conduct this entire conversation in {language_name}. Ask questions and respond in {language_name}."
        
        return f"""You are conducting a customer feedback survey about {company_name} (the supplier company). Focus on {company_name}'s service delivery, support quality, and business relationship aspects.

BUSINESS CONTEXT:{business_context}

CONVERSATION HISTORY:
{conversation_history}

SURVEY DATA COLLECTED SO FAR:
{json.dumps(extracted_data, indent=2)}

CONVERSATION STEP: {step_count}

YOUR ROLE: You are a helpful customer feedback specialist having a natural, {tone} conversation. Your goal is to collect feedback about {company_name}:
{prioritized_topics}{language_instruction}

GUIDELINES:
- Keep the conversation natural and engaging
- Use a {tone} tone throughout
- Ask ONE question at a time
- Before asking any question, check if the data has already been collected. Only ask for missing fields.
- Reference their previous responses to show you're listening
- If they mention specific issues, dig deeper with follow-up questions
- Keep questions focused on {company_name}'s performance and relationship

RESPONSE FORMAT: Return only the next question or response. No system messages or explanations."""
    
    def _get_demo_system_prompt(self, extracted_data: Dict[str, Any], step_count: int, conversation_history: str) -> str:
        """Get original hardcoded system prompt for demo mode"""
        return f"""You are conducting a customer feedback survey about Archelo Group (the supplier company). Focus on Archelo Group's service delivery, support quality, and business relationship aspects.

CONVERSATION HISTORY:
{conversation_history}

SURVEY DATA COLLECTED SO FAR:
{json.dumps(extracted_data, indent=2)}

CONVERSATION STEP: {step_count}

YOUR ROLE: You are a helpful customer feedback specialist having a natural conversation. Your goal is to collect feedback about Archelo Group:
1. Business relationship tenure - How long working with Archelo Group
2. NPS score (0-10) - How likely to recommend Archelo Group
3. Reason for their NPS score about Archelo Group
4. Satisfaction level (1-5) - Overall satisfaction with Archelo Group
5. Professional services quality rating (1-5) - Quality of Archelo Group's professional services
6. Product value rating (1-5) - Value and quality of Archelo Group's products/solutions
7. Pricing appreciation rating (1-5) - How they feel about Archelo Group's pricing value
8. Support services rating (1-5) - Quality of Archelo Group's support and customer service
9. Improvement suggestions - What could Archelo Group do better
10. Additional feedback - Any other comments about Archelo Group

GUIDELINES:
- Keep the conversation natural and engaging
- Ask ONE question at a time
- Before asking any question, check if the data has already been collected. Only ask for missing fields.
- Reference their previous responses to show you're listening
- If they mention specific issues, dig deeper with follow-up questions
- Keep questions focused on Archelo Group's performance and relationship

RESPONSE FORMAT: Return only the next question or response. No system messages or explanations."""
    
    def _get_prioritized_topics(self) -> str:
        """Get prioritized survey topics with industry-specific hints injected - campaign data takes precedence"""
        company_name = self.get_company_name()
        
        # Phase 2: Get industry topic hints for prompt verticalization
        topic_hints = self.get_topic_hints_for_industry()
        
        base_topics = [
            f"1. Business relationship tenure - How long working with {company_name}",
            f"2. NPS score (0-10) - How likely to recommend {company_name}",
            f"3. Reason for their NPS score about {company_name}",
            f"4. Satisfaction level (1-5) - Overall satisfaction with {company_name}",
            f"5. Professional services quality rating (1-5) - Quality of {company_name}'s professional services",
            f"6. Product value rating (1-5) - Value and quality of {company_name}'s products/solutions",
            f"7. Pricing appreciation rating (1-5) - How they feel about {company_name}'s pricing value",
            f"8. Support services rating (1-5) - Quality of {company_name}'s support and customer service",
            f"9. Improvement suggestions - What could {company_name} do better",
            f"10. Additional feedback - Any other comments about {company_name}"
        ]
        
        # Check campaign prioritized topics first (cached primitive)
        if not self.is_demo_mode and self._campaign_prioritized_topics:
            custom_topics = []
            for i, topic in enumerate(self._campaign_prioritized_topics[:10], 1):
                # Inject industry hints if available for this topic
                topic_with_hint = self._inject_topic_hint(topic, topic_hints)
                custom_topics.append(f"{i}. {topic_with_hint}")
            
            # Merge with base topics, prioritizing custom ones
            remaining_base = base_topics[len(custom_topics):]
            all_topics = custom_topics + remaining_base
            return "\n".join(all_topics[:10])  # Max 10 topics
        
        # Fall back to business account prioritized topics (cached primitive)
        if not self.is_demo_mode and self._ba_prioritized_topics:
            custom_topics = []
            for i, topic in enumerate(self._ba_prioritized_topics[:10], 1):
                # Inject industry hints if available for this topic
                topic_with_hint = self._inject_topic_hint(topic, topic_hints)
                custom_topics.append(f"{i}. {topic_with_hint}")
            
            # Merge with base topics, prioritizing custom ones
            remaining_base = base_topics[len(custom_topics):]
            all_topics = custom_topics + remaining_base
            return "\n".join(all_topics[:10])  # Max 10 topics
        
        return "\n".join(base_topics)
    
    def _inject_topic_hint(self, topic: str, topic_hints: Dict[str, str]) -> str:
        """Inject industry-specific hint keywords into topic description
        
        Args:
            topic: Original topic name (e.g., "Product Quality")
            topic_hints: Dict mapping topics to hint keywords
        
        Returns:
            Topic with hint injected if available (e.g., "Product Quality (focus on: defects, throughput)")
            or original topic if no hint available
        """
        # Check if we have a hint for this topic
        hint = topic_hints.get(topic, "")
        
        if hint:
            # Inject hint in parentheses with "focus on:" prefix
            return f"{topic} (focus on: {hint})"
        
        return topic
    
    def get_completion_message(self) -> str:
        """Get survey completion message - campaign data takes precedence"""
        company_name = self.get_company_name()
        
        if self.is_demo_mode:
            return "Thank you so much for taking the time to share your detailed feedback about Archelo Group! Your insights are incredibly valuable and will help us improve our service delivery. Have a wonderful day!"
        
        # Check campaign custom end message first (cached primitive)
        if self._campaign_custom_end_message:
            return self._campaign_custom_end_message
        
        # Fall back to business account custom end message (cached primitive)
        if self._ba_custom_end_message:
            return self._ba_custom_end_message
        
        return f"Thank you so much for taking the time to share your detailed feedback about {company_name}! Your insights are incredibly valuable and will help us improve our service delivery. Have a wonderful day!"
    
    def _build_prioritized_topics_with_fields(self) -> List[Dict[str, Any]]:
        """
        Build prioritized topics with database field mappings for hybrid prompt architecture.
        
        V2 ENHANCEMENT (Nov 23, 2025): Now returns is_required metadata for deterministic flow.
        - Topics in campaign.prioritized_topics = is_required=True (must-ask)
        - Topics in campaign.optional_topics = is_required=False (best-effort)
        - Default base topics = is_required based on position (first 2 are must-ask)
        """
        company_name = self.get_company_name()
        
        # Define base topics with field mappings
        base_topics_map = [
            {"topic": "Business Relationship Tenure", "description": f"How long working with {company_name}", "fields": TOPIC_FIELD_MAP["Business Relationship Tenure"]},
            {"topic": "NPS", "description": f"How likely to recommend {company_name} (0-10 scale)", "fields": TOPIC_FIELD_MAP["NPS"]},
            {"topic": "Overall Satisfaction", "description": f"Overall satisfaction with {company_name} (1-5 scale)", "fields": TOPIC_FIELD_MAP["Overall Satisfaction"]},
            {"topic": "Professional Services Quality", "description": f"Quality of {company_name}'s professional services (1-5 scale)", "fields": TOPIC_FIELD_MAP["Professional Services Quality"]},
            {"topic": "Product Value", "description": f"Value and quality of {company_name}'s products/solutions (1-5 scale)", "fields": TOPIC_FIELD_MAP["Product Value"]},
            {"topic": "Pricing Value", "description": f"How they feel about {company_name}'s pricing value (1-5 scale)", "fields": TOPIC_FIELD_MAP["Pricing Value"]},
            {"topic": "Support Quality", "description": f"Quality of {company_name}'s support and customer service (1-5 scale)", "fields": TOPIC_FIELD_MAP["Support Quality"]},
            {"topic": "Improvement Suggestions", "description": f"What could {company_name} do better", "fields": TOPIC_FIELD_MAP["Improvement Suggestions"]},
            {"topic": "Additional Feedback", "description": f"Any other comments about {company_name}", "fields": TOPIC_FIELD_MAP["Additional Feedback"]}
        ]
        
        # V2 ENHANCEMENT: Get optional topics list from campaign (cached primitive)
        campaign_optional_topics = self._campaign_optional_topics if not self.is_demo_mode else []
        
        # Check campaign prioritized topics first (cached primitive)
        if not self.is_demo_mode and self._campaign_prioritized_topics:
            # Map custom topics to field mappings where possible
            custom_topics = []
            for topic_name in self._campaign_prioritized_topics[:10]:
                # Try to find matching base topic for field mapping
                matched = next((t for t in base_topics_map if topic_name.lower() in t["topic"].lower() or t["topic"].lower() in topic_name.lower()), None)
                
                # V2 ENHANCEMENT: Topics in prioritized_topics are REQUIRED (must-ask)
                if matched:
                    custom_topics.append({
                        "topic": topic_name, 
                        "description": matched["description"], 
                        "fields": matched["fields"],
                        "is_required": True  # Prioritized topics are must-ask
                    })
                else:
                    # Use generic mapping for unknown topics
                    custom_topics.append({
                        "topic": topic_name, 
                        "description": topic_name, 
                        "fields": ["improvement_feedback"],
                        "is_required": True  # Prioritized topics are must-ask
                    })
            
            # Add optional topics if configured
            if campaign_optional_topics:
                for topic_name in campaign_optional_topics[:5]:  # Max 5 optional topics
                    # Try to find matching base topic for field mapping
                    matched = next((t for t in base_topics_map if topic_name.lower() in t["topic"].lower() or t["topic"].lower() in topic_name.lower()), None)
                    
                    if matched:
                        custom_topics.append({
                            "topic": topic_name,
                            "description": matched["description"],
                            "fields": matched["fields"],
                            "is_required": False  # Optional topics are best-effort
                        })
                    else:
                        custom_topics.append({
                            "topic": topic_name,
                            "description": topic_name,
                            "fields": ["improvement_feedback"],
                            "is_required": False  # Optional topics are best-effort
                        })
            
            # Merge with base topics if needed to fill out list
            # CRITICAL FIX: Filter bi-directionally to prevent duplicates (e.g., "NPS" and "NPS Score")
            used_base_topics = [
                t for t in base_topics_map 
                if not any(
                    ct["topic"].lower() in t["topic"].lower() or t["topic"].lower() in ct["topic"].lower() 
                    for ct in custom_topics
                )
            ]
            
            # Fill remaining slots with base topics (mark as optional if we already have 2+ required topics)
            remaining_slots = 10 - len(custom_topics)
            has_enough_required = sum(1 for t in custom_topics if t.get("is_required", False)) >= 2
            
            for base_topic in used_base_topics[:remaining_slots]:
                custom_topics.append({
                    **base_topic,
                    "is_required": not has_enough_required  # First 2 base topics are required, rest optional
                })
                if not has_enough_required and custom_topics[-1]["is_required"]:
                    has_enough_required = sum(1 for t in custom_topics if t.get("is_required", False)) >= 2
            
            all_topics = custom_topics
        else:
            # Demo mode or no custom topics - use base topics with first 2 as required
            all_topics = []
            for i, base_topic in enumerate(base_topics_map[:10]):
                all_topics.append({
                    **base_topic,
                    "is_required": i < 2  # First 2 topics (Tenure, NPS) are must-ask
                })
        
        # Add priority order
        for i, topic in enumerate(all_topics, 1):
            topic["priority"] = i
        
        return all_topics
    
    def build_survey_config_json(self, participant_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build structured survey configuration JSON for hybrid prompt architecture with rich context"""
        company_name = self.get_company_name()
        
        # Build participant profile if data provided
        # CRITICAL FIX: Do NOT include participant language - campaign language always takes precedence
        participant_profile = None
        if participant_data:
            participant_profile = {
                "name": participant_data.get("name"),
                "email": participant_data.get("email"),
                "company": participant_data.get("company_name"),
                "role": participant_data.get("role"),
                "region": participant_data.get("region"),
                "customer_tier": participant_data.get("customer_tier")
            }
        
        # Build context block with campaign overrides (uses cached primitives)
        context = {}
        
        # Company description (business account only - cached primitive)
        if self._ba_company_description:
            context['company_description'] = self._ba_company_description
        
        # Product description (campaign overrides business account - cached primitives)
        product_desc = self._campaign_product_description or self._ba_product_description
        if product_desc:
            context['product_description'] = product_desc
        
        # Target clients (campaign overrides business account - cached primitives)
        target_clients = self._campaign_target_clients_description or self._ba_target_clients_description
        if target_clients:
            context['target_clients'] = target_clients
        
        # Industry (uses effective industry with campaign override support)
        effective_industry = self.get_effective_industry()
        if effective_industry:
            context['industry'] = effective_industry
        
        # Build goals with industry-specific hints integrated
        goals = self._build_prioritized_topics_with_fields()
        
        # Apply role-based goal filtering if participant data is provided
        if participant_data:
            participant_role = participant_data.get('role')
            role_tier = _map_role_to_tier(participant_role)
            
            # Extract topic names from goals for filtering
            goal_topics = [goal.get('topic', '') for goal in goals]
            
            # Filter topics based on role exclusions
            filtered_topics = filter_goals_by_role(goal_topics, role_tier)
            
            # Keep only goals whose topics are in the filtered list, maintaining priority order
            goals = [goal for goal in goals if goal.get('topic', '') in filtered_topics]
            
            # Re-assign priority numbers after filtering
            for i, goal in enumerate(goals, 1):
                goal['priority'] = i
        
        # Get industry topic hints and merge them into goal objects
        topic_hints = self.get_topic_hints_for_industry()
        if topic_hints:
            for goal in goals:
                topic_name = goal.get('topic', '')
                # Look for matching hint (case-insensitive partial match)
                matching_hint = None
                for hint_topic, hint_keywords in topic_hints.items():
                    if hint_topic.lower() in topic_name.lower() or topic_name.lower() in hint_topic.lower():
                        matching_hint = hint_keywords
                        break
                
                if matching_hint:
                    goal['industry_hint'] = matching_hint
        
        # Build survey configuration
        config = {
            "goals": goals,
            "max_questions": self.get_max_questions(),
            "max_duration_seconds": self.get_max_duration_seconds(),
            "conversation_tone": self.get_conversation_tone(),
            "company_name": company_name,
            "context": context,
            "participant_profile": participant_profile
        }
        
        return config
    
    def get_effective_survey_config(self) -> Dict[str, Any]:
        """Get merged survey configuration from campaign and business account data"""
        return {
            'company_name': self.get_company_name(),
            'product_name': self.get_product_name(),
            'conversation_tone': self.get_conversation_tone(),
            'max_questions': self.get_max_questions(),
            'max_duration_seconds': self.get_max_duration_seconds(),
            'completion_message': self.get_completion_message(),
            'prioritized_topics': self._get_prioritized_topics(),
            'is_demo_mode': self.is_demo_mode,
            'has_campaign_customization': self.has_campaign_customization(),
            'has_business_customization': self._has_customization(),
            'campaign_id': self.campaign_id,
            'business_account_id': self.business_account_id,
            # Optional campaign-specific fields (uses cached primitives + COLD PATH lazy reload for rare fields)
            'target_clients_description': self._campaign_target_clients_description or self._ba_target_clients_description,
            'max_follow_ups_per_topic': self._get_cold_path_max_follow_ups(),
            'optional_topics': self._get_cold_path_optional_topics(),
            'custom_system_prompt': self._get_cold_path_custom_system_prompt()
        }
    
    def _get_cold_path_max_follow_ups(self) -> int:
        """COLD PATH: Lazy reload for rarely-accessed max_follow_ups_per_topic attribute"""
        if self.campaign_id:
            campaign = Campaign.query.get(self.campaign_id)
            if campaign and campaign.max_follow_ups_per_topic:
                return campaign.max_follow_ups_per_topic
        if self.business_account_id:
            ba = BusinessAccount.query.get(self.business_account_id)
            if ba and hasattr(ba, 'max_follow_ups_per_topic') and ba.max_follow_ups_per_topic:
                return ba.max_follow_ups_per_topic
        return 2  # Default
    
    def _get_cold_path_optional_topics(self) -> Optional[list]:
        """COLD PATH: Lazy reload for rarely-accessed optional_topics attribute"""
        if self.campaign_id:
            campaign = Campaign.query.get(self.campaign_id)
            if campaign and campaign.optional_topics:
                return campaign.optional_topics
        if self.business_account_id:
            ba = BusinessAccount.query.get(self.business_account_id)
            if ba and hasattr(ba, 'optional_topics') and ba.optional_topics:
                return ba.optional_topics
        return None
    
    def _get_cold_path_custom_system_prompt(self) -> Optional[str]:
        """COLD PATH: Lazy reload for rarely-accessed custom_system_prompt attribute"""
        if self.campaign_id:
            campaign = Campaign.query.get(self.campaign_id)
            if campaign and campaign.custom_system_prompt:
                return campaign.custom_system_prompt
        return None
    
    def should_force_completion(self, step_count: int) -> bool:
        """Check if survey should be force-completed based on limits"""
        max_questions = self.get_max_questions()
        return step_count > max_questions
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get template configuration info for debugging - includes campaign and business account data"""
        info = {
            'is_demo_mode': self.is_demo_mode,
            'business_account_id': self.business_account_id,
            'campaign_id': self.campaign_id,
            'company_name': self.get_company_name(),
            'product_name': self.get_product_name(),
            'conversation_tone': self.get_conversation_tone(),
            'max_questions': self.get_max_questions(),
            'max_duration_seconds': self.get_max_duration_seconds(),
            'has_business_customization': self._has_customization(),
            'has_campaign_customization': self.has_campaign_customization(),
            'data_source_priority': 'campaign -> business_account -> demo',
            'campaign_exists': self.campaign_id is not None,
            'business_account_exists': self.business_account_id is not None
        }
        
        # Add campaign-specific debug info if available (COLD PATH - lazy reload for debug only)
        if self.campaign_id:
            campaign = Campaign.query.get(self.campaign_id)
            if campaign:
                info['campaign_info'] = {
                    'name': campaign.name,
                    'status': campaign.status,
                    'has_product_description': bool(self._campaign_product_description),
                    'has_custom_end_message': bool(self._campaign_custom_end_message),
                    'has_prioritized_topics': bool(self._campaign_prioritized_topics)
                }
        
        # Add business account debug info if available (uses cached primitives)
        if self.business_account_id:
            info['business_account_info'] = {
                'name': self._ba_name,
                'account_type': self._ba_account_type or 'unknown',
                'has_product_description': bool(self._ba_product_description),
                'has_conversation_tone': bool(self._ba_conversation_tone)
            }
        
        return info