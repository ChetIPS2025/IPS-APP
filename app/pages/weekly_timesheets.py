"""Weekly Job Timesheets — legacy route redirects to Job Detail tab."""

from __future__ import annotations

import streamlit as st

from app.navigation import WJT_PREFILL_JOB_KEY, WJT_PREFILL_WEEK_KEY, open_jobs_weekly_timesheets
def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("weekly_timesheets"):
        return

    pre_job = str(st.session_state.pop(WJT_PREFILL_JOB_KEY, "") or "").strip()
    pre_week = str(st.session_state.pop(WJT_PREFILL_WEEK_KEY, "") or "").strip()[:10]
    open_jobs_weekly_timesheets(job_id=pre_job, week_start=pre_week or None)
    st.rerun()
