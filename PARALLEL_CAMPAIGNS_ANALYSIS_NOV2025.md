# Concurrent Campaigns Feature - Analysis & Implementation Plan
**Document Version:** 2.1  
**Date:** November 25, 2025  
**Status:** Ready for Implementation  
**Architect Review:** ✅ Approved with Updated Risk Matrix  
**Addendum:** Dashboard Audit + Downgrade Path Design Complete

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

---

# ADDENDUM: Dashboard Audit & Downgrade Path Design
**Added:** November 25, 2025  
**Purpose:** Address Gap 1 (Dashboard/Analytics Assumptions) and Gap 2 (Toggle Downgrade Path)

---

## Appendix D: Single-Active-Campaign Code Audit

### Audit Scope
Complete codebase analysis to identify all locations that assume only one active campaign exists per business account.

### Audit Methodology
- Searched for patterns: `get_active_campaign`, `active_campaign`, `existing_active`, `.first()` with active status filter
- Reviewed all campaign-related API endpoints
- Examined template rendering logic
- Analyzed background scheduler behavior

---

### D.1: Code Locations Requiring Updates

#### **CRITICAL: Must Fix Before Launch**

| File | Line | Pattern | Issue | Fix Required |
|------|------|---------|-------|--------------|
| `models.py` | 534-542 | `get_active_campaign()` | Returns `.first()` - only one campaign | Update to return list or deprecate |
| `campaign_routes.py` | 738-744 | `existing_active = ...filter_by(status='active').first()` | Blocks activation if any active exists | Check `allow_parallel_campaigns` flag |
| `task_queue.py` | 1986-1994 | `existing_active = ...filter_by(status='active').first()` | Scheduler blocks auto-activation | Check `allow_parallel_campaigns` flag |
| `task_queue.py` | 2058 | `break` after activating one campaign | Only activates one per scheduler run | Remove when parallel enabled |

#### **MEDIUM: API Defaulting Logic**

| File | Line | Pattern | Issue | Fix Required |
|------|------|---------|-------|--------------|
| `routes.py` | 878-880 | `active_campaign = Campaign.get_active_campaign()` | Demo survey uses single active | OK for demo (single tenant) |
| `routes.py` | 1542-1548 | `active_campaign = ...filter_by(status='active').order_by(id.desc()).first()` | Dashboard data defaults to most recent active | ✅ Already uses `.order_by().first()` - safe pattern |
| `routes.py` | 2070-2092 | `get_active_campaign()` API endpoint | Returns single campaign | Update to return list of active campaigns |
| `routes.py` | 2155-2161 | `/api/company_nps` defaults | Uses `.order_by(id.desc()).first()` | ✅ Safe - selects most recent |
| `routes.py` | 2369-2375 | `/api/tenure_nps` defaults | Uses `.order_by(id.desc()).first()` | ✅ Safe - selects most recent |

#### **LOW: UI Display (Informational Only)**

| File | Line | Pattern | Issue | Fix Required |
|------|------|---------|-------|--------------|
| `templates/business_auth/license_info.html` | 198-216 | `{% if active_campaign %}` | Shows single active campaign info | Update to show list or count |
| `templates/business_auth/admin_panel.html` | 578 | `active_campaigns` count | Shows count (already handles multiple) | ✅ No change needed |
| `templates/business_auth/platform_dashboard.html` | 362, 414 | `active_campaigns` metric | Shows count (already handles multiple) | ✅ No change needed |
| `templates/dashboard.html` | 374-381 | `activeCampaignBanner` | Shows single campaign banner | Consider multi-campaign indicator |
| `templates/campaign_insights.html` | 138-145 | `activeCampaignBanner` | Shows single campaign banner | Consider multi-campaign indicator |

---

### D.2: Safe Patterns Already in Use

The following patterns are **already safe** for concurrent campaigns:

1. **Campaign Filtering by ID**: Most API endpoints accept `campaign_id` parameter and filter by specific campaign
2. **Order by DESC + First**: When defaulting, code uses `.order_by(Campaign.id.desc()).first()` which safely selects the most recent
3. **Campaign List Pages**: Campaign list templates already display multiple campaigns
4. **Count-Based Metrics**: Admin panels use `.count()` which handles multiple active campaigns

---

### D.3: Recommended Code Changes

#### Change 1: Update `Campaign.get_active_campaign()` Method

**Current (models.py:534-542):**
```python
@staticmethod
def get_active_campaign(client_identifier='archelo_group'):
    """Get the currently active campaign for a client"""
    today = date.today()
    return Campaign.query.filter(
        Campaign.client_identifier == client_identifier,
        Campaign.status == 'active',
        Campaign.start_date <= today,
        Campaign.end_date >= today
    ).first()
```

**Proposed:**
```python
@staticmethod
def get_active_campaigns(business_account_id: int) -> list:
    """Get all currently active campaigns for a business account"""
    today = date.today()
    return Campaign.query.filter(
        Campaign.business_account_id == business_account_id,
        Campaign.status == 'active',
        Campaign.start_date <= today,
        Campaign.end_date >= today
    ).order_by(Campaign.start_date.desc()).all()

@staticmethod
def get_primary_active_campaign(business_account_id: int):
    """Get the most recent active campaign (for UI defaults)"""
    campaigns = Campaign.get_active_campaigns(business_account_id)
    return campaigns[0] if campaigns else None
```

#### Change 2: Update `campaign_routes.py` Activation Logic

**Current (line 738-744):**
```python
existing_active = Campaign.query.filter_by(
    business_account_id=current_account.id,
    status='active'
).first()

if existing_active:
    flash('Cannot activate campaign...', 'error')
```

**Proposed:**
```python
# Check parallel campaign setting
if not current_account.allow_parallel_campaigns:
    existing_active = Campaign.query.filter_by(
        business_account_id=current_account.id,
        status='active'
    ).first()
    
    if existing_active:
        flash('Cannot activate campaign...', 'error')
        return redirect(...)
```

#### Change 3: Update `task_queue.py` Scheduler

**Current (line 1986-1994):**
```python
existing_active = Campaign.query.filter_by(
    business_account_id=account_id,
    status='active'
).first()

if existing_active:
    logger.debug(f"Cannot activate campaigns...")
    return changes_made
```

**Proposed:**
```python
# Check parallel campaign setting for this account
if not account.allow_parallel_campaigns:
    existing_active = Campaign.query.filter_by(
        business_account_id=account_id,
        status='active'
    ).first()
    
    if existing_active:
        logger.debug(f"Cannot activate campaigns...")
        return changes_made
```

#### Change 4: Update `/api/campaigns/active` Endpoint

**Current (routes.py:2070-2092):**
```python
@app.route('/api/campaigns/active', methods=['GET'])
def get_active_campaign():
    campaign = Campaign.get_active_campaign(client_identifier)
    return jsonify({'active_campaign': campaign.to_dict(), 'has_active_campaign': True})
```

**Proposed:**
```python
@app.route('/api/campaigns/active', methods=['GET'])
def get_active_campaigns():
    """Get all currently active campaigns"""
    campaigns = Campaign.get_active_campaigns(business_account_id)
    return jsonify({
        'active_campaigns': [c.to_dict() for c in campaigns],
        'active_campaign_count': len(campaigns),
        'has_active_campaign': len(campaigns) > 0
    })
```

#### Change 5: Update License Info Template

**Current (license_info.html:198-216):**
```html
{% if active_campaign %}
<div class="license-usage-card">
    Active Campaign: {{ active_campaign.name }}
</div>
{% endif %}
```

**Proposed:**
```html
{% if active_campaigns %}
<div class="license-usage-card">
    <div class="license-usage-header">
        <div class="license-usage-title">
            <i class="fas fa-play-circle"></i>
            Active Campaigns ({{ active_campaigns|length }})
        </div>
    </div>
    {% for campaign in active_campaigns %}
    <div class="active-campaign-item">
        <strong>{{ campaign.name }}</strong>
        <span class="text-muted">{{ campaign.days_remaining() }} days remaining</span>
    </div>
    {% endfor %}
</div>
{% endif %}
```

---

## Appendix E: Toggle Downgrade Path Design

### E.1: Problem Statement

**Scenario:** Platform admin enables parallel campaigns for an account, they activate 2+ campaigns, then admin tries to **disable** parallel campaigns.

**Question:** What should happen?

---

### E.2: Design Options Analysis

| Option | Behavior | Pros | Cons | Recommendation |
|--------|----------|------|------|----------------|
| **A: Block** | Prevent disabling until only 1 campaign active | Safest, no data issues, clear user action | Requires manual intervention | ✅ **RECOMMENDED** |
| **B: Auto-Pause** | Automatically pause newest campaigns | Automated, no admin effort | Could disrupt active surveys, data loss risk | ❌ Too risky |
| **C: Warning Only** | Allow disable, future activations blocked | Most flexible | Inconsistent state, confusing | ❌ Poor UX |
| **D: Force Complete** | Complete all but one campaign | Clean resolution | Premature campaign completion | ❌ Data integrity risk |

---

### E.3: Recommended Approach: Block with Clear Messaging

#### Implementation

**Route Handler Update (business_auth_routes.py):**
```python
@business_auth.route('/admin/toggle-parallel-campaigns/<int:account_id>', methods=['POST'])
@require_platform_admin
def toggle_parallel_campaigns(account_id):
    business_account = BusinessAccount.query.get_or_404(account_id)
    enable = request.form.get('enable', 'false').lower() == 'true'
    
    # DOWNGRADE CHECK: Block disabling if multiple active campaigns exist
    if not enable and business_account.allow_parallel_campaigns:
        active_count = Campaign.query.filter_by(
            business_account_id=account_id,
            status='active'
        ).count()
        
        if active_count > 1:
            flash(
                f'Cannot disable parallel campaigns. '
                f'This account has {active_count} active campaigns. '
                f'Please complete or pause campaigns until only 1 remains active.',
                'error'
            )
            return redirect(url_for('business_auth.admin_licenses', account_id=account_id))
    
    # Proceed with toggle...
    old_value = business_account.allow_parallel_campaigns
    business_account.allow_parallel_campaigns = enable
    
    # Audit logging...
    db.session.commit()
    
    flash(f'Parallel campaigns {"enabled" if enable else "disabled"} for {business_account.name}', 'success')
    return redirect(url_for('business_auth.admin_licenses', account_id=account_id))
```

#### UI Enhancement

**Admin Licenses Page (admin_licenses.html):**
```html
{% if business_account.allow_parallel_campaigns %}
    {% set active_count = active_campaigns|length if active_campaigns else 0 %}
    {% if active_count > 1 %}
        <div class="alert alert-warning mt-2">
            <i class="fas fa-exclamation-triangle me-2"></i>
            <strong>{{ active_count }} campaigns currently active.</strong>
            To disable parallel campaigns, complete or pause campaigns until only 1 remains.
        </div>
    {% endif %}
    
    <button type="submit" 
            class="btn btn-warning"
            {% if active_count > 1 %}disabled{% endif %}>
        <i class="fas fa-ban me-2"></i>
        Disable Parallel Campaigns
    </button>
{% else %}
    <button type="submit" class="btn btn-success">
        <i class="fas fa-check-circle me-2"></i>
        Enable Parallel Campaigns
    </button>
{% endif %}
```

---

### E.4: Validation Rules Summary

| Action | Condition | Allowed | Error Message |
|--------|-----------|---------|---------------|
| Enable parallel | Any state | ✅ Yes | - |
| Disable parallel | 0 active campaigns | ✅ Yes | - |
| Disable parallel | 1 active campaign | ✅ Yes | - |
| Disable parallel | 2+ active campaigns | ❌ No | "Complete or pause campaigns until only 1 remains" |

---

## Appendix F: Cache Invalidation Verification

### F.1: Analysis Summary

**Question:** Does the codebase cache the `allow_parallel_campaigns` value in a way that could cause stale decisions?

### F.2: Investigation Results

| Component | Caching Behavior | Risk Level | Action Required |
|-----------|------------------|------------|-----------------|
| **LicenseService** | No caching of `allow_parallel_campaigns` | ✅ None | No change needed |
| **Campaign Scheduler** | Queries database fresh each run | ✅ None | No change needed |
| **Flask-Caching** | Dashboard data cached, not license settings | ✅ None | No change needed |
| **Session Data** | Not stored in session | ✅ None | No change needed |

### F.3: Verification Code Audit

**LicenseService.can_activate_campaign() (license_service.py):**
```python
def can_activate_campaign(business_account_id: int) -> bool:
    # Each call queries BusinessAccount fresh from database
    business_account = BusinessAccount.query.get(business_account_id)
    # ... uses business_account.allow_parallel_campaigns directly
```
**Result:** ✅ No caching - fresh query each call

**Task Queue Scheduler (task_queue.py):**
```python
def _process_account_campaigns(self, account, today):
    # Account object passed from fresh query in parent loop
    # ... checks account.allow_parallel_campaigns
```
**Result:** ✅ No caching - uses account from current query

### F.4: Conclusion

**No cache invalidation hooks needed.** The codebase queries the database directly for the `allow_parallel_campaigns` setting each time it's needed. Changes to the toggle take effect immediately.

---

## Appendix G: Updated Implementation Phases

Based on the audit findings, the implementation phases are updated:

### Phase 2A: Code Audit Fixes (NEW - 1-2 days)

**Before database migration, update code to prepare for parallel campaigns:**

1. ✅ Add `get_active_campaigns()` method to Campaign model
2. ✅ Add `get_primary_active_campaign()` method for UI defaults
3. ✅ Update `campaign_routes.py` activation logic to check flag
4. ✅ Update `task_queue.py` scheduler to check flag
5. ✅ Update `/api/campaigns/active` endpoint
6. ✅ Update `license_info.html` template

**Why before migration?** These code changes are backward-compatible. The flag will default to `False`, so existing behavior is preserved until we add the database column.

### Phase 2B: Downgrade Path (NEW - 0.5 days)

1. ✅ Add validation in `toggle_parallel_campaigns()` route
2. ✅ Update admin UI with warning message and disabled state
3. ✅ Add integration test for downgrade blocking

---

## Document Changelog

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Oct 30, 2025 | Architect | Initial implementation plan |
| 2.0 | Nov 24, 2025 | Architect | Updated risk matrix, complexity assessment, validation of original plan |
| 2.1 | Nov 25, 2025 | Architect | Added dashboard audit (Appendix D), downgrade path design (Appendix E), cache verification (Appendix F), updated phases |

---

## Approval & Sign-Off

- [x] **Architect Review**: Approved (Nov 24, 2025)
- [x] **Dashboard Audit**: Complete (Nov 25, 2025)
- [x] **Downgrade Path Design**: Complete (Nov 25, 2025)
- [ ] **Platform Owner**: Pending
- [ ] **Engineering Lead**: Pending
- [ ] **QA Lead**: Pending

---

## Summary: Ready for Active Account Enablement

✅ **Confirmed:** The concurrent campaigns feature can be safely enabled for existing active business accounts.

**Prerequisites Addressed:**
1. ✅ Dashboard/Analytics audit complete - 5 code changes identified
2. ✅ Downgrade path designed - Block approach with clear messaging
3. ✅ Cache invalidation verified - No action needed

**Updated Complexity Score:** **7.5/10** (increased slightly due to additional code changes)

**Next Steps:**
1. Platform owner reviews and approves updated plan
2. Begin Phase 2A: Code audit fixes (backward-compatible)
3. Execute database migration (Phase 1)
4. Implement downgrade path (Phase 2B)
5. Testing and rollout (Phase 4)
