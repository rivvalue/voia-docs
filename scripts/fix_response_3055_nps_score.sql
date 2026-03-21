-- Fix for Task #33: Correct NPS score for survey response ID 3055
-- Root cause: V2 survey ran without campaign context due to missing fields in
-- verify_survey_access return dict, causing NPS score to be recorded incorrectly.
--
-- Before: nps_score=5, nps_category='Detractor'
-- After:  nps_score=9, nps_category='Promoter'
--
-- Applied to production (Neon) database on 2026-03-21.

UPDATE survey_response
SET nps_score = 9,
    nps_category = 'Promoter'
WHERE id = 3055;
