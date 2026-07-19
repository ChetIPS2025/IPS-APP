"""Scheduling CRUD and date-range queries."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

import streamlit as st

from app.db import delete_rows, get_client, insert_row, run_user_supabase_operation
from app.perf_debug import perf_span
from app.services.repository import ServiceResult, clear_data_cache_for_table, update_row
from app.services.scheduling_conflicts import (
    build_event_conflict_report,
    parse_dt,
)

SCHEDULE_EVENTS_TABLE = "schedule_events"
SCHEDULE_EMPLOYEES_TABLE = "schedule_event_employees"
SCHEDULE_ASSETS_TABLE = "schedule_event_assets"
AVAILABILITY_TABLE = "employee_availability"

EVENT_TYPES: tuple[str, ...] = (
    "job",
    "travel",
    "orientation",
    "training",
    "shop",
    "meeting",
    "outage",
    "time_off",
    "other",
)
EVENT_STATUSES: tuple[str, ...] = (
    "tentative",
    "confirmed",
    "in_progress",
    "completed",
    "cancelled",
)
AVAILABILITY_TYPES: tuple[str, ...] = (
    "unavailable",
    "vacation",
    "sick",
    "training",
    "available",
    "other",
)

_SCHEDULE_CACHE_KEY = "_ips_schedule_events_cache"
_SCHEDULE_RANGE_KEY = "_ips_schedule_range_cache"
_SCHEDULING_DATA_VERSION_KEY = "_ips_scheduling_data_version"
_EXPORT_CACHE_KEY = "_ips_scheduling_export_csv"


def scheduling_data_version() -> int:
    """Monotonic token bumped when schedule data or assignments change."""
    return int(st.session_state.get(_SCHEDULING_DATA_VERSION_KEY) or 0)


def _bump_scheduling_data_version() -> None:
    st.session_state[_SCHEDULING_DATA_VERSION_KEY] = scheduling_data_version() + 1


def invalidate_scheduling_page_cache(*, force: bool = False) -> None:
    """Central cache invalidation for Scheduling page snapshots and exports."""
    _bump_scheduling_data_version()
    for key in (_SCHEDULE_CACHE_KEY, _SCHEDULE_RANGE_KEY, _EXPORT_CACHE_KEY):
        st.session_state.pop(key, None)
    if force:
        from app.pages._core.page_data_cache import clear_page_data_cache_prefix

        clear_page_data_cache_prefix("scheduling_page_snapshot:")
        clear_page_data_cache_prefix("scheduling_event_detail:")
        clear_page_data_cache_prefix("scheduling_filter_options:")
        clear_page_data_cache_prefix("scheduling_form_options:")
        clear_page_data_cache_prefix("scheduling_active_employees:")
        clear_page_data_cache_prefix("scheduling_export_csv:")


def clear_scheduling_cache() -> None:
    """Compatibility entry point — clears repository table caches and bumps version."""
    invalidate_scheduling_page_cache(force=True)
    clear_data_cache_for_table(SCHEDULE_EVENTS_TABLE)
    clear_data_cache_for_table(SCHEDULE_EMPLOYEES_TABLE)
    clear_data_cache_for_table(SCHEDULE_ASSETS_TABLE)
    clear_data_cache_for_table(AVAILABILITY_TABLE)


def _run_query(operation: str, fn):
    return run_user_supabase_operation(operation, fn, friendly_on_failure=False)


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_range(anchor: date) -> tuple[date, date]:
    start = monday_of(anchor)
    end = start + timedelta(days=7)
    return start, end


def _iso_start(d: date) -> str:
    return datetime.combine(d, time.min, tzinfo=timezone.utc).isoformat()


def _iso_end_exclusive(d: date) -> str:
    return datetime.combine(d, time.min, tzinfo=timezone.utc).isoformat()


def _combine_date_time(d: date | None, t: time | None, *, end: bool = False) -> datetime | None:
    if d is None:
        return None
    if t is None:
        t = time(23, 59, 59) if end else time(0, 0, 0)
    return datetime.combine(d, t, tzinfo=timezone.utc)


def list_schedule_events(
    start_at: datetime | date,
    end_at: datetime | date,
    *,
    filters: dict[str, Any] | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Server-side range query: events overlapping [start_at, end_at)."""
    if isinstance(start_at, date) and not isinstance(start_at, datetime):
        range_start = _iso_start(start_at)
    else:
        range_start = parse_dt(start_at)
        range_start = range_start.isoformat() if range_start else _iso_start(date.today())

    if isinstance(end_at, date) and not isinstance(end_at, datetime):
        range_end = _iso_end_exclusive(end_at)
    else:
        range_end = parse_dt(end_at)
        range_end = range_end.isoformat() if range_end else _iso_end_exclusive(date.today() + timedelta(days=7))

    filt = filters or {}

    def _run():
        q = (
            get_client()
            .table(SCHEDULE_EVENTS_TABLE)
            .select("*")
            .lt("start_at", range_end)
            .gt("end_at", range_start)
            .order("start_at")
            .limit(limit)
        )
        status = str(filt.get("status") or "").strip()
        if status and status.lower() not in {"all", "all statuses"}:
            q = q.eq("status", status.lower())
        job_id = str(filt.get("job_id") or "").strip()
        if job_id:
            q = q.eq("job_id", job_id)
        supervisor_id = str(filt.get("supervisor_id") or "").strip()
        if supervisor_id:
            q = q.eq("supervisor_id", supervisor_id)
        customer_id = str(filt.get("customer_id") or "").strip()
        if customer_id:
            q = q.eq("customer_id", customer_id)
        event_type = str(filt.get("event_type") or "").strip()
        if event_type and event_type.lower() != "all":
            q = q.eq("event_type", event_type.lower())
        resp = q.execute()
        return list(resp.data or [])

    with perf_span("scheduling.list_events"):
        try:
            return _run_query("read schedule_events", _run)
        except Exception:
            return []


def get_schedule_event(event_id: str) -> dict[str, Any] | None:
    eid = str(event_id or "").strip()
    if not eid:
        return None

    def _run():
        return (
            get_client()
            .table(SCHEDULE_EVENTS_TABLE)
            .select("*")
            .eq("id", eid)
            .limit(1)
            .execute()
        )

    try:
        resp = _run_query("read schedule_event", _run)
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def list_event_employees(event_id: str) -> list[dict[str, Any]]:
    eid = str(event_id or "").strip()
    if not eid:
        return []

    def _run():
        return (
            get_client()
            .table(SCHEDULE_EMPLOYEES_TABLE)
            .select("*")
            .eq("schedule_event_id", eid)
            .execute()
        )

    try:
        resp = _run_query("read schedule_event_employees", _run)
        return list(resp.data or [])
    except Exception:
        return []


def list_event_assets(event_id: str) -> list[dict[str, Any]]:
    eid = str(event_id or "").strip()
    if not eid:
        return []

    def _run():
        return (
            get_client()
            .table(SCHEDULE_ASSETS_TABLE)
            .select("*")
            .eq("schedule_event_id", eid)
            .execute()
        )

    try:
        resp = _run_query("read schedule_event_assets", _run)
        return list(resp.data or [])
    except Exception:
        return []


def list_employee_assignments_in_range(
    start_at: datetime | date,
    end_at: datetime | date,
    *,
    limit: int = 2000,
) -> list[dict[str, Any]]:
    """Employee assignment rows joined with parent event window for conflict checks."""

    def _run():
        if isinstance(start_at, date) and not isinstance(start_at, datetime):
            rs = _iso_start(start_at)
        else:
            dt = parse_dt(start_at)
            rs = dt.isoformat() if dt else _iso_start(date.today())
        if isinstance(end_at, date) and not isinstance(end_at, datetime):
            re = _iso_end_exclusive(end_at)
        else:
            dt = parse_dt(end_at)
            re = dt.isoformat() if dt else _iso_end_exclusive(date.today() + timedelta(days=7))
        resp = (
            get_client()
            .table(SCHEDULE_EMPLOYEES_TABLE)
            .select("*, schedule_events!inner(id, title, start_at, end_at, status)")
            .lt("schedule_events.start_at", re)
            .gt("schedule_events.end_at", rs)
            .limit(limit)
            .execute()
        )
        rows = []
        for row in resp.data or []:
            ev = row.pop("schedule_events", {}) or {}
            merged = {**row, **ev}
            merged["schedule_event_id"] = str(merged.get("schedule_event_id") or ev.get("id") or "")
            rows.append(merged)
        return rows

    with perf_span("scheduling.employee_assignments"):
        try:
            return _run_query("read schedule employee assignments", _run)
        except Exception:
            return []


def list_asset_assignments_in_range(
    start_at: datetime | date,
    end_at: datetime | date,
    *,
    limit: int = 2000,
) -> list[dict[str, Any]]:
    def _run():
        if isinstance(start_at, date) and not isinstance(start_at, datetime):
            rs = _iso_start(start_at)
        else:
            dt = parse_dt(start_at)
            rs = dt.isoformat() if dt else _iso_start(date.today())
        if isinstance(end_at, date) and not isinstance(end_at, datetime):
            re = _iso_end_exclusive(end_at)
        else:
            dt = parse_dt(end_at)
            re = dt.isoformat() if dt else _iso_end_exclusive(date.today() + timedelta(days=7))
        resp = (
            get_client()
            .table(SCHEDULE_ASSETS_TABLE)
            .select("*, schedule_events!inner(id, title, start_at, end_at, status)")
            .lt("schedule_events.start_at", re)
            .gt("schedule_events.end_at", rs)
            .limit(limit)
            .execute()
        )
        rows = []
        for row in resp.data or []:
            ev = row.pop("schedule_events", {}) or {}
            merged = {**row, **ev}
            merged["schedule_event_id"] = str(merged.get("schedule_event_id") or ev.get("id") or "")
            rows.append(merged)
        return rows

    with perf_span("scheduling.asset_assignments"):
        try:
            return _run_query("read schedule asset assignments", _run)
        except Exception:
            return []


def list_supervisor_events_in_range(
    start_at: datetime | date,
    end_at: datetime | date,
    *,
    limit: int = 500,
) -> list[dict[str, Any]]:
    events = list_schedule_events(start_at, end_at, limit=limit)
    return [e for e in events if str(e.get("supervisor_id") or "").strip()]


def list_employee_availability(
    employee_id: str,
    start_at: datetime | date,
    end_at: datetime | date,
) -> list[dict[str, Any]]:
    eid = str(employee_id or "").strip()
    if not eid:
        return []
    if isinstance(start_at, date) and not isinstance(start_at, datetime):
        rs = _iso_start(start_at)
    else:
        dt = parse_dt(start_at)
        rs = dt.isoformat() if dt else _iso_start(date.today())
    if isinstance(end_at, date) and not isinstance(end_at, datetime):
        re = _iso_end_exclusive(end_at)
    else:
        dt = parse_dt(end_at)
        re = dt.isoformat() if dt else _iso_end_exclusive(date.today() + timedelta(days=7))

    def _run():
        return (
            get_client()
            .table(AVAILABILITY_TABLE)
            .select("*")
            .eq("employee_id", eid)
            .lt("start_at", re)
            .gt("end_at", rs)
            .execute()
        )

    try:
        resp = _run_query("read employee_availability", _run)
        return list(resp.data or [])
    except Exception:
        return []


def list_availability_in_range(
    start_at: datetime | date,
    end_at: datetime | date,
    *,
    employee_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    if isinstance(start_at, date) and not isinstance(start_at, datetime):
        rs = _iso_start(start_at)
    else:
        dt = parse_dt(start_at)
        rs = dt.isoformat() if dt else _iso_start(date.today())
    if isinstance(end_at, date) and not isinstance(end_at, datetime):
        re = _iso_end_exclusive(end_at)
    else:
        dt = parse_dt(end_at)
        re = dt.isoformat() if dt else _iso_end_exclusive(date.today() + timedelta(days=7))

    def _run():
        q = (
            get_client()
            .table(AVAILABILITY_TABLE)
            .select("*")
            .lt("start_at", re)
            .gt("end_at", rs)
        )
        resp = q.limit(2000).execute()
        return list(resp.data or [])

    try:
        rows = _run_query("read availability range", _run)
    except Exception:
        return []
    if employee_ids:
        wanted = {str(x).strip() for x in employee_ids if str(x).strip()}
        return [r for r in rows if str(r.get("employee_id") or "").strip() in wanted]
    return rows


def list_employee_schedule(
    employee_id: str,
    start_at: datetime | date,
    end_at: datetime | date,
) -> list[dict[str, Any]]:
    eid = str(employee_id or "").strip()
    if not eid:
        return []
    assignments = list_employee_assignments_in_range(start_at, end_at)
    event_ids = {
        str(a.get("schedule_event_id") or "").strip()
        for a in assignments
        if str(a.get("employee_id") or "").strip() == eid
    }
    events = list_schedule_events(start_at, end_at)
    out = [e for e in events if str(e.get("id") or "").strip() in event_ids]
    out.sort(key=lambda r: str(r.get("start_at") or ""))
    return out


def list_upcoming_employee_schedule(employee_id: str, *, limit: int = 4) -> list[dict[str, Any]]:
    """Next non-cancelled assignments for an employee (employee portal)."""
    start = date.today()
    end = start + timedelta(days=120)
    rows = list_employee_schedule(employee_id, start, end)
    out: list[dict[str, Any]] = []
    for ev in rows:
        if str(ev.get("status") or "").strip().lower() == "cancelled":
            continue
        out.append(ev)
        if len(out) >= limit:
            break
    return out


def schedule_suggestion_for_employee_day(employee_id: str, work_date: date) -> dict[str, Any] | None:
    """Planned assignment hint for timekeeping (does not mutate time entries)."""
    eid = str(employee_id or "").strip()
    if not eid:
        return None
    day_start = datetime.combine(work_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(work_date, time.max, tzinfo=timezone.utc)
    events = list_employee_schedule(eid, day_start, day_end)
    for ev in events:
        if str(ev.get("status") or "").strip().lower() == "cancelled":
            continue
        s, e = parse_dt(ev.get("start_at")), parse_dt(ev.get("end_at"))
        hours = event_hours(s, e) if s and e else 0.0
        return {
            "event_id": str(ev.get("id") or ""),
            "title": str(ev.get("title") or "Scheduled assignment"),
            "job_id": str(ev.get("job_id") or ""),
            "work_date": work_date.isoformat(),
            "expected_hours": round(hours, 2),
            "shift": str(ev.get("shift_name") or ""),
            "location": str(ev.get("location") or ""),
        }
    return None


def schedule_suggestion_for_job_day(job_id: str, report_date: date) -> dict[str, Any] | None:
    """Planned crew/equipment hint for daily reports."""
    jid = str(job_id or "").strip()
    if not jid:
        return None
    day_start = datetime.combine(report_date, time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(report_date, time.max, tzinfo=timezone.utc)
    events = [e for e in list_schedule_events(day_start, day_end, filters={"job_id": jid})]
    for ev in events:
        if str(ev.get("status") or "").strip().lower() == "cancelled":
            continue
        eid = str(ev.get("id") or "").strip()
        crew = list_event_employees(eid) if eid else []
        assets = list_event_assets(eid) if eid else []
        return {
            "event_id": eid,
            "title": str(ev.get("title") or "Scheduled work"),
            "shift": str(ev.get("shift_name") or ""),
            "work_instructions": str(ev.get("work_instructions") or ""),
            "employees": crew,
            "assets": assets,
        }
    return None


def list_job_schedule(job_id: str) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid:
        return []

    def _run():
        return (
            get_client()
            .table(SCHEDULE_EVENTS_TABLE)
            .select("*")
            .eq("job_id", jid)
            .order("start_at")
            .limit(200)
            .execute()
        )

    try:
        resp = _run_query("read job schedule", _run)
        return list(resp.data or [])
    except Exception:
        return []


def list_asset_schedule(
    asset_id: str,
    start_at: datetime | date,
    end_at: datetime | date,
) -> list[dict[str, Any]]:
    aid = str(asset_id or "").strip()
    if not aid:
        return []
    rows = list_asset_assignments_in_range(start_at, end_at)
    event_ids = {
        str(r.get("schedule_event_id") or "").strip()
        for r in rows
        if str(r.get("asset_id") or "").strip() == aid
    }
    events = list_schedule_events(start_at, end_at)
    return [e for e in events if str(e.get("id") or "").strip() in event_ids]


def _normalize_event_payload(payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload or {})
    for key in ("event_type", "status"):
        if key in body and body[key] is not None:
            body[key] = str(body[key]).strip().lower()
    if "required_certifications" in body and body["required_certifications"] is None:
        body["required_certifications"] = []
    return body


def create_schedule_event(payload: dict[str, Any]) -> ServiceResult:
    body = _normalize_event_payload(payload)
    result = insert_row(SCHEDULE_EVENTS_TABLE, body)
    if result.ok:
        clear_scheduling_cache()
    return result


def update_schedule_event(event_id: str, payload: dict[str, Any]) -> ServiceResult:
    eid = str(event_id or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Missing event id.")
    body = _normalize_event_payload(payload)
    result = update_row(SCHEDULE_EVENTS_TABLE, body, {"id": eid})
    if result.ok:
        clear_scheduling_cache()
    return result


def delete_schedule_event(event_id: str) -> ServiceResult:
    eid = str(event_id or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Missing event id.")
    try:
        delete_rows(SCHEDULE_EMPLOYEES_TABLE, {"schedule_event_id": eid})
        delete_rows(SCHEDULE_ASSETS_TABLE, {"schedule_event_id": eid})
        delete_rows(SCHEDULE_EVENTS_TABLE, {"id": eid})
        clear_scheduling_cache()
        return ServiceResult(ok=True)
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))


def replace_event_employees(
    event_id: str,
    employee_ids: list[str],
    *,
    supervisor_flags: dict[str, bool] | None = None,
) -> ServiceResult:
    eid = str(event_id or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Missing event id.")
    flags = supervisor_flags or {}
    try:
        delete_rows(SCHEDULE_EMPLOYEES_TABLE, {"schedule_event_id": eid})
        for emp_id in employee_ids:
            emp = str(emp_id or "").strip()
            if not emp:
                continue
            insert_row(
                SCHEDULE_EMPLOYEES_TABLE,
                {
                    "schedule_event_id": eid,
                    "employee_id": emp,
                    "is_supervisor": bool(flags.get(emp)),
                },
            )
        clear_scheduling_cache()
        return ServiceResult(ok=True)
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))


def replace_event_assets(event_id: str, asset_ids: list[str]) -> ServiceResult:
    eid = str(event_id or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Missing event id.")
    try:
        delete_rows(SCHEDULE_ASSETS_TABLE, {"schedule_event_id": eid})
        for aid in asset_ids:
            asset_id = str(aid or "").strip()
            if not asset_id:
                continue
            insert_row(
                SCHEDULE_ASSETS_TABLE,
                {
                    "schedule_event_id": eid,
                    "asset_id": asset_id,
                    "quantity": 1,
                },
            )
        clear_scheduling_cache()
        return ServiceResult(ok=True)
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))


def enrich_events(
    events: list[dict[str, Any]],
    *,
    jobs_by_id: dict[str, dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
    customers_by_id: dict[str, dict[str, Any]] | None = None,
    employee_rows_by_event: dict[str, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    customers = customers_by_id or {}
    emp_map = employee_rows_by_event or {}
    out: list[dict[str, Any]] = []
    for ev in events:
        row = dict(ev)
        jid = str(row.get("job_id") or "").strip()
        job = jobs_by_id.get(jid) or {}
        if job:
            row.setdefault("job_number", job.get("job_number"))
            row.setdefault("job_name", job.get("job_name") or job.get("project_name"))
            row.setdefault("customer_name", job.get("customer") or job.get("customer_name"))
        cid = str(row.get("customer_id") or "").strip()
        cust = customers.get(cid) or {}
        if cust:
            row.setdefault("customer_name", cust.get("customer_name") or cust.get("company_name"))
        sid = str(row.get("supervisor_id") or "").strip()
        sup = employees_by_id.get(sid) or {}
        if sup:
            row["supervisor_name"] = (
                sup.get("full_name") or sup.get("employee_name") or sup.get("name") or "—"
            )
        eid = str(row.get("id") or "").strip()
        assigned = emp_map.get(eid)
        if assigned is None and eid:
            assigned = list_event_employees(eid)
        row["assigned_employee_count"] = len(assigned or [])
        out.append(row)
    return out


def compute_event_conflicts(
    payload: dict[str, Any],
    *,
    employee_ids: list[str],
    asset_ids: list[str],
    exclude_event_id: str = "",
    employee_certs: list[dict[str, Any]] | None = None,
    assets_by_id: dict[str, dict[str, Any]] | None = None,
    employee_labels: dict[str, str] | None = None,
    range_pad_days: int = 14,
) -> Any:
    start = parse_dt(payload.get("start_at"))
    end = parse_dt(payload.get("end_at"))
    if not start or not end:
        from app.services.scheduling_conflicts import ConflictReport

        return ConflictReport()

    pad_start = start.date() - timedelta(days=range_pad_days)
    pad_end = end.date() + timedelta(days=range_pad_days)

    with perf_span("scheduling.conflicts"):
        return build_event_conflict_report(
            start_at=start,
            end_at=end,
            employee_ids=employee_ids,
            asset_ids=asset_ids,
            supervisor_id=str(payload.get("supervisor_id") or "").strip(),
            required_certifications=list(payload.get("required_certifications") or []),
            employee_assignments=list_employee_assignments_in_range(pad_start, pad_end),
            supervisor_events=list_supervisor_events_in_range(pad_start, pad_end),
            asset_assignments=list_asset_assignments_in_range(pad_start, pad_end),
            availability_rows=list_availability_in_range(pad_start, pad_end, employee_ids=employee_ids),
            employee_certs=employee_certs or [],
            assets_by_id=assets_by_id or {},
            employee_labels=employee_labels,
            exclude_event_id=exclude_event_id,
        )


def validate_schedule_event_draft(
    *,
    event_id: str | None,
    start_at: object,
    end_at: object,
    employee_ids: list[str],
    asset_ids: list[str],
    supervisor_id: str | None,
    required_certifications: list[str],
    employee_certs: list[dict[str, Any]] | None = None,
    assets_by_id: dict[str, dict[str, Any]] | None = None,
    employee_labels: dict[str, str] | None = None,
    range_pad_days: int = 14,
) -> Any:
    """Conflict validation for a single draft event — scoped overlapping resources only."""
    start = parse_dt(start_at)
    end = parse_dt(end_at)
    if not start or not end:
        from app.services.scheduling_conflicts import ConflictReport

        return ConflictReport()

    pad_start = start.date() - timedelta(days=range_pad_days)
    pad_end = end.date() + timedelta(days=range_pad_days)
    exclude_event_id = str(event_id or "").strip()
    scoped_assets = assets_by_id or {}
    if asset_ids and not scoped_assets:
        from app.services.scheduling_reference_service import get_assets_by_ids, rows_to_by_id

        scoped_assets = rows_to_by_id(get_assets_by_ids(asset_ids))

    with perf_span("scheduling.dialog_validation"):
        emp_assignments = list_employee_assignments_in_range(pad_start, pad_end)
        asset_assignments = list_asset_assignments_in_range(pad_start, pad_end)
        supervisor_events = list_supervisor_events_in_range(pad_start, pad_end)
        availability = list_availability_in_range(pad_start, pad_end, employee_ids=employee_ids)
        certs = employee_certs
        if certs is None and required_certifications:
            from app.services.scheduling_reference_service import list_relevant_certifications

            certs = list_relevant_certifications(employee_ids, required_certifications)
        return build_event_conflict_report(
            start_at=start,
            end_at=end,
            employee_ids=employee_ids,
            asset_ids=asset_ids,
            supervisor_id=str(supervisor_id or "").strip(),
            required_certifications=list(required_certifications or []),
            employee_assignments=emp_assignments,
            supervisor_events=supervisor_events,
            asset_assignments=asset_assignments,
            availability_rows=availability,
            employee_certs=certs or [],
            assets_by_id=scoped_assets,
            employee_labels=employee_labels,
            exclude_event_id=exclude_event_id,
        )


def event_hours(start_at: object, end_at: object) -> float:
    s = parse_dt(start_at)
    e = parse_dt(end_at)
    if not s or not e:
        return 0.0
    return max(0.0, (e - s).total_seconds() / 3600.0)


def build_weekly_schedule_export_rows(
    events: list[dict[str, Any]],
    *,
    jobs_by_id: dict[str, dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
    employee_rows_by_event: dict[str, list[dict[str, Any]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for ev in events:
        if str(ev.get("status") or "").strip().lower() == "cancelled":
            continue
        eid = str(ev.get("id") or "").strip()
        job = jobs_by_id.get(str(ev.get("job_id") or "").strip()) or {}
        for assign in employee_rows_by_event.get(eid) or []:
            emp_id = str(assign.get("employee_id") or "").strip()
            emp = employees_by_id.get(emp_id) or {}
            emp_name = str(emp.get("full_name") or emp.get("employee_name") or emp.get("name") or emp_id)
            rows.append(
                {
                    "employee": emp_name,
                    "job_event": str(ev.get("title") or job.get("job_number") or "Event"),
                    "date": str(ev.get("start_at") or "")[:10],
                    "shift_time": f"{str(ev.get('start_at') or '')[11:16]} - {str(ev.get('end_at') or '')[11:16]}",
                    "location": str(ev.get("location") or job.get("location") or ""),
                    "supervisor": str(ev.get("supervisor_name") or ""),
                    "per_diem": str(ev.get("per_diem_amount") or ""),
                    "lodging_notes": str(ev.get("lodging_name") or ""),
                    "equipment_summary": "",
                }
            )
    return rows
