# Phase 1 Implementation Readiness Assessment
**Date:** November 23, 2025  
**Status:** ✅ APPROVED - Ready to proceed to Phase 2

---

## Gap 1: Database Schema Verification

### ✅ VERIFIED - No Migration Needed

**Campaign Model Fields Status:**

| Field | Status | Location | Notes |
|-------|--------|----------|-------|
| `max_follow_ups_per_topic` | ✅ EXISTS | `models.py:232` | `db.Column(db.Integer, nullable=True, default=2)` |
| `product_description` | ✅ EXISTS | `models.py:227` | `db.Column(db.Text, nullable=True)` |
| `conversation_tone` | ⚠️ INDIRECT | Via BusinessAccount | Campaign doesn't have it, but BusinessAccount does (cascade fallback works) |

**Conclusion:** All required fields are present. No database migration needed.

**V2 Controller Implementation Note:**
```python
# Conversation tone cascade pattern (already works):
conversation_tone = self.campaign.conversation_tone or \
                    self.business_account.conversation_tone or \
                    "professional"
```

---

## Gap 2: Session Storage Strategy

### ✅ DECISION - Use Existing Database-Backed Storage

**Current Infrastructure:**
- ✅ `ActiveConversation` model exists (`models.py:154-186`)
- ✅ Persistence functions exist:
  - `save_conversation_state()` (line 1648)
  - `load_conversation_state()` (line 1692)
  - `delete_conversation_state()` (line 1726)
- ✅ Multi-worker safe (database-backed, not Flask session)

**Current ActiveConversation Schema:**
```python
class ActiveConversation(db.Model):
    conversation_id = db.Column(db.String(36), primary_key=True)
    business_account_id = db.Column(db.Integer, ForeignKey)
    campaign_id = db.Column(db.Integer, ForeignKey)
    participant_data = db.Column(db.Text)
    conversation_history = db.Column(db.Text)  # JSON
    extracted_data = db.Column(db.Text)        # JSON
    survey_data = db.Column(db.Text)           # JSON (legacy field)
    step_count = db.Column(db.Integer)
    created_at = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime)
```

**V2 Additional State Needed:**
- `current_goal_pointer` (string, topic name)
- `topic_question_counts` (JSON dict, e.g., `{"Product Quality": 2}`)

**Implementation Strategy:**

**Option A (RECOMMENDED):** Store in existing `survey_data` JSON field
```python
# V2 stores additional state in survey_data:
survey_data = {
    'current_goal_pointer': 'Product Quality',
    'topic_question_counts': {'Product Quality': 2, 'Support': 1},
    'last_activity': '2025-11-23T10:30:00Z',
    'resume_offered': False
}
```

**Option B:** Add new columns (requires migration)
```python
# Would need migration:
current_goal_pointer = db.Column(db.String(100))
topic_question_counts = db.Column(db.JSON)
```

**Decision:** Use Option A (survey_data JSON field)
- ✅ No migration needed
- ✅ Backward compatible
- ✅ Flexible for future additions
- ✅ Already proven pattern (existing fields use JSON)

---

## Gap 3: Helper Implementation Alignment

### ⚠️ NEEDS UPDATE - Deterministic Helpers Missing V2 Features

**Current Status:**
- ✅ `all_goals_completed()` - fully aligned with design
- ✅ `get_next_goal()` - has two-tier priority logic
- ❌ `get_next_goal()` - missing per-topic follow-up counters
- ❌ `get_next_goal()` - missing follow-up limit enforcement

**Required Updates to `deterministic_helpers.py`:**

**1. Update `get_next_goal()` Signature:**
```python
def get_next_goal(
    goals: List[Dict],
    extracted_data: Dict,
    prefilled_fields: Set[str],
    current_goal_pointer: Optional[str] = None,
    topic_question_counts: Dict[str, int] = None,  # NEW: Per-topic counter
    max_follow_up_per_topic: int = 2,              # NEW: Campaign-configured limit
    allow_multi_turn: bool = True,
    role_excluded_topics: Optional[Set[str]] = None,
    limit_optional_follow_ups: bool = True
) -> Tuple[Optional[Dict], List[str], bool]:
```

**2. Add Follow-Up Limit Enforcement Logic:**
```python
# In multi-turn section:
if current_goal_pointer and allow_multi_turn:
    current_goal = next((g for g in applicable_goals 
                        if g.get('topic') == current_goal_pointer), None)
    
    if current_goal:
        missing_fields = _get_missing_fields(...)
        
        if missing_fields:
            # NEW: Check per-topic follow-up limit
            follow_ups_used = topic_question_counts.get(current_goal_pointer, 1) - 1
            is_required = current_goal.get('is_required', True)
            
            # Must-ask topics bypass limit
            if is_required or follow_ups_used < max_follow_up_per_topic:
                return current_goal, missing_fields, True
            else:
                logger.info(f"Follow-up limit reached for '{current_goal_pointer}' - moving on")
                # Fall through to next topic selection
```

**3. Update Unit Tests:**
- Add test for per-topic follow-up limit enforcement
- Add test for must-ask bypass exception
- Add test for optional topic limit respect

---

## Implementation Plan for Phase 1 Completion

### Task 1: Update `deterministic_helpers.py` (2 hours)

**File:** `deterministic_helpers.py`

**Changes:**
1. Add `topic_question_counts` parameter to `get_next_goal()`
2. Add `max_follow_up_per_topic` parameter to `get_next_goal()`
3. Implement per-topic follow-up limit enforcement
4. Implement must-ask bypass logic
5. Update docstring with new parameters

**Unit Tests to Add:**
```python
# Test: Optional topic hits follow-up limit
# Test: Must-ask topic bypasses follow-up limit
# Test: Counter-based follow-up decisions
```

### Task 2: Create Session State Utilities (1 hour)

**File:** `session_state_utils.py` (NEW)

**Functions:**
```python
def save_deterministic_state(conversation_id, controller):
    """Save V2 controller state to ActiveConversation"""
    
def load_deterministic_state(conversation_id):
    """Load V2 state from ActiveConversation"""
    
def initialize_deterministic_state(campaign_id, participant_id, business_account_id):
    """Initialize new V2 session state"""
```

---

## Pre-Phase 2 Checklist

- [x] Database schema verified (no migration needed)
- [x] Session storage strategy decided (use survey_data JSON field)
- [ ] Update `deterministic_helpers.py` with follow-up tracking
- [ ] Create `session_state_utils.py` for state persistence
- [ ] Run unit tests to verify helper updates
- [ ] Document session state schema in design doc

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| ActiveConversation table size | Low | JSON fields compress well, auto-cleanup after finalization |
| Multi-worker race conditions | Low | Database-backed storage handles concurrency |
| Backward compatibility | Low | Legacy surveys use conversation_history, V2 uses survey_data |
| Session size limits | Minimal | PostgreSQL TEXT field supports up to 1GB |

---

## Next Steps (Phase 2)

Once Phase 1 tasks complete:
1. Create `ai_conversational_survey_v2.py` controller class
2. Implement LLM stubs with static context
3. Wire up feature flag routing in `routes.py`
4. Integration testing

**Estimated Phase 2 Duration:** 2-3 days

---

## Approval

**Phase 1 Status:** ✅ **APPROVED**

**Blockers:** None

**Proceed to Phase 1 Implementation:** YES
