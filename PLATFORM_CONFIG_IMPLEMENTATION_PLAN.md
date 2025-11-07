# Platform Admin Configuration Layer - Implementation Plan

**Date:** November 7, 2025  
**Purpose:** Enable Platform Admin to configure global fallback defaults for conversational AI survey system  
**Current State:** ~40+ hardcoded values scattered across `ai_conversational_survey.py` and related files  
**Target State:** Centralized, database-driven configuration with admin UI and proper fallback chain

---

## Executive Summary

### Problem
The conversational AI survey system has operational parameters (minimum questions, retry limits, AI model settings) hardcoded throughout the codebase. This prevents Platform Admins from:
- Controlling system-wide behavior without code deployments
- Managing AI costs through token/temperature adjustments
- Tuning UX parameters based on user feedback
- Providing global fallbacks for business accounts and campaigns

### Solution
Implement a three-tier configuration architecture:
```
Campaign Settings → Business Account Settings → Platform Admin Defaults → Hardcoded Fallbacks
```

### Effort Estimate
- **Option 1 (Pilot):** 12-16 hours (1.5-2 days)
- **Option 2 (Phased):** 26-40 hours (3-5 days)
- **Option 3 (Full):** 32-48 hours (4-6 days)

### Risk Level
**LOW-MEDIUM** with phased approach and feature flags

---

## Implementation Options

## Option 1: Pilot Implementation (AI Parameters Only)

### Scope
Focus on **AI model parameters** as proof-of-concept:
- Extraction model settings (max_tokens, temperature)
- Question generation settings (max_tokens, temperature)
- Model selection (gpt-4o vs gpt-4o-mini)

### Why Start Here?
✅ **Highest business value** - Direct cost control  
✅ **Lowest risk** - Only 4-6 integration points  
✅ **Fast validation** - Proves architecture works  
✅ **Easy rollback** - Feature flag toggle  

### Effort: 12-16 hours (1.5-2 days)

#### Phase 1A: Foundation (4 hours)
- Create `platform_config` table
- Build `PlatformConfigService` base class
- Seed AI parameter defaults
- Add unit tests

#### Phase 1B: Integration (4-6 hours)
- Refactor `ai_conversational_survey.py` (lines 266-273, 873-880)
- Add config lookups with caching
- Comprehensive testing (AI calls, cost validation)
- Feature flag implementation

#### Phase 1C: Admin UI (4-6 hours)
- Simple config page: `/business/admin/platform-config`
- AI Parameters section only
- Validation (max_tokens: 100-1000, temperature: 0.0-1.0)
- Save/Reset functionality

### Configuration Keys (Pilot)
```python
{
    'ai_extraction_model': 'gpt-4o',
    'ai_extraction_max_tokens': 400,
    'ai_extraction_temperature': 0.3,
    'ai_question_gen_model': 'gpt-4o',
    'ai_question_gen_max_tokens': 300,
    'ai_question_gen_temperature': 0.8
}
```

### Success Criteria
- [ ] Platform Admin can change AI parameters via UI
- [ ] Changes apply to new surveys immediately
- [ ] Existing surveys continue working
- [ ] No performance degradation (<5ms config lookups)
- [ ] Cost reduction validated (if lower tokens/mini model used)

### Risks
🟢 **LOW** - Minimal integration points, easy rollback

---

## Option 2: Phased Rollout (Recommended)

### Scope
Full implementation across **3 deployment phases**:

**Phase 1:** AI Parameters (Option 1)  
**Phase 2:** Operational Parameters (retry, limits, thresholds)  
**Phase 3:** UX Parameters (frustration detection, history windows)

### Why This Approach?
✅ **Risk mitigation** - Validate each phase before proceeding  
✅ **Incremental value** - Immediate benefits from Phase 1  
✅ **Feedback loops** - Platform Admin can test and provide input  
✅ **Rollback safety** - Can halt at any phase  

### Effort: 26-40 hours (3-5 days)

#### Phase 2A: Operational Parameters (8-12 hours)
**New Configuration Keys:**
```python
{
    'min_questions_minimal_core': 5,
    'nps_retry_limit': 2,
    'nps_deferred_min_steps': 2,
    'nps_extraction_step_limit': 3,
    'early_survey_threshold': 4
}
```

**Integration Points:**
- `_check_completion_criteria()` - lines 644-676
- `_generate_next_question()` - lines 770-786
- `_extract_survey_data_fallback()` - line 332, 499

**UI Enhancement:**
- Add "Completion Criteria" section to admin UI
- Add "Retry Logic" section
- Validation rules for each parameter

**Testing Requirements:**
- Survey completion with various min_questions values
- NPS retry behavior validation
- Edge cases (0, negative, very large values)

#### Phase 2B: UX Parameters (6-10 hours)
**New Configuration Keys:**
```python
{
    'conversation_history_window': 6,
    'frustration_detection_window': 3,
    'short_response_threshold': 5,
    'long_response_threshold': 20,
    'frustration_keywords': [
        'repeating', 'repeat', 'over and over', 'again',
        'already told you', 'already answered', ...
    ]
}
```

**Integration Points:**
- `_detect_frustration()` - lines 688-718
- `_generate_next_question()` - line 908

**UI Enhancement:**
- Add "User Experience" section
- Text area for frustration keywords (comma-separated)
- Helper text with examples

**Testing Requirements:**
- Frustration detection with custom keywords
- History window adjustments
- Response threshold validation

### Success Criteria (All Phases)
- [ ] All ~40 hardcoded values are configurable
- [ ] Admin UI is intuitive and well-documented
- [ ] Zero regressions in survey behavior
- [ ] Performance benchmarks met (<5ms config lookups)
- [ ] Comprehensive test coverage (>80%)

### Risks
🟡 **LOW-MEDIUM** - More integration points, requires thorough testing

---

## Option 3: Full Implementation (Single Deployment)

### Scope
Implement entire configuration layer in one release cycle.

### Why Consider This?
✅ **Faster total completion** - No deployment overhead between phases  
✅ **Holistic testing** - All interactions tested together  
✅ **Single migration** - One-time database change  

⚠️ **Higher risk** - Larger changeset, more test cases  
⚠️ **Longer feedback loop** - No intermediate validation  

### Effort: 32-48 hours (4-6 days)

Includes all work from Options 1 & 2, plus:

#### Additional Work (6-8 hours)
- Comprehensive documentation
- Migration script for existing surveys
- Performance benchmarking suite
- Admin training materials
- Rollback procedures

### Success Criteria
Same as Option 2, plus:
- [ ] Complete admin documentation published
- [ ] Migration playbook validated
- [ ] Performance baseline documented

### Risks
🟡 **MEDIUM** - Larger blast radius, requires extended testing period

---

## Technical Implementation Details

### Database Schema

```python
class PlatformConfig(db.Model):
    """Platform-wide configuration defaults for AI survey system"""
    __tablename__ = 'platform_config'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    config_value = db.Column(db.JSON, nullable=False)
    config_type = db.Column(db.String(50), nullable=False)  # 'integer', 'float', 'string', 'json_array'
    category = db.Column(db.String(50))  # 'ai_parameters', 'operational', 'ux'
    description = db.Column(db.Text)
    min_value = db.Column(db.Float, nullable=True)  # For validation
    max_value = db.Column(db.Float, nullable=True)  # For validation
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationship for audit trail
    updated_by_user = db.relationship('User', backref='config_updates')
```

**Indexes:**
- `config_key` (unique, primary lookup)
- `category` (for UI grouping)

**Estimated Size:** <100 rows, negligible storage impact

---

### Configuration Service

```python
class PlatformConfigService:
    """
    Singleton service for platform configuration management.
    Implements caching and fallback chain.
    """
    
    _instance = None
    _config_cache = {}
    _cache_timestamp = None
    CACHE_TTL_SECONDS = 300  # 5 minutes
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with caching.
        
        Lookup order:
        1. In-memory cache (if fresh)
        2. Database
        3. Provided default
        4. Hardcoded fallback
        """
        # Check cache freshness
        if self._cache_timestamp and (datetime.utcnow() - self._cache_timestamp).seconds < self.CACHE_TTL_SECONDS:
            if key in self._config_cache:
                return self._config_cache[key]
        
        # Query database
        config = PlatformConfig.query.filter_by(config_key=key).first()
        if config:
            self._config_cache[key] = config.config_value
            self._cache_timestamp = datetime.utcnow()
            return config.config_value
        
        # Fallback to default
        return default if default is not None else self._get_hardcoded_default(key)
    
    def set_config(self, key: str, value: Any, user_id: int = None) -> bool:
        """Update configuration value and invalidate cache"""
        config = PlatformConfig.query.filter_by(config_key=key).first()
        
        if config:
            config.config_value = value
            config.updated_at = datetime.utcnow()
            config.updated_by = user_id
        else:
            config = PlatformConfig(
                config_key=key,
                config_value=value,
                updated_by=user_id
            )
            db.session.add(config)
        
        db.session.commit()
        self.invalidate_cache()
        return True
    
    def invalidate_cache(self):
        """Clear cache after config updates"""
        self._config_cache = {}
        self._cache_timestamp = None
    
    def _get_hardcoded_default(self, key: str) -> Any:
        """Hardcoded fallbacks (last resort)"""
        DEFAULTS = {
            # AI Parameters
            'ai_extraction_model': 'gpt-4o',
            'ai_extraction_max_tokens': 400,
            'ai_extraction_temperature': 0.3,
            'ai_question_gen_model': 'gpt-4o',
            'ai_question_gen_max_tokens': 300,
            'ai_question_gen_temperature': 0.8,
            
            # Operational Parameters
            'min_questions_minimal_core': 5,
            'nps_retry_limit': 2,
            'nps_deferred_min_steps': 2,
            'nps_extraction_step_limit': 3,
            'early_survey_threshold': 4,
            
            # UX Parameters
            'conversation_history_window': 6,
            'frustration_detection_window': 3,
            'short_response_threshold': 5,
            'long_response_threshold': 20,
            'frustration_keywords': [
                'repeating', 'repeat', 'over and over', 'again',
                'already told you', 'already answered', 'already said',
                'done', 'enough', 'stop', 'frustrated', 'annoying',
                'irritating', 'waste of time', 'same question',
                'asked this already', 'keep asking', 'how many times',
                'told you already', 'finished', 'complete'
            ]
        }
        return DEFAULTS.get(key)
```

**Performance Target:** <5ms cache hits, <20ms cache misses

---

### Integration Example (AIConversationalSurvey)

**BEFORE:**
```python
elif has_minimal_core and self.step_count >= 5:  # Hardcoded
    return True
```

**AFTER:**
```python
from platform_config_service import PlatformConfigService

class AIConversationalSurvey:
    def __init__(self, ...):
        self.config_service = PlatformConfigService()
        # ... rest of init
    
    def _check_completion_criteria(self):
        min_questions = self.config_service.get_config('min_questions_minimal_core', 5)
        
        if has_minimal_core and self.step_count >= min_questions:
            return True
```

**Pattern Applies To:**
- All ~40 hardcoded values
- Single config service instance (singleton)
- Consistent fallback behavior

---

### Admin UI Structure

```
/business/admin/platform-config
│
├── AI Parameters Section
│   ├── Model Selection (dropdown: gpt-4o, gpt-4o-mini)
│   ├── Extraction Max Tokens (slider: 100-1000)
│   ├── Extraction Temperature (slider: 0.0-1.0)
│   ├── Question Gen Max Tokens (slider: 100-1000)
│   └── Question Gen Temperature (slider: 0.0-1.0)
│
├── Completion Criteria Section
│   ├── Minimum Questions (input: 1-20)
│   ├── NPS Retry Limit (input: 0-5)
│   ├── NPS Deferred Min Steps (input: 1-10)
│   └── Early Survey Threshold (input: 1-10)
│
└── User Experience Section
    ├── Conversation History Window (input: 1-20)
    ├── Frustration Detection Window (input: 1-10)
    ├── Short Response Threshold (input: 1-50 chars)
    ├── Long Response Threshold (input: 10-200 chars)
    └── Frustration Keywords (textarea, comma-separated)
```

**Features:**
- Real-time validation
- Reset to defaults button (per section)
- Last updated timestamp + username
- Help tooltips for each parameter
- Preview of current values vs defaults
- Save confirmation with change summary

**Access Control:**
- Platform Admin only (check `is_platform_admin` flag)
- Audit log entry on every change
- Flash messages for success/errors

---

### Migration Strategy

#### Step 1: Create Table + Seed Data
```python
def upgrade():
    # Create table
    op.create_table(
        'platform_config',
        # ... columns
    )
    
    # Seed with current hardcoded values
    from platform_config_service import PlatformConfigService
    config_service = PlatformConfigService()
    
    defaults = {
        'ai_extraction_model': 'gpt-4o',
        'ai_extraction_max_tokens': 400,
        # ... all defaults
    }
    
    for key, value in defaults.items():
        config_service.set_config(key, value, user_id=None)
```

#### Step 2: Deploy Code (Feature Flag OFF)
- Code deployed but not active
- Verify no regressions
- Monitor for 24 hours

#### Step 3: Enable Feature Flag
```python
ENABLE_PLATFORM_CONFIG = os.environ.get('ENABLE_PLATFORM_CONFIG', 'false').lower() == 'true'
```

#### Step 4: Gradual Rollout
- Enable for internal testing campaigns first
- Monitor AI costs, survey completion rates
- Enable globally after validation

---

## Testing Strategy

### Unit Tests
```python
# test_platform_config_service.py
def test_get_config_from_cache():
    # Test cache hit performance (<5ms)
    
def test_get_config_from_db():
    # Test DB fallback
    
def test_get_config_hardcoded_default():
    # Test final fallback
    
def test_set_config_invalidates_cache():
    # Test cache invalidation
```

### Integration Tests
```python
# test_ai_conversational_survey_config.py
def test_survey_respects_min_questions_config():
    # Create survey with custom min_questions
    # Verify completion behavior
    
def test_survey_respects_ai_parameter_config():
    # Mock OpenAI API
    # Verify correct model/tokens/temperature used
    
def test_survey_fallback_to_defaults():
    # Delete config entries
    # Verify hardcoded defaults used
```

### Performance Tests
```python
def test_config_lookup_performance():
    # Benchmark 1000 config lookups
    # Assert <5ms average for cache hits
    # Assert <20ms average for cache misses
```

### E2E Tests
- Complete survey flow with default configs
- Complete survey flow with custom configs
- Admin UI CRUD operations
- Config changes apply to new surveys

---

## Rollback Plan

### Feature Flag Rollback
```python
# Set environment variable:
ENABLE_PLATFORM_CONFIG=false

# System reverts to hardcoded values immediately
```

### Database Rollback
```sql
-- Drop table if needed (non-destructive):
DROP TABLE IF EXISTS platform_config;
```

### Code Rollback
```bash
# Git revert to previous version
git revert <commit-hash>
```

**Recovery Time:** <5 minutes (feature flag toggle)

---

## Monitoring & Observability

### Metrics to Track
```python
# Add to Sentry/logging:
- config_lookup_time_ms (histogram)
- config_cache_hit_rate (gauge)
- config_update_count (counter)
- ai_token_usage_per_survey (histogram)
- survey_completion_rate (gauge)
```

### Alerts
- Config lookup time >50ms (95th percentile)
- Cache hit rate <90%
- Unexpected config changes (non-admin users)
- Survey completion rate drops >10%

### Dashboards
- AI cost trends (before/after config changes)
- Survey completion metrics by config version
- Config change audit log

---

## Cost/Benefit Analysis

### Costs
**Development:** 12-48 hours (depending on option)  
**Testing:** 6-10 hours  
**Documentation:** 2-4 hours  
**Total:** 20-62 hours (2.5-7.5 days)

### Benefits
**Cost Control:**
- Platform Admin can reduce AI costs 30-50% by adjusting tokens/model
- Estimated savings: $500-2000/month (based on survey volume)

**Flexibility:**
- No code deployments needed for parameter tuning
- A/B testing different configurations
- Rapid response to user feedback

**Operational Efficiency:**
- Centralized configuration management
- Audit trail for all changes
- Reduced support tickets (admins can self-serve)

**ROI:** Positive within 1-2 months (cost savings alone)

---

## Recommendation

### Recommended: **Option 2 (Phased Rollout)**

**Rationale:**
1. **Lowest risk** - Incremental validation at each phase
2. **Fastest time-to-value** - AI cost control in Phase 1 (1.5-2 days)
3. **Feedback loops** - Platform Admin can guide later phases
4. **Rollback safety** - Can pause at any phase
5. **Best practices** - Industry standard for infrastructure changes

**Timeline:**
- **Week 1:** Phase 1 (AI Parameters) - Deploy & validate
- **Week 2:** Phase 2A (Operational Parameters) - Deploy & validate
- **Week 3:** Phase 2B (UX Parameters) - Deploy & validate
- **Week 4:** Documentation & training

**Success Criteria Before Proceeding:**
- Zero regressions in survey behavior
- Platform Admin satisfaction with UI
- Performance benchmarks met
- No increase in support tickets

---

## Next Steps

1. **Review this plan** - Confirm Option 2 is acceptable
2. **Assign priority** - When to start implementation?
3. **Platform Admin involvement** - Who will test/validate?
4. **Success metrics** - Define KPIs for each phase
5. **Communication plan** - How to notify business accounts?

---

## Appendix: Complete Configuration Catalog

### AI Parameters (6 configs)
| Key | Default | Type | Range | Description |
|-----|---------|------|-------|-------------|
| ai_extraction_model | gpt-4o | string | gpt-4o, gpt-4o-mini | Model for data extraction |
| ai_extraction_max_tokens | 400 | integer | 100-1000 | Max tokens for extraction |
| ai_extraction_temperature | 0.3 | float | 0.0-1.0 | Temperature for extraction |
| ai_question_gen_model | gpt-4o | string | gpt-4o, gpt-4o-mini | Model for question generation |
| ai_question_gen_max_tokens | 300 | integer | 100-1000 | Max tokens for questions |
| ai_question_gen_temperature | 0.8 | float | 0.0-1.0 | Temperature for questions |

### Operational Parameters (5 configs)
| Key | Default | Type | Range | Description |
|-----|---------|------|-------|-------------|
| min_questions_minimal_core | 5 | integer | 1-20 | Minimum questions before completion |
| nps_retry_limit | 2 | integer | 0-5 | Max NPS retry attempts |
| nps_deferred_min_steps | 2 | integer | 1-10 | Min steps before NPS deferral |
| nps_extraction_step_limit | 3 | integer | 1-10 | Max step for NPS extraction |
| early_survey_threshold | 4 | integer | 1-10 | Threshold for early rating detection |

### UX Parameters (5 configs)
| Key | Default | Type | Range | Description |
|-----|---------|------|-------|-------------|
| conversation_history_window | 6 | integer | 1-20 | Messages in AI context |
| frustration_detection_window | 3 | integer | 1-10 | Messages for frustration check |
| short_response_threshold | 5 | integer | 1-50 | Chars for short response |
| long_response_threshold | 20 | integer | 10-200 | Chars for long response |
| frustration_keywords | [array] | json_array | - | Keywords triggering frustration |

**Total:** 16 configuration parameters  
**Industry Standards (NOT configurable):** NPS scale (0-10), NPS thresholds (9, 7), Rating scale (1-5)

---

**Document Version:** 1.0  
**Last Updated:** November 7, 2025  
**Author:** AI Development Team  
**Status:** Awaiting Review
