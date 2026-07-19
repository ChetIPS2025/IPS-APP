"""Job detail Schedule tab and related scheduling UI helpers."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import streamlit as st

from app.components.scheduling_dialogs import SCHED_PREFILL_JOB_KEY, open_new_schedule_dialog
from app.navigation import set_nav_slug
from app.services.scheduling_conflicts import parse_dt
from app.services.scheduling_service import (
    enrich_events,
    list_event_assets,
    list_event_employees,
    list_job_schedule,
)
from app.ui.streamlit_perf import ips_app_rerun
from app.utils.formatting import fmt_date


def _can_manage_scheduling() -> bool:
    from app.auth import effective_role
    from app.utils.permissions import normalize_role

    return normalize_role(effective_role()) in {"admin", "supervisor", "project manager"}


def _event_bucket(ev: dict[str, Any], *, today: date) -> str:
    start = parse_dt(ev.get("start_at"))
    if not start:
        return "upcoming"
    if str(ev.get("status") or "").strip().lower() in {"completed", "cancelled"}:
        return "past"
    return "upcoming" if start.date() >= today else "past"


def render_job_schedule_tab(
    job: dict[str, Any],
    *,
    jobs_by_id: dict[str, dict[str, Any]] | None = None,
    employees_by_id: dict[str, dict[str, Any]] | None = None,
    customers_by_id: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Schedule tab inside Job Details."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        st.caption("Save this job before viewing schedule events.")
        return

    if _can_manage_scheduling():
        if st.button("+ Schedule This Job", key=f"job_sched_add_{jid}", type="primary"):
            st.session_state[SCHED_PREFILL_JOB_KEY] = jid
            open_new_schedule_dialog(job_id=jid)
            set_nav_slug("scheduling")
            ips_app_rerun()

    events = list_job_schedule(jid)
    if not events:
        st.caption("No schedule events for this job yet.")
        st.markdown(
            f"**Planned dates:** {fmt_date(job.get('start_date'))} – {fmt_date(job.get('end_date'))}"
        )
        return

    jobs_map = jobs_by_id or {jid: job}
    emp_map = employees_by_id or {}
    events = enrich_events(
        events,
        jobs_by_id=jobs_map,
        employees_by_id=emp_map,
        customers_by_id=customers_by_id or {},
    )

    today = date.today()
    upcoming = [e for e in events if _event_bucket(e, today=today) == "upcoming"]
    past = [e for e in events if _event_bucket(e, today=today) == "past"]

    total_hours = 0.0
    for ev in events:
        s, e = parse_dt(ev.get("start_at")), parse_dt(ev.get("end_at"))
        if s and e:
            total_hours += max(0.0, (e - s).total_seconds() / 3600.0)

    st.markdown(f"**Planned labor hours (scheduled):** {total_hours:.1f}")

    if upcoming:
        st.markdown("#### Upcoming")
        for ev in upcoming:
            _render_job_schedule_event_row(ev, employees_by_id=emp_map)

    if past:
        st.markdown("#### Past")
        for ev in past:
            _render_job_schedule_event_row(ev, employees_by_id=emp_map)


def _render_job_schedule_event_row(
    ev: dict[str, Any],
    *,
    employees_by_id: dict[str, dict[str, Any]],
) -> None:
    eid = str(ev.get("id") or "").strip()
    title = str(ev.get("title") or "Event")
    when = f"{str(ev.get('start_at') or '')[:16]} → {str(ev.get('end_at') or '')[:16]}"
    status = str(ev.get("status") or "—").replace("_", " ").title()
    supervisor = str(ev.get("supervisor_name") or "—")
    crew = list_event_employees(eid) if eid else []
    assets = list_event_assets(eid) if eid else []
    crew_names = []
    for row in crew:
        emp = employees_by_id.get(str(row.get("employee_id") or "")) or {}
        crew_names.append(str(emp.get("full_name") or emp.get("employee_name") or emp.get("name") or "—"))

    st.markdown(f"**{title}** · {status}")
    st.caption(f"{when} · {ev.get('location') or '—'} · Supervisor: {supervisor}")
    if crew_names:
        st.caption(f"Crew: {', '.join(crew_names)}")
    if assets:
        st.caption(f"Equipment assignments: {len(assets)}")
