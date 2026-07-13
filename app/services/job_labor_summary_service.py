"""Approved timekeeping labor rollup for a job (read-only job detail panels)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.db import fetch_table_admin
from app.services.employee_labor import compute_burdened_labor_cost
from app.services.job_weekly_timesheets import monday_of_week, week_bounds
from app.services.weekly_job_timesheet_service import (
    _employees_map,
    _fetch_job,
    _num,
    _parse_date,
    _timekeeping_row_matches_job,
)
def _row_timestamp(row: dict[str, Any]) -> datetime | None:
    for key in ("updated_at", "approved_at", "created_at"):
        raw = str(row.get(key) or "").strip()
        if not raw:
            continue
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
    wd = _parse_date(row.get("work_date"))
    if wd:
        return datetime.combine(wd, datetime.min.time())
    return None


def _round_bucket(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in ("st_hours", "ot_hours", "dt_hours", "total_hours", "labor_cost"):
        out[key] = round(float(out.get(key) or 0), 2)
    return out


def get_job_labor_summary(job_id: str) -> dict[str, Any]:
    """
    Aggregate approved supervisor-entered timekeeping for one job.

    Returns totals, breakdowns by employee and week, and last updated timestamp.
    """
    jid = str(job_id or "").strip()
    empty: dict[str, Any] = {
        "job_id": jid,
        "total_approved_hours": 0.0,
        "st_hours": 0.0,
        "ot_hours": 0.0,
        "dt_hours": 0.0,
        "labor_cost": 0.0,
        "by_employee": [],
        "by_week": [],
        "last_updated": None,
        "last_updated_display": "—",
    }
    if not jid:
        return empty

    job = _fetch_job(jid)
    if not job:
        return empty

    try:
        rows = fetch_table_admin("employee_timekeeping_days", limit=20000)
    except Exception:
        return empty

    try:
        emp_map = _employees_map()
    except Exception:
        emp_map = {}

    emp_buckets: dict[str, dict[str, Any]] = {}
    week_buckets: dict[str, dict[str, Any]] = {}
    st_total = ot_total = dt_total = 0.0
    labor_cost = 0.0
    last_ts: datetime | None = None

    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or "").strip().lower() != "approved":
            continue
        if not _timekeeping_row_matches_job(jid, job, row):
            continue

        st_h = _num(row.get("st_hours"))
        ot_h = _num(row.get("ot_hours"))
        dt_h = _num(row.get("dt_hours"))
        hours = st_h + ot_h + dt_h
        if hours <= 0:
            continue

        eid = str(row.get("employee_id") or "").strip()
        emp = emp_map.get(eid, {})
        emp_name = str(emp.get("name") or row.get("employee_name") or "Unknown").strip()
        cost = compute_burdened_labor_cost(emp, st_h, ot_h, dt_h)

        st_total += st_h
        ot_total += ot_h
        dt_total += dt_h
        labor_cost += cost

        ts = _row_timestamp(row)
        if ts and (last_ts is None or ts > last_ts):
            last_ts = ts

        emp_key = eid or emp_name.lower()
        eb = emp_buckets.setdefault(
            emp_key,
            {
                "employee_id": eid,
                "employee_name": emp_name,
                "st_hours": 0.0,
                "ot_hours": 0.0,
                "dt_hours": 0.0,
                "total_hours": 0.0,
                "labor_cost": 0.0,
            },
        )
        eb["st_hours"] += st_h
        eb["ot_hours"] += ot_h
        eb["dt_hours"] += dt_h
        eb["total_hours"] += hours
        eb["labor_cost"] += cost

        wd = _parse_date(row.get("work_date"))
        if wd:
            ws, we = week_bounds(monday_of_week(wd))
            wk = ws.isoformat()
            wb = week_buckets.setdefault(
                wk,
                {
                    "week_start": ws.isoformat(),
                    "week_end": we.isoformat(),
                    "st_hours": 0.0,
                    "ot_hours": 0.0,
                    "dt_hours": 0.0,
                    "total_hours": 0.0,
                    "labor_cost": 0.0,
                },
            )
            wb["st_hours"] += st_h
            wb["ot_hours"] += ot_h
            wb["dt_hours"] += dt_h
            wb["total_hours"] += hours
            wb["labor_cost"] += cost

    by_employee = sorted(
        [_round_bucket(v) for v in emp_buckets.values()],
        key=lambda r: str(r.get("employee_name") or "").lower(),
    )
    by_week = sorted(
        [_round_bucket(v) for v in week_buckets.values()],
        key=lambda r: str(r.get("week_start") or ""),
        reverse=True,
    )

    last_updated: str | None = None
    last_display = "—"
    if last_ts:
        last_updated = last_ts.isoformat()
        last_display = last_ts.strftime("%Y-%m-%d")

    total_hours = st_total + ot_total + dt_total
    return {
        "job_id": jid,
        "total_approved_hours": round(total_hours, 2),
        "st_hours": round(st_total, 2),
        "ot_hours": round(ot_total, 2),
        "dt_hours": round(dt_total, 2),
        "labor_cost": round(labor_cost, 2),
        "by_employee": by_employee,
        "by_week": by_week,
        "last_updated": last_updated,
        "last_updated_display": last_display,
    }
