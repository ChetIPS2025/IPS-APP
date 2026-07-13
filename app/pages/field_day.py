"""Unified field day shell — one job, Report | Crew | Time | Tasks tabs."""

from __future__ import annotations

import streamlit as st

from app.auth import current_profile, current_role, effective_role

from app.components.headers import render_page_brand_header
from app.db import fetch_jobs_with_order_fallback
from app.mobile_ui import ensure_narrow_viewport_detected
from app.pages.supervisor_daily_reports import render_daily_reports_for_job
from app.services.job_service import sort_jobs_by_number_then_name
from app.utils.field_context import (
    inject_field_day_shell_css,
    render_field_checkin_block,
    render_field_day_tab_bar,
    render_field_job_bar,
)
from app.utils.permissions import role_can_access_page
def _admin_read() -> bool:
    return effective_role() in {"admin", "manager"}


def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("field_day"):
        return

    ensure_narrow_viewport_detected()
    inject_field_day_shell_css()
    st.markdown(
        '<span class="ips-field-day-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    render_page_brand_header(
        "Today's Work",
        "Pick a job once, then move through report, crew time, hours, and tasks.",
    )

    admin = _admin_read()
    prof = current_profile() or {}
    uid = str(prof.get("id") or "").strip() or None
    uname = str(prof.get("full_name") or prof.get("email") or "").strip()
    role = str(effective_role() or "").strip().lower()

    jobs = sort_jobs_by_number_then_name(
        list(fetch_jobs_with_order_fallback(limit=3000, use_admin=admin) or [])
    )
    if not jobs:
        st.warning("No jobs loaded.")
        return

    jid, label, _job = render_field_job_bar(jobs, key_prefix="fday")
    if not jid:
        return

    tab = render_field_day_tab_bar(key_prefix="fday")

    if tab == "Report":
        def _checkin() -> None:
            render_field_checkin_block(
                job_id=jid,
                user_id=uid,
                user_name=uname,
                admin=admin,
                key_prefix="fday_ci",
            )

        render_daily_reports_for_job(
            job_id=jid,
            job_label=label,
            admin_read=admin,
            show_title=False,
            inline=True,
            wizard=True,
            checkin_block=_checkin,
        )
        return

    if tab == "Crew":
        from app.utils.permissions import can_submit_timekeeping
        if not can_submit_timekeeping(effective_role()):
            st.info(
                "Crew time is entered by your supervisor in **Timekeeping**. "
                "Use the **Time** tab to view your hours."
            )
            return
        st.info("Enter crew hours in **Timekeeping** (Time tab or main Timekeeping module).")
        if st.button("Open Timekeeping", type="primary", key="fday_crew_tk"):
            from app.navigation import navigate_to_timekeeping
            navigate_to_timekeeping(job_id=jid)
            st.rerun()
        return

    if tab == "Time":
        if not role_can_access_page(effective_role(), "timekeeping"):
            st.info("Timekeeping is not available for your role.")
            return
        from app.pages.timekeeping import render_field_time_panel
        render_field_time_panel(key_prefix="fday_tk")
        return

    if tab == "Tasks":
        if not role_can_access_page(effective_role(), "tasks"):
            st.info("Tasks are not available for your role.")
            return
        from app.pages.tasks import render_field_tasks_panel
        render_field_tasks_panel(key_prefix="fday_tasks")
        return
