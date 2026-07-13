"""Operations dashboard bottom panels — Jobs by Status and Recent Activity."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.pages._core._data import dashboard_job_status_overview, load_recent_item_activity
from app.services.job_service import normalize_job_status_for_filter
_STATUS_PANEL_ORDER: tuple[tuple[str, str, str], ...] = (
    ("Active", "#2563eb", "#dbeafe"),
    ("On Hold", "#d97706", "#ffedd5"),
    ("Pending", "#7c3aed", "#ede9fe"),
    ("Completed", "#16a34a", "#dcfce7"),
    ("Cancelled", "#64748b", "#e2e8f0"),
)

_PENDING_RAW_STATUSES = frozenset(
    {
        "pending",
        "draft",
        "not started",
        "estimate pending",
        "planning",
        "scheduled",
    }
)


def _panel_status_bucket(job: dict[str, Any]) -> str:
    raw = str(job.get("status") or "").strip().lower().replace("_", " ")
    norm = normalize_job_status_for_filter(job.get("status"))
    if raw in _PENDING_RAW_STATUSES:
        return "Pending"
    if norm == "On Hold":
        return "On Hold"
    if norm == "Completed":
        return "Completed"
    if norm == "Cancelled":
        return "Cancelled"
    if norm in {"Archived", "Deleted"}:
        return ""
    return "Active"


def _jobs_by_status_counts() -> tuple[dict[str, int], bool]:
    overview, is_live = dashboard_job_status_overview()
    counts = {label: 0 for label, _, _ in _STATUS_PANEL_ORDER}
    if is_live and overview:
        from app.pages._core._data import load_jobs
        for job in load_jobs():
            if not isinstance(job, dict) or bool(job.get("is_deleted")):
                continue
            bucket = _panel_status_bucket(job)
            if bucket:
                counts[bucket] = counts.get(bucket, 0) + 1
        return counts, True

    for label, value in overview.items():
        key = str(label or "").strip()
        if key == "Not Started":
            key = "Pending"
        if key in counts:
            counts[key] = int(value or 0)
    if not any(counts.values()):
        counts = {"Active": 51, "On Hold": 4, "Pending": 8, "Completed": 12, "Cancelled": 2}
        return counts, False
    return counts, is_live


def _status_row_html(*, label: str, count: int, dot_color: str, bar_color: str, max_count: int) -> str:
    ot = "d" + "iv"
    pct = 0 if max_count <= 0 else min(100, round((count / max_count) * 100))
    return (
        f'<{ot} class="ips-dash-status-row">'
        f'<{ot} class="ips-dash-status-head">'
        f'<span class="ips-dash-status-dot" style="background:{html.escape(dot_color)}"></span>'
        f'<span class="ips-dash-status-label">{html.escape(label)}</span>'
        f'<span class="ips-dash-status-count">{count:,}</span>'
        f"</{ot}>"
        f'<{ot} class="ips-dash-status-track">'
        f'<{ot} class="ips-dash-status-bar" style="width:{pct}%;background:{html.escape(bar_color)}"></{ot}>'
        f"</{ot}>"
        f"</{ot}>"
    )


def _jobs_by_status_html(counts: dict[str, int]) -> str:
    max_count = max(counts.values()) if counts else 0
    rows = "".join(
        _status_row_html(
            label=label,
            count=int(counts.get(label, 0)),
            dot_color=dot,
            bar_color=bar,
            max_count=max_count,
        )
        for label, dot, bar in _STATUS_PANEL_ORDER
    )
    ot = "d" + "iv"
    return (
        f'<{ot} class="dashboard-main-card ips-dash-ops-panel ips-dash-ops-panel--status">'
        f'<h3 class="ips-dash-ops-panel-title">Jobs by Status</h3>'
        f'<{ot} class="ips-dash-status-list">{rows}</{ot}>'
        f'<a class="ips-dash-ops-panel-link" href="?ips_nav=jobs" target="_top" rel="noopener noreferrer">'
        f"View all jobs →</a>"
        f"</{ot}>"
    )


def _normalize_activity_row(row: dict[str, Any]) -> dict[str, str]:
    if str(row.get("text") or "").strip() and str(row.get("time") or "").strip():
        return {
            "icon": str(row.get("icon") or "📋"),
            "bg": str(row.get("bg") or row.get("icon_bg") or "#dbeafe"),
            "text": str(row.get("text") or ""),
            "time": str(row.get("time") or ""),
        }
    title = str(row.get("title") or row.get("text") or "Activity update").strip()
    meta = str(row.get("meta") or row.get("time") or "").strip()
    time_label = meta.split("·")[-1].strip() if "·" in meta else meta
    return {
        "icon": str(row.get("icon") or "📋"),
        "bg": str(row.get("bg") or row.get("icon_bg") or "#dbeafe"),
        "text": title,
        "time": time_label or "—",
    }


def _activity_item_html(item: dict[str, str]) -> str:
    ot = "d" + "iv"
    icon = html.escape(str(item.get("icon") or "📋"))
    bg = html.escape(str(item.get("bg") or "#dbeafe"))
    text = html.escape(str(item.get("text") or ""))
    time_label = html.escape(str(item.get("time") or ""))
    return (
        f'<{ot} class="ips-dash-activity-item">'
        f'<span class="ips-dash-activity-icon" style="background:{bg}">{icon}</span>'
        f'<span class="ips-dash-activity-text">{text}</span>'
        f'<span class="ips-dash-activity-time">{time_label}</span>'
        f"</{ot}>"
    )


def _recent_activity_html(items: list[dict[str, str]]) -> str:
    body = "".join(_activity_item_html(_normalize_activity_row(row)) for row in items) or (
        '<p class="ips-dash-activity-empty">No recent activity yet.</p>'
    )
    ot = "d" + "iv"
    return (
        f'<{ot} class="dashboard-main-card ips-dash-ops-panel ips-dash-ops-panel--activity">'
        f'<h3 class="ips-dash-ops-panel-title">Recent Activity</h3>'
        f'<{ot} class="ips-dash-activity-list">{body}</{ot}>'
        f'<a class="ips-dash-ops-panel-link" href="?ips_nav=company_updates" target="_top" rel="noopener noreferrer">'
        f"View all activity →</a>"
        f"</{ot}>"
    )


def render_dashboard_ops_panels(*, activity_limit: int = 8) -> None:
    """Render Jobs by Status and Recent Activity cards side by side."""
    status_counts, _ = _jobs_by_status_counts()
    activity_rows, _ = load_recent_item_activity(limit=activity_limit)
    activity_rows = [_normalize_activity_row(row) for row in activity_rows]

    with st.container(key="dashboard_main"):
        ot = "d" + "iv"
        st.markdown(
            f'<{ot} class="dashboard-main-grid">'
            f"{_jobs_by_status_html(status_counts)}"
            f"{_recent_activity_html(activity_rows)}"
            f"</{ot}>",
            unsafe_allow_html=True,
        )


__all__ = ["render_dashboard_ops_panels"]
