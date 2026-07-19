"""Indexed batch conflict detection for Scheduling calendar views."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.perf_debug import perf_span
from app.services.scheduling_conflicts import build_event_conflict_report, parse_dt

_VIEWS_WITH_CONFLICT_FLAGS = frozenset({"Week", "Day"})


def view_mode_needs_conflict_flags(view_mode: str) -> bool:
    return str(view_mode or "").strip() in _VIEWS_WITH_CONFLICT_FLAGS


def _employee_labels(employees_by_id: dict[str, dict[str, Any]], employee_ids: set[str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for eid in employee_ids:
        emp = employees_by_id.get(eid) or {}
        labels[eid] = str(
            emp.get("full_name") or emp.get("employee_name") or emp.get("name") or eid
        )
    return labels


def find_conflicting_schedule_event_ids(
    events: list[dict[str, Any]],
    *,
    employee_assignments: list[dict[str, Any]],
    asset_assignments: list[dict[str, Any]],
    supervisor_events: list[dict[str, Any]],
    availability_rows: list[dict[str, Any]],
    employee_certs: list[dict[str, Any]],
    assets_by_id: dict[str, dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
    employee_rows_by_event: dict[str, list[dict[str, Any]]],
    asset_rows_by_event: dict[str, list[dict[str, Any]]],
) -> set[str]:
    """Return event IDs with conflict warnings using shared indexed inputs."""
    if not events:
        return set()

    with perf_span("scheduling.conflict_index_build"):
        emp_by_employee: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in employee_assignments:
            eid = str(row.get("employee_id") or "").strip()
            if eid:
                emp_by_employee[eid].append(row)

        asset_by_asset: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in asset_assignments:
            aid = str(row.get("asset_id") or "").strip()
            if aid:
                asset_by_asset[aid].append(row)

        sup_by_supervisor: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in supervisor_events:
            sid = str(row.get("supervisor_id") or "").strip()
            if sid:
                sup_by_supervisor[sid].append(row)

        avail_by_employee: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in availability_rows:
            eid = str(row.get("employee_id") or "").strip()
            if eid:
                avail_by_employee[eid].append(row)

        certs_by_employee: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in employee_certs:
            eid = str(row.get("employee_id") or "").strip()
            if eid:
                certs_by_employee[eid].append(row)

    all_emp_ids = {
        str(r.get("employee_id") or "").strip()
        for rows in employee_rows_by_event.values()
        for r in rows
        if str(r.get("employee_id") or "").strip()
    }
    labels = _employee_labels(employees_by_id, all_emp_ids)

    conflict_ids: set[str] = set()
    with perf_span("scheduling.conflict_batch"):
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
            supervisor_id = str(ev.get("supervisor_id") or "").strip()

            scoped_emp_assignments: list[dict[str, Any]] = []
            for emp_id in emp_ids:
                scoped_emp_assignments.extend(emp_by_employee.get(emp_id, []))

            scoped_asset_assignments: list[dict[str, Any]] = []
            for asset_id in asset_ids:
                scoped_asset_assignments.extend(asset_by_asset.get(asset_id, []))

            scoped_supervisor_events = sup_by_supervisor.get(supervisor_id, []) if supervisor_id else []

            scoped_availability: list[dict[str, Any]] = []
            for emp_id in emp_ids:
                scoped_availability.extend(avail_by_employee.get(emp_id, []))

            scoped_certs: list[dict[str, Any]] = []
            for emp_id in emp_ids:
                scoped_certs.extend(certs_by_employee.get(emp_id, []))

            report = build_event_conflict_report(
                start_at=start,
                end_at=end,
                employee_ids=emp_ids,
                asset_ids=asset_ids,
                supervisor_id=supervisor_id,
                required_certifications=list(ev.get("required_certifications") or []),
                employee_assignments=scoped_emp_assignments,
                supervisor_events=scoped_supervisor_events,
                asset_assignments=scoped_asset_assignments,
                availability_rows=scoped_availability,
                employee_certs=scoped_certs,
                assets_by_id=assets_by_id,
                employee_labels=labels,
                exclude_event_id=eid,
            )
            if report.has_warnings:
                conflict_ids.add(eid)
    return conflict_ids
