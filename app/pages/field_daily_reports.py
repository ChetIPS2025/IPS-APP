"""Daily Reports — field supervisor module (crew narrative, photos, site check-in)."""

from __future__ import annotations

import streamlit as st

from app.auth import current_profile, current_role, effective_role

try:
    from app.components.headers import render_page_brand_header
    from app.db import fetch_jobs_with_order_fallback
    from app.mobile_ui import ensure_narrow_viewport_detected
    from app.pages.supervisor_daily_reports import render_daily_reports_for_job
    from app.services.job_service import sort_jobs_by_number_then_name
    from app.utils.field_context import (
        inject_field_day_shell_css,
        navigate_to_field_day,
        render_field_checkin_block,
        render_field_job_bar,
    )
except ImportError:
    from components.headers import render_page_brand_header  # type: ignore
    from db import fetch_jobs_with_order_fallback  # type: ignore
    from mobile_ui import ensure_narrow_viewport_detected  # type: ignore
    from pages.supervisor_daily_reports import render_daily_reports_for_job  # type: ignore
    from services.job_service import sort_jobs_by_number_then_name  # type: ignore
    from utils.field_context import (  # type: ignore
        inject_field_day_shell_css,
        navigate_to_field_day,
        render_field_checkin_block,
        render_field_job_bar,
    )


def _admin_read() -> bool:
    return effective_role() in {"admin", "manager"}


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("field_daily_reports"):
        return

    ensure_narrow_viewport_detected()
    inject_field_day_shell_css()
    st.markdown(
        '<span class="ips-field-daily-reports-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    render_page_brand_header(
        "Daily Report",
        "Field daily reports with crew, photos, safety, and site check-in.",
    )

    admin = _admin_read()
    prof = current_profile() or {}
    uid = str(prof.get("id") or "").strip() or None
    uname = str(prof.get("full_name") or prof.get("email") or "").strip()

    jobs = sort_jobs_by_number_then_name(
        list(fetch_jobs_with_order_fallback(limit=3000, use_admin=admin) or [])
    )
    if not jobs:
        st.warning("No jobs loaded.")
        return

    jid, label, _job = render_field_job_bar(jobs, key_prefix="fdr")
    if not jid:
        return

    st.info("Tip: use **Today's Work** for report, crew time, hours, and tasks on one page.")
    if st.button("Open Today's Work", key="fdr_open_field_day", use_container_width=True):
        navigate_to_field_day(job_id=jid, tab="Report")
        st.rerun()

    def _checkin() -> None:
        render_field_checkin_block(
            job_id=jid,
            user_id=uid,
            user_name=uname,
            admin=admin,
            key_prefix="fdr",
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
