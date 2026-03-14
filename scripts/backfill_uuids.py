#!/usr/bin/env python3
"""
Backfill UUID columns for existing database rows.

Requires PostgreSQL 13+ (uses gen_random_uuid() which is built-in since PG 13).
For PostgreSQL < 13, run: CREATE EXTENSION IF NOT EXISTS pgcrypto;

This script:
1. Adds the uuid column (nullable, no default) if it doesn't exist on each table
2. Populates NULL uuid values with gen_random_uuid()
3. Sets server default for future inserts
4. Adds NOT NULL constraint and unique index

Usage:
    python scripts/backfill_uuids.py --dry-run    # Show counts only
    python scripts/backfill_uuids.py --execute     # Actually run the backfill
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text

TABLES = [
    'survey_response',
    'campaigns',
    'business_accounts',
    'platform_email_settings',
    'participants',
    'campaign_participants',
    'business_account_users',
    'email_deliveries',
    'audit_logs',
    'executive_reports',
    'notifications',
    'bulk_operation_jobs',
]


def check_column_exists(table_name):
    result = db.session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = 'uuid'"
    ), {'table': table_name})
    return result.fetchone() is not None


def add_uuid_column(table_name):
    db.session.execute(text(
        f'ALTER TABLE {table_name} ADD COLUMN uuid VARCHAR(36)'
    ))
    db.session.commit()
    print(f"  + Added uuid column to {table_name} (nullable, no default)")


def count_nulls(table_name):
    result = db.session.execute(text(
        f"SELECT COUNT(*) FROM {table_name} WHERE uuid IS NULL"
    ))
    return result.scalar()


def count_total(table_name):
    result = db.session.execute(text(
        f"SELECT COUNT(*) FROM {table_name}"
    ))
    return result.scalar()


def backfill_table(table_name):
    result = db.session.execute(text(
        f"UPDATE {table_name} SET uuid = gen_random_uuid()::text WHERE uuid IS NULL"
    ))
    db.session.commit()
    return result.rowcount


def set_column_default(table_name):
    db.session.execute(text(
        f"ALTER TABLE {table_name} ALTER COLUMN uuid SET DEFAULT gen_random_uuid()::text"
    ))
    db.session.commit()
    print(f"  + Set server default on {table_name}.uuid")


def add_not_null_constraint(table_name):
    db.session.execute(text(
        f"ALTER TABLE {table_name} ALTER COLUMN uuid SET NOT NULL"
    ))
    db.session.commit()


def add_unique_index(table_name):
    index_name = f"uq_{table_name}_uuid"
    result = db.session.execute(text(
        "SELECT indexname FROM pg_indexes WHERE tablename = :table AND indexname = :idx"
    ), {'table': table_name, 'idx': index_name})
    if result.fetchone() is None:
        db.session.execute(text(
            f"CREATE UNIQUE INDEX {index_name} ON {table_name}(uuid)"
        ))
        db.session.commit()
        print(f"  + Created unique index {index_name}")
    else:
        print(f"  = Unique index {index_name} already exists")


def main():
    parser = argparse.ArgumentParser(description='Backfill UUID columns')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true', help='Show counts without making changes')
    group.add_argument('--execute', action='store_true', help='Run the backfill')
    args = parser.parse_args()

    with app.app_context():
        print(f"\n{'=' * 60}")
        print(f"UUID Backfill {'(DRY RUN)' if args.dry_run else '(EXECUTING)'}")
        print(f"{'=' * 60}\n")

        for table in TABLES:
            total = count_total(table)
            col_exists = check_column_exists(table)

            if not col_exists:
                if args.dry_run:
                    print(f"  {table}: {total} rows — uuid column MISSING (will be added)")
                    continue
                else:
                    add_uuid_column(table)

            nulls = count_nulls(table)

            if args.dry_run:
                if nulls > 0:
                    print(f"  {table}: {total} total, {nulls} need UUIDs")
                else:
                    print(f"  {table}: {total} total, all have UUIDs ✓")
            else:
                if nulls > 0:
                    updated = backfill_table(table)
                    print(f"  {table}: backfilled {updated} rows")
                else:
                    print(f"  {table}: all {total} rows already have UUIDs ✓")

                set_column_default(table)
                add_not_null_constraint(table)
                add_unique_index(table)

        print(f"\n{'=' * 60}")
        if args.dry_run:
            print("DRY RUN complete. No changes made.")
        else:
            print("BACKFILL complete. All tables have UUID columns with NOT NULL + unique index.")
        print(f"{'=' * 60}\n")


if __name__ == '__main__':
    main()
