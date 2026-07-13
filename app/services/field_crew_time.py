"""Supervisor crew time batches (field entry → submit → approve → time_entries)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.services.field_ops_util import fetch_fn, table_exists, write_fn

_LOG = logging.getLogger(__name__)

TIME_TYPES: tuple[str, ...] = ("ST", "OT", "DT", "Travel", "Per Diem")
OT_WARNING_HOURS = 8.0


def fetch_batch_for_job_date(
    job_id: str,
    work_date: date,
    *,
    admin: bool = False,
) -> dict[str, Any] | None:
    jid = str(job_id or "").strip()
    if not jid or not table_exists("crew_time_batches", admin=admin):
        return None
    fn = fetch_fn(admin=admin)
    rows = fn(
        "crew_time_batches",
        {"job_id": jid, "work_date": work_date.isoformat()[:10]},
        limit=1,
    )
    return rows[0] if rows else None


def fetch_batch_lines(batch_id: str, *, admin: bool = False) -> list[dict[str, Any]]:
    bid = str(batch_id or "").strip()
    if not bid or not table_exists("crew_time_entries", admin=admin):
        return []
    fn = fetch_fn(admin=admin)
    lines = list(fn("crew_time_entries", {"batch_id": bid}, limit=200) or [])
    lines.sort(key=lambda r: int(r.get("sort_order") or 0))
    return lines


def _replace_lines(batch_id: str, lines: list[dict[str, Any]], *, admin: bool) -> None:
    _, _, delete_fn = write_fn(admin=admin)
    insert_fn, _, _ = write_fn(admin=admin)
    delete_fn("crew_time_entries", {"batch_id": batch_id})
    for i, line in enumerate(lines):
        eid = str(line.get("employee_id") or "").strip()
        if not eid:
            continue
        try:
            hrs = float(line.get("hours") or 0)
        except (TypeError, ValueError):
            hrs = 0.0
        if hrs <= 0:
            continue
        tt = str(line.get("time_type") or "ST").strip()
        if tt not in TIME_TYPES:
            tt = "ST"
        insert_fn(
            "crew_time_entries",
            {
                "batch_id": batch_id,
                "employee_id": eid,
                "time_type": tt,
                "hours": round(hrs, 2),
                "notes": str(line.get("notes") or "").strip()[:2000],
                "sort_order": i,
            },
        )


def upsert_crew_time_batch(
    *,
    job_id: str,
    work_date: date,
    supervisor_name: str,
    lines: list[dict[str, Any]],
    notes: str = "",
    status: str = "draft",
    created_by: str | None = None,
    admin: bool = False,
) -> dict[str, Any]:
    jid = str(job_id or "").strip()
    if not jid:
        raise ValueError("job_id required")
    if not table_exists("crew_time_batches", admin=admin):
        raise RuntimeError("crew_time_batches not found — run sql/061_field_operations_phase1.sql")
    insert_fn, update_fn, _ = write_fn(admin=admin)
    existing = fetch_batch_for_job_date(jid, work_date, admin=admin)
    body: dict[str, Any] = {
        "job_id": jid,
        "work_date": work_date.isoformat()[:10],
        "supervisor_name": str(supervisor_name or "").strip()[:200],
        "status": str(status or "draft").strip().lower(),
        "notes": str(notes or "").strip()[:4000],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if existing and existing.get("id"):
        bid = str(existing["id"])
        if str(existing.get("status") or "").lower() == "approved":
            raise RuntimeError("This batch is approved and cannot be edited.")
        update_fn("crew_time_batches", body, {"id": bid})
        _replace_lines(bid, lines, admin=admin)
        out = dict(existing)
        out.update(body)
        return out
    if created_by:
        body["created_by"] = created_by
    row = insert_fn("crew_time_batches", body)
    bid = str(row.get("id") or "").strip()
    if not bid:
        raise RuntimeError("crew_time_batches insert failed")
    _replace_lines(bid, lines, admin=admin)
    return row


def submit_batch(batch_id: str, *, admin: bool = False) -> None:
    _, update_fn, _ = write_fn(admin=admin)
    now = datetime.now(timezone.utc).isoformat()
    update_fn(
        "crew_time_batches",
        {"status": "submitted", "submitted_at": now, "updated_at": now},
        {"id": str(batch_id).strip()},
    )


def approve_batch_and_sync_time_entries(
    batch_id: str,
    *,
    approved_by: str | None = None,
    admin: bool = True,
) -> int:
    """Push approved lines into ``time_entries`` for payroll / job costing."""
    bid = str(batch_id or "").strip()
    if not bid:
        raise ValueError("batch_id required")
    fn = fetch_fn(admin=admin)
    batches = fn("crew_time_batches", {"id": bid}, limit=1)
    if not batches:
        raise RuntimeError("Batch not found")
    batch = batches[0]
    jid = str(batch.get("job_id") or "").strip()
    wd = str(batch.get("work_date") or "")[:10]
    if not jid or not wd:
        raise RuntimeError("Batch missing job or date")
    lines = fetch_batch_lines(bid, admin=admin)
    from app.db import fetch_by_match_admin, insert_row_admin, update_rows_admin
    synced = 0
    for line in lines:
        eid = str(line.get("employee_id") or "").strip()
        if not eid:
            continue
        try:
            hrs = float(line.get("hours") or 0)
        except (TypeError, ValueError):
            hrs = 0.0
        if hrs <= 0:
            continue
        tt = str(line.get("time_type") or "ST").strip()
        if tt not in TIME_TYPES:
            tt = "ST"
        existing = fetch_by_match_admin(
            "time_entries",
            {"employee_id": eid, "job_id": jid, "work_date": wd, "time_type": tt},
            limit=1,
        )
        payload = {
            "employee_id": eid,
            "job_id": jid,
            "work_date": wd,
            "hours": round(hrs, 2),
            "time_type": tt,
            "notes": str(line.get("notes") or "").strip()[:2000],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if existing:
            update_rows_admin("time_entries", payload, {"id": str(existing[0]["id"])})
            entry_id = str(existing[0]["id"])
        else:
            if approved_by:
                payload["created_by"] = approved_by
            inserted = insert_row_admin("time_entries", payload)
            entry_id = str((inserted or {}).get("id") or "")
        from app.services.job_cost_transaction_service import _safe_sync, sync_time_entry
        if entry_id:
            _safe_sync(sync_time_entry, entry_id)
        synced += 1
    _, update_fn, _ = write_fn(admin=admin)
    now = datetime.now(timezone.utc).isoformat()
    update_fn(
        "crew_time_batches",
        {
            "status": "approved",
            "approved_at": now,
            "approved_by": str(approved_by).strip() if approved_by else None,
            "updated_at": now,
        },
        {"id": bid},
    )
    from app.services.job_timeline import EVENT_CREW_TIME, log_job_event
    log_job_event(
        job_id=jid,
        event_type=EVENT_CREW_TIME,
        title="Crew time approved",
        description=f"{synced} line(s) synced to payroll for {wd}",
        related_table="crew_time_batches",
        related_id=bid,
        admin=admin,
    )
    return synced


def overtime_warnings(lines: list[dict[str, Any]]) -> list[str]:
    """Per-employee ST+OT+DT sum > 8h warning."""
    by_emp: dict[str, float] = {}
    for line in lines or []:
        eid = str(line.get("employee_id") or "").strip()
        if not eid:
            continue
        tt = str(line.get("time_type") or "ST")
        if tt in ("Travel", "Per Diem"):
            continue
        try:
            h = float(line.get("hours") or 0)
        except (TypeError, ValueError):
            h = 0.0
        by_emp[eid] = by_emp.get(eid, 0.0) + h
    warnings: list[str] = []
    for eid, total in by_emp.items():
        if total > OT_WARNING_HOURS + 0.01:
            warnings.append(f"Employee {eid[:8]}… has {total:.1f}h (over {OT_WARNING_HOURS:.0f}h ST/OT/DT)")
    return warnings


def copy_yesterday_lines(
    job_id: str,
    work_date: date,
    *,
    admin: bool = False,
) -> list[dict[str, Any]]:
    prev = work_date - timedelta(days=1)
    batch = fetch_batch_for_job_date(job_id, prev, admin=admin)
    if not batch or not batch.get("id"):
        return []
    lines = fetch_batch_lines(str(batch["id"]), admin=admin)
    return [
        {
            "employee_id": str(l.get("employee_id") or ""),
            "time_type": str(l.get("time_type") or "ST"),
            "hours": float(l.get("hours") or 0),
            "notes": str(l.get("notes") or ""),
        }
        for l in lines
        if isinstance(l, dict) and l.get("employee_id")
    ]
