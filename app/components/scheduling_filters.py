"""Scheduling filter controls with lightweight option lists."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.perf_debug import perf_span
from app.services.scheduling_reference_service import (
    list_schedule_job_filter_options,
    list_schedule_supervisor_filter_options,
)

_FILTERS_KEY = "scheduling_filters"
_SHOW_UNASSIGNED_KEY = "scheduling_show_unassigned"


def render_scheduling_filters(*, filters_key: str = _FILTERS_KEY) -> dict[str, str]:
    filt = dict(st.session_state.get(filters_key) or {})
    with perf_span("scheduling.filters"):
        job_options = list_schedule_job_filter_options()
        supervisor_options = list_schedule_supervisor_filter_options()

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            job_opts = ["All"] + [opt["id"] for opt in job_options]
            job_labels = {opt["id"]: opt["label"] for opt in job_options}
            job_pick = st.selectbox(
                "Job",
                job_opts,
                index=job_opts.index(filt.get("job_id")) if filt.get("job_id") in job_opts else 0,
                format_func=lambda x: "All jobs" if x == "All" else job_labels.get(x, x),
                key="sched_filter_job",
            )
            filt["job_id"] = "" if job_pick == "All" else job_pick
        with c2:
            sup_opts = ["All"] + [opt["id"] for opt in supervisor_options]
            sup_labels = {opt["id"]: opt["label"] for opt in supervisor_options}
            sup_pick = st.selectbox(
                "Supervisor",
                sup_opts,
                index=sup_opts.index(filt.get("supervisor_id")) if filt.get("supervisor_id") in sup_opts else 0,
                format_func=lambda x: "All supervisors" if x == "All" else sup_labels.get(x, x),
                key="sched_filter_supervisor",
            )
            filt["supervisor_id"] = "" if sup_pick == "All" else sup_pick
        with c3:
            status_opts = ["All statuses", "tentative", "confirmed", "in_progress", "completed", "cancelled"]
            cur_status = str(filt.get("status") or "All statuses")
            filt["status"] = st.selectbox(
                "Status",
                status_opts,
                index=status_opts.index(cur_status) if cur_status in status_opts else 0,
                key="sched_filter_status",
            )
        with c4:
            st.session_state[_SHOW_UNASSIGNED_KEY] = st.checkbox(
                "Show Unassigned Employees",
                value=bool(st.session_state.get(_SHOW_UNASSIGNED_KEY)),
                key="sched_filter_unassigned",
            )
    st.session_state[filters_key] = filt
    return filt


def show_unassigned_enabled() -> bool:
    return bool(st.session_state.get(_SHOW_UNASSIGNED_KEY))
