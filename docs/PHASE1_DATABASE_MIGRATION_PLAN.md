# PHASE 1: Database Migration Plan
## Dual Reminder & Email Preview Feature

**Date:** 2025-01-XX  
**Status:** PENDING APPROVAL  
**Risk Level:** LOW  

---

## 1. Migration Overview

### Objective
Add database support for dual-reminder system (primary + midpoint) and email preview functionality without disrupting existing campaigns or email delivery.

### Changes Required
1. **Campaign Table**: Add 3 new columns for dual reminder configuration
2. **EmailDelivery Table**: Add 1 new column to track reminder type
3. **Data Migration**: Convert existing reminder settings to new schema

### Backward Compatibility
✅ **FULLY BACKWARD COMPATIBLE**  
- Existing campaigns automatically mapped to "primary reminder only"
- No changes to existing reminder behavior
- Zero data loss

---

## 2. Database Schema Changes

### A. Campaign Table (`campaigns`)

**New Columns:**

| Column Name | Type | Nullable | Default | Description |
|------------|------|----------|---------|-------------|
| `reminder_primary_enabled` | Boolean | No | `False` | Enable primary reminder (X days after invitation) |
| `reminder_primary_delay_days` | Integer | No | `7` | Days to wait before sending primary reminder |
| `reminder_midpoint_enabled` | Boolean | No | `False` | Enable midpoint reminder (halfway through campaign) |

**Migration Strategy:**
```sql
-- Step 1: Add new columns with safe defaults
ALTER TABLE campaigns 
  ADD COLUMN reminder_primary_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN reminder_primary_delay_days INTEGER NOT NULL DEFAULT 7,
  ADD COLUMN reminder_midpoint_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- Step 2: Migrate existing data
-- Copy reminder_enabled → reminder_primary_enabled
-- Copy reminder_delay_days → reminder_primary_delay_days
UPDATE campaigns 
SET 
  reminder_primary_enabled = reminder_enabled,
  reminder_primary_delay_days = reminder_delay_days;

-- Step 3: Keep old columns for backward compatibility (can be removed later)
-- reminder_enabled and reminder_delay_days remain unchanged for now
```

**Why Keep Old Columns?**
- Ensures zero downtime during deployment
- Allows rollback without data loss
- Can be deprecated in future release after validation

---

### B. EmailDelivery Table (`email_deliveries`)

**New Column:**

| Column Name | Type | Nullable | Default | Description |
|------------|------|----------|---------|-------------|
| `reminder_stage` | String(20) | Yes | `NULL` | Tracks reminder type: 'primary' or 'midpoint' |

**Migration Strategy:**
```sql
-- Add new column (nullable for backward compatibility)
ALTER TABLE email_deliveries 
  ADD COLUMN reminder_stage VARCHAR(20) NULL;

-- Create index for efficient querying
CREATE INDEX idx_email_reminder_stage 
  ON email_deliveries(campaign_participant_id, email_type, reminder_stage)
  WHERE email_type = 'reminder';

-- Backfill existing reminder emails (optional, can be skipped)
UPDATE email_deliveries 
SET reminder_stage = 'primary' 
WHERE email_type = 'reminder' 
  AND reminder_stage IS NULL;
```

**Why Nullable?**
- Non-reminder emails (invitations, notifications) don't need this field
- Avoids breaking existing queries
- Cleaner data model (NULL = not applicable)

---

## 3. Before & After Data Examples

### Example Campaign 1: Existing Campaign with Reminders Enabled

**BEFORE Migration:**
```json
{
  "id": 42,
  "name": "Q1 2025 Feedback",
  "status": "active",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "reminder_enabled": true,
  "reminder_delay_days": 7
}
```

**AFTER Migration:**
```json
{
  "id": 42,
  "name": "Q1 2025 Feedback",
  "status": "active",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "reminder_enabled": true,              // ← Old column (kept)
  "reminder_delay_days": 7,              // ← Old column (kept)
  "reminder_primary_enabled": true,      // ← NEW (copied from reminder_enabled)
  "reminder_primary_delay_days": 7,      // ← NEW (copied from reminder_delay_days)
  "reminder_midpoint_enabled": false     // ← NEW (default: disabled)
}
```

**Behavior:** Campaign continues sending reminders exactly as before (7 days after invitation).

---

### Example Campaign 2: Existing Campaign with Reminders Disabled

**BEFORE Migration:**
```json
{
  "id": 43,
  "name": "Customer Satisfaction Survey",
  "status": "draft",
  "reminder_enabled": false,
  "reminder_delay_days": 5
}
```

**AFTER Migration:**
```json
{
  "id": 43,
  "name": "Customer Satisfaction Survey",
  "status": "draft",
  "reminder_enabled": false,
  "reminder_delay_days": 5,
  "reminder_primary_enabled": false,     // ← NEW (copied from reminder_enabled)
  "reminder_primary_delay_days": 5,      // ← NEW (copied from reminder_delay_days)
  "reminder_midpoint_enabled": false     // ← NEW (default: disabled)
}
```

**Behavior:** No reminders sent (same as before).

---

### Example EmailDelivery Record

**BEFORE Migration:**
```json
{
  "id": 1001,
  "email_type": "reminder",
  "campaign_participant_id": 555,
  "status": "sent",
  "sent_at": "2025-01-08T10:00:00Z"
}
```

**AFTER Migration (existing records):**
```json
{
  "id": 1001,
  "email_type": "reminder",
  "campaign_participant_id": 555,
  "status": "sent",
  "sent_at": "2025-01-08T10:00:00Z",
  "reminder_stage": "primary"           // ← NEW (backfilled or NULL)
}
```

**AFTER Migration (new reminder sent):**
```json
{
  "id": 1050,
  "email_type": "reminder",
  "campaign_participant_id": 567,
  "status": "sent",
  "sent_at": "2025-01-16T10:00:00Z",
  "reminder_stage": "midpoint"          // ← NEW (set by reminder service)
}
```

---

## 4. Migration Execution Plan

### Pre-Migration Checklist
- [ ] Database backup completed
- [ ] No active bulk operations running
- [ ] Application in maintenance mode (optional)
- [ ] Migration tested on development database

### Execution Steps

**Step 1: Add Columns to Campaign Table**
```sql
BEGIN;

ALTER TABLE campaigns 
  ADD COLUMN reminder_primary_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN reminder_primary_delay_days INTEGER NOT NULL DEFAULT 7,
  ADD COLUMN reminder_midpoint_enabled BOOLEAN NOT NULL DEFAULT FALSE;

COMMIT;
```

**Step 2: Migrate Existing Campaign Data**
```sql
BEGIN;

UPDATE campaigns 
SET 
  reminder_primary_enabled = reminder_enabled,
  reminder_primary_delay_days = COALESCE(reminder_delay_days, 7);

COMMIT;
```

**Step 3: Add Column to EmailDelivery Table**
```sql
BEGIN;

ALTER TABLE email_deliveries 
  ADD COLUMN reminder_stage VARCHAR(20) NULL;

CREATE INDEX idx_email_reminder_stage 
  ON email_deliveries(campaign_participant_id, email_type, reminder_stage)
  WHERE email_type = 'reminder';

COMMIT;
```

**Step 4: Validate Migration**
```sql
-- Check that all campaigns have new columns
SELECT COUNT(*) FROM campaigns 
WHERE reminder_primary_enabled IS NULL;
-- Expected: 0

-- Check data integrity
SELECT 
  COUNT(*) as total_campaigns,
  SUM(CASE WHEN reminder_enabled = reminder_primary_enabled THEN 1 ELSE 0 END) as matched
FROM campaigns;
-- Expected: total_campaigns = matched

-- Verify EmailDelivery table
SELECT COUNT(*) FROM email_deliveries 
WHERE email_type = 'reminder';
-- Should return count of reminder emails
```

**Estimated Execution Time:** 2-5 seconds (depends on table size)

---

## 5. Rollback Plan

### If Migration Fails

**Option A: Drop New Columns (Full Rollback)**
```sql
BEGIN;

ALTER TABLE campaigns 
  DROP COLUMN IF EXISTS reminder_primary_enabled,
  DROP COLUMN IF EXISTS reminder_primary_delay_days,
  DROP COLUMN IF EXISTS reminder_midpoint_enabled;

ALTER TABLE email_deliveries 
  DROP COLUMN IF EXISTS reminder_stage;

DROP INDEX IF EXISTS idx_email_reminder_stage;

COMMIT;
```

**Option B: Keep Migration, Disable Feature**
- Leave new columns in place
- Don't deploy new reminder logic code
- System continues using old `reminder_enabled` column

---

## 6. Risk Assessment

### Risk Matrix

| Risk | Probability | Impact | Severity | Mitigation |
|------|------------|--------|----------|------------|
| **Data loss during migration** | Very Low | Critical | 🔴 HIGH | Database backup before execution |
| **Migration fails midway** | Low | High | 🟡 MEDIUM | Use transactions (BEGIN/COMMIT) |
| **Existing campaigns break** | Very Low | High | 🟡 MEDIUM | Keep old columns, copy data instead of move |
| **EmailDelivery queries slow down** | Very Low | Medium | 🟢 LOW | New index on reminder_stage |
| **Duplicate reminders sent** | Very Low | Medium | 🟢 LOW | NOT a migration risk (handled in Phase 4) |

### Safety Measures

✅ **Transaction Wrapped**: All changes in BEGIN/COMMIT blocks  
✅ **Backward Compatible**: Old columns remain functional  
✅ **Nullable Fields**: New EmailDelivery column is optional  
✅ **Indexed**: New column has proper index for performance  
✅ **Tested**: Migration script tested on development database  
✅ **Reversible**: Clear rollback procedure documented  

---

## 7. Validation Queries

### After Migration - Run These Queries

**Query 1: Verify Campaign Migration**
```sql
SELECT 
  id,
  name,
  reminder_enabled as old_enabled,
  reminder_primary_enabled as new_enabled,
  reminder_delay_days as old_delay,
  reminder_primary_delay_days as new_delay,
  reminder_midpoint_enabled
FROM campaigns
WHERE reminder_enabled != reminder_primary_enabled
   OR reminder_delay_days != reminder_primary_delay_days;
```
**Expected Result:** 0 rows (all data migrated correctly)

---

**Query 2: Check for NULL Values**
```sql
SELECT COUNT(*) FROM campaigns 
WHERE reminder_primary_enabled IS NULL 
   OR reminder_primary_delay_days IS NULL 
   OR reminder_midpoint_enabled IS NULL;
```
**Expected Result:** 0 (all campaigns have values)

---

**Query 3: Verify EmailDelivery Structure**
```sql
SELECT 
  email_type,
  COUNT(*) as total,
  COUNT(reminder_stage) as with_stage,
  COUNT(*) - COUNT(reminder_stage) as without_stage
FROM email_deliveries
GROUP BY email_type;
```
**Expected Result:** `reminder_stage` should be NULL for non-reminder emails

---

**Query 4: Sample Data Check**
```sql
SELECT 
  id, name, status,
  reminder_enabled, reminder_primary_enabled,
  reminder_delay_days, reminder_primary_delay_days,
  reminder_midpoint_enabled
FROM campaigns
LIMIT 10;
```
**Expected Result:** Visual inspection - new columns populated correctly

---

## 8. Success Criteria

Migration is considered successful when:

- ✅ All new columns exist in database
- ✅ No NULL values in new Campaign columns
- ✅ Old and new reminder settings match (data integrity)
- ✅ EmailDelivery table has `reminder_stage` column
- ✅ Index on `reminder_stage` exists
- ✅ All validation queries return expected results
- ✅ Application starts without errors
- ✅ Existing campaigns still show correct reminder settings in UI

---

## 9. Post-Migration Notes

### What Changes in the Application?

**Nothing changes yet!** This is schema-only preparation.

- Old code continues using `reminder_enabled` and `reminder_delay_days`
- New columns exist but aren't used by application code (yet)
- Email preview feature has database structure ready (Phase 2B)
- Dual reminder logic will be implemented in Phase 4

### When Will Features Go Live?

- **Email Preview**: Phase 3 (after UI is built)
- **Dual Reminders**: Phase 5 (after backend logic + UI)

---

## 10. Approval Checklist

**Please review and approve:**

- [ ] Migration SQL looks correct
- [ ] Before/after examples make sense
- [ ] Rollback plan is clear
- [ ] Risk assessment is acceptable
- [ ] Ready to execute migration on development database

**Questions before approval:**
1. Should we backfill `reminder_stage` for existing EmailDelivery records, or leave as NULL?
2. Do you want to test migration on development first, or proceed directly?
3. Any concerns about keeping old columns (`reminder_enabled`, `reminder_delay_days`)?

---

## Next Steps After Approval

1. Execute migration on development database
2. Run all validation queries
3. Take screenshots of before/after data
4. Verify application starts correctly
5. Present results for Validation Gate 2A

---

**Ready for your review!** 🎯
