"""
Migration: Add influence_weight column to survey_response table

Added by Task #55 (Influence-Weighted Risk & Growth Scoring, Phase 1).
db.create_all() does not add columns to existing tables, so this migration
issues ALTER TABLE ... ADD COLUMN IF NOT EXISTS to safely add the column
without dropping any data.

Column managed:
  - influence_weight  FLOAT  (nullable, default 1.0)
    Respondent seniority multiplier populated at analysis time.
    C-level=5, VP/Director=3, Manager=2, Team Lead=1.5, End User=1.
    Existing rows without a value will have NULL, treated as 1.0 at runtime.

Safe to run multiple times (idempotent).
"""

import logging

logger = logging.getLogger(__name__)


def run(db):
    """Add influence_weight column to survey_response table if missing."""
    from sqlalchemy import text

    try:
        db.session.execute(text(
            "ALTER TABLE survey_response ADD COLUMN IF NOT EXISTS influence_weight FLOAT DEFAULT 1.0"
        ))
        db.session.commit()
        logger.info("Migration: influence_weight column ensured on survey_response table")
    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Migration add_influence_weight FAILED: {e}. "
            "influence_weight will not persist until this is resolved."
        )
        raise
