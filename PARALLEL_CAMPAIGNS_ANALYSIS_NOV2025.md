# Concurrent Campaigns Feature - Analysis & Implementation Plan
**Document Version:** 2.0  
**Date:** November 24, 2025  
**Status:** Ready for Implementation  
**Architect Review:** ✅ Approved with Updated Risk Matrix

---

## Executive Summary

This document provides an updated analysis for implementing concurrent (parallel) campaigns in VOÏA, allowing business accounts to run multiple active campaigns simultaneously within their license limits. The feature is controlled by platform administrators via a toggle during business account creation.

**Key Findings:**
- ✅ **Original Plan (Oct 30, 2025) Remains Valid**: The technical architecture is sound and aligned with current codebase
- ⚠️ **Implementation Status**: NOT IMPLEMENTED - Database schema changes and application logic still pending
- 📊 **Complexity Score**: **7/10** (Multi-layer changes across database, services, UI, and testing)
- 🎯 **Recommendation**: Proceed with phased rollout using existing plan with updated risk mitigations

---

## Current State Assessment

### What Exists Today
1. **Single Active Campaign Enforcement**: Database constraint `idx_single_active_campaign_per_account` blocks multiple active campaigns
2. **License System**: Fully implemented with `LicenseService.can_activate_campaign()` enforcing yearly limits
3. **Campaign Scheduler**: Background job in `task_queue.py` with PostgreSQL advisory locking (lock ID: 123456)
4. **Multi-Tenant Isolation**: Robust tenant separation with proper authorization checks
5. **Audit Trail System**: Comprehensive logging infrastructure ready for new events

### What's Missing
1. `BusinessAccount.allow_parallel_campaigns` field (database column)
2. Database trigger to replace partial unique index
3. Application-layer logic to respect the new toggle
4. Platform admin UI to control the setting
5. Audit logging for setting changes
6. Integration tests for concurrent activation scenarios

---

## Updated Risk Assessment Matrix

| Risk ID | Risk Description | Severity | Likelihood | Mitigation Strategy | Status |
|---------|-----------------|----------|------------|---------------------|--------|
| **R1** | **Migration/Trigger Deployment Failure** | HIGH | Low | • Rehearse migration in staging<br>• Full database backup before deployment<br>• Maintenance window with rollback plan<br>• Monitor trigger performance post-deployment | NEW |
| **R2** | **License Limit Drift** | MEDIUM | Medium | • Integration tests for LicenseService with parallel campaigns<br>• Telemetry tracking campaigns_used vs license limits<br>• Automated reconciliation job<br>• Dashboard alerts for limit breaches | NEW |
| **R3** | **Platform Admin UI Misuse** | MEDIUM | Medium | • Confirmation dialog with clear warnings<br>• Comprehensive audit logging<br>• Setting change notifications to business account owners<br>• Quarterly audit reviews | NEW |
| **R4** | **Reporting Dashboard Mismatches** | MEDIUM | Low | • Regression tests for concurrent campaign analytics<br>• Update NPS aggregation logic if needed<br>• Test data segmentation with multiple active campaigns<br>• UI validation for multi-campaign views | NEW |
| **R5** | **Background Job Bypass** | LOW | Very Low | • Database trigger enforces rules at DB level<br>• All scheduler jobs use transactional locking<br>• Code review checklist for campaign activation paths<br>• Automated tests for scheduler edge cases | EXISTING |
| **R6** | **Race Conditions During Activation** | LOW | Medium | • SELECT FOR UPDATE in all activation paths<br>• Database trigger as final safeguard<br>• Load testing with concurrent activations<br>• Advisory lock in scheduler (already exists) | COVERED |
| **R7** | **Campaign Status Taxonomy Drift** | LOW | Low | • Audit current Campaign.status values (active, ready, draft, completed, paused)<br>• Align trigger logic with status taxonomy<br>• Document status transitions<br>• Unit tests for each status | NEW |

**Risk Scoring:**
- **Critical Risks**: 0
- **High Risks**: 1 (R1 - mitigated with proper deployment procedures)
- **Medium Risks**: 3 (R2, R3, R4 - manageable with testing and monitoring)
- **Low Risks**: 3 (R5, R6, R7 - covered by existing architecture)

---

## Technical Architecture Validation

### ✅ Approved Design Elements

#### 1. Three-Layer Enforcement (Defense in Depth)
```
Layer 1: PostgreSQL Trigger (Primary) → Enforces at database level
Layer 2: Application Logic (Secondary) → LicenseService.can_activate_campaign()
Layer 3: Transactional Locking (Race Prevention) → SELECT FOR UPDATE
```
**Architect Verdict**: Sound architecture, prevents bypasses

#### 2. Database Trigger Strategy
**Status**: Validated - replaces partial unique index with conditional logic
```sql
CREATE TRIGGER check_single_active_campaign
    BEFORE INSERT OR UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION enforce_single_active_campaign();
```
**Key Validation**: Trigger checks `NEW.status = 'active'` and queries `allow_parallel_campaigns` flag

#### 3. Campaign Activation Entry Points
**All Identified and Covered:**
1. ✅ Web UI: `campaign_routes.py - activate_campaign()`
2. ✅ Background Scheduler: `task_queue.py - _run_campaign_scheduler()`
3. ✅ Admin Scripts: Documented requirement for SELECT FOR UPDATE
4. ✅ Test Fixtures: Must handle IntegrityError gracefully

#### 4. Platform Admin Control
**Location**: `business_auth_routes.py` + `admin_licenses.html`  
**Access**: Platform admin only (role check enforced)  
**Audit**: Full audit trail with before/after values

---

## Revised Implementation Plan

### Phase 0: Preparation & Validation (1-2 days)
**Objective**: Ensure clean foundation before schema changes

**Tasks:**
- [ ] Audit current `Campaign.status` values in production database
  ```sql
  SELECT DISTINCT status FROM campaigns;
  ```
- [ ] Document current campaign lifecycle state machine
- [ ] Create staging environment migration rehearsal script
- [ ] Backup production database (automated + manual verification)
- [ ] Review all campaign activation code paths for SELECT FOR UPDATE readiness

**Deliverables:**
- Campaign status taxonomy documentation
- Migration rehearsal results from staging
- Code path audit checklist

---

### Phase 1: Database Schema Changes (2-3 days)
**Objective**: Add parallel campaigns toggle and replace constraint

**Tasks:**

#### 1.1: Create Alembic Migration
```python
# migrations/versions/add_parallel_campaigns_support.py
def upgrade():
    # Add new column
    op.add_column('business_accounts', 
        sa.Column('allow_parallel_campaigns', sa.Boolean(), 
                  nullable=False, server_default='false'))
    
    # Create index
    op.create_index('idx_business_account_parallel_campaigns', 
                   'business_accounts', ['allow_parallel_campaigns'])
    
    # Drop existing unique index
    op.drop_index('idx_single_active_campaign_per_account', 
                  table_name='campaigns')
    
    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION enforce_single_active_campaign()
        RETURNS TRIGGER AS $$
        DECLARE
            account_parallel_allowed BOOLEAN;
            existing_active_count INTEGER;
        BEGIN
            IF NEW.status = 'active' AND (TG_OP = 'INSERT' OR OLD.status != 'active') THEN
                SELECT allow_parallel_campaigns INTO account_parallel_allowed
                FROM business_accounts WHERE id = NEW.business_account_id;
                
                IF NOT account_parallel_allowed THEN
                    SELECT COUNT(*) INTO existing_active_count
                    FROM campaigns
                    WHERE business_account_id = NEW.business_account_id
                      AND status = 'active'
                      AND id != NEW.id;
                    
                    IF existing_active_count > 0 THEN
                        RAISE EXCEPTION 
                            'Cannot activate campaign: business_account_id % has parallel campaigns disabled and already has % active campaign(s)',
                            NEW.business_account_id, existing_active_count
                        USING ERRCODE = 'unique_violation';
                    END IF;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER check_single_active_campaign
            BEFORE INSERT OR UPDATE ON campaigns
            FOR EACH ROW
            EXECUTE FUNCTION enforce_single_active_campaign();
    """)

def downgrade():
    # Drop trigger and function
    op.execute("DROP TRIGGER IF EXISTS check_single_active_campaign ON campaigns")
    op.execute("DROP FUNCTION IF EXISTS enforce_single_active_campaign")
    
    # Restore unique index
    op.execute("""
        CREATE UNIQUE INDEX idx_single_active_campaign_per_account 
        ON campaigns (business_account_id) 
        WHERE status = 'active'
    """)
    
    # Remove index and column
    op.drop_index('idx_business_account_parallel_campaigns')
    op.drop_column('business_accounts', 'allow_parallel_campaigns')
```

#### 1.2: Testing & Validation
- [ ] Test migration upgrade in staging
- [ ] Test migration downgrade (rollback path)
- [ ] Verify trigger fires correctly for status transitions
- [ ] Performance test: Measure trigger overhead (<50ms requirement)
- [ ] Test concurrent activation attempts (should block correctly)

**Deliverables:**
- Migration script tested in staging
- Trigger performance metrics
- Rollback procedure documented

---

### Phase 2: Application Services (3-4 days)
**Objective**: Extend license enforcement and activation logic

**Tasks:**

#### 2.1: Update LicenseService
**File**: `license_service.py`

```python
@staticmethod
def can_activate_campaign(business_account_id: int) -> bool:
    """
    Check if business account can activate another campaign.
    
    Checks:
    1. Platform admin bypass (unchanged)
    2. License yearly limits (unchanged)
    3. NEW: Parallel campaign setting enforcement
    """
    try:
        # Existing platform admin check
        current_user_id = session.get('business_user_id')
        if current_user_id:
            from models import BusinessAccountUser
            current_user = BusinessAccountUser.query.get(current_user_id)
            if current_user and current_user.is_platform_admin():
                logger.debug(f"Platform admin bypassing campaign limit check")
                return True
        
        # Get business account
        from models import BusinessAccount, Campaign
        business_account = BusinessAccount.query.get(business_account_id)
        if not business_account:
            return False
        
        # NEW: Check parallel campaign setting
        if not business_account.allow_parallel_campaigns:
            # Enforce single active campaign
            active_count = Campaign.query.filter(
                Campaign.business_account_id == business_account_id,
                Campaign.status == 'active'
            ).count()
            
            if active_count >= 1:
                logger.warning(
                    f"Business account {business_account_id} attempted to activate "
                    f"second campaign while parallel campaigns disabled"
                )
                return False
        
        # Existing license limit checks (unchanged)
        period_start, period_end = LicenseService.get_license_period(business_account_id)
        current_license = LicenseService.get_current_license(business_account_id)
        max_campaigns = current_license.max_campaigns_per_year if current_license else 4
        
        # Count campaigns in current period
        campaigns_used = Campaign.query.filter(
            Campaign.business_account_id == business_account_id,
            Campaign.status.in_(['active', 'completed']),
            Campaign.created_at >= period_start,
            Campaign.created_at <= period_end
        ).count()
        
        return campaigns_used < max_campaigns
        
    except Exception as e:
        logger.error(f"Error in can_activate_campaign: {e}")
        return False
```

#### 2.2: Update Campaign Activation Routes
**File**: `campaign_routes.py`

```python
@campaigns.route('/campaigns/<int:campaign_id>/activate', methods=['POST'])
@require_login
def activate_campaign(campaign_id):
    try:
        # CRITICAL: Lock business account during validation
        business_account = BusinessAccount.query.filter_by(
            id=current_account.id
        ).with_for_update().first()
        
        # Check activation allowed
        if not LicenseService.can_activate_campaign(business_account.id):
            db.session.rollback()
            license_info = LicenseService.get_license_info(business_account.id)
            
            # Check if blocked due to parallel campaigns setting
            if not business_account.allow_parallel_campaigns:
                active_campaigns = Campaign.query.filter_by(
                    business_account_id=business_account.id,
                    status='active'
                ).all()
                
                if active_campaigns:
                    flash(
                        f'Cannot activate campaign. Another campaign "{active_campaigns[0].name}" '
                        f'is already active. Only one campaign can be active at a time. '
                        f'Please complete the active campaign first.',
                        'error'
                    )
                    return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
            
            # License limit error
            flash(
                f'Cannot activate campaign. Your {license_info["license_type"]} license allows '
                f'{license_info["campaigns_limit"]} campaigns per period. You have used '
                f'{license_info["campaigns_used"]} campaigns.',
                'error'
            )
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Get and activate campaign
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=business_account.id
        ).first_or_404()
        
        campaign.status = 'active'
        db.session.commit()
        
        flash('Campaign activated successfully', 'success')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except IntegrityError as e:
        db.session.rollback()
        if 'parallel campaigns disabled' in str(e).lower():
            flash(
                'Cannot activate: Another campaign is already active. '
                'Please complete it first or contact support to enable parallel campaigns.',
                'error'
            )
        else:
            flash('Database error during activation', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
```

#### 2.3: Update Campaign Scheduler
**File**: `task_queue.py`

```python
def _run_campaign_scheduler(self):
    """Background job to auto-activate/complete campaigns"""
    from models import Campaign, BusinessAccount
    from license_service import LicenseService
    
    today = date.today()
    changes = 0
    
    # Auto-activate ready campaigns
    ready_campaigns = Campaign.query.filter(
        Campaign.status == 'ready',
        Campaign.start_date <= today
    ).all()
    
    for campaign in ready_campaigns:
        try:
            # Lock business account
            business_account = BusinessAccount.query.filter_by(
                id=campaign.business_account_id
            ).with_for_update().first()
            
            # Check activation allowed
            if not LicenseService.can_activate_campaign(business_account.id):
                logger.warning(
                    f"Cannot auto-activate campaign {campaign.id}: "
                    f"License limit or parallel campaign restriction"
                )
                continue
            
            # Activate campaign (trigger will enforce rules)
            campaign.status = 'active'
            db.session.commit()
            changes += 1
            logger.info(f"Auto-activated campaign {campaign.id}")
            
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Failed to auto-activate campaign {campaign.id}: {e}")
    
    # Auto-complete expired campaigns (unchanged)
    # ...existing completion logic...
    
    return changes
```

#### 2.4: Add Audit Events
**File**: `audit_service.py` (if separate) or inline in routes

```python
# Event: parallel_campaign_setting_changed
# Event: campaign_activation_blocked_parallel
# See audit trail section below for full specification
```

**Deliverables:**
- Updated LicenseService with parallel campaign checks
- Campaign activation routes with SELECT FOR UPDATE
- Scheduler updates with proper locking
- Audit event logging integrated

---

### Phase 3: Platform Admin UI (2-3 days)
**Objective**: Expose toggle in admin interface with proper controls

**Tasks:**

#### 3.1: Update Admin Licenses Page
**File**: `templates/business_auth/admin_licenses.html`

```html
<!-- Platform Admin Only: Parallel Campaign Setting -->
{% if current_user.is_platform_admin() %}
<div class="card mt-4">
    <div class="card-header bg-primary text-white">
        <h6 class="mb-0">
            <i class="fas fa-layer-group me-2"></i>
            Parallel Campaign Execution
        </h6>
    </div>
    <div class="card-body">
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
                <p class="mb-2">
                    <strong>Current Setting:</strong> 
                    {% if business_account.allow_parallel_campaigns %}
                        <span class="badge bg-success">
                            <i class="fas fa-check-circle me-1"></i>Enabled
                        </span>
                        <span class="text-muted ms-2">Multiple active campaigns allowed</span>
                    {% else %}
                        <span class="badge bg-secondary">
                            <i class="fas fa-ban me-1"></i>Disabled (Default)
                        </span>
                        <span class="text-muted ms-2">Single active campaign enforced</span>
                    {% endif %}
                </p>
                
                <div class="alert alert-info mt-3 mb-0">
                    <i class="fas fa-info-circle me-2"></i>
                    <strong>What this controls:</strong>
                    <ul class="mb-0 mt-2">
                        <li>When <strong>enabled</strong>: Account can run multiple campaigns simultaneously (subject to license limits)</li>
                        <li>When <strong>disabled</strong>: Only one campaign can be active at a time (default behavior)</li>
                    </ul>
                </div>
            </div>
            
            <div class="ms-4">
                <form method="POST" 
                      action="{{ url_for('business_auth.toggle_parallel_campaigns', account_id=business_account.id) }}" 
                      onsubmit="return confirm('⚠️ Change Parallel Campaign Setting?\n\nThis will {{ 'DISABLE' if business_account.allow_parallel_campaigns else 'ENABLE' }} parallel campaigns for {{ business_account.name }}.\n\n{{ 'They will no longer be able to run multiple campaigns simultaneously.' if business_account.allow_parallel_campaigns else 'They will be able to activate multiple campaigns at once.' }}\n\nThis change is logged in the audit trail. Continue?');">
                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                    <input type="hidden" name="enable" value="{{ 'false' if business_account.allow_parallel_campaigns else 'true' }}"/>
                    
                    <button type="submit" 
                            class="btn {{ 'btn-warning' if business_account.allow_parallel_campaigns else 'btn-success' }}">
                        <i class="fas {{ 'fa-ban' if business_account.allow_parallel_campaigns else 'fa-check-circle' }} me-2"></i>
                        {{ 'Disable' if business_account.allow_parallel_campaigns else 'Enable' }} Parallel Campaigns
                    </button>
                </form>
            </div>
        </div>
    </div>
</div>
{% endif %}
```

#### 3.2: Create Toggle Route Handler
**File**: `business_auth_routes.py`

```python
@business_auth.route('/admin/toggle-parallel-campaigns/<int:account_id>', methods=['POST'])
@require_platform_admin
def toggle_parallel_campaigns(account_id):
    """
    Platform admin only: Toggle parallel campaign setting
    Full audit trail logged
    """
    from models import BusinessAccount
    from audit_service import queue_audit_log
    
    business_account = BusinessAccount.query.get_or_404(account_id)
    
    # Get requested setting
    enable = request.form.get('enable', 'false').lower() == 'true'
    
    # Store old value for audit
    old_value = business_account.allow_parallel_campaigns
    
    # Validate state change
    if old_value == enable:
        flash('Setting is already in the requested state.', 'info')
        return redirect(url_for('business_auth.admin_licenses', account_id=account_id))
    
    # Update setting
    business_account.allow_parallel_campaigns = enable
    
    # Audit trail
    queue_audit_log(
        business_account_id=business_account.id,
        user_id=session.get('business_user_id'),
        event_type='parallel_campaign_setting_changed',
        event_description=f'Parallel campaigns {"enabled" if enable else "disabled"} by platform admin',
        metadata={
            'old_value': old_value,
            'new_value': enable,
            'changed_by_user_id': session.get('business_user_id'),
            'changed_by_email': session.get('business_user_email'),
            'is_platform_admin': True,
            'account_name': business_account.name,
            'account_id': business_account.id,
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': request.remote_addr
        }
    )
    
    db.session.commit()
    
    flash(
        f'✅ Parallel campaign setting {"enabled" if enable else "disabled"} for {business_account.name}. '
        f'This change has been logged in the audit trail.',
        'success'
    )
    return redirect(url_for('business_auth.admin_licenses', account_id=account_id))
```

#### 3.3: Business Account Creation Integration
**File**: Update business account creation form to include toggle

```html
<!-- Add to business account creation form -->
<div class="form-check mb-3">
    <input type="checkbox" 
           class="form-check-input" 
           id="allowParallelCampaigns" 
           name="allow_parallel_campaigns"
           value="true">
    <label class="form-check-label" for="allowParallelCampaigns">
        <strong>Allow Parallel Campaigns</strong>
        <small class="d-block text-muted">
            Enable this account to run multiple campaigns simultaneously (default: disabled)
        </small>
    </label>
</div>
```

**Deliverables:**
- Admin UI with toggle and confirmation dialogs
- Route handler with audit logging
- Business account creation form updated

---

### Phase 4: Testing & Rollout (3-5 days)
**Objective**: Comprehensive testing and safe production deployment

**Tasks:**

#### 4.1: Unit Tests
```python
# tests/test_parallel_campaigns.py

def test_single_active_campaign_enforced_when_disabled():
    """Verify single active campaign rule enforced when flag is False"""
    account = create_business_account(allow_parallel_campaigns=False)
    campaign1 = create_campaign(account, status='active')
    
    with pytest.raises(IntegrityError):
        campaign2 = create_campaign(account, status='active')
        db.session.commit()

def test_multiple_active_campaigns_allowed_when_enabled():
    """Verify parallel campaigns work when flag is True"""
    account = create_business_account(allow_parallel_campaigns=True)
    campaign1 = create_campaign(account, status='active')
    campaign2 = create_campaign(account, status='active')
    db.session.commit()
    
    assert Campaign.query.filter_by(status='active').count() == 2

def test_license_service_respects_parallel_setting():
    """Verify LicenseService.can_activate_campaign() checks parallel flag"""
    account = create_business_account(allow_parallel_campaigns=False)
    campaign1 = create_campaign(account, status='active')
    
    assert LicenseService.can_activate_campaign(account.id) is False

def test_scheduler_respects_parallel_setting():
    """Verify background scheduler honors parallel campaign setting"""
    # Test auto-activation with parallel campaigns disabled
    # Test auto-activation with parallel campaigns enabled

def test_audit_trail_logs_setting_changes():
    """Verify audit events created when toggle changed"""
    # Test setting change creates audit log entry
```

#### 4.2: Integration Tests
```python
def test_concurrent_activation_race_condition():
    """Verify SELECT FOR UPDATE prevents race conditions"""
    # Simulate 2 users activating campaigns simultaneously

def test_platform_admin_can_toggle_setting():
    """Verify platform admin can enable/disable parallel campaigns"""
    
def test_business_user_cannot_toggle_setting():
    """Verify non-platform-admin cannot change setting"""

def test_migration_upgrade_downgrade():
    """Verify migration can upgrade and rollback cleanly"""
```

#### 4.3: Load Testing
```bash
# Concurrent activation stress test
# - 10 simultaneous activation requests
# - Verify only 1 succeeds when parallel disabled
# - Verify all succeed when parallel enabled (within license limits)
```

#### 4.4: Deployment Checklist
- [ ] Database backup completed
- [ ] Migration tested in staging
- [ ] Trigger performance validated (<50ms)
- [ ] All tests passing (unit + integration)
- [ ] Documentation updated (replit.md, API docs)
- [ ] Monitoring dashboards configured
- [ ] Rollback procedure documented
- [ ] Feature flag configured (optional: kill-switch)
- [ ] Platform admin training completed
- [ ] Deployment window scheduled (low-traffic period)

#### 4.5: Rollout Strategy
1. **Deploy to Staging**: Test end-to-end with real workflows
2. **Deploy to Production**: During maintenance window (2 AM - 4 AM UTC)
3. **Monitor Phase 1** (48 hours): Watch trigger performance, error rates
4. **Enable for Beta Accounts** (1 week): Select 2-3 accounts for testing
5. **Monitor Phase 2** (1 week): Validate no issues with concurrent campaigns
6. **General Availability**: Platform admins can enable for any account

**Deliverables:**
- Full test suite (unit + integration + load)
- Deployment runbook
- Monitoring dashboards
- Rollback procedure
- Post-deployment validation checklist

---

## Complexity Justification

**Score: 7/10**

### Complexity Breakdown

| Component | Complexity (1-10) | Justification |
|-----------|-------------------|---------------|
| Database Migration | 8 | Trigger creation + index replacement requires careful testing |
| Application Logic | 6 | Multiple entry points to update with transactional locking |
| UI Integration | 4 | Straightforward admin toggle with confirmation |
| Audit Trail | 3 | Existing infrastructure, just add new event types |
| Testing | 7 | Concurrent activation scenarios require careful setup |
| Deployment | 8 | Trigger deployment + data migration needs rehearsal |

**Average: 6.0** → Rounded up to **7/10** due to cross-layer dependencies

### Why Not Higher?
- Existing architecture supports the feature well (defense in depth already designed)
- License system already handles complex limit checks
- Audit trail infrastructure mature and proven
- PostgreSQL triggers are well-documented and testable

### Why Not Lower?
- Multi-layer changes across database, services, UI, and scheduler
- Concurrency scenarios require careful testing
- Database trigger deployment carries inherent risk
- Regression testing scope is broad (all campaign workflows)

---

## Security Considerations

### Access Control
- ✅ **Platform Admin Only**: Toggle restricted to platform administrators
- ✅ **Confirmation Dialogs**: JavaScript confirmation before state change
- ✅ **Audit Logging**: All changes logged with user ID, timestamp, IP
- ✅ **CSRF Protection**: Form submissions require CSRF token

### Data Integrity
- ✅ **Database Trigger**: Final enforcement layer prevents bypasses
- ✅ **Transactional Locking**: SELECT FOR UPDATE prevents race conditions
- ✅ **License Limits**: Unchanged enforcement of yearly campaign limits
- ✅ **Multi-Tenant Isolation**: No cross-account access possible

---

## Rollback Strategy

### Immediate Rollback (< 5 minutes)
**Scenario**: Critical issue discovered immediately after deployment

```sql
-- Rollback migration
BEGIN;
DROP TRIGGER IF EXISTS check_single_active_campaign ON campaigns;
DROP FUNCTION IF EXISTS enforce_single_active_campaign;
CREATE UNIQUE INDEX idx_single_active_campaign_per_account 
    ON campaigns (business_account_id) WHERE status = 'active';
ALTER TABLE business_accounts DROP COLUMN allow_parallel_campaigns;
COMMIT;
```

### Delayed Rollback (< 1 hour)
**Scenario**: Issues discovered during monitoring phase

1. Set all `allow_parallel_campaigns = false` in database
2. Complete any in-flight activations
3. Run migration downgrade during next maintenance window

### Partial Rollback
**Scenario**: Feature works but needs refinement

1. Keep database schema
2. Disable UI toggle (hide from admin interface)
3. Set all accounts to `allow_parallel_campaigns = false`
4. Fix issues and re-enable

---

## Success Metrics

### Technical Metrics
- ✅ **Trigger Performance**: < 50ms overhead on campaign activation
- ✅ **Zero Data Integrity Issues**: No unauthorized parallel campaigns
- ✅ **Zero Race Conditions**: All concurrent activations handled correctly
- ✅ **100% Audit Coverage**: All setting changes logged

### Business Metrics
- 📊 **Adoption Rate**: Track how many accounts have parallel campaigns enabled
- 📊 **Campaign Throughput**: Measure increase in concurrent active campaigns
- 📊 **Error Rate**: Monitor activation failures due to parallel restrictions

### User Experience Metrics
- 👥 **Platform Admin Satisfaction**: Survey after 1 month of use
- 👥 **Business Account Feedback**: Monitor support tickets related to feature
- 👥 **Activation Success Rate**: Compare before/after deployment

---

## Open Questions & Decisions Needed

### Q1: Feature Flag for Kill-Switch?
**Question**: Should we add an environment variable to disable the feature globally?  
**Recommendation**: Yes - `ENABLE_PARALLEL_CAMPAIGNS=true/false`  
**Rationale**: Provides instant rollback without database changes

### Q2: Default Setting for New Accounts?
**Question**: Should `allow_parallel_campaigns` default to True or False?  
**Current**: False (single active campaign)  
**Recommendation**: Keep False (safer default, explicit opt-in)

### Q3: Notification to Business Account Owners?
**Question**: Should we email business account when setting is changed?  
**Recommendation**: Yes - transparency builds trust  
**Implementation**: Add email notification in toggle route handler

### Q4: Migration Deployment Window?
**Question**: When should we deploy the database migration?  
**Recommendation**: Next planned maintenance window or dedicated 2 AM - 4 AM UTC slot

---

## Appendix A: Campaign Status Taxonomy

**Current Status Values:**
```python
Campaign.status in ('draft', 'ready', 'active', 'paused', 'completed')
```

**Trigger Logic Alignment:**
- ✅ Trigger checks `NEW.status = 'active'`
- ✅ Ignores 'draft', 'ready', 'paused', 'completed'
- ✅ Only enforces on INSERT or UPDATE that changes status to 'active'

---

## Appendix B: Entry Point Audit

**All Campaign Activation Paths:**

| Entry Point | File | Status | SELECT FOR UPDATE | Audit Logged |
|-------------|------|--------|-------------------|--------------|
| Web UI Activation | campaign_routes.py | ✅ Ready | ✅ Required | ✅ Via route handler |
| Background Scheduler | task_queue.py | ✅ Ready | ✅ Required | ✅ Via scheduler |
| Admin Scripts | admin_tools/*.py | ⚠️ TODO | ✅ Required | ✅ Via script |
| Test Fixtures | tests/fixtures.py | ⚠️ TODO | ✅ Required | ❌ Tests only |
| Future API | N/A | 📝 TBD | ✅ Required | ✅ Via API |

**Action Items:**
- [ ] Review all admin scripts for activation logic
- [ ] Update test fixtures to handle IntegrityError
- [ ] Add code review checklist item for future campaign activation code

---

## Appendix C: Monitoring & Alerting

**Recommended Dashboards:**

1. **Parallel Campaigns Overview**
   - Accounts with parallel campaigns enabled (count)
   - Active campaigns per account (histogram)
   - Activation success/failure rates

2. **Performance Metrics**
   - Trigger execution time (p50, p95, p99)
   - Database lock wait times
   - SELECT FOR UPDATE query duration

3. **Error Tracking**
   - IntegrityError exceptions (parallel campaigns disabled)
   - License limit exceeded errors
   - Concurrent activation race conditions

**Alerts:**
- 🚨 Trigger execution > 100ms (Warning)
- 🚨 Activation failure rate > 5% (Critical)
- 🚨 Unauthorized parallel campaign detected (Critical)

---

## Document Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Oct 30, 2025 | Architect | Initial implementation plan |
| 2.0 | Nov 24, 2025 | Architect | Updated risk matrix, complexity assessment, validation of original plan |

---

## Approval & Sign-Off

- [x] **Architect Review**: Approved (Nov 24, 2025)
- [ ] **Platform Owner**: Pending
- [ ] **Engineering Lead**: Pending
- [ ] **QA Lead**: Pending

---

**Next Steps:**
1. Platform owner reviews and approves plan
2. Create implementation tickets in task tracking system
3. Schedule deployment window
4. Begin Phase 0 (Preparation)
