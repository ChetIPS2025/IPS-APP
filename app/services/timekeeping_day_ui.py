"""Pure helpers for timekeeping day allocation + approval UI state."""

from __future__ import annotations

import html

_TIMECARD_STATUS_LABELS = {
    "draft": "Draft",
    "pending": "Pending",
    "approved": "Approved",
    "rejected": "Rejected",
}


def normalize_timecard_status(raw: object) -> str:
    key = str(raw or "Draft").strip().lower().replace("_", " ")
    return _TIMECARD_STATUS_LABELS.get(key, str(raw or "Draft").strip() or "Draft")


def day_fully_approved_and_allocated(alloc_state: str, day_status: str) -> bool:
    """True only when every hour is allocated and the day is approved."""
    return (
        normalize_timecard_status(day_status) == "Approved"
        and str(alloc_state or "").strip() == "complete"
    )


def top_row_day_marker_classes(alloc_state: str) -> str:
    state = str(alloc_state or "").strip()
    if state == "complete":
        return " ips-time-week-day-filled ips-time-week-day-alloc-complete"
    if state == "overallocated":
        return " ips-time-week-day-alloc-over"
    if state in {"incomplete", "needs_assignment"}:
        return " ips-time-week-day-alloc-warn"
    return ""


def day_approval_marker_class(
    day_status: str,
    *,
    has_hours: bool,
    alloc_state: str = "",
) -> str:
    if day_fully_approved_and_allocated(alloc_state, day_status):
        return " ips-tk-day-approved-complete"
    norm = normalize_timecard_status(day_status)
    if norm == "Approved":
        return " ips-tk-day-approved"
    if norm == "Rejected":
        return " ips-tk-day-rejected"
    if norm == "Pending":
        return " ips-tk-day-pending"
    if has_hours:
        return " ips-tk-day-draft"
    return " ips-tk-day-draft-empty"


def list_day_box_marker_classes(
    *,
    day_status: str,
    alloc_state: str,
    has_hours: bool,
) -> str:
    approval_cls = day_approval_marker_class(
        day_status,
        has_hours=has_hours,
        alloc_state=alloc_state,
    )
    norm = normalize_timecard_status(day_status)
    if norm in ("Approved", "Rejected", "Pending"):
        return approval_cls
    return approval_cls + top_row_day_marker_classes(alloc_state)


def list_day_status_badge_html(day_status: str, alloc_state: str) -> str:
    if day_fully_approved_and_allocated(alloc_state, day_status):
        return (
            '<span class="ips-timekeeping-status-pill ips-timekeeping-status-approved '
            'ips-timekeeping-status-pill-day-box">APPROVED</span>'
        )
    norm = normalize_timecard_status(day_status)
    return html.escape(norm.upper())
