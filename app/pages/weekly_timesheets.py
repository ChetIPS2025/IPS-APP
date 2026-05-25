"""Weekly Job Timesheets — builder and export."""

from __future__ import annotations

from datetime import date

import streamlit as st

try:
    from app.components.headers import render_page_brand_header
    from app.components.weekly_timesheet_builder import render_weekly_timesheet_builder
    from app.pages._core._data import load_jobs
    from app.services.job_service import job_row_select_label
except ImportError:
    from components.headers import render_page_brand_header  # type: ignore
    from components.weekly_timesheet_builder import render_weekly_timesheet_builder  # type: ignore
    from pages._core._data import load_jobs  # type: ignore
    from services.job_service import job_row_select_label  # type: ignore


def _job_options() -> dict[str, str]:
    opts: dict[str, str] = {"": ""}
    for job in load_jobs():
        jid = str(job.get("id") or "").strip()
        if not jid:
            continue
        label = job_row_select_label(job)
        cust = str(job.get("customer") or "").strip()
        opts[f"{label} | {cust}" if cust else label] = jid
    return opts


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("weekly_timesheets"):
        return

    st.markdown('<span class="ips-weekly-timesheets-page ips-page-shell-marker" aria-hidden="true"></span>', unsafe_allow_html=True)

    render_page_brand_header(
        "Weekly Timesheets",
        "Build customer-facing weekly job timesheets from timekeeping, materials, and notes.",
    )

    pre_job = str(st.session_state.pop("wjt_prefill_job_id", "") or "").strip()
    render_weekly_timesheet_builder(job_options=_job_options(), default_job_id=pre_job, key_prefix="wjt")
