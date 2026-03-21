"""
Backfill tenure_with_fc for existing survey responses where it is NULL.

For each survey_response where tenure_with_fc IS NULL, if there is a linked
campaign_participant_id -> campaign_participants -> participant with a non-null
tenure_years, compute the tenure category via map_tenure_years_to_category()
and write it.

Rows with no valid campaign_participant_id linkage are skipped (NULL preserved).
This is correct: unauthenticated demo/trial participants have no tenure_years.

Usage:
    python scripts/backfill_tenure.py           # dry run (no writes)
    python scripts/backfill_tenure.py --commit  # apply changes

This script is idempotent: rows that already have tenure_with_fc are skipped.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import SurveyResponse, CampaignParticipant, Participant
from tenure_utils import map_tenure_years_to_category

DRY_RUN = '--commit' not in sys.argv


def backfill():
    with app.app_context():
        updated = 0
        no_linkage = 0
        no_tenure = 0

        responses = SurveyResponse.query.filter(
            SurveyResponse.tenure_with_fc.is_(None)
        ).all()

        print(f"Found {len(responses)} responses with NULL tenure_with_fc")

        for resp in responses:
            if not resp.campaign_participant_id:
                no_linkage += 1
                continue

            cp = CampaignParticipant.query.get(resp.campaign_participant_id)
            if cp is None:
                no_linkage += 1
                continue

            participant = Participant.query.get(cp.participant_id)
            if participant is None or participant.tenure_years is None:
                no_tenure += 1
                continue

            tenure_category = map_tenure_years_to_category(participant.tenure_years)

            if DRY_RUN:
                print(
                    f"[DRY RUN] response id={resp.id} "
                    f"campaign_participant_id={resp.campaign_participant_id} "
                    f"tenure_years={participant.tenure_years} -> '{tenure_category}'"
                )
            else:
                resp.tenure_with_fc = tenure_category
                print(
                    f"[UPDATE] response id={resp.id} "
                    f"campaign_participant_id={resp.campaign_participant_id} "
                    f"tenure_years={participant.tenure_years} -> '{tenure_category}'"
                )

            updated += 1

        if not DRY_RUN:
            db.session.commit()
            print(f"\nCommitted {updated} updates.")
        else:
            print(f"\n[DRY RUN] Would update {updated} responses.")

        print(f"Skipped (no campaign_participant_id linkage): {no_linkage}")
        print(f"Skipped (linked participant has no tenure_years): {no_tenure}")


if __name__ == '__main__':
    backfill()
