-- Migration: Concurrent Campaigns Feature - Phase 1
-- Version: 1.0
-- Date: November 25, 2025
-- Description: Add allow_parallel_campaigns toggle and trigger-based enforcement

-- ============================================================================
-- UPGRADE SCRIPT
-- ============================================================================

-- Step 1: Add allow_parallel_campaigns column to business_accounts
ALTER TABLE business_accounts 
ADD COLUMN IF NOT EXISTS allow_parallel_campaigns BOOLEAN NOT NULL DEFAULT FALSE;

-- Step 2: Create index for performance
CREATE INDEX IF NOT EXISTS idx_business_account_parallel_campaigns 
ON business_accounts (allow_parallel_campaigns);

-- Step 3: Drop the old partial unique index (if exists)
DROP INDEX IF EXISTS idx_single_active_campaign_per_account;

-- Step 4: Create the enforcement trigger function
CREATE OR REPLACE FUNCTION enforce_single_active_campaign()
RETURNS TRIGGER AS $$
DECLARE
    account_parallel_allowed BOOLEAN;
    existing_active_count INTEGER;
BEGIN
    -- Only check when a campaign is being activated
    IF NEW.status = 'active' AND (TG_OP = 'INSERT' OR OLD.status != 'active') THEN
        -- Look up the parallel campaigns setting for this business account
        SELECT allow_parallel_campaigns INTO account_parallel_allowed
        FROM business_accounts
        WHERE id = NEW.business_account_id;
        
        -- If parallel campaigns NOT allowed, enforce single active campaign
        IF NOT account_parallel_allowed THEN
            -- Count existing active campaigns (excluding the one being activated)
            SELECT COUNT(*) INTO existing_active_count
            FROM campaigns
            WHERE business_account_id = NEW.business_account_id
              AND status = 'active'
              AND id != NEW.id;
            
            -- Block activation if another campaign is already active
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

-- Step 5: Create the trigger (drop first if exists to avoid conflicts)
DROP TRIGGER IF EXISTS check_single_active_campaign ON campaigns;
CREATE TRIGGER check_single_active_campaign
    BEFORE INSERT OR UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION enforce_single_active_campaign();

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify column exists
-- SELECT column_name, data_type, is_nullable, column_default 
-- FROM information_schema.columns 
-- WHERE table_name = 'business_accounts' AND column_name = 'allow_parallel_campaigns';

-- Verify trigger exists
-- SELECT trigger_name, event_manipulation, action_timing 
-- FROM information_schema.triggers 
-- WHERE trigger_name = 'check_single_active_campaign';

-- Verify all accounts default to false
-- SELECT id, name, allow_parallel_campaigns FROM business_accounts;

-- ============================================================================
-- ROLLBACK SCRIPT
-- ============================================================================

-- To rollback this migration, execute the following:
--
-- DROP TRIGGER IF EXISTS check_single_active_campaign ON campaigns;
-- DROP FUNCTION IF EXISTS enforce_single_active_campaign;
-- 
-- CREATE UNIQUE INDEX idx_single_active_campaign_per_account 
--     ON campaigns (business_account_id) 
--     WHERE status = 'active';
-- 
-- DROP INDEX IF EXISTS idx_business_account_parallel_campaigns;
-- ALTER TABLE business_accounts DROP COLUMN IF EXISTS allow_parallel_campaigns;
