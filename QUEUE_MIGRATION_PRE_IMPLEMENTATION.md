# Queue Migration Pre-Implementation Checklist

## Overview
This document outlines all pre-implementation steps required before migrating from in-memory TaskQueue to PostgreSQL-backed queue. The goal is to ensure **zero functionality loss** during migration.

---

## Phase 1: Baseline Documentation & Testing

### 1.1 Current Task Queue Usage Inventory

**All files importing task_queue:**
- ✅ `app.py` - starts task queue on application startup
- ✅ `routes.py` - AI analysis, campaign exports
- ✅ `campaign_routes.py` - email tasks
- ✅ `participant_routes.py` - email tasks
- ✅ `business_auth_routes.py` - executive reports, transcript analysis
- ✅ `reminder_service.py` - reminder emails
- ✅ `audit_utils.py` - audit logging
- ✅ `models.py` - campaign lifecycle transitions
- ✅ `fix_classification.py` - manual AI analysis

**Task Types Currently in Use:**
1. `ai_analysis` - Survey response sentiment analysis
2. `send_email` - Participant invitations, campaign notifications
3. `send_reminder_email` - Campaign reminder emails
4. `audit_log` - Background audit trail writing
5. `export_campaign` - Campaign data exports
6. `executive_report` - PDF report generation
7. `transcript_analysis` - Meeting transcript AI analysis

### 1.2 Functional Testing Baseline

**Test Cases to Validate (Before Migration):**

```bash
# Test 1: Survey Submission + AI Analysis
- [ ] Submit survey response
- [ ] Verify response saved to database
- [ ] Verify AI analysis task queued
- [ ] Verify AI analysis completes
- [ ] Verify sentiment_label populated

# Test 2: Campaign Participant Invitation
- [ ] Add participant to campaign
- [ ] Click "Send Invitations" button
- [ ] Verify email task queued
- [ ] Verify EmailDelivery record created
- [ ] Verify email sent (check logs)

# Test 3: Campaign Reminder Emails
- [ ] Campaign with reminder_enabled=True
- [ ] Run reminder service manually
- [ ] Verify reminder tasks queued
- [ ] Verify EmailDelivery records created
- [ ] Verify emails sent

# Test 4: Campaign Export
- [ ] Click "Export Campaign" button
- [ ] Verify export job created
- [ ] Verify export task queued
- [ ] Verify JSON file generated
- [ ] Verify download works

# Test 5: Executive Report Generation
- [ ] Click "Generate Executive Report"
- [ ] Verify report task queued
- [ ] Verify PDF generated
- [ ] Verify download works

# Test 6: Audit Logging
- [ ] Perform any admin action
- [ ] Verify audit_log task queued
- [ ] Verify AuditLog record created

# Test 7: Campaign Scheduler (Automated)
- [ ] Create campaign with start_date=today
- [ ] Wait 5 minutes (scheduler runs)
- [ ] Verify campaign auto-activated
- [ ] Verify audit log created

# Test 8: Email Retry Logic
- [ ] Force email failure (invalid SMTP)
- [ ] Verify EmailDelivery status=failed
- [ ] Wait for retry interval
- [ ] Verify retry task queued
- [ ] Verify retry_count incremented
```

**Baseline Metrics to Record:**
```python
# Current queue statistics
stats = get_queue_stats()
# Record:
# - queue_size
# - workers count
# - last_scheduler_run
# - Average task processing time
```

### 1.3 Database State Verification

**Check Tables Affected:**
```sql
-- Verify these tables exist and have data
SELECT COUNT(*) FROM survey_response;
SELECT COUNT(*) FROM email_delivery;
SELECT COUNT(*) FROM audit_log;
SELECT COUNT(*) FROM export_job;
SELECT COUNT(*) FROM executive_report;
SELECT COUNT(*) FROM campaign_participant;
```

---

## Phase 2: Data Safety & Backup

### 2.1 Database Backup

**Action Required:**
- [ ] Create database snapshot/checkpoint in Replit
- [ ] Document how to rollback if needed
- [ ] Verify restoration process works

**Replit Checkpoint Instructions:**
```
1. Use Replit's automatic checkpoints system
2. Manually trigger checkpoint before migration
3. Test rollback to previous checkpoint
4. Confirm chat history + database state preserved
```

### 2.2 Code Versioning

**Action Required:**
- [ ] Commit all current changes to git
- [ ] Tag current version: `git tag pre-queue-migration`
- [ ] Push to remote (if applicable)
- [ ] Document commit hash for rollback

```bash
# Create safety commit
git add -A
git commit -m "Pre-migration checkpoint: In-memory TaskQueue baseline"
git tag v1.0-pre-queue-migration
```

---

## Phase 3: Dependency Analysis

### 3.1 Check for In-Memory Queue Dependencies

**Critical Behaviors to Preserve:**

1. **Task Ordering:**
   - Current: FIFO (First In, First Out)
   - Target: Priority-based with FIFO within same priority
   - **Risk:** LOW (priority ordering is better)

2. **Task Isolation:**
   - Current: Per-Gunicorn-worker queues (isolated)
   - Target: Shared queue across all workers
   - **Risk:** LOW (shared queue is the goal)

3. **Daemon Threads:**
   - Current: Workers are daemon threads (die with main process)
   - Target: Workers are daemon threads (same behavior)
   - **Risk:** NONE

4. **Scheduler Coordination:**
   - Current: PostgreSQL advisory locks prevent duplicate runs
   - Target: Same mechanism (no change)
   - **Risk:** NONE

5. **Task Retry Logic:**
   - Current: EmailDelivery retry via scheduler (PostgreSQL-backed)
   - Target: Same mechanism (no change)
   - **Risk:** NONE

6. **Graceful Shutdown:**
   - Current: No graceful shutdown (tasks in queue lost)
   - Target: Tasks persist in database (improvement)
   - **Risk:** NONE (improvement)

### 3.2 Identify Hard-Coded Assumptions

**Search for potential issues:**
```bash
# Check for assumptions about task_queue object
grep -r "task_queue.task_queue" .  # Direct queue access (should be minimal)
grep -r "task_queue.qsize()" .     # Queue size checks
grep -r "task_queue.get_stats()" . # Stats endpoint
```

**Findings:**
- `get_queue_stats()` used in routes.py (admin dashboard)
- **Action:** Implement equivalent for PostgreSQL queue

---

## Phase 4: Environment & Configuration

### 4.1 Feature Flag Preparation

**Environment Variables to Add:**
```bash
# Add to .env file
USE_POSTGRES_QUEUE=false  # Start disabled, enable after testing
QUEUE_POLL_INTERVAL=2     # Polling interval in seconds
QUEUE_WORKER_COUNT=5      # Number of worker threads
```

**Configuration Class:**
```python
class QueueConfig:
    USE_POSTGRES_QUEUE = os.environ.get('USE_POSTGRES_QUEUE', 'false').lower() == 'true'
    POLL_INTERVAL = int(os.environ.get('QUEUE_POLL_INTERVAL', '2'))
    WORKER_COUNT = int(os.environ.get('QUEUE_WORKER_COUNT', '5'))
```

### 4.2 Database Migration Script

**Create migration file:**
```bash
# migrations/add_task_queue_table.sql
# To be executed before code deployment
```

**Rollback script:**
```bash
# migrations/rollback_task_queue_table.sql
# In case of issues
```

---

## Phase 5: Monitoring Setup

### 5.1 Metrics to Track During Migration

**Before Migration (Baseline):**
- [ ] Average queue size
- [ ] Task processing time by type
- [ ] Task failure rate
- [ ] Number of tasks processed per hour
- [ ] Scheduler run frequency

**During Migration (Comparison):**
- [ ] Same metrics as above
- [ ] Database query count increase
- [ ] Database connection pool usage
- [ ] Task pickup latency (time from creation to processing start)

### 5.2 Alert Thresholds

**Define alert conditions:**
```python
# Queue depth alert
if queue_depth > 100:
    alert("Queue backlog detected")

# Processing time alert
if avg_processing_time > 60:  # seconds
    alert("Tasks taking too long")

# Error rate alert
if error_rate > 0.05:  # 5%
    alert("High task failure rate")

# Stuck task alert
if task_processing_time > 300:  # 5 minutes
    alert("Task stuck in processing state")
```

---

## Phase 6: Code Review Checklist

### 6.1 Files to Review Before Changes

**Critical files to understand fully:**
- [ ] `task_queue.py` (1370 lines) - current implementation
- [ ] `app.py` - queue initialization
- [ ] `routes.py` - task queue usage patterns
- [ ] `reminder_service.py` - reminder email queueing
- [ ] `email_service.py` - email sending integration

### 6.2 Integration Points to Preserve

**Survey Response Flow:**
```python
# CRITICAL: This flow must remain unchanged
1. Save SurveyResponse to database (SYNCHRONOUS)
2. Queue AI analysis task (ASYNCHRONOUS)
3. Return success to user
4. Background worker processes AI analysis
```

**Email Delivery Flow:**
```python
# CRITICAL: EmailDelivery tracking must work
1. Create EmailDelivery record (status='pending')
2. Queue email task with email_delivery_id
3. Background worker sends email
4. Update EmailDelivery record (status='sent' or 'failed')
```

**Campaign Scheduler Flow:**
```python
# CRITICAL: Scheduler must coordinate across workers
1. Acquire PostgreSQL advisory lock
2. Check for campaigns to activate/complete
3. Update campaign status
4. Queue notification emails
5. Release lock
```

---

## Phase 7: Test Data Preparation

### 7.1 Create Test Campaigns

**Setup test environment:**
```python
# Create test business account
test_account = BusinessAccount(name="Queue Migration Test")

# Create test campaign
test_campaign = Campaign(
    name="Queue Migration Test Campaign",
    business_account_id=test_account.id,
    start_date=date.today(),
    end_date=date.today() + timedelta(days=7)
)

# Add test participants
for i in range(10):
    participant = Participant(
        name=f"Test User {i}",
        email=f"test{i}@example.com",
        business_account_id=test_account.id
    )
    # Add to campaign
```

### 7.2 Prepare Test Scenarios

**Test data volume:**
- [ ] 10 survey responses (trigger AI analysis)
- [ ] 50 email invitations (test email queueing)
- [ ] 5 campaign exports (test long-running tasks)
- [ ] 3 executive reports (test PDF generation)
- [ ] Campaign with auto-activation (test scheduler)

---

## Phase 8: Rollback Plan

### 8.1 Rollback Triggers

**When to rollback:**
- ❌ Survey responses fail to save
- ❌ Email delivery rate drops below 90%
- ❌ AI analysis completion rate drops below 80%
- ❌ Queue depth grows unbounded (>1000 tasks)
- ❌ Database connection pool exhausted
- ❌ Any data loss detected

### 8.2 Rollback Procedure

**Steps to rollback:**
```bash
# 1. Set feature flag
export USE_POSTGRES_QUEUE=false

# 2. Restart application
# (Workers will revert to in-memory queue)

# 3. Verify in-memory queue working
curl http://localhost:5000/api/queue/stats

# 4. Monitor for 1 hour

# 5. If stable, investigate PostgreSQL queue issue

# 6. If unstable, rollback database
# (Use Replit checkpoint restoration)
```

### 8.3 Rollback Testing

**Test rollback before migration:**
- [ ] Enable PostgreSQL queue
- [ ] Submit test task
- [ ] Disable PostgreSQL queue
- [ ] Verify in-memory queue works
- [ ] Repeat 3 times to confirm reliability

---

## Phase 9: Communication Plan

### 9.1 Stakeholder Notification

**Who to notify:**
- [ ] Platform admin users (if any)
- [ ] Active business account owners (if migration affects them)
- [ ] Development team members

**When to notify:**
- [ ] 24 hours before migration
- [ ] At migration start
- [ ] At migration completion
- [ ] If rollback occurs

### 9.2 Maintenance Window

**Recommended approach:**
- [ ] No maintenance window needed (zero-downtime migration)
- [ ] Feature flag allows gradual rollout
- [ ] Users unaffected (surveys still work)

---

## Phase 10: Pre-Implementation Verification

### 10.1 Final Checklist Before Starting

**Verify all of the following:**

- [ ] ✅ Architecture documented (QUEUE_MIGRATION_ARCHITECTURE.md)
- [ ] ✅ Pre-implementation steps documented (this file)
- [ ] ✅ Baseline tests defined
- [ ] ✅ Database backup/checkpoint created
- [ ] ✅ Code committed and tagged
- [ ] ✅ Dependency analysis complete
- [ ] ✅ Feature flag strategy defined
- [ ] ✅ Monitoring setup planned
- [ ] ✅ Rollback plan documented
- [ ] ✅ Test data prepared
- [ ] ⏸️ Current system stable (no errors in logs)
- [ ] ⏸️ Database connection pool healthy
- [ ] ⏸️ All baseline tests passing

### 10.2 Approval Gates

**Required approvals before proceeding:**
- [ ] User confirms architecture document reviewed
- [ ] User confirms pre-implementation checklist reviewed
- [ ] User approves starting implementation

---

## Estimated Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| **Pre-Implementation Validation** | 30 min | Run all baseline tests, verify system health |
| **Database Migration** | 10 min | Create task_queue table and indexes |
| **Code Implementation** | 4-6 hours | Implement PostgresTaskQueue class |
| **Unit Testing** | 1-2 hours | Test PostgresTaskQueue in isolation |
| **Integration Testing** | 2-3 hours | Test with feature flag enabled |
| **Gradual Rollout** | 4-8 hours | Enable by task type, monitor |
| **Validation** | 24 hours | Monitor production usage |
| **Cleanup** | 1 hour | Remove in-memory queue code |
| **TOTAL** | 1.5-2 days | End-to-end migration |

---

## Success Criteria

### Must Have (Before Declaring Success)
- ✅ All 8 baseline test cases pass with PostgreSQL queue
- ✅ Zero survey response submission failures
- ✅ Email delivery rate ≥ 99%
- ✅ AI analysis completion rate ≥ 95%
- ✅ Queue depth < 50 tasks consistently
- ✅ No stuck tasks (processing > 5 minutes)
- ✅ Campaign scheduler runs every 5 minutes
- ✅ All monitoring metrics green for 48 hours

### Nice to Have (Optimization Phase)
- 📊 Task processing time dashboard
- 📊 Queue health monitoring endpoint
- 📊 Automated alerts for queue issues
- 📊 Historical task analytics

---

## Document Status
- **Version:** 1.0
- **Date:** October 21, 2025
- **Status:** Ready for User Review
- **Next Step:** User approval to proceed with implementation

---

## User Action Required

**Please review and confirm:**
1. ✅ Architecture design approved (QUEUE_MIGRATION_ARCHITECTURE.md)
2. ✅ Pre-implementation steps understood
3. ✅ Ready to proceed with baseline testing
4. ✅ Approve database checkpoint creation
5. ✅ Approve starting implementation

**Once approved, we will proceed with:**
1. Running baseline tests (30 minutes)
2. Creating database backup/checkpoint
3. Beginning PostgreSQL queue implementation
