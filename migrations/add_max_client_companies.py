"""
Migration: Add max_client_companies column to license_history table

Added by Task #69 (License — Client company count limit).
db.create_all() does not add columns to existing tables, so this migration
issues ALTER TABLE ... ADD COLUMN IF NOT EXISTS statements to safely add
the column without dropping any data.

Columns managed:
  - max_client_companies  INTEGER  NULL  (NULL means unlimited)

Safe to run multiple times (idempotent).
"""

import logging

logger = logging.getLogger(__name__)


def run(db):
    """Add max_client_companies column to license_history table if missing."""
    from sqlalchemy import text

    try:
        db.session.execute(text(
            "ALTER TABLE license_history ADD COLUMN IF NOT EXISTS max_client_companies INTEGER"
        ))
        db.session.commit()
        logger.info("Migration: max_client_companies column ensured on license_history table")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Migration add_max_client_companies failed: {e}")
        raise
