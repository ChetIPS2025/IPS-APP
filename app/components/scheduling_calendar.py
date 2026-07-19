"""Scheduling calendar and list views."""

from __future__ import annotations

import html
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Callable

import streamlit as st

from app.services.scheduling_conflicts import parse_dt
from app.services.scheduling_service import event_hours, monday_of, week_range
from app.ui.streamlit_perf import fragment_rerun

OpenEventFn = Callable[[str], None]


def _status_class(status: object) -> str:
    return str(status or "tentative").strip().lower().replace(" ", "_")


def _fmt_time(value: object) -> str:
    dt = parse_dt(value)
    if not dt:
        return "—"
    return dt.strftime("%I:%M %p").lstrip("0")


def _event_card_html(ev: dict[str, Any], *, has_conflict: bool = False) -> str:
    title = html.escape(str(ev.get("title") or "Event"))
    job_no = html.escape(str(ev.get("job_number") or ""))
    customer = html.escape(str(ev.get("customer_name") or ""))
    location = html.escape(str(ev.get("location") or ""))
    supervisor = html.escape(str(ev.get("supervisor_name") or ""))
    status = html.escape(str(ev.get("status") or "tentative").replace("_", " ").title())
    assigned = int(ev.get("assigned_employee_count") or 0)
    required = ev.get("required_crew_count")
    req_txt = f"{assigned}/{required}" if required not in (None, "") else str(assigned)
    conflict = '<span class="ips-scheduling-conflict-icon" title="Conflict">⚠</span> ' if has_conflict else ""
    time_txt = html.escape(f"{_fmt_time(ev.get('start_at'))} – {_fmt_time(ev.get('end_at'))}")
    meta_parts = [p for p in [job_no, customer, location, time_txt, supervisor, f"Crew {req_txt}", status] if p and p != "—"]
    meta = html.escape(" · ".join(meta_parts))
    cls = f"ips-scheduling-event-card status-{_status_class(ev.get('status'))}"
    if has_conflict:
        cls += " has-conflict"
    return (
        f'<div class="{cls}">'
        f'{conflict}<div class="ips-scheduling-event-title">{title}</div>'
        f'<div class="ips-scheduling-event-meta">{meta}</div>'
        f"</div>"
    )


def events_by_day(events: list[dict[str, Any]], week_start: date) -> dict[date, list[dict[str, Any]]]:
    days = [week_start + timedelta(days=i) for i in range(7)]
    buckets: dict[date, list[dict[str, Any]]] = {d: [] for d in days}
    for ev in events:
        start = parse_dt(ev.get("start_at"))
        if not start:
            continue
        day = start.date()
        if day in buckets:
            buckets[day].append(ev)
        else:
            # Spanning midnight — show on start day only for MVP
            if week_start <= day < week_start + timedelta(days=7):
                buckets.setdefault(day, []).append(ev)
    for day in buckets:
        buckets[day].sort(key=lambda r: str(r.get("start_at") or ""))
    return buckets


def render_week_calendar(
    events: list[dict[str, Any]],
    *,
    week_anchor: date,
    conflict_event_ids: set[str] | None = None,
    on_open_event: OpenEventFn | None = None,
) -> None:
    week_start, _ = week_range(week_anchor)
    conflict_ids = conflict_event_ids or set()
    buckets = events_by_day(events, week_start)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    cols_html: list[str] = []
    for idx, day in enumerate([week_start + timedelta(days=i) for i in range(7)]):
        cards = []
        for ev in buckets.get(day, []):
            eid = str(ev.get("id") or "").strip()
            cards.append(_event_card_html(ev, has_conflict=eid in conflict_ids))
        cards_html = "".join(cards) or '<div class="ips-scheduling-event-meta">No events</div>'
        cols_html.append(
            f'<div class="ips-scheduling-day-col">'
            f'<div class="ips-scheduling-day-head">{html.escape(day_names[idx])}</div>'
            f'<div class="ips-scheduling-day-date">{html.escape(day.strftime("%b %d"))}</div>'
            f"{cards_html}"
            f"</div>"
        )
    st.markdown(
        f'<div class="ips-scheduling-week-grid">{"".join(cols_html)}</div>',
        unsafe_allow_html=True,
    )
    if on_open_event:
        for ev in events:
            eid = str(ev.get("id") or "").strip()
            if not eid:
                continue
            label = str(ev.get("title") or "Open event")[:40]
            if st.button(label, key=f"sched_open_{eid}", type="tertiary"):
                on_open_event(eid)
                fragment_rerun()


def render_day_agenda(
    events: list[dict[str, Any]],
    *,
    day: date,
    conflict_event_ids: set[str] | None = None,
    on_open_event: OpenEventFn | None = None,
) -> None:
    conflict_ids = conflict_event_ids or set()
    day_events = []
    for ev in events:
        start = parse_dt(ev.get("start_at"))
        if start and start.date() == day:
            day_events.append(ev)
    day_events.sort(key=lambda r: str(r.get("start_at") or ""))
    if not day_events:
        st.info("No events scheduled for this day.")
        return
    for ev in day_events:
        eid = str(ev.get("id") or "").strip()
        st.markdown(_event_card_html(ev, has_conflict=eid in conflict_ids), unsafe_allow_html=True)
        if on_open_event and st.button("Open", key=f"sched_day_open_{eid}", type="tertiary"):
            on_open_event(eid)


def render_crew_schedule_table(
    events: list[dict[str, Any]],
    *,
    week_anchor: date,
    employees_by_id: dict[str, dict[str, Any]],
    employee_rows_by_event: dict[str, list[dict[str, Any]]],
    show_unassigned: bool = False,
    on_open_event: OpenEventFn | None = None,
) -> None:
    week_start, week_end = week_range(week_anchor)
    days = [week_start + timedelta(days=i) for i in range(7)]
    hours_by_emp_day: dict[str, dict[date, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    for ev in events:
        eid = str(ev.get("id") or "").strip()
        for row in employee_rows_by_event.get(eid) or []:
            emp_id = str(row.get("employee_id") or "").strip()
            if not emp_id:
                continue
            start = parse_dt(ev.get("start_at"))
            if not start:
                continue
            day = start.date()
            if week_start <= day < week_end:
                hours_by_emp_day[emp_id][day].append(ev)

    emp_ids = sorted(hours_by_emp_day.keys(), key=lambda eid: str((employees_by_id.get(eid) or {}).get("full_name") or eid))
    if show_unassigned:
        emp_ids = sorted(
            employees_by_id.keys(),
            key=lambda eid: str((employees_by_id.get(eid) or {}).get("full_name") or eid),
        )
    if not emp_ids and not show_unassigned:
        st.info("No crew assignments this week.")
        return
    if not emp_ids:
        st.info("No employees to display.")
        return

    head = "".join(f"<th>{html.escape(d.strftime('%a %m/%d'))}</th>" for d in days)
    body_rows: list[str] = []
    for emp_id in emp_ids:
        emp = employees_by_id.get(emp_id) or {}
        name = html.escape(str(emp.get("full_name") or emp.get("employee_name") or emp.get("name") or emp_id))
        total_hours = 0.0
        cells: list[str] = []
        for d in days:
            evs = hours_by_emp_day[emp_id].get(d) or []
            if not evs:
                cells.append("<td>—</td>")
                continue
            parts = []
            for ev in evs:
                hrs = event_hours(ev.get("start_at"), ev.get("end_at"))
                total_hours += hrs
                label = html.escape(str(ev.get("job_number") or ev.get("title") or "Event"))
                loc = html.escape(str(ev.get("location") or "")[:12])
                parts.append(f"{label}<br><span style='color:#64748b;font-size:0.68rem;'>{hrs:.1f}h {loc}</span>")
            cells.append(f"<td>{'<hr style=\"margin:0.25rem 0;border:none;border-top:1px solid #e2e8f0;\">'.join(parts)}</td>")
        conflict = "OK"
        row_html = (
            f"<tr><td><strong>{name}</strong></td>"
            f"{''.join(cells)}"
            f"<td>{total_hours:.1f}</td><td>{conflict}</td></tr>"
        )
        body_rows.append(row_html)

    table = (
        '<div class="ips-scheduling-crew-table-wrap">'
        '<table class="ips-scheduling-crew-table">'
        "<thead><tr><th>Employee</th>"
        f"{head}<th>Total Hrs</th><th>Conflicts</th></tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table></div>"
    )
    st.markdown(table, unsafe_allow_html=True)
    if on_open_event:
        for ev in events:
            eid = str(ev.get("id") or "").strip()
            if eid and st.button(f"Open {ev.get('title', 'event')}", key=f"sched_crew_open_{eid}", type="tertiary"):
                on_open_event(eid)


def render_jobs_schedule_grouped(
    events: list[dict[str, Any]],
    *,
    jobs_by_id: dict[str, dict[str, Any]],
    on_open_event: OpenEventFn | None = None,
) -> None:
    by_job: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ev in events:
        jid = str(ev.get("job_id") or "").strip() or "__none__"
        by_job[jid].append(ev)

    if not by_job:
        st.info("No job schedule events in this range.")
        return

    for jid, evs in sorted(by_job.items(), key=lambda kv: str((jobs_by_id.get(kv[0]) or {}).get("job_number") or kv[0])):
        job = jobs_by_id.get(jid) or {}
        title = str(job.get("job_number") or job.get("job_name") or evs[0].get("title") or "Job")
        starts = [parse_dt(e.get("start_at")) for e in evs]
        ends = [parse_dt(e.get("end_at")) for e in evs]
        starts = [s for s in starts if s]
        ends = [e for e in ends if e]
        first = min(starts).date().isoformat() if starts else "—"
        last = max(ends).date().isoformat() if ends else "—"
        crew_ids = set()
        for e in evs:
            crew_ids.add(int(e.get("assigned_employee_count") or 0))
        st.markdown(
            f"**{html.escape(title)}** · {html.escape(str(job.get('customer') or job.get('customer_name') or '—'))} · "
            f"{first} → {last} · {len(evs)} event(s)"
        )
        if on_open_event:
            for ev in evs:
                eid = str(ev.get("id") or "").strip()
                if eid and st.button(f"View {ev.get('title', 'event')}", key=f"sched_job_grp_{eid}", type="tertiary"):
                    on_open_event(eid)


def render_equipment_schedule_table(
    events: list[dict[str, Any]],
    *,
    assets_by_id: dict[str, dict[str, Any]],
    asset_rows_by_event: dict[str, list[dict[str, Any]]],
    on_open_event: OpenEventFn | None = None,
) -> None:
    rows: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for ev in events:
        eid = str(ev.get("id") or "").strip()
        for assign in asset_rows_by_event.get(eid) or []:
            aid = str(assign.get("asset_id") or "").strip()
            asset = assets_by_id.get(aid) or {}
            rows.append((ev, assign, asset))

    if not rows:
        st.info("No equipment scheduled in this range.")
        return

    header = st.columns([1.0, 1.4, 1.0, 1.4, 1.0, 1.0, 0.8, 0.8])
    for col, label in zip(header, ("Asset #", "Asset", "Category", "Job/Event", "Start", "End", "Status", "Conflict")):
        with col:
            st.markdown(f"**{label}**")
    for idx, (ev, _assign, asset) in enumerate(rows):
        cols = st.columns([1.0, 1.4, 1.0, 1.4, 1.0, 1.0, 0.8, 0.8])
        vals = (
            str(asset.get("asset_number") or asset.get("asset_id") or "—"),
            str(asset.get("asset_name") or asset.get("name") or "—"),
            str(asset.get("category") or "—"),
            str(ev.get("title") or "—"),
            str(ev.get("start_at") or "")[:16],
            str(ev.get("end_at") or "")[:16],
            str(asset.get("status") or "—"),
            "—",
        )
        for col, val in zip(cols, vals):
            with col:
                st.markdown(html.escape(val))
        eid = str(ev.get("id") or "").strip()
        if on_open_event and eid and st.button("Open", key=f"sched_eq_open_{eid}_{idx}", type="tertiary"):
            on_open_event(eid)
