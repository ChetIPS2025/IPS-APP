"""Canonical status normalization and cross-module open/closed rules."""

from __future__ import annotations

import re
from typing import Any

from app.services.jobs_service import normalize_job_status
from app.utils.constants import ASSET_STATUSES, ESTIMATE_STATUSES, JOB_STATUSES, TASK_STATUSES
__all__ = [
    "ASSET_STATUSES",
    "ESTIMATE_STATUSES",
    "JOB_STATUSES",
    "TASK_STATUSES",
    "is_estimate_open_for_customer_count",
    "is_job_open_for_customer_count",
    "normalize_asset_status",
    "normalize_task_status",
    "normalize_task_status_label",
    "task_priority_to_db",
    "task_status_filter_bucket",
    "task_status_to_db",
]

_EMOJI_PREFIX = re.compile(
    r"^[\U0001F300-\U0001FAFF\U00002600-\U000027BF\u2705\u2B50\uFE0F?\s]+"
)

_TASK_CLOSED_ALIASES = frozenset({"done", "complete", "completed", "closed"})
_TASK_LABEL_MAP = {
    "open": "Open",
    "in progress": "In Progress",
    "in_progress": "In Progress",
    "blocked": "Blocked",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "done": "Complete",
    "complete": "Complete",
    "completed": "Complete",
    "closed": "Complete",
}

_CLOSED_JOB_LABELS = frozenset({"Completed", "Cancelled", "Archived", "Deleted"})


def _strip_emoji(value: object) -> str:
    raw = str(value or "").strip()
    cleaned = _EMOJI_PREFIX.sub("", raw).strip()
    return cleaned or raw


def is_job_open_for_customer_count(job: dict[str, Any]) -> bool:
    """Match Jobs list semantics: open = not completed/cancelled/archived/deleted."""
    if bool(job.get("is_deleted")):
        return False
    return normalize_job_status(job.get("status")) not in _CLOSED_JOB_LABELS


def is_estimate_open_for_customer_count(est: dict[str, Any]) -> bool:
    """Match Estimates active view — same rows as 'Active Estimates' filter."""
    from app.services.estimate_job_workflow_service import estimate_visible_in_active_view
    return estimate_visible_in_active_view(est)


def normalize_task_status_label(value: object) -> str:
    """Canonical task status label for display and DB (Open, In Progress, Blocked, Complete, Cancelled)."""
    cleaned = _strip_emoji(value)
    if not cleaned:
        return "Open"
    key = cleaned.lower().replace("_", " ")
    if key in _TASK_LABEL_MAP:
        return _TASK_LABEL_MAP[key]
    if cleaned in TASK_STATUSES:
        return cleaned
    return cleaned.title() if cleaned else "Open"


def task_status_filter_bucket(value: object) -> str:
    """Binary Open/Closed bucket for list filters."""
    label = normalize_task_status_label(value)
    if label in {"Complete", "Cancelled"}:
        return "Closed"
    return "Open"


def normalize_task_status(value: object) -> str:
    """Backward-compatible alias for task Open/Closed filter bucket."""
    return task_status_filter_bucket(value)


def task_status_to_db(value: object) -> str:
    label = normalize_task_status_label(value)
    if label == "Complete":
        return "Complete"
    if label == "Cancelled":
        return "Cancelled"
    if label == "In Progress":
        return "In Progress"
    if label == "Blocked":
        return "Blocked"
    return "Open"


def task_priority_to_db(value: object) -> str:
    cleaned = _strip_emoji(value)
    if not cleaned:
        return "Normal"
    key = cleaned.lower()
    if key in {"high", "urgent"}:
        return "High"
    if key == "low":
        return "Low"
    if key in {"medium", "normal"}:
        return "Normal"
    return cleaned if cleaned in {"High", "Low", "Normal", "Urgent"} else "Normal"


def normalize_asset_status(raw: object) -> str:
    """Canonical asset status labels used on the Assets page."""
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "Available",
        "available": "Available",
        "in service": "In Service",
        "in_service": "In Service",
        "assigned": "Assigned",
        "out for repair": "Out for Repair",
        "repair": "Out for Repair",
        "maintenance due": "Maintenance Due",
        "maintenance_due": "Maintenance Due",
        "maintenance": "Maintenance Due",
        "retired": "Retired",
        "sold": "Sold",
        "lost": "Lost",
        "checked out": "Checked Out",
        "checked_out": "Checked Out",
        "active": "In Service",
        "overdue": "Overdue",
        "down": "Down",
        "out of service": "Out of Service",
        "disposed": "Retired",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    if label in ASSET_STATUSES:
        return label
    return label if label else "Available"
