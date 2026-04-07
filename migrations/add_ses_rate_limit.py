"""
Migration: Add ses_rate_limit_per_second to platform_email_settings

Added by Task #91 (SES send rate limiter — configurable token bucket).
db.create_all() does not add columns to existing tables, so this migration
issues ALTER TABLE … ADD COLUMN IF NOT EXISTS to safely add the column
without touching any existing data.

Column managed:
  - ses_rate_limit_per_second  FLOAT  NOT NULL DEFAULT 14.0

Safe to run multiple times (idempotent).
"""

import logging

logger = logging.getLogger(__name__)


def run(db):
    """Add ses_rate_limit_per_second column to platform_email_settings if missing."""
    from sqlalchemy import text

    try:
        db.session.execute(text(
            "ALTER TABLE platform_email_settings "
            "ADD COLUMN IF NOT EXISTS ses_rate_limit_per_second FLOAT NOT NULL DEFAULT 14.0"
        ))
        db.session.commit()
        logger.info(
            "Migration: ses_rate_limit_per_second column ensured on "
            "platform_email_settings table"
        )
    except Exception as e:
        db.session.rollback()
        logger.error(
            f"Migration add_ses_rate_limit failed: {e}. "
            "The SES rate limiter will not be configurable from the admin panel "
            "until this column is added."
        )
        raise
