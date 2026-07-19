"""Scheduling module — plan jobs, crews, travel, and equipment assignments."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import streamlit as st

from app.auth import effective_role
from app.components.scheduling_calendar import (
    render_crew_schedule_table,
    render_day_agenda,
    render_equipment_schedule_table,
    render_jobs_schedule_grouped,
    render_week_calendar,
)
from app.components.scheduling_css import inject_scheduling_css
from app.components.scheduling_dialogs import (
    SCHED_FORM_KEY,
    SCHED_OPEN_DETAIL_KEY,
    open_new_schedule_dialog,
    open_schedule_detail,
    show_schedule_detail_dialog,
    show_schedule_event_dialog,
)
from app.pages._core._access import begin_module
from app.pages._core._data import (
    load_all_certifications,
    load_assets,
    load_customers,
    load_employees,
    load_jobs,
)
from app.perf_debug import perf_span
from app.services.scheduling_conflicts import build_event_conflict_report, parse_dt
from app.services.scheduling_service import (
    clear_scheduling_cache,
    enrich_events,
    list_asset_assignments_in_range,
    list_employee_assignments_in_range,
    list_schedule_events,
    list_availability_in_range,
    list_supervisor_events_in_range,
    monday_of,
    week_range,
    build_weekly_schedule_export_rows,
)
from app.ui.streamlit_perf import fragment, fragment_rerun, ips_app_rerun

_MODULE = "scheduling"
_VIEW_KEY = "scheduling_view_mode"
_WEEK_KEY = "scheduling_week_anchor"
_DAY_KEY = "scheduling_day_anchor"
_FILTERS_KEY = "scheduling_filters"
_SHOW_UNASSIGNED_KEY = "scheduling_show_unassigned"

_VIEW_MODES = ("Week", "Day", "Crew", "Jobs", "Equipment")


def _can_manage_scheduling() -> bool:
    from app.utils.permissions import normalize_role

    return normalize_role(effective_role()) in {"admin", "supervisor", "project manager"}


def _week_anchor() -> date:
    raw = st.session_state.get(_WEEK_KEY)
    if isinstance(raw, date):
        return raw
    return monday_of(date.today())


def _set_week_anchor(d: date) -> None:
    st.session_state[_WEEK_KEY] = monday_of(d)


def _day_anchor() -> date:
    raw = st.session_state.get(_DAY_KEY)
    if isinstance(raw, date):
        return raw
    return date.today()


def _clamp_day_to_week() -> None:
    week_start, week_end = week_range(_week_anchor())
    raw = st.session_state.get(_DAY_KEY)
    if not isinstance(raw, date) or not (week_start <= raw < week_end):
        st.session_state[_DAY_KEY] = week_start


def _day_in_week() -> date:
    _clamp_day_to_week()
    return _day_anchor()


def _view_mode() -> str:
    mode = str(st.session_state.get(_VIEW_KEY) or "Week").strip()
    return mode if mode in _VIEW_MODES else "Week"


def _refs() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    with perf_span("scheduling.refs.jobs"):
        jobs = load_jobs()
    with perf_span("scheduling.refs.employees"):
        employees = load_employees()
    with perf_span("scheduling.refs.assets"):
        assets = load_assets()
    with perf_span("scheduling.refs.customers"):
        customers = load_customers()
    jobs_by_id = {str(j.get("id") or "").strip(): j for j in jobs if str(j.get("id") or "").strip()}
    employees_by_id = {str(e.get("id") or "").strip(): e for e in employees if str(e.get("id") or "").strip()}
    assets_by_id = {str(a.get("id") or "").strip(): a for a in assets if str(a.get("id") or "").strip()}
    customers_by_id = {str(c.get("id") or "").strip(): c for c in customers if str(c.get("id") or "").strip()}
    return jobs, employees, assets, customers, jobs_by_id, employees_by_id, assets_by_id, customers_by_id


def _assignment_maps(
    start: date,
    end: date,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    emp_rows = list_employee_assignments_in_range(start, end)
    asset_rows = list_asset_assignments_in_range(start, end)
    by_event_emp: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_event_asset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in emp_rows:
        eid = str(row.get("schedule_event_id") or "").strip()
        if eid:
            by_event_emp[eid].append(row)
    for row in asset_rows:
        eid = str(row.get("schedule_event_id") or "").strip()
        if eid:
            by_event_asset[eid].append(row)
    return dict(by_event_emp), dict(by_event_asset)


def _conflict_event_ids(
    events: list[dict[str, Any]],
    *,
    employee_rows_by_event: dict[str, list[dict[str, Any]]],
    asset_rows_by_event: dict[str, list[dict[str, Any]]],
    pad_start: date,
    pad_end: date,
    assets_by_id: dict[str, dict[str, Any]],
    employee_certs: list[dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
) -> set[str]:
    emp_assignments = list_employee_assignments_in_range(pad_start, pad_end)
    asset_assignments = list_asset_assignments_in_range(pad_start, pad_end)
    supervisor_events = list_supervisor_events_in_range(pad_start, pad_end)
    all_emp_ids = {
        str(r.get("employee_id") or "").strip()
        for rows in employee_rows_by_event.values()
        for r in rows
        if str(r.get("employee_id") or "").strip()
    }
    availability = list_availability_in_range(pad_start, pad_end, employee_ids=list(all_emp_ids))
    labels = {
        eid: str(
            (employees_by_id.get(eid) or {}).get("full_name")
            or (employees_by_id.get(eid) or {}).get("employee_name")
            or eid
        )
        for eid in all_emp_ids
    }
    conflict_ids: set[str] = set()
    with perf_span("scheduling.conflicts.batch"):
        for ev in events:
            eid = str(ev.get("id") or "").strip()
            if not eid:
                continue
            start = parse_dt(ev.get("start_at"))
            end = parse_dt(ev.get("end_at"))
            if not start or not end:
                continue
            emp_ids = [
                str(r.get("employee_id") or "").strip()
                for r in employee_rows_by_event.get(eid) or []
                if str(r.get("employee_id") or "").strip()
            ]
            asset_ids = [
                str(r.get("asset_id") or "").strip()
                for r in asset_rows_by_event.get(eid) or []
                if str(r.get("asset_id") or "").strip()
            ]
            report = build_event_conflict_report(
                start_at=start,
                end_at=end,
                employee_ids=emp_ids,
                asset_ids=asset_ids,
                supervisor_id=str(ev.get("supervisor_id") or "").strip(),
                required_certifications=list(ev.get("required_certifications") or []),
                employee_assignments=emp_assignments,
                supervisor_events=supervisor_events,
                asset_assignments=asset_assignments,
                availability_rows=availability,
                employee_certs=employee_certs,
                assets_by_id=assets_by_id,
                employee_labels=labels,
                exclude_event_id=eid,
            )
            if report.has_warnings:
                conflict_ids.add(eid)
    return conflict_ids


def _open_event(event_id: str) -> None:
    open_schedule_detail(event_id)
    ips_app_rerun()


@fragment
def _render_filters(
    *,
    jobs: list[dict[str, Any]],
    employees: list[dict[str, Any]],
) -> dict[str, str]:
    filt = dict(st.session_state.get(_FILTERS_KEY) or {})
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        job_opts = ["All"] + [str(j.get("id") or "") for j in jobs if str(j.get("id") or "").strip()]
        job_labels = {
            str(j.get("id") or ""): f"{j.get('job_number', '—')} — {j.get('job_name', j.get('project_name', 'Job'))}"
            for j in jobs
            if str(j.get("id") or "").strip()
        }
        job_pick = st.selectbox(
            "Job",
            job_opts,
            index=job_opts.index(filt.get("job_id")) if filt.get("job_id") in job_opts else 0,
            format_func=lambda x: "All jobs" if x == "All" else job_labels.get(x, x),
            key="sched_filter_job",
        )
        filt["job_id"] = "" if job_pick == "All" else job_pick
    with c2:
        emp_opts = ["All"] + [str(e.get("id") or "") for e in employees if str(e.get("id") or "").strip()]
        emp_labels = {
            str(e.get("id") or ""): str(e.get("full_name") or e.get("employee_name") or e.get("name") or e.get("id"))
            for e in employees
        }
        sup_pick = st.selectbox(
            "Supervisor",
            emp_opts,
            index=emp_opts.index(filt.get("supervisor_id")) if filt.get("supervisor_id") in emp_opts else 0,
            format_func=lambda x: "All supervisors" if x == "All" else emp_labels.get(x, x),
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
    st.session_state[_FILTERS_KEY] = filt
    return filt


def _apply_client_filters(
    events: list[dict[str, Any]],
    filt: dict[str, str],
    *,
    jobs_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    out = events
    emp_f = str(filt.get("employee_id") or "").strip()
    if emp_f:
        # Filter applied in crew view primarily; week view uses server filters
        pass
    loc = str(filt.get("location") or "").strip().lower()
    if loc:
        out = [e for e in out if loc in str(e.get("location") or "").lower()]
    cust = str(filt.get("customer_id") or "").strip()
    if cust:
        out = [
            e
            for e in out
            if str(e.get("customer_id") or "").strip() == cust
            or str((jobs_by_id.get(str(e.get("job_id") or "")) or {}).get("customer_id") or "") == cust
        ]
    return out


def render() -> None:
    if not begin_module(_MODULE):
        return

    inject_scheduling_css()

    (
        jobs,
        employees,
        assets,
        customers,
        jobs_by_id,
        employees_by_id,
        assets_by_id,
        customers_by_id,
    ) = _refs()

    week_anchor = _week_anchor()
    week_start, week_end = week_range(week_anchor)
    filt = _render_filters(jobs=jobs, employees=employees)

    with perf_span("scheduling.query.events"):
        events = list_schedule_events(week_start, week_end, filters=filt)

    emp_by_event, asset_by_event = _assignment_maps(week_start, week_end)
    events = enrich_events(
        events,
        jobs_by_id=jobs_by_id,
        employees_by_id=employees_by_id,
        customers_by_id=customers_by_id,
        employee_rows_by_event=emp_by_event,
    )
    events = _apply_client_filters(events, filt, jobs_by_id=jobs_by_id)

    pad_start = week_start - timedelta(days=14)
    pad_end = week_end + timedelta(days=14)
    with perf_span("scheduling.refs.certs"):
        employee_certs = load_all_certifications()
    conflict_ids = _conflict_event_ids(
        events,
        employee_rows_by_event=emp_by_event,
        asset_rows_by_event=asset_by_event,
        pad_start=pad_start,
        pad_end=pad_end,
        assets_by_id=assets_by_id,
        employee_certs=employee_certs,
        employees_by_id=employees_by_id,
    )

    from app.ui.page_header import render_page_header

    def _new_event() -> None:
        open_new_schedule_dialog()
        ips_app_rerun()

    def _refresh() -> None:
        clear_scheduling_cache()
        fragment_rerun()

    render_page_header(
        "Scheduling",
        "Plan jobs, crews, travel, and equipment assignments.",
        icon="📅",
        primary_action=_new_event if _can_manage_scheduling() else None,
        show_refresh=True,
        on_refresh=_refresh,
        primary_action_width=2.0,
    )

    nav1, nav2, nav3, nav4 = st.columns(4)

    def _today() -> None:
        _set_week_anchor(date.today())
        st.session_state[_DAY_KEY] = date.today()
        fragment_rerun()

    def _prev_week() -> None:
        _set_week_anchor(week_anchor - timedelta(days=7))
        _clamp_day_to_week()
        fragment_rerun()

    def _next_week() -> None:
        _set_week_anchor(week_anchor + timedelta(days=7))
        _clamp_day_to_week()
        fragment_rerun()

    with nav1:
        st.button("Today", key="sched_hdr_today", on_click=_today, use_container_width=True)
    with nav2:
        st.button("Previous Week", key="sched_hdr_prev", on_click=_prev_week, use_container_width=True)
    with nav3:
        st.button("Next Week", key="sched_hdr_next", on_click=_next_week, use_container_width=True)
    with nav4:
        st.caption(f"Week: {week_start.strftime('%b %d')} – {(week_end - timedelta(days=1)).strftime('%b %d, %Y')}")

    if _can_manage_scheduling():
        exp_col1, exp_col2 = st.columns([1, 3])
        with exp_col1:
            if st.button("Export Weekly Schedule", key="sched_export_week", use_container_width=True):
                import csv
                import io

                rows = build_weekly_schedule_export_rows(
                    events,
                    jobs_by_id=jobs_by_id,
                    employees_by_id=employees_by_id,
                    employee_rows_by_event=emp_by_event,
                )
                buf = io.StringIO()
                if rows:
                    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
                st.download_button(
                    "Download CSV",
                    data=buf.getvalue().encode("utf-8"),
                    file_name=f"schedule_{week_start.isoformat()}.csv",
                    mime="text/csv",
                    key="sched_export_csv_dl",
                )

    mode_cols = st.columns(len(_VIEW_MODES))
    for col, mode in zip(mode_cols, _VIEW_MODES):
        with col:
            if st.button(
                mode,
                key=f"sched_view_{mode.lower()}",
                type="primary" if _view_mode() == mode else "secondary",
                use_container_width=True,
            ):
                st.session_state[_VIEW_KEY] = mode
                fragment_rerun()

    mode = _view_mode()
    with st.container(key="scheduling_page_wrap"):
        if mode == "Week":
            with perf_span("scheduling.render.week"):
                render_week_calendar(
                    events,
                    week_anchor=week_anchor,
                    conflict_event_ids=conflict_ids,
                    on_open_event=_open_event,
                )
        elif mode == "Day":
            week_start, week_end = week_range(week_anchor)
            day = _day_in_week()
            st.date_input(
                "Day",
                value=day,
                min_value=week_start,
                max_value=week_end - timedelta(days=1),
                key=_DAY_KEY,
            )
            render_day_agenda(
                events,
                day=_day_anchor(),
                conflict_event_ids=conflict_ids,
                on_open_event=_open_event,
            )
        elif mode == "Crew":
            render_crew_schedule_table(
                events,
                week_anchor=week_anchor,
                employees_by_id=employees_by_id,
                employee_rows_by_event=emp_by_event,
                show_unassigned=bool(st.session_state.get(_SHOW_UNASSIGNED_KEY)),
                on_open_event=_open_event,
            )
        elif mode == "Jobs":
            render_jobs_schedule_grouped(
                events,
                jobs_by_id=jobs_by_id,
                on_open_event=_open_event,
            )
        elif mode == "Equipment":
            render_equipment_schedule_table(
                events,
                assets_by_id=assets_by_id,
                asset_rows_by_event=asset_by_event,
                on_open_event=_open_event,
            )

    if st.session_state.get(SCHED_FORM_KEY):
        show_schedule_event_dialog(
            jobs=jobs,
            employees=employees,
            assets=assets,
            customers=customers,
            employee_certs=employee_certs,
        )

    if st.session_state.get(SCHED_OPEN_DETAIL_KEY):
        show_schedule_detail_dialog(
            jobs_by_id=jobs_by_id,
            employees_by_id=employees_by_id,
            assets_by_id=assets_by_id,
        )
