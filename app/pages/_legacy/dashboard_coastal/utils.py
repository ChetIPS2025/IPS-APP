"""Dashboard shared helpers and session state keys."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

STATE_DATE_START = "dashboard_date_start"
STATE_DATE_END = "dashboard_date_end"
STATE_FILTER_COMPANY = "dashboard_filter_company"
STATE_FILTER_JOB_STATUS = "dashboard_filter_job_status"
STATE_SELECTED_METRIC = "dashboard_selected_metric"
STATE_VIEW_MODE = "dashboard_view_mode"

_TERMINAL_JOB_STATUSES = frozenset(
    {"closed", "complete", "completed", "cancelled", "canceled"}
)


def norm_status(v: Any) -> str:
    return " ".join(str(v or "").strip().split()).casefold()


def row_ts(row: dict) -> str:
    for k in ("updated_at", "modified_at", "created_at"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def recent_rows(rows: list[dict], *, limit: int = 12) -> list[dict]:
    if not rows:
        return []
    return sorted(rows, key=row_ts, reverse=True)[:limit]


def dash_kf(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        s = str(v).strip()
        if not s:
            return default
        return float(s)
    except Exception:
        return default


def is_open_job(job: dict) -> bool:
    return norm_status((job or {}).get("status")) not in _TERMINAL_JOB_STATUSES


def is_pending_estimate(est: dict) -> bool:
    return not str((est or {}).get("job_id") or "").strip()


def job_status_bucket(status_value: Any) -> str | None:
    s = norm_status(status_value)
    if not s:
        return None
    awarded = {"awarded", "won", "active"}
    bidding = {
        "bidding", "estimating", "proposal", "quoted", "draft", "submitted",
        "approved", "scheduled", "in progress", "on hold",
    }
    if s in awarded or any(t in s for t in awarded):
        return "awarded"
    if s in bidding or any(t in s for t in bidding):
        return "bidding"
    return None
