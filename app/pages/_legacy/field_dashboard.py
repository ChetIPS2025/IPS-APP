"""Mobile-first superintendent / field operations dashboard (Phase 1)."""

from __future__ import annotations

from datetime import date

import streamlit as st

from auth import current_profile, current_role

try:
    from app.data_cache import fetch_table_for_session
    from app.db import fetch_jobs_with_order_fallback
    from app.services.field_dashboard import field_dashboard_snapshot
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
    from app.ui import IPS_NAV_PENDING_KEY
    from app.ui.components.badges import render_badge
    from app.ui.components.empty_states import render_empty_state
    from app.ui.components.cards import render_kpi_grid
    from app.ui.page_shell import inject_ips_dashboard_layout, render_page_header
except ImportError:
    from data_cache import fetch_table_for_session  # type: ignore
    from db import fetch_jobs_with_order_fallback  # type: ignore
    from services.field_dashboard import field_dashboard_snapshot  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore
    from ui import IPS_NAV_PENDING_KEY  # type: ignore
    from ui.components.badges import render_badge  # type: ignore
    from ui.components.empty_states import render_empty_state  # type: ignore
    from ui.components.cards import render_kpi_grid  # type: ignore
    from ui.page_shell import inject_ips_dashboard_layout, render_page_header  # type: ignore


def _admin_read() -> bool:
    return current_role() in {"admin", "manager"}


def _nav(page: str) -> None:
    st.session_state[IPS_NAV_PENDING_KEY] = page
    st.rerun()


def render() -> None:
    inject_ips_dashboard_layout()
    render_page_header(
        "Field Dashboard",
        "Today's jobs, missing reports, crew time, and quick field actions.",
    )
    role = current_role()
    if role == "viewer":
        st.warning("View-only access.")
        return

    admin = _admin_read()
    prof = current_profile() or {}
    uid = str(prof.get("id") or "").strip() or None
    today = date.today()

    jobs = sort_jobs_by_number_then_name(
        list(fetch_jobs_with_order_fallback(limit=3000, use_admin=admin) or [])
    )
    time_entries = fetch_table_for_session("time_entries", admin=admin, limit=8000)
    te_today = [
        te
        for te in (time_entries or [])
        if isinstance(te, dict) and str(te.get("work_date") or "")[:10] == today.isoformat()[:10]
    ]
    estimates = {
        str(e.get("id") or ""): e
        for e in (fetch_table_for_session("estimates", admin=admin, limit=3000) or [])
        if isinstance(e, dict) and e.get("id")
    }

    snap = field_dashboard_snapshot(
        today=today,
        jobs=jobs,
        time_entries_today=te_today,
        estimates_by_id=estimates,
        admin=admin,
        user_id=uid,
    )

    render_kpi_grid(
        [
            {"label": "Reports today", "value": str(snap.get("submitted_today", 0))},
            {"label": "Missing reports", "value": str(snap.get("missing_reports", 0))},
            {"label": "Draft reports", "value": str(snap.get("draft_reports_today", 0))},
            {"label": "Awaiting review", "value": str(snap.get("submitted_awaiting_review", 0))},
            {"label": "Jobs w/ delays", "value": str(snap.get("jobs_with_delays", 0))},
            {"label": "Unread alerts", "value": str(snap.get("unread_notifications", 0))},
        ],
        columns=3,
    )

    st.markdown("##### Quick actions")
    q1, q2, q3 = st.columns(3, gap="small")
    with q1:
        if st.button("Daily Report", use_container_width=True, type="primary", key="fd_daily"):
            _nav("Daily Reports")
    with q2:
        if st.button("Crew Time", use_container_width=True, key="fd_time"):
            _nav("Crew Time")
    with q3:
        if st.button("Work & Plan", use_container_width=True, key="fd_plan"):
            _nav("Work & Plan (Supervisor)")

    q4, q5, q6 = st.columns(3, gap="small")
    with q4:
        if st.button("Upload Photo", use_container_width=True, key="fd_photo"):
            _nav("Job Database")
    with q5:
        if st.button("Check In", use_container_width=True, key="fd_checkin"):
            _nav("Daily Reports")
    with q6:
        if st.button("Time Tracking", use_container_width=True, key="fd_tt"):
            _nav("Time Tracking")

    missing_rep = snap.get("missing_sample_labels") or []
    if missing_rep:
        st.markdown("##### Missing daily reports (active jobs)")
        for lbl in missing_rep:
            st.caption(f"• {lbl}")

    missing_time = snap.get("jobs_missing_time_today") or []
    if missing_time:
        st.markdown("##### No time logged today")
        for lbl in missing_time:
            render_badge(str(lbl)[:60], tone="warning")

    over = snap.get("jobs_over_labor") or []
    if over and role in {"admin", "manager"}:
        st.markdown("##### Labor over estimate")
        for _jid, label, est_h, act_h in over[:6]:
            st.caption(f"**{label}** — {act_h:.1f}h actual vs {est_h:.1f}h bid")

    active = [j for j in jobs if isinstance(j, dict)]
    if active:
        st.markdown("##### Today's jobs")
        for j in active[:12]:
            st.caption(job_row_select_label(j))
    else:
        render_empty_state("No jobs loaded.", icon="🏗️")
