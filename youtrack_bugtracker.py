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


def get_project_custom_fields() -> list:
    """
    Query the YouTrack project's custom fields to discover exact names and allowed values.
    Returns a list of field dicts with 'name', 'fieldType', and optionally 'bundle' values.
    """
    if not _configured():
        return []

    url = (
        f"{YOUTRACK_URL}/api/admin/projects/{YOUTRACK_PROJECT_ID}/customFields"
        f"?fields=field(name,fieldType(id)),bundle(values(name))"
    )
    try:
        resp = requests.get(url, headers=_headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning(f"Could not fetch YouTrack project custom fields: {exc}")
        return []


def _find_enum_value(fields_data: list, field_name_lower: str, candidates: list) -> str | None:
    """
    Given the project custom fields data, find the first allowed value from `candidates`
    that exists in the bundle for the field whose name matches `field_name_lower` (case-insensitive).
    Returns the exact value string as stored in YouTrack, or None if not found.
    """
    for field in fields_data:
        f = field.get("field", {})
        name = f.get("name", "")
        if name.lower() == field_name_lower:
            bundle = field.get("bundle", {})
            values = bundle.get("values", [])
            allowed = {v["name"].lower(): v["name"] for v in values if "name" in v}
            for candidate in candidates:
                match = allowed.get(candidate.lower())
                if match:
                    return match
    return None


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

    fields_data = get_project_custom_fields()

    if fields_data:
        type_candidates = (
            ["Incident", "Bug"] if issue_type.lower() == "bug"
            else ["Question", "Feature", "Feature Request", "Task", "Story", "Improvement"]
        )
        resolved_type = _find_enum_value(fields_data, "type", type_candidates)
        if resolved_type is None:
            logger.warning(
                f"Could not resolve YouTrack 'Type' value for '{issue_type}'; "
                f"omitting Type field to avoid 400 error."
            )
        else:
            logger.debug(f"Resolved YouTrack Type value: '{resolved_type}'")

        if priority:
            priority_candidates = [priority, "High", "Normal", "Medium", "Low"]
            resolved_priority = _find_enum_value(fields_data, "priority", priority_candidates)
            if resolved_priority is None:
                logger.warning(
                    f"Could not resolve YouTrack 'Priority' value for '{priority}'; "
                    f"omitting Priority field to avoid 400 error."
                )
            else:
                logger.debug(f"Resolved YouTrack Priority value: '{resolved_priority}'")
        else:
            resolved_priority = None

        type_field_name = "Type"
        priority_field_name = "Priority"
        for field in fields_data:
            fname = field.get("field", {}).get("name", "")
            if fname.lower() == "type":
                type_field_name = fname
            elif fname.lower() == "priority":
                priority_field_name = fname
    else:
        resolved_type = None
        resolved_priority = None
        type_field_name = "Type"
        priority_field_name = "Priority"

    custom_fields = []

    if resolved_type:
        custom_fields.append(
            {
                "name": type_field_name,
                "$type": "SingleEnumIssueCustomField",
                "value": {"name": resolved_type},
            }
        )

    if resolved_priority:
        custom_fields.append(
            {
                "name": priority_field_name,
                "$type": "SingleEnumIssueCustomField",
                "value": {"name": resolved_priority},
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
        if not resp.ok:
            yt_body = ""
            try:
                yt_body = resp.json()
            except Exception:
                yt_body = resp.text
            logger.error(
                f"YouTrack API error {resp.status_code}: {yt_body}"
            )
            raise RuntimeError(
                f"YouTrack API returned {resp.status_code}: {yt_body}"
            )
        data = resp.json()
        issue_id = data.get("idReadable") or data.get("id", "")
        issue_url = data.get("url") or f"{YOUTRACK_URL}/issue/{issue_id}"
        logger.info(f"YouTrack issue created: {issue_id}")
        return {"id": issue_id, "url": issue_url}
    except RuntimeError:
        raise
    except requests.RequestException as exc:
        logger.error(f"YouTrack request failed: {exc}")
        raise RuntimeError("Could not reach YouTrack. Check YOUTRACK_URL.") from exc
