"""Focused schedule event detail for fast-path dialog loading."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.pages._core.page_data_cache import page_data_cache_get
from app.perf_debug import perf_span
from app.services.scheduling_conflicts import build_event_conflict_report, parse_dt
from app.services.scheduling_reference_service import (
    get_assets_by_ids,
    get_customers_by_ids,
    get_jobs_by_ids,
    get_people_by_ids,
    list_relevant_certifications,
    rows_to_by_id,
)
from app.services.scheduling_service import (
    get_schedule_event,
    list_asset_assignments_in_range,
    list_availability_in_range,
    list_employee_assignments_in_range,
    list_event_assets,
    list_event_employees,
    scheduling_data_version,
)


def get_schedule_event_detail(event_id: str) -> dict[str, Any] | None:
    """Load one event with focused assignments and reference labels."""
    eid = str(event_id or "").strip()
    if not eid:
        return None

    cache_key = f"scheduling_event_detail:{scheduling_data_version()}:{eid}"

    def _build() -> dict[str, Any] | None:
        with perf_span("scheduling.detail_lookup"):
            event = get_schedule_event(eid)
            if not event:
                return None

            emp_rows = list_event_employees(eid)
            asset_rows = list_event_assets(eid)

            job_ids = [str(event.get("job_id") or "").strip()]
            emp_ids = [str(r.get("employee_id") or "").strip() for r in emp_rows]
            sup_id = str(event.get("supervisor_id") or "").strip()
            if sup_id:
                emp_ids.append(sup_id)
            asset_ids = [str(r.get("asset_id") or "").strip() for r in asset_rows]
            customer_ids = [str(event.get("customer_id") or "").strip()]

            jobs_by_id = rows_to_by_id(get_jobs_by_ids([x for x in job_ids if x]))
            job = jobs_by_id.get(job_ids[0] or "") or {}
            if not customer_ids[0] and job.get("customer_id"):
                customer_ids = [str(job.get("customer_id") or "").strip()]

            employees_by_id = rows_to_by_id(get_people_by_ids([x for x in emp_ids if x]))
            assets_by_id = rows_to_by_id(get_assets_by_ids([x for x in asset_ids if x]))
            customers_by_id = rows_to_by_id(get_customers_by_ids([x for x in customer_ids if x]))

            start = parse_dt(event.get("start_at"))
            end = parse_dt(event.get("end_at"))
            conflict_report = None
            if start and end:
                from datetime import timedelta

                pad_start = start.date() - timedelta(days=14)
                pad_end = end.date() + timedelta(days=14)
                required = list(event.get("required_certifications") or [])
                certs = list_relevant_certifications(emp_ids, required) if required else []
                conflict_report = build_event_conflict_report(
                    start_at=start,
                    end_at=end,
                    employee_ids=[x for x in emp_ids if x and x != sup_id] or emp_ids,
                    asset_ids=[x for x in asset_ids if x],
                    supervisor_id=sup_id,
                    required_certifications=required,
                    employee_assignments=list_employee_assignments_in_range(pad_start, pad_end),
                    supervisor_events=[
                        ev
                        for ev in __import__(
                            "app.services.scheduling_service",
                            fromlist=["list_schedule_events"],
                        ).list_schedule_events(pad_start, pad_end)
                        if str(ev.get("supervisor_id") or "").strip()
                    ],
                    asset_assignments=list_asset_assignments_in_range(pad_start, pad_end),
                    availability_rows=list_availability_in_range(
                        pad_start, pad_end, employee_ids=[x for x in emp_ids if x]
                    ),
                    employee_certs=certs,
                    assets_by_id=assets_by_id,
                    employee_labels={
                        pid: str(
                            (employees_by_id.get(pid) or {}).get("full_name")
                            or (employees_by_id.get(pid) or {}).get("employee_name")
                            or pid
                        )
                        for pid in emp_ids
                        if pid
                    },
                    exclude_event_id=eid,
                )

            return {
                "event": event,
                "employee_rows": emp_rows,
                "asset_rows": asset_rows,
                "jobs_by_id": jobs_by_id,
                "employees_by_id": employees_by_id,
                "assets_by_id": assets_by_id,
                "customers_by_id": customers_by_id,
                "conflict_report": conflict_report,
            }

    return page_data_cache_get(cache_key, _build)


def invalidate_schedule_event_detail_cache(event_id: str | None = None) -> None:
    if event_id:
        prefix = f"scheduling_event_detail:{scheduling_data_version()}:{str(event_id).strip()}"
        cache = st.session_state.get("_ips_page_data_cache") or {}
        if isinstance(cache, dict):
            for key in list(cache.keys()):
                if isinstance(key, str) and key.startswith(prefix.rsplit(":", 1)[0]):
                    cache.pop(key, None)
