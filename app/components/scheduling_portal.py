"""Employee-facing upcoming schedule cards."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.services.scheduling_service import enrich_events, list_upcoming_employee_schedule
from app.utils.formatting import fmt_date


def render_employee_upcoming_schedule(
    employee_id: str,
    *,
    employees_by_id: dict[str, dict[str, Any]] | None = None,
    jobs_by_id: dict[str, dict[str, Any]] | None = None,
    limit: int = 4,
) -> None:
    """Next assignments for the employee dashboard (no internal notes)."""
    eid = str(employee_id or "").strip()
    if not eid:
        return

    st.markdown('<h3 class="ips-ep-section-title">Upcoming Schedule</h3>', unsafe_allow_html=True)
    events = list_upcoming_employee_schedule(eid, limit=limit)
    if not events:
        st.markdown('<p class="ips-ep-empty">No upcoming assignments scheduled.</p>', unsafe_allow_html=True)
        return

    events = enrich_events(
        events,
        jobs_by_id=jobs_by_id or {},
        employees_by_id=employees_by_id or {},
    )

    for ev in events:
        title = html.escape(str(ev.get("title") or "Assignment"))
        job_no = html.escape(str(ev.get("job_number") or ""))
        location = html.escape(str(ev.get("location") or "—"))
        supervisor = html.escape(str(ev.get("supervisor_name") or "—"))
        status = html.escape(str(ev.get("status") or "—").replace("_", " ").title())
        start = str(ev.get("start_at") or "")[:16]
        travel = html.escape(str(ev.get("mobilization_notes") or ev.get("lodging_name") or "").strip())
        travel_line = f"<p class='ips-ep-meta'>{travel}</p>" if travel else ""
        label = f"{job_no} — {title}" if job_no else title
        st.markdown(
            f"""
<div class="ips-ep-card ips-ep-schedule-card">
  <div class="ips-ep-card-head"><strong>{label}</strong></div>
  <p class="ips-ep-meta">{html.escape(fmt_date(start[:10]))} · {html.escape(start[11:16])}</p>
  <p class="ips-ep-muted">{location}</p>
  <p class="ips-ep-meta">Supervisor: {supervisor} · {status}</p>
  {travel_line}
</div>
""",
            unsafe_allow_html=True,
        )

    with st.expander("View Full Schedule"):
        all_events = list_upcoming_employee_schedule(employee_id, limit=30)
        all_events = enrich_events(
            all_events,
            jobs_by_id=jobs_by_id or {},
            employees_by_id=employees_by_id or {},
        )
        if len(all_events) <= len(events):
            st.caption("No additional assignments in the next 120 days.")
        for ev in all_events:
            st.markdown(
                f"- **{ev.get('title', 'Event')}** · {str(ev.get('start_at') or '')[:16]} · "
                f"{ev.get('location') or '—'}"
            )
