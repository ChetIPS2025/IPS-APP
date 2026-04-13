"""
DB-facing helpers for PM matrix time tracking (public.employees, public.time_entries).

Used by services and pages; keeps Supabase/PostgREST access in one place.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

try:
    from db import delete_rows, fetch_by_match, fetch_table, insert_row, update_rows
except ImportError:
    from app.db import delete_rows, fetch_by_match, fetch_table, insert_row, update_rows  # type: ignore

try:
    from services.job_service import sort_jobs_by_number_then_name
except ImportError:
    from app.services.job_service import sort_jobs_by_number_then_name  # type: ignore


# Closed job statuses excluded from matrix rows (case-insensitive); see pm_matrix_service.
_PM_CLOSED_STATUSES = frozenset(
    {"completed", "closed", "cancelled", "canceled", "archived", "on hold", "on_hold"}
)


def fetch_active_employees(*, limit: int = 5000) -> list[dict[str, Any]]:
    """Employees with ``is_active`` and a non-empty ``id``."""
    try:
        rows = fetch_table("employees", limit=limit, order_by="name")
    except Exception:
        return []
    return [e for e in rows if e.get("is_active", True) is not False and e.get("id")]


def fetch_jobs_for_matrix_rows(*, limit: int = 5000) -> list[dict[str, Any]]:
    """
    Jobs suitable for PM matrix row labels: exclude closed statuses; if ``is_active``
    exists on a row and is false, exclude that row. Schemas without ``jobs.is_active``
    rely on ``status`` only.
    """
    try:
        jobs = fetch_table("jobs", limit=limit, order_by="job_number")
    except Exception:
        return []
    jobs = sort_jobs_by_number_then_name(jobs)
    out: list[dict[str, Any]] = []
    for j in jobs:
        if "is_active" in j and j.get("is_active") is False:
            continue
        st = str(j.get("status") or "").strip().lower()
        if st and st in _PM_CLOSED_STATUSES:
            continue
        out.append(j)
    return out if out else jobs


def fetch_time_entries_for_week(week_start: date) -> list[dict[str, Any]]:
    """All ``time_entries`` rows for Mon..Sun of the week containing ``week_start`` (Monday)."""
    week_end = week_start + timedelta(days=6)
    return fetch_time_entries_between(week_start, week_end)


def fetch_time_entries_between(work_start: date, work_end: date) -> list[dict[str, Any]]:
    """Inclusive date range on ``work_date`` (delegates to :mod:`services.time_grid_service`)."""
    try:
        from services.time_grid_service import fetch_time_entries_between as _between
    except ImportError:
        from app.services.time_grid_service import fetch_time_entries_between as _between  # type: ignore

    return _between(work_start, work_end)


def upsert_time_entry_by_key(
    *,
    employee_id: str,
    job_id: str,
    work_date: date,
    hours: float,
    notes: str = "",
    created_by: Any = None,
    updated_at_iso: str | None = None,
) -> None:
    """
    Insert or update the single row for (employee_id, job_id, work_date).
    Delegates to :func:`services.time_grid_service.upsert_time_entry`.
    """
    try:
        from services.time_grid_service import upsert_time_entry
    except ImportError:
        from app.services.time_grid_service import upsert_time_entry  # type: ignore

    from datetime import datetime, timezone

    ts = updated_at_iso or datetime.now(timezone.utc).isoformat()
    upsert_time_entry(
        employee_id=employee_id,
        job_id=job_id,
        work_date=work_date,
        hours=float(hours or 0),
        notes=notes or "",
        created_by=created_by,
        updated_at_iso=ts,
    )


def delete_time_entry_by_natural_key(
    *,
    employee_id: str,
    job_id: str,
    work_date: date,
) -> bool:
    """Delete the row matching (employee_id, job_id, work_date). Returns True if a row was removed."""
    wd = work_date.isoformat()[:10]
    rows = fetch_by_match(
        "time_entries",
        {"employee_id": employee_id, "job_id": job_id, "work_date": wd},
        limit=1,
    )
    if not rows:
        return False
    delete_rows("time_entries", {"id": rows[0]["id"]})
    return True


def save_hours_or_delete(
    *,
    employee_id: str,
    job_id: str,
    work_date: date,
    hours: float | None,
    notes: str = "",
    created_by: Any = None,
    updated_at_iso: str | None = None,
) -> None:
    """
    If ``hours`` is None, blank, or <= 0, delete the natural-key row; otherwise upsert hours + notes.
    """
    try:
        h = float(hours) if hours is not None else 0.0
    except (TypeError, ValueError):
        h = 0.0
    if h <= 0:
        delete_time_entry_by_natural_key(
            employee_id=employee_id,
            job_id=job_id,
            work_date=work_date,
        )
        return
    upsert_time_entry_by_key(
        employee_id=employee_id,
        job_id=job_id,
        work_date=work_date,
        hours=min(h, 999.99),
        notes=notes,
        created_by=created_by,
        updated_at_iso=updated_at_iso,
    )
