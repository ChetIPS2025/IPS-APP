"""Daily Reports — field supervisor module (crew narrative, photos, site check-in)."""

from __future__ import annotations

import streamlit as st

from auth import current_profile, current_role

try:
    from app.components.headers import render_page_brand_header
    from app.db import fetch_jobs_with_order_fallback
    from app.mobile_ui import ensure_narrow_viewport_detected
    from app.pages.supervisor_daily_reports import render_daily_reports_for_job
    from app.services.job_checkins import check_in, check_out, fetch_open_checkin
    from app.services.job_service import sort_jobs_by_number_then_name
    from app.utils.field_context import render_field_job_bar
except ImportError:
    from components.headers import render_page_brand_header  # type: ignore
    from db import fetch_jobs_with_order_fallback  # type: ignore
    from mobile_ui import ensure_narrow_viewport_detected  # type: ignore
    from pages.supervisor_daily_reports import render_daily_reports_for_job  # type: ignore
    from services.job_checkins import check_in, check_out, fetch_open_checkin  # type: ignore
    from services.job_service import sort_jobs_by_number_then_name  # type: ignore
    from utils.field_context import render_field_job_bar  # type: ignore


def _admin_read() -> bool:
    return current_role() in {"admin", "manager"}


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("field_daily_reports"):
        return

    ensure_narrow_viewport_detected()
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

    open_ci = fetch_open_checkin(job_id=jid, user_id=uid, admin=admin)
    with st.expander("Site check-in / check-out", expanded=open_ci is None):
        if open_ci:
            st.success(f"Checked in since {str(open_ci.get('check_in_time') or '')[:16]}")
            note_out = st.text_input("Check-out note", key="fdr_co_note")
            if st.button("Check out", type="primary", key="fdr_checkout"):
                try:
                    check_out(checkin_id=str(open_ci["id"]), notes=note_out, admin=admin)
                    st.success("Checked out.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            note_in = st.text_input("Check-in note (GPS optional later)", key="fdr_ci_note")
            if st.button("Check in on site", type="primary", key="fdr_checkin"):
                try:
                    check_in(
                        job_id=jid,
                        user_id=uid,
                        user_name=uname,
                        notes=note_in,
                        admin=admin,
                    )
                    st.success("Checked in.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    render_daily_reports_for_job(
        job_id=jid,
        job_label=label,
        admin_read=admin,
        show_title=False,
        inline=True,
        expand_sections=True,
    )
