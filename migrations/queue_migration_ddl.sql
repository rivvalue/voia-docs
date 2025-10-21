-- PostgreSQL Task Queue Migration DDL
-- Purpose: Create persistent task queue table for production reliability
-- Date: October 21, 2025
-- Zero data loss requirement: Tasks persist across restarts/crashes

-- ===================================================================
-- STEP 1: Create task_queue table
-- ===================================================================

CREATE TABLE IF NOT EXISTS task_queue (
    id SERIAL PRIMARY KEY,
    task_type VARCHAR(50) NOT NULL,
    task_data JSONB,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 1,
    
    -- Scheduling
    scheduled_at TIMESTAMP NOT NULL DEFAULT NOW(),
    claimed_at TIMESTAMP,
    claimed_by VARCHAR(100),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Multi-tenant context
    business_account_id INTEGER REFERENCES business_accounts(id) ON DELETE CASCADE,
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE CASCADE
);

-- ===================================================================
-- STEP 2: Create optimized indexes
-- ===================================================================

-- Index for pending task queries (most critical for performance)
-- Workers scan for: status='pending' AND scheduled_at <= NOW()
-- ORDER BY priority DESC, scheduled_at ASC
-- Index column order MUST match ORDER BY for optimal performance
CREATE INDEX IF NOT EXISTS idx_pending_tasks 
    ON task_queue (priority DESC, scheduled_at ASC) 
    WHERE status = 'pending';

-- Index for task type filtering and analytics
CREATE INDEX IF NOT EXISTS idx_task_type 
    ON task_queue (task_type, created_at);

-- Index for retention cleanup queries - completed tasks
-- Daily cleanup job deletes: status='completed' AND completed_at < NOW() - INTERVAL '7 days'
CREATE INDEX IF NOT EXISTS idx_completed_retention
    ON task_queue (completed_at)
    WHERE status = 'completed';

-- Index for retention cleanup queries - failed tasks  
-- Daily cleanup job deletes: status='failed' AND completed_at < NOW() - INTERVAL '30 days'
CREATE INDEX IF NOT EXISTS idx_failed_retention
    ON task_queue (completed_at)
    WHERE status = 'failed';

-- Index for multi-tenant views and business account filtering
CREATE INDEX IF NOT EXISTS idx_business_account 
    ON task_queue (business_account_id, status) 
    WHERE business_account_id IS NOT NULL;

-- Index for stuck task detection (stale task recovery)
CREATE INDEX IF NOT EXISTS idx_stuck_tasks
    ON task_queue (status, started_at)
    WHERE status = 'processing';

-- ===================================================================
-- STEP 3: Add task_queue-specific columns to campaigns
-- ===================================================================

-- Email reminder system columns (already added by previous migration)
-- ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS reminder_enabled BOOLEAN DEFAULT false;
-- ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS reminder_delay_days INTEGER DEFAULT 7;

-- ===================================================================
-- NOTES
-- ===================================================================

-- Queue Capacity:
--   - Target: 50 business accounts, 2M emails/year, 200K AI conversations/year
--   - Load: ~0.07 tasks/sec average, ~0.2 tasks/sec peak
--   - Capacity: 100-500 tasks/sec (500-7,000x headroom)

-- Index Strategy:
--   1. idx_pending_tasks: Partial index for hot path (worker claims) - MATCHES ORDER BY clause
--   2. idx_task_type: Analytics and task type filtering
--   3. idx_completed_retention: Retention cleanup for completed tasks (7 days)
--   4. idx_failed_retention: Retention cleanup for failed tasks (30 days)
--   5. idx_business_account: Multi-tenant isolation and reporting
--   6. idx_stuck_tasks: Stale task recovery (crash/timeout handling)

-- Retention Policy:
--   - Completed tasks: 7 days
--   - Failed tasks: 30 days
--   - Pending/processing: No limit (until resolved)

-- Transaction Safety:
--   - Worker claims use: SELECT FOR UPDATE SKIP LOCKED
--   - Ensures atomic task assignment across workers
--   - Prevents duplicate processing

-- Zero Data Loss:
--   - All tasks persisted to PostgreSQL
--   - Stale task recovery on startup and every 5 minutes (requeue stuck tasks)
--   - Recovery threshold: 30 minutes (avoids requeuing long-running tasks like executive reports)
--   - Retry logic with exponential backoff (1, 2, 4 minutes)
--   - Tasks survive application restarts/crashes/deployments
--   - For future enhancement: Consider heartbeat mechanism for sub-30-minute crash detection
