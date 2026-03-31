-- Migration: Add campaign vetting fields
-- Task #45: Campaign vetting gate before activation
-- Date: 2026-03-31

ALTER TABLE campaigns
    ADD COLUMN IF NOT EXISTS simulation_completed_at TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN IF NOT EXISTS manager_validated_at TIMESTAMP WITHOUT TIME ZONE,
    ADD COLUMN IF NOT EXISTS manager_validated_by VARCHAR(200);
