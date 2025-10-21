# PostgreSQL Queue Architecture - Target Design

## Executive Summary
Migration from in-memory TaskQueue to PostgreSQL-backed persistent queue for 50 business accounts target (2M emails/year, 200K AI conversations/year).

**Timeline:** Next Year (2025-2026)
**Migration Effort:** 1-2 days
**Infrastructure Cost:** $0 (uses existing PostgreSQL)
**Risk Level:** Low (proven technology, graceful degradation)

---

## Current State (In-Memory Queue)

### Architecture
- **Implementation:** Python `threading.Queue` (in-memory FIFO)
- **Workers:** 3 daemon threads per process
- **Persistence:** None (tasks lost on restart)
- **Multi-process:** Each Gunicorn worker has separate queue (no coordination)
- **Scheduler:** Single thread with PostgreSQL advisory locks

### Limitations
- ❌ Tasks lost on application restart/crash
- ❌ Per-worker isolation (4 workers = 4 separate queues)
- ❌ No task history or audit trail
- ❌ No observability (can't inspect queued tasks)
- ❌ Limited retry mechanism
- ⚠️ No horizontal scaling capability

### What Works Well
- ✅ Simple and lightweight
- ✅ Fast task pickup (<1ms)
- ✅ Adequate for current load (10 accounts)
- ✅ Zero infrastructure dependencies

---

## Target State (PostgreSQL Queue)

### Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│              USER SURVEY SUBMISSION                      │
│  1. Save SurveyResponse to DB (synchronous, <100ms)     │
│  2. Insert task into task_queue table (synchronous)     │
│  3. Return success to user immediately                  │
└──────────────────────────────────────────────────────────┘
                         ║
                         ║ (No blocking - user sees success)
                         ▼
┌──────────────────────────────────────────────────────────┐
│           POSTGRESQL TASK_QUEUE TABLE                    │
│  ┌────────────────────────────────────────────────────┐ │
│  │ id | task_type | task_data | status | priority    │ │
│  │ 1  | ai_analysis | {...}   | pending | 2          │ │
│  │ 2  | send_email  | {...}   | pending | 3          │ │
│  │ 3  | send_reminder | {...} | processing | 3       │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  Indexes:                                                │
│  - idx_pending_tasks (status, priority, scheduled_at)   │
│  - idx_task_type (task_type) for analytics             │
│  - idx_created_at (created_at) for cleanup             │
└──────────────────────────────────────────────────────────┘
                         ║
                         ║ SELECT FOR UPDATE SKIP LOCKED
                         ▼
┌──────────────────────────────────────────────────────────┐
│          BACKGROUND WORKER POOL (5 Workers)              │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Worker 1-3      │  │  Worker 4-5      │            │
│  │  AI Analysis     │  │  Email Sending   │            │
│  │  (GPT-4o calls)  │  │  (SES/SMTP)      │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  Polling: Every 2 seconds with exponential backoff      │
│  Processing: 0.07 tasks/sec avg, 0.2 tasks/sec peak    │
└──────────────────────────────────────────────────────────┘
                         ║
                         ║ Task completion
                         ▼
┌──────────────────────────────────────────────────────────┐
│              TASK HISTORY & MONITORING                   │
│  - Completed tasks kept for 7 days                      │
│  - Failed tasks kept for 30 days                        │
│  - Metrics: queue depth, processing time, error rate    │
│  - Alerts: queue depth > 100, error rate > 5%          │
└──────────────────────────────────────────────────────────┘
```

---

## Database Schema

### Task Queue Table

```sql
CREATE TABLE task_queue (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,           -- 'ai_analysis', 'send_email', etc.
    task_data JSONB NOT NULL,                 -- Task payload (flexible)
    status VARCHAR(20) DEFAULT 'pending',     -- 'pending', 'processing', 'completed', 'failed'
    priority INTEGER DEFAULT 1,               -- 1=normal, 2=high, 3=urgent
    
    -- Scheduling
    scheduled_at TIMESTAMP DEFAULT NOW(),     -- When to process (support delayed tasks)
    
    -- Processing metadata
    claimed_at TIMESTAMP,                     -- When worker claimed the task
    claimed_by VARCHAR(100),                  -- Worker ID that claimed it
    started_at TIMESTAMP,                     -- When processing started
    completed_at TIMESTAMP,                   -- When processing finished
    
    -- Error handling
    error_message TEXT,                       -- Error details if failed
    retry_count INTEGER DEFAULT 0,            -- Number of retry attempts
    max_retries INTEGER DEFAULT 3,            -- Maximum retry attempts
    
    -- Audit
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Business context (for filtering/reporting)
    business_account_id INTEGER,              -- Multi-tenant scoping
    campaign_id INTEGER,                      -- Campaign context
    
    CONSTRAINT fk_business_account FOREIGN KEY (business_account_id) 
        REFERENCES business_account(id) ON DELETE SET NULL,
    CONSTRAINT fk_campaign FOREIGN KEY (campaign_id) 
        REFERENCES campaign(id) ON DELETE SET NULL
);

-- Critical index for worker claiming
CREATE INDEX idx_pending_tasks ON task_queue(status, priority DESC, scheduled_at ASC)
    WHERE status = 'pending';

-- Index for task type analytics
CREATE INDEX idx_task_type ON task_queue(task_type, created_at DESC);

-- Index for cleanup queries
CREATE INDEX idx_created_at ON task_queue(created_at)
    WHERE status IN ('completed', 'failed');

-- Index for business account filtering
CREATE INDEX idx_business_account ON task_queue(business_account_id, status);
```

---

## Worker Claiming Pattern (SELECT FOR UPDATE SKIP LOCKED)

### PostgreSQL 9.5+ Feature
Ensures only ONE worker gets each task (no race conditions):

```python
def claim_next_task(worker_id: str) -> Optional[Dict]:
    """
    Atomically claim the next available task.
    
    Returns:
        Task dict if available, None if queue empty
    """
    task = db.session.execute(
        text("""
            UPDATE task_queue 
            SET status = 'processing', 
                claimed_at = NOW(), 
                claimed_by = :worker_id,
                started_at = NOW()
            WHERE id = (
                SELECT id 
                FROM task_queue
                WHERE status = 'pending'
                  AND scheduled_at <= NOW()
                ORDER BY priority DESC, scheduled_at ASC
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING *
        """),
        {"worker_id": worker_id}
    ).fetchone()
    
    if task:
        db.session.commit()
        return dict(task)
    
    return None
```

**How it works:**
1. `FOR UPDATE` - locks the selected row
2. `SKIP LOCKED` - skips rows locked by other workers
3. `UPDATE ... WHERE id = (SELECT ...)` - atomically claim in one query
4. Each worker gets a different task (no duplicates)

---

## Task Lifecycle

```
┌──────────┐
│ PENDING  │ ◄── Task created
└────┬─────┘
     │
     │ Worker claims task (SELECT FOR UPDATE SKIP LOCKED)
     ▼
┌──────────────┐
│ PROCESSING   │ ◄── Worker processing
└────┬────┬────┘
     │    │
     │    │ Task fails
     │    ▼
     │  ┌────────┐
     │  │ FAILED │ ◄── Max retries exceeded
     │  └────────┘
     │
     │ Task succeeds
     ▼
┌───────────┐
│ COMPLETED │ ◄── Keep for 7 days, then delete
└───────────┘
```

**Retry Logic:**
- Failed tasks set back to `status='pending'` with `retry_count++`
- If `retry_count >= max_retries`, set `status='failed'` permanently
- Exponential backoff: `scheduled_at = NOW() + (2^retry_count * 60 seconds)`

---

## Performance Characteristics

### Capacity Analysis

| Metric | Current (In-Memory) | Target (PostgreSQL) | Your Load | Headroom |
|--------|---------------------|---------------------|-----------|----------|
| **Throughput** | ~1000 tasks/sec | 100-500 tasks/sec | 0.07 tasks/sec | 1,400-7,000x |
| **Latency** | <1ms pickup | 1-5s pickup (polling) | N/A | Acceptable |
| **Persistence** | None | Disk-backed | Required | ✅ |
| **Multi-worker** | Isolated queues | Shared queue | Required | ✅ |
| **Task history** | None | 7-30 days | Desired | ✅ |
| **Horizontal scaling** | No | Yes (multi-server) | Future | ✅ |

### Polling Strategy

**Initial:** Poll every 2 seconds
**Exponential Backoff:** If queue empty, increase to 5s, 10s, 30s (max)
**Reset:** On task found, reset to 2 seconds

**Rationale:**
- Your load: 0.07 tasks/sec = ~1 task every 14 seconds
- Polling every 2s means ~7 empty polls per task
- Minimal overhead: 7 SELECT queries × 2s = 14 seconds of polling
- PostgreSQL easily handles 0.5 queries/second

---

## Migration Strategy

### Phase 1: Implementation (Day 1)
1. Create `task_queue` table schema
2. Implement `PostgresTaskQueue` class (parallel to existing)
3. Add feature flag: `USE_POSTGRES_QUEUE=true/false`
4. Test with non-critical tasks (audit logs)

### Phase 2: Gradual Rollout (Day 1-2)
1. Enable for audit logs (low risk)
2. Enable for AI analysis (medium risk, monitored)
3. Enable for email sending (high priority, last)
4. Monitor queue depth, error rate, processing time

### Phase 3: Cutover (Day 2)
1. Set `USE_POSTGRES_QUEUE=true` as default
2. Deprecate in-memory queue (keep for 1 week as fallback)
3. Monitor for 48 hours

### Phase 4: Cleanup (Day 7+)
1. Remove in-memory queue code
2. Remove feature flag
3. Document new queue in replit.md

### Rollback Plan
- Feature flag toggle back to `USE_POSTGRES_QUEUE=false`
- In-memory queue code remains until Week 2
- Zero data loss (survey responses always saved first)

---

## Worker Pool Configuration

### Current: 3 Workers (All-Purpose)
```python
task_queue = TaskQueue(max_workers=3)
```

### Target: 5 Workers (Specialized)
```python
# Worker pool with specialization
workers = [
    PostgresWorker(id="ai-1", task_types=["ai_analysis"], poll_interval=2),
    PostgresWorker(id="ai-2", task_types=["ai_analysis"], poll_interval=2),
    PostgresWorker(id="ai-3", task_types=["ai_analysis"], poll_interval=2),
    PostgresWorker(id="email-1", task_types=["send_email", "send_reminder_email"], poll_interval=2),
    PostgresWorker(id="email-2", task_types=["send_email", "send_reminder_email"], poll_interval=2),
]
```

**Rationale:**
- AI tasks: 548/day ÷ 3 workers = 183 tasks/worker/day ✅
- Email tasks: 5,479/day ÷ 2 workers = 2,740 tasks/worker/day ✅
- Specialization prevents email delays from blocking AI analysis

---

## Monitoring & Observability

### Metrics to Track
1. **Queue Depth:** `SELECT COUNT(*) FROM task_queue WHERE status='pending'`
   - Alert if > 100 tasks
   
2. **Processing Time:** `AVG(completed_at - started_at)` by task_type
   - Alert if AI analysis > 60 seconds
   
3. **Error Rate:** `COUNT(*) WHERE status='failed' / COUNT(*)`
   - Alert if > 5% in last hour
   
4. **Worker Health:** `SELECT claimed_by, COUNT(*) FROM task_queue WHERE status='processing' GROUP BY claimed_by`
   - Alert if any worker stuck on same task > 5 minutes

### Dashboard Queries

```sql
-- Queue health overview
SELECT 
    status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_age_seconds
FROM task_queue
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY status;

-- Task type breakdown
SELECT 
    task_type,
    COUNT(*) as total,
    SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
    AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_processing_time
FROM task_queue
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY task_type;

-- Stuck tasks (processing > 5 minutes)
SELECT 
    id, 
    task_type, 
    claimed_by, 
    started_at,
    EXTRACT(EPOCH FROM (NOW() - started_at)) as processing_seconds
FROM task_queue
WHERE status = 'processing'
  AND started_at < NOW() - INTERVAL '5 minutes';
```

---

## Cleanup Strategy

### Completed Tasks
- Keep for 7 days for debugging
- Daily cleanup job at 2 AM UTC
```sql
DELETE FROM task_queue 
WHERE status = 'completed' 
  AND completed_at < NOW() - INTERVAL '7 days';
```

### Failed Tasks
- Keep for 30 days for analysis
- Monthly cleanup job
```sql
DELETE FROM task_queue 
WHERE status = 'failed' 
  AND completed_at < NOW() - INTERVAL '30 days';
```

---

## Scalability Roadmap

### Current Target: 50 Business Accounts
- **PostgreSQL Queue:** ✅ Perfect fit (500-2,500x headroom)
- **5 Workers:** ✅ Adequate capacity
- **Infrastructure Cost:** $0

### Future: 100 Business Accounts
- **PostgreSQL Queue:** ✅ Still adequate (250-1,250x headroom)
- **Workers:** Consider 8-10 workers
- **Infrastructure Cost:** $0

### Future: 200 Business Accounts (2-3 years)
- **Evaluate Redis Migration:** Consider if queue depth consistently > 50
- **Workers:** 10-15 workers (can scale horizontally across servers)
- **Infrastructure Cost:** ~$10-30/month for Redis

### Future: 500+ Business Accounts (3+ years)
- **Migrate to Celery + Redis:** Enterprise-grade distributed queue
- **Workers:** Unlimited (horizontal scaling)
- **Infrastructure Cost:** ~$50-100/month

---

## Risk Assessment

### Low Risk
- ✅ PostgreSQL proven technology (billions of transactions/day globally)
- ✅ Feature flag allows instant rollback
- ✅ Survey responses always saved first (no user impact)
- ✅ Gradual rollout by task type

### Medium Risk
- ⚠️ Database connection pool pressure (mitigated: pool_size=10, max_overflow=20)
- ⚠️ Table bloat if cleanup fails (mitigated: daily cleanup job)

### High Risk
- ❌ None identified

---

## Success Criteria

### Day 1 (Implementation)
- ✅ Task queue table created and indexed
- ✅ PostgresTaskQueue class functional
- ✅ Feature flag toggle working
- ✅ Unit tests passing

### Day 2 (Rollout)
- ✅ All task types migrated
- ✅ Zero failed tasks in 24 hours
- ✅ Queue depth < 10 consistently
- ✅ Processing time < 30 seconds avg

### Week 1 (Validation)
- ✅ Zero data loss incidents
- ✅ Email delivery rate = 99%+
- ✅ AI analysis completion rate = 95%+
- ✅ Survey response submission unaffected

### Month 1 (Optimization)
- ✅ Cleanup job running successfully
- ✅ Monitoring dashboard operational
- ✅ Performance metrics stable

---

## Appendix: Comparison to Alternatives

| Feature | PostgreSQL Queue | Redis Queue | Celery |
|---------|-----------------|-------------|--------|
| **Cost** | $0 | $10-30/month | $50-100/month |
| **Throughput** | 100-500/sec | 5,000+/sec | 10,000+/sec |
| **Persistence** | ✅ Disk | ⚠️ Optional (AOF) | ✅ Backend |
| **Setup Time** | 1-2 days | 2-3 days | 1-2 weeks |
| **Complexity** | Low | Low | High |
| **Monitoring** | SQL queries | Redis CLI | Flower dashboard |
| **Best For** | <100 accounts | 100-500 accounts | 500+ accounts |
| **Recommended** | ✅ Next year | Future (2026) | Future (2027+) |

---

## Document Version
- **Version:** 1.0
- **Date:** October 21, 2025
- **Author:** VOÏA Development Team
- **Status:** Pre-Implementation
