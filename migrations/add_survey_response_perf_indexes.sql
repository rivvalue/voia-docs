-- Performance indexes for survey_response table
-- Fixes 499 slow queries identified in production analytics (April 2026)
--
-- All indexes use CREATE INDEX CONCURRENTLY IF NOT EXISTS to be:
--   - Non-blocking: no table lock, safe to run against live production
--   - Idempotent: safe to re-run; will not fail if index already exists
--
-- Run this script directly against the production Neon database.
-- NOTE: CONCURRENTLY cannot run inside a transaction block. Run outside
-- of BEGIN/COMMIT or with autocommit enabled.

-- (campaign_id) alone — primary filter used by every distribution query.
-- Already present via column-level index=True in models.py, but adding
-- explicit named index ensures the planner has a clear B-tree to use.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sr_campaign_id
    ON survey_response (campaign_id);

-- (campaign_id, nps_category) — NPS distribution GROUP BY
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sr_campaign_nps_category
    ON survey_response (campaign_id, nps_category);

-- (campaign_id, sentiment_label) — sentiment distribution GROUP BY
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sr_campaign_sentiment_label
    ON survey_response (campaign_id, sentiment_label);

-- (campaign_id, churn_risk_level) — high-risk accounts panel filter
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sr_campaign_churn_risk
    ON survey_response (campaign_id, churn_risk_level);

-- (campaign_id, tenure_with_fc) — tenure distribution GROUP BY
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sr_campaign_tenure
    ON survey_response (campaign_id, tenure_with_fc);

-- (campaign_id, growth_range, growth_rate) — growth factor distribution GROUP BY
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sr_campaign_growth
    ON survey_response (campaign_id, growth_range, growth_rate);

-- Functional index on upper(company_name) — company-level lookups.
-- Without this, any WHERE upper(company_name) = ... bypasses the plain B-tree
-- index on company_name and falls back to a sequential scan.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sr_company_name_upper
    ON survey_response (upper(company_name));

-- (campaign_id, company_name) — company-level data query filter
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sr_campaign_company_name
    ON survey_response (campaign_id, company_name);
