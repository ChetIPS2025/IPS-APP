"""Employee Portal upcoming schedule."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.utils.formatting import fmt_date


def build_schedule_cards_html(events: list[dict[str, Any]]) -> str:
    if not events:
        return ""
    parts: list[str] = []
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
        parts.append(
            f"""
<div class="ips-ep-card ips-ep-schedule-card">
  <div class="ips-ep-card-head"><strong>{label}</strong></div>
  <p class="ips-ep-meta">{html.escape(fmt_date(start[:10]))} · {html.escape(start[11:16])}</p>
  <p class="ips-ep-muted">{location}</p>
  <p class="ips-ep-meta">Supervisor: {supervisor} · {status}</p>
  {travel_line}
</div>
"""
        )
    return "".join(parts)


def render_schedule_section(events: list[dict[str, Any]]) -> None:
    from app.perf_debug import perf_span

    st.markdown('<h3 class="ips-ep-section-title">Upcoming Schedule</h3>', unsafe_allow_html=True)
    if not events:
        st.markdown('<p class="ips-ep-empty">No upcoming assignments scheduled.</p>', unsafe_allow_html=True)
        return
    with perf_span("employee_portal.cards_html"):
        st.markdown(build_schedule_cards_html(events), unsafe_allow_html=True)
