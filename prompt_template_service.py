"""
Prompt Template Service for VOÏA Conversational Surveys
Handles dynamic prompt generation based on BusinessAccount customization settings
Supports dual-mode operation: demo (hardcoded) vs customer (customized)
Hybrid Prompt Architecture: Structured JSON configuration + conversation guidance
"""

import json
from typing import Dict, Any, Optional, List
from models import BusinessAccount, Campaign

# Topic-to-Field Mapping for AI Response Validation and Analytics
TOPIC_FIELD_MAP = {
    "NPS": ["nps_score", "nps_reasoning"],
    "Business Relationship Tenure": ["tenure_with_fc"],
    "Overall Satisfaction": ["satisfaction_rating"],
    "Professional Services Quality": ["service_rating"],
    "Product Value": ["product_value_rating"],
    "Pricing Value": ["pricing_rating"],
    "Support Quality": ["support_rating"],
    "Improvement Suggestions": ["improvement_feedback"],
    "Additional Feedback": ["additional_comments"]
}

# Role-Based Persona Templates for Conversational Surveys
# These personas adapt the AI's tone and focus based on participant seniority
PERSONA_TEMPLATES = {
    'c_level': """You are VOÏA, an AI-powered feedback agent. You're speaking with a C-level executive at one of {business_account_name}'s client organizations.

Your role is to lead a strategic, respectful conversation focused on the executive's perception of {business_account_name}'s overall value, trust, alignment with business goals, and ROI.

Use a concise, professional tone. Prioritize high-level themes like:
- Business impact
- Relationship strength
- Pricing justification
- Roadmap alignment
- Renewal confidence

Avoid detailed product questions unless raised by the executive. Be mindful of their time and keep the conversation efficient.""",
    
    'vp_director': """You are VOÏA, a feedback specialist speaking with a senior leader (VP or Director) who oversees operations related to {business_account_name}'s products or services.

Focus the conversation on:
- Adoption and performance of the solution
- Internal feedback from their teams
- Ease of collaboration with {business_account_name}
- Perceived value and strategic alignment

Maintain a professional tone with space for nuance. Invite constructive feedback and let them expand where needed. Highlight how their insights shape future improvements.""",
    
    'manager': """You are VOÏA, gathering feedback from a manager directly responsible for teams using {business_account_name}'s solutions.

Keep the conversation operational and practical:
- How the product/service performs day to day
- Feedback received from their team
- Responsiveness of {business_account_name}'s support or delivery teams
- Specific frictions or wins in the collaboration

Maintain a professional but personable tone. Use their answers to explore real-world usage, friction points, and overall satisfaction.""",
    
    'team_lead': """You are VOÏA, collecting feedback from a team lead or supervisor who supports users of {business_account_name}'s product or services.

Your conversation should focus on:
- Day-to-day usability
- Training/support experience
- Integration with team workflows
- Communication with {business_account_name}'s reps

Use accessible language. Be encouraging and non-technical. Give space for honest input about what works well and what doesn't.""",
    
    'end_user': """You are VOÏA, a friendly AI assistant asking for feedback from someone who uses {business_account_name}'s product or service in their day-to-day work.

Keep the tone conversational and clear. Focus on:
- What they like or dislike about the tool/service
- Ease of use
- Any frustrations or suggestions
- Whether they'd recommend it to others in their role

Avoid jargon or business terms. Make them feel heard and valued as the people who experience the product most directly.""",
    
    'default': """You are VOÏA, an AI-powered customer feedback specialist conducting a survey for {business_account_name}.

Your role is to lead a natural, conversational dialogue focused on gathering strategic feedback about the client's experience and satisfaction with {business_account_name}'s products or services.

Maintain a professional yet approachable tone. Adapt your focus based on the participant's responses and ensure they feel heard throughout the conversation."""
}


def _map_role_to_tier(role_string: Optional[str]) -> str:
    """
    Map participant role to persona tier with normalized matching
    
    Args:
        role_string: Raw role string from participant data
        
    Returns:
        Persona tier key (c_level, vp_director, manager, team_lead, end_user, default)
    """
    if not role_string:
        return 'end_user'  # Conservative default when role is missing
    
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
    
    def __init__(self, business_account_id: Optional[int] = None, campaign_id: Optional[int] = None):
        """
        Initialize prompt template service with hybrid business+campaign data support
        
        SOLUTION 4 (Hybrid Hot/Cold Path):
        - Hot path attributes (high frequency): Extracted to primitives at init (no session issues)
        - Cold path attributes (rare): Lazy-loaded via ID lookup when needed
        
        Args:
            business_account_id: ID of business account for customized prompts, 
                               None for demo mode
            campaign_id: ID of campaign for campaign-specific customization,
                        takes precedence over business account data
        """
        # Store IDs for cold path lazy reload
        self.business_account_id = business_account_id
        self.campaign_id = campaign_id
        
        # Load ORM objects ONCE for hot path extraction
        campaign = None
        business_account = None
        
        if campaign_id:
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
        
        if business_account_id:
            business_account = BusinessAccount.query.get(business_account_id)
        
        # === HOT PATH: Extract frequently-accessed attributes as primitives ===
        # These are accessed 2+ times or critical for hybrid prompt mode
        
        # Campaign hot path attributes (8 attributes)
        self._campaign_prioritized_topics = list(campaign.prioritized_topics) if campaign and campaign.prioritized_topics else None
        self._campaign_product_description = campaign.product_description if campaign else None
        self._campaign_survey_goals = list(campaign.survey_goals) if campaign and campaign.survey_goals else None
        self._campaign_target_clients_description = campaign.target_clients_description if campaign else None
        self._campaign_max_questions = campaign.max_questions if campaign else None
        self._campaign_max_duration_seconds = campaign.max_duration_seconds if campaign else None
        self._campaign_custom_end_message = campaign.custom_end_message if campaign else None
        self._campaign_anonymize_responses = campaign.anonymize_responses if campaign else False
        
        # BusinessAccount hot path attributes (11 attributes)
        self._ba_name = business_account.name if business_account else None
        self._ba_account_type = business_account.account_type if business_account else None
        self._ba_target_clients_description = business_account.target_clients_description if business_account else None
        self._ba_product_description = business_account.product_description if business_account else None
        self._ba_industry = business_account.industry if business_account else None
        self._ba_company_description = business_account.company_description if business_account else None
        self._ba_survey_goals = list(business_account.survey_goals) if business_account and business_account.survey_goals else None
        self._ba_prioritized_topics = list(business_account.prioritized_topics) if business_account and business_account.prioritized_topics else None
        self._ba_conversation_tone = business_account.conversation_tone if business_account else None
        self._ba_max_questions = business_account.max_questions if business_account else None
        self._ba_max_duration_seconds = business_account.max_duration_seconds if business_account else None
        self._ba_custom_end_message = business_account.custom_end_message if business_account else None
        
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
            self._campaign_survey_goals or
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
    
    def get_survey_goals(self) -> list:
        """Get survey goals/objectives (HOT PATH - uses cached primitives)"""
        if self.is_demo_mode:
            return [
                "Understand customer satisfaction with Archelo Group",
                "Identify areas for service improvement",
                "Measure likelihood to recommend our solutions"
            ]
        
        # Check campaign survey goals first (cached primitive)
        if self._campaign_survey_goals:
            return self._campaign_survey_goals
        
        # Fall back to business account survey goals (cached primitive)
        if self._ba_survey_goals:
            return self._ba_survey_goals
        
        # Generate goals based on company info
        company_name = self.get_company_name()
        return [
            f"Understand customer satisfaction with {company_name}",
            "Identify areas for service improvement",
            f"Measure likelihood to recommend {company_name}"
        ]
    
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
        Select appropriate persona template based on participant role
        
        Args:
            participant_data: Dictionary with participant info including role
            anonymize: Whether anonymization is enabled for this campaign
            
        Returns:
            Formatted persona template with business account name substituted
        """
        business_name = self.get_company_name()
        
        # Use default persona if anonymization is enabled OR participant data is missing
        if anonymize or not participant_data:
            return PERSONA_TEMPLATES['default'].format(business_account_name=business_name)
        
        # Extract role and map to tier
        role = participant_data.get('role')
        tier = _map_role_to_tier(role)
        
        # Get persona template and substitute business name
        persona_template = PERSONA_TEMPLATES.get(tier, PERSONA_TEMPLATES['default'])
        return persona_template.format(business_account_name=business_name)
    
    def generate_welcome_message(self, respondent_name: str) -> str:
        """Generate personalized welcome message"""
        company_name = self.get_company_name()
        product_name = self.get_product_name()
        
        if self.is_demo_mode:
            # Use original hardcoded message for demo mode
            return f"Hi {respondent_name}, we'd love to hear from you.\n\nArchelo is on a mission to make workplace tools less painful, and your feedback makes us better.\n\nThis short conversation will help us understand what's working, what's not, and how to improve your experience with ArcheloFlow.\n\nOn a scale of 0-10, how likely are you to recommend Archelo Group to a friend or colleague?"
        
        # Generate customized welcome message (uses cached primitive)
        company_description = ""
        if self._ba_company_description:
            company_description = f"\n\n{self._ba_company_description}"
        
        survey_purpose = f"This short conversation will help us understand what's working, what's not, and how to improve your experience with {product_name}."
        
        return f"Hi {respondent_name}, we'd love to hear from you.{company_description}\n\n{survey_purpose}\n\nOn a scale of 0-10, how likely are you to recommend {company_name} to a friend or colleague?"
    
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
        """Generate hybrid prompt with structured JSON configuration and conversation guidance"""
        survey_config = self.build_survey_config_json(participant_data)
        
        # Check if anonymization is enabled for this campaign (uses cached primitive)
        anonymize = self._campaign_anonymize_responses
        
        # Select role-based persona template
        persona_intro = self._select_persona_template(participant_data, anonymize)
        
        # Get participant language for response
        participant_language = 'en'  # Default to English
        if participant_data and participant_data.get('language'):
            participant_language = participant_data.get('language')
        
        # Language instruction based on participant preference
        language_instruction = ""
        if participant_language and participant_language != 'en':
            language_map = {'fr': 'French', 'es': 'Spanish'}
            language_name = language_map.get(participant_language, participant_language)
            language_instruction = f"\n\nIMPORTANT: Conduct this entire conversation in {language_name}. Ask questions and respond in {language_name}."
        
        # Build participant profile section
        participant_section = ""
        if survey_config.get("participant_profile"):
            profile = survey_config["participant_profile"]
            participant_section = f"""
PARTICIPANT PROFILE:
- Name: {profile.get('name')}
- Role: {profile.get('role') or 'Not specified'}
- Region: {profile.get('region') or 'Not specified'}
- Customer Tier: {profile.get('customer_tier') or 'Not specified'}
- Language: {profile.get('language', 'en')}
- Company: {profile.get('company')}
"""
        
        # Build goals section with field mappings
        goals_text = ""
        for goal in survey_config['goals']:
            goals_text += f"  {goal['priority']}. {goal['topic']}: {goal['description']}\n"
        
        return f"""SURVEY CONFIGURATION:
{json.dumps(survey_config, indent=2)}
{participant_section}
CONVERSATION HISTORY:
{conversation_history}

SURVEY DATA COLLECTED SO FAR:
{json.dumps(extracted_data, indent=2)}

CONVERSATION STEP: {step_count} / {survey_config['max_questions']}

{persona_intro}{language_instruction}

Your responsibilities:
1. Follow SURVEY CONFIGURATION.goals priorities strictly - always work through topics in priority order
2. Ask ONE question at a time in a {survey_config['conversation_tone']} conversational style
3. Select the highest-priority remaining topic from goals list - only ask about details that are still missing
4. Stop when max_questions ({survey_config['max_questions']}) is reached
5. Before asking any question, check if the data has already been collected. Only ask for missing fields.

Be empathetic, adapt to user communication style, and keep the conversation natural while respecting all constraints.

RESPONSE FORMAT: Return JSON with fields: message, message_type, step, topic, progress, is_complete"""
    
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
        
        return f"""You are conducting a customer feedback survey about {company_name} (the supplier company). Focus on {company_name}'s service delivery, support quality, and business relationship aspects.

BUSINESS CONTEXT:{business_context}

CONVERSATION HISTORY:
{conversation_history}

SURVEY DATA COLLECTED SO FAR:
{json.dumps(extracted_data, indent=2)}

CONVERSATION STEP: {step_count}

YOUR ROLE: You are a helpful customer feedback specialist having a natural, {tone} conversation. Your goal is to collect feedback about {company_name}:
{prioritized_topics}

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
        """Get prioritized survey topics - campaign data takes precedence"""
        company_name = self.get_company_name()
        
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
            for i, topic in enumerate(self._campaign_prioritized_topics[:5], 1):
                custom_topics.append(f"{i}. {topic}")
            
            # Merge with base topics, prioritizing custom ones
            remaining_base = base_topics[len(custom_topics):]
            all_topics = custom_topics + remaining_base
            return "\n".join(all_topics[:10])  # Max 10 topics
        
        # Fall back to business account prioritized topics (cached primitive)
        if not self.is_demo_mode and self._ba_prioritized_topics:
            custom_topics = []
            for i, topic in enumerate(self._ba_prioritized_topics[:5], 1):
                custom_topics.append(f"{i}. {topic}")
            
            # Merge with base topics, prioritizing custom ones
            remaining_base = base_topics[len(custom_topics):]
            all_topics = custom_topics + remaining_base
            return "\n".join(all_topics[:10])  # Max 10 topics
        
        return "\n".join(base_topics)
    
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
        """Build prioritized topics with database field mappings for hybrid prompt architecture"""
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
        
        # Check campaign prioritized topics first (cached primitive)
        if not self.is_demo_mode and self._campaign_prioritized_topics:
            # Map custom topics to field mappings where possible
            custom_topics = []
            for topic_name in self._campaign_prioritized_topics[:5]:
                # Try to find matching base topic for field mapping
                matched = next((t for t in base_topics_map if topic_name.lower() in t["topic"].lower() or t["topic"].lower() in topic_name.lower()), None)
                if matched:
                    custom_topics.append({"topic": topic_name, "description": matched["description"], "fields": matched["fields"]})
                else:
                    # Use generic mapping for unknown topics
                    custom_topics.append({"topic": topic_name, "description": topic_name, "fields": ["improvement_feedback"]})
            
            # Merge with base topics
            used_base_topics = [t for t in base_topics_map if not any(ct["topic"].lower() in t["topic"].lower() for ct in custom_topics)]
            all_topics = custom_topics + used_base_topics[:10 - len(custom_topics)]
        else:
            all_topics = base_topics_map[:10]
        
        # Add priority order
        for i, topic in enumerate(all_topics, 1):
            topic["priority"] = i
        
        return all_topics
    
    def build_survey_config_json(self, participant_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build structured survey configuration JSON for hybrid prompt architecture with rich context"""
        company_name = self.get_company_name()
        
        # Build participant profile if data provided
        participant_profile = None
        if participant_data:
            participant_profile = {
                "name": participant_data.get("name"),
                "email": participant_data.get("email"),
                "company": participant_data.get("company_name"),
                "role": participant_data.get("role"),
                "region": participant_data.get("region"),
                "customer_tier": participant_data.get("customer_tier"),
                "language": participant_data.get("language", "en")
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
        
        # Industry (business account - cached primitive)
        if self._ba_industry:
            context['industry'] = self._ba_industry
        
        # Build survey configuration
        config = {
            "goals": self._build_prioritized_topics_with_fields(),
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
            'survey_goals': self.get_survey_goals(),
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
                    'has_custom_goals': bool(self._campaign_survey_goals),
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