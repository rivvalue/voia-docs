"""
Migration: Add vetting columns to campaigns table

Added by Task #48 to fix missing columns introduced by Tasks #44 and #45.
db.create_all() does not add columns to existing tables, so this migration
issues ALTER TABLE ... ADD COLUMN IF NOT EXISTS statements to safely add
the columns without dropping any data.

Columns managed:
  - simulation_completed_at  TIMESTAMP    (Task #44)
  - manager_validated_at     TIMESTAMP    (Task #45)
  - manager_validated_by     VARCHAR(200) (Task #45)

Safe to run multiple times (idempotent).
"""

import logging

logger = logging.getLogger(__name__)


def run(db):
    """Add vetting columns to campaigns table if missing."""
    from sqlalchemy import text

    columns = [
        ("simulation_completed_at", "TIMESTAMP"),
        ("manager_validated_at", "TIMESTAMP"),
        ("manager_validated_by", "VARCHAR(200)"),
    ]

    for col_name, col_type in columns:
        try:
            db.session.execute(text(
                f"ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
            ))
            db.session.commit()
            logger.info(f"Migration: {col_name} column ensured on campaigns table")
        except Exception as e:
            db.session.rollback()
            logger.error(
                f"Migration add_simulation_completed_at failed for column {col_name}: {e}. "
                "Campaigns pages will crash until this column is added."
            )
            raise
