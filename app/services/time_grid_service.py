"""Fetch and index weekly grid time entries (public.time_entries)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.db import delete_rows, get_client, insert_row, run_user_supabase_operation, update_rows
def _run_time_entries_query(operation: str, fn):
    return run_user_supabase_operation(operation, fn, friendly_on_failure=False)


def monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_dates(week_start: date) -> list[date]:
    return [week_start + timedelta(days=i) for i in range(7)]


def fetch_time_entries_for_date(work_date: date) -> list[dict[str, Any]]:
    wd = work_date.isoformat()[:10]

    def _run():
        return (
            get_client()
            .table("time_entries")
            .select("*")
            .eq("work_date", wd)
            .limit(20000)
            .execute()
        )

    r = _run_time_entries_query("read time_entries", _run)
    return r.data or []


def fetch_time_entries_between(work_start: date, work_end: date) -> list[dict[str, Any]]:
    def _run():
        return (
            get_client()
            .table("time_entries")
            .select("*")
            .gte("work_date", work_start.isoformat())
            .lte("work_date", work_end.isoformat())
            .limit(20000)
            .execute()
        )

    r = _run_time_entries_query("read time_entries", _run)
    return r.data or []


def index_by_employee_date(entries: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """(employee_id str, work_date iso str) -> list of rows."""
    out: dict[tuple[str, str], list[dict]] = {}
    for e in entries:
        eid = str(e.get("employee_id") or "")
        wd = str(e.get("work_date") or "")[:10]
        if not eid or not wd:
            continue
        out.setdefault((eid, wd), []).append(e)
    for k in out:
        out[k].sort(key=lambda x: str(x.get("id")))
    return out


def sum_employee_week_hours(entries: list[dict], employee_id: str, week_dates_: list[date]) -> float:
    total = 0.0
    wd_set = {d.isoformat() for d in week_dates_}
    for e in entries:
        if str(e.get("employee_id")) != str(employee_id):
            continue
        wds = str(e.get("work_date") or "")[:10]
        if wds in wd_set:
            total += float(e.get("hours", 0) or 0)
    return total


def grid_labor_cost_dollars(hours: float, employee: dict | None, *, time_type: str | None = None) -> float:
    """Grid hours billed at employee burdened rate (respects ST/OT/DT when provided)."""
    if not employee:
        return 0.0
    from app.services.employee_labor import time_entry_burdened_cost
    _, total = time_entry_burdened_cost(
        {"hours": hours, "time_type": time_type or "ST"},
        employee,
    )
    return total


def fetch_entries_employee_between(employee_id: str, work_start: date, work_end: date) -> list[dict[str, Any]]:
    def _run():
        return (
            get_client()
            .table("time_entries")
            .select("*")
            .eq("employee_id", employee_id)
            .gte("work_date", work_start.isoformat())
            .lte("work_date", work_end.isoformat())
            .limit(10000)
            .execute()
        )

    r = _run_time_entries_query("read time_entries", _run)
    return r.data or []


def delete_time_entries_by_ids(entry_ids: list[str]) -> None:
    from app.services.job_cost_transaction_service import (
        SOURCE_TIME_ENTRY,
        delete_job_cost_transaction,
    )
    for eid in entry_ids:
        if eid:
            delete_job_cost_transaction(SOURCE_TIME_ENTRY, str(eid))
            delete_rows("time_entries", {"id": eid})


def delete_employee_work_date(employee_id: str, work_date: date) -> int:
    rows = fetch_entries_employee_between(employee_id, work_date, work_date)
    ids = [str(r.get("id")) for r in rows if r.get("id")]
    delete_time_entries_by_ids(ids)
    return len(ids)


def delete_employee_week(employee_id: str, week_start: date, week_end: date) -> int:
    rows = fetch_entries_employee_between(employee_id, week_start, week_end)
    ids = [str(r.get("id")) for r in rows if r.get("id")]
    delete_time_entries_by_ids(ids)
    return len(ids)


def _normalize_time_type(raw: str | None) -> str:
    s = str(raw or "ST").strip().upper()
    if s in ("OT", "O/T", "O-T"):
        return "OT"
    return "ST"


def upsert_time_entry(
    *,
    employee_id: str,
    job_id: str | None,
    work_date: date,
    hours: float,
    notes: str,
    created_by,
    updated_at_iso: str,
    non_job_code: str | None = None,
    time_type: str | None = None,
) -> None:
    """Insert or update one row: (employee, job, day, ST|OT) or (employee, non_job_code, day, ST|OT)."""
    tt = _normalize_time_type(time_type)
    wd = work_date.isoformat()[:10]

    def _lookup():
        return (
            get_client()
            .table("time_entries")
            .select("id,job_id,non_job_code,time_type")
            .eq("employee_id", employee_id)
            .eq("work_date", wd)
            .limit(500)
            .execute()
        )

    r = _run_time_entries_query("read time_entries", _lookup)
    rows = r.data or []
    row0 = None
    if job_id:
        for row in rows:
            if str(row.get("job_id") or "") == str(job_id) and _normalize_time_type(row.get("time_type")) == tt:
                row0 = row
                break
    else:
        nj = (non_job_code or "").strip()
        if not nj:
            raise ValueError("non_job_code is required when job_id is null")
        for row in rows:
            if not row.get("job_id") and str(row.get("non_job_code") or "").strip() == nj:
                if _normalize_time_type(row.get("time_type")) == tt:
                    row0 = row
                    break
    payload_update: dict[str, Any] = {
        "hours": float(hours or 0),
        "notes": (notes or "").strip(),
        "time_type": tt,
        "updated_at": updated_at_iso,
    }
    if row0:
        update_rows("time_entries", payload_update, {"id": row0["id"]})
        from app.services.job_cost_transaction_service import _safe_sync, sync_time_entry
        merged = {**row0, **payload_update, "id": row0["id"], "employee_id": employee_id, "job_id": job_id, "work_date": wd}
        _safe_sync(sync_time_entry, merged)
        return
    ins: dict[str, Any] = {
        "employee_id": employee_id,
        "work_date": wd,
        "hours": float(hours or 0),
        "notes": (notes or "").strip(),
        "time_type": tt,
        "created_by": created_by,
        "updated_at": updated_at_iso,
    }
    if job_id:
        ins["job_id"] = job_id
        ins["non_job_code"] = None
    else:
        ins["job_id"] = None
        ins["non_job_code"] = (non_job_code or "").strip()
    row = insert_row("time_entries", ins)
    if job_id and row:
        from app.services.job_cost_transaction_service import _safe_sync, sync_time_entry
        _safe_sync(sync_time_entry, row)


def copy_employee_day_to_day(
    *,
    employee_id: str,
    from_date: date,
    to_date: date,
    created_by,
    updated_at_iso: str,
) -> None:
    """Replace destination day with a copy of source day (same jobs, hours, notes)."""
    src = fetch_entries_employee_between(employee_id, from_date, from_date)
    delete_employee_work_date(employee_id, to_date)
    for row in src:
        jid = row.get("job_id")
        nj = str(row.get("non_job_code") or "").strip()
        if jid:
            upsert_time_entry(
                employee_id=employee_id,
                job_id=str(jid),
                work_date=to_date,
                hours=float(row.get("hours", 0) or 0),
                notes=str(row.get("notes") or ""),
                created_by=created_by,
                updated_at_iso=updated_at_iso,
                non_job_code=None,
                time_type=str(row.get("time_type") or "ST"),
            )
        elif nj:
            upsert_time_entry(
                employee_id=employee_id,
                job_id=None,
                work_date=to_date,
                hours=float(row.get("hours", 0) or 0),
                notes=str(row.get("notes") or ""),
                created_by=created_by,
                updated_at_iso=updated_at_iso,
                non_job_code=nj,
                time_type=str(row.get("time_type") or "ST"),
            )


def copy_employee_previous_week_to_current(
    *,
    employee_id: str,
    dest_week_start: date,
    created_by,
    updated_at_iso: str,
) -> None:
    """Replace the current week with a copy of the prior Mon–Sun week for this employee."""
    dest_end = dest_week_start + timedelta(days=6)
    delete_employee_week(employee_id, dest_week_start, dest_end)
    src_start = dest_week_start - timedelta(days=7)
    src_end = src_start + timedelta(days=6)
    src_rows = fetch_entries_employee_between(employee_id, src_start, src_end)
    for row in src_rows:
        wd = row.get("work_date")
        if not wd:
            continue
        s = str(wd)[:10]
        try:
            sd = date.fromisoformat(s)
        except ValueError:
            continue
        dest_date = sd + timedelta(days=7)
        if dest_date < dest_week_start or dest_date > dest_end:
            continue
        jid = row.get("job_id")
        nj = str(row.get("non_job_code") or "").strip()
        if jid:
            upsert_time_entry(
                employee_id=employee_id,
                job_id=str(jid),
                work_date=dest_date,
                hours=float(row.get("hours", 0) or 0),
                notes=str(row.get("notes") or ""),
                created_by=created_by,
                updated_at_iso=updated_at_iso,
                non_job_code=None,
                time_type=str(row.get("time_type") or "ST"),
            )
        elif nj:
            upsert_time_entry(
                employee_id=employee_id,
                job_id=None,
                work_date=dest_date,
                hours=float(row.get("hours", 0) or 0),
                notes=str(row.get("notes") or ""),
                created_by=created_by,
                updated_at_iso=updated_at_iso,
                non_job_code=nj,
                time_type=str(row.get("time_type") or "ST"),
            )


def fill_employee_job_across_week(
    *,
    employee_id: str,
    job_id: str,
    week_dates: list[date],
    hours_per_day: float,
    notes: str,
    created_by,
    updated_at_iso: str,
) -> None:
    for d in week_dates:
        upsert_time_entry(
            employee_id=employee_id,
            job_id=job_id,
            work_date=d,
            hours=hours_per_day,
            notes=notes,
            created_by=created_by,
            updated_at_iso=updated_at_iso,
            time_type="ST",
        )
