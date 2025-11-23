"""
Deterministic Helper Functions for Conversational Survey V2
============================================================

These helpers provide backend-controlled flow logic for conversational surveys,
removing AI decision-making from completion and topic selection.

Created: November 22, 2025
Feature Flag: DETERMINISTIC_SURVEY_FLOW
"""

from typing import Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


def all_goals_completed(
    goals: List[Dict],
    extracted_data: Dict,
    prefilled_fields: Set[str],
    role_excluded_topics: Optional[Set[str]] = None
) -> bool:
    """
    Deterministically check if ALL survey goals are completed.
    
    This function removes completion authority from the LLM and gives it
    to the backend, eliminating "early-stop bugs."
    
    Args:
        goals: List of goal dicts with 'topic', 'fields', 'priority'
        extracted_data: Dict of field_name -> value collected so far
        prefilled_fields: Set of field names pre-populated from participant data
                         (e.g., 'tenure_with_fc', 'company_name')
        role_excluded_topics: Set of topic names excluded for this participant's role
                             (e.g., {'Pricing Value'} for End Users)
    
    Returns:
        True if ALL required fields for ALL applicable goals are filled.
        False if ANY field is missing.
    
    Algorithm:
        1. Filter out role-excluded topics
        2. For each remaining goal:
           - Check if ALL its fields exist in (extracted_data OR prefilled_fields)
           - Return False immediately if any field missing
        3. Return True only if all goals complete
    
    Example:
        goals = [
            {'topic': 'Product Quality', 'fields': ['nps_score', 'satisfaction_rating'], 'priority': 1},
            {'topic': 'Support Quality', 'fields': ['support_rating'], 'priority': 2}
        ]
        extracted_data = {'nps_score': 9, 'satisfaction_rating': 8}
        prefilled_fields = {'tenure_with_fc'}
        
        # Missing 'support_rating' → Returns False
    """
    role_excluded_topics = role_excluded_topics or set()
    
    logger.debug(f"🔍 Checking completion: {len(goals)} total goals, {len(role_excluded_topics)} excluded")
    logger.debug(f"   Extracted data has {len(extracted_data)} fields")
    logger.debug(f"   Prefilled data has {len(prefilled_fields)} fields")
    
    # Filter goals by role (remove excluded topics)
    applicable_goals = [
        goal for goal in goals
        if goal.get('topic') not in role_excluded_topics
    ]
    
    logger.debug(f"   After role filtering: {len(applicable_goals)} applicable goals")
    
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
    allow_multi_turn: bool = True,
    role_excluded_topics: Optional[Set[str]] = None
) -> Tuple[Optional[Dict], List[str], bool]:
    """
    Select the next goal and identify missing fields.
    
    This function provides deterministic topic selection, removing AI control
    over conversation flow.
    
    Args:
        goals: List of goal dicts with 'topic', 'fields', 'priority'
        extracted_data: Dict of collected field values
        prefilled_fields: Set of pre-populated field names
        current_goal_pointer: Name of topic currently being discussed (for multi-turn)
        allow_multi_turn: If True, stay on same topic for follow-up questions
        role_excluded_topics: Topics to exclude for this participant's role
    
    Returns:
        Tuple of (next_goal, missing_fields, is_follow_up):
        - next_goal: Goal dict or None if all complete
        - missing_fields: List of field names still needed
        - is_follow_up: True if this is a clarifying question on same topic
    
    Algorithm:
        1. If current_goal_pointer set AND allow_multi_turn:
           - Check if current goal still has missing fields
           - If yes, return (current_goal, missing_fields, is_follow_up=True)
        2. Otherwise, iterate goals by priority:
           - Find first goal with missing fields
           - Return (goal, missing_fields, is_follow_up=False)
        3. If no missing fields anywhere, return (None, [], False)
    
    Multi-Turn Example:
        User gives vague answer → some fields extracted but others missing
        → get_next_goal() returns SAME goal with is_follow_up=True
        → LLM generates clarifying question for same topic
    
    Example:
        goals = [
            {'topic': 'Product Quality', 'fields': ['nps_score', 'feedback'], 'priority': 1},
            {'topic': 'Pricing', 'fields': ['pricing_rating'], 'priority': 2}
        ]
        extracted_data = {'nps_score': 8}  # Missing 'feedback'
        current_goal_pointer = 'Product Quality'
        
        # Returns: (Product Quality goal, ['feedback'], is_follow_up=True)
    """
    role_excluded_topics = role_excluded_topics or set()
    
    logger.debug(f"🔍 Getting next goal:")
    logger.debug(f"   Current pointer: {current_goal_pointer}")
    logger.debug(f"   Allow multi-turn: {allow_multi_turn}")
    logger.debug(f"   Extracted: {len(extracted_data)} fields")
    
    # Filter goals by role
    applicable_goals = [
        goal for goal in goals
        if goal.get('topic') not in role_excluded_topics
    ]
    
    # STEP 1: Multi-turn logic (stay on same topic if incomplete)
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
                logger.info(f"📍 Multi-turn: Staying on '{current_goal_pointer}' ({len(missing_fields)} fields missing)")
                return current_goal, missing_fields, True  # is_follow_up=True
            else:
                logger.debug(f"   Current goal '{current_goal_pointer}' is now complete")
    
    # STEP 2: Linear progression (find next incomplete goal by priority)
    for goal in sorted(applicable_goals, key=lambda g: g.get('priority', 999)):
        topic = goal.get('topic', 'Unknown')
        fields = goal.get('fields', [])
        
        missing_fields = _get_missing_fields(fields, extracted_data, prefilled_fields)
        
        if missing_fields:
            logger.info(f"📍 Next goal: '{topic}' (priority {goal.get('priority')}, {len(missing_fields)} fields needed)")
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
    print("TESTING DETERMINISTIC HELPERS")
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
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
