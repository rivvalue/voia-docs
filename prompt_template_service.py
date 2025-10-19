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
    "Support Quality": ["service_rating"],
    "Improvement Suggestions": ["improvement_feedback"],
    "Additional Feedback": ["improvement_feedback"]
}


class PromptTemplateService:
    """Service for generating dynamic survey prompts based on business account configuration"""
    
    def __init__(self, business_account_id: Optional[int] = None, campaign_id: Optional[int] = None):
        """
        Initialize prompt template service with hybrid business+campaign data support
        
        Args:
            business_account_id: ID of business account for customized prompts, 
                               None for demo mode
            campaign_id: ID of campaign for campaign-specific customization,
                        takes precedence over business account data
        """
        self.business_account_id = business_account_id
        self.campaign_id = campaign_id
        self.business_account = None
        self.campaign = None
        self.is_demo_mode = False
        
        # Load campaign data first if provided
        if campaign_id:
            try:
                self.campaign = Campaign.query.get(campaign_id)
                if not self.campaign:
                    # Log warning but continue - allows graceful degradation
                    import logging
                    logging.warning(f"Campaign ID {campaign_id} not found, falling back to business account only")
                # If campaign exists and has a business account, load that too
                elif self.campaign.business_account_id:
                    self.business_account_id = self.campaign.business_account_id
                    business_account_id = self.campaign.business_account_id
            except Exception as e:
                # Log error but continue - allows graceful degradation
                import logging
                logging.error(f"Error loading campaign {campaign_id}: {e}")
                self.campaign = None
        
        # Load business account data
        if business_account_id:
            self.business_account = BusinessAccount.query.get(business_account_id)
        
        # Determine demo mode after loading both campaign and business account data
        # Demo mode is only true if NEITHER campaign NOR business account exist
        # Priority: Campaign → Business → Demo
        # FIXED: Less strict - prefer business account if it exists with non-demo account_type
        self.is_demo_mode = not (
            (self.campaign and self.has_campaign_customization()) or 
            (self.business_account and self.business_account.account_type != 'demo')
        )
    
    def _has_customization(self) -> bool:
        """Check if business account or campaign has meaningful customization data"""
        # Check campaign customization first
        if self.campaign and self.has_campaign_customization():
            return True
            
        # Check business account customization
        if not self.business_account:
            return False
        
        # Account has customization if it has company-specific fields
        return bool(
            self.business_account.industry or
            self.business_account.company_description or
            self.business_account.product_description or
            self.business_account.target_clients_description
        )
    
    def get_company_name(self) -> str:
        """Get company name for survey context"""
        if self.is_demo_mode:
            return "Archelo Group"
        
        if self.business_account and self.business_account.name:
            # Use business account name as company name
            return self.business_account.name
        
        return "Archelo Group"  # Fallback
    
    def get_product_name(self) -> str:
        """Get product/service name for survey context - campaign data takes precedence"""
        if self.is_demo_mode:
            return "ArcheloFlow"
        
        # Check campaign product description first
        if self.campaign and self.campaign.product_description:
            product_desc = self.campaign.product_description.strip()
            # Take first 3-5 words as product name if it's a description
            words = product_desc.split()
            if len(words) <= 5:
                return product_desc
            else:
                return " ".join(words[:3]) + "..."
        
        # Fall back to business account product description
        if self.business_account and self.business_account.product_description:
            # Extract product name from description or use first few words
            product_desc = self.business_account.product_description.strip()
            # Take first 3-5 words as product name if it's a description
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
        """Check if campaign has meaningful customization data"""
        if not self.campaign:
            return False
        
        # Campaign has customization if it has campaign-specific fields
        return bool(
            self.campaign.product_description or
            self.campaign.target_clients_description or
            self.campaign.survey_goals or
            self.campaign.max_questions != 8 or  # Default is 8
            self.campaign.max_duration_seconds != 120 or  # Default is 120
            self.campaign.max_follow_ups_per_topic != 2 or  # Default is 2
            self.campaign.prioritized_topics or
            self.campaign.optional_topics or
            self.campaign.custom_end_message or
            self.campaign.custom_system_prompt
        )
    
    def get_conversation_tone(self) -> str:
        """Get conversation tone setting - always from business account for consistent identity"""
        if self.is_demo_mode:
            return "professional"
        
        if self.business_account and self.business_account.conversation_tone:
            return self.business_account.conversation_tone
        
        return "professional"  # Default
    
    def get_survey_goals(self) -> list:
        """Get survey goals/objectives - campaign data takes precedence"""
        if self.is_demo_mode:
            return [
                "Understand customer satisfaction with Archelo Group",
                "Identify areas for service improvement",
                "Measure likelihood to recommend our solutions"
            ]
        
        # Check campaign survey goals first
        if (self.campaign and 
            self.campaign.survey_goals and 
            isinstance(self.campaign.survey_goals, list)):
            return self.campaign.survey_goals
        
        # Fall back to business account survey goals
        if (self.business_account and 
            self.business_account.survey_goals and 
            isinstance(self.business_account.survey_goals, list)):
            return self.business_account.survey_goals
        
        # Generate goals based on company info
        company_name = self.get_company_name()
        return [
            f"Understand customer satisfaction with {company_name}",
            "Identify areas for service improvement",
            f"Measure likelihood to recommend {company_name}"
        ]
    
    def get_max_questions(self) -> int:
        """Get maximum questions limit - campaign data takes precedence"""
        if self.is_demo_mode:
            return 8  # Demo default
        
        # Check campaign max questions first
        if self.campaign and self.campaign.max_questions:
            return self.campaign.max_questions
        
        # Fall back to business account
        if self.business_account and self.business_account.max_questions:
            return self.business_account.max_questions
        
        return 8  # Default
    
    def get_max_duration_seconds(self) -> int:
        """Get maximum survey duration in seconds - campaign data takes precedence"""
        if self.is_demo_mode:
            return 120  # 2 minutes default
        
        # Check campaign max duration first
        if self.campaign and self.campaign.max_duration_seconds:
            return self.campaign.max_duration_seconds
        
        # Fall back to business account
        if self.business_account and self.business_account.max_duration_seconds:
            return self.business_account.max_duration_seconds
        
        return 120  # Default
    
    def generate_welcome_message(self, respondent_name: str) -> str:
        """Generate personalized welcome message"""
        company_name = self.get_company_name()
        product_name = self.get_product_name()
        
        if self.is_demo_mode:
            # Use original hardcoded message for demo mode
            return f"Hi {respondent_name}, we'd love to hear from you.\n\nArchelo is on a mission to make workplace tools less painful, and your feedback makes us better.\n\nThis short conversation will help us understand what's working, what's not, and how to improve your experience with ArcheloFlow.\n\nOn a scale of 0-10, how likely are you to recommend Archelo Group to a friend or colleague?"
        
        # Generate customized welcome message
        company_description = ""
        if self.business_account and self.business_account.company_description:
            company_description = f"\n\n{self.business_account.company_description}"
        
        survey_purpose = f"This short conversation will help us understand what's working, what's not, and how to improve your experience with {product_name}."
        
        return f"Hi {respondent_name}, we'd love to hear from you.{company_description}\n\n{survey_purpose}\n\nOn a scale of 0-10, how likely are you to recommend {company_name} to a friend or colleague?"
    
    def generate_system_prompt(self, extracted_data: Dict[str, Any], step_count: int, conversation_history: str) -> str:
        """Generate system prompt for OpenAI conversation"""
        company_name = self.get_company_name()
        product_name = self.get_product_name()
        tone = self.get_conversation_tone()
        
        if self.is_demo_mode:
            # Use original hardcoded prompt for demo mode
            return self._get_demo_system_prompt(extracted_data, step_count, conversation_history)
        
        # Generate customized system prompt
        business_context = ""
        if self.business_account:
            if self.business_account.industry:
                business_context += f"\n- Industry: {self.business_account.industry}"
            if self.business_account.target_clients_description:
                business_context += f"\n- Target Clients: {self.business_account.target_clients_description}"
        
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
- CRITICALLY IMPORTANT: DON'T ask for information you already have (check SURVEY DATA COLLECTED SO FAR)
- ALREADY COLLECTED DATA CHECK: Before asking ANY question, verify the field is NULL in SURVEY DATA COLLECTED SO FAR
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
- CRITICALLY IMPORTANT: DON'T ask for information you already have (check SURVEY DATA COLLECTED SO FAR)
- ALREADY COLLECTED DATA CHECK: Before asking ANY question, verify the field is NULL in SURVEY DATA COLLECTED SO FAR
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
        
        # Check campaign prioritized topics first
        if (not self.is_demo_mode and 
            self.campaign and 
            self.campaign.prioritized_topics and 
            isinstance(self.campaign.prioritized_topics, list)):
            
            custom_topics = []
            for i, topic in enumerate(self.campaign.prioritized_topics[:5], 1):
                custom_topics.append(f"{i}. {topic}")
            
            # Merge with base topics, prioritizing custom ones
            remaining_base = base_topics[len(custom_topics):]
            all_topics = custom_topics + remaining_base
            return "\n".join(all_topics[:10])  # Max 10 topics
        
        # Fall back to business account prioritized topics
        if (not self.is_demo_mode and 
            self.business_account and 
            self.business_account.prioritized_topics and 
            isinstance(self.business_account.prioritized_topics, list)):
            
            custom_topics = []
            for i, topic in enumerate(self.business_account.prioritized_topics[:5], 1):
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
        
        # Check campaign custom end message first
        if (self.campaign and self.campaign.custom_end_message):
            return self.campaign.custom_end_message
        
        # Fall back to business account custom end message
        if (self.business_account and 
            self.business_account.custom_end_message):
            return self.business_account.custom_end_message
        
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
        
        # Check campaign prioritized topics first
        if (not self.is_demo_mode and 
            self.campaign and 
            self.campaign.prioritized_topics and 
            isinstance(self.campaign.prioritized_topics, list)):
            
            # Map custom topics to field mappings where possible
            custom_topics = []
            for topic_name in self.campaign.prioritized_topics[:5]:
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
        """Build structured survey configuration JSON for hybrid prompt architecture"""
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
        
        # Build survey configuration
        config = {
            "goals": self._build_prioritized_topics_with_fields(),
            "max_questions": self.get_max_questions(),
            "max_duration_seconds": self.get_max_duration_seconds(),
            "conversation_tone": self.get_conversation_tone(),
            "company_name": company_name,
            "industry": self.business_account.industry if self.business_account and hasattr(self.business_account, 'industry') else None,
            "target_clients": self.business_account.target_clients_description if self.business_account and hasattr(self.business_account, 'target_clients_description') else None,
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
            # Optional campaign-specific fields
            'target_clients_description': self.campaign.target_clients_description if self.campaign else (self.business_account.target_clients_description if self.business_account else None),
            'max_follow_ups_per_topic': self.campaign.max_follow_ups_per_topic if self.campaign else (self.business_account.max_follow_ups_per_topic if hasattr(self.business_account, 'max_follow_ups_per_topic') and self.business_account else 2),
            'optional_topics': self.campaign.optional_topics if self.campaign else (self.business_account.optional_topics if hasattr(self.business_account, 'optional_topics') and self.business_account else None),
            'custom_system_prompt': self.campaign.custom_system_prompt if self.campaign else None
        }
    
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
            'campaign_exists': self.campaign is not None,
            'business_account_exists': self.business_account is not None
        }
        
        # Add campaign-specific debug info if available
        if self.campaign:
            info['campaign_info'] = {
                'name': self.campaign.name,
                'status': self.campaign.status,
                'has_product_description': bool(self.campaign.product_description),
                'has_custom_goals': bool(self.campaign.survey_goals),
                'has_custom_end_message': bool(self.campaign.custom_end_message),
                'has_prioritized_topics': bool(self.campaign.prioritized_topics)
            }
        
        # Add business account debug info if available
        if self.business_account:
            info['business_account_info'] = {
                'name': self.business_account.name,
                'account_type': getattr(self.business_account, 'account_type', 'unknown'),
                'has_product_description': bool(getattr(self.business_account, 'product_description', None)),
                'has_conversation_tone': bool(getattr(self.business_account, 'conversation_tone', None))
            }
        
        return info