"""
Prompt Template Service for VOÏA Conversational Surveys
Handles dynamic prompt generation based on BusinessAccount customization settings
Supports dual-mode operation: demo (hardcoded) vs customer (customized)
"""

import json
from typing import Dict, Any, Optional
from models import BusinessAccount


class PromptTemplateService:
    """Service for generating dynamic survey prompts based on business account configuration"""
    
    def __init__(self, business_account_id: Optional[int] = None):
        """
        Initialize prompt template service
        
        Args:
            business_account_id: ID of business account for customized prompts, 
                               None for demo mode
        """
        self.business_account_id = business_account_id
        self.business_account = None
        self.is_demo_mode = False
        
        if business_account_id:
            self.business_account = BusinessAccount.query.get(business_account_id)
            # Check if this is demo account or missing customization
            if (not self.business_account or 
                self.business_account.account_type == 'demo' or
                not self._has_customization()):
                self.is_demo_mode = True
        else:
            self.is_demo_mode = True
    
    def _has_customization(self) -> bool:
        """Check if business account has meaningful customization data"""
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
        """Get product/service name for survey context"""
        if self.is_demo_mode:
            return "ArcheloFlow"
        
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
    
    def get_conversation_tone(self) -> str:
        """Get conversation tone setting"""
        if self.is_demo_mode:
            return "professional"
        
        if self.business_account and self.business_account.conversation_tone:
            return self.business_account.conversation_tone
        
        return "professional"  # Default
    
    def get_survey_goals(self) -> list:
        """Get survey goals/objectives"""
        if self.is_demo_mode:
            return [
                "Understand customer satisfaction with Archelo Group",
                "Identify areas for service improvement",
                "Measure likelihood to recommend our solutions"
            ]
        
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
        """Get maximum questions limit"""
        if self.is_demo_mode:
            return 8  # Demo default
        
        if self.business_account and self.business_account.max_questions:
            return self.business_account.max_questions
        
        return 8  # Default
    
    def get_max_duration_seconds(self) -> int:
        """Get maximum survey duration in seconds"""
        if self.is_demo_mode:
            return 120  # 2 minutes default
        
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
        """Get prioritized survey topics based on business account settings"""
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
        
        # Add custom prioritized topics if available
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
        """Get survey completion message"""
        company_name = self.get_company_name()
        
        if self.is_demo_mode:
            return "Thank you so much for taking the time to share your detailed feedback about Archelo Group! Your insights are incredibly valuable and will help us improve our service delivery. Have a wonderful day!"
        
        if (self.business_account and 
            self.business_account.custom_end_message):
            return self.business_account.custom_end_message
        
        return f"Thank you so much for taking the time to share your detailed feedback about {company_name}! Your insights are incredibly valuable and will help us improve our service delivery. Have a wonderful day!"
    
    def should_force_completion(self, step_count: int) -> bool:
        """Check if survey should be force-completed based on limits"""
        max_questions = self.get_max_questions()
        return step_count > max_questions
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get template configuration info for debugging"""
        return {
            'is_demo_mode': self.is_demo_mode,
            'business_account_id': self.business_account_id,
            'company_name': self.get_company_name(),
            'product_name': self.get_product_name(),
            'conversation_tone': self.get_conversation_tone(),
            'max_questions': self.get_max_questions(),
            'max_duration_seconds': self.get_max_duration_seconds(),
            'has_customization': self._has_customization() if self.business_account else False
        }