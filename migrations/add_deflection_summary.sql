-- Migration: Add deflection_summary column to survey_response table
-- Phase 6 (Dec 2025): Stores topic status with deflection metadata for analytics
-- Structure: JSON {"total_topics": N, "completed": N, "skipped": N, "deflections": [...]}

ALTER TABLE survey_response ADD COLUMN IF NOT EXISTS deflection_summary TEXT;

-- Add comment for documentation
COMMENT ON COLUMN survey_response.deflection_summary IS 'JSON summary of topic deflections for analytics (Phase 6, Dec 2025)';
