# Phase 0: Preparation & Validation Report
**Feature:** Concurrent Campaigns  
**Date:** November 25, 2025  
**Status:** ✅ COMPLETE - Ready for Team Review

---

## 1. Campaign Status Taxonomy Audit

### Current Status Values in Database
```
| Status    | Count |
|-----------|-------|
| completed | 13    |
| draft     | 1     |
| active    | 0     |
| ready     | 0     |
| paused    | 0     |
```

### Status Values in Code (models.py)
The Campaign model supports these status transitions:
- `draft` → Initial state when campaign is created
- `ready` → Campaign configured and ready for activation
- `active` → Campaign is live and collecting responses
- `paused` → Campaign temporarily halted (rare)
- `completed` → Campaign has ended

**Trigger Alignment:** ✅ The planned database trigger checks `NEW.status = 'active'` which aligns with the status taxonomy.

---

## 2. Current Database Constraint Verification

### Existing Single Active Campaign Constraint
```sql
CREATE UNIQUE INDEX idx_single_active_campaign_per_account 
ON public.campaigns USING btree (business_account_id) 
WHERE ((status)::text = 'active'::text)
```

**Status:** ✅ Confirmed - This partial unique index will be replaced by the trigger in Phase 1.

### `allow_parallel_campaigns` Column
**Status:** ❌ Does NOT exist yet - confirms implementation has not started.

---

## 3. Code Path Audit for SELECT FOR UPDATE

### Current Usage in Codebase
| File | Location | Pattern | Purpose |
|------|----------|---------|---------|
| `license_service.py` | Line 1105 | `.with_for_update()` | License assignment |
| `participant_routes.py` | Line 1544 | `.with_for_update()` | Bulk operations lock |
| `participant_routes.py` | Line 1769 | `.with_for_update()` | Bulk operations lock |
| `postgres_task_queue.py` | Line 237 | `FOR UPDATE SKIP LOCKED` | Task claiming |

### Campaign Activation Paths - Need Updates
| Entry Point | File | Current State | Action Required |
|-------------|------|---------------|-----------------|
| Web UI Activation | `campaign_routes.py:714` | ❌ No locking | Add `with_for_update()` on BusinessAccount |
| Background Scheduler | `task_queue.py:_auto_activate_campaigns()` | ❌ No locking | Add `with_for_update()` on BusinessAccount |

---

## 4. Existing activate_campaign() Analysis

**Location:** `campaign_routes.py` lines 714-800

**Current Logic Flow:**
1. Get current business account
2. Get campaign by ID (scoped to account)
3. Validate status is 'ready'
4. Check for existing active campaign → **BLOCKS if any active**
5. Check date constraints
6. Check license limits via LicenseService
7. Activate campaign

**Required Changes for Phase 2A:**
- Add `with_for_update()` on BusinessAccount query
- Wrap single-active check with `if not account.allow_parallel_campaigns:`

---

## 5. Pre-Implementation Checklist

| Item | Status | Notes |
|------|--------|-------|
| Campaign status values documented | ✅ | draft, ready, active, paused, completed |
| Trigger logic aligned with statuses | ✅ | Checks `status = 'active'` |
| Current constraint identified | ✅ | `idx_single_active_campaign_per_account` |
| Column does not exist yet | ✅ | Clean starting point |
| SELECT FOR UPDATE patterns exist | ✅ | Can follow existing patterns |
| Activation entry points identified | ✅ | 2 locations need updates |
| No active campaigns in DB currently | ✅ | Safe to deploy |

---

## 6. Risk Assessment Update

| Risk | Pre-Phase 0 | Post-Phase 0 | Notes |
|------|-------------|--------------|-------|
| Status taxonomy mismatch | Medium | ✅ Low | Confirmed alignment |
| Unknown code paths | Medium | ✅ Low | All paths identified |
| Existing constraint conflicts | Medium | ✅ Low | Clean removal path |
| Data migration needed | Unknown | ✅ None | Column add only, default=False |

---

## 7. Phase 1 Readiness

### Migration Script Preview
```python
# Phase 1 will execute:
1. Add column: allow_parallel_campaigns BOOLEAN DEFAULT FALSE
2. Create index: idx_business_account_parallel_campaigns
3. Drop index: idx_single_active_campaign_per_account
4. Create function: enforce_single_active_campaign()
5. Create trigger: check_single_active_campaign
```

### Estimated Downtime
- **Database Migration:** < 30 seconds (column add + trigger create)
- **Application Restart:** Standard restart (~10 seconds)
- **Total:** < 1 minute

---

## 8. Team Approval Checklist

Before proceeding to Phase 1, please confirm:

- [ ] Campaign status taxonomy reviewed and approved
- [ ] Database constraint replacement approach approved
- [ ] Code change locations reviewed
- [ ] Risk assessment accepted
- [ ] Deployment window identified (if needed)

---

## Next Steps (Awaiting Approval)

**Phase 1: Database Schema Changes**
1. Create and run Alembic migration
2. Add `allow_parallel_campaigns` column to BusinessAccount
3. Replace partial unique index with trigger
4. Verify trigger functionality with test cases

**Estimated Duration:** 2-3 days

---

**Phase 0 Completed By:** Solution Architect  
**Ready for Review:** ✅ Yes
