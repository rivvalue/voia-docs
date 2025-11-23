# Design Document: Deterministic Conversational Survey Controller (V2)

**Version:** 1.0  
**Date:** November 22, 2025  
**Status:** Design Phase  
**Feature Flag:** `DETERMINISTIC_SURVEY_FLOW`

---

## 1. Executive Summary

### Problem Statement
Current conversational survey system (`ai_conversational_survey.py`) has "early-stop bugs" where the LLM prematurely marks surveys complete, causing data loss. The LLM controls both question generation AND flow logic, creating unpredictable behavior.

### Solution
Reverse the paradigm: **VOÏA backend controls flow deterministically**, LLM performs only two narrow tasks:
1. **Extract structured data** from user responses
2. **Generate natural language question** for a given topic (no flow decisions)

### Implementation Strategy
- **Parallel implementation** (new code, zero refactoring of existing system)
- **Feature flag toggle** (`DETERMINISTIC_SURVEY_FLOW`) for safe rollout
- **Gradual migration** with rollback capability

---

## 2. User Requirements (Confirmed Decisions)

| Scenario | Behavior |
|----------|----------|
| **Off-topic responses** | Extract any useful data, then re-ask current question |
| **Early data delivery** | Capture data but still ask question later for confirmation (don't auto-skip) |
| **Incomplete answers** | Stay on same topic, ask clarifying follow-up question (multi-turn same goal) |
| **Session abandonment** | Ask user if they want to resume or restart |

---

## 3. Architecture Overview

### 3.1 Current System (Legacy)
```
User → routes.py → AIConversationalSurvey._process_with_ai_combined()
                    ↓
              Single LLM call returns:
              - extracted_data
              - next_question
              - is_complete (LLM DECIDES!)
                    ↓
              Response to user
```

### 3.2 New System (Deterministic V2)
```
User → routes.py → DeterministicSurveyController.handle_user_message()
                    ↓
              1. Extract data (LLM stub)
              2. Check completion (Helper 1 - BACKEND DECIDES)
              3. Get next goal (Helper 2 - BACKEND DECIDES)
              4. Generate question (LLM stub for specific topic)
                    ↓
              Response to user
```

### 3.3 Key Differences

| Aspect | Legacy (V1) | Deterministic (V2) |
|--------|-------------|-------------------|
| **Flow Control** | LLM decides | Backend decides |
| **Completion Logic** | AI-driven | all_goals_completed() |
| **Question Selection** | AI self-directed | get_next_goal() |
| **LLM Calls per Turn** | 1 combined call | 2 separate calls (extract + question) |
| **Early Stop Risk** | High | Eliminated |
| **Predictability** | Low | High |

---

## 4. Core Components

### 4.1 Helper 1: `all_goals_completed()`

**Purpose:** Deterministic check if survey should end

**CRITICAL CHANGE (Nov 22, 2025):** Now distinguishes between **must-ask** and **optional** topics.

**Signature:**
```python
def all_goals_completed(
    goals: List[Dict],
    extracted_data: Dict,
    prefilled_fields: Set[str],
    role_excluded_topics: Set[str],
    check_optional: bool = False  # NEW: Controls must-ask vs optional checking
) -> bool
```

**Two-Tier Completion Logic:**
1. Filter goals by role (exclude topics not relevant to participant role)
2. Filter by `is_required` flag:
   - If `check_optional=False` (default): Only check **must-ask** topics
   - If `check_optional=True`: Check **all** topics (must-ask + optional)
3. For each remaining goal:
   - Check if ALL fields are filled in `extracted_data` OR `prefilled_fields`
   - Return `False` if any field missing
4. Return `True` only if all checked goals complete

**Key Behavior:**
- Survey can end when ALL **must-ask** topics are complete (optional can remain incomplete)
- This prevents early-stop bugs on required data while allowing graceful end with partial optional data

**Integration Points:**
- `filter_goals_by_role()` from `prompt_template_service.py`
- `TOPIC_FIELD_MAP` for field definitions
- Prefilled fields from participant data (tenure, company name, etc.)
- Campaign `survey_config.must_ask_topics` and `optional_topics` lists

---

### 4.2 Helper 2: `get_next_goal()`

**Purpose:** Select next topic and identify missing fields with **TWO-TIER PRIORITY** and **PER-TOPIC FOLLOW-UP LIMITS**

**CRITICAL CHANGES:**
- Nov 22, 2025: Must-ask topics ALWAYS come before optional topics
- Nov 23, 2025: Added per-topic follow-up counter enforcement (backend-controlled)

**Signature:**
```python
def get_next_goal(
    goals: List[Dict],
    extracted_data: Dict,
    prefilled_fields: Set[str],
    current_goal_pointer: Optional[str],
    topic_question_counts: Dict[str, int],  # NEW: Per-topic question counter
    max_follow_up_per_topic: int = 2,       # NEW: Campaign-configured limit
    allow_multi_turn: bool = True,
    limit_optional_follow_ups: bool = True  # Conserve questions on optional topics
) -> Tuple[Optional[Dict], List[str], bool]
```

**Returns:** `(next_goal, missing_fields, is_follow_up)`

**Two-Tier Priority Logic with Follow-Up Enforcement:**

1. **Multi-turn logic** (if `current_goal_pointer` set AND `allow_multi_turn=True`):
   - Check if current goal still has missing fields
   - **NEW: Check per-topic follow-up limit**
     - Calculate: `follow_ups_used = topic_question_counts.get(topic, 1) - 1`
     - If `is_required=True` (must-ask): **Bypass limit** (unlimited follow-ups for completion)
     - If `is_required=False` (optional) AND `follow_ups_used >= max_follow_up_per_topic`:
       - Log: "Follow-up limit reached for optional topic"
       - Move to next topic (accept partial data)
     - Otherwise: Return (current_goal, missing_fields, is_follow_up=True)

2. **TIER 1 - Must-Ask Topics** (is_required=True):
   - Iterate all must-ask topics by priority
   - Find first goal with missing fields
   - Return (goal, missing_fields, is_follow_up=False)

3. **TIER 2 - Optional Topics** (is_required=False):
   - **Only executed if ALL must-ask topics complete**
   - Iterate all optional topics by priority
   - Find first goal with missing fields
   - Return (goal, missing_fields, is_follow_up=False)

4. If no missing fields anywhere, return (None, [], False)

**State Management:**
- `current_goal_pointer`: Stored in session for multi-turn tracking
- `topic_question_counts`: Dict tracking questions asked per topic (e.g., `{"Product Quality": 2}`)
- Cleared when moving to next goal
- Persisted across page refreshes (session-based)

**Per-Topic Follow-Up Limit Rules:**
- **Must-ask topics**: Unlimited follow-ups (bypass `max_follow_up_per_topic` limit)
- **Optional topics**: Strictly enforce `max_follow_up_per_topic` limit
- **Rationale**: Survey integrity requires must-ask completion; optional topics are best-effort
- **Campaign setting**: `max_follow_up_per_topic` configured per campaign (default: 2)

**Edge Case Handling:**
- Optional topic hits limit with missing fields → Accept partial data, move on
- Must-ask topic with many vague answers → Continue asking until complete (no limit)
- All topics hit follow-up limits → Survey ends gracefully

---

### 4.3 Main Controller: `DeterministicSurveyController`

**File:** `ai_conversational_survey_v2.py` (NEW FILE)

**Class Structure:**
```python
class DeterministicSurveyController:
    def __init__(self, campaign_id, participant_id, business_account_id):
        self.campaign = get_campaign(campaign_id)
        self.participant = get_participant(participant_id)
        self.business_account = get_business_account(business_account_id)
        
        # Build goals with role/industry filtering
        self.goals = self._build_filtered_goals()
        self.prefilled_fields = self._load_prefilled_fields()
        
        # Session state
        self.extracted_data = {}
        self.conversation_history = []
        self.current_goal_pointer = None
        self.step_count = 0
        
    def handle_user_message(self, user_message: str) -> Dict:
        """Main orchestration method with per-topic follow-up enforcement"""
        # 1) Extract data (NO needs_followup flag - backend decides flow)
        new_fields = self._extract_with_ai(user_message)
        self.extracted_data.update(new_fields)
        self.step_count += 1
        
        # 2) Check global completion
        if self._check_completion_or_continue():
            return self._finish_survey()
        
        # 3) Get next goal (backend decides follow-up using counters)
        next_goal, missing_fields, is_follow_up = get_next_goal(
            goals=self.goals,
            extracted_data=self.extracted_data,
            prefilled_fields=self.prefilled_fields,
            current_goal_pointer=self.current_goal_pointer,
            topic_question_counts=self.topic_question_counts,  # NEW: Counter dict
            max_follow_up_per_topic=self.campaign.max_follow_up_per_topic,  # NEW: Limit
            allow_multi_turn=True
        )
        
        if not next_goal:
            return self._finish_survey()
        
        topic_name = next_goal["topic"]
        
        # 4) Generate question for chosen topic
        question = self._generate_question_with_ai(next_goal, missing_fields, is_follow_up)
        
        # 5) Update state (increment counter, set pointer)
        self.topic_question_counts[topic_name] = self.topic_question_counts.get(topic_name, 0) + 1
        self.current_goal_pointer = topic_name
        
        return {"message": question, "is_complete": False, "topic": topic_name}
        
    def _extract_with_ai(self, user_message: str) -> Dict:
        """Stub: Call LLM for pure extraction (NO flow decisions)"""
        
    def _generate_question_with_ai(self, goal: Dict, missing_fields: List[str], is_follow_up: bool) -> str:
        """Stub: Call LLM to generate question for specific topic"""
        
    def _build_filtered_goals(self) -> List[Dict]:
        """Apply role-based filtering and industry verticalization"""
        
    def _load_prefilled_fields(self) -> Set[str]:
        """Load tenure, company name, etc. from participant data"""
```

---

## 5. Flow Diagrams

### 5.1 Main Orchestration Flow

```
User sends message
    ↓
Add to conversation_history
    ↓
Call _extract_with_ai(user_message)
    ↓
Update extracted_data with new fields
    ↓
Increment step_count
    ↓
Check: all_goals_completed() OR step_count >= max_questions?
    ├─ YES → Return completion message (is_complete=True)
    └─ NO  → Continue
         ↓
    Call get_next_goal(current_goal_pointer)
         ↓
    Returns: (goal, missing_fields, is_follow_up)
         ↓
    Call _generate_question_with_ai(goal, missing_fields, is_follow_up)
         ↓
    Update current_goal_pointer
         ↓
    Return question to user (is_complete=False)
```

### 5.2 Multi-Turn Same Topic Flow (with Per-Topic Follow-Up Limits)

**Scenario: Optional topic with max_follow_up_per_topic=2**

```
User gives vague answer on "Product Quality" (optional topic)
    ↓
Extract returns: {"satisfaction_rating": 7} (missing elaboration)
topic_question_counts = {"Product Quality": 1}  # First question
    ↓
get_next_goal(current_goal_pointer="Product Quality", topic_question_counts)
    ↓
Backend checks:
  - Still missing fields: ["detailed_feedback"]
  - Follow-ups used: 1 - 1 = 0 (under limit of 2)
  - is_required=False (optional)
    ↓
Returns: (same_goal, ["detailed_feedback"], is_follow_up=True)
    ↓
Generate follow-up question: "Could you elaborate on why you gave 7/10?"
Increment counter: topic_question_counts["Product Quality"] = 2
    ↓
User gives partial answer: "It's okay"
Extract returns: {} (still missing elaboration)
topic_question_counts = {"Product Quality": 2}
    ↓
get_next_goal(current_goal_pointer="Product Quality", topic_question_counts)
    ↓
Backend checks:
  - Still missing fields: ["detailed_feedback"]
  - Follow-ups used: 2 - 1 = 1 (under limit of 2)
  - is_required=False (optional)
    ↓
Returns: (same_goal, ["detailed_feedback"], is_follow_up=True)
    ↓
Generate second follow-up: "Could you tell me more about what makes it 'okay'?"
Increment counter: topic_question_counts["Product Quality"] = 3
    ↓
User says: "Not sure"
Extract returns: {} (still missing)
topic_question_counts = {"Product Quality": 3}
    ↓
get_next_goal(current_goal_pointer="Product Quality", topic_question_counts)
    ↓
Backend checks:
  - Still missing fields: ["detailed_feedback"]
  - Follow-ups used: 3 - 1 = 2 (REACHED LIMIT)
  - is_required=False (optional)
    ↓
LIMIT EXCEEDED: Accept partial data, force move to next topic
Returns: (next_topic_goal, missing_fields, is_follow_up=False)
```

**Must-Ask Topic Exception:**
```
Topic: "NPS Score" (must-ask, max_follow_up_per_topic=2)
User gives vague answers 5 times → Backend continues asking
Follow-up limit BYPASSED because is_required=True
Survey cannot complete until must-ask fields collected
```

### 5.3 Early Data Capture Flow

```
User says: "Pricing is great! Response time is slow though"
(We're currently asking about Product Quality)
    ↓
Extract returns: {
    "pricing_satisfaction": "positive",
    "support_response_time": "slow"
}
    ↓
Update extracted_data (store for future use)
    ↓
get_next_goal() → Still returns "Product Quality" goal
    ↓
Re-ask Product Quality question (ignore early data for now)
    ↓
Later, when we reach "Pricing" topic:
    - Check extracted_data: already has pricing_satisfaction
    - Still ask confirmation: "Earlier you mentioned pricing was great. On a scale 1-10, how would you rate it?"
```

---

## 6. LLM Integration (Stubs)

### 6.1 Extraction Stub

**Prompt Template:**
```python
def _extract_with_ai(self, user_message: str) -> Dict:
    """
    Call LLM to extract structured fields from user response.
    NO flow control, NO question generation.
    
    IMPORTANT: Includes conversation context for multi-turn comprehension
    (e.g., pronouns, references to previous topics).
    """
    
    language = self.campaign.language  # "fr", "en", "es"
    all_fields = self._list_all_fields()  # From TOPIC_FIELD_MAP
    
    # Include last 5-6 message exchanges for context
    # Critical for understanding pronouns ("it", "they") and multi-turn clarifications
    conversation_context = self._format_conversation_history(last_n=6)
    
    # Build static context block for semantic understanding
    company_name = self.business_account.name
    product_desc = self.campaign.product_description or self.business_account.product_description
    industry = self.get_effective_industry()
    participant_role = self.participant.role
    campaign_goal = self.campaign.description or self.business_account.company_description
    
    prompt = f"""You are a data extraction assistant for the VOÏA survey platform.

STATIC CONTEXT (for understanding only, do NOT restate it):
- Company: {company_name}
- Product: {product_desc}
- Industry: {industry}
- Participant role: {participant_role}
- Campaign goal: {campaign_goal}

Your task:
- Read the user's latest response.
- Extract all clearly provided information relevant to the fields below.
- Use the previous conversation context ONLY to interpret pronouns or references.
- Use the static context ONLY to understand domain terminology and resolve ambiguity.
- Return ONLY the fields that appear in the current user response (directly or through context).
- Do NOT speculate or infer information not clearly stated.

ALL_POSSIBLE_FIELDS = {all_fields}

Previous conversation context (summary):
\"\"\"{conversation_context}\"\"\"

Current user response:
\"\"\"{user_message}\"\"\"

RULES:
- Only output fields for which the user clearly provided information.
- If a field is not mentioned, DO NOT include it in the JSON output at all.
- Do NOT output null values.
- Do NOT restate the static context in your extractions.
- Do NOT generate questions.
- Do NOT perform survey flow logic.
- Values must be short, semantic summaries (not long paragraphs).
- Respond with VALID JSON ONLY.

Examples:

1. Off-topic extraction with context:
   User says: "It's still unstable and support never replies."
   Output: {{"product_quality_feedback": "unstable", "support_experience_feedback": "support slow to reply"}}

2. Nothing to extract:
   User says: "I'm not sure yet."
   Output: {{}}

3. Pronoun resolution using static + conversation context:
   Static context: Product = "Saaspasse (SaaS for internal podcasts)"
   Conversation context: Previous discussion about recording features
   User says: "It crashes frequently"
   Output: {{"product_quality_feedback": "crashes frequently during recording"}}

4. Industry-specific terminology preservation:
   Static context: Industry = "Software", Product = "podcast production SaaS"
   User says: "The encoding quality is poor"
   Output: {{"product_quality_feedback": "poor audio encoding quality"}}
"""
    
    # Use configured model (from environment/business settings, NOT hardcoded)
    # Leverages VOÏA's tiered model routing strategy
    response = self._call_openai(prompt, model=self.extraction_model)
    return json.loads(response)
```

**Static Context Benefits:**
- **Pronoun resolution**: "It crashes" → LLM knows "it" = actual product name from context
- **Industry terminology**: LLM uses domain-specific terms (e.g., "throughput" for manufacturing)
- **Role-appropriate extraction**: End users focus on UX, executives focus on ROI
- **Off-topic smart capture**: User mentions pricing while discussing product → LLM captures both with proper context
- **Sparse output**: "do NOT restate" instruction prevents LLM from echoing context back

**Configuration Integration:**
- `self.extraction_model` sourced from business account or environment config
- Supports VOÏA's AI cost optimization strategy (tiered routing: gpt-4o-mini vs gpt-4o)
- Never hardcode model names - allows per-tenant overrides

**Data Merge Strategy:**
```python
# Controller safely merges sparse payloads (only non-null fields returned)
extracted_data.update(new_fields)  # Latest non-empty value wins

# Handles user reversals automatically:
# Turn 1: User says "I rate it 8"  → {"nps_score": 8}
# Turn 3: User says "Actually, 7" → {"nps_score": 7}  # Overwrites with latest
```

**Token Efficiency:**
- Sends ALL possible fields every turn (~20-30 fields, ~400 tokens)
- Rationale: Enables off-topic capture (user mentions pricing while discussing product)
- Tradeoff accepted: Slightly higher token cost for comprehensive data capture

**Error Handling:**
- Invalid JSON → Log error, return empty dict, continue
- API failure → Retry with exponential backoff (3 attempts)
- Timeout → Return empty dict, log warning

---

### 6.2 Question Generation Stub

**Prompt Template:**
```python
def _generate_question_with_ai(
    self, 
    goal: Dict, 
    missing_fields: List[str],
    is_follow_up: bool
) -> str:
    """
    Call LLM to generate a natural question for a specific topic.
    NO flow control, NO extraction, NO completion.
    """
    
    language = self.campaign.language
    industry_hints = self._get_industry_hints(goal['topic'])
    
    # Include conversation context (last 6 messages)
    # Needed to avoid repeating questions and maintain natural flow
    conversation_context = self._format_conversation_history(last_n=6)
    
    # Build static context block for personalized question generation
    company_name = self.business_account.name
    product_desc = self.campaign.product_description or self.business_account.product_description
    industry = self.get_effective_industry()
    participant_role = self.participant.role
    role_label = self._select_persona_template(self.participant)  # "Manager", "C-level executive", etc.
    conversation_tone = self.campaign.conversation_tone or self.business_account.conversation_tone or "professional"
    target_clients = self.campaign.target_clients_description or self.business_account.target_clients_description
    
    follow_up_instruction = ""
    if is_follow_up:
        follow_up_instruction = """
IMPORTANT: This is a FOLLOW-UP question on the same topic.
The user's previous answer was incomplete or vague.
Ask a clarifying question to get more details.
"""
    
    prompt = f"""You are VOÏA, an AI-powered customer feedback specialist conducting a survey for {company_name}.

STATIC CONTEXT (use to personalize questions):
- Company: {company_name}
- Product: {product_desc}
- Industry: {industry}
- Target clients: {target_clients}
- Participant role: {role_label}
- Conversation tone: {conversation_tone}

CURRENT TOPIC: {goal['topic']}
Industry-specific hints for this topic: {industry_hints}
Fields to collect: {missing_fields}
Language: {language}

{follow_up_instruction}

Your task:
- Generate a natural, conversational question about {goal['topic']}
- Use the static context to make the question specific and relevant (e.g., mention actual product name, not "the product")
- Tailor the question to the participant's role ({role_label})
- Use industry-appropriate terminology from the hints
- Maintain {conversation_tone} tone

Strict rules:
- Ask EXACTLY ONE question in {language}
- Focus ONLY on the current topic: {goal['topic']}
- Do NOT ask about other topics
- Do NOT conclude the survey
- Do NOT thank or say goodbye
- The platform controls completion, not you

Recent conversation context:
{conversation_context}

Generate the next question:"""
    
    # Use configured model (from environment/business settings, NOT hardcoded)
    # Allows per-campaign or per-tenant quality/cost tradeoffs
    response = self._call_openai(prompt, model=self.question_model)
    return response.strip()
```

**Static Context Benefits:**
- **Personalized questions**: "How satisfied are you with Saaspasse's podcast recording quality?" (not generic "the product")
- **Role-appropriate depth**: C-level gets strategic questions, end users get UX questions
- **Industry terminology**: Manufacturing gets "throughput" questions, healthcare gets "compliance" questions
- **Tone consistency**: Professional vs casual based on business account settings
- **Natural conversation**: Refers to actual product/company names for authenticity

**Configuration Integration:**
- `self.question_model` sourced from business account or environment config
- Typically uses premium model (gpt-4o) for question quality
- Never hardcode model names - supports A/B testing and cost optimization

**Error Handling:**
- Empty response → Return generic question for topic
- API failure → Retry with exponential backoff (3 attempts)
- Timeout → Fallback to template-based question

---

### 6.2.1 Conversation Context Helper

**Required Helper Function:**
```python
def _format_conversation_history(self, last_n: int = 6) -> str:
    """
    Format last N message exchanges for LLM context.
    
    Includes both participant and assistant messages to provide
    full conversational context for pronoun resolution and flow.
    
    Args:
        last_n: Number of recent messages to include (default 6)
    
    Returns:
        Formatted string of conversation history
    
    Example output:
        Assistant: How satisfied are you with our product quality?
        Participant: It's pretty good overall
        Assistant: Could you elaborate on what makes it good?
        Participant: It's reliable and easy to use
    """
    if not self.conversation_history:
        return "No previous conversation"
    
    # Get last N messages (both directions)
    recent = self.conversation_history[-last_n:]
    
    formatted = []
    for msg in recent:
        sender = msg.get('sender', 'Unknown')
        text = msg.get('message', '')
        formatted.append(f"{sender}: {text}")
    
    return "\n".join(formatted)
```

**Why Context Matters:**
- **Pronoun resolution:** "It's still slow" → needs context to know what "it" refers to
- **Multi-turn coherence:** Follow-up questions need to reference previous answers
- **Avoiding repetition:** Don't re-ask questions already answered
- **Natural flow:** Conversation feels cohesive, not robotic

**Token Cost Tradeoff:**
- 6 messages ≈ 100-200 tokens per LLM call
- Cost: Minimal (~$0.001 per extraction with gpt-4o-mini)
- Benefit: Massive extraction quality improvement (30-50% better pronoun handling)

---

### 6.3 Edge Case: Max Questions with Must-Ask Incomplete

**CRITICAL EDGE CASE (Nov 22, 2025):** What happens if question limit is hit before must-ask complete?

**Scenario:** Campaign has `max_questions=5`, but must-ask topics need 7 questions.

**Two-Tier Question Management:**

**Must-Ask Topics:**
- **Cannot finalize if incomplete** - Survey has integrity requirements
- **Recommended Solution:** Extend quota past `max_questions` for must-ask completion
- **Alternative:** Return hard error and require admin intervention

**Optional Topics:**
- If limit hit during optional topic: **Gracefully end survey**
- Save any partial optional data collected
- Log: "Survey ended at question limit with optional topics incomplete"

**Implementation (Recommended - Extend Quota):**
```python
def _check_completion_or_continue(self):
    """Check if survey should end, respecting must-ask priority."""
    
    must_ask_complete = all_goals_completed(
        self.goals,
        self.extracted_data,
        self.prefilled_fields,
        check_optional=False  # Only check must-ask
    )
    
    if self.step_count >= self.max_questions:
        if not must_ask_complete:
            # OVERRIDE: Must-ask incomplete - extend quota
            logger.warning(
                f"Extending quota past {self.max_questions} questions "
                f"(must-ask topics incomplete)"
            )
            # Continue survey despite limit
            return False  # Not complete, continue
        else:
            # Must-ask done, gracefully end
            logger.info(f"Survey ended at question limit (must-ask complete)")
            return True  # Complete
    
    # Standard check: all goals done (including optional if within limit)
    return all_goals_completed(
        self.goals,
        self.extracted_data,
        self.prefilled_fields,
        check_optional=True  # Check all topics if within limit
    )
```

**Key Principle:** Must-ask topics are non-negotiable. Optional topics are best-effort.

---

## 7. Session State Management

### 7.1 Required Session Fields

```python
session['deterministic_survey_state'] = {
    'extracted_data': {},              # Dict of collected fields
    'conversation_history': [],        # List of {sender, message, timestamp}
    'current_goal_pointer': None,      # Current topic for multi-turn
    'step_count': 0,                   # Number of questions asked
    'topic_question_counts': {},       # NEW: Per-topic question counter (e.g., {"Product Quality": 2})
    'prefilled_fields': {},            # From participant data
    'last_activity': timestamp,        # For abandonment detection (inactivity only)
    'resume_offered': False            # Track if resume question shown
}
```

**Per-Topic Question Counter (`topic_question_counts`):**
- **Purpose**: Track how many questions asked per topic to enforce `max_follow_up_per_topic` limit
- **Format**: `{"Product Quality": 3, "Support Quality": 1, "Pricing": 2}`
- **Incremented**: Every time a question is asked about a topic (initial + follow-ups)
- **Used by**: `get_next_goal()` to determine if follow-up limit reached
- **Must-ask exception**: Counter tracked but limit ignored for `is_required=True` topics
- **Reset**: Never reset mid-survey (persists until survey completion or abandonment)

### 7.2 Abandonment Handling and Termination Controls

**IMPORTANT: Conversation Duration Setting REMOVED in V2**

The legacy `max_conversation_duration` setting (total time limit for survey) is **NOT implemented in V2**.

**V2 Termination Controls (Only Two):**

1. **Question Count Limit** (`max_questions`):
   - Hard cap on total questions asked
   - Exception: Must-ask topics can extend past limit to ensure completion
   - Configured per campaign

2. **Inactivity Timeout** (Session abandonment):
   - User returns after >30 minutes of inactivity
   - Triggers resume-or-restart prompt
   - Based on `last_activity` timestamp

**Why Duration Removed:**
- **Simpler**: Question count is more predictable and controllable
- **Better UX**: User can take breaks without losing progress
- **No added value**: Inactivity timeout already handles abandonment
- **Less confusion**: One clear limit (questions) vs multiple overlapping limits

**Abandonment Detection:**
- User returns after >30 minutes of inactivity (NOT total duration)
- `last_activity` timestamp check

**Abandonment Behavior:**
```python
if session_exists and not session['resume_offered']:
    # Ask user: Resume or Restart?
    return {
        'message': "Welcome back! Would you like to continue where you left off?",
        'options': ['Resume', 'Start Fresh'],
        'requires_choice': True
    }
```

**User chooses "Start Fresh":**
- Clear all session state
- Call `start_conversation()` to begin new survey

**User chooses "Resume":**
- Load existing state
- Call `get_next_goal(current_goal_pointer, topic_question_counts)` to continue
- Counters and state preserved across resume

---

## 8. Feature Flag Integration

### 8.1 Flag Configuration

**File:** `feature_flags.py`

```python
DETERMINISTIC_SURVEY_FLOW = os.environ.get('DETERMINISTIC_SURVEY_FLOW', 'false').lower() == 'true'
```

### 8.2 Route Switching Logic

**File:** `routes.py`

```python
from feature_flags import DETERMINISTIC_SURVEY_FLOW
from ai_conversational_survey import AIConversationalSurvey  # Legacy
from ai_conversational_survey_v2 import DeterministicSurveyController  # New

@app.route('/api/conversation_response', methods=['POST'])
def conversation_response():
    # ... existing auth/validation ...
    
    if DETERMINISTIC_SURVEY_FLOW:
        # Use new deterministic controller
        controller = DeterministicSurveyController(
            campaign_id=campaign_id,
            participant_id=participant_id,
            business_account_id=business_account_id
        )
        result = controller.handle_user_message(user_message)
    else:
        # Use legacy AI-driven flow
        survey = AIConversationalSurvey(...)
        result = survey.process_user_response(user_message)
    
    return jsonify(result)
```

---

## 9. Migration Strategy

### 9.1 Rollout Phases

| Phase | Flag Value | Users | Duration | Goal |
|-------|-----------|-------|----------|------|
| 1. Development | `false` | Dev only | 2 weeks | Build & test |
| 2. Canary | `true` | 5% (demo accounts) | 1 week | Validate stability |
| 3. Gradual Rollout | `true` | 25% → 50% → 100% | 3 weeks | Monitor metrics |
| 4. Legacy Sunset | N/A | Remove old code | 1 week | Cleanup |

### 9.2 Rollback Plan

**If deterministic flow has critical bugs:**
1. Set `DETERMINISTIC_SURVEY_FLOW=false` (instant rollback)
2. Restart Gunicorn workers
3. Users automatically revert to legacy flow
4. No data loss (session state compatible)

### 9.3 Data Compatibility

**Both systems use same session schema:**
- `extracted_data` format identical
- `conversation_history` format identical
- Users can switch between flows mid-survey (graceful degradation)

---

## 10. Testing Strategy

### 10.1 Unit Tests

**Helper 1 Tests:**
- All goals complete → returns True
- Missing one field → returns False
- Prefilled fields count as complete
- Role-excluded topics ignored

**Helper 2 Tests:**
- Returns next incomplete goal
- Respects priority ordering
- Handles multi-turn (same goal twice)
- Returns None when complete

**Controller Tests:**
- Off-topic extraction still re-asks
- Early data captured but topic not skipped
- Multi-turn follow-ups work
- Max questions limit enforced

### 10.2 Integration Tests

**Flow Tests:**
- Complete survey end-to-end
- Abandonment and resume
- Language switching (FR/EN/ES)
- Industry hints applied
- Role filtering works

### 10.3 A/B Testing Metrics

| Metric | Legacy (V1) | Deterministic (V2) | Target |
|--------|-------------|-------------------|--------|
| Early stops | Baseline | < 50% of baseline | Reduce significantly |
| Completion rate | Baseline | > baseline | Improve |
| Avg questions asked | Baseline | ~same | Maintain efficiency |
| User satisfaction | Baseline | >= baseline | No regression |
| Data completeness | Baseline | > baseline | Improve |

---

## 11. Open Questions / Future Enhancements

### 11.1 Resolved (Answered by User)
- ✅ Off-topic handling: Extract + re-ask
- ✅ Early data: Capture but confirm later
- ✅ Incomplete answers: Multi-turn same topic
- ✅ Abandonment: Ask to resume or restart

### 11.2 Pending Discussion
- **Validation logic**: Should we validate extracted data quality (e.g., NPS 0-10 range)?
- **Industry hints injection**: Where exactly in question prompt?
- **Error budget**: How many extraction failures before fallback to legacy?
- **Audit logging**: Format for new dual-call LLM logs?

---

## 12. Success Criteria

### 12.1 Functional Requirements
- ✅ Zero early stops due to LLM decision errors
- ✅ All goals completed before survey ends
- ✅ Multi-turn clarifications work
- ✅ Early data captured and confirmed
- ✅ Resume/restart functionality

### 12.2 Non-Functional Requirements
- ✅ Feature flag rollback <5 minutes
- ✅ Session state compatible with legacy
- ✅ No performance regression (2 LLM calls vs 1 acceptable)
- ✅ Multilingual support (FR/EN/ES)
- ✅ Industry verticalization preserved

---

## 13. Implementation Timeline

| Week | Tasks |
|------|-------|
| **Week 1** | Design doc, prototype helpers, add feature flag |
| **Week 2** | Build DeterministicSurveyController, LLM stubs, unit tests |
| **Week 3** | Integration tests, route switching, session management |
| **Week 4** | Canary rollout, monitoring, bug fixes |
| **Week 5** | Gradual rollout to 100%, metrics analysis |
| **Week 6** | Legacy code removal, final cleanup |

---

## 14. File Inventory

### New Files (V2)
- `ai_conversational_survey_v2.py` - Main controller class
- `deterministic_helpers.py` - Helper 1 & 2 functions
- `DESIGN_DETERMINISTIC_SURVEY_V2.md` - This document

### Modified Files
- `routes.py` - Add feature flag switching logic
- `feature_flags.py` - Add DETERMINISTIC_SURVEY_FLOW flag
- `prompt_template_service.py` - Expose industry hints method

### Unchanged (Legacy)
- `ai_conversational_survey.py` - Keep as-is for rollback
- `conversational_survey.py` - Keep as-is

---

## 15. Appendix: Comparison with OpenAI Suggestion

### What We Adopted
- ✅ `all_goals_completed()` concept
- ✅ `get_next_goal()` concept
- ✅ Split extraction/question generation
- ✅ Main orchestration flow

### What We Enhanced
- ➕ Role-based filtering integration
- ➕ Industry verticalization support
- ➕ Prefilled fields handling
- ➕ Multi-language support (FR/EN/ES)
- ➕ Multi-turn same topic logic
- ➕ Early data capture with confirmation
- ➕ Session persistence and resume
- ➕ Feature flag architecture
- ➕ Error handling and retry logic
- ➕ Audit logging integration

### What We Rejected
- ❌ French-only hardcoded prompts
- ❌ Simple dict-based state (too fragile)
- ❌ No validation/error handling

---

**End of Design Document**
