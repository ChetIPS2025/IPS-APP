"""Superintendent / field dashboard aggregates."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

try:
    from app.services.supervisor_daily_reports import (
        dashboard_daily_report_snapshot,
        fetch_all_reports_since,
        job_status_needs_daily_report,
        labor_hours_actual_by_job_on_date,
    )
except ImportError:
    from services.supervisor_daily_reports import (  # type: ignore
        dashboard_daily_report_snapshot,
        fetch_all_reports_since,
        job_status_needs_daily_report,
        labor_hours_actual_by_job_on_date,
    )

from services.field_ops_util import fetch_fn, table_exists


def field_dashboard_snapshot(
    *,
    today: date,
    jobs: list[dict[str, Any]],
    time_entries_today: list[dict[str, Any]],
    estimates_by_id: dict[str, dict[str, Any]],
    admin: bool = False,
    user_id: str | None = None,
) -> dict[str, Any]:
    """KPIs for the mobile-first field dashboard."""
    since = today - timedelta(days=14)
    reports_recent = fetch_all_reports_since(since, admin=admin, limit=2000)
    reports_today = [
        r
        for r in reports_recent
        if isinstance(r, dict) and str(r.get("report_date") or "")[:10] == today.isoformat()[:10]
    ]
    hours_by_job = labor_hours_actual_by_job_on_date(time_entries_today, work_date=today)
    dr = dashboard_daily_report_snapshot(
        today=today,
        jobs=jobs,
        reports_today=reports_today,
        reports_recent=reports_recent,
        hours_by_job=hours_by_job,
        estimates_by_id=estimates_by_id,
    )

    pending_co = 0
    open_checkins = 0
    unread_notifications = 0

    if table_exists("notifications", admin=admin) and user_id:
        fn = fetch_fn(admin=admin)
        notes = fn("notifications", {"user_id": str(user_id).strip()}, limit=200)
        unread_notifications = sum(1 for n in (notes or []) if isinstance(n, dict) and not n.get("read_at"))

    active_jobs = [j for j in (jobs or []) if isinstance(j, dict) and job_status_needs_daily_report(j.get("status"))]
    jobs_missing_time: list[str] = []
    for j in active_jobs[:30]:
        jid = str(j.get("id") or "").strip()
        if jid and float(hours_by_job.get(jid, 0.0)) <= 0.01:
            try:
                from app.services.job_service import job_row_select_label
            except ImportError:
                from services.job_service import job_row_select_label  # type: ignore
            jobs_missing_time.append(job_row_select_label(j))

    drafts_today = sum(
        1
        for r in reports_today
        if isinstance(r, dict) and str(r.get("status") or "Draft").strip() == "Draft"
    )
    submitted_not_reviewed = sum(
        1
        for r in reports_today
        if isinstance(r, dict) and str(r.get("status") or "").strip() == "Submitted"
    )

    return {
        **dr,
        "draft_reports_today": drafts_today,
        "submitted_awaiting_review": submitted_not_reviewed,
        "jobs_missing_time_today": jobs_missing_time[:8],
        "pending_change_orders": pending_co,
        "open_checkins": open_checkins,
        "unread_notifications": unread_notifications,
        "active_job_count": len(active_jobs),
    }
