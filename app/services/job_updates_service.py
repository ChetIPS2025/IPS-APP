"""Job daily updates — field work performed notes per job (not company_updates)."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.db import (
    delete_rows_admin,
    fetch_by_match_admin,
    fetch_table_admin,
    insert_row_admin,
    update_rows_admin,
)
from app.services.job_weekly_timesheets import monday_of_week, week_bounds
TABLE = "job_daily_updates"
DAILY_UPDATES_MISSING_MSG = (
    "No job daily updates table found. Work performed can be entered manually."
)

_table_available: bool | None = None


def _is_missing_table_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "could not find" in msg or "does not exist" in msg or "schema cache" in msg


def clear_job_daily_updates_cache() -> None:
    global _table_available
    _table_available = None


def daily_updates_table_available(*, force: bool = False) -> bool:
    global _table_available
    if not force and _table_available is not None:
        return _table_available
    try:
        fetch_table_admin(TABLE, columns="id", limit=1)
        _table_available = True
    except Exception as exc:
        if _is_missing_table_error(exc):
            _table_available = False
        else:
            raise
    return bool(_table_available)


def _parse_date(v: Any) -> date | None:
    if isinstance(v, date):
        return v
    if v in (None, ""):
        return None
    try:
        return date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _safe_fetch(job_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
    if not daily_updates_table_available():
        return []
    try:
        return fetch_by_match_admin(TABLE, {"job_id": str(job_id).strip()}, limit=limit) or []
    except Exception as exc:
        if _is_missing_table_error(exc):
            clear_job_daily_updates_cache()
            return []
        raise


def get_job_daily_updates(
    job_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """Return daily updates for a job, optionally filtered to a date range."""
    jid = str(job_id or "").strip()
    if not jid:
        return []
    rows = _safe_fetch(jid)
    if start_date is None and end_date is None:
        return sorted(rows, key=lambda r: str(r.get("update_date") or ""))
    out: list[dict[str, Any]] = []
    for row in rows:
        ud = _parse_date(row.get("update_date"))
        if ud is None:
            continue
        if start_date and ud < start_date:
            continue
        if end_date and ud > end_date:
            continue
        out.append(row)
    return sorted(out, key=lambda r: str(r.get("update_date") or ""))


def get_job_daily_updates_for_week(job_id: str, week_start: date) -> list[dict[str, Any]]:
    ws, we = week_bounds(monday_of_week(week_start))
    return get_job_daily_updates(job_id, start_date=ws, end_date=we)


def _row_text_parts(row: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for key in ("work_performed", "notes", "summary", "delays", "safety_notes"):
        txt = str(row.get(key) or "").strip()
        if txt:
            parts.append(txt)
    weather = str(row.get("weather") or "").strip()
    if weather:
        parts.append(f"Weather: {weather}")
    return parts


def format_work_performed_from_updates(rows: list[dict[str, Any]]) -> str:
    """Combine update rows into a single Work Performed block."""
    lines: list[str] = []
    for row in rows:
        ud = _parse_date(row.get("update_date"))
        parts = _row_text_parts(row)
        if not parts:
            continue
        body = " — ".join(parts)
        if ud:
            lines.append(f"{ud.isoformat()}: {body}")
        else:
            lines.append(body)
    return "\n".join(lines[:20])


def get_work_performed_for_week(job_id: str, week_start: date) -> str:
    rows = get_job_daily_updates_for_week(job_id, week_start)
    return format_work_performed_from_updates(rows)


def create_job_daily_update(data: dict[str, Any]) -> dict[str, Any]:
    if not daily_updates_table_available(force=True):
        raise RuntimeError(DAILY_UPDATES_MISSING_MSG)
    payload = dict(data or {})
    payload.setdefault("update_date", date.today().isoformat())
    row = insert_row_admin(TABLE, payload)
    clear_job_daily_updates_cache()
    return row


def update_job_daily_update(update_id: str, data: dict[str, Any]) -> dict[str, Any]:
    if not daily_updates_table_available(force=True):
        raise RuntimeError(DAILY_UPDATES_MISSING_MSG)
    uid = str(update_id or "").strip()
    if not uid:
        raise ValueError("Update id is required.")
    update_rows_admin(TABLE, {"id": uid}, dict(data or {}))
    rows = fetch_by_match_admin(TABLE, {"id": uid}, limit=1)
    clear_job_daily_updates_cache()
    return rows[0] if rows else {}


def delete_job_daily_update(update_id: str) -> None:
    if not daily_updates_table_available(force=True):
        raise RuntimeError(DAILY_UPDATES_MISSING_MSG)
    uid = str(update_id or "").strip()
    if not uid:
        raise ValueError("Update id is required.")
    delete_rows_admin(TABLE, {"id": uid})
    clear_job_daily_updates_cache()
