"""Mobile-first field supervisor dashboard — today's jobs, reports, and quick actions."""

from __future__ import annotations

from datetime import date

import streamlit as st

from app.auth import current_profile, current_role, effective_role

from app.components.cards import render_kpi_card
from app.components.headers import render_dashboard_quick_actions, render_page_brand_header
from app.data_cache import fetch_table_for_session
from app.db import fetch_jobs_with_order_fallback
from app.mobile_ui import ensure_narrow_viewport_detected
from app.navigation import set_nav_slug
from app.services.field_dashboard import field_dashboard_snapshot
from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
from app.utils.field_context import navigate_to_field_page, navigate_to_field_day, open_job_detail
def _admin_read() -> bool:
    return effective_role() in {"admin", "manager"}


def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("field_dashboard"):
        return

    ensure_narrow_viewport_detected()
    st.markdown(
        '<span class="ips-field-dashboard-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    role = effective_role()
    if role == "viewer":
        st.warning("View-only access.")
        return

    render_page_brand_header(
        "Field Home",
        "Today's jobs, missing reports, crew time, and quick field actions.",
    )

    admin = _admin_read()
    prof = current_profile() or {}
    uid = str(prof.get("id") or "").strip() or None
    session_key = uid or "anonymous"
    today = date.today()

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
        if isinstance(te, dict) and str(te.get("work_date") or "")[:10] == today.isoformat()[:10]
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

    snap = field_dashboard_snapshot(
        today=today,
        jobs=jobs,
        time_entries_today=te_today,
        estimates_by_id=estimates,
        admin=admin,
        user_id=uid,
    )

    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-kpi-grid">', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3)
    k4, k5, k6 = st.columns(3)
    cards = [
        (k1, "Reports today", str(snap.get("submitted_today", 0)), "📝", "#dbeafe"),
        (k2, "Missing reports", str(snap.get("missing_reports", 0)), "⚠️", "#fee2e2"),
        (k3, "Draft reports", str(snap.get("draft_reports_today", 0)), "📋", "#ffedd5"),
        (k4, "Awaiting review", str(snap.get("submitted_awaiting_review", 0)), "👀", "#f3e8ff"),
        (k5, "Jobs w/ delays", str(snap.get("jobs_with_delays", 0)), "⏳", "#fef3c7"),
        (k6, "Unread alerts", str(snap.get("unread_notifications", 0)), "🔔", "#e0f2fe"),
    ]
    for col, title, value, icon, bg in cards:
        with col:
            render_kpi_card(title, value, icon, bg)
    st.markdown(f"</{ot}>", unsafe_allow_html=True)

    quick_actions: list[tuple[str, str, str]] = [
        ("📋", "Today's Work", "field_day"),
        ("📝", "Daily Report", "field_daily_reports"),
        ("👷", "Crew Time", "field_crew_time"),
        ("✅", "Today's Tasks", "tasks"),
        ("⏱", "Log Time", "timekeeping"),
    ]
    if _admin_read() or role in {"supervisor", "manager"}:
        quick_actions.insert(3, ("📦", "Scan Stock", "scan_inventory"))

    render_dashboard_quick_actions(quick_actions, key_prefix="ips_field_dash_qa", title="Field Actions")

    missing_rep = snap.get("missing_sample_jobs") or []
    if missing_rep:
        st.markdown("##### Missing daily reports (active jobs)")
        for item in missing_rep:
            jid = str(item.get("id") or "").strip()
            lbl = str(item.get("label") or "Job").strip()
            if jid and st.button(lbl, key=f"field_missing_rep_{jid}", use_container_width=True):
                navigate_to_field_day(job_id=jid, tab="Report")
                st.rerun()
    elif snap.get("missing_sample_labels"):
        st.markdown("##### Missing daily reports (active jobs)")
        for lbl in snap.get("missing_sample_labels") or []:
            st.caption(f"• {lbl}")

    missing_time = snap.get("jobs_missing_time_today") or []
    if missing_time:
        st.markdown("##### No time logged today")
        for lbl in missing_time:
            st.caption(f"• {lbl}")

    over = snap.get("jobs_over_labor") or []
    if over and role in {"admin", "manager"}:
        st.markdown("##### Labor over estimate")
        for _jid, label, est_h, act_h in over[:6]:
            st.caption(f"**{label}** — {act_h:.1f}h actual vs {est_h:.1f}h bid")

    active = [j for j in jobs if isinstance(j, dict)]
    if active:
        st.markdown("##### Today's jobs")
        for j in active[:12]:
            label = job_row_select_label(j)
            if st.button(label, key=f"field_dash_job_{j.get('id')}", use_container_width=True):
                open_job_detail(str(j.get("id") or ""))
                st.rerun()
    else:
        st.info("No jobs loaded.")
