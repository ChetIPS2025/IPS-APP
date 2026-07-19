"""Scheduling create/edit/detail dialogs."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any, Callable

import streamlit as st

from app.auth import current_profile, effective_role
from app.services.scheduling_conflicts import ConflictReport
from app.services.scheduling_service import (
    EVENT_STATUSES,
    EVENT_TYPES,
    create_schedule_event,
    delete_schedule_event,
    get_schedule_event,
    list_event_assets,
    list_event_employees,
    replace_event_assets,
    replace_event_employees,
    update_schedule_event,
    compute_event_conflicts,
)
from app.ui.streamlit_perf import ips_app_rerun
from app.utils.permissions import normalize_role

SCHED_FORM_KEY = "sched_event_form"
SCHED_EDIT_ID_KEY = "sched_edit_event_id"
SCHED_OPEN_DETAIL_KEY = "sched_open_detail_id"
SCHED_CONFLICTS_KEY = "sched_pending_conflicts"
SCHED_SAVE_WITH_CONFLICTS_KEY = "sched_save_with_conflicts"
SCHED_PREFILL_JOB_KEY = "sched_prefill_job_id"


def _can_manage_scheduling(role: str | None = None) -> bool:
    r = normalize_role(role or effective_role())
    return r in {"admin", "supervisor", "project manager"}


def _employee_label(emp: dict[str, Any]) -> str:
    return str(emp.get("full_name") or emp.get("employee_name") or emp.get("name") or emp.get("id") or "—")


def _asset_label(asset: dict[str, Any]) -> str:
    num = str(asset.get("asset_number") or asset.get("asset_id") or "").strip()
    name = str(asset.get("asset_name") or asset.get("name") or "").strip()
    return f"{num} — {name}" if num and name else num or name or "Asset"


def _dt_from_inputs(d: date | None, t: time | None, *, end: bool = False) -> datetime | None:
    if d is None:
        return None
    if t is None:
        t = time(23, 59) if end else time(8, 0)
    return datetime.combine(d, t, tzinfo=timezone.utc)


def _parse_date_field(key: str) -> date | None:
    val = st.session_state.get(key)
    if isinstance(val, date):
        return val
    return None


def _parse_time_field(key: str) -> time | None:
    val = st.session_state.get(key)
    if isinstance(val, time):
        return val
    return None


def open_new_schedule_dialog(*, job_id: str = "") -> None:
    st.session_state[SCHED_EDIT_ID_KEY] = ""
    st.session_state[SCHED_FORM_KEY] = True
    if job_id:
        st.session_state[SCHED_PREFILL_JOB_KEY] = job_id
    st.session_state.pop(SCHED_CONFLICTS_KEY, None)
    st.session_state.pop(SCHED_SAVE_WITH_CONFLICTS_KEY, None)


def open_edit_schedule_dialog(event_id: str) -> None:
    st.session_state[SCHED_EDIT_ID_KEY] = str(event_id or "").strip()
    st.session_state[SCHED_FORM_KEY] = True
    st.session_state.pop(SCHED_CONFLICTS_KEY, None)
    st.session_state.pop(SCHED_SAVE_WITH_CONFLICTS_KEY, None)


def open_schedule_detail(event_id: str) -> None:
    st.session_state[SCHED_OPEN_DETAIL_KEY] = str(event_id or "").strip()


def _job_prefill(
    job_id: str,
    *,
    jobs_by_id: dict[str, dict[str, Any]],
    customers_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    jid = str(job_id or "").strip()
    if not jid:
        return {}
    job = jobs_by_id.get(jid) or {}
    out: dict[str, Any] = {
        "job_id": jid,
        "title": str(job.get("job_name") or job.get("project_name") or job.get("job_number") or "Job assignment"),
        "location": str(job.get("location") or ""),
    }
    cid = str(job.get("customer_id") or "").strip()
    if cid:
        out["customer_id"] = cid
    sup = str(job.get("supervisor_id") or "").strip()
    if sup:
        out["supervisor_id"] = sup
    return out


@st.dialog("Schedule Event", width="large")
def show_schedule_event_dialog(
    *,
    jobs: list[dict[str, Any]],
    employees: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    employee_certs: list[dict[str, Any]] | None = None,
) -> None:
    if not _can_manage_scheduling():
        st.warning("You do not have permission to edit schedules.")
        return

    jobs_by_id = {str(j.get("id") or "").strip(): j for j in jobs if str(j.get("id") or "").strip()}
    employees_by_id = {str(e.get("id") or "").strip(): e for e in employees if str(e.get("id") or "").strip()}
    assets_by_id = {str(a.get("id") or "").strip(): a for a in assets if str(a.get("id") or "").strip()}
    customers_by_id = {str(c.get("id") or "").strip(): c for c in customers if str(c.get("id") or "").strip()}

    edit_id = str(st.session_state.get(SCHED_EDIT_ID_KEY) or "").strip()
    existing = get_schedule_event(edit_id) if edit_id else None
    prefill_job = str(st.session_state.pop(SCHED_PREFILL_JOB_KEY, "") or "").strip()
    if not existing and prefill_job:
        existing = _job_prefill(prefill_job, jobs_by_id=jobs_by_id, customers_by_id=customers_by_id)

    title_label = "Edit Schedule Event" if edit_id else "New Schedule Event"
    st.markdown(f"### {title_label}")

    job_options = ["—"] + [str(j.get("id") or "") for j in jobs if str(j.get("id") or "").strip()]
    job_labels = {
        str(j.get("id") or ""): f"{j.get('job_number', '—')} — {j.get('job_name', j.get('project_name', 'Job'))}"
        for j in jobs
        if str(j.get("id") or "").strip()
    }
    emp_options = [str(e.get("id") or "") for e in employees if str(e.get("id") or "").strip()]
    emp_labels = {str(e.get("id") or ""): _employee_label(e) for e in employees}
    asset_options = [str(a.get("id") or "") for a in assets if str(a.get("id") or "").strip()]
    asset_labels = {str(a.get("id") or ""): _asset_label(a) for a in assets}

    c1, c2 = st.columns(2)
    with c1:
        event_type = st.selectbox("Event Type", EVENT_TYPES, index=EVENT_TYPES.index(str((existing or {}).get("event_type") or "job")) if str((existing or {}).get("event_type") or "job") in EVENT_TYPES else 0, key="sched_form_event_type")
        title = st.text_input("Title", value=str((existing or {}).get("title") or ""), key="sched_form_title")
        job_idx = 0
        cur_job = str((existing or {}).get("job_id") or "")
        if cur_job in job_options:
            job_idx = job_options.index(cur_job)
        job_pick = st.selectbox(
            "Job",
            job_options,
            index=job_idx,
            format_func=lambda x: "—" if x == "—" else job_labels.get(x, x),
            key="sched_form_job",
        )
    with c2:
        status = st.selectbox("Status", EVENT_STATUSES, index=EVENT_STATUSES.index(str((existing or {}).get("status") or "tentative")) if str((existing or {}).get("status") or "tentative") in EVENT_STATUSES else 0, key="sched_form_status")
        location = st.text_input("Location", value=str((existing or {}).get("location") or ""), key="sched_form_location")
        supervisor = st.selectbox(
            "Supervisor",
            [""] + emp_options,
            index=(emp_options.index(str((existing or {}).get("supervisor_id") or "")) + 1) if str((existing or {}).get("supervisor_id") or "") in emp_options else 0,
            format_func=lambda x: "—" if not x else emp_labels.get(x, x),
            key="sched_form_supervisor",
        )

    if job_pick and job_pick != "—" and job_pick in jobs_by_id:
        pre = _job_prefill(job_pick, jobs_by_id=jobs_by_id, customers_by_id=customers_by_id)
        if not st.session_state.get("sched_form_title") and pre.get("title"):
            st.session_state["sched_form_title"] = pre["title"]
        if not st.session_state.get("sched_form_location") and pre.get("location"):
            st.session_state["sched_form_location"] = pre["location"]

    d1, d2, d3 = st.columns(3)
    with d1:
        start_date = st.date_input("Start Date", value=date.today(), key="sched_form_start_date")
    with d2:
        start_time = st.time_input("Start Time", value=time(8, 0), key="sched_form_start_time")
    with d3:
        all_day = st.checkbox("All Day", value=bool((existing or {}).get("all_day")), key="sched_form_all_day")
    e1, e2 = st.columns(2)
    with e1:
        end_date = st.date_input("End Date", value=date.today(), key="sched_form_end_date")
    with e2:
        end_time = st.time_input("End Time", value=time(17, 0), key="sched_form_end_time")

    cur_emps = [str(r.get("employee_id") or "") for r in (list_event_employees(edit_id) if edit_id else [])]
    cur_assets = [str(r.get("asset_id") or "") for r in (list_event_assets(edit_id) if edit_id else [])]

    assigned = st.multiselect(
        "Assigned Employees",
        emp_options,
        default=[e for e in cur_emps if e in emp_options],
        format_func=lambda x: emp_labels.get(x, x),
        key="sched_form_employees",
    )
    assigned_assets = st.multiselect(
        "Assigned Assets",
        asset_options,
        default=[a for a in cur_assets if a in asset_options],
        format_func=lambda x: asset_labels.get(x, x),
        key="sched_form_assets",
    )

    c3, c4 = st.columns(2)
    with c3:
        required_crew = st.number_input("Required Crew Count", min_value=0, value=int((existing or {}).get("required_crew_count") or 0), key="sched_form_required_crew")
        shift_name = st.text_input("Shift Name", value=str((existing or {}).get("shift_name") or ""), key="sched_form_shift")
        per_diem = st.number_input("Per Diem Amount", min_value=0.0, value=float((existing or {}).get("per_diem_amount") or 0.0), step=25.0, key="sched_form_per_diem")
    with c4:
        lodging_name = st.text_input("Lodging Name", value=str((existing or {}).get("lodging_name") or ""), key="sched_form_lodging_name")
        lodging_address = st.text_area("Lodging Address", value=str((existing or {}).get("lodging_address") or ""), key="sched_form_lodging_address", height=68)

    work_instructions = st.text_area("Work Instructions", value=str((existing or {}).get("work_instructions") or ""), key="sched_form_work_instructions")
    mobilization_notes = st.text_area("Mobilization Notes", value=str((existing or {}).get("mobilization_notes") or ""), key="sched_form_mobilization")
    internal_notes = st.text_area("Internal Notes", value=str((existing or {}).get("internal_notes") or ""), key="sched_form_internal")

    conflict_report: ConflictReport | None = st.session_state.get(SCHED_CONFLICTS_KEY)
    if isinstance(conflict_report, ConflictReport) and conflict_report.has_warnings:
        st.warning("Conflicts detected:")
        for w in conflict_report.warnings:
            st.markdown(f"- {w.message}")

    bc1, bc2, bc3, bc4 = st.columns(4)
    with bc1:
        cancel = st.button("Cancel", key="sched_form_cancel", use_container_width=True)
    with bc2:
        check = st.button("Check Conflicts", key="sched_form_check", use_container_width=True)
    with bc3:
        save = st.button("Save Event", key="sched_form_save", type="primary", use_container_width=True)
    with bc4:
        save_anyway = False
        if isinstance(conflict_report, ConflictReport) and conflict_report.has_warnings:
            save_anyway = st.button("Save With Conflicts", key="sched_form_save_conflicts", use_container_width=True)

    if cancel:
        st.session_state[SCHED_FORM_KEY] = False
        st.session_state.pop(SCHED_CONFLICTS_KEY, None)
        st.rerun()

    start_dt = _dt_from_inputs(start_date, None if all_day else start_time)
    end_dt = _dt_from_inputs(end_date, None if all_day else end_time, end=True)
    payload: dict[str, Any] = {
        "event_type": event_type,
        "title": title.strip(),
        "job_id": job_pick if job_pick and job_pick != "—" else None,
        "location": location.strip(),
        "start_at": start_dt.isoformat() if start_dt else None,
        "end_at": end_dt.isoformat() if end_dt else None,
        "all_day": all_day,
        "status": status,
        "supervisor_id": supervisor or None,
        "required_crew_count": int(required_crew) if required_crew else None,
        "shift_name": shift_name.strip(),
        "per_diem_amount": per_diem if per_diem else None,
        "lodging_name": lodging_name.strip(),
        "lodging_address": lodging_address.strip(),
        "mobilization_notes": mobilization_notes.strip(),
        "work_instructions": work_instructions.strip(),
        "internal_notes": internal_notes.strip(),
        "required_certifications": [],
    }
    emp_labels_map = {eid: emp_labels.get(eid, eid) for eid in assigned}

    if check and start_dt and end_dt:
        report = compute_event_conflicts(
            payload,
            employee_ids=assigned,
            asset_ids=assigned_assets,
            exclude_event_id=edit_id,
            employee_certs=employee_certs or [],
            assets_by_id=assets_by_id,
            employee_labels=emp_labels_map,
        )
        st.session_state[SCHED_CONFLICTS_KEY] = report
        st.rerun()

    if (save or save_anyway) and start_dt and end_dt:
        if end_dt <= start_dt:
            st.error("End must be after start.")
            return
        report = compute_event_conflicts(
            payload,
            employee_ids=assigned,
            asset_ids=assigned_assets,
            exclude_event_id=edit_id,
            employee_certs=employee_certs or [],
            assets_by_id=assets_by_id,
            employee_labels=emp_labels_map,
        )
        if report.has_warnings and not save_anyway:
            st.session_state[SCHED_CONFLICTS_KEY] = report
            st.warning("Resolve conflicts or use Save With Conflicts.")
            st.rerun()
            return
        profile = current_profile() or {}
        payload["updated_by"] = profile.get("id")
        if not edit_id:
            payload["created_by"] = profile.get("id")
            result = create_schedule_event(payload)
            if not result.ok:
                st.error(result.error or "Could not create event.")
                return
            new_id = str((result.data or {}).get("id") or "").strip()
        else:
            result = update_schedule_event(edit_id, payload)
            if not result.ok:
                st.error(result.error or "Could not update event.")
                return
            new_id = edit_id
        replace_event_employees(new_id, assigned)
        replace_event_assets(new_id, assigned_assets)
        saved = get_schedule_event(new_id) or {}
        from app.services.scheduling_notifications import notify_schedule_event_saved

        notify_schedule_event_saved(saved, previous=existing if edit_id else None, employee_ids=assigned)
        st.session_state[SCHED_FORM_KEY] = False
        st.session_state.pop(SCHED_CONFLICTS_KEY, None)
        st.success("Schedule event saved.")
        ips_app_rerun()


@st.dialog("Schedule Event Details", width="large")
def show_schedule_detail_dialog(
    *,
    jobs_by_id: dict[str, dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
    assets_by_id: dict[str, dict[str, Any]],
) -> None:
    eid = str(st.session_state.get(SCHED_OPEN_DETAIL_KEY) or "").strip()
    ev = get_schedule_event(eid) if eid else None
    if not ev:
        st.warning("Event not found.")
        if st.button("Close", key="sched_detail_missing_close"):
            st.session_state.pop(SCHED_OPEN_DETAIL_KEY, None)
            st.rerun()
        return

    st.markdown(f"### {ev.get('title', 'Event')}")
    st.caption(f"Type: {ev.get('event_type', '—')} · Status: {str(ev.get('status', '—')).replace('_', ' ').title()}")

    jid = str(ev.get("job_id") or "").strip()
    job = jobs_by_id.get(jid) or {}
    if job:
        st.markdown(f"**Job:** {job.get('job_number', '—')} — {job.get('job_name', job.get('project_name', '—'))}")
    st.markdown(f"**When:** {str(ev.get('start_at') or '')[:16]} → {str(ev.get('end_at') or '')[:16]}")
    st.markdown(f"**Location:** {ev.get('location') or '—'}")
    sup = employees_by_id.get(str(ev.get("supervisor_id") or "").strip()) or {}
    if sup:
        st.markdown(f"**Supervisor:** {_employee_label(sup)}")

    emps = list_event_employees(eid)
    if emps:
        st.markdown("**Crew**")
        for row in emps:
            emp = employees_by_id.get(str(row.get("employee_id") or "")) or {}
            st.markdown(f"- {_employee_label(emp)}")

    assets = list_event_assets(eid)
    if assets:
        st.markdown("**Equipment**")
        for row in assets:
            asset = assets_by_id.get(str(row.get("asset_id") or "")) or {}
            st.markdown(f"- {_asset_label(asset)}")

    if ev.get("work_instructions"):
        st.markdown(f"**Work Instructions:** {ev.get('work_instructions')}")
    if ev.get("mobilization_notes"):
        st.markdown(f"**Mobilization:** {ev.get('mobilization_notes')}")
    if _can_manage_scheduling() and ev.get("internal_notes"):
        st.markdown(f"**Internal Notes:** {ev.get('internal_notes')}")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if _can_manage_scheduling() and st.button("Edit", key="sched_detail_edit", use_container_width=True):
            st.session_state.pop(SCHED_OPEN_DETAIL_KEY, None)
            open_edit_schedule_dialog(eid)
            st.rerun()
    with c2:
        if _can_manage_scheduling() and st.button("Mark Confirmed", key="sched_detail_confirm", use_container_width=True):
            update_schedule_event(eid, {"status": "confirmed"})
            st.rerun()
    with c3:
        if _can_manage_scheduling() and st.button("Cancel Event", key="sched_detail_cancel_ev", use_container_width=True):
            update_schedule_event(eid, {"status": "cancelled"})
            st.rerun()
    with c4:
        if normalize_role(effective_role()) == "admin" and st.button("Delete", key="sched_detail_delete", use_container_width=True):
            delete_schedule_event(eid)
            st.session_state.pop(SCHED_OPEN_DETAIL_KEY, None)
            st.rerun()
