# Implementation Plan: Optional Parallel Campaigns Feature

**Document Version:** 1.0  
**Date:** October 30, 2025  
**Status:** Design Review - Awaiting Approval  
**Architect Review:** ✅ Approved

---

## Executive Summary

This document outlines the implementation plan for adding optional parallel campaign support to VOÏA's multi-tenant system. The feature will allow platform administrators to enable select business accounts to run multiple active campaigns simultaneously, while maintaining the default single-active-campaign behavior for all other accounts.

**Key Objectives:**
- Add platform-admin controlled toggle for parallel campaigns
- Default to single-active campaign (backward compatible)
- Full audit trail for all setting changes
- Zero disruption to existing business accounts
- Maintain license limit enforcement (Bug #2 fix compatible)

---

## Requirements Summary

### Functional Requirements
1. **FR-1**: Platform admins can enable/disable parallel campaigns per business account
2. **FR-2**: Setting accessible only through licensing management module
3. **FR-3**: Default behavior: Single active campaign enforced (allow_parallel_campaigns = False)
4. **FR-4**: All existing business accounts default to False (no parallel campaigns)
5. **FR-5**: Full audit trail for all changes to parallel campaign setting
6. **FR-6**: Campaign activation respects the per-account setting
7. **FR-7**: Clear UI indication of setting status

### Non-Functional Requirements
1. **NFR-1**: No breaking changes for existing business accounts
2. **NFR-2**: Race condition protection during concurrent activations
3. **NFR-3**: Rollback capability within 5 minutes
4. **NFR-4**: Performance: No measurable impact on campaign activation (<50ms overhead)
5. **NFR-5**: Security: Platform-admin only access to toggle

---

## Technical Design

### 1. Data Model Changes

#### BusinessAccount Model Extension
```python
# Add to models.py - BusinessAccount class
allow_parallel_campaigns = db.Column(
    db.Boolean, 
    nullable=False, 
    default=False,
    index=True,
    comment='Allow multiple active campaigns simultaneously (platform-admin setting only)'
)
```

**Rationale:**
- Placed on BusinessAccount (not LicenseHistory) because it's an operational setting, not license-tier feature
- Non-nullable with explicit default ensures data consistency
- Indexed for efficient queries during campaign activation
- Comment documents purpose and access control

#### Database Migration Strategy
```python
# Alembic migration: add_parallel_campaigns_setting.py

def upgrade():
    # Add column with default False
    op.add_column('business_accounts', 
        sa.Column('allow_parallel_campaigns', sa.Boolean(), 
                  nullable=False, server_default='false'))
    
    # Create index for performance
    op.create_index('idx_business_account_parallel_campaigns', 
                   'business_accounts', ['allow_parallel_campaigns'])
    
    # Drop existing partial unique index
    op.drop_index('idx_single_active_campaign_per_account', 
                  table_name='campaigns')

def downgrade():
    # Restore partial unique index
    op.execute("""
        CREATE UNIQUE INDEX idx_single_active_campaign_per_account 
        ON campaigns (business_account_id) 
        WHERE status = 'active'
    """)
    
    # Drop index and column
    op.drop_index('idx_business_account_parallel_campaigns', 
                  table_name='business_accounts')
    op.drop_column('business_accounts', 'allow_parallel_campaigns')
```

### 2. Constraint Enforcement Strategy

#### Remove Database Constraint
Current: Partial unique index prevents multiple active campaigns at DB level
```python
# REMOVE from models.py Campaign.__table_args__
db.Index('idx_single_active_campaign_per_account', 
        'business_account_id', 
        unique=True, 
        postgresql_where=db.text("status = 'active'"))
```

#### Replace with Application-Layer Enforcement
**Location:** `license_service.py` - `LicenseService.can_activate_campaign()`

**Logic Flow:**
```python
def can_activate_campaign(business_account_id: int) -> bool:
    # 1. Check platform admin bypass (unchanged)
    # 2. Check license limits (unchanged - Bug #2 fix)
    # 3. NEW: Check parallel campaign setting
    
    business_account = BusinessAccount.query.get(business_account_id)
    
    if not business_account.allow_parallel_campaigns:
        # Enforce single active campaign
        active_count = Campaign.query.filter(
            Campaign.business_account_id == business_account_id,
            Campaign.status == 'active'
        ).count()
        
        if active_count >= 1:
            logger.warning(f"Business account {business_account_id} attempted to activate "
                          f"second campaign while parallel campaigns disabled")
            return False
    
    # If parallel allowed or no active campaigns, check license limits
    return campaigns_used < max_campaigns
```

#### Race Condition Protection
**Issue:** Two concurrent activation requests could both pass validation and create 2 active campaigns

**Solution:** Use `SELECT FOR UPDATE` in campaign activation transaction
```python
# In campaign_routes.py - activate_campaign endpoint
def activate_campaign(campaign_id):
    # Lock business account row during activation check
    business_account = BusinessAccount.query.filter_by(
        id=current_account.id
    ).with_for_update().first()
    
    # Perform validation with locked row
    if not LicenseService.can_activate_campaign(business_account.id):
        db.session.rollback()
        flash('Cannot activate campaign...', 'error')
        return redirect(...)
    
    # Activate campaign
    campaign.status = 'active'
    db.session.commit()
```

### 3. UI Integration

#### Location: Admin Licenses Page
**File:** `templates/business_auth/admin_licenses.html`

**Section:** Business Account License Details Card

**UI Component:**
```html
<!-- Platform Admin Only: Parallel Campaign Setting -->
{% if current_user.is_platform_admin() %}
<div class="license-setting-row mt-4 pt-4" style="border-top: 1px solid #dee2e6;">
    <div class="d-flex justify-content-between align-items-start">
        <div>
            <h6 class="mb-2">
                <i class="fas fa-layer-group text-primary me-2"></i>
                Parallel Campaign Execution
            </h6>
            <p class="text-muted small mb-0">
                <strong>Current Setting:</strong> 
                {% if business_account.allow_parallel_campaigns %}
                    <span class="badge bg-success">Enabled - Multiple active campaigns allowed</span>
                {% else %}
                    <span class="badge bg-secondary">Disabled - Single active campaign enforced (default)</span>
                {% endif %}
            </p>
            <p class="text-muted small mt-2 mb-0">
                When enabled, this account can run multiple campaigns simultaneously (subject to license limits).
                When disabled (default), only one campaign can be active at a time.
            </p>
        </div>
        <div>
            <form method="POST" action="{{ url_for('business_auth.toggle_parallel_campaigns', account_id=business_account.id) }}" 
                  onsubmit="return confirm('Are you sure you want to change the parallel campaign setting? This affects campaign activation rules for this business account.')">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <input type="hidden" name="enable" value="{{ 'false' if business_account.allow_parallel_campaigns else 'true' }}"/>
                <button type="submit" class="btn btn-sm {{ 'btn-warning' if business_account.allow_parallel_campaigns else 'btn-primary' }}">
                    <i class="fas {{ 'fa-ban' if business_account.allow_parallel_campaigns else 'fa-check' }} me-1"></i>
                    {{ 'Disable' if business_account.allow_parallel_campaigns else 'Enable' }}
                </button>
            </form>
        </div>
    </div>
</div>
{% endif %}
```

#### New Route Handler
**File:** `business_auth_routes.py`

```python
@business_auth.route('/admin/toggle-parallel-campaigns/<int:account_id>', methods=['POST'])
@require_platform_admin
def toggle_parallel_campaigns(account_id):
    """
    Platform admin only: Toggle parallel campaign setting for a business account
    Full audit trail logged
    """
    business_account = BusinessAccount.query.get_or_404(account_id)
    
    # Get requested setting
    enable = request.form.get('enable', 'false').lower() == 'true'
    
    # Store old value for audit
    old_value = business_account.allow_parallel_campaigns
    
    # Update setting
    business_account.allow_parallel_campaigns = enable
    
    # Audit trail
    from audit_service import queue_audit_log
    queue_audit_log(
        business_account_id=business_account.id,
        user_id=session.get('business_user_id'),
        event_type='parallel_campaign_setting_changed',
        event_description=f'Parallel campaigns {"enabled" if enable else "disabled"} by platform admin',
        metadata={
            'old_value': old_value,
            'new_value': enable,
            'changed_by': session.get('business_user_email'),
            'account_name': business_account.business_name
        }
    )
    
    db.session.commit()
    
    flash(f'Parallel campaign setting {"enabled" if enable else "disabled"} for {business_account.business_name}', 'success')
    return redirect(url_for('business_auth.admin_licenses', account_id=account_id))
```

### 4. Audit Trail Integration

#### New Event Types
```python
# Add to audit_service.py or models.py - AuditLog event types
EVENT_TYPES = [
    'parallel_campaign_setting_changed',      # Platform admin toggled setting
    'campaign_activation_blocked_parallel',   # Activation blocked due to parallel setting
    # ... existing event types
]
```

#### Logging Points
1. **Setting Changed**: When platform admin toggles the setting
2. **Activation Blocked**: When campaign activation is denied due to parallel setting
3. **Setting Checked**: Optional debug logging during validation

---

## Implementation Plan

### Phase 1: Database Migration & Model Changes (1 day)
**Owner:** Backend Developer  
**Priority:** P0 (Blocking)

**Tasks:**
1. [ ] Create Alembic migration script
   - Add `allow_parallel_campaigns` column (default False)
   - Create index on column
   - Drop existing partial unique index
2. [ ] Update `models.py` - BusinessAccount class
   - Add column definition
   - Update `to_dict()` method to include field
3. [ ] Test migration on development database
   - Verify all existing accounts default to False
   - Verify index created successfully
   - Verify partial unique index removed
4. [ ] Write migration rollback test
   - Test downgrade restores unique index
   - Verify data preservation

**Deliverables:**
- Migration script: `migrations/versions/add_parallel_campaigns_setting.py`
- Updated `models.py`
- Migration test results

**Risks:**
- Migration failure on production database
- Data loss during column addition

**Mitigation:**
- Test on full production database backup
- Use transactional DDL
- Have DBA review migration script
- Perform migration during low-traffic window

---

### Phase 2: Service Layer Updates (1 day)
**Owner:** Backend Developer  
**Priority:** P0 (Blocking)

**Tasks:**
1. [ ] Update `LicenseService.can_activate_campaign()`
   - Add parallel campaign check
   - Add audit logging for blocked activations
   - Add comprehensive docstring
2. [ ] Update campaign activation routes
   - Add `SELECT FOR UPDATE` in transaction
   - Update error messages
   - Add debug logging
3. [ ] Update `LicenseService.get_license_info()`
   - Include `allow_parallel_campaigns` in response
4. [ ] Unit tests for new logic
   - Test with parallel enabled (should allow multiple)
   - Test with parallel disabled (should block at 2nd)
   - Test platform admin bypass
   - Test race condition scenarios

**Deliverables:**
- Updated `license_service.py`
- Updated `campaign_routes.py`
- Unit tests: `test_parallel_campaigns.py`

**Risks:**
- Race conditions during concurrent activations
- Logic errors blocking valid activations
- Performance degradation

**Mitigation:**
- Use database-level locking (`SELECT FOR UPDATE`)
- Comprehensive unit tests
- Load testing with concurrent requests
- Feature flag to disable quickly if issues

---

### Phase 3: UI & Route Implementation (1 day)
**Owner:** Full-Stack Developer  
**Priority:** P1

**Tasks:**
1. [ ] Add UI component to `admin_licenses.html`
   - Toggle button with confirmation
   - Status badge display
   - Clear explanatory text
2. [ ] Implement route handler
   - `toggle_parallel_campaigns()` endpoint
   - Platform admin authentication
   - Audit logging integration
   - CSRF protection
3. [ ] Update license overview page
   - Show current setting status
   - Add info tooltip
4. [ ] UI/UX testing
   - Test as platform admin
   - Test as business admin (should not see)
   - Test confirmation flow
   - Test audit trail generation

**Deliverables:**
- Updated `admin_licenses.html`
- New route in `business_auth_routes.py`
- UI screenshots for review

**Risks:**
- Unauthorized access to toggle
- UI confusion about behavior
- CSRF vulnerabilities

**Mitigation:**
- Double-check `@require_platform_admin` decorator
- Clear UI copy with examples
- Confirmation modal before changes
- CSRF token validation

---

### Phase 4: Audit Trail & Logging (0.5 days)
**Owner:** Backend Developer  
**Priority:** P1

**Tasks:**
1. [ ] Add new event types to audit system
2. [ ] Implement logging in all touchpoints
3. [ ] Create audit log report query
4. [ ] Test audit trail completeness

**Deliverables:**
- Updated `audit_service.py`
- Audit log query documentation

**Risks:**
- Missing audit events
- Performance impact of logging

**Mitigation:**
- Code review checklist for all touchpoints
- Async audit logging (already implemented)
- Performance monitoring

---

### Phase 5: Testing & Quality Assurance (2 days)
**Owner:** QA Team + Backend Developer  
**Priority:** P0 (Blocking)

**Tasks:**
1. [ ] Unit tests
   - LicenseService logic tests
   - Model method tests
   - Route handler tests
2. [ ] Integration tests
   - Campaign activation with parallel disabled
   - Campaign activation with parallel enabled
   - Race condition tests (concurrent activations)
   - Platform admin access control tests
3. [ ] UI tests
   - Toggle functionality
   - Permission checks
   - Visual regression tests
4. [ ] Performance tests
   - Campaign activation latency
   - Database query performance
   - Concurrent user simulation (100 users)
5. [ ] Manual QA testing
   - End-to-end workflow testing
   - Edge case validation
   - Audit trail verification

**Test Cases:**

**TC-1: Default Behavior (Parallel Disabled)**
- Given: Business account with `allow_parallel_campaigns = False`
- When: User tries to activate 2nd campaign while 1st is active
- Then: Activation blocked with clear error message
- And: Audit log created

**TC-2: Parallel Enabled Behavior**
- Given: Business account with `allow_parallel_campaigns = True`
- When: User activates 2nd campaign while 1st is active
- Then: Both campaigns active simultaneously
- And: Both count towards license limit

**TC-3: Race Condition Protection**
- Given: Business account with parallel disabled
- When: Two concurrent activation requests submitted
- Then: Only one succeeds, other blocked
- And: No database constraint violations

**TC-4: Platform Admin Toggle**
- Given: Platform admin viewing business account license page
- When: Admin toggles parallel campaign setting
- Then: Setting updated immediately
- And: Audit log created with admin details

**TC-5: License Limit Interaction**
- Given: Business account with 4 campaign limit and parallel enabled
- When: User has 4 active campaigns
- Then: Cannot activate 5th campaign (license limit)
- And: Clear error message about license limit

**Deliverables:**
- Test suite: `test_parallel_campaigns.py`
- Integration test results
- Performance test report
- QA sign-off

**Risks:**
- Incomplete test coverage
- Missed edge cases
- Performance regressions

**Mitigation:**
- Code coverage requirement: >90%
- Peer review of test cases
- Load testing with production-like data
- Performance baseline comparison

---

### Phase 6: Documentation & Deployment (1 day)
**Owner:** Technical Writer + DevOps  
**Priority:** P1

**Tasks:**
1. [ ] Update technical documentation
   - Architecture docs
   - Database schema docs
   - API documentation
2. [ ] Update user-facing documentation
   - Platform admin guide
   - Feature explanation
3. [ ] Create deployment runbook
   - Pre-deployment checklist
   - Migration steps
   - Rollback procedure
   - Monitoring checklist
4. [ ] Update replit.md
   - Document new feature
   - Update architecture section
5. [ ] Prepare deployment package
   - Migration scripts
   - Code changes
   - Rollback scripts

**Deliverables:**
- Updated documentation
- Deployment runbook
- Updated `replit.md`

**Risks:**
- Incomplete documentation
- Unclear rollback procedure

**Mitigation:**
- Peer review of documentation
- Practice rollback on staging
- Deploy during low-traffic window

---

## Risk Assessment & Mitigation

### Critical Risks (P0)

#### RISK-1: Race Condition During Concurrent Activations
**Likelihood:** Medium  
**Impact:** High (data integrity violation)

**Description:**
Two simultaneous activation requests could both pass the "active campaign count" check before either commits, resulting in 2 active campaigns when parallel is disabled.

**Mitigation Strategy:**
1. **Primary:** Use `SELECT FOR UPDATE` to lock BusinessAccount row during activation transaction
2. **Secondary:** Add application-level mutex/semaphore for campaign activations
3. **Detection:** Monitor for constraint violations in error logs
4. **Testing:** Concurrent activation stress tests with 10+ simultaneous requests

**Residual Risk:** Low (with locking implemented)

---

#### RISK-2: Database Migration Failure
**Likelihood:** Low  
**Impact:** Critical (system downtime)

**Description:**
Migration could fail on production database due to lock contention, timeout, or unexpected schema state.

**Mitigation Strategy:**
1. **Prevention:**
   - Test on full production backup
   - Review migration with DBA
   - Use transactional DDL
   - Schedule during low-traffic window (3-5 AM)
2. **Detection:**
   - Pre-migration health checks
   - Real-time migration monitoring
3. **Recovery:**
   - Immediate rollback capability
   - Database backup before migration
   - Tested downgrade script

**Residual Risk:** Very Low

---

#### RISK-3: Unauthorized Access to Toggle
**Likelihood:** Low  
**Impact:** High (security breach)

**Description:**
Non-platform-admin users could access toggle endpoint and modify settings for any business account.

**Mitigation Strategy:**
1. **Prevention:**
   - `@require_platform_admin` decorator on all routes
   - CSRF token validation
   - Input validation (account_id)
   - Session validation
2. **Detection:**
   - Audit logs for all setting changes
   - Monitoring for unauthorized access attempts
3. **Testing:**
   - Penetration testing
   - Access control unit tests

**Residual Risk:** Very Low

---

### High Risks (P1)

#### RISK-4: Logic Error Blocking Valid Activations
**Likelihood:** Medium  
**Impact:** High (business impact)

**Description:**
Bug in validation logic could incorrectly block legitimate campaign activations.

**Mitigation Strategy:**
1. **Prevention:**
   - Comprehensive unit tests
   - Code review by 2+ developers
   - Integration tests with real scenarios
2. **Detection:**
   - User error reporting
   - Monitoring activation success rates
   - Debug logging for all validations
3. **Recovery:**
   - Quick hotfix capability
   - Platform admin override capability
   - Clear error messages for debugging

**Residual Risk:** Low

---

#### RISK-5: Performance Degradation
**Likelihood:** Low  
**Impact:** Medium (user experience)

**Description:**
Additional database queries and locking could slow down campaign activation.

**Mitigation Strategy:**
1. **Prevention:**
   - Index on `allow_parallel_campaigns`
   - Efficient query design
   - Use of SELECT FOR UPDATE only when needed
2. **Detection:**
   - Performance monitoring (APM)
   - Latency alerts
   - Load testing
3. **Acceptance Criteria:**
   - Campaign activation < 500ms (95th percentile)
   - No more than 50ms overhead from new checks

**Residual Risk:** Very Low

---

### Medium Risks (P2)

#### RISK-6: Audit Trail Gaps
**Likelihood:** Low  
**Impact:** Medium (compliance)

**Description:**
Missing or incomplete audit logs for setting changes.

**Mitigation Strategy:**
1. **Prevention:**
   - Code review checklist
   - Automated tests verify audit creation
   - Centralized audit logging service
2. **Detection:**
   - Audit log completeness reports
   - Regular audit reviews

**Residual Risk:** Very Low

---

#### RISK-7: User Confusion About Feature
**Likelihood:** Medium  
**Impact:** Low (support tickets)

**Description:**
Business account admins confused about why they can't activate 2nd campaign.

**Mitigation Strategy:**
1. **Prevention:**
   - Clear error messages
   - UI explanations
   - Documentation
2. **Detection:**
   - Support ticket tracking
   - User feedback
3. **Response:**
   - Help documentation
   - Platform admin communication

**Residual Risk:** Low

---

## Testing Strategy

### Unit Tests (Target: >90% Coverage)

**File:** `test_parallel_campaigns_unit.py`

```python
class TestParallelCampaignsUnit:
    def test_default_value_false(self):
        """New business accounts default to parallel disabled"""
        
    def test_can_activate_with_parallel_enabled(self):
        """Multiple active campaigns allowed when enabled"""
        
    def test_cannot_activate_with_parallel_disabled(self):
        """Second active campaign blocked when disabled"""
        
    def test_platform_admin_bypass(self):
        """Platform admins bypass parallel restriction"""
        
    def test_toggle_creates_audit_log(self):
        """Setting change creates audit trail"""
        
    def test_license_limit_still_enforced(self):
        """Parallel enabled still respects license limits"""
```

### Integration Tests

**File:** `test_parallel_campaigns_integration.py`

```python
class TestParallelCampaignsIntegration:
    def test_campaign_activation_flow_parallel_disabled(self):
        """End-to-end: Activate campaign with parallel disabled"""
        
    def test_campaign_activation_flow_parallel_enabled(self):
        """End-to-end: Activate multiple campaigns with parallel enabled"""
        
    def test_concurrent_activation_race_condition(self):
        """Concurrent activations handled correctly"""
        
    def test_toggle_endpoint_platform_admin(self):
        """Platform admin can toggle setting"""
        
    def test_toggle_endpoint_non_admin_denied(self):
        """Non-platform-admin cannot access toggle"""
```

### Load Tests

**Tool:** Locust or Apache JMeter

**Scenarios:**
1. 100 concurrent users activating campaigns
2. 50 concurrent toggle operations
3. Mixed load (activations + toggles + normal traffic)

**Success Criteria:**
- 95th percentile latency < 500ms
- Zero database deadlocks
- Zero constraint violations
- Correct behavior under load

### Manual QA Checklist

- [ ] Platform admin can see toggle
- [ ] Business admin cannot see toggle
- [ ] Toggle works (enable → disable → enable)
- [ ] Audit logs created for all changes
- [ ] Campaign activation blocked correctly
- [ ] Error messages clear and actionable
- [ ] UI responsive and intuitive
- [ ] Migration completes successfully
- [ ] Rollback works correctly
- [ ] Documentation accurate

---

## Rollback Plan

### Immediate Rollback (<5 minutes)

**Trigger Conditions:**
- Critical bug blocking campaign activations
- Data integrity violations
- Performance degradation >200ms
- Security vulnerability discovered

**Rollback Steps:**

1. **Stop Feature Use (Immediate)**
   ```python
   # Add feature flag to license_service.py
   PARALLEL_CAMPAIGNS_ENABLED = os.environ.get('PARALLEL_CAMPAIGNS_ENABLED', 'false') == 'true'
   
   def can_activate_campaign(business_account_id: int) -> bool:
       if not PARALLEL_CAMPAIGNS_ENABLED:
           # Fallback to legacy behavior
           return legacy_single_active_check(business_account_id)
       # New logic...
   ```
   
   Set environment variable: `PARALLEL_CAMPAIGNS_ENABLED=false`
   
   Restart application

2. **Database Rollback (If Needed, 15 minutes)**
   ```bash
   # Run downgrade migration
   alembic downgrade -1
   ```
   
   This will:
   - Restore partial unique index
   - Remove `allow_parallel_campaigns` column
   - Revert to original schema

3. **Verification**
   - Test campaign activation
   - Verify single-active enforcement
   - Check application logs
   - Monitor error rates

**Data Preservation:**
- Audit logs retained
- Campaign data unaffected
- Business account data preserved

### Partial Rollback (Keep DB Changes, Disable Feature)

If only application logic has issues:
1. Set feature flag to false
2. Keep database schema changes
3. Fix bugs and redeploy

---

## Timeline & Effort Estimates

### Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Database Migration | 1 day | None |
| Phase 2: Service Layer | 1 day | Phase 1 |
| Phase 3: UI Implementation | 1 day | Phase 2 |
| Phase 4: Audit Trail | 0.5 days | Phase 3 |
| Phase 5: Testing | 2 days | Phase 4 |
| Phase 6: Documentation | 1 day | Phase 5 |
| **Total** | **6.5 days** | Sequential |

### Detailed Timeline (Example)

**Week 1:**
- Day 1-2: Database migration + service layer
- Day 3: UI implementation
- Day 4: Audit trail + start testing
- Day 5: Complete testing

**Week 2:**
- Day 1: Documentation + deployment prep
- Day 2: Deploy to staging
- Day 3: Staging validation
- Day 4: Production deployment
- Day 5: Post-deployment monitoring

**Total Calendar Time:** ~2 weeks (10 business days including buffer)

---

## Success Criteria

### Go-Live Criteria (Must Pass All)

- [ ] All unit tests passing (>90% coverage)
- [ ] All integration tests passing
- [ ] Load tests passing (100 concurrent users)
- [ ] Security review completed
- [ ] Code review approved by 2+ developers
- [ ] Architect review approved
- [ ] Migration tested on production backup
- [ ] Rollback tested successfully
- [ ] Documentation complete
- [ ] QA sign-off obtained

### Post-Deployment Success Metrics

**Week 1:**
- Zero critical bugs
- Zero data integrity issues
- Campaign activation latency <500ms (95th)
- <5 support tickets related to feature

**Week 2-4:**
- Platform admin adoption >50%
- Zero unauthorized access attempts
- Complete audit trail for all changes
- User satisfaction score >4/5

---

## Monitoring & Observability

### Metrics to Track

1. **Functional Metrics:**
   - Campaign activations (success/failure rate)
   - Parallel campaign setting changes (count by admin)
   - Active campaigns per account (distribution)

2. **Performance Metrics:**
   - Campaign activation latency (p50, p95, p99)
   - Database query performance
   - Lock contention events

3. **Security Metrics:**
   - Unauthorized access attempts
   - Platform admin actions
   - Audit log completeness

4. **Business Metrics:**
   - % of accounts with parallel enabled
   - Average active campaigns per account
   - Feature usage trends

### Alerting Thresholds

- **Critical:** Campaign activation failure rate >5%
- **Warning:** Campaign activation latency p95 >500ms
- **Info:** Platform admin changes setting

### Dashboards

1. **Feature Health Dashboard:**
   - Activation success rate
   - Performance metrics
   - Error rates

2. **Audit Dashboard:**
   - Setting changes over time
   - Admin activity
   - Blocked activations

---

## Appendix A: Database Schema Comparison

### Before (Current State)

```sql
-- campaigns table
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    business_account_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- ... other columns
);

CREATE UNIQUE INDEX idx_single_active_campaign_per_account 
ON campaigns (business_account_id) 
WHERE status = 'active';
```

### After (Proposed State)

```sql
-- business_accounts table
CREATE TABLE business_accounts (
    id SERIAL PRIMARY KEY,
    allow_parallel_campaigns BOOLEAN NOT NULL DEFAULT FALSE,
    -- ... other columns
);

CREATE INDEX idx_business_account_parallel_campaigns 
ON business_accounts (allow_parallel_campaigns);

-- campaigns table
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    business_account_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    -- ... other columns
);

-- NO unique index on campaigns
```

---

## Appendix B: Audit Event Schema

### Event Type: `parallel_campaign_setting_changed`

```json
{
    "event_type": "parallel_campaign_setting_changed",
    "business_account_id": 123,
    "user_id": 456,
    "timestamp": "2025-10-30T14:30:00Z",
    "event_description": "Parallel campaigns enabled by platform admin",
    "metadata": {
        "old_value": false,
        "new_value": true,
        "changed_by": "admin@platform.com",
        "account_name": "Acme Corporation",
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0..."
    }
}
```

### Event Type: `campaign_activation_blocked_parallel`

```json
{
    "event_type": "campaign_activation_blocked_parallel",
    "business_account_id": 123,
    "user_id": 456,
    "timestamp": "2025-10-30T14:35:00Z",
    "event_description": "Campaign activation blocked - parallel campaigns disabled",
    "metadata": {
        "campaign_id": 789,
        "campaign_name": "Q4 2025 Survey",
        "existing_active_campaigns": 1,
        "existing_campaign_names": ["Q3 2025 Survey"],
        "allow_parallel_campaigns": false
    }
}
```

---

## Appendix C: Error Messages

### Campaign Activation Blocked

**User-Facing Message:**
```
Cannot activate campaign. Your account is configured to allow only one active 
campaign at a time. Please complete or end your current active campaign 
"[Campaign Name]" before activating this one.

If you need to run multiple campaigns simultaneously, please contact your 
platform administrator.
```

**Admin-Facing Message (in logs):**
```
Campaign activation blocked for business_account_id=123, campaign_id=789. 
Parallel campaigns disabled (allow_parallel_campaigns=false). 
Existing active campaigns: 1 (IDs: [456])
```

---

## Sign-Off

### Required Approvals

- [ ] **Solution Architect:** Design review approved
- [ ] **Technical Lead:** Implementation plan approved
- [ ] **Security Team:** Security review approved
- [ ] **Product Owner:** Business requirements approved
- [ ] **DevOps Lead:** Deployment plan approved

### Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-10-30 | AI Agent + Architect | Initial draft |

---

**End of Implementation Plan**
