"""
Migration: Add UNIQUE constraint on survey_response.campaign_participant_id

Added by Task #114 (FullRead: Fix resubmission duplicates & response view).

This migration:
1. Deduplicates any existing survey_response rows that share the same
   campaign_participant_id, keeping only the row with the highest id
   (most recent submission) per participant.
2. Adds a UNIQUE constraint on campaign_participant_id to prevent future
   duplicate submissions at the database level.

Safe to run multiple times (idempotent): uses IF NOT EXISTS / existence check
before adding the constraint.
"""

import logging

logger = logging.getLogger(__name__)


def run(db):
    """Deduplicate and add UNIQUE constraint on survey_response.campaign_participant_id."""
    from sqlalchemy import text

    try:
        # Step 1: Remove duplicate rows, keeping the one with the highest id per participant
        db.session.execute(text("""
            DELETE FROM survey_response
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM survey_response
                WHERE campaign_participant_id IS NOT NULL
                GROUP BY campaign_participant_id
            )
            AND campaign_participant_id IS NOT NULL
        """))
        db.session.commit()
        logger.info("Migration: deduplicated survey_response rows by campaign_participant_id")

        # Step 2: Add UNIQUE constraint if it doesn't already exist
        constraint_exists = db.session.execute(text("""
            SELECT COUNT(*) FROM information_schema.table_constraints
            WHERE table_name = 'survey_response'
            AND constraint_name = 'uq_survey_response_campaign_participant'
            AND constraint_type = 'UNIQUE'
        """)).scalar()

        if not constraint_exists:
            db.session.execute(text("""
                ALTER TABLE survey_response
                ADD CONSTRAINT uq_survey_response_campaign_participant
                UNIQUE (campaign_participant_id)
            """))
            db.session.commit()
            logger.info("Migration: UNIQUE constraint uq_survey_response_campaign_participant added to survey_response")
        else:
            logger.info("Migration: UNIQUE constraint uq_survey_response_campaign_participant already exists — skipping")

    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Migration add_survey_response_unique_participant FAILED: {e}. "
            "Duplicate survey submissions may occur until this constraint is added."
        )
        raise
