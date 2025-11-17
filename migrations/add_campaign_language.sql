-- Migration: Add language support to campaigns
-- Date: 2025-01-15
-- Description: Add language_code column to campaigns table to enable French/English campaign support

-- Add language_code column to campaigns (nullable with default for backward compatibility)
ALTER TABLE campaigns 
ADD COLUMN IF NOT EXISTS language_code VARCHAR(5) DEFAULT 'en';

-- Add check constraint to ensure only valid language codes
ALTER TABLE campaigns
ADD CONSTRAINT chk_campaign_language CHECK (language_code IN ('en', 'fr'));

-- Create index for language filtering
CREATE INDEX IF NOT EXISTS idx_campaign_language ON campaigns(language_code);

-- Optional: Add response_language to survey_response for analytics tracking
ALTER TABLE survey_response
ADD COLUMN IF NOT EXISTS response_language VARCHAR(5);

-- Add comment for documentation
COMMENT ON COLUMN campaigns.language_code IS 'Language code for campaign (en=English, fr=French) - affects emails, survey pages, AI conversations';
COMMENT ON COLUMN survey_response.response_language IS 'Language in which the survey response was collected - for analytics filtering';

-- Update existing campaigns to default English
UPDATE campaigns SET language_code = 'en' WHERE language_code IS NULL;
