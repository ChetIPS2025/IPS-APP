"""Weekly Job Timesheets — builder and export."""

from __future__ import annotations

import streamlit as st

try:
    from app.components.headers import render_page_brand_header
    from app.components.weekly_timesheet_builder import render_weekly_timesheet_builder
    from app.services.job_service import weekly_timesheet_job_options
except ImportError:
    from components.headers import render_page_brand_header  # type: ignore
    from components.weekly_timesheet_builder import render_weekly_timesheet_builder  # type: ignore
    from services.job_service import weekly_timesheet_job_options  # type: ignore


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
        "Build and export customer-facing weekly job timesheets from approved Timekeeping hours.",
    )

    pre_job = str(st.session_state.pop("wjt_prefill_job_id", "") or "").strip()
    pre_week_raw = str(st.session_state.pop("wjt_prefill_week_start", "") or "").strip()[:10]
    pre_week = None
    if pre_week_raw:
        try:
            from datetime import date

            pre_week = date.fromisoformat(pre_week_raw)
        except ValueError:
            pre_week = None
    render_weekly_timesheet_builder(
        job_options=weekly_timesheet_job_options(),
        default_job_id=pre_job,
        default_week_start=pre_week,
        key_prefix="wjt",
    )
