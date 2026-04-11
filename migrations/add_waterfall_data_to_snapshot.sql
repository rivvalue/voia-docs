-- Migration: Add waterfall_data column to campaign_kpi_snapshots
-- This stores the NPS waterfall analysis by loyalty driver for FullRead (classic) campaigns.
-- Added: 2026-04-10

ALTER TABLE campaign_kpi_snapshots
    ADD COLUMN IF NOT EXISTS waterfall_data TEXT;

-- Phase 2: Add priority matrix and driver analysis summary columns (2026-04-11)
ALTER TABLE campaign_kpi_snapshots
    ADD COLUMN IF NOT EXISTS priority_matrix_data TEXT;

ALTER TABLE campaign_kpi_snapshots
    ADD COLUMN IF NOT EXISTS driver_analysis_summary TEXT;
