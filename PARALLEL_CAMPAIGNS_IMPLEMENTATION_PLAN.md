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

#### Multi-Layer Defense Architecture

**Critical Design Principle:** Data integrity MUST NOT depend solely on application code. We implement a defense-in-depth approach with three enforcement layers.

#### Layer 1: Database Trigger (Primary Safeguard)

Replace the partial unique index with a PostgreSQL trigger that enforces single-active campaign rule when `allow_parallel_campaigns = false`.

**Rationale:** This ensures data integrity even if:
- Scripts bypass application layer
- Future code paths forget the check
- Background jobs activate campaigns directly

**Implementation:**
```sql
-- Create trigger function
CREATE OR REPLACE FUNCTION enforce_single_active_campaign()
RETURNS TRIGGER AS $$
DECLARE
    account_parallel_allowed BOOLEAN;
    existing_active_count INTEGER;
BEGIN
    -- Only check when activating a campaign (status becomes 'active')
    IF NEW.status = 'active' AND (TG_OP = 'INSERT' OR OLD.status != 'active') THEN
        
        -- Check if parallel campaigns allowed for this account
        SELECT allow_parallel_campaigns INTO account_parallel_allowed
        FROM business_accounts
        WHERE id = NEW.business_account_id;
        
        -- If parallel not allowed, enforce single active campaign
        IF NOT account_parallel_allowed THEN
            -- Count existing active campaigns for this account
            SELECT COUNT(*) INTO existing_active_count
            FROM campaigns
            WHERE business_account_id = NEW.business_account_id
              AND status = 'active'
              AND id != NEW.id;  -- Exclude the campaign being activated
            
            -- Raise error if another active campaign exists
            IF existing_active_count > 0 THEN
                RAISE EXCEPTION 
                    'Cannot activate campaign: business_account_id % has parallel campaigns disabled and already has % active campaign(s). Campaign ID: %',
                    NEW.business_account_id, existing_active_count, NEW.id
                USING ERRCODE = 'unique_violation',
                      HINT = 'Enable parallel campaigns for this account or complete existing active campaigns first.';
            END IF;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
CREATE TRIGGER check_single_active_campaign
    BEFORE INSERT OR UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION enforce_single_active_campaign();
```

**Migration Update:**
```python
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
                FROM business_accounts
                WHERE id = NEW.business_account_id;
                
                IF NOT account_parallel_allowed THEN
                    SELECT COUNT(*) INTO existing_active_count
                    FROM campaigns
                    WHERE business_account_id = NEW.business_account_id
                      AND status = 'active'
                      AND id != NEW.id;
                    
                    IF existing_active_count > 0 THEN
                        RAISE EXCEPTION 
                            'Cannot activate campaign: business_account_id % has parallel campaigns disabled and already has % active campaign(s). Campaign ID: %',
                            NEW.business_account_id, existing_active_count, NEW.id
                        USING ERRCODE = 'unique_violation',
                              HINT = 'Enable parallel campaigns for this account or complete existing active campaigns first.';
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

#### Layer 2: Application-Layer Enforcement

**Location:** `license_service.py` - `LicenseService.can_activate_campaign()`

**Purpose:** Provide clear error messages and prevent unnecessary database round-trips

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

#### Layer 3: Transaction-Level Concurrency Control

**Purpose:** Prevent race conditions during concurrent activation attempts

**All Campaign Activation Entry Points MUST Use SELECT FOR UPDATE:**

1. **Primary Route:** `campaign_routes.py - activate_campaign()`
2. **Background Jobs:** `campaign_lifecycle_manager.py - auto_activate_campaigns()`
3. **Admin Tools:** Any admin scripts that activate campaigns
4. **Test Utilities:** Test fixtures that create active campaigns
5. **API Endpoints:** Any future API that activates campaigns

#### Complete Entry Point Inventory

**MANDATORY REQUIREMENT:** All code paths that activate campaigns must use transactional locking.

**Entry Point 1: Web UI Campaign Activation**
```python
# File: campaign_routes.py - activate_campaign()
@campaigns.route('/campaigns/<int:campaign_id>/activate', methods=['POST'])
@require_login
def activate_campaign(campaign_id):
    try:
        # CRITICAL: Lock business account during validation
        business_account = BusinessAccount.query.filter_by(
            id=current_account.id
        ).with_for_update().first()
        
        # Perform validation with locked row
        if not LicenseService.can_activate_campaign(business_account.id):
            db.session.rollback()
            license_info = LicenseService.get_license_info(business_account.id)
            flash(f'Cannot activate campaign. {license_info["campaigns_used"]}/{license_info["campaigns_limit"]} campaigns used.', 'error')
            return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
        # Get campaign and verify ownership
        campaign = Campaign.query.filter_by(
            id=campaign_id,
            business_account_id=business_account.id
        ).first_or_404()
        
        # Activate campaign (trigger will enforce rules)
        campaign.status = 'active'
        db.session.commit()
        
        flash('Campaign activated successfully', 'success')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
        
    except IntegrityError as e:
        db.session.rollback()
        if 'parallel campaigns disabled' in str(e).lower():
            flash('Cannot activate: Another campaign is already active. Please complete it first.', 'error')
        else:
            flash('Database error during activation', 'error')
        return redirect(url_for('campaigns.view_campaign', campaign_id=campaign_id))
```

**Entry Point 2: Background Job - Auto Campaign Lifecycle**
```python
# File: campaign_lifecycle_manager.py - auto_activate_campaigns()
def auto_activate_campaigns():
    """Background job to auto-activate ready campaigns on their start_date"""
    today = date.today()
    
    # Find campaigns ready for activation
    ready_campaigns = Campaign.query.filter(
        Campaign.status == 'ready',
        Campaign.start_date <= today
    ).all()
    
    for campaign in ready_campaigns:
        try:
            # CRITICAL: Lock business account during validation
            business_account = BusinessAccount.query.filter_by(
                id=campaign.business_account_id
            ).with_for_update().first()
            
            # Check if activation allowed
            if not LicenseService.can_activate_campaign(business_account.id):
                logger.warning(f"Cannot auto-activate campaign {campaign.id}: License limit reached")
                continue
            
            # Activate (trigger will enforce parallel rules)
            campaign.status = 'active'
            db.session.commit()
            logger.info(f"Auto-activated campaign {campaign.id}")
            
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Failed to auto-activate campaign {campaign.id}: {e}")
```

**Entry Point 3: Admin Scripts**
```python
# File: admin_tools/force_activate_campaign.py
def force_activate_campaign(campaign_id, override_limits=False):
    """Admin script to manually activate a campaign"""
    with app.app_context():
        campaign = Campaign.query.get_or_404(campaign_id)
        
        if not override_limits:
            # CRITICAL: Lock business account
            business_account = BusinessAccount.query.filter_by(
                id=campaign.business_account_id
            ).with_for_update().first()
            
            if not LicenseService.can_activate_campaign(business_account.id):
                raise ValueError("Cannot activate: License limits exceeded")
        
        # Activate (trigger will enforce parallel rules unless overridden)
        campaign.status = 'active'
        
        try:
            db.session.commit()
            print(f"Campaign {campaign_id} activated successfully")
        except IntegrityError as e:
            db.session.rollback()
            if override_limits:
                # For emergency overrides, disable trigger temporarily
                print("WARNING: Overriding parallel campaign restriction")
                db.session.execute("SET session_replication_role = 'replica'")
                campaign.status = 'active'
                db.session.commit()
                db.session.execute("SET session_replication_role = 'origin'")
            else:
                raise
```

**Entry Point 4: Test Utilities**
```python
# File: tests/fixtures.py - create_active_campaign()
def create_active_campaign(business_account, name="Test Campaign"):
    """Test helper to create an active campaign"""
    # CRITICAL: Lock business account during test setup
    business_account = BusinessAccount.query.filter_by(
        id=business_account.id
    ).with_for_update().first()
    
    campaign = Campaign(
        name=name,
        business_account_id=business_account.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        status='active'  # Will trigger enforcement
    )
    
    db.session.add(campaign)
    
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # If parallel disabled and active exists, this is expected
        if not business_account.allow_parallel_campaigns:
            raise ValueError("Cannot create second active campaign: parallel disabled")
        raise
    
    return campaign
```

**Entry Point Audit Checklist:**

- [ ] `campaign_routes.py`: activate_campaign() - uses SELECT FOR UPDATE ✓
- [ ] `campaign_lifecycle_manager.py`: auto_activate_campaigns() - uses SELECT FOR UPDATE ✓
- [ ] `admin_tools/*.py`: All admin scripts reviewed and updated ✓
- [ ] `tests/fixtures.py`: Test helpers handle trigger exceptions ✓
- [ ] Future API endpoints: Must use SELECT FOR UPDATE (enforced by code review)

**Code Review Requirement:** Any PR that activates campaigns MUST include transactional locking.

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

#### Complete Audit Event Specification

**CRITICAL:** Audit logging must use correct field names based on context (platform admin vs business user)

#### Event Type 1: `parallel_campaign_setting_changed`

**Triggered When:** Platform admin enables/disables parallel campaigns for a business account

**Implementation:**
```python
# File: business_auth_routes.py - toggle_parallel_campaigns()
from audit_service import queue_audit_log

# After changing the setting
queue_audit_log(
    business_account_id=business_account.id,
    user_id=session.get('business_user_id'),  # Platform admin's user ID
    event_type='parallel_campaign_setting_changed',
    event_description=f'Parallel campaigns {"enabled" if enable else "disabled"} by platform admin',
    metadata={
        'old_value': old_value,  # Boolean: previous setting
        'new_value': enable,      # Boolean: new setting
        'changed_by_user_id': session.get('business_user_id'),
        'changed_by_email': session.get('business_user_email'),
        'changed_by_name': current_user.full_name if current_user else 'Unknown',
        'is_platform_admin': True,
        'account_name': business_account.business_name,
        'account_id': business_account.id,
        'timestamp': datetime.utcnow().isoformat(),
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'Unknown')
    }
)
```

**Field Mappings:**
- `business_account_id`: ID of the account whose setting changed
- `user_id`: Platform admin's BusinessAccountUser.id
- `metadata.changed_by_user_id`: Same as user_id (redundant but explicit)
- `metadata.changed_by_email`: Platform admin's email
- `metadata.old_value`: Previous allow_parallel_campaigns value
- `metadata.new_value`: New allow_parallel_campaigns value

**Database Schema:**
```python
# Existing AuditLog model supports this structure
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_account_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=True)  # Platform admin ID
    event_type = db.Column(db.String(100), nullable=False)
    event_description = db.Column(db.Text, nullable=True)
    metadata = db.Column(db.JSON, nullable=True)  # Flexible structure
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### Event Type 2: `campaign_activation_blocked_parallel`

**Triggered When:** Campaign activation blocked due to parallel campaigns disabled

**Implementation:**
```python
# File: license_service.py - can_activate_campaign()
def can_activate_campaign(business_account_id: int) -> bool:
    business_account = BusinessAccount.query.get(business_account_id)
    
    if not business_account.allow_parallel_campaigns:
        active_count = Campaign.query.filter(
            Campaign.business_account_id == business_account_id,
            Campaign.status == 'active'
        ).count()
        
        if active_count >= 1:
            # Get existing active campaigns for logging
            active_campaigns = Campaign.query.filter(
                Campaign.business_account_id == business_account_id,
                Campaign.status == 'active'
            ).all()
            
            # Log the blocked activation attempt
            # CRITICAL: Use has_request_context() to support background jobs, scripts, tests
            from audit_service import queue_audit_log
            from flask import has_request_context, session, request
            
            # Safely extract request context data with fallbacks
            if has_request_context():
                user_id = session.get('business_user_id')
                user_email = session.get('business_user_email')
                ip_address = request.remote_addr
                user_agent = request.headers.get('User-Agent', 'Unknown')
                context_type = 'web_request'
            else:
                # Background job, admin script, or test context
                user_id = None
                user_email = 'system_background_job'
                ip_address = None
                user_agent = 'Background Process'
                context_type = 'background_job'
            
            queue_audit_log(
                business_account_id=business_account_id,
                user_id=user_id,  # None for background jobs
                event_type='campaign_activation_blocked_parallel',
                event_description=f'Campaign activation blocked: parallel campaigns disabled, {active_count} active campaign(s) exist',
                metadata={
                    'reason': 'parallel_campaigns_disabled',
                    'allow_parallel_campaigns': False,
                    'existing_active_count': active_count,
                    'existing_campaign_ids': [c.id for c in active_campaigns],
                    'existing_campaign_names': [c.name for c in active_campaigns],
                    'attempted_by_user_id': user_id,
                    'attempted_by_email': user_email,
                    'context_type': context_type,  # 'web_request' or 'background_job'
                    'timestamp': datetime.utcnow().isoformat(),
                    'ip_address': ip_address,
                    'user_agent': user_agent
                }
            )
            
            logger.warning(f"Business account {business_account_id} attempted to activate "
                          f"second campaign while parallel campaigns disabled (context: {context_type})")
            return False
    
    # Continue with normal validation...
```

**Field Mappings:**
- `business_account_id`: Account attempting activation
- `user_id`: Business user attempting to activate campaign
- `metadata.existing_active_count`: Number of currently active campaigns
- `metadata.existing_campaign_ids`: Array of active campaign IDs
- `metadata.existing_campaign_names`: Array of active campaign names

#### Audit Service Compatibility Check

**Current `queue_audit_log()` Signature:**
```python
# File: audit_service.py
def queue_audit_log(
    business_account_id: int,
    user_id: int = None,
    event_type: str = None,
    event_description: str = None,
    metadata: dict = None
):
    """Queue an audit log entry for async processing"""
    # Implementation uses PostgreSQL task queue
```

**Compatibility:** ✓ CONFIRMED - No changes needed to audit_service.py

**Logging Points Summary:**

1. **Setting Changed** (business_auth_routes.py):
   - Location: `toggle_parallel_campaigns()` route
   - Trigger: After successful database commit
   - Async: Yes (via task queue)

2. **Activation Blocked** (license_service.py):
   - Location: `can_activate_campaign()` method
   - Trigger: Before returning False
   - Async: Yes (via task queue)

3. **Database Trigger Fired** (PostgreSQL):
   - Location: Campaign INSERT/UPDATE trigger
   - Logged: Via application error handling
   - Sample error message logged to application logs

#### Audit Event Queries

**Query: Get all parallel campaign setting changes**
```sql
SELECT 
    al.created_at,
    al.event_description,
    ba.business_name,
    al.metadata->>'changed_by_email' as changed_by,
    al.metadata->>'old_value' as old_value,
    al.metadata->>'new_value' as new_value
FROM audit_logs al
JOIN business_accounts ba ON al.business_account_id = ba.id
WHERE al.event_type = 'parallel_campaign_setting_changed'
ORDER BY al.created_at DESC;
```

**Query: Get all blocked activations**
```sql
SELECT 
    al.created_at,
    ba.business_name,
    al.metadata->>'attempted_by_email' as attempted_by,
    al.metadata->>'existing_active_count' as active_count,
    al.metadata->>'existing_campaign_names' as blocked_campaigns
FROM audit_logs al
JOIN business_accounts ba ON al.business_account_id = ba.id
WHERE al.event_type = 'campaign_activation_blocked_parallel'
ORDER BY al.created_at DESC;
```

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

**TC-6: Background Job Activation (Non-Request Context)**
- Given: Background job auto-activating ready campaigns
- When: Job attempts to activate campaign with parallel disabled and active exists
- Then: Activation blocked correctly
- And: Audit log created with context_type='background_job'
- And: No Flask request context errors raised

**TC-7: Admin Script Activation (Non-Request Context)**
- Given: Admin script activating campaign via CLI
- When: Script runs outside Flask request context
- Then: Campaign activation succeeds/fails based on rules
- And: Audit logging works without session/request proxies
- And: No RuntimeError exceptions

**TC-8: Test Fixture Creation (Non-Request Context)**
- Given: Test setup creating active campaigns
- When: Test runs without request context
- Then: Database trigger enforces rules correctly
- And: Test handles IntegrityError appropriately
- And: No proxy access errors

**Deliverables:**
- Test suite: `test_parallel_campaigns.py`
- Non-request context tests: `test_parallel_campaigns_background.py`
- Integration test results
- Performance test report
- QA sign-off

**Risks:**
- Incomplete test coverage
- Missed edge cases (especially non-request contexts)
- Performance regressions
- RuntimeError in background jobs

**Mitigation:**
- Code coverage requirement: >90%
- Peer review of test cases
- Explicit tests for all activation contexts
- Load testing with production-like data
- Performance baseline comparison
- CI/CD tests run without Flask request context

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
