"""Superintendent / field dashboard aggregates."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.services.supervisor_daily_reports import (
    dashboard_daily_report_snapshot,
    fetch_all_reports_since,
    job_status_needs_daily_report,
    labor_hours_actual_by_job_on_date,
)
from app.services.field_ops_util import fetch_fn, table_exists


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
            from app.services.job_service import job_row_select_label
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


def load_field_dashboard_snapshot(*, today: date | None = None) -> dict[str, Any]:
    """Load field dashboard KPIs for header badges and lightweight widgets."""
    from app.auth import current_profile, effective_role
    from app.data_cache import fetch_table_for_session
    from app.db import fetch_jobs_with_order_fallback
    from app.services.job_service import sort_jobs_by_number_then_name

    admin = effective_role() in {"admin", "manager"}
    prof = current_profile() or {}
    uid = str(prof.get("id") or "").strip() or None
    session_key = uid or "anonymous"
    work_date = today or date.today()

    jobs = sort_jobs_by_number_then_name(
        list(fetch_jobs_with_order_fallback(limit=3000, use_admin=admin) or [])
    )
    time_entries = fetch_table_for_session(
        "time_entries",
        session_key=session_key,
        use_admin=admin,
        limit=8000,
    )
    te_today = [
        te
        for te in (time_entries or [])
        if isinstance(te, dict) and str(te.get("work_date") or "")[:10] == work_date.isoformat()[:10]
    ]
    estimates = {
        str(e.get("id") or ""): e
        for e in (
            fetch_table_for_session(
                "estimates",
                session_key=session_key,
                use_admin=admin,
                limit=3000,
            )
            or []
        )
        if isinstance(e, dict) and e.get("id")
    }

    return field_dashboard_snapshot(
        today=work_date,
        jobs=jobs,
        time_entries_today=te_today,
        estimates_by_id=estimates,
        admin=admin,
        user_id=uid,
    )
