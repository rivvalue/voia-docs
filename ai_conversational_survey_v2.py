"""
Deterministic Conversational Survey Controller (V2)
====================================================

VOÏA backend-controlled survey flow that eliminates LLM-driven completion bugs.

Key Design Principles:
- Backend controls flow decisions (completion, topic selection)
- LLM performs only extraction and question generation
- No LLM authority over survey progression
- Per-topic follow-up limits with must-ask bypass

Created: November 23, 2025
Feature Flag: DETERMINISTIC_SURVEY_FLOW

ROLLBACK PROCEDURE (Revised Extraction Prompt)
===============================================
If the revised extraction prompt (Nov 2025) causes issues, rollback immediately:

1. Set environment variable:
   USE_REVISED_EXTRACTION_PROMPT=false

2. Restart the workflow:
   - In Replit UI: Click "Stop" then "Run" on the workflow
   - Or use: `pkill gunicorn && gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`

3. Verify rollback:
   - Check logs for "ORIGINAL extraction prompt" messages
   - Complete a test survey and verify data extraction works

The system will automatically revert to the original prompt (pre-Nov 2025) which uses:
- Direct database field names (satisfaction_rating, pricing_rating, etc.)
- No field mapping layer
- Original validation rules

To re-enable the revised prompt:
   USE_REVISED_EXTRACTION_PROMPT=true (or remove the variable, defaults to true)
"""

import os
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
from openai import OpenAI

# VOÏA infrastructure
from app import db
from models import Campaign, Participant, BusinessAccount
from prompt_template_service import PromptTemplateService

# V2-specific modules
from deterministic_helpers import (
    all_goals_completed,
    get_next_goal,
    build_role_exclusions,
    extract_prefilled_fields
)
from session_state_utils import (
    initialize_deterministic_state,
    save_deterministic_state,
    load_deterministic_state,
    delete_deterministic_state,
    update_last_activity
)

logger = logging.getLogger(__name__)


# ============================================================================
# EXTRACTION PROMPT CONFIGURATION
# ============================================================================
# Feature flag for revised extraction prompt (Nov 2025)
# Set USE_REVISED_EXTRACTION_PROMPT=false to rollback to original prompt
USE_REVISED_EXTRACTION_PROMPT = os.environ.get('USE_REVISED_EXTRACTION_PROMPT', 'true').lower() == 'true'

# Field mapping: Prompt field names → Database column names
# Allows descriptive prompt fields while maintaining DB compatibility
EXTRACTION_TO_DB_FIELD_MAP = {
    # Ratings (prompt uses descriptive names)
    'overall_satisfaction_rating': 'satisfaction_rating',
    'pricing_value_rating': 'pricing_rating',
    'service_rating': 'service_rating',  # Already matches
    'product_appreciation_rating': 'product_value_rating',
    
    # NPS (recommendation metrics, separate from satisfaction)
    'nps_score': 'nps_score',  # Already matches
    'nps_reasoning': 'recommendation_reason',
    
    # Text feedback
    'detailed_feedback': 'general_feedback',
    'pricing_satisfaction': 'improvement_feedback',
    
    # Arrays (needs JSON serialization)
    'feature_requests': 'feature_requests',
    
    # Support rating (already matches, kept for completeness)
    'support_rating': 'support_rating'
}


def _mask_pii(text, max_length=100):
    """Mask PII and truncate text for logging"""
    if not text:
        return text
    if isinstance(text, dict):
        return {k: _mask_pii(v) if k not in ['conversation_id', 'step_count'] else v 
                for k, v in list(text.items())[:5]}
    text_str = str(text)
    if len(text_str) > max_length:
        return text_str[:max_length] + "... [truncated]"
    return text_str


class DeterministicSurveyController:
    """
    V2 Controller: Backend-controlled deterministic survey flow
    
    Eliminates early-stop bugs by removing LLM authority over:
    1. Survey completion decisions
    2. Topic selection and progression
    3. Follow-up question necessity
    
    LLM performs ONLY:
    1. Data extraction from user responses (sparse JSON)
    2. Question generation for specified topic (no flow decisions)
    """
    
    def __init__(
        self,
        business_account_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        participant_data: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None
    ):
        """
        Initialize V2 controller with deterministic flow control.
        
        Args:
            business_account_id: Business account ID for multi-tenant isolation
            campaign_id: Campaign ID for survey configuration
            participant_data: Participant metadata (role, tenure, etc.)
            conversation_id: Optional conversation ID for resume functionality
        """
        # OpenAI client for LLM stubs
        self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
        # Store IDs
        self.business_account_id = business_account_id
        self.campaign_id = campaign_id
        self.participant_data = participant_data or {}
        self.conversation_id = conversation_id or str(uuid.uuid4())
        
        # Load campaign configuration
        self.campaign = Campaign.query.filter_by(id=campaign_id).first() if campaign_id else None
        self.business_account = BusinessAccount.query.filter_by(id=business_account_id).first() if business_account_id else None
        
        # Get language from campaign or session (FIX Nov 23, 2025)
        from flask import session
        self.language = None
        if self.campaign and hasattr(self.campaign, 'language_code'):
            self.language = self.campaign.language_code
        elif 'language' in session:
            self.language = session.get('language', 'en')
        else:
            self.language = 'en'  # Default fallback
        
        # Initialize prompt template service for campaign-specific prompts
        # FIX (Nov 23, 2025): Pass campaign object and language to avoid session/language issues
        self.template_service = PromptTemplateService(
            business_account_id=business_account_id,
            campaign_id=campaign_id,
            campaign=self.campaign,  # Pass object to avoid session detachment
            language=self.language   # Pass language for AI prompt enforcement
        )
        
        # V2 State (will be loaded from session or initialized fresh)
        self.extracted_data: Dict[str, Any] = {}
        self.conversation_history: List[Dict] = []
        self.current_goal_pointer: Optional[str] = None
        self.topic_question_counts: Dict[str, int] = {}
        self.step_count: int = 0
        self.is_complete: bool = False
        
        # Build deterministic goals with role/industry filtering
        self.goals = self._build_filtered_goals()
        self.prefilled_fields = self._load_prefilled_fields()
        self.role_excluded_topics = build_role_exclusions(
            self.participant_data.get('role')
        )
        
        # Campaign limits
        self.max_follow_up_per_topic = getattr(self.campaign, 'max_follow_up_per_topic', 2) if self.campaign else 2
        self.max_questions = self.template_service.get_template_info().get('max_questions', 15)
        
        # Track AI prompts for debugging
        self.ai_prompts_log = []
        
        logger.info(f"V2 Controller initialized: conv_id={self.conversation_id}, "
                   f"campaign={campaign_id}, goals={len(self.goals)}, "
                   f"prefilled={len(self.prefilled_fields)}")
    
    def start_conversation(self, company_name: str, respondent_name: str) -> Dict[str, Any]:
        """
        Start new V2 conversational survey with deterministic flow.
        
        Args:
            company_name: Company name for personalization
            respondent_name: Respondent name for greeting
        
        Returns:
            Response dict with welcome message and conversation_id
        """
        logger.info(f"Starting V2 conversation for {company_name}")
        
        # Initialize fresh state
        state = initialize_deterministic_state(
            conversation_id=self.conversation_id,
            campaign_id=self.campaign_id or 0,
            participant_id=self.participant_data.get('id') or 0,
            business_account_id=self.business_account_id or 0
        )
        
        # Update controller state
        self.extracted_data = state['extracted_data']
        self.conversation_history = state['conversation_history']
        self.current_goal_pointer = state['current_goal_pointer']
        self.topic_question_counts = state['topic_question_counts']
        self.step_count = state['step_count']
        
        # FIX (Nov 23, 2025): Store company_name and respondent_name for finalization
        # These are required NOT NULL fields in database
        self.extracted_data['company_name'] = company_name
        self.extracted_data['respondent_name'] = respondent_name
        
        # Pre-populate from participant data
        if self.participant_data.get('tenure_with_fc'):
            self.extracted_data['tenure_with_fc'] = self.participant_data['tenure_with_fc']
            logger.debug(f"Pre-populated tenure: {self.participant_data['tenure_with_fc']}")
        
        # Generate welcome message (using V1 template service for consistency)
        welcome_message = self._generate_welcome_message(company_name, respondent_name)
        
        # Add to conversation history
        self.conversation_history.append({
            'sender': 'VOÏA',
            'message': welcome_message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Save initial state
        save_deterministic_state(self.conversation_id, self._get_state_dict())
        
        return {
            'message': welcome_message,
            'message_type': 'welcome',
            'step': 'welcome',
            'progress': 10,
            'is_complete': False,
            'conversation_id': self.conversation_id,
            'extracted_data': self.extracted_data,
            'controller_version': 'v2_deterministic'
        }
    
    def process_user_response(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user response with deterministic backend-controlled flow.
        
        This is the main orchestration method that:
        1. Extracts data (LLM stub - no flow decisions)
        2. Checks completion (backend decision)
        3. Selects next goal (backend decision with follow-up limits)
        4. Generates question (LLM stub for specific topic)
        
        Args:
            user_input: User's response text
            context: Additional context (not used in V2)
        
        Returns:
            Response dict with next question or completion message
        """
        # Add user message to conversation history
        self.conversation_history.append({
            'sender': 'User',
            'message': user_input,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Increment step count BEFORE processing
        self.step_count += 1
        
        logger.info(f"V2 Step {self.step_count}: Processing user response")
        logger.debug(f"User input: {_mask_pii(user_input)}")
        
        # STEP 1: Extract data (LLM performs extraction ONLY, no flow decisions)
        new_fields = self._extract_with_ai(user_input)
        self.extracted_data.update(new_fields)
        
        logger.debug(f"Extracted {len(new_fields)} new fields: {list(new_fields.keys())}")
        logger.debug(f"Total extracted: {len(self.extracted_data)} fields")
        
        # STEP 2: Check backend-controlled completion criteria
        # CRITICAL: Backend decides, NOT LLM
        if self._should_complete_survey():
            logger.info(f"✅ BACKEND COMPLETION: Survey ended by V2 controller at step {self.step_count}")
            return self._finish_survey()
        
        # STEP 3: Get next goal (backend decision with per-topic follow-up limits)
        next_goal, missing_fields, is_follow_up = get_next_goal(
            goals=self.goals,
            extracted_data=self.extracted_data,
            prefilled_fields=self.prefilled_fields,
            current_goal_pointer=self.current_goal_pointer,
            topic_question_counts=self.topic_question_counts,
            max_follow_up_per_topic=self.max_follow_up_per_topic,
            allow_multi_turn=True,
            role_excluded_topics=self.role_excluded_topics
        )
        
        if not next_goal:
            logger.info("No more goals - survey complete")
            return self._finish_survey()
        
        topic_name = next_goal.get('topic', 'Unknown')
        
        # STEP 4: Generate question for chosen topic (LLM generates question ONLY)
        question = self._generate_question_with_ai(next_goal, missing_fields, is_follow_up)
        
        # STEP 5: Update state (increment counter, set pointer)
        # CRITICAL: Increment counter AFTER question generated (before next turn)
        self.topic_question_counts[topic_name] = self.topic_question_counts.get(topic_name, 0) + 1
        self.current_goal_pointer = topic_name
        
        logger.info(f"Topic '{topic_name}' question count: {self.topic_question_counts[topic_name]}")
        
        # Add VOÏA question to conversation history
        self.conversation_history.append({
            'sender': 'VOÏA',
            'message': question,
            'timestamp': datetime.utcnow().isoformat(),
            'topic': topic_name,
            'is_follow_up': is_follow_up
        })
        
        # Save state to database
        save_deterministic_state(self.conversation_id, self._get_state_dict())
        
        # Calculate progress
        progress = self._calculate_progress()
        
        return {
            'message': question,
            'message_type': 'question',
            'step': f'step_{self.step_count}',
            'progress': progress,
            'is_complete': False,
            'topic': topic_name,
            'is_follow_up': is_follow_up,
            'extracted_data': self.extracted_data,
            'controller_version': 'v2_deterministic'
        }
    
    def _map_extracted_fields_to_db(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map LLM extraction field names to database column names.
        
        Handles:
        - Field name translation (overall_satisfaction_rating → satisfaction_rating)
        - Feature requests JSON serialization (array → JSON string)
        - Rating range validation (NPS: 0-10, others: 0-5 scale enforcement)
        - Both revised and original prompt field names for compatibility
        
        Args:
            extracted_data: Raw extraction from LLM (with prompt field names)
        
        Returns:
            Database-ready dict (with DB column names)
        """
        db_ready = {}
        
        for prompt_field, value in extracted_data.items():
            if value is None or value == '':
                continue  # Skip nulls/empties (sparse JSON)
            
            # Get database column name (or use prompt field if no mapping exists)
            db_field = EXTRACTION_TO_DB_FIELD_MAP.get(prompt_field, prompt_field)
            
            # Special handling: feature_requests array → JSON string
            if db_field == 'feature_requests' and isinstance(value, list):
                db_ready[db_field] = json.dumps(value)
                continue
            
            # Rating validation with scale-specific ranges
            if db_field in ['nps_score', 'satisfaction_rating', 'pricing_rating', 
                           'service_rating', 'product_value_rating', 'support_rating']:
                if isinstance(value, (int, float)):
                    # NPS uses 0-10 scale, others use 0-5 scale
                    if db_field == 'nps_score':
                        max_value = 10
                    else:
                        max_value = 5
                    
                    # Clamp to valid range
                    validated_rating = max(0, min(max_value, int(round(value))))
                    if validated_rating != value:
                        logger.warning(f"Rating out of range: {prompt_field}={value}, clamped to {validated_rating} (scale: 0-{max_value})")
                    db_ready[db_field] = validated_rating
                else:
                    logger.warning(f"Non-numeric rating ignored: {prompt_field}={value}")
                continue
            
            # Default: use value as-is
            db_ready[db_field] = value
        
        logger.debug(f"Field mapping: {len(extracted_data)} prompt fields → {len(db_ready)} DB fields")
        return db_ready
    
    def _extract_with_ai(self, user_message: str) -> Dict[str, Any]:
        """
        LLM Stub 1: Extract structured data from user response.
        
        CRITICAL: This stub performs ONLY extraction, NO flow decisions.
        No "is_complete" flag, no "needs_followup" flag.
        
        Returns sparse JSON (only fields mentioned, no null pollution).
        
        Args:
            user_message: User's response text
        
        Returns:
            Dict of extracted field_name -> value (sparse, no nulls)
        """
        # Build extraction prompt with static context
        extraction_prompt = self._build_extraction_prompt(user_message)
        
        logger.debug(f"Calling LLM for extraction (no flow decisions)")
        
        try:
            # Log prompt for debugging
            self.ai_prompts_log.append({
                'type': 'extraction',
                'prompt': extraction_prompt[:500],  # Truncate for logging
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Call OpenAI for extraction
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use cost-optimized model for extraction
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Extract structured data from user responses. Return ONLY mentioned fields (sparse JSON, no nulls)."},
                    {"role": "user", "content": extraction_prompt}
                ],
                temperature=0.0,  # Deterministic extraction
                response_format={"type": "json_object"}
            )
            
            extracted_json = response.choices[0].message.content
            if extracted_json:
                raw_extracted = json.loads(extracted_json)
            else:
                raw_extracted = {}
            
            logger.debug(f"LLM extracted (raw): {_mask_pii(raw_extracted)}")
            
            # Map to database field names ONLY if using revised prompt
            # This ensures rollback works correctly (old prompt = no mapping)
            if USE_REVISED_EXTRACTION_PROMPT:
                mapped_data = self._map_extracted_fields_to_db(raw_extracted)
                logger.debug(f"LLM extracted (mapped): {_mask_pii(mapped_data)}")
                return mapped_data
            else:
                # Original prompt returns data with DB column names already
                logger.debug(f"LLM extracted (original prompt, no mapping): {_mask_pii(raw_extracted)}")
                return raw_extracted
            
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return {}  # Fail gracefully, return empty dict
    
    def _generate_question_with_ai(
        self,
        goal: Dict,
        missing_fields: List[str],
        is_follow_up: bool
    ) -> str:
        """
        LLM Stub 2: Generate natural language question for specific topic.
        
        CRITICAL: This stub performs ONLY question generation, NO flow decisions.
        Backend has already decided which topic to ask about.
        
        Args:
            goal: Goal dict with topic name and fields
            missing_fields: List of fields still needed for this topic
            is_follow_up: True if this is a clarifying question on same topic
        
        Returns:
            Natural language question string
        """
        topic_name = goal.get('topic', 'Unknown')
        
        # Build question generation prompt with static context
        question_prompt = self._build_question_prompt(goal, missing_fields, is_follow_up)
        
        logger.debug(f"Calling LLM for question generation on topic '{topic_name}' (follow-up: {is_follow_up})")
        
        try:
            # Log prompt for debugging
            self.ai_prompts_log.append({
                'type': 'question_generation',
                'topic': topic_name,
                'is_follow_up': is_follow_up,
                'prompt': question_prompt[:500],  # Truncate for logging
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Build language-aware system prompt (FIX Nov 23, 2025)
            language_instruction = ""
            if self.language and self.language != 'en':
                language_map = {
                    'fr': 'French',
                    'es': 'Spanish',
                    'de': 'German',
                    'it': 'Italian',
                    'pt': 'Portuguese'
                }
                language_name = language_map.get(self.language, self.language)
                language_instruction = f"\n\nIMPORTANT: Generate the question in {language_name} language. The entire conversation must remain in {language_name}."
            
            system_prompt = f"You are a conversational survey assistant. Generate natural, engaging questions for the specified topic.{language_instruction}"
            
            # Call OpenAI for question generation
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use cost-optimized model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question_prompt}
                ],
                temperature=0.7  # Allow some creativity in phrasing
            )
            
            question_content = response.choices[0].message.content
            question = question_content.strip() if question_content else self._fallback_question(topic_name, is_follow_up)
            
            logger.debug(f"LLM generated question: {_mask_pii(question)}")
            
            return question
            
        except Exception as e:
            logger.error(f"Question generation error: {e}")
            # Fallback to template-based question
            return self._fallback_question(topic_name, is_follow_up)
    
    def _build_extraction_prompt(self, user_message: str) -> str:
        """
        Build LLM prompt for data extraction with static context blocks.
        
        Feature flag: USE_REVISED_EXTRACTION_PROMPT controls which prompt version to use
        - Revised (Nov 2025): Enhanced rating fields, explicit parsing rules, NPS/satisfaction separation
        - Original: Legacy prompt for rollback safety
        
        Returns SPARSE JSON (only mentioned fields, no nulls).
        """
        # Get static context from campaign/participant
        company_name = self.participant_data.get('company_name', 'the company')
        product_description = getattr(self.campaign, 'product_description', 'our services')
        industry = self.participant_data.get('client_industry', 'your industry')
        role = self.participant_data.get('role', 'team member')
        
        # Recent conversation context (last 6 messages for pronoun resolution)
        recent_history = self.conversation_history[-6:] if len(self.conversation_history) > 6 else self.conversation_history
        context_snippet = "\n".join([
            f"{msg['sender']}: {msg['message'][:100]}" 
            for msg in recent_history
        ])
        
        # Use feature flag to select prompt version
        if USE_REVISED_EXTRACTION_PROMPT:
            return self._build_revised_extraction_prompt(user_message, company_name, product_description, industry, role, context_snippet)
        else:
            return self._build_original_extraction_prompt(user_message, company_name, product_description, industry, role, context_snippet)
    
    def _build_revised_extraction_prompt(self, user_message: str, company_name: str, product_description: str, industry: str, role: str, context_snippet: str) -> str:
        """
        REVISED extraction prompt (Nov 2025)
        
        Key improvements:
        - Consolidated service/support into single service_rating field
        - Clear NPS (recommendation) vs overall satisfaction separation
        - Explicit rating parsing rules (7/10 → 7, no adjective guessing)
        - Scale normalization instructions for 5-point → 10-point conversion
        """
        prompt = f"""Extract structured data from the user's response below.

**STATIC CONTEXT (for understanding only, do NOT restate):**
- Company: {company_name}
- Product/Service: {product_description}
- Industry: {industry}
- Participant Role: {role}

**RECENT CONVERSATION:**
{context_snippet}

**USER'S LATEST RESPONSE:**
{user_message}

**FIELDS YOU MAY FILL:**
You may fill any of the following fields if the information is clearly present in the current response (or clearly implied from the response + context):

- nps_score (0–10 integer; likelihood to recommend)
- nps_reasoning (string; why that score)
- overall_satisfaction_rating (0–5 integer; overall satisfaction, distinct from NPS)
- detailed_feedback (string; general comments, problems, positives)
- pricing_satisfaction (string; perception of price vs value, in text)
- pricing_value_rating (0–5 integer; numeric rating of price/value fairness)
- service_rating (0–5 integer; ALL service/support/account management/professional services)
- product_appreciation_rating (0–5 integer; how much they like the product itself)
- feature_requests (array of strings; concrete requested features or capabilities)

**RATING RULES:**
- Only fill a numeric rating field when the user gives an explicit number for that aspect
  (e.g., "I'd give it 7", "7/10", "je dirais 8", "support is 4 out of 5").
- Map the number to the correct field based on what the user is rating:
  - overall / global satisfaction → overall_satisfaction_rating (0-5 scale)
  - recommendation likelihood → nps_score (0-10 scale)
  - service, support, account management, professional services → service_rating (0-5 scale)
  - price, value for money, cost vs benefit → pricing_value_rating (0-5 scale)
  - the product itself / tool / platform → product_appreciation_rating (0-5 scale)
- **SCALE HANDLING:**
  - For NPS (recommendation): Use 0-10 scale. Accept "7", "7/10", "7 sur 10" as 7.
  - For satisfaction/service/pricing/product: Use 0-5 scale. Accept "4", "4/5", "4 out of 5" as 4.
  - If user gives rating on wrong scale, convert intelligently:
    * "8/10 for satisfaction" → convert to 0-5 scale: round((8/10)*5) = 4
    * "4 out of 5 for recommendation" → convert to 0-10 scale: (4/5)*10 = 8
- If the scale is unclear or non-numeric, do NOT guess a rating.
- Do NOT infer numeric ratings from adjectives alone ("good", "average", "excellent") without a number.

**GENERAL EXTRACTION RULES:**
1. Extract ONLY fields that are explicitly mentioned or clearly implied in the current response
   (taking STATIC CONTEXT and RECENT CONVERSATION into account for pronouns like "it", "the tool", "the price").
2. Capture feedback for topics even if they were not asked about yet
   (e.g., if the user spontaneously comments on price or support, fill pricing_* or service_* fields).
3. Return SPARSE JSON:
   - Do NOT include fields that are not mentioned.
   - Do NOT include null or empty values.
4. feature_requests:
   - If the user mentions specific features they want (e.g., "I wish it had X", "you should add Y"),
     put each feature as a separate string in the feature_requests array.
5. Do NOT generate questions.
6. Do NOT assess survey completion or control flow.

**OUTPUT FORMAT:**
Return ONLY a single JSON object, like:
{{
  "field_name_1": value_1,
  "field_name_2": value_2,
  ...
}}"""
        
        return prompt
    
    def _build_original_extraction_prompt(self, user_message: str, company_name: str, product_description: str, industry: str, role: str, context_snippet: str) -> str:
        """
        ORIGINAL extraction prompt (pre-Nov 2025)
        
        Kept for rollback safety. Set USE_REVISED_EXTRACTION_PROMPT=false to use this.
        """
        prompt = f"""Extract structured data from the user's response below.

**STATIC CONTEXT (for understanding only, do NOT restate):**
- Company: {company_name}
- Product/Service: {product_description}
- Industry: {industry}
- Participant Role: {role}

**RECENT CONVERSATION:**
{context_snippet}

**USER'S LATEST RESPONSE:**
{user_message}

**EXTRACTION INSTRUCTIONS:**
1. Extract ONLY fields that are explicitly mentioned or clearly implied
2. Return SPARSE JSON (do NOT include null/empty fields)
3. Use these field names if mentioned (note the different scales):
   - nps_score (0-10 integer; recommendation likelihood)
   - nps_reasoning (string)
   - satisfaction_rating (0-5 integer; overall satisfaction)
   - service_rating (0-5 integer; service/support quality)
   - pricing_rating (0-5 integer; price/value rating)
   - product_value_rating (0-5 integer; product quality)
   - support_rating (0-5 integer; support quality)
   - detailed_feedback (string)
   - pricing_satisfaction (string)
   - feature_requests (array of strings)
   
4. SCALE RULES: NPS uses 0-10, all other ratings use 0-5. Convert if needed.
5. If user provides data for topics we haven't asked about yet, capture it anyway

**OUTPUT FORMAT:**
{{
  "field_name": value
}}

Return ONLY the JSON object, no explanation."""
        
        return prompt
    
    def _build_question_prompt(
        self,
        goal: Dict,
        missing_fields: List[str],
        is_follow_up: bool
    ) -> str:
        """
        Build LLM prompt for question generation with static context.
        
        Static context provides understanding WITHOUT verbosity:
        - Company, product, industry, role
        - Recent conversation turns
        - Current topic and missing fields
        """
        topic_name = goal.get('topic', 'Unknown')
        
        # Get static context
        company_name = self.participant_data.get('company_name', 'the company')
        product_description = getattr(self.campaign, 'product_description', 'our services')
        industry = self.participant_data.get('client_industry', 'your industry')
        role = self.participant_data.get('role', 'team member')
        
        # Conversation tone
        conversation_tone = getattr(self.campaign, 'conversation_tone', None) or \
                           getattr(self.business_account, 'conversation_tone', 'professional')
        
        # Recent conversation context
        recent_history = self.conversation_history[-6:]
        context_snippet = "\n".join([
            f"{msg['sender']}: {msg['message'][:100]}" 
            for msg in recent_history
        ])
        
        # Build question prompt
        follow_up_instruction = ""
        if is_follow_up:
            follow_up_instruction = """
**THIS IS A FOLLOW-UP QUESTION** - The user's previous answer was incomplete or vague.
Ask a clarifying question to get more specific information about the missing fields."""
        
        prompt = f"""Generate a natural, conversational question for the topic: {topic_name}

**STATIC CONTEXT (for understanding only, do NOT restate):**
- Company: {company_name}
- Product/Service: {product_description}
- Industry: {industry}
- Participant Role: {role}
- Conversation Tone: {conversation_tone}

**RECENT CONVERSATION:**
{context_snippet}

**TOPIC TO ASK ABOUT:**
{topic_name}

**MISSING FIELDS:**
{', '.join(missing_fields)}

{follow_up_instruction}

**QUESTION GENERATION INSTRUCTIONS:**
1. Generate ONE clear, engaging question
2. Focus on collecting the missing fields above
3. Use conversational, natural language (match tone: {conversation_tone})
4. Keep it concise (1-2 sentences max)
5. Do NOT repeat information user already provided
6. Do NOT mention "fields" or technical terms

**OUTPUT:**
Return ONLY the question text, no JSON, no explanation."""
        
        return prompt
    
    def _should_complete_survey(self) -> bool:
        """
        Backend-controlled completion decision (NO LLM involvement).
        
        Survey completes when:
        1. All MUST-ASK topics complete (optional can be partial), OR
        2. Max questions reached (loop protection)
        
        CRITICAL FIX (Nov 23, 2025): Uses check_optional=False to allow graceful end
        with partial optional data (this is the whole point of V2!)
        
        Returns:
            True if survey should end, False to continue
        """
        # Check max questions limit (loop protection)
        if self.step_count >= self.max_questions:
            logger.warning(f"Max questions reached ({self.max_questions}) - forcing completion")
            return True
        
        # CRITICAL: Check if all MUST-ASK topics complete (backend decision)
        # check_optional=False allows survey to end even if optional topics incomplete
        # This is THE KEY DESIGN PRINCIPLE of V2 - must-ask required, optional best-effort
        all_must_ask_complete = all_goals_completed(
            goals=self.goals,
            extracted_data=self.extracted_data,
            prefilled_fields=self.prefilled_fields,
            role_excluded_topics=self.role_excluded_topics,
            check_optional=False  # CRITICAL: Only check must-ask topics (allow partial optional)
        )
        
        if all_must_ask_complete:
            logger.info("✅ All MUST-ASK topics complete - backend completing survey (optional may be partial)")
            return True
        
        return False
    
    def _finish_survey(self) -> Dict[str, Any]:
        """
        Finalize survey and return completion message.
        
        Returns:
            Completion response dict
        """
        self.is_complete = True
        
        # Generate completion message (using template service for consistency)
        completion_message = self.template_service.get_completion_message()
        
        # Add to conversation history
        self.conversation_history.append({
            'sender': 'VOÏA',
            'message': completion_message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Save final state
        save_deterministic_state(self.conversation_id, self._get_state_dict())
        
        logger.info(f"Survey completed: {len(self.extracted_data)} fields collected in {self.step_count} steps")
        
        return {
            'message': completion_message,
            'message_type': 'completion',
            'step': 'complete',
            'progress': 100,
            'is_complete': True,
            'extracted_data': self.extracted_data,
            'conversation_history': self.conversation_history,
            'step_count': self.step_count,
            'controller_version': 'v2_deterministic'
        }
    
    def _build_filtered_goals(self) -> List[Dict]:
        """
        Build goal list with role-based and industry-based filtering.
        
        CRITICAL FIX (Nov 23, 2025): Integrates with real template service configuration.
        Uses build_survey_config_json() to get campaign-configured goals with role filtering.
        
        FIX (Nov 23, 2025): Added topic normalization to handle meta-topics like "NPS Score"
        
        Returns:
            List of goal dicts with topic, fields, priority, is_required
        """
        # Build survey config from template service (uses real campaign configuration)
        survey_config = self.template_service.build_survey_config_json(self.participant_data)
        
        # Extract goals from survey config
        # Template service returns goals with topic, description, fields, priority
        template_goals = survey_config.get('goals', [])
        
        if not template_goals:
            logger.warning("No goals returned from template service - using fallback NPS goal")
            template_goals = [
                {
                    'topic': 'NPS',
                    'description': 'Net Promoter Score',
                    'fields': ['nps_score', 'nps_reasoning'],
                    'priority': 1
                }
            ]
        
        # Transform template service goals to V2 format
        # V2 FIX (Nov 23, 2025): PromptTemplateService NOW returns is_required metadata
        # Source of truth: Campaign.prioritized_topics (is_required=True) vs Campaign.optional_topics (is_required=False)
        goals = []
        for goal in template_goals:
            priority = goal.get('priority', 999)
            topic_name = goal.get('topic', 'Unknown')
            
            # FIX: Normalize meta-topics that reference survey methodology itself
            # "NPS Score" is not a valid topic (it's the survey tool), map to "NPS" (the reasoning/feedback)
            if topic_name.lower() in ['nps score', 'score nps', 'nps score reasoning']:
                logger.warning(f"Normalizing meta-topic '{topic_name}' → 'NPS' to avoid circular questions")
                topic_name = 'NPS'
            
            # Use template service's is_required metadata (authoritative source)
            # Fallback to priority-based logic only if metadata missing (backward compatibility)
            is_required = goal.get('is_required', priority <= 2)
            
            goals.append({
                'topic': topic_name,
                'fields': goal.get('fields', []),
                'priority': priority,
                'is_required': is_required,  # Now from template service, not derived!
                'description': goal.get('description', '')
            })
        
        logger.info(f"Built {len(goals)} goals from template service:")
        for g in goals:
            req_label = "MUST-ASK" if g['is_required'] else "OPTIONAL"
            logger.debug(f"  - {req_label} P{g['priority']}: {g['topic']} ({len(g['fields'])} fields)")
        
        # FIX (Nov 23, 2025): Apply role-based priority adjustments
        # Participant role now influences question order within campaign priorities
        from deterministic_helpers import apply_role_priority_adjustments
        participant_role = self.participant_data.get('role')
        goals = apply_role_priority_adjustments(goals, participant_role)
        
        return goals
    
    def _load_prefilled_fields(self) -> Set[str]:
        """
        Load prefilled fields from participant data.
        
        Returns:
            Set of field names that are pre-populated
        """
        return extract_prefilled_fields(self.participant_data)
    
    def _generate_welcome_message(self, company_name: str, respondent_name: str) -> str:
        """
        Generate welcome message (reuses V1 template service for consistency).
        
        Args:
            company_name: Company name (not used, template service has its own)
            respondent_name: Respondent name
        
        Returns:
            Welcome message string
        """
        # Use template service for consistency with V1
        # Note: company_name is handled by template service internally
        return self.template_service.generate_welcome_message(respondent_name)
    
    def _fallback_question(self, topic_name: str, is_follow_up: bool) -> str:
        """
        Fallback question when LLM generation fails.
        
        Args:
            topic_name: Topic name
            is_follow_up: Whether this is a follow-up question
        
        Returns:
            Generic question string
        """
        if is_follow_up:
            return f"Could you tell me more about {topic_name}?"
        else:
            return f"How would you rate your experience with {topic_name}?"
    
    def _calculate_progress(self) -> int:
        """
        Calculate survey progress percentage.
        
        Returns:
            Progress percentage (0-100)
        """
        if self.step_count >= self.max_questions:
            return 100
        
        # Simple linear progress based on step count
        progress = int((self.step_count / self.max_questions) * 90) + 10  # 10-100 range
        return min(progress, 95)  # Cap at 95% until completion
    
    def _get_state_dict(self) -> Dict[str, Any]:
        """
        Get current controller state as dict for persistence.
        
        V2 ENHANCEMENT (Nov 23, 2025): Now includes controller_version and is_complete
        for finalization route branching and completion state tracking.
        
        FIX (Dec 11, 2025): Added ai_prompts_log for debugging prompt effectiveness.
        
        Returns:
            State dict for session_state_utils
        """
        return {
            'conversation_id': self.conversation_id,
            'campaign_id': self.campaign_id,
            'participant_id': self.participant_data.get('id'),
            'business_account_id': self.business_account_id,
            'participant_data': self.participant_data,
            'extracted_data': self.extracted_data,
            'conversation_history': self.conversation_history,
            'step_count': self.step_count,
            'current_goal_pointer': self.current_goal_pointer,
            'topic_question_counts': self.topic_question_counts,
            'last_activity': datetime.utcnow().isoformat(),
            'resume_offered': False,
            'controller_version': 'v2_deterministic',  # V2 ENHANCEMENT: For finalization routing
            'is_complete': self.is_complete,  # V2 ENHANCEMENT: Completion state tracking
            'ai_prompts_log': self.ai_prompts_log  # FIX: Persist prompts for debugging
        }
    
    def load_conversation_state(self, conversation_id: str) -> bool:
        """
        Load persisted conversation state from database.
        
        Args:
            conversation_id: Conversation UUID
        
        Returns:
            True if state loaded successfully, False otherwise
        """
        state = load_deterministic_state(conversation_id)
        
        if not state:
            logger.warning(f"No persisted state found for conversation {conversation_id}")
            return False
        
        # Restore controller state
        self.conversation_id = state['conversation_id']
        self.extracted_data = state['extracted_data']
        self.conversation_history = state['conversation_history']
        self.step_count = state['step_count']
        self.current_goal_pointer = state['current_goal_pointer']
        self.topic_question_counts = state['topic_question_counts']
        self.ai_prompts_log = state.get('ai_prompts_log', [])  # FIX: Restore prompts log
        
        logger.info(f"Loaded V2 state: conv_id={conversation_id}, step={self.step_count}")
        
        return True


# ============================================================================
# WRAPPER FUNCTIONS FOR ROUTE INTEGRATION (V1 COMPATIBILITY)
# ============================================================================

def start_ai_conversational_survey_v2(
    company_name: str,
    respondent_name: str,
    tenure_with_fc: Optional[str] = None,
    business_account_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    participant_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    V2 wrapper for start_ai_conversational_survey() - maintains V1 interface.
    
    Args:
        company_name: Company name
        respondent_name: Respondent name
        tenure_with_fc: Tenure category (pre-populated)
        business_account_id: Business account ID
        campaign_id: Campaign ID
        participant_data: Participant metadata dict
    
    Returns:
        Response dict compatible with V1 interface
    """
    logger.info(f"Starting V2 conversational survey (deterministic flow)")
    
    # Initialize V2 controller
    controller = DeterministicSurveyController(
        business_account_id=business_account_id,
        campaign_id=campaign_id,
        participant_data=participant_data
    )
    
    # Start conversation
    response = controller.start_conversation(company_name, respondent_name)
    
    logger.info(f"V2 survey started: conv_id={response['conversation_id']}")
    
    return response


def process_ai_conversation_response_v2(
    user_input: str,
    survey_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    V2 wrapper for process_ai_conversation_response() - maintains V1 interface.
    
    Args:
        user_input: User's message text
        survey_data: Survey context dict with conversation_id, business_account_id, campaign_id
    
    Returns:
        Response dict compatible with V1 interface
    """
    conversation_id = survey_data.get('conversation_id')
    business_account_id = survey_data.get('business_account_id')
    campaign_id = survey_data.get('campaign_id')
    
    logger.debug(f"Processing V2 response: conv_id={conversation_id}")
    
    # Load existing conversation state
    controller = DeterministicSurveyController(
        business_account_id=business_account_id,
        campaign_id=campaign_id,
        conversation_id=conversation_id
    )
    
    # Try to load persisted state
    if conversation_id and not controller.load_conversation_state(conversation_id):
        logger.warning(f"No persisted state for {conversation_id} - this may be a resumed conversation")
        # State will be initialized fresh, which may cause issues
        # But we'll continue gracefully
    elif not conversation_id:
        logger.error("No conversation_id provided - cannot load state")
        # This is a critical error, but we'll continue with fresh state
    
    # Process user response
    response = controller.process_user_response(user_input, survey_data)
    
    logger.debug(f"V2 response processed: complete={response.get('is_complete')}")
    
    return response


def finalize_ai_conversational_survey_v2(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    V2-specific finalization for deterministic survey conversations.
    
    CRITICAL (Nov 23, 2025): Loads V2 deterministic state from database including:
    - controller_version='v2_deterministic' (for route branching)
    - is_complete=True (completion verification)
    - topic_question_counts (per-topic follow-up tracking)
    - extracted_data (structured survey responses)
    
    Args:
        context: Survey context with conversation_id, business_account_id, campaign_id
    
    Returns:
        Structured survey data dict for database persistence
    """
    from models import ActiveConversation
    from session_state_utils import load_deterministic_state
    import json
    
    conversation_id = context.get('conversation_id')
    
    if not conversation_id:
        logger.error("FINALIZATION ERROR: Missing conversation_id in context")
        raise ValueError("V2 finalization failed: conversation_id required")
    
    logger.info(f"✅ Finalizing V2 deterministic conversation: {conversation_id}")
    
    # FIX (Nov 23, 2025): Load ActiveConversation to get participant_data
    active_conv = ActiveConversation.query.filter_by(conversation_id=conversation_id).first()
    if not active_conv:
        logger.error(f"FINALIZATION ERROR: No ActiveConversation found for {conversation_id}")
        raise ValueError(f"V2 finalization failed: missing ActiveConversation for {conversation_id}")
    
    # Parse participant_data JSON to get required fields
    participant_data = json.loads(active_conv.participant_data) if active_conv.participant_data else {}
    
    # Load persisted V2 state from database
    # FIX (Nov 23, 2025): Use correct function name from session_state_utils
    persisted_state = load_deterministic_state(conversation_id)
    
    if not persisted_state:
        logger.error(f"FINALIZATION ERROR: No persisted state for V2 conversation {conversation_id}")
        raise ValueError(f"V2 finalization failed: missing state for conversation {conversation_id}")
    
    # Verify this is a V2 conversation
    controller_version = persisted_state.get('controller_version', 'unknown')
    if controller_version != 'v2_deterministic':
        logger.error(f"FINALIZATION ERROR: Wrong controller version (expected v2_deterministic, got {controller_version})")
        raise ValueError(f"V2 finalization failed: controller_version mismatch ({controller_version})")
    
    # Extract V2-specific state
    extracted_data = persisted_state.get('extracted_data', {})
    conversation_history = persisted_state.get('conversation_history', [])
    step_count = persisted_state.get('step_count', 0)
    topic_question_counts = persisted_state.get('topic_question_counts', {})
    is_complete = persisted_state.get('is_complete', False)
    ai_prompts_log = persisted_state.get('ai_prompts_log', [])  # FIX (Dec 11, 2025): Extract prompts log
    
    logger.info(f"V2 State loaded: {len(extracted_data)} fields, {step_count} steps, complete={is_complete}, prompts={len(ai_prompts_log)}")
    logger.debug(f"Topic question counts: {topic_question_counts}")
    
    # FIX (Nov 23, 2025): Map participant_data keys to database field names
    # ActiveConversation uses: participant_name, participant_company
    # Database expects: respondent_name, company_name
    company_name = (
        participant_data.get('participant_company') or  # Correct key from token schema
        participant_data.get('company_name') or          # Legacy fallback
        extracted_data.get('company_name') or
        context.get('company_name')
    )
    respondent_name = (
        participant_data.get('participant_name') or      # Correct key from token schema
        participant_data.get('respondent_name') or       # Legacy fallback
        extracted_data.get('respondent_name') or
        context.get('respondent_name')
    )
    
    # Defensive logging if fields still missing
    if not company_name or not respondent_name:
        logger.warning(
            f"⚠️ Missing required fields after all lookups: "
            f"company_name={company_name}, respondent_name={respondent_name}, "
            f"participant_data keys={list(participant_data.keys())}"
        )
    
    # Return structured data for database persistence
    # Format matches V1 for database compatibility
    structured_data = {
        'extracted_data': extracted_data,
        'conversation_history': conversation_history,
        'step_count': step_count,
        'topic_question_counts': topic_question_counts,
        'is_complete': is_complete,
        'controller_version': 'v2_deterministic',
        'ai_prompts_log': json.dumps(ai_prompts_log) if ai_prompts_log else None,  # FIX (Dec 11, 2025): JSON serialize prompts for DB
        
        # FIX (Nov 23, 2025): Add required NOT NULL fields for database
        'company_name': company_name,
        'respondent_name': respondent_name,
        
        # Map extracted data to database fields (V1 compatibility)
        # Note: As of Nov 2025, extracted_data already contains DB column names
        # (mapped by _map_extracted_fields_to_db during extraction)
        'nps_score': extracted_data.get('nps_score'),
        'recommendation_reason': extracted_data.get('recommendation_reason'),  # Already mapped from nps_reasoning
        'satisfaction_rating': extracted_data.get('satisfaction_rating'),  # Already mapped from overall_satisfaction_rating
        'service_rating': extracted_data.get('service_rating'),
        'product_value_rating': extracted_data.get('product_value_rating'),  # Already mapped from product_appreciation_rating
        'pricing_rating': extracted_data.get('pricing_rating'),  # Already mapped from pricing_value_rating
        'support_rating': extracted_data.get('support_rating'),
        'improvement_feedback': extracted_data.get('improvement_feedback'),  # Already mapped from pricing_satisfaction
        'general_feedback': extracted_data.get('general_feedback'),  # Already mapped from detailed_feedback
        'additional_comments': extracted_data.get('additional_comments'),
        'feature_requests': extracted_data.get('feature_requests'),  # Already JSON-serialized if array
        'tenure_with_fc': extracted_data.get('tenure_with_fc')
    }
    
    logger.info(f"✅ V2 finalization complete: {len(structured_data)} total fields, company={company_name}, respondent={respondent_name}")
    
    return structured_data
