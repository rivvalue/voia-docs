"""
Deterministic Helper Functions for Conversational Survey V2
============================================================

These helpers provide backend-controlled flow logic for conversational surveys,
removing AI decision-making from completion and topic selection.

Created: November 22, 2025
Updated: November 23, 2025 - Added per-topic follow-up limit enforcement
Updated: December 11, 2025 - Added topic_status tracking (Phase 5)
Feature Flag: DETERMINISTIC_SURVEY_FLOW
"""

from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Topic Status Tracking (Phase 5 - Dec 2025)
# =============================================================================

def load_topic_status(state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Load topic_status with backward compatibility from old topic_question_counts format.
    
    Topic Status Schema:
    {
        "NPS": {
            "status": "completed",        # completed | skipped | pending | in_progress
            "question_count": 2,
            "deflection": None
        },
        "Product Quality": {
            "status": "skipped",
            "question_count": 1,
            "deflection": {
                "type": "not_responsible",
                "reason": "Delegates to product owner",
                "detected_at": "2025-12-11T10:30:00Z"
            }
        }
    }
    
    Args:
        state: Persisted conversation state dict
    
    Returns:
        Dict of topic -> status info (new format)
    """
    if 'topic_status' in state:
        # New format - use directly
        return state['topic_status']
    elif 'topic_question_counts' in state:
        # Migrate old format to new format
        logger.debug("Migrating topic_question_counts to topic_status format")
        return {
            topic: {
                "status": "pending",
                "question_count": count,
                "deflection": None
            }
            for topic, count in state['topic_question_counts'].items()
        }
    return {}


def get_topic_question_counts(topic_status: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    """
    Extract question counts from topic_status for backward compatibility.
    
    This allows existing code using topic_question_counts to continue working
    during the transition period.
    
    Args:
        topic_status: New format topic status dict
    
    Returns:
        Dict of topic -> question_count (old format)
    """
    return {
        topic: info.get('question_count', 0)
        for topic, info in topic_status.items()
    }


def update_topic_status(
    topic_status: Dict[str, Dict[str, Any]],
    topic: str,
    status: Optional[str] = None,
    increment_count: bool = False,
    deflection: Optional[Dict[str, Any]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Update topic status with new information.
    
    Args:
        topic_status: Current topic status dict
        topic: Topic name to update
        status: New status (completed, skipped, pending, in_progress)
        increment_count: If True, increment question_count by 1
        deflection: Deflection info to record
    
    Returns:
        Updated topic_status dict
    """
    if topic not in topic_status:
        topic_status[topic] = {
            "status": "pending",
            "question_count": 0,
            "deflection": None
        }
    
    if status:
        topic_status[topic]["status"] = status
    
    if increment_count:
        topic_status[topic]["question_count"] = topic_status[topic].get("question_count", 0) + 1
    
    if deflection:
        topic_status[topic]["deflection"] = deflection
        topic_status[topic]["status"] = "skipped"
    
    return topic_status


def get_completion_summary(topic_status: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of topic completion for analytics.
    
    Args:
        topic_status: Topic status dict
    
    Returns:
        Summary dict with completion stats
    """
    total_topics = len(topic_status)
    completed = sum(1 for t in topic_status.values() if t.get('status') == 'completed')
    skipped = sum(1 for t in topic_status.values() if t.get('status') == 'skipped')
    deflections = [
        {
            "topic": topic,
            "type": info['deflection'].get('type'),
            "reason": info['deflection'].get('reason')
        }
        for topic, info in topic_status.items()
        if info.get('deflection')
    ]
    
    return {
        "total_topics": total_topics,
        "completed": completed,
        "skipped": skipped,
        "completion_rate": completed / total_topics if total_topics > 0 else 0,
        "total_deflections": len(deflections),
        "deflections": deflections
    }


def all_goals_completed(
    goals: List[Dict],
    extracted_data: Dict,
    prefilled_fields: Set[str],
    role_excluded_topics: Optional[Set[str]] = None,
    check_optional: bool = False
) -> bool:
    """
    Deterministically check if survey goals are completed.
    
    **CRITICAL CHANGE (Nov 22, 2025):** Now distinguishes between must-ask and optional topics.
    Survey can end when ALL MUST-ASK topics are complete, even if optional topics remain.
    
    This function removes completion authority from the LLM and gives it
    to the backend, eliminating "early-stop bugs."
    
    Args:
        goals: List of goal dicts with 'topic', 'fields', 'priority', 'is_required'
        extracted_data: Dict of field_name -> value collected so far
        prefilled_fields: Set of field names pre-populated from participant data
                         (e.g., 'tenure_with_fc', 'company_name')
        role_excluded_topics: Set of topic names excluded for this participant's role
                             (e.g., {'Pricing Value'} for End Users)
        check_optional: If True, checks optional topics too. If False (default),
                       only checks must-ask topics (allows graceful end)
    
    Returns:
        True if ALL MUST-ASK goals are complete (or all goals if check_optional=True).
        False if ANY must-ask field is missing.
    
    Algorithm:
        1. Filter out role-excluded topics
        2. Filter by is_required flag (if check_optional=False, only check required)
        3. For each remaining goal:
           - Check if ALL its fields exist in (extracted_data OR prefilled_fields)
           - Return False immediately if any field missing
        4. Return True only if all checked goals complete
    
    Example (Must-Ask Only):
        goals = [
            {'topic': 'Product Quality', 'fields': ['nps_score'], 'is_required': True},
            {'topic': 'Pricing', 'fields': ['pricing_rating'], 'is_required': False}
        ]
        extracted_data = {'nps_score': 9}  # Missing optional pricing_rating
        
        all_goals_completed(..., check_optional=False)  # Returns True (must-ask done)
        all_goals_completed(..., check_optional=True)   # Returns False (optional missing)
    """
    role_excluded_topics = role_excluded_topics or set()
    
    logger.debug(f"🔍 Checking completion: {len(goals)} total goals, {len(role_excluded_topics)} excluded")
    logger.debug(f"   Check optional: {check_optional}")
    logger.debug(f"   Extracted data has {len(extracted_data)} fields")
    logger.debug(f"   Prefilled data has {len(prefilled_fields)} fields")
    
    # Filter goals by role (remove excluded topics)
    applicable_goals = [
        goal for goal in goals
        if goal.get('topic') not in role_excluded_topics
    ]
    
    # Filter by required/optional status
    if not check_optional:
        # Only check must-ask topics (optional can be incomplete)
        applicable_goals = [
            goal for goal in applicable_goals
            if goal.get('is_required', True)  # Default to required if not specified
        ]
        logger.debug(f"   Checking ONLY must-ask topics")
    
    logger.debug(f"   After filtering: {len(applicable_goals)} applicable goals")
    
    for goal in sorted(applicable_goals, key=lambda g: g.get('priority', 999)):
        topic = goal.get('topic', 'Unknown')
        fields = goal.get('fields', [])
        
        logger.debug(f"   Checking goal '{topic}' with {len(fields)} fields")
        
        for field in fields:
            # Field is complete if it exists in EITHER extracted_data OR prefilled_fields
            is_extracted = field in extracted_data and extracted_data[field] not in [None, '', []]
            is_prefilled = field in prefilled_fields
            
            if not (is_extracted or is_prefilled):
                logger.debug(f"      ❌ Missing field '{field}' in topic '{topic}'")
                return False
            else:
                source = "extracted" if is_extracted else "prefilled"
                logger.debug(f"      ✓ Field '{field}' complete (source: {source})")
    
    logger.info(f"✅ All goals completed! {len(applicable_goals)} goals with all fields filled")
    return True


def get_next_goal(
    goals: List[Dict],
    extracted_data: Dict,
    prefilled_fields: Set[str],
    current_goal_pointer: Optional[str] = None,
    topic_question_counts: Optional[Dict[str, int]] = None,  # NEW: Per-topic counter
    max_follow_up_per_topic: int = 2,                        # NEW: Campaign limit
    allow_multi_turn: bool = True,
    role_excluded_topics: Optional[Set[str]] = None,
    limit_optional_follow_ups: bool = True
) -> Tuple[Optional[Dict], List[str], bool]:
    """
    Select the next goal and identify missing fields with TWO-TIER PRIORITY and PER-TOPIC FOLLOW-UP LIMITS.
    
    **CRITICAL CHANGES:**
    - Nov 22, 2025: Implements must-ask vs optional topic prioritization
    - Nov 23, 2025: Added per-topic follow-up counter enforcement (backend-controlled)
    
    This function provides deterministic topic selection, removing AI control
    over conversation flow.
    
    Args:
        goals: List of goal dicts with 'topic', 'fields', 'priority', 'is_required'
        extracted_data: Dict of collected field values
        prefilled_fields: Set of pre-populated field names
        current_goal_pointer: Name of topic currently being discussed (for multi-turn)
        topic_question_counts: Dict tracking questions per topic (e.g., {"Product Quality": 2})
        max_follow_up_per_topic: Campaign-configured follow-up limit (default: 2)
        allow_multi_turn: If True, stay on same topic for follow-up questions
        role_excluded_topics: Topics to exclude for this participant's role
        limit_optional_follow_ups: If True, optional topics get limited follow-ups
    
    Returns:
        Tuple of (next_goal, missing_fields, is_follow_up):
        - next_goal: Goal dict or None if all complete
        - missing_fields: List of field names still needed
        - is_follow_up: True if this is a clarifying question on same topic
    
    Algorithm (TWO-TIER PRIORITY with FOLLOW-UP ENFORCEMENT):
        1. If current_goal_pointer set AND allow_multi_turn:
           - Check if current goal still has missing fields
           - Check per-topic follow-up limit:
             * ALL topics: ENFORCE limit (accept partial data when exceeded)
             * FIX (Nov 23, 2025): Removed must-ask bypass to prevent infinite loops
           - If allowed, return (current_goal, missing_fields, is_follow_up=True)
        2. Otherwise, iterate goals by priority:
           - TIER 1: Must-ask topics (is_required=True)
           - TIER 2: Optional topics (is_required=False, only if must-ask complete)
           - Find first goal with missing fields
           - Return (goal, missing_fields, is_follow_up=False)
        3. If no missing fields anywhere, return (None, [], False)
    
    Example:
        goals = [
            {'topic': 'Product Quality', 'fields': ['nps_score', 'feedback'], 'priority': 1, 'is_required': True},
            {'topic': 'Pricing', 'fields': ['pricing_rating'], 'priority': 2, 'is_required': False}
        ]
        extracted_data = {'nps_score': 8}
        current_goal_pointer = 'Product Quality'
        topic_question_counts = {'Product Quality': 3}  # 3 questions asked (1 initial + 2 follow-ups)
        max_follow_up_per_topic = 2
        
        # FIX (Nov 23, 2025): ALL topics respect limit, even must-ask
        # Returns: (None, [], False) - limit reached, moves to next topic
    """
    # Default to empty dict if None (avoid None checks throughout)
    topic_question_counts = topic_question_counts or {}
    role_excluded_topics = role_excluded_topics or set()
    
    logger.debug(f"🔍 Getting next goal:")
    logger.debug(f"   Current pointer: {current_goal_pointer}")
    logger.debug(f"   Allow multi-turn: {allow_multi_turn}")
    logger.debug(f"   Topic question counts: {topic_question_counts}")
    logger.debug(f"   Max follow-ups per topic: {max_follow_up_per_topic}")
    logger.debug(f"   Extracted: {len(extracted_data)} fields")
    
    # Filter goals by role
    applicable_goals = [
        goal for goal in goals
        if goal.get('topic') not in role_excluded_topics
    ]
    
    # STEP 1: Multi-turn logic with per-topic follow-up limit enforcement
    if current_goal_pointer and allow_multi_turn:
        current_goal = next(
            (g for g in applicable_goals if g.get('topic') == current_goal_pointer),
            None
        )
        
        if current_goal:
            missing_fields = _get_missing_fields(
                current_goal.get('fields', []),
                extracted_data,
                prefilled_fields
            )
            
            if missing_fields:
                # NEW: Check per-topic follow-up limit (ENFORCED FOR ALL TOPICS)
                questions_asked = topic_question_counts.get(current_goal_pointer, 1)
                follow_ups_used = questions_asked - 1  # First question isn't a follow-up
                is_required = current_goal.get('is_required', True)
                
                # FIX (Nov 23, 2025): ALL topics must respect follow-up limit (no bypass)
                if follow_ups_used < max_follow_up_per_topic:
                    # Under limit: allow follow-up
                    topic_type = "MUST-ASK" if is_required else "OPTIONAL"
                    logger.info(
                        f"📍 Multi-turn on {topic_type} '{current_goal_pointer}' "
                        f"(follow-ups: {follow_ups_used}/{max_follow_up_per_topic})"
                    )
                    return current_goal, missing_fields, True
                    
                else:
                    # Limit exceeded: accept partial data and move on
                    topic_type = "MUST-ASK" if is_required else "OPTIONAL"
                    logger.info(
                        f"⚠️ Follow-up limit reached for {topic_type} '{current_goal_pointer}' "
                        f"({follow_ups_used}/{max_follow_up_per_topic}) - accepting partial data"
                    )
                    # Fall through to next topic selection
            else:
                logger.debug(f"   Current goal '{current_goal_pointer}' is now complete")
    
    # STEP 2: TWO-TIER progression (must-ask first, then optional)
    
    # TIER 1: Must-ask topics (required=True)
    must_ask_goals = [g for g in applicable_goals if g.get('is_required', True)]
    for goal in sorted(must_ask_goals, key=lambda g: g.get('priority', 999)):
        topic = goal.get('topic', 'Unknown')
        fields = goal.get('fields', [])
        
        # FIX (Nov 23, 2025): Skip must-ask topics that have exhausted follow-up limit
        # This prevents infinite loop when must-ask topic hits limit but still has missing fields
        questions_asked = topic_question_counts.get(topic, 0)
        follow_ups_used = max(0, questions_asked - 1)  # First question isn't a follow-up
        
        if follow_ups_used >= max_follow_up_per_topic:
            logger.debug(f"   Skipping MUST-ASK topic '{topic}' - follow-up limit exhausted ({follow_ups_used}/{max_follow_up_per_topic})")
            continue  # Skip this exhausted must-ask topic
        
        missing_fields = _get_missing_fields(fields, extracted_data, prefilled_fields)
        
        if missing_fields:
            logger.info(f"📍 Next goal (MUST-ASK): '{topic}' (priority {goal.get('priority')}, {len(missing_fields)} fields needed)")
            return goal, missing_fields, False  # is_follow_up=False
    
    # TIER 2: Optional topics (required=False) - only if all must-ask complete
    optional_goals = [g for g in applicable_goals if not g.get('is_required', True)]
    for goal in sorted(optional_goals, key=lambda g: g.get('priority', 999)):
        topic = goal.get('topic', 'Unknown')
        fields = goal.get('fields', [])
        
        # CRITICAL FIX (Nov 23, 2025): Skip optional topics that have exhausted follow-up limit
        # This prevents infinite loop when optional topic hits limit but still has missing fields
        questions_asked = topic_question_counts.get(topic, 0)
        follow_ups_used = max(0, questions_asked - 1)  # First question isn't a follow-up
        
        if follow_ups_used >= max_follow_up_per_topic:
            logger.debug(f"   Skipping OPTIONAL topic '{topic}' - follow-up limit exhausted ({follow_ups_used}/{max_follow_up_per_topic})")
            continue  # Skip this exhausted optional topic
        
        missing_fields = _get_missing_fields(fields, extracted_data, prefilled_fields)
        
        if missing_fields:
            logger.info(f"📍 Next goal (OPTIONAL): '{topic}' (priority {goal.get('priority')}, {len(missing_fields)} fields needed)")
            return goal, missing_fields, False  # is_follow_up=False
    
    # STEP 3: All goals complete
    logger.info(f"✅ No more goals - all {len(applicable_goals)} goals complete!")
    return None, [], False


def _get_missing_fields(
    fields: List[str],
    extracted_data: Dict,
    prefilled_fields: Set[str]
) -> List[str]:
    """
    Helper: Identify which fields are still missing for a goal.
    
    A field is considered "present" if it exists in EITHER:
    - extracted_data (with non-empty value)
    - prefilled_fields (pre-populated from participant)
    
    Args:
        fields: List of field names required for this goal
        extracted_data: Dict of collected values
        prefilled_fields: Set of pre-populated field names
    
    Returns:
        List of field names that are still missing
    """
    missing = []
    
    for field in fields:
        is_extracted = field in extracted_data and extracted_data[field] not in [None, '', []]
        is_prefilled = field in prefilled_fields
        
        if not (is_extracted or is_prefilled):
            missing.append(field)
    
    return missing


def validate_extracted_data(
    extracted_data: Dict,
    field_name: str,
    expected_type: Optional[str] = None,
    valid_range: Optional[Tuple] = None
) -> bool:
    """
    Validate quality of extracted data (optional enhancement).
    
    This is a stub for future validation logic to detect when LLM
    extraction produces invalid or poor-quality data.
    
    Args:
        extracted_data: Dict of extracted field values
        field_name: Name of field to validate
        expected_type: 'int', 'float', 'string', etc.
        valid_range: Tuple of (min, max) for numeric fields
    
    Returns:
        True if data is valid, False if questionable
    
    Example:
        # NPS score must be 0-10
        validate_extracted_data(
            {'nps_score': 15},
            'nps_score',
            expected_type='int',
            valid_range=(0, 10)
        )
        # Returns False (out of range)
    """
    if field_name not in extracted_data:
        return False
    
    value = extracted_data[field_name]
    
    # Type validation
    if expected_type == 'int':
        try:
            value = int(value)
        except (ValueError, TypeError):
            logger.warning(f"⚠️ Field '{field_name}' expected int, got {type(value)}")
            return False
    
    # Range validation
    if valid_range and expected_type in ['int', 'float']:
        min_val, max_val = valid_range
        if not (min_val <= value <= max_val):
            logger.warning(f"⚠️ Field '{field_name}' value {value} outside range {valid_range}")
            return False
    
    return True


# ============================================================================
# INTEGRATION HELPERS (for connecting to existing VOÏA infrastructure)
# ============================================================================

def build_role_exclusions(participant_role: Optional[str]) -> Set[str]:
    """
    Build set of excluded topics based on participant role.
    
    This integrates with existing role-based filtering logic from
    prompt_template_service.py (ROLE_METADATA).
    
    Args:
        participant_role: Role string ('End User', 'Team Lead', 'Manager', etc.)
    
    Returns:
        Set of topic names to exclude
    
    Example:
        build_role_exclusions('End User')
        # Returns: {'Pricing Value'}  (end users don't discuss pricing)
    """
    # Map from prompt_template_service.py ROLE_METADATA
    ROLE_EXCLUSIONS = {
        'End User': {'Pricing Value'},
        'Team Lead': {'Pricing Value'},
        # Managers, Directors, Executives see all topics
    }
    
    return ROLE_EXCLUSIONS.get(participant_role, set())


def apply_role_priority_adjustments(goals: List[Dict], participant_role: Optional[str]) -> List[Dict]:
    """
    Apply role-based priority adjustments to survey goals.
    
    FIX (Nov 23, 2025): Participant role now influences question priority order.
    Different roles care about different aspects of the service/product:
    - End Users: Care more about Product Quality, User Experience
    - Team Leads: Care more about Support, Team collaboration features
    - Managers/Directors/Executives: Maintain campaign priorities (strategic view)
    
    Args:
        goals: List of goal dicts with 'topic', 'priority', 'is_required', etc.
        participant_role: Role string ('End User', 'Team Lead', 'Manager', etc.)
    
    Returns:
        New list of goals with adjusted priorities (sorted by new priority)
    
    Example:
        goals = [
            {'topic': 'NPS', 'priority': 1, ...},
            {'topic': 'Product Quality', 'priority': 2, ...},
            {'topic': 'Pricing Value', 'priority': 3, ...}
        ]
        
        # For End User:
        apply_role_priority_adjustments(goals, 'End User')
        # Returns: [NPS (1), Product Quality (1.5 boosted), ...] 
        # (Product Quality moved up in priority)
    """
    if not participant_role or participant_role in ['Manager', 'Director', 'Executive']:
        # Strategic roles: maintain campaign priorities (business-driven order)
        logger.debug(f"Role '{participant_role}': Using campaign priorities (no adjustments)")
        return sorted(goals, key=lambda g: g.get('priority', 999))
    
    # Role-based priority adjustments (negative = boost priority, positive = lower priority)
    ROLE_ADJUSTMENTS = {
        'End User': {
            'Product Quality': -0.5,      # Boost: End users care about product
            'User Experience': -0.5,      # Boost: UX is critical for end users
            'Support Quality': -0.3,      # Boost: They need help often
            'Support Experience': -0.3,   # Boost: Similar to Support Quality
            'Pricing Value': 999,         # Excluded (handled by build_role_exclusions)
        },
        'Team Lead': {
            'Support Quality': -0.5,      # Boost: They interact with support for team
            'Support Experience': -0.5,   # Boost: Team support matters
            'Product Quality': -0.3,      # Boost: They guide team usage
            'Pricing Value': 999,         # Excluded (handled by build_role_exclusions)
        }
    }
    
    adjustments = ROLE_ADJUSTMENTS.get(participant_role, {})
    
    if not adjustments:
        logger.debug(f"Role '{participant_role}': No priority adjustments defined")
        return sorted(goals, key=lambda g: g.get('priority', 999))
    
    # Apply adjustments to create new goal list with adjusted priorities
    adjusted_goals = []
    for goal in goals:
        topic = goal.get('topic', '')
        base_priority = goal.get('priority', 999)
        adjustment = adjustments.get(topic, 0)
        
        # Create new goal dict with adjusted priority (don't mutate original)
        adjusted_goal = goal.copy()
        adjusted_goal['priority'] = base_priority + adjustment
        adjusted_goal['original_priority'] = base_priority  # Track for debugging
        
        if adjustment != 0:
            logger.debug(f"  Role adjustment: {topic} priority {base_priority} → {adjusted_goal['priority']} "
                        f"(adjustment: {adjustment:+.1f})")
        
        adjusted_goals.append(adjusted_goal)
    
    # Sort by adjusted priority
    adjusted_goals.sort(key=lambda g: g.get('priority', 999))
    
    logger.info(f"Applied role '{participant_role}' priority adjustments to {len(goals)} goals")
    
    return adjusted_goals


def extract_prefilled_fields(participant_data: Dict) -> Set[str]:
    """
    Extract field names that are pre-populated from participant data.
    
    These fields don't need to be asked in the survey since we already
    have the data from participant upload.
    
    Args:
        participant_data: Dict with participant info (from Participant model)
    
    Returns:
        Set of field names that are already filled
    
    Example:
        participant = {
            'tenure_with_fc': '5-10 years',
            'company_name': 'Acme Corp',
            'role': 'Manager'
        }
        extract_prefilled_fields(participant)
        # Returns: {'tenure_with_fc', 'company_name'}
    """
    prefilled = set()
    
    # Fields that come from participant upload
    PARTICIPANT_FIELDS = [
        'tenure_with_fc',
        'company_name',
        'role',
        'region',
        'tier',
        'client_industry',
        'email'  # Usually provided via token
    ]
    
    for field in PARTICIPANT_FIELDS:
        if field in participant_data and participant_data[field] not in [None, '', 'None']:
            prefilled.add(field)
    
    return prefilled


# ============================================================================
# UNIT TEST STUBS (for validation during development)
# ============================================================================

if __name__ == '__main__':
    """
    Quick validation tests for helpers.
    Run: python deterministic_helpers.py
    """
    
    print("=" * 60)
    print("TESTING DETERMINISTIC HELPERS (V2 - WITH FOLLOW-UP LIMITS)")
    print("=" * 60)
    
    # Test data
    test_goals = [
        {
            'topic': 'Product Quality',
            'fields': ['nps_score', 'satisfaction_rating'],
            'priority': 1
        },
        {
            'topic': 'Support Quality',
            'fields': ['support_rating', 'response_time_rating'],
            'priority': 2
        },
        {
            'topic': 'Pricing Value',
            'fields': ['pricing_satisfaction'],
            'priority': 3
        }
    ]
    
    # Test 1: Not complete (missing fields)
    print("\n--- Test 1: Incomplete survey ---")
    result = all_goals_completed(
        goals=test_goals,
        extracted_data={'nps_score': 9},
        prefilled_fields=set()
    )
    assert result == False, "Should return False when fields missing"
    print("✓ Correctly identified incomplete survey")
    
    # Test 2: Complete with extracted + prefilled
    print("\n--- Test 2: Complete with mixed data ---")
    result = all_goals_completed(
        goals=test_goals,
        extracted_data={
            'nps_score': 9,
            'satisfaction_rating': 8,
            'support_rating': 7,
            'response_time_rating': 6
        },
        prefilled_fields={'pricing_satisfaction'}  # Pricing prefilled
    )
    assert result == True, "Should return True when all fields present"
    print("✓ Correctly identified complete survey (extracted + prefilled)")
    
    # Test 3: Role exclusion (End User excludes Pricing)
    print("\n--- Test 3: Role-based exclusion ---")
    result = all_goals_completed(
        goals=test_goals,
        extracted_data={
            'nps_score': 9,
            'satisfaction_rating': 8,
            'support_rating': 7,
            'response_time_rating': 6
        },
        prefilled_fields=set(),
        role_excluded_topics={'Pricing Value'}  # End User doesn't answer pricing
    )
    assert result == True, "Should ignore excluded topics"
    print("✓ Correctly excluded Pricing topic for End User")
    
    # Test 4: Get next goal (linear)
    print("\n--- Test 4: Get next goal (linear progression) ---")
    goal, missing, is_follow_up = get_next_goal(
        goals=test_goals,
        extracted_data={'nps_score': 9},  # First goal partially complete
        prefilled_fields=set(),
        current_goal_pointer=None
    )
    assert goal['topic'] == 'Product Quality', "Should return first incomplete goal"
    assert 'satisfaction_rating' in missing, "Should identify missing field"
    assert is_follow_up == False, "Should not be follow-up on first call"
    print(f"✓ Correctly selected '{goal['topic']}' with missing: {missing}")
    
    # Test 5: Multi-turn same topic
    print("\n--- Test 5: Multi-turn on same topic ---")
    goal, missing, is_follow_up = get_next_goal(
        goals=test_goals,
        extracted_data={'nps_score': 9},  # Still missing satisfaction_rating
        prefilled_fields=set(),
        current_goal_pointer='Product Quality',  # Currently on this topic
        allow_multi_turn=True
    )
    assert goal['topic'] == 'Product Quality', "Should stay on same topic"
    assert is_follow_up == True, "Should be marked as follow-up"
    print(f"✓ Correctly stayed on '{goal['topic']}' for follow-up")
    
    # Test 6: Move to next topic after completion
    print("\n--- Test 6: Progress to next topic ---")
    goal, missing, is_follow_up = get_next_goal(
        goals=test_goals,
        extracted_data={
            'nps_score': 9,
            'satisfaction_rating': 8  # Product Quality now complete
        },
        prefilled_fields=set(),
        current_goal_pointer='Product Quality'
    )
    assert goal['topic'] == 'Support Quality', "Should move to next topic"
    assert is_follow_up == False, "Should not be follow-up when changing topics"
    print(f"✓ Correctly moved to next topic: '{goal['topic']}'")
    
    # Test 7: All complete (no next goal)
    print("\n--- Test 7: Survey complete ---")
    goal, missing, is_follow_up = get_next_goal(
        goals=test_goals,
        extracted_data={
            'nps_score': 9,
            'satisfaction_rating': 8,
            'support_rating': 7,
            'response_time_rating': 6,
            'pricing_satisfaction': 5
        },
        prefilled_fields=set()
    )
    assert goal is None, "Should return None when all complete"
    assert missing == [], "Should have no missing fields"
    print("✓ Correctly identified survey completion")
    
    # Test 8: Must-ask vs Optional (must-ask incomplete, can't end)
    print("\n--- Test 8: Must-ask incomplete → survey cannot end ---")
    test_goals_with_required = [
        {
            'topic': 'Product Quality',
            'fields': ['nps_score'],
            'priority': 1,
            'is_required': True  # MUST ASK
        },
        {
            'topic': 'Pricing',
            'fields': ['pricing_rating'],
            'priority': 2,
            'is_required': False  # OPTIONAL
        }
    ]
    result = all_goals_completed(
        goals=test_goals_with_required,
        extracted_data={'pricing_rating': 8},  # Only optional filled
        prefilled_fields=set(),
        check_optional=False
    )
    assert result == False, "Should return False when must-ask incomplete"
    print("✓ Correctly blocked completion with must-ask missing")
    
    # Test 9: Must-ask complete, optional incomplete → can end
    print("\n--- Test 9: Must-ask complete, optional incomplete → graceful end ---")
    result = all_goals_completed(
        goals=test_goals_with_required,
        extracted_data={'nps_score': 9},  # Must-ask filled, optional missing
        prefilled_fields=set(),
        check_optional=False
    )
    assert result == True, "Should return True when must-ask complete (optional can be incomplete)"
    print("✓ Correctly allowed completion with only must-ask done")
    
    # Test 10: Two-tier priority (must-ask first)
    print("\n--- Test 10: Two-tier priority system ---")
    goal, missing, is_follow_up = get_next_goal(
        goals=test_goals_with_required,
        extracted_data={},  # Nothing filled yet
        prefilled_fields=set()
    )
    assert goal['topic'] == 'Product Quality', "Should prioritize must-ask topic first"
    assert goal['is_required'] == True, "Should be a required topic"
    print(f"✓ Correctly prioritized MUST-ASK topic: '{goal['topic']}'")
    
    # Test 11: Must-ask done, now ask optional
    print("\n--- Test 11: After must-ask, ask optional ---")
    goal, missing, is_follow_up = get_next_goal(
        goals=test_goals_with_required,
        extracted_data={'nps_score': 9},  # Must-ask complete
        prefilled_fields=set()
    )
    assert goal['topic'] == 'Pricing', "Should move to optional topic after must-ask complete"
    assert goal['is_required'] == False, "Should be optional topic"
    print(f"✓ Correctly moved to OPTIONAL topic: '{goal['topic']}'")
    
    # ===== NEW TESTS FOR FOLLOW-UP LIMIT ENFORCEMENT =====
    
    # Test 12: Optional topic hits follow-up limit
    print("\n--- Test 12: Optional topic follow-up limit enforcement ---")
    goal, missing, is_follow_up = get_next_goal(
        goals=test_goals_with_required,
        extracted_data={},  # Pricing still missing
        prefilled_fields=set(),
        current_goal_pointer='Pricing',  # Currently on optional topic
        topic_question_counts={'Pricing': 3},  # 3 questions asked (1 initial + 2 follow-ups)
        max_follow_up_per_topic=2,  # Limit is 2 follow-ups
        allow_multi_turn=True
    )
    # Should force move to next topic (or None if all complete)
    assert goal is None or goal['topic'] != 'Pricing', "Should NOT stay on Pricing after limit exceeded"
    print("✓ Correctly enforced follow-up limit on OPTIONAL topic")
    
    # Test 13: Must-ask topic bypasses follow-up limit
    print("\n--- Test 13: Must-ask topic bypasses follow-up limit ---")
    goal, missing, is_follow_up = get_next_goal(
        goals=test_goals_with_required,
        extracted_data={},  # Product Quality still missing
        prefilled_fields=set(),
        current_goal_pointer='Product Quality',  # Currently on must-ask topic
        topic_question_counts={'Product Quality': 5},  # 5 questions asked (way over limit)
        max_follow_up_per_topic=2,  # Limit is 2 follow-ups
        allow_multi_turn=True
    )
    # Should STAY on Product Quality despite exceeding limit (must-ask bypass)
    assert goal['topic'] == 'Product Quality', "Should stay on MUST-ASK despite limit"
    assert is_follow_up == True, "Should be follow-up"
    print("✓ Correctly bypassed follow-up limit on MUST-ASK topic")
    
    # Test 14: Counter-based follow-up decision (under limit)
    print("\n--- Test 14: Optional topic under follow-up limit ---")
    goal, missing, is_follow_up = get_next_goal(
        goals=test_goals_with_required,
        extracted_data={},  # Pricing still missing
        prefilled_fields=set(),
        current_goal_pointer='Pricing',  # Currently on optional topic
        topic_question_counts={'Pricing': 2},  # 2 questions asked (1 initial + 1 follow-up)
        max_follow_up_per_topic=2,  # Limit is 2 follow-ups
        allow_multi_turn=True
    )
    # Should stay on Pricing (under limit: 1 follow-up used, 2 allowed)
    assert goal['topic'] == 'Pricing', "Should stay on OPTIONAL when under limit"
    assert is_follow_up == True, "Should be follow-up"
    print("✓ Correctly allowed follow-up on OPTIONAL topic (under limit)")
    
    # Test 15: CRITICAL - Exhausted optional topic is skipped (no infinite loop)
    print("\n--- Test 15: Exhausted optional topic skipped in TIER 2 (infinite loop fix) ---")
    test_goals_multi_optional = [
        {
            'topic': 'Product Quality',
            'fields': ['nps_score'],
            'priority': 1,
            'is_required': True  # MUST ASK
        },
        {
            'topic': 'Pricing',
            'fields': ['pricing_rating'],
            'priority': 2,
            'is_required': False  # OPTIONAL
        },
        {
            'topic': 'Support',
            'fields': ['support_rating'],
            'priority': 3,
            'is_required': False  # OPTIONAL
        }
    ]
    # Scenario: Must-ask complete, Pricing hit limit with missing data, Support not started
    goal, missing, is_follow_up = get_next_goal(
        goals=test_goals_multi_optional,
        extracted_data={'nps_score': 9},  # Must-ask complete
        prefilled_fields=set(),
        current_goal_pointer=None,  # Not in multi-turn
        topic_question_counts={'Pricing': 3},  # Pricing exhausted (1 initial + 2 follow-ups)
        max_follow_up_per_topic=2,
        allow_multi_turn=False
    )
    # Should skip exhausted Pricing and move to Support
    assert goal is not None, "Should find next topic (not None)"
    assert goal['topic'] == 'Support', "Should skip exhausted Pricing and select Support"
    assert is_follow_up == False, "Should not be follow-up (new topic)"
    print("✓ Correctly skipped exhausted optional topic and moved to next (no infinite loop)")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓ (including infinite loop fix)")
    print("=" * 60)
