import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import OpenAI
from prompt_template_service import PromptTemplateService

# Configure logger with PII masking
logger = logging.getLogger(__name__)

def _mask_pii(text, max_length=100):
    """Mask PII and truncate text for logging"""
    if not text:
        return text
    if isinstance(text, dict):
        return {k: _mask_pii(v) if k not in ['conversation_id', 'step_count'] else v for k, v in list(text.items())[:5]}
    text_str = str(text)
    if len(text_str) > max_length:
        return text_str[:max_length] + "... [truncated]"
    return text_str

def normalize_company_name(company_name):
    """Normalize company name for case-insensitive comparison"""
    if not company_name:
        return company_name
    # Convert to title case for consistent display (first letter caps, rest lowercase)
    return company_name.strip().title()

class AIConversationalSurvey:
    """OpenAI-powered conversational survey system with adaptive questioning"""
    
    def __init__(self, business_account_id: Optional[int] = None, campaign_id: Optional[int] = None, participant_data: Optional[Dict[str, Any]] = None):
        self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        self.conversation_history = []
        self.survey_data = {}
        self.extracted_data = {}
        self.step_count = 0
        self.is_complete = False
        
        # Store IDs for conversation state persistence
        self.business_account_id = business_account_id
        self.campaign_id = campaign_id
        
        # Store participant data for personalized prompts
        self.participant_data = participant_data
        
        # Track all AI prompts for debugging (language issues, prompt effectiveness, etc.)
        self.ai_prompts_log = []
        
        # CRITICAL FIX: Pre-populate tenure from participant_data if available
        # This ensures tenure is always loaded into extracted_data, not just when passed as parameter
        if participant_data and participant_data.get('tenure_with_fc'):
            self.extracted_data['tenure_with_fc'] = participant_data['tenure_with_fc']
            logger.debug(f"Pre-populated tenure from participant_data: {participant_data['tenure_with_fc']}")
        
        # NPS retry tracking to prevent infinite loops
        self.nps_retry_count = 0
        self.nps_deferred = False
        
        # CAMPAIGN-AWARE EXTRACTION: Track current topic being collected
        self.current_topic = None  # Will be set when question is generated
        self.current_expected_field = None  # Specific field expected for current question
        
        # Initialize prompt template service for dynamic prompts with campaign-specific customization
        self.template_service = PromptTemplateService(business_account_id, campaign_id)
        
        # Debug logging for template mode
        template_info = self.template_service.get_template_info()
        logger.debug(f"Template initialized: business_account_id={business_account_id}, campaign_id={campaign_id}")
        logger.debug(f"Template mode: {template_info['is_demo_mode']}, max_questions={template_info['max_questions']}")
        logger.debug(f"Participant data available: {bool(participant_data)}")
        
    def start_conversation(self, company_name: str, respondent_name: str) -> Dict[str, Any]:
        """Start a new AI-powered conversational survey"""
        # CRITICAL FIX: Preserve any pre-populated extracted_data (like tenure from form)
        # The extracted_data might already be set by start_ai_conversational_survey
        existing_extracted_data = self.extracted_data.copy() if hasattr(self, 'extracted_data') and self.extracted_data else {}
        
        logger.debug(f"Pre-conversation extracted_data fields: {list(existing_extracted_data.keys())}")
        
        self.survey_data = {
            'company_name': company_name,
            'respondent_name': respondent_name,
            'conversation_history': [],
            'extracted_data': existing_extracted_data  # Preserve the pre-populated data
        }
        
        # CRITICAL: Keep reference to extracted_data intact
        self.extracted_data = self.survey_data['extracted_data']
        
        # Debug logging
        logger.debug(f"Conversation started with {len(self.extracted_data)} pre-populated fields")
        
        welcome_message = self._generate_welcome_message(company_name, respondent_name)
        
        self.conversation_history.append({
            'sender': 'VOÏA',
            'message': welcome_message,
            'timestamp': 'now'
        })
        
        return {
            'message': welcome_message,
            'message_type': 'welcome',
            'step': 'welcome',
            'progress': 10,
            'is_complete': False,
            'conversation_id': str(uuid.uuid4()),
            'extracted_data': self.extracted_data  # Include initial extracted data
        }
    
    def process_user_response(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user response and generate next AI question"""
        # Add user response to conversation history
        self.conversation_history.append({
            'sender': 'User',
            'message': user_input,
            'timestamp': 'now'
        })
        
        # Increment step count BEFORE processing
        self.step_count += 1
        
        logger.debug(f"Step {self.step_count}: Processing user input")
        logger.debug(f"User input: {_mask_pii(user_input)}")
        
        # ANTI-LOOP PROTECTION: Prevent infinite loops but allow service questions
        if self.template_service.should_force_completion(self.step_count):
            logger.info(f"Loop protection: forcing completion at step {self.step_count}")
            self.is_complete = True
            return {
                'message': self.template_service.get_completion_message(),
                'message_type': 'completion',
                'step': 'forced_complete',
                'progress': 100,
                'is_complete': True
            }
        
        # CRITICAL FIX: Backend controls completion, NOT OpenAI
        # Check if we have enough data to complete
        if self._check_completion_criteria():
            # Don't call OpenAI - backend decides survey is complete
            next_question = {
                'message': self.template_service.get_completion_message(),
                'message_type': 'completion',
                'step': 'complete',
                'progress': 100,
                'is_complete': True
            }
            self.is_complete = True
            logger.info(f"✅ BACKEND COMPLETION: Survey ended by VOÏA at step {self.step_count}")
        else:
            # PERFORMANCE FIX: Single combined AI call for extraction + next question
            combined_result = self._process_with_ai_combined(user_input, context)
            
            if combined_result['success']:
                # Update extracted data from combined result
                extracted = combined_result.get('extracted_data', {})
                newly_extracted = {}
                for key, value in extracted.items():
                    if value is not None and self.extracted_data.get(key) is None:
                        newly_extracted[key] = value
                        self.extracted_data[key] = value
                        logger.debug(f"Locked field: {key} (first capture)")
                
                self.survey_data['extracted_data'] = self.extracted_data
                logger.debug(f"Step {self.step_count}: New fields={list(newly_extracted.keys())}, Total fields={len(self.extracted_data)}")
                
                # Use AI-generated next question
                next_question = combined_result['next_question']
            else:
                # Fallback: Use rule-based extraction + fallback questions
                logger.warning(f"AI combined call failed, using fallback at step {self.step_count}")
                extracted = self._extract_survey_data_fallback(user_input)
                for key, value in extracted.items():
                    if value is not None and self.extracted_data.get(key) is None:
                        self.extracted_data[key] = value
                next_question = self._generate_fallback_question(user_input, context)
            
            # CRITICAL: Override OpenAI's is_complete decision - backend decides
            if next_question.get('is_complete'):
                logger.warning(f"⚠️ OpenAI tried to end survey at step {self.step_count} - OVERRIDDEN by backend")
                # Don't just set is_complete=False, REPLACE the completion message with a new question
                next_question = self._generate_fallback_question(user_input, context)
                next_question['is_complete'] = False  # Ensure backend control
        
        # Add AI response to conversation history
        if not next_question.get('is_complete', False):
            self.conversation_history.append({
                'sender': 'VOÏA',
                'message': next_question['message'],
                'timestamp': 'now'
            })
        
        # Debug logging
        logger.debug(f"Step {self.step_count}: Total extracted fields: {len(self.extracted_data)}")
        
        # Add extracted_data to response for frontend state sync
        next_question['extracted_data'] = self.extracted_data
        return next_question
    
    def _generate_welcome_message(self, company_name: str, respondent_name: str) -> str:
        """Generate personalized welcome message using template service"""
        # Use template service for dynamic or demo-specific welcome messages
        return self.template_service.generate_welcome_message(respondent_name)
    
    def _process_with_ai_combined(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """PERFORMANCE OPTIMIZATION: Single API call for extraction + next question
        
        This reduces API calls from 2 to 1 per user response, cutting rate limit pressure in half
        """
        try:
            # Get context
            company_name = self.template_service.get_company_name()
            campaign_language = self.template_service.get_language_code()
            survey_config = self.template_service.build_survey_config_json(self.participant_data)
            
            # Build missing goals context
            missing_goals = self._get_missing_goals()
            missing_goals_text = ", ".join(missing_goals) if missing_goals else "All goals collected"
            
            # Build conversation history for context
            history_text = self._format_conversation_history()
            
            # Generate hybrid prompt from template service
            hybrid_prompt = self.template_service._generate_hybrid_prompt(
                company_name=company_name,
                participant_data=self.participant_data,
                conversation_history=history_text
            )
            
            prompt = f"""{hybrid_prompt}

CURRENT STATE:
- Step: {self.step_count}
- Missing campaign goals: {missing_goals_text}
- Already collected data: {list(self.extracted_data.keys())}

USER'S LATEST RESPONSE: "{user_input}"

YOUR TASK (COMPLETE BOTH IN ONE RESPONSE):
1. Extract any relevant data from the user's response
2. Generate the next conversational question based on missing goals

Return JSON with this EXACT format:
{{
    "extracted_data": {{
        "nps_score": number or null,
        "nps_category": string or null,
        "satisfaction_rating": number or null,
        "service_rating": number or null,
        "product_value_rating": number or null,
        "pricing_rating": number or null,
        "support_rating": number or null,
        "product_quality_feedback": string or null,
        "support_experience_feedback": string or null,
        "service_rating_feedback": string or null,
        "user_experience_feedback": string or null,
        "feature_requests": string or null,
        "general_feedback": string or null,
        "nps_reasoning": string or null,
        "improvement_feedback": string or null,
        "additional_comments": string or null
    }},
    "next_question": {{
        "message": "Your next question in {campaign_language}",
        "message_type": "ai_question",
        "step": "descriptive_step_name",
        "progress": number,
        "is_complete": false
    }}
}}

CRITICAL: Keep is_complete=false. Backend controls survey completion, not you."""

            # Model selection via environment variable
            conversation_model = os.environ.get('AI_CONVERSATION_MODEL', 'gpt-4o')
            
            # Log the full prompt for debugging
            self.ai_prompts_log.append({
                'step': self.step_count,
                'type': 'combined_extraction_and_question',
                'prompt': prompt,
                'timestamp': 'now'
            })
            
            response = self.openai_client.chat.completions.create(
                model=conversation_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=800,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
                logger.info(f"✅ Combined AI call successful at step {self.step_count}")
                return {
                    'success': True,
                    'extracted_data': result.get('extracted_data', {}),
                    'next_question': result.get('next_question', {})
                }
            else:
                logger.warning(f"Empty response from combined AI call")
                return {'success': False}
                
        except Exception as e:
            logger.warning(f"Combined AI call failed: {str(e)[:100]}")
            return {'success': False}
    
    def _extract_survey_data_with_ai(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """CAMPAIGN-AWARE: Extract structured survey data from natural language using OpenAI"""
        try:
            # Get list of already captured data to prevent overwrites
            locked_fields = [key for key, value in self.extracted_data.items() if value is not None]
            
            # Get dynamic company name from template service
            company_name = self.template_service.get_company_name()
            
            # CAMPAIGN-AWARE CONTEXT: Build survey config to understand campaign priorities
            survey_config = self.template_service.build_survey_config_json(self.participant_data)
            
            # Build campaign-specific context section
            campaign_context = ""
            if self.current_topic and self.current_expected_field:
                campaign_context = f"""
CURRENT QUESTION CONTEXT:
- Topic being collected: {self.current_topic}
- Expected field: {self.current_expected_field}
- If user provides a numeric rating, it should map to: {self.current_expected_field}
"""
            
            # Build prioritized topics context
            topics_context = ""
            if survey_config.get('goals'):
                topics_list = "\n".join([f"  {i+1}. {goal['topic']} → fields: {goal.get('fields', [])}" 
                                        for i, goal in enumerate(survey_config['goals'][:8])])
                topics_context = f"""
CAMPAIGN PRIORITIZED TOPICS (in order):
{topics_list}

Use these field mappings when extracting data to ensure correct assignment.
"""
            
            prompt = f"""Extract survey data from this customer response: "{user_input}"

Context of conversation:
- Company: {context.get('company_name', 'Unknown')}
- Current extracted data: {json.dumps(self.extracted_data, indent=2)}
- Conversation step: {self.step_count}
- ALREADY CAPTURED (DO NOT RE-EXTRACT): {locked_fields}
{campaign_context}{topics_context}
CRITICAL INSTRUCTION: Only extract NEW information from this specific response. 
DO NOT re-extract or change data that was already captured in previous responses.

RATING EXTRACTION PRIORITY: If you see explicit ratings like "I rate them 3", "3 out of 5", "I'd give them a 4", extract these immediately.
If a numeric rating is provided and we know the current expected field (see CURRENT QUESTION CONTEXT above), use that field assignment.

Extract any of the following data present in the response:
- Tenure with {company_name}: Look for duration mentions like "6 months", "2 years", "less than 6 months", etc.
- NPS score (0-10): Numbers for recommendations, likelihood scores (0-10 only)
- Satisfaction level (1-5): Explicit ratings like "I rate them 3", "3/5", satisfaction numbers (1-5 only)
- Service quality rating (1-5): Service/professional ratings like "service is 4", "I rate their service 3" (1-5 only)  
- Product value rating (1-5): Product/solution ratings like "product is 2", "I rate the value 4" (1-5 only)
- Pricing rating (1-5): Pricing ratings like "price is fair, 3", "I rate pricing 2" (1-5 only)
- Support rating (1-5): Support ratings like "support gets a 4", customer service numbers (1-5 only)
- Improvement suggestions: General feedback about what could be better
- Product quality feedback: Specific feedback about product quality, reliability, performance
- Support experience feedback: Specific feedback about support experience, responsiveness
- Service rating feedback: Specific feedback about service quality, delivery
- User experience feedback: Specific feedback about UX, ease of use, interface
- Feature requests: Requests for new features or capabilities
- General feedback: Any other topic-specific feedback
- Compliments: What they liked or appreciated  
- Complaints: What they didn't like or found problematic
- Reasons: Why they gave their rating or recommendation
- Additional comments: Any other relevant feedback

PATTERNS TO WATCH FOR:
- "I rate [topic] X" or "I'd rate [topic] X" → extract rating X for that topic
- "[Topic] is X" or "[Topic] gets X" → extract rating X 
- "X out of 5" or "X/5" → extract rating X
- Simple numbers in context → extract as ratings when topic is clear

Return ONLY JSON in this format:
{{
    "tenure_with_fc": string or null,
    "nps_score": number or null,
    "nps_category": "Promoter/Passive/Detractor" or null,
    "satisfaction_rating": number or null,
    "service_rating": number or null,
    "product_value_rating": number or null,
    "pricing_rating": number or null,
    "support_rating": number or null,
    "improvement_feedback": "text" or null,
    "compliment_feedback": "text" or null,
    "complaint_feedback": "text" or null,
    "nps_reasoning": "text" or null,
    "additional_comments": "text" or null
}}

Only include fields that are clearly present in the response. If a field is not mentioned, use null.

IMPORTANT: If data was already captured (listed in ALREADY CAPTURED above), return null for those fields to prevent overwrites."""

            # Model selection via environment variable for cost optimization
            conversation_model = os.environ.get('AI_CONVERSATION_MODEL', 'gpt-4o')
            
            response = self.openai_client.chat.completions.create(
                model=conversation_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=400,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            if content:
                extracted = json.loads(content)
            else:
                extracted = {}
            
            # Add NPS category if score is provided
            if extracted.get('nps_score') is not None:
                score = extracted['nps_score']
                if score >= 9:
                    extracted['nps_category'] = 'Promoter'
                elif score >= 7:
                    extracted['nps_category'] = 'Passive'
                else:
                    extracted['nps_category'] = 'Detractor'
            
            return extracted
            
        except Exception as e:
            logger.warning(f"AI extraction error, using fallback: {str(e)[:50]}")
            # Use robust fallback extraction
            return self._extract_survey_data_fallback(user_input)
    
    def _extract_survey_data_fallback(self, user_input: str) -> Dict[str, Any]:
        """CAMPAIGN-AWARE: Enhanced rule-based extraction with intelligent pattern matching"""
        extracted = {}
        text_lower = user_input.lower()
        
        # Extract NPS score - only if we're in the NPS collection step and don't have it yet
        import re
        
        # CAMPAIGN-AWARE: If we know the expected field, use that for numeric extraction
        if self.current_expected_field and re.search(r'\b[0-9]+\b', user_input):
            logger.debug(f"Campaign-aware fallback: expected field is {self.current_expected_field}")
            
            # Extract numeric value
            matches = re.findall(r'\b([0-9]+)\b', user_input)
            if matches:
                value = int(matches[-1])  # Take last match
                
                # Validate and assign based on expected field
                if self.current_expected_field == 'nps_score' and 0 <= value <= 10:
                    extracted['nps_score'] = value
                    if value >= 9:
                        extracted['nps_category'] = 'Promoter'
                    elif value >= 7:
                        extracted['nps_category'] = 'Passive'
                    else:
                        extracted['nps_category'] = 'Detractor'
                    logger.debug(f"Fallback captured NPS={value}")
                elif self.current_expected_field in ['satisfaction_rating', 'service_rating', 'product_value_rating', 'pricing_rating', 'support_rating'] and 1 <= value <= 5:
                    extracted[self.current_expected_field] = value
                    logger.debug(f"Fallback captured {self.current_expected_field}={value}")
        
        # Extract NPS score ONLY during steps 1-3 (before satisfaction questions start at step 4)
        # This prevents "1" or "5" from satisfaction questions being misinterpreted as NPS
        if not extracted.get('nps_score') and not self.extracted_data.get('nps_score') and self.step_count <= 3 and re.search(r'\b([0-9]|10)\b', user_input):
            logger.debug(f"Attempting NPS extraction at step {self.step_count}")
            nps_patterns = [
                r'(?:score|rating|give|rate).*?(10|[0-9])',  # Fixed: 10 before single digits
                r'^(10|[0-9])(?:\s|$|/|,|\.)',
                r'(10|[0-9])\s*(?:out of 10|/10)',
                r'(?:i.*d.*say|i.*d.*give|i.*d.*rate).*?(10|[0-9])',  # Fixed order
                r'(?:probably|maybe|around|about).*?(10|[0-9])',
                r'\b(10|[0-9])\b(?!\d)',  # Fixed: Check for 10 first
                r'(10|[0-9])',  # Fixed order
                r'(?:is|was|would be|rating|score).*?(10|[0-9])',
                r'(10|[0-9])(?:\s*(?:stars?|points?|rating))?'  # Fixed order
            ]
            
            for pattern in nps_patterns:
                matches = re.findall(pattern, user_input, re.IGNORECASE)
                # Use LAST match to handle "scale of 1 to 10, I give it 7" → extracts 7, not 1
                if matches:
                    match = matches[-1]  # Take the last match
                    score = int(match)
                    if 0 <= score <= 10:
                        extracted['nps_score'] = score
                        if score >= 9:
                            extracted['nps_category'] = 'Promoter'
                        elif score >= 7:
                            extracted['nps_category'] = 'Passive'
                        else:
                            extracted['nps_category'] = 'Detractor'
                        logger.debug(f"NPS captured via fallback: {score}")
                        break
                if 'nps_score' in extracted:
                    break
        
        # CRITICAL FIX: Extract explicit numeric ratings for all categories 
        # Patterns like "I rate them 3", "service is 4", "I'd give them a 2"
        if re.search(r'\b[1-5]\b', user_input):
            logger.debug(f"Attempting explicit rating extraction")
            
            # Generic rating patterns - catch "I rate X" statements
            generic_rating_patterns = [
                r'(?:i\s*rate.*?)([1-5])',
                r'(?:i.*d\s*rate.*?)([1-5])',
                r'(?:i.*d\s*give.*?)([1-5])',
                r'(?:rate.*?)([1-5])',
                r'(?:give.*?)([1-5])',
                r'([1-5])(?:\s*out\s*of\s*5|/5)',
                r'(?:is\s*a?\s*)([1-5])',
                r'(?:gets\s*a?\s*)([1-5])',
                r'([1-5])(?:\s*(?:stars?|points?))',
                r'\b([1-5])\b'  # Any isolated 1-5 number
            ]
            
            # Service-specific rating patterns
            service_patterns = [
                r'(?:service.*?)([1-5])',
                r'(?:professional.*?)([1-5])',
                r'(?:quality.*?)([1-5])'
            ]
            
            # Satisfaction-specific patterns  
            satisfaction_patterns = [
                r'(?:satisfaction.*?)([1-5])',
                r'(?:satisfied.*?)([1-5])',
                r'(?:happy.*?)([1-5])'
            ]
            
            # Product/value-specific patterns
            product_patterns = [
                r'(?:product.*?)([1-5])',
                r'(?:solution.*?)([1-5])',
                r'(?:value.*?)([1-5])',
                r'(?:deliverable.*?)([1-5])'
            ]
            
            # Pricing-specific patterns
            pricing_patterns = [
                r'(?:pric.*?)([1-5])',
                r'(?:cost.*?)([1-5])',
                r'(?:afford.*?)([1-5])'
            ]
            
            # Support-specific patterns
            support_patterns = [
                r'(?:support.*?)([1-5])',
                r'(?:help.*?)([1-5])',
                r'(?:customer.*service.*?)([1-5])'
            ]
            
            # Try service patterns first (most likely in this context)
            for pattern in service_patterns:
                matches = re.findall(pattern, user_input, re.IGNORECASE)
                if matches:  # Use LAST match to handle "scale 1-5, I rate it 4" → extracts 4, not 1
                    match = matches[-1]
                    rating = int(match)
                    if 1 <= rating <= 5 and not self.extracted_data.get('service_rating'):
                        extracted['service_rating'] = rating
                        logger.debug(f"Service rating captured: {rating}")
                        break
                if 'service_rating' in extracted:
                    break
            
            # Try satisfaction patterns
            if not extracted.get('satisfaction_rating'):
                for pattern in satisfaction_patterns:
                    matches = re.findall(pattern, user_input, re.IGNORECASE)
                    if matches:  # Use LAST match
                        match = matches[-1]
                        rating = int(match)
                        if 1 <= rating <= 5 and not self.extracted_data.get('satisfaction_rating'):
                            extracted['satisfaction_rating'] = rating
                            logger.debug(f"Satisfaction rating captured: {rating}")
                            break
                    if 'satisfaction_rating' in extracted:
                        break
            
            # Try product patterns
            if not extracted.get('product_value_rating'):
                for pattern in product_patterns:
                    matches = re.findall(pattern, user_input, re.IGNORECASE)
                    if matches:  # Use LAST match
                        match = matches[-1]
                        rating = int(match)
                        if 1 <= rating <= 5 and not self.extracted_data.get('product_value_rating'):
                            extracted['product_value_rating'] = rating
                            logger.debug(f"Product value rating captured: {rating}")
                            break
                    if 'product_value_rating' in extracted:
                        break
            
            # Try pricing patterns
            if not extracted.get('pricing_rating'):
                for pattern in pricing_patterns:
                    matches = re.findall(pattern, user_input, re.IGNORECASE)
                    if matches:  # Use LAST match
                        match = matches[-1]
                        rating = int(match)
                        if 1 <= rating <= 5 and not self.extracted_data.get('pricing_rating'):
                            extracted['pricing_rating'] = rating
                            logger.debug(f"Pricing rating captured: {rating}")
                            break
                    if 'pricing_rating' in extracted:
                        break
            
            # Try support patterns
            if not extracted.get('support_rating'):
                for pattern in support_patterns:
                    matches = re.findall(pattern, user_input, re.IGNORECASE)
                    if matches:  # Use LAST match
                        match = matches[-1]
                        rating = int(match)
                        if 1 <= rating <= 5 and not self.extracted_data.get('support_rating'):
                            extracted['support_rating'] = rating
                            logger.debug(f"Support rating captured: {rating}")
                            break
                    if 'support_rating' in extracted:
                        break
            
            # Generic patterns as final fallback (infer from context)
            # CRITICAL FIX: Don't infer 1-5 ratings if we just extracted an NPS score (prevents "4" NPS from being misread as satisfaction)
            if not any(extracted.get(key) for key in ['service_rating', 'satisfaction_rating', 'product_value_rating', 'pricing_rating', 'support_rating']) and not extracted.get('nps_score'):
                for pattern in generic_rating_patterns:
                    matches = re.findall(pattern, user_input, re.IGNORECASE)
                    if matches:  # Use LAST match
                        match = matches[-1]
                        rating = int(match)
                        if 1 <= rating <= 5:
                            # Try to infer which rating based on conversation context/step
                            # This is intelligent contextual assignment
                            if self.step_count <= 4:  # Early in survey - likely satisfaction
                                if not self.extracted_data.get('satisfaction_rating'):
                                    extracted['satisfaction_rating'] = rating
                                    logger.debug(f"Satisfaction rating inferred: {rating}")
                            elif 'service' in text_lower or 'professional' in text_lower:
                                if not self.extracted_data.get('service_rating'):
                                    extracted['service_rating'] = rating
                                    logger.debug(f"Service rating inferred: {rating}")
                            else:
                                # Default assignment to missing category
                                if not self.extracted_data.get('service_rating'):
                                    extracted['service_rating'] = rating
                                    logger.debug(f"Service rating captured (default): {rating}")
                            break
                    if any(extracted.get(key) for key in ['service_rating', 'satisfaction_rating', 'product_value_rating', 'pricing_rating', 'support_rating']):
                        break
        
        # Enhanced satisfaction detection
        satisfaction_keywords = {
            5: ['very satisfied', 'extremely satisfied', 'absolutely satisfied', 'completely satisfied', 'love it', 'excellent', 'outstanding', 'perfect'],
            4: ['satisfied', 'happy', 'pleased', 'good', 'great', 'positive', 'content'],
            3: ['neutral', 'okay', 'fine', 'average', 'alright', 'so-so', 'mixed'],
            2: ['dissatisfied', 'unhappy', 'disappointed', 'not good', 'poor', 'below average'],
            1: ['very dissatisfied', 'extremely dissatisfied', 'terrible', 'awful', 'horrible', 'hate', 'worst']
        }
        
        # Service quality rating keywords
        service_keywords = {
            5: ['excellent service', 'outstanding service', 'perfect service', 'amazing service', 'superb service'],
            4: ['good service', 'great service', 'quality service', 'professional service', 'solid service'],
            3: ['average service', 'okay service', 'standard service', 'fair service', 'decent service'],
            2: ['poor service', 'bad service', 'lacking service', 'subpar service', 'disappointing service'],
            1: ['terrible service', 'awful service', 'horrible service', 'worst service', 'unacceptable service']
        }
        
        # Product value keywords
        product_keywords = {
            5: ['excellent product', 'outstanding product', 'amazing product', 'perfect solution', 'superb deliverables'],
            4: ['good product', 'quality product', 'solid solution', 'valuable deliverables', 'great outcome'],
            3: ['average product', 'okay solution', 'standard deliverables', 'fair outcome', 'decent product'],
            2: ['poor product', 'lacking solution', 'disappointing deliverables', 'subpar outcome', 'weak product'],
            1: ['terrible product', 'awful solution', 'horrible deliverables', 'worst outcome', 'useless product']
        }
        
        # Pricing appreciation keywords - expanded for better matching
        pricing_keywords = {
            5: ['excellent value', 'outstanding value', 'great value', 'fantastic value', 'amazing value', 'perfect price', 'love the price', 'incredible value', 'bargain', 'cheap', 'inexpensive', 'very affordable'],
            4: ['good value', 'fair value', 'reasonable price', 'worth it', 'good price', 'affordable', 'reasonably priced', 'decent value', 'fair pricing', 'competitive price'],
            3: ['fair price', 'average price', 'okay price', 'standard pricing', 'acceptable price', 'normal price', 'moderate cost', 'typical pricing', 'middle range'],
            2: ['expensive', 'pricey', 'costly', 'overpriced', 'high price', 'bit expensive', 'somewhat costly', 'higher than expected', 'steep price'],
            1: ['very expensive', 'too expensive', 'way overpriced', 'ridiculously expensive', 'unaffordable', 'extremely expensive', 'outrageously priced', 'way too much', 'can\'t afford']
        }
        
        # Support services keywords
        support_keywords = {
            5: ['excellent support', 'outstanding support', 'amazing support', 'perfect support', 'superb support'],
            4: ['good support', 'helpful support', 'responsive support', 'quality support', 'solid support'],
            3: ['average support', 'okay support', 'standard support', 'fair support', 'decent support'],
            2: ['poor support', 'slow support', 'unhelpful support', 'lacking support', 'bad support'],
            1: ['terrible support', 'awful support', 'horrible support', 'worst support', 'no support']
        }
        
        for rating, keywords in satisfaction_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['satisfaction_rating'] = rating
                break
        
        # Extract service quality ratings
        for rating, keywords in service_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['service_rating'] = rating
                break
        
        # Extract product value ratings
        for rating, keywords in product_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['product_value_rating'] = rating
                break
        
        # Extract pricing ratings
        for rating, keywords in pricing_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['pricing_rating'] = rating
                break
        
        # Extract support ratings
        for rating, keywords in support_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                extracted['support_rating'] = rating
                break
        
        # Extract tenure information - only if we're answering the tenure question (step_count will be 1 when processing tenure response)
        if not self.extracted_data.get('tenure_with_fc') and self.step_count == 1:
            tenure_patterns = {
                'Less than 6 months': ['less than 6 months', 'under 6 months', 'few months', '3 months', '4 months', '5 months'],
                '6 months - 1 year': ['6 months', 'seven months', '8 months', '9 months', '10 months', '11 months', 'about a year'],
                '1-2 years': ['1 year', '2 years', 'one year', 'two years', '18 months', 'year and half'],
                '2-3 years': ['2 years', '3 years', 'two years', 'three years', '30 months'],
                '3-5 years': ['3 years', '4 years', '5 years', 'three years', 'four years', 'five years'],
                '5-10 years': ['5 years', '6 years', '7 years', '8 years', '9 years', '10 years', 'decade'],
                'More than 10 years': ['more than 10 years', 'over 10 years', '11 years', '15 years', '20 years', 'decades']
            }
            
            for tenure_option, patterns in tenure_patterns.items():
                if any(pattern in text_lower for pattern in patterns):
                    extracted['tenure_with_fc'] = tenure_option
                    break
        
        # CRITICAL FIX: Map feedback to topic-specific fields based on current context
        # This ensures unique fields per topic for backend-controlled completion
        
        # Determine which feedback field to use based on current topic
        feedback_field = self._get_feedback_field_for_topic()
        
        # Extract improvement suggestions (topic-aware)
        improvement_indicators = ['improve', 'better', 'fix', 'change', 'enhance', 'upgrade', 'should', 'could', 'need to', 'would like']
        if any(indicator in text_lower for indicator in improvement_indicators):
            if feedback_field:
                extracted[feedback_field] = user_input
            else:
                extracted['improvement_feedback'] = user_input  # Fallback
        
        # Extract compliments (topic-aware)
        positive_indicators = ['love', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'good job', 'well done', 'appreciate']
        if any(indicator in text_lower for indicator in positive_indicators):
            if feedback_field:
                extracted[feedback_field] = user_input
            else:
                extracted['compliment_feedback'] = user_input  # Fallback
        
        # Extract complaints (topic-aware)
        negative_indicators = ['problem', 'issue', 'difficult', 'hard', 'confusing', 'slow', 'expensive', 'bad', 'worst', 'hate']
        if any(indicator in text_lower for indicator in negative_indicators):
            if feedback_field:
                extracted[feedback_field] = user_input
            else:
                extracted['complaint_feedback'] = user_input  # Fallback
        
        # Store reasoning if it seems like reasoning OR if it's any substantive response
        reasoning_indicators = ['because', 'since', 'due to', 'reason', 'why', 'that\'s why', 'good', 'bad', 'great', 'poor', 'like', 'dislike', 'satisfied', 'happy', 'disappointed']
        if any(indicator in text_lower for indicator in reasoning_indicators) or len(user_input.strip()) > 5:
            extracted['nps_reasoning'] = user_input
        
        # CRITICAL FIX: Only store as additional_comments if it's substantive text (not just numbers)
        # Don't store simple numeric answers like "4", "7", "3" as comments
        if len(user_input.strip()) > 2 and not user_input.strip().isdigit():
            extracted['additional_comments'] = user_input
        
        return extracted
    
    def _check_completion_criteria(self) -> bool:
        """
        CRITICAL FIX: Backend-controlled completion - ONLY complete when campaign goals are satisfied
        OpenAI cannot decide completion - backend enforces this strictly
        """
        # Check for user frustration signals (emergency exit)
        user_frustrated = self._detect_user_frustration()
        
        # Question limit enforcement - hard cap
        max_questions = self.template_service.get_max_questions()
        at_question_limit = self.step_count >= max_questions
        
        # CRITICAL: Check if ALL campaign goals are satisfied (or no goals defined)
        survey_config = self.template_service.build_survey_config_json(self.participant_data)
        has_campaign_goals = survey_config.get('goals') and len(survey_config.get('goals', [])) > 0
        
        if has_campaign_goals:
            # Campaign has goals - enforce completion of ALL goals
            has_campaign_priorities = self._check_campaign_priorities_collected()
        else:
            # Campaign has no custom goals - allow completion at question limit
            has_campaign_priorities = False
        
        # BACKEND-CONTROLLED COMPLETION LOGIC:
        # Complete survey ONLY if:
        # 1. User shows frustration (emergency exit - respect user experience)
        # 2. We've reached the hard question limit
        # 3. ALL campaign goals have been collected (if campaign has goals)
        
        completion_reasons = []
        
        if user_frustrated:
            completion_reasons.append("USER_FRUSTRATED")
            logger.warning(f"⚠️ User frustration detected at step {self.step_count} - allowing early exit")
        if at_question_limit:
            completion_reasons.append("AT_QUESTION_LIMIT")
            logger.warning(f"⚠️ Question limit ({max_questions}) reached")
        if has_campaign_goals and has_campaign_priorities:
            completion_reasons.append("ALL_CAMPAIGN_GOALS_COLLECTED")
            logger.info(f"✅ All campaign goals collected at step {self.step_count}")
        
        completion_ready = len(completion_reasons) > 0
        
        logger.debug(f"BACKEND COMPLETION CHECK: Frustrated={user_frustrated}, AtLimit={at_question_limit}, HasGoals={has_campaign_goals}, AllGoals={has_campaign_priorities}, Steps={self.step_count}/{max_questions}, Ready={completion_ready}")
        if completion_reasons:
            logger.info(f"COMPLETION REASONS: {', '.join(completion_reasons)}")
        
        return completion_ready
    
    def _detect_user_frustration(self) -> bool:
        """Detect if user is showing frustration with the survey process"""
        if not self.conversation_history:
            return False
        
        # Check recent user messages for frustration signals
        recent_messages = [msg for msg in self.conversation_history[-3:] if msg['sender'] == 'User']
        
        # CRITICAL: Only detect SURVEY frustration, not product feedback frustration
        # Use specific phrases to avoid false positives like "not enough support" → "enough"
        frustration_keywords = [
            'repeating yourself', 'repeating the same', 'keep repeating', 
            'over and over', 'already told you', 'already answered',
            'already said that', "i'm done", 'done with this', "that's enough",
            'enough questions', 'stop asking', 'frustrated with this survey',
            'annoying survey', 'irritating questions', 'waste of my time',
            'same question again', 'asked this already', 'keep asking the same',
            'how many times do i', 'told you this already', 
            'i want to finish', 'let me finish', 'can we finish'
        ]
        
        for message in recent_messages:
            message_text = message['message'].lower()
            if any(keyword in message_text for keyword in frustration_keywords):
                logger.debug(f"DETECTED: '{message['message']}'")
                return True
        
        # Check for pattern of very short responses after longer ones (user giving up)
        if len(recent_messages) >= 2:
            last_two = recent_messages[-2:]
            if (len(last_two[0]['message']) > 20 and 
                len(last_two[1]['message']) <= 5 and
                last_two[1]['message'].lower().strip() in ['ok', 'fine', 'sure', 'yes', 'no', 'done']):
                logger.debug(f"PATTERN: Long response followed by short dismissive response")
                return True
        
        return False
    
    def _get_feedback_field_for_topic(self):
        """
        Map current topic to appropriate feedback field for backend-controlled completion
        Returns the unique feedback field name based on current question topic, or None if no topic set
        """
        if not self.current_topic:
            return None
        
        topic_lower = self.current_topic.lower()
        
        # Map topics to unique feedback fields
        if 'product quality' in topic_lower:
            return 'product_quality_feedback'
        elif 'support experience' in topic_lower or 'support quality' in topic_lower:
            return 'support_experience_feedback'
        elif 'service rating' in topic_lower or 'service quality' in topic_lower:
            return 'service_rating_feedback'
        elif 'user experience' in topic_lower or 'ux' in topic_lower or 'usability' in topic_lower:
            return 'user_experience_feedback'
        elif 'feature' in topic_lower:
            return 'feature_requests'
        elif 'improvement' in topic_lower:
            return 'improvement_feedback'
        else:
            # For any other topic, use general_feedback
            return 'general_feedback'
    
    def _check_campaign_priorities_collected(self) -> bool:
        """
        CRITICAL FIX: Backend-controlled completion - check if ALL campaign goals are satisfied
        This prevents OpenAI from deciding to end the survey prematurely
        """
        # Get campaign's prioritized topics from survey config
        survey_config = self.template_service.build_survey_config_json(self.participant_data)
        
        if not survey_config.get('goals'):
            # No custom priorities - return False to use default minimal core logic
            logger.debug("CAMPAIGN PRIORITIES: No custom goals defined, using default completion logic")
            return False
        
        # CRITICAL: Check if ALL fields for ALL goals are collected
        # Don't use hardcoded map - use the actual fields from goals
        missing_goals = []
        for goal in survey_config['goals']:
            topic = goal.get('topic', '')
            fields = goal.get('fields', [])
            
            # Check if at least one field from this goal is collected
            goal_satisfied = any(self.extracted_data.get(field) is not None for field in fields)
            
            if not goal_satisfied:
                missing_goals.append(topic)
        
        all_collected = len(missing_goals) == 0
        
        logger.info(f"BACKEND COMPLETION CHECK: {len(survey_config['goals'])} goals total, {len(missing_goals)} missing")
        if missing_goals:
            logger.info(f"MISSING GOALS: {missing_goals[:3]}...")  # Show first 3
        
        return all_collected
    
    def _get_next_question_priority(self) -> str:
        """CAMPAIGN-AWARE: Determine what question should be asked next based on campaign priorities"""
        data = self.extracted_data
        company_name = self.template_service.get_company_name()
        
        # CAMPAIGN-AWARE: Check if campaign has custom prioritized topics
        survey_config = self.template_service.build_survey_config_json(self.participant_data)
        campaign_goals = survey_config.get('goals', [])
        
        # If campaign has custom goals, follow those priorities
        if campaign_goals and len(campaign_goals) > 0:
            logger.debug(f"PRIORITY: Using campaign goals (count={len(campaign_goals)})")
            
            # Iterate through campaign goals in priority order
            for goal in campaign_goals:
                topic = goal.get('topic', '')
                description = goal.get('description', '')
                fields = goal.get('fields', [])
                
                # Check if any field for this topic is missing
                for field in fields:
                    if not data.get(field):
                        # Special handling for NPS retry logic
                        if field == 'nps_score' and not self.nps_deferred:
                            if self.nps_retry_count >= 2:
                                self.nps_deferred = True
                                logger.debug(f"NPS DEFERRED: Failed to capture after {self.nps_retry_count} attempts")
                                continue  # Skip to next topic
                            else:
                                self.nps_retry_count += 1
                                logger.debug(f"NPS RETRY ATTEMPT {self.nps_retry_count}/2 (campaign-aware)")
                                return f"Ask about {topic}: {description}"
                        
                        # Return this topic as next priority
                        logger.debug(f"PRIORITY: Next topic={topic}, field={field}")
                        return f"Ask about {topic}: {description}"
            
            # All campaign goals collected
            logger.debug("CAMPAIGN-AWARE PRIORITY: All campaign goals collected")
            return "Wrap up the conversation - you have enough information"
        
        # FALLBACK: No campaign goals, use legacy hardcoded sequence
        logger.debug("FALLBACK PRIORITY: Using legacy hardcoded sequence (no campaign goals)")
        
        if not data.get('tenure_with_fc'):
            return f"Ask about business relationship tenure with {company_name} (how long working together)"
        elif not data.get('nps_score') and not self.nps_deferred:
            # NPS retry logic - track attempts and defer after 2 failed attempts
            if self.nps_retry_count >= 2:
                self.nps_deferred = True
                logger.debug(f"NPS DEFERRED: Failed to capture after {self.nps_retry_count} attempts")
                # Move to next topic instead of retrying NPS
                if not data.get('nps_reasoning') and not data.get('improvement_feedback'):
                    return f"Let's move on - what do you think about your overall experience with {company_name}?"
                elif not data.get('satisfaction_rating'):
                    return f"On a scale of 1-5, how satisfied are you overall with {company_name}?"
                elif not data.get('service_rating'):
                    return f"How would you rate the professional services quality from {company_name} (1-5)?"
                else:
                    return f"What could {company_name} do better or improve?"
            else:
                # Track retry attempt
                self.nps_retry_count += 1
                logger.debug(f"NPS RETRY ATTEMPT {self.nps_retry_count}/2")
                return f"Ask for NPS score (0-10 likelihood to recommend {company_name})"
        elif not data.get('nps_reasoning') and not data.get('improvement_feedback'):
            return f"Ask WHY they gave that NPS score - what's their reasoning about {company_name}"
        elif not data.get('satisfaction_rating'):
            return f"Ask for overall satisfaction rating (1-5) with {company_name}"
        elif not data.get('service_rating'):
            return f"Ask for professional services quality rating (1-5) from {company_name}"
        elif not data.get('product_value_rating'):
            return f"Ask for product/solution value rating (1-5) from {company_name}"
        elif not data.get('pricing_rating'):
            return f"Ask for pricing value rating (1-5) for {company_name} services"
        elif not data.get('improvement_feedback'):
            return f"Ask what {company_name} could do better or improve"
        else:
            return "Wrap up the conversation - you have enough information"
    
    def _set_current_topic_from_priority(self, priority_string: str) -> None:
        """CAMPAIGN-AWARE: Parse priority string and set current topic/expected field for extraction"""
        # Map priority strings to expected fields
        field_mapping = {
            'tenure': ('Business Relationship Tenure', 'tenure_with_fc'),
            'nps': ('NPS', 'nps_score'),
            'nps score': ('NPS', 'nps_score'),
            'reasoning': ('NPS Reasoning', 'nps_reasoning'),
            'satisfaction': ('Overall Satisfaction', 'satisfaction_rating'),
            'service': ('Professional Services Quality', 'service_rating'),
            'professional': ('Professional Services Quality', 'service_rating'),
            'product': ('Product Value', 'product_value_rating'),
            'value': ('Product Value', 'product_value_rating'),
            'pricing': ('Pricing Value', 'pricing_rating'),
            'support': ('Support Quality', 'support_rating'),
            'improvement': ('Improvement Suggestions', 'improvement_feedback'),
            'wrap up': ('Completion', None)
        }
        
        priority_lower = priority_string.lower()
        
        # Find matching topic/field
        for keyword, (topic, field) in field_mapping.items():
            if keyword in priority_lower:
                self.current_topic = topic
                self.current_expected_field = field
                logger.debug(f"EXTRACTION: Current topic={topic}, expected field={field}")
                return
        
        # Default: no specific topic identified
        self.current_topic = None
        self.current_expected_field = None
    
    def _generate_ai_question(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate next question using OpenAI with dynamic prompts"""
        try:
            # Format conversation history for context
            history_text = self._format_conversation_history()
            
            # CAMPAIGN-AWARE: Determine what topic/field should be collected next
            next_priority = self._get_next_question_priority()
            self._set_current_topic_from_priority(next_priority)
            
            # Generate dynamic system prompt using template service (with participant data for hybrid prompt)
            system_prompt = self.template_service.generate_system_prompt(
                extracted_data=self.extracted_data,
                step_count=self.step_count,
                conversation_history=history_text,
                participant_data=self.participant_data
            )
            
            # Get campaign language for language-aware final instructions
            campaign_language = self.template_service._campaign_language_code or 'en'
            
            # Build user prompt WITHOUT language-specific instructions (they're in system prompt)
            user_prompt = f"""CUSTOMER'S LATEST RESPONSE: "{user_input}"

NEXT LOGICAL QUESTION PRIORITY:
{next_priority}

RESPONSE FORMAT - Return JSON:
{{
    "message": "Your next question or closing message",
    "message_type": "ai_question",
    "step": "descriptive_step_name",
    "progress": 0-100,
    "is_complete": true/false
}}"""
            
            # Log full prompt for debugging (language issues, prompt effectiveness, etc.)
            self.ai_prompts_log.append({
                'step': self.step_count,
                'timestamp': datetime.utcnow().isoformat(),
                'prompt_type': 'question_generation',
                'system_prompt': system_prompt,
                'user_prompt': user_prompt,
                'language': campaign_language,
                'user_input': user_input[:100]  # Truncate for privacy
            })

            # Model selection via environment variable for cost optimization
            conversation_model = os.environ.get('AI_CONVERSATION_MODEL', 'gpt-4o')
            
            # CRITICAL: Use system/user message structure for proper language enforcement
            response = self.openai_client.chat.completions.create(
                model=conversation_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=300,
                temperature=0.8
            )
            
            content = response.choices[0].message.content
            if content:
                result = json.loads(content)
            else:
                result = {'message': 'Thank you for your feedback!', 'is_complete': True, 'progress': 100}
            
            
            # Ensure progress is reasonable
            if result.get('progress', 0) < self.step_count * 15:
                result['progress'] = min(100, self.step_count * 15)
            
            self.is_complete = result.get('is_complete', False)
            
            return result
            
        except Exception as e:
            logger.debug(f"AI question generation error: {e}")
            return self._generate_fallback_question(user_input, context)
    
    def _format_conversation_history(self) -> str:
        """Format conversation history for AI context"""
        if not self.conversation_history:
            return "This is the start of the conversation."
        
        formatted = []
        for msg in self.conversation_history[-6:]:  # Last 6 messages for context
            sender = msg.get('sender', 'Unknown')
            message = msg.get('message', '')
            formatted.append(f"{sender}: {message}")
        
        return "\n".join(formatted)
    
    def _get_translated_message(self, key: str, **kwargs) -> str:
        """Get translated fallback message based on campaign language"""
        lang = self.template_service.get_language_code()
        company_name = kwargs.get('company_name', '')
        score = kwargs.get('score', '')
        
        messages = {
            'nps_promoter': {
                'en': f"Wonderful! A {score} is fantastic. What specifically about {company_name} made your experience so great?",
                'fr': f"Merveilleux! Un {score} est fantastique. Qu'est-ce qui a rendu votre expérience avec {company_name} si exceptionnelle?"
            },
            'nps_passive': {
                'en': f"Thanks for the {score}! What would it take to make you even more likely to recommend {company_name}?",
                'fr': f"Merci pour ce {score}! Que faudrait-il pour que vous soyez encore plus susceptible de recommander {company_name}?"
            },
            'nps_detractor': {
                'en': f"I appreciate your honesty with the {score}. What are the main issues that are holding you back from recommending {company_name}?",
                'fr': f"J'apprécie votre franchise avec ce {score}. Quels sont les principaux problèmes qui vous empêchent de recommander {company_name}?"
            },
            'nps_question': {
                'en': f"On a scale of 0-10, how likely are you to recommend {company_name} to a friend or colleague?",
                'fr': f"Sur une échelle de 0 à 10, quelle est la probabilité que vous recommandiez {company_name} à un ami ou collègue?"
            },
            'tenure_question': {
                'en': f"How long have you been working with {company_name}? Please choose from: Less than 6 months, 6 months - 1 year, 1-2 years, 2-3 years, 3-5 years, 5-10 years, or More than 10 years.",
                'fr': f"Depuis combien de temps travaillez-vous avec {company_name}? Veuillez choisir parmi: Moins de 6 mois, 6 mois - 1 an, 1-2 ans, 2-3 ans, 3-5 ans, 5-10 ans, ou Plus de 10 ans."
            },
            'satisfaction_question': {
                'en': f"How would you describe your overall satisfaction with {company_name}'s service? Very satisfied, satisfied, neutral, dissatisfied, or very dissatisfied?",
                'fr': f"Comment décririez-vous votre satisfaction globale avec le service de {company_name}? Très satisfait, satisfait, neutre, insatisfait, ou très insatisfait?"
            },
            'service_quality': {
                'en': f"How would you rate the quality of {company_name}'s professional services? Excellent, good, average, poor, or very poor?",
                'fr': f"Comment évalueriez-vous la qualité des services professionnels de {company_name}? Excellent, bon, moyen, médiocre, ou très médiocre?"
            },
            'product_value': {
                'en': f"How would you rate the value and quality of {company_name}'s products or solutions? Excellent, good, average, poor, or very poor?",
                'fr': f"Comment évalueriez-vous la valeur et la qualité des produits ou solutions de {company_name}? Excellent, bon, moyen, médiocre, ou très médiocre?"
            },
            'pricing_value': {
                'en': f"How do you feel about {company_name}'s pricing? Do you find it excellent value, good value, fair, expensive, or very expensive?",
                'fr': f"Que pensez-vous des tarifs de {company_name}? Trouvez-vous qu'ils offrent une excellente valeur, une bonne valeur, sont équitables, chers, ou très chers?"
            },
            'support_quality': {
                'en': f"How would you rate {company_name}'s support and customer service? Excellent, good, average, poor, or very poor?",
                'fr': f"Comment évalueriez-vous le support et le service client de {company_name}? Excellent, bon, moyen, médiocre, ou très médiocre?"
            }
        }
        
        return messages.get(key, {}).get(lang, messages.get(key, {}).get('en', ''))
    
    def _generate_fallback_question(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fixed progression logic based on step count and missing data"""
        extracted = self.extracted_data
        # Get dynamic company name from template service instead of hardcoded values
        company_name = self.template_service.get_company_name()
        
        logger.debug(f"Fallback generation - Step: {self.step_count}, Extracted: {extracted}")
        logger.debug(f"Current extracted data: {self.extracted_data}")
        logger.debug(f"Tenure from extracted_data: {self.extracted_data.get('tenure_with_fc')}")
        logger.debug(f"NPS from extracted_data: {self.extracted_data.get('nps_score')}")
        
        # FIXED: Special case handling without step manipulation
        if (self.extracted_data.get('tenure_with_fc') is not None and 
            self.extracted_data.get('nps_score') is not None and 
            not self.extracted_data.get('nps_reasoning') and
            self.step_count <= 4):
            score = self.extracted_data['nps_score']
            if score >= 9:
                return {
                    'message': self._get_translated_message('nps_promoter', company_name=company_name, score=score),
                    'message_type': 'ai_question',
                    'step': 'nps_reasoning',
                    'progress': 40,
                    'is_complete': False
                }
            elif score >= 7:
                return {
                    'message': self._get_translated_message('nps_passive', company_name=company_name, score=score),
                    'message_type': 'ai_question',
                    'step': 'nps_reasoning',
                    'progress': 40,
                    'is_complete': False
                }
            else:
                return {
                    'message': self._get_translated_message('nps_detractor', company_name=company_name, score=score),
                    'message_type': 'ai_question',
                    'step': 'nps_reasoning',
                    'progress': 40,
                    'is_complete': False
                }
        
        # Use step-based progression but check if we already have tenure data
        if self.step_count == 1:
            # First question: Ask for tenure with {company_name} ONLY if we don't have it
            if self.extracted_data.get('tenure_with_fc') is None:
                return {
                    'message': self._get_translated_message('tenure_question', company_name=company_name),
                    'message_type': 'ai_question',
                    'step': 'tenure_collection',
                    'progress': 15,
                    'is_complete': False
                }
            else:
                # We already have tenure, skip to NPS question
                # Don't manipulate step count - let natural progression continue
                return {
                    'message': self._get_translated_message('nps_question', company_name=company_name),
                    'message_type': 'ai_question',
                    'step': 'nps_collection',
                    'progress': 25,
                    'is_complete': False
                }

        elif self.step_count == 2:
            # Second question: Ask for NPS about {company_name} (the supplier) ONLY if we don't have it
            if self.extracted_data.get('nps_score') is None:
                return {
                    'message': self._get_translated_message('nps_question', company_name=company_name),
                    'message_type': 'ai_question',
                    'step': 'nps_collection',
                    'progress': 25,
                    'is_complete': False
                }
            # If we have NPS but no reasoning, ask for reasoning
            elif not self.extracted_data.get('nps_reasoning'):
                score = self.extracted_data.get('nps_score')
                if score >= 9:
                    return {
                        'message': self._get_translated_message('nps_promoter', company_name=company_name, score=score),
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
                elif score >= 7:
                    return {
                        'message': self._get_translated_message('nps_passive', company_name=company_name, score=score),
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
                else:
                    return {
                        'message': self._get_translated_message('nps_detractor', company_name=company_name, score=score),
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
            else:
                # Move to satisfaction question
                return {
                    'message': self._get_translated_message('satisfaction_question', company_name=company_name),
                    'message_type': 'ai_question',
                    'step': 'satisfaction',
                    'progress': 45,
                    'is_complete': False
                }
        
        elif self.step_count == 3:
            # Check if we just got NPS score and need to ask reasoning question
            if extracted.get('nps_score') is not None or self.extracted_data.get('nps_score') is not None:
                # We just got the NPS score, ask for reasoning
                score = extracted.get('nps_score') or self.extracted_data.get('nps_score')
                if score is not None and score >= 9:
                    return {
                        'message': self._get_translated_message('nps_promoter', company_name=company_name, score=score),
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
                elif score is not None and score >= 7:
                    return {
                        'message': self._get_translated_message('nps_passive', company_name=company_name, score=score),
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
                else:
                    return {
                        'message': self._get_translated_message('nps_detractor', company_name=company_name, score=score),
                        'message_type': 'ai_question',
                        'step': 'nps_reasoning',
                        'progress': 40,
                        'is_complete': False
                    }
            else:
                # Third question: We should have already asked the NPS reasoning question
                # This response is the user's answer to the NPS reasoning question
                # Move to satisfaction question
                return {
                    'message': self._get_translated_message('satisfaction_question', company_name=company_name),
                    'message_type': 'ai_question',
                    'step': 'satisfaction',
                    'progress': 40,
                    'is_complete': False
                }
        
        elif self.step_count == 4:
            # Fourth question: Overall satisfaction rating
            return {
                'message': self._get_translated_message('satisfaction_question', company_name=company_name),
                'message_type': 'ai_question',
                'step': 'satisfaction',
                'progress': 45,
                'is_complete': False
            }
        
        elif self.step_count == 5:
            # Fifth question: Professional services quality rating
            return {
                'message': self._get_translated_message('service_quality', company_name=company_name),
                'message_type': 'ai_question',
                'step': 'service_quality',
                'progress': 50,
                'is_complete': False
            }
        
        elif self.step_count == 6:
            # Sixth question: Product value rating
            return {
                'message': self._get_translated_message('product_value', company_name=company_name),
                'message_type': 'ai_question',
                'step': 'product_value',
                'progress': 55,
                'is_complete': False
            }
        
        elif self.step_count == 7:
            # Seventh question: Pricing appreciation rating
            return {
                'message': self._get_translated_message('pricing_value', company_name=company_name),
                'message_type': 'ai_question',
                'step': 'pricing_value',
                'progress': 65,
                'is_complete': False
            }
        
        elif self.step_count == 8:
            # Eighth question: Support services rating
            return {
                'message': self._get_translated_message('support_quality', company_name=company_name),
                'message_type': 'ai_question',
                'step': 'support_quality',
                'progress': 75,
                'is_complete': False
            }
        
        elif self.step_count == 9:
            # Ninth question: Improvement suggestions
            if extracted.get('nps_score', 0) < 7:
                return {
                    'message': f"What specific changes would make the biggest difference in improving your experience with {company_name}?",
                    'message_type': 'ai_question',
                    'step': 'improvement',
                    'progress': 85,
                    'is_complete': False
                }
            else:
                return {
                    'message': f"Is there anything {company_name} could do even better to enhance your experience?",
                    'message_type': 'ai_question',
                    'step': 'improvement',
                    'progress': 85,
                    'is_complete': False
                }
        
        # Step 10 or higher: Complete the survey
        else:
            return {
                'message': f"Thank you so much for sharing your valuable feedback about {company_name}! Your insights help improve their service for everyone.",
                'message_type': 'conclusion',
                'step': 'conclusion',
                'progress': 100,
                'is_complete': True
            }
    
    def finalize_survey(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Convert conversational data to structured survey format"""
        extracted = self.extracted_data
        
        # Ensure we have at least minimum required data by analyzing conversation history
        if not extracted.get('nps_score') and self.conversation_history:
            self._extract_missing_data_from_history()
        
        # Combine all feedback text
        feedback_parts = []
        for key in ['nps_reasoning', 'improvement_feedback', 'compliment_feedback', 'complaint_feedback', 'additional_comments']:
            if extracted.get(key):
                feedback_parts.append(extracted[key])
        
        combined_feedback = ' '.join(feedback_parts) if feedback_parts else None
        
        # Ensure required fields have values or reasonable defaults
        nps_score = extracted.get('nps_score')
        if nps_score is None:
            # Try to extract from conversation history as fallback
            nps_score = self._extract_nps_from_history()
        
        # Set default NPS category if score exists
        nps_category = extracted.get('nps_category')
        if nps_score is not None and not nps_category:
            if nps_score >= 9:
                nps_category = 'Promoter'
            elif nps_score >= 7:
                nps_category = 'Passive'
            else:
                nps_category = 'Detractor'
        
        return {
            'company_name': normalize_company_name(context.get('company_name')),
            'respondent_name': context.get('respondent_name'),
            'respondent_email': context.get('respondent_email'),
            'tenure_with_fc': extracted.get('tenure_with_fc'),
            'nps_score': nps_score,
            'nps_category': nps_category,
            'satisfaction_rating': extracted.get('satisfaction_rating'),
            'service_rating': extracted.get('support_rating') or extracted.get('service_rating'),  # Support questions map to service_rating
            'pricing_rating': extracted.get('pricing_rating'),
            'product_value_rating': extracted.get('product_value_rating'),  # Product value rating
            'improvement_feedback': extracted.get('improvement_feedback'),
            'recommendation_reason': extracted.get('nps_reasoning'),
            'additional_comments': combined_feedback,
            'conversation_history': json.dumps(self.conversation_history),
            'ai_prompts_log': json.dumps(self.ai_prompts_log) if self.ai_prompts_log else None
        }
    
    def _extract_missing_data_from_history(self):
        """Extract missing survey data from conversation history as fallback"""
        conversation_text = ' '.join([msg.get('message', '') for msg in self.conversation_history if msg.get('sender') == 'User'])
        
        # Try to extract NPS score using sophisticated pattern matching (reused from fallback)
        import re
        
        # Use sophisticated NPS patterns that avoid "1 from '1 to 10'" false matches
        nps_patterns = [
            r'(?:score|rating|give|rate).*?(10|[0-9])',  # 10 before single digits
            r'^(10|[0-9])(?:\s|$|/|,|\.)',
            r'(10|[0-9])\s*(?:out of 10|/10)',
            r'(?:i.*d.*say|i.*d.*give|i.*d.*rate).*?(10|[0-9])',
            r'(?:probably|maybe|around|about).*?(10|[0-9])',
            r'\b(10|[0-9])\b(?!\d)',
            r'(10|[0-9])',
            r'(?:is|was|would be|rating|score).*?(10|[0-9])',
            r'(10|[0-9])(?:\s*(?:stars?|points?|rating))?'
        ]
        
        # Look for NPS in user responses
        for msg in self.conversation_history:
            if msg.get('sender') == 'User':
                message = msg.get('message', '')
                for pattern in nps_patterns:
                    matches = re.findall(pattern, message, re.IGNORECASE)
                    if matches:
                        # Use LAST match to handle "scale of 1 to 10, I give it 7" → extracts 7, not 1
                        match = matches[-1]
                        score = int(match)
                        if 0 <= score <= 10:
                            self.extracted_data['nps_score'] = score
                            if score >= 9:
                                self.extracted_data['nps_category'] = 'Promoter'
                            elif score >= 7:
                                self.extracted_data['nps_category'] = 'Passive'
                            else:
                                self.extracted_data['nps_category'] = 'Detractor'
                            logger.debug(f"NPS extracted from history: {score}")
                            break
                if 'nps_score' in self.extracted_data:
                    break
        
        # Extract satisfaction keywords
        text_lower = conversation_text.lower()
        if not self.extracted_data.get('satisfaction_rating'):
            if any(word in text_lower for word in ['very satisfied', 'extremely satisfied']):
                self.extracted_data['satisfaction_rating'] = 5
            elif any(word in text_lower for word in ['satisfied', 'happy', 'pleased']):
                self.extracted_data['satisfaction_rating'] = 4
            elif any(word in text_lower for word in ['neutral', 'okay', 'fine']):
                self.extracted_data['satisfaction_rating'] = 3
            elif any(word in text_lower for word in ['dissatisfied', 'unhappy', 'disappointed']):
                self.extracted_data['satisfaction_rating'] = 2
            elif any(word in text_lower for word in ['very dissatisfied', 'terrible', 'awful']):
                self.extracted_data['satisfaction_rating'] = 1
    
    def _extract_nps_from_history(self):
        """Extract NPS score from conversation history using sophisticated pattern matching"""
        import re
        
        # Use sophisticated NPS patterns that avoid "1 from '1 to 10'" false matches
        nps_patterns = [
            r'(?:score|rating|give|rate).*?(10|[0-9])',  # 10 before single digits
            r'^(10|[0-9])(?:\s|$|/|,|\.)',
            r'(10|[0-9])\s*(?:out of 10|/10)',
            r'(?:i.*d.*say|i.*d.*give|i.*d.*rate).*?(10|[0-9])',
            r'(?:probably|maybe|around|about).*?(10|[0-9])',
            r'\b(10|[0-9])\b(?!\d)',
            r'(10|[0-9])',
            r'(?:is|was|would be|rating|score).*?(10|[0-9])',
            r'(10|[0-9])(?:\s*(?:stars?|points?|rating))?'
        ]
        
        for msg in self.conversation_history:
            if msg.get('sender') == 'User':
                message = msg.get('message', '')
                for pattern in nps_patterns:
                    matches = re.findall(pattern, message, re.IGNORECASE)
                    if matches:
                        # Use LAST match to handle "scale of 1 to 10, I give it 7" → extracts 7, not 1
                        match = matches[-1]
                        score = int(match)
                        if 0 <= score <= 10:
                            logger.debug(f"NPS extracted from history via finalize: {score}")
                            return score
        return None


# Global instances for session persistence
ai_conversation_instances = {}


def save_conversation_state(conversation_id: str, ai_survey: 'AIConversationalSurvey'):
    """Save conversation state to database for persistence across workers and restarts"""
    try:
        from app import db
        from models import ActiveConversation
        from datetime import datetime
        import json
        import logging
        
        logger = logging.getLogger(__name__)
        
        conversation_data = {
            'conversation_history': json.dumps(ai_survey.conversation_history),
            'extracted_data': json.dumps(ai_survey.extracted_data),
            'survey_data': json.dumps(ai_survey.survey_data),
            'step_count': ai_survey.step_count,
            'business_account_id': ai_survey.business_account_id,
            'campaign_id': ai_survey.campaign_id,
            'participant_data': json.dumps(ai_survey.participant_data) if ai_survey.participant_data else None
        }
        
        existing = ActiveConversation.query.filter_by(conversation_id=conversation_id).first()
        
        if existing:
            for key, value in conversation_data.items():
                setattr(existing, key, value)
            existing.last_updated = datetime.utcnow()
        else:
            new_conversation = ActiveConversation(
                conversation_id=conversation_id,
                **conversation_data
            )
            db.session.add(new_conversation)
        
        db.session.commit()
        logger.debug(f"Conversation state saved for {conversation_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving conversation state for {conversation_id}: {e}")
        db.session.rollback()
        return False


def load_conversation_state(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Load conversation state from database"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from models import ActiveConversation
        import json
        
        session = ActiveConversation.query.filter_by(conversation_id=conversation_id).first()
        
        if not session:
            logger.debug(f"No persisted state found for conversation {conversation_id}")
            return None
        
        state = {
            'conversation_history': json.loads(session.conversation_history) if session.conversation_history else [],
            'extracted_data': json.loads(session.extracted_data) if session.extracted_data else {},
            'survey_data': json.loads(session.survey_data) if session.survey_data else {},
            'step_count': session.step_count,
            'business_account_id': session.business_account_id,
            'campaign_id': session.campaign_id,
            'participant_data': json.loads(session.participant_data) if session.participant_data else None
        }
        
        logger.debug(f"Loaded conversation state for {conversation_id}: step {state['step_count']}")
        return state
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error loading conversation state for {conversation_id}: {e}")
        return None


def delete_conversation_state(conversation_id: str):
    """Delete conversation state from database after finalization"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from app import db
        from models import ActiveConversation
        
        session = ActiveConversation.query.filter_by(conversation_id=conversation_id).first()
        if session:
            db.session.delete(session)
            db.session.commit()
            logger.debug(f"Deleted conversation state for {conversation_id}")
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting conversation state for {conversation_id}: {e}")
        db.session.rollback()

def start_ai_conversational_survey(company_name: str, respondent_name: str, tenure_with_fc=None, business_account_id: Optional[int] = None, campaign_id: Optional[int] = None, participant_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Start a new AI-powered conversational survey session with optional participant segmentation data"""
    conversation_id = str(uuid.uuid4())
    ai_survey = AIConversationalSurvey(business_account_id=business_account_id, campaign_id=campaign_id, participant_data=participant_data)
    
    # If tenure data is provided from the form, pre-populate it
    if tenure_with_fc:
        ai_survey.extracted_data['tenure_with_fc'] = tenure_with_fc
        logger.debug(f"Pre-populated tenure from form: {tenure_with_fc}")
    
    result = ai_survey.start_conversation(company_name, respondent_name)
    result['conversation_id'] = conversation_id
    
    # Store instance for session persistence
    ai_conversation_instances[conversation_id] = ai_survey
    
    save_conversation_state(conversation_id, ai_survey)
    
    return result

def process_ai_conversation_response(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Process user's conversational response with AI"""
    conversation_id = context.get('conversation_id')
    
    logger.debug(f" Processing conversation_id: {conversation_id}")
    logger.debug(f" Available instances: {list(ai_conversation_instances.keys())}")
    logger.debug(f" Context keys: {list(context.keys())}")
    
    if conversation_id and conversation_id in ai_conversation_instances:
        ai_survey = ai_conversation_instances[conversation_id]
        logger.debug(f" Found existing instance with step {ai_survey.step_count}, extracted data: {ai_survey.extracted_data}")
        response = ai_survey.process_user_response(user_input, context)
        
        save_conversation_state(conversation_id, ai_survey)
        
        return response
    else:
        logger.warning(f" No instance found for conversation_id {conversation_id}, attempting database recovery")
        logger.debug(f"INSTANCES: {ai_conversation_instances}")
        
        persisted_state = load_conversation_state(conversation_id)
        
        if persisted_state:
            logger.info(f"RECOVERY: Found persisted state, step {persisted_state['step_count']}")
            business_account_id = persisted_state['business_account_id']
            campaign_id = persisted_state['campaign_id']
            participant_data = persisted_state['participant_data']
            
            ai_survey = AIConversationalSurvey(business_account_id=business_account_id, campaign_id=campaign_id, participant_data=participant_data)
            ai_survey.conversation_history = persisted_state['conversation_history']
            ai_survey.extracted_data = persisted_state['extracted_data']
            ai_survey.survey_data = persisted_state['survey_data']
            ai_survey.step_count = persisted_state['step_count']
            
            ai_conversation_instances[conversation_id] = ai_survey
            
        else:
            logger.debug(f"No database state, recreating from client context")
            business_account_id = context.get('business_account_id')
            campaign_id = context.get('campaign_id')
            participant_data = context.get('participant_data')
            ai_survey = AIConversationalSurvey(business_account_id=business_account_id, campaign_id=campaign_id, participant_data=participant_data)
            
            company_name = context.get('company_name', '')
            respondent_name = context.get('respondent_name', '')
            
            ai_survey.survey_data = {
                'company_name': company_name,
                'respondent_name': respondent_name,
                'conversation_history': context.get('conversation_history', []),
                'extracted_data': context.get('extracted_data', {})
            }
            
            ai_survey.extracted_data = ai_survey.survey_data['extracted_data']
            ai_survey.step_count = context.get('step_count', len(context.get('conversation_history', [])) // 2)
            
            logger.debug(f"Recreated instance with step {ai_survey.step_count}, extracted data: {ai_survey.extracted_data}")
            
            if conversation_id:
                ai_conversation_instances[conversation_id] = ai_survey
        
        response = ai_survey.process_user_response(user_input, context)
        
        save_conversation_state(conversation_id, ai_survey)
        
        return response

def finalize_ai_conversational_survey(context: Dict[str, Any]) -> Dict[str, Any]:
    """Finalize and convert AI conversational survey to structured format"""
    conversation_id = context.get('conversation_id')
    
    logger.debug(f"Finalizing conversation {conversation_id}")
    logger.debug(f"Available instances: {list(ai_conversation_instances.keys())}")
    
    ai_survey = None
    
    if conversation_id and conversation_id in ai_conversation_instances:
        ai_survey = ai_conversation_instances[conversation_id]
        logger.debug(f"Found in-memory AI survey instance with extracted data: {ai_survey.extracted_data}")
    else:
        logger.debug("No in-memory instance found - attempting database recovery")
        persisted_state = load_conversation_state(conversation_id)
        
        if persisted_state:
            logger.info(f"RECOVERY (finalize): Found persisted state, step {persisted_state['step_count']}")
            business_account_id = persisted_state['business_account_id']
            campaign_id = persisted_state['campaign_id']
            participant_data = persisted_state['participant_data']
            
            ai_survey = AIConversationalSurvey(business_account_id=business_account_id, campaign_id=campaign_id, participant_data=participant_data)
            ai_survey.conversation_history = persisted_state['conversation_history']
            ai_survey.extracted_data = persisted_state['extracted_data']
            ai_survey.survey_data = persisted_state['survey_data']
            ai_survey.step_count = persisted_state['step_count']
        else:
            logger.debug("FALLBACK (finalize): No database state, using client context")
    
    if ai_survey:
        logger.debug(f"Using AI survey instance with extracted data: {ai_survey.extracted_data}")
        
        finalization_context = {
            'company_name': ai_survey.survey_data.get('company_name'),
            'respondent_name': ai_survey.survey_data.get('respondent_name'),
            'respondent_email': context.get('respondent_email')
        }
        
        result = ai_survey.finalize_survey(finalization_context)
        logger.debug(f"Finalized result: {result}")
        
        # CRITICAL: Inject server-controlled ai_prompts_log for debugging (don't trust client data)
        result['ai_prompts_log'] = json.dumps(ai_survey.ai_prompts_log) if ai_survey.ai_prompts_log else None
        
        if conversation_id in ai_conversation_instances:
            del ai_conversation_instances[conversation_id]
        
        delete_conversation_state(conversation_id)
        
        return result
    else:
        logger.debug("CLIENT FALLBACK: No instance or database state found - using context")
        survey_data = context.get('survey_data', {})
        extracted_data = survey_data.get('extracted_data', {})
        
        logger.debug(f"Fallback survey_data: {survey_data}")
        logger.debug(f"Fallback extracted_data: {extracted_data}")
        
        raw_company_name = context.get('company_name') or survey_data.get('company_name')
        return {
            'company_name': normalize_company_name(raw_company_name),
            'respondent_name': context.get('respondent_name') or survey_data.get('respondent_name'),
            'respondent_email': context.get('respondent_email'),
            'nps_score': extracted_data.get('nps_score'),
            'nps_category': extracted_data.get('nps_category'),
            'satisfaction_rating': extracted_data.get('satisfaction_rating'),
            'improvement_feedback': extracted_data.get('improvement_feedback'),
            'recommendation_reason': extracted_data.get('nps_reasoning'),
            'additional_comments': extracted_data.get('additional_comments'),
            'conversation_history': context.get('conversation_history', json.dumps([]))
        }