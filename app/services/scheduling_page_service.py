"""Scheduling page snapshot — events, assignments, references, and conflicts."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import streamlit as st

from app.auth import effective_role
from app.pages._core._data import employees_catalog_data_version, jobs_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get
from app.perf_debug import perf_span
from app.services.scheduling_conflict_batch_service import (
    find_conflicting_schedule_event_ids,
    view_mode_needs_conflict_flags,
)
from app.services.scheduling_reference_service import (
    get_assets_by_ids,
    get_customers_by_ids,
    get_jobs_by_ids,
    get_people_by_ids,
    list_active_employee_roster,
    list_relevant_certifications,
    rows_to_by_id,
)
from app.services.scheduling_service import (
    enrich_events,
    list_asset_assignments_in_range,
    list_availability_in_range,
    list_employee_assignments_in_range,
    list_schedule_events,
    scheduling_data_version,
    week_range,
)

CONFLICT_PAD_DAYS = 14


@dataclass(frozen=True)
class SchedulingAssignmentSnapshot:
    employee_rows: list[dict[str, Any]]
    asset_rows: list[dict[str, Any]]
    employee_rows_by_event: dict[str, list[dict[str, Any]]]
    asset_rows_by_event: dict[str, list[dict[str, Any]]]


@dataclass(frozen=True)
class SchedulingPageSnapshot:
    week_start: date
    week_end: date
    events: list[dict[str, Any]]
    employee_assignments_by_event: dict[str, list[dict[str, Any]]]
    asset_assignments_by_event: dict[str, list[dict[str, Any]]]
    conflict_event_ids: set[str]
    jobs_by_id: dict[str, dict[str, Any]]
    employees_by_id: dict[str, dict[str, Any]]
    assets_by_id: dict[str, dict[str, Any]]
    customers_by_id: dict[str, dict[str, Any]]
    assignment_snapshot: SchedulingAssignmentSnapshot | None = None
    warning: str | None = None


def _filters_cache_token(filters: dict[str, str]) -> str:
    payload = json.dumps(filters or {}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _assignment_maps_from_rows(
    emp_rows: list[dict[str, Any]],
    asset_rows: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
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


def _filter_assignments_to_events(
    emp_rows: list[dict[str, Any]],
    asset_rows: list[dict[str, Any]],
    event_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not event_ids:
        return [], []
    emp_filtered = [
        r for r in emp_rows if str(r.get("schedule_event_id") or "").strip() in event_ids
    ]
    asset_filtered = [
        r for r in asset_rows if str(r.get("schedule_event_id") or "").strip() in event_ids
    ]
    return emp_filtered, asset_filtered


def _collect_reference_ids(
    events: list[dict[str, Any]],
    *,
    emp_by_event: dict[str, list[dict[str, Any]]],
    asset_by_event: dict[str, list[dict[str, Any]]],
    view_mode: str,
    show_unassigned: bool,
) -> tuple[set[str], set[str], set[str], set[str]]:
    job_ids: set[str] = set()
    employee_ids: set[str] = set()
    asset_ids: set[str] = set()
    customer_ids: set[str] = set()

    for ev in events:
        jid = str(ev.get("job_id") or "").strip()
        if jid:
            job_ids.add(jid)
        cid = str(ev.get("customer_id") or "").strip()
        if cid:
            customer_ids.add(cid)
        sid = str(ev.get("supervisor_id") or "").strip()
        if sid:
            employee_ids.add(sid)
        eid = str(ev.get("id") or "").strip()
        for row in emp_by_event.get(eid) or []:
            emp = str(row.get("employee_id") or "").strip()
            if emp:
                employee_ids.add(emp)

    if view_mode == "Equipment" or view_mode in {"Week", "Day"}:
        for rows in asset_by_event.values():
            for row in rows:
                aid = str(row.get("asset_id") or "").strip()
                if aid:
                    asset_ids.add(aid)

    if view_mode == "Equipment":
        pass  # asset_ids already collected
    elif view_mode not in {"Week", "Day", "Crew", "Jobs"}:
        pass

    if view_mode == "Crew" and show_unassigned:
        for row in list_active_employee_roster():
            eid = str(row.get("id") or "").strip()
            if eid:
                employee_ids.add(eid)

    return job_ids, employee_ids, asset_ids, customer_ids


def _query_range_for_view(
    *,
    week_start: date,
    week_end: date,
    selected_day: date,
    view_mode: str,
) -> tuple[date, date]:
    if view_mode == "Day":
        return selected_day, selected_day + timedelta(days=1)
    return week_start, week_end


def load_scheduling_page_snapshot(
    *,
    week_start: date,
    week_end: date,
    selected_day: date,
    view_mode: str,
    filters: dict[str, str],
    show_unassigned: bool = False,
    include_conflicts: bool | None = None,
    force_refresh: bool = False,
) -> SchedulingPageSnapshot:
    if include_conflicts is None:
        include_conflicts = view_mode_needs_conflict_flags(view_mode)

    filt = {k: str(v or "") for k, v in (filters or {}).items()}
    role = str(effective_role() or "").strip().casefold()
    query_start, query_end = _query_range_for_view(
        week_start=week_start,
        week_end=week_end,
        selected_day=selected_day,
        view_mode=view_mode,
    )
    cache_key = (
        f"scheduling_page_snapshot:{scheduling_data_version()}:"
        f"{jobs_catalog_data_version()}:{employees_catalog_data_version()}:"
        f"{query_start.isoformat()}:{query_end.isoformat()}:"
        f"{view_mode}:{show_unassigned}:{include_conflicts}:{role}:"
        f"{_filters_cache_token(filt)}"
    )

    def _build() -> SchedulingPageSnapshot:
        warnings: list[str] = []
        with perf_span("scheduling.snapshot"):
            pad_start = week_start - timedelta(days=CONFLICT_PAD_DAYS)
            pad_end = week_end + timedelta(days=CONFLICT_PAD_DAYS)

            with perf_span("scheduling.events_query"):
                pad_events = list_schedule_events(pad_start, pad_end, filters=filt)

            def _event_in_range(ev: dict[str, Any], start: date, end: date) -> bool:
                from app.services.scheduling_conflicts import parse_dt

                ev_start = parse_dt(ev.get("start_at"))
                ev_end = parse_dt(ev.get("end_at"))
                if not ev_start or not ev_end:
                    return False
                range_start = datetime.combine(start, time.min, tzinfo=timezone.utc)
                range_end = datetime.combine(end, time.min, tzinfo=timezone.utc)
                return ev_start < range_end and ev_end > range_start

            events = [
                ev
                for ev in pad_events
                if _event_in_range(ev, query_start, query_end)
            ]

            with perf_span("scheduling.employee_assignments"):
                emp_rows_pad = list_employee_assignments_in_range(pad_start, pad_end)
            with perf_span("scheduling.asset_assignments"):
                asset_rows_pad = list_asset_assignments_in_range(pad_start, pad_end)

            event_ids = {str(ev.get("id") or "").strip() for ev in events if str(ev.get("id") or "").strip()}
            emp_rows, asset_rows = _filter_assignments_to_events(
                emp_rows_pad, asset_rows_pad, event_ids
            )
            emp_by_event, asset_by_event = _assignment_maps_from_rows(emp_rows, asset_rows)

            job_ids, employee_ids, asset_ids, customer_ids = _collect_reference_ids(
                events,
                emp_by_event=emp_by_event,
                asset_by_event=asset_by_event,
                view_mode=view_mode,
                show_unassigned=show_unassigned,
            )

            jobs_by_id = rows_to_by_id(get_jobs_by_ids(sorted(job_ids)))
            for job in jobs_by_id.values():
                cid = str(job.get("customer_id") or "").strip()
                if cid:
                    customer_ids.add(cid)

            employees_by_id = rows_to_by_id(get_people_by_ids(sorted(employee_ids)))
            assets_by_id = rows_to_by_id(get_assets_by_ids(sorted(asset_ids))) if asset_ids else {}
            customers_by_id = rows_to_by_id(get_customers_by_ids(sorted(customer_ids))) if customer_ids else {}

            if view_mode == "Crew" and show_unassigned:
                for row in list_active_employee_roster():
                    eid = str(row.get("id") or "").strip()
                    if eid and eid not in employees_by_id:
                        employees_by_id[eid] = row

            enriched = enrich_events(
                events,
                jobs_by_id=jobs_by_id,
                employees_by_id=employees_by_id,
                customers_by_id=customers_by_id,
                employee_rows_by_event=emp_by_event,
            )

            conflict_ids: set[str] = set()
            if include_conflicts and enriched:
                required_types: set[str] = set()
                for ev in enriched:
                    for cert in ev.get("required_certifications") or []:
                        val = str(cert or "").strip()
                        if val:
                            required_types.add(val)

                employee_certs: list[dict[str, Any]] = []
                if required_types:
                    try:
                        employee_certs = list_relevant_certifications(
                            sorted(employee_ids),
                            sorted(required_types),
                        )
                    except Exception:
                        warnings.append(
                            "Schedule loaded, but certification conflicts could not be checked."
                        )

                supervisor_events = [
                    ev for ev in pad_events if str(ev.get("supervisor_id") or "").strip()
                ]

                availability: list[dict[str, Any]] = []
                try:
                    with perf_span("scheduling.availability"):
                        availability = list_availability_in_range(
                            pad_start,
                            pad_end,
                            employee_ids=sorted(employee_ids),
                        )
                except Exception:
                    warnings.append(
                        "Schedule loaded, but availability conflicts could not be checked."
                    )

                try:
                    conflict_ids = find_conflicting_schedule_event_ids(
                        enriched,
                        employee_assignments=emp_rows_pad,
                        asset_assignments=asset_rows_pad,
                        supervisor_events=supervisor_events,
                        availability_rows=availability,
                        employee_certs=employee_certs,
                        assets_by_id=assets_by_id,
                        employees_by_id=employees_by_id,
                        employee_rows_by_event=emp_by_event,
                        asset_rows_by_event=asset_by_event,
                    )
                except Exception:
                    warnings.append("Schedule loaded, but conflict checks could not be completed.")

            assignment_snapshot = SchedulingAssignmentSnapshot(
                employee_rows=emp_rows_pad,
                asset_rows=asset_rows_pad,
                employee_rows_by_event=emp_by_event,
                asset_rows_by_event=asset_by_event,
            )

            return SchedulingPageSnapshot(
                week_start=week_start,
                week_end=week_end,
                events=enriched,
                employee_assignments_by_event=emp_by_event,
                asset_assignments_by_event=asset_by_event,
                conflict_event_ids=conflict_ids,
                jobs_by_id=jobs_by_id,
                employees_by_id=employees_by_id,
                assets_by_id=assets_by_id,
                customers_by_id=customers_by_id,
                assignment_snapshot=assignment_snapshot,
                warning=" · ".join(warnings) if warnings else None,
            )

    return page_data_cache_get(cache_key, _build)
