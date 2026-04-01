"""
Migration: Add simulation_completed_at column to campaigns table

Added by Task #48 to fix missing column introduced by Task #44 (Survey simulation mode).
db.create_all() does not add columns to existing tables, so this migration
issues an ALTER TABLE ... ADD COLUMN IF NOT EXISTS to safely add the column
without dropping any data.

Safe to run multiple times (idempotent).
"""

import logging

logger = logging.getLogger(__name__)


def run(db):
    """Add simulation_completed_at TIMESTAMP column to campaigns table if missing."""
    from sqlalchemy import text
    try:
        db.session.execute(text(
            "ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS simulation_completed_at TIMESTAMP"
        ))
        db.session.commit()
        logger.info("Migration: simulation_completed_at column ensured on campaigns table")
    except Exception as e:
        logger.warning(f"Migration add_simulation_completed_at failed: {e}")
        db.session.rollback()
        raise
