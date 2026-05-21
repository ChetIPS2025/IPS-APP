"""Daily Reports — field supervisor module (wraps supervisor daily reports + check-in)."""

from __future__ import annotations

import streamlit as st

from auth import current_profile, current_role

try:
    from app.db import fetch_jobs_with_order_fallback
    from app.pages.supervisor_daily_reports import render_daily_reports_for_job
    from app.services.job_checkins import check_in, check_out, fetch_open_checkin
    from app.services.job_service import job_row_select_label, sort_jobs_by_number_then_name
    from app.ui.page_shell import inject_ips_dashboard_layout, render_page_header
except ImportError:
    from db import fetch_jobs_with_order_fallback  # type: ignore
    from pages.supervisor_daily_reports import render_daily_reports_for_job  # type: ignore
    from services.job_checkins import check_in, check_out, fetch_open_checkin  # type: ignore
    from services.job_service import job_row_select_label, sort_jobs_by_number_then_name  # type: ignore
    from ui.page_shell import inject_ips_dashboard_layout, render_page_header  # type: ignore


def _admin_read() -> bool:
    return current_role() in {"admin", "manager"}


def render() -> None:
    inject_ips_dashboard_layout()
    render_page_header(
        "Daily Reports",
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
    labels = [job_row_select_label(j) for j in jobs]
    ids = [str(j.get("id")) for j in jobs]
    ix = st.selectbox("Job", range(len(ids)), format_func=lambda i: labels[i], key="fdr_job_ix")
    jid = ids[int(ix)]
    label = labels[int(ix)]

    with st.expander("Site check-in / check-out", expanded=False):
        open_ci = fetch_open_checkin(job_id=jid, user_id=uid, admin=admin)
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

    render_daily_reports_for_job(job_id=jid, job_label=label, admin_read=admin, show_title=False)
