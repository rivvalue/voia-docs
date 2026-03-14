#!/usr/bin/env python3
"""
Cleanup script to remove test-generated business accounts from the dev database.

Targets accounts created on 2026-01-28 and 2026-02-09 by test suite runs.
Supports dry-run mode to preview what would be deleted before executing.

Usage:
    python cleanup_test_accounts.py --dry-run   # Preview counts
    python cleanup_test_accounts.py --execute    # Actually delete
"""

import sys
from app import app, db
from sqlalchemy import text


TARGET_DATES = ('2026-01-28', '2026-02-09')


def get_target_account_ids():
    placeholders = ', '.join([f':d{i}' for i in range(len(TARGET_DATES))])
    params = {f'd{i}': d for i, d in enumerate(TARGET_DATES)}
    result = db.session.execute(
        text(f"SELECT id, name, created_at FROM business_accounts WHERE DATE(created_at) IN ({placeholders}) ORDER BY id"),
        params
    ).fetchall()
    return result


def dry_run():
    print("\n=== DRY RUN: Cleanup Test Accounts ===\n")

    accounts = get_target_account_ids()
    account_ids = [row[0] for row in accounts]
    print(f"Found {len(accounts)} business accounts created on {', '.join(TARGET_DATES)}")

    if not account_ids:
        print("Nothing to clean up.")
        return

    print(f"Account ID range: {min(account_ids)} - {max(account_ids)}")
    print(f"\nFirst 5 accounts:")
    for row in accounts[:5]:
        print(f"  ID: {row[0]}, Name: {row[1]}, Created: {row[2]}")
    if len(accounts) > 5:
        print(f"  ... and {len(accounts) - 5} more")

    id_placeholders = ', '.join([f':id{i}' for i in range(len(account_ids))])
    id_params = {f'id{i}': aid for i, aid in enumerate(account_ids)}

    campaign_ids_result = db.session.execute(
        text(f"SELECT id FROM campaigns WHERE business_account_id IN ({id_placeholders})"),
        id_params
    ).fetchall()
    campaign_ids = [r[0] for r in campaign_ids_result]

    print(f"\nRelated record counts:")
    print(f"  Campaigns: {len(campaign_ids)}")

    if campaign_ids:
        cid_placeholders = ', '.join([f':cid{i}' for i in range(len(campaign_ids))])
        cid_params = {f'cid{i}': cid for i, cid in enumerate(campaign_ids)}

        campaign_child_tables = [
            ('survey_response', 'campaign_id'),
            ('campaign_participants', 'campaign_id'),
            ('active_conversations', 'campaign_id'),
            ('executive_reports', 'campaign_id'),
            ('email_deliveries', 'campaign_id'),
            ('export_jobs', 'campaign_id'),
            ('campaign_kpi_snapshots', 'campaign_id'),
            ('classic_survey_configs', 'campaign_id'),
        ]

        for table, col in campaign_child_tables:
            try:
                count = db.session.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE {col} IN ({cid_placeholders})"),
                    cid_params
                ).scalar()
                print(f"  {table}: {count}")
            except Exception as e:
                print(f"  {table}: (error: {e})")

    account_child_tables = [
        ('business_account_users', 'business_account_id'),
        ('participants', 'business_account_id'),
        ('notifications', 'business_account_id'),
        ('audit_logs', 'business_account_id'),
        ('branding_configs', 'business_account_id'),
        ('email_configurations', 'business_account_id'),
        ('survey_templates', 'business_account_id'),
        ('bulk_operation_jobs', 'business_account_id'),
    ]

    for table, col in account_child_tables:
        try:
            count = db.session.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE {col} IN ({id_placeholders})"),
                id_params
            ).scalar()
            print(f"  {table}: {count}")
        except Exception as e:
            print(f"  {table}: (error: {e})")

    print(f"\n  business_accounts: {len(account_ids)} (license_history cascades automatically)")
    print(f"\nTo execute deletion, run: python cleanup_test_accounts.py --execute")


def _make_params(prefix, ids):
    placeholders = ', '.join([f':{prefix}{i}' for i in range(len(ids))])
    params = {f'{prefix}{i}': v for i, v in enumerate(ids)}
    return placeholders, params


def _batch_delete(table, column, ids, prefix='x'):
    if not ids:
        return 0
    total = 0
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i+batch_size]
        placeholders, params = _make_params(prefix, batch)
        result = db.session.execute(
            text(f"DELETE FROM {table} WHERE {column} IN ({placeholders})"),
            params
        )
        total += result.rowcount
    return total


def _safe_batch_delete(table, column, ids, prefix='x'):
    try:
        nested = db.session.begin_nested()
        count = _batch_delete(table, column, ids, prefix)
        nested.commit()
        return count
    except Exception as e:
        nested.rollback()
        print(f"  Skipped {table}: {e}")
        return 0


def execute_cleanup():
    print("\n=== EXECUTING: Cleanup Test Accounts ===\n")

    accounts = get_target_account_ids()
    account_ids = [row[0] for row in accounts]
    print(f"Found {len(accounts)} business accounts to delete")

    if not account_ids:
        print("Nothing to clean up.")
        return

    ph, pm = _make_params('id', account_ids)

    campaign_ids = [r[0] for r in db.session.execute(
        text(f"SELECT id FROM campaigns WHERE business_account_id IN ({ph})"), pm
    ).fetchall()]
    print(f"  Found {len(campaign_ids)} campaigns to delete")

    if campaign_ids:
        count = _batch_delete('survey_response', 'campaign_id', campaign_ids, 'sr')
        print(f"  Deleted {count} from survey_response")

        for table in ['campaign_participants', 'active_conversations', 'executive_reports',
                      'email_deliveries', 'export_jobs', 'campaign_kpi_snapshots',
                      'classic_survey_configs', 'task_queue']:
            count = _safe_batch_delete(table, 'campaign_id', campaign_ids, 'cid')
            print(f"  Deleted {count} from {table}")

        count = _batch_delete('campaigns', 'id', campaign_ids, 'did')
        print(f"  Deleted {count} campaigns")

    aph, apm = _make_params('aid', account_ids)
    user_ids = [r[0] for r in db.session.execute(
        text(f"SELECT id FROM business_account_users WHERE business_account_id IN ({aph})"), apm
    ).fetchall()]
    if user_ids:
        count = _safe_batch_delete('user_sessions', 'user_id', user_ids, 'us')
        print(f"  Deleted {count} from user_sessions")
        count = _safe_batch_delete('platform_email_settings', 'configured_by_user_id', user_ids, 'pes')
        print(f"  Deleted {count} from platform_email_settings")
        count = _safe_batch_delete('platform_survey_settings', 'updated_by_user_id', user_ids, 'pss')
        print(f"  Deleted {count} from platform_survey_settings")

    participant_ids = [r[0] for r in db.session.execute(
        text(f"SELECT id FROM participants WHERE business_account_id IN ({aph})"), apm
    ).fetchall()]
    if participant_ids:
        count = _safe_batch_delete('campaign_participants', 'participant_id', participant_ids, 'cpid')
        print(f"  Deleted {count} from campaign_participants (by participant_id)")
        count = _safe_batch_delete('email_deliveries', 'participant_id', participant_ids, 'edpid')
        print(f"  Deleted {count} from email_deliveries (by participant_id)")

    for table in ['task_queue', 'business_account_users', 'participants',
                  'notifications', 'audit_logs', 'branding_configs',
                  'email_configurations', 'survey_templates',
                  'bulk_operation_jobs', 'license_history']:
        count = _safe_batch_delete(table, 'business_account_id', account_ids, 'ba')
        print(f"  Deleted {count} from {table}")

    count = _batch_delete('business_accounts', 'id', account_ids, 'baid')
    print(f"  Deleted {count} business_accounts")

    db.session.commit()

    remaining = get_target_account_ids()
    remaining_count = len(remaining)
    if remaining_count > 0:
        print(f"\nWARNING: {remaining_count} target accounts still remain after cleanup!")
        sys.exit(1)
    else:
        print(f"\nCleanup complete. Deleted {len(account_ids)} test accounts and all related records.")
        print(f"Verification: 0 target accounts remain.")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('--dry-run', '--execute'):
        print("Usage:")
        print("  python cleanup_test_accounts.py --dry-run    # Preview counts")
        print("  python cleanup_test_accounts.py --execute    # Delete records")
        sys.exit(1)

    with app.app_context():
        if sys.argv[1] == '--dry-run':
            dry_run()
        else:
            execute_cleanup()


if __name__ == '__main__':
    main()
