"""
YouTrack (JetBrains) bug tracker integration for VOÏA in-app feedback.

Required environment variables (set in Replit Secrets):
    YOUTRACK_URL        – Base URL of your YouTrack instance,
                          e.g. https://yourorg.youtrack.cloud
    YOUTRACK_TOKEN      – Permanent token generated in YouTrack
                          (Profile → Account Security → Tokens)
    YOUTRACK_PROJECT_ID – Short project name/ID in YouTrack, e.g. VOIA
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

YOUTRACK_URL = os.environ.get("YOUTRACK_URL", "").rstrip("/")
YOUTRACK_TOKEN = os.environ.get("YOUTRACK_TOKEN", "")
YOUTRACK_PROJECT_ID = os.environ.get("YOUTRACK_PROJECT_ID", "")


def _headers():
    return {
        "Authorization": f"Bearer {YOUTRACK_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _configured():
    """Return True when all three env vars are set."""
    return bool(YOUTRACK_URL and YOUTRACK_TOKEN and YOUTRACK_PROJECT_ID)


def create_issue(title: str, description: str, issue_type: str, priority: str = None) -> dict:
    """
    Create an issue in YouTrack.

    Args:
        title:       Issue summary / title.
        description: Full Markdown description (may include environment block).
        issue_type:  "Bug" or "Feature" — maps to the YouTrack Type custom field.
        priority:    YouTrack priority value ("Low", "Normal", "High", "Critical").
                     Optional; omitted for Feature requests.

    Returns:
        dict with keys ``id`` (str) and ``url`` (str) on success, or raises.
    """
    if not _configured():
        raise RuntimeError(
            "YouTrack integration is not configured. "
            "Set YOUTRACK_URL, YOUTRACK_TOKEN, and YOUTRACK_PROJECT_ID."
        )

    custom_fields = [
        {
            "name": "Type",
            "$type": "SingleEnumIssueCustomField",
            "value": {"name": issue_type},
        }
    ]

    if priority:
        custom_fields.append(
            {
                "name": "Priority",
                "$type": "SingleEnumIssueCustomField",
                "value": {"name": priority},
            }
        )

    payload = {
        "project": {"shortName": YOUTRACK_PROJECT_ID},
        "summary": title,
        "description": description,
        "customFields": custom_fields,
    }

    url = f"{YOUTRACK_URL}/api/issues?fields=id,idReadable,url"

    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        issue_id = data.get("idReadable") or data.get("id", "")
        issue_url = data.get("url") or f"{YOUTRACK_URL}/issue/{issue_id}"
        logger.info(f"YouTrack issue created: {issue_id}")
        return {"id": issue_id, "url": issue_url}
    except requests.HTTPError as exc:
        logger.error(f"YouTrack API error {exc.response.status_code}: {exc.response.text}")
        raise RuntimeError(f"YouTrack API returned {exc.response.status_code}") from exc
    except requests.RequestException as exc:
        logger.error(f"YouTrack request failed: {exc}")
        raise RuntimeError("Could not reach YouTrack. Check YOUTRACK_URL.") from exc
