"""Weekly Timekeeping list snapshot — summaries + batch day rows for one week."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import streamlit as st

from app.pages._core._data import load_timekeeping_summaries, timekeeping_catalog_data_version
from app.utils.dates import week_dates, week_end, week_start
from app.utils.permissions import normalize_role

_DAY_FIELD_NAMES: tuple[str, ...] = (
    "monday_hours",
    "tuesday_hours",
    "wednesday_hours",
    "thursday_hours",
    "friday_hours",
    "saturday_hours",
    "sunday_hours",
)


@dataclass(frozen=True)
class WeeklyTimekeepingPage:
    week_start: date
    week_end: date
    employees: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    warning: str | None = None
    is_live: bool = True
    days_loaded: bool = True
    week_days_by_employee: dict[str, list[dict[str, Any]]] | None = None


def _timekeeping_employee_id(row: dict[str, Any]) -> str:
    """Normalize employee id from summary or day rows (prefer employee_id over id)."""
    return str(row.get("employee_id") or row.get("id") or "").strip()


def _float_hours(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def normalize_work_date(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if "T" in raw:
        raw = raw.split("T", 1)[0]
    return raw[:10]


def _day_status_from_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Draft"
    statuses = [str(r.get("status") or "Draft").strip() or "Draft" for r in rows]
    lowered = {s.casefold() for s in statuses}
    if "rejected" in lowered:
        return "Rejected"
    if "pending" in lowered:
        return "Pending"
    if statuses and all(s.casefold() == "approved" for s in statuses):
        return "Approved"
    return "Draft"


def aggregate_daily_display_rows(
    saved_rows: list[dict[str, Any]],
    week_start_d: date,
    *,
    hours_unknown: bool = False,
) -> list[dict[str, Any]]:
    """Build seven lightweight day rows (st/ot/dt totals per calendar date)."""
    days = week_dates(week_start_d)
    if hours_unknown:
        return [
            {
                "date": day.isoformat(),
                "st": 0.0,
                "ot": 0.0,
                "dt": 0.0,
                "status": "Draft",
                "hours_unknown": True,
            }
            for day in days
        ]

    by_date: dict[str, list[dict[str, Any]]] = {}
    for row in saved_rows:
        iso = normalize_work_date(row.get("work_date") or row.get("date"))
        if iso and _work_date_in_week(iso, week_start_d):
            by_date.setdefault(iso, []).append(row)

    out: list[dict[str, Any]] = []
    for day in days:
        iso = day.isoformat()
        day_rows = by_date.get(iso) or []
        if not day_rows:
            out.append(
                {
                    "date": iso,
                    "st": 0.0,
                    "ot": 0.0,
                    "dt": 0.0,
                    "status": "Draft",
                    "hours_unknown": False,
                }
            )
            continue
        out.append(
            {
                "date": iso,
                "st": sum(_float_hours(r.get("st_hours")) for r in day_rows),
                "ot": sum(_float_hours(r.get("ot_hours")) for r in day_rows),
                "dt": sum(_float_hours(r.get("dt_hours")) for r in day_rows),
                "status": _day_status_from_rows(day_rows),
                "hours_unknown": False,
            }
        )
    return out


def _work_date_in_week(work_date: str, week_start_d: date) -> bool:
    iso = normalize_work_date(work_date)
    if not iso:
        return False
    try:
        day = date.fromisoformat(iso)
    except ValueError:
        return False
    end = week_end(week_start_d)
    return week_start_d <= day <= end


def _daily_hours_total(day_row: dict[str, Any]) -> float:
    if day_row.get("hours_unknown"):
        return 0.0
    return (
        _float_hours(day_row.get("st"))
        + _float_hours(day_row.get("ot"))
        + _float_hours(day_row.get("dt"))
    )


def _attach_daily_hour_fields(row: dict[str, Any], daily_rows: list[dict[str, Any]]) -> None:
    for field_name, day_row in zip(_DAY_FIELD_NAMES, daily_rows, strict=False):
        row[field_name] = _daily_hours_total(day_row)


def _timecard_id_for_row(row: dict[str, Any], week_start_d: date) -> str:
    eid = _timekeeping_employee_id(row)
    week_start_str = str(row.get("week_start") or week_start_d.isoformat())[:10]
    return f"{eid}_{week_start_str}"


def _normalize_status(value: object) -> str:
    raw = str(value or "Draft").strip() or "Draft"
    mapping = {
        "pending approval": "Pending",
        "pending": "Pending",
        "approved": "Approved",
        "rejected": "Rejected",
        "draft": "Draft",
    }
    return mapping.get(raw.casefold(), raw)


def _build_employee_row(
    summary: dict[str, Any],
    *,
    week_start_d: date,
    week_days_by_employee: dict[str, list[dict[str, Any]]],
    days_loaded: bool,
    hours_unknown: bool,
) -> dict[str, Any]:
    eid = _timekeeping_employee_id(summary)
    saved_rows = list(week_days_by_employee.get(eid) or [])
    daily_rows = aggregate_daily_display_rows(
        saved_rows,
        week_start_d,
        hours_unknown=hours_unknown,
    )
    summary_st = _float_hours(summary.get("st_total"))
    summary_ot = _float_hours(summary.get("ot_total"))
    summary_dt = _float_hours(summary.get("dt_total"))
    summary_total = summary_st + summary_ot + summary_dt

    if days_loaded and not hours_unknown:
        st_total = sum(_float_hours(d.get("st")) for d in daily_rows)
        ot_total = sum(_float_hours(d.get("ot")) for d in daily_rows)
        dt_total = sum(_float_hours(d.get("dt")) for d in daily_rows)
        total_hours = st_total + ot_total + dt_total
        incomplete = summary_total > 0 and total_hours <= 0
    else:
        st_total = summary_st
        ot_total = summary_ot
        dt_total = summary_dt
        total_hours = summary_total
        incomplete = False

    built = {
        **summary,
        "timecard_id": _timecard_id_for_row(summary, week_start_d),
        "employee_id": eid,
        "employee_name": str(summary.get("name") or summary.get("employee_name") or "—"),
        "department": str(summary.get("department") or summary.get("department_name") or "—") or "—",
        "week_start": str(summary.get("week_start") or week_start_d.isoformat())[:10],
        "st_total": st_total,
        "ot_total": ot_total,
        "dt_total": dt_total,
        "total_hours": total_hours,
        "status": _normalize_status(summary.get("status")),
        "_daily_display_rows": daily_rows,
        "_daily_data_incomplete": incomplete,
        "_daily_hours_unknown": hours_unknown,
    }
    _attach_daily_hour_fields(built, daily_rows)
    return built


def _weekly_page_cache_key(
    *,
    week_start_d: date,
    role: str,
    page: int,
    page_size: int,
    employee_filters: tuple[str, ...] | None,
    status_filters: tuple[str, ...] | None,
) -> str:
    emp_key = ",".join(sorted(employee_filters or ()))
    status_key = ",".join(sorted(status_filters or ()))
    return (
        f"weekly_timekeeping_page:{week_start_d.isoformat()}:"
        f"{normalize_role(role)}:{page}:{page_size}:"
        f"{timekeeping_catalog_data_version()}:"
        f"emp={emp_key}:status={status_key}"
    )


def _load_week_days_batch(week_start_d: date) -> tuple[dict[str, list[dict[str, Any]]], bool, str | None]:
    from app.services.phase2_modules_service import list_timekeeping_days_for_week_with_status

    result = list_timekeeping_days_for_week_with_status(week_start_d)
    by_eid: dict[str, list[dict[str, Any]]] = {}
    for row in result.rows:
        eid = _timekeeping_employee_id(row)
        if eid:
            by_eid.setdefault(eid, []).append(row)
    return by_eid, result.ok, result.error


def _load_weekly_page_uncached(
    *,
    week_start_d: date,
    page: int,
    page_size: int,
    role: str,
    employee_filters: list[str] | None,
    status_filters: list[str] | None,
) -> WeeklyTimekeepingPage:
    from app.perf_debug import perf_span

    normalized_week = week_start(week_start_d)
    week_end_d = week_end(normalized_week)

    with perf_span("timekeeping.employee_summaries"):
        summaries = load_timekeeping_summaries(normalized_week)

    warning: str | None = None
    with perf_span("timekeeping.week_days_batch"):
        week_days_by_employee, days_ok, days_error = _load_week_days_batch(normalized_week)

    hours_unknown = not days_ok
    if days_error:
        warning = "Daily time entries could not be loaded."

    with perf_span("timekeeping.list_build"):
        employees = [
            _build_employee_row(
                summary,
                week_start_d=normalized_week,
                week_days_by_employee=week_days_by_employee,
                days_loaded=days_ok,
                hours_unknown=hours_unknown,
            )
            for summary in summaries
        ]

    if not warning and any(row.get("_daily_data_incomplete") for row in employees):
        warning = "Some weekly totals do not match saved daily entries."

    if employee_filters:
        allowed = {str(v).strip() for v in employee_filters if str(v).strip()}
        employees = [row for row in employees if str(row.get("employee_id") or "") in allowed]
    if status_filters:
        allowed_status = {str(v).strip().casefold() for v in status_filters if str(v).strip()}
        employees = [
            row
            for row in employees
            if str(row.get("status") or "").strip().casefold() in allowed_status
        ]

    return WeeklyTimekeepingPage(
        week_start=normalized_week,
        week_end=week_end_d,
        employees=employees,
        total_count=len(employees),
        page=max(1, int(page or 1)),
        page_size=max(1, int(page_size or 50)),
        warning=warning,
        is_live=True,
        days_loaded=days_ok,
        week_days_by_employee=week_days_by_employee if days_ok else None,
    )


def load_weekly_timekeeping_page(
    *,
    week_start: date,
    page: int = 1,
    page_size: int = 50,
    employee_filters: list[str] | None = None,
    status_filters: list[str] | None = None,
    role: str = "",
) -> WeeklyTimekeepingPage:
    """Load summaries and batch week-day rows for the weekly list UI."""
    from app.perf_debug import perf_span
    from app.utils.dates import week_start as normalize_week_start

    normalized_week = normalize_week_start(week_start)
    cache_key = _weekly_page_cache_key(
        week_start_d=normalized_week,
        role=role,
        page=page,
        page_size=page_size,
        employee_filters=tuple(employee_filters or ()),
        status_filters=tuple(status_filters or ()),
    )

    store = st.session_state.setdefault("_ips_page_data_cache", {})
    cached = store.get(cache_key)
    if isinstance(cached, WeeklyTimekeepingPage) and cached.days_loaded:
        return cached

    with perf_span("timekeeping.week_snapshot"):
        fresh = _load_weekly_page_uncached(
            week_start_d=normalized_week,
            page=page,
            page_size=page_size,
            role=role,
            employee_filters=employee_filters,
            status_filters=status_filters,
        )
    if fresh.days_loaded:
        store[cache_key] = fresh
    return fresh


def seed_week_days_session_cache(
    week_start_d: date,
    week_days_by_employee: dict[str, list[dict[str, Any]]],
) -> None:
    """Share batch week-day rows with legacy page helpers for day editor paths."""
    sig = week_start(week_start_d).isoformat()
    st.session_state["ips_tk_week_days_by_employee"] = week_days_by_employee
    st.session_state["ips_tk_week_days_sig"] = sig


def invalidate_weekly_timekeeping_page_cache(week_start_d: date | None = None) -> None:
    """Invalidate cached weekly list snapshots (optionally one week only)."""
    from app.pages._core.page_data_cache import (
        clear_page_data_cache_key,
        clear_page_data_cache_prefix,
        clear_weekly_timekeeping_page_data_cache,
    )

    if week_start_d is not None:
        ws = week_start(week_start_d).isoformat()
        clear_page_data_cache_prefix(f"weekly_timekeeping_page:{ws}:")
        clear_page_data_cache_key(f"timekeeping_summaries:{ws}")
        if st.session_state.get("ips_tk_week_days_sig") == ws:
            st.session_state.pop("ips_tk_week_days_by_employee", None)
            st.session_state.pop("ips_tk_week_days_sig", None)
        return

    clear_weekly_timekeeping_page_data_cache()
    clear_page_data_cache_prefix("timekeeping_summaries:")


__all__ = [
    "WeeklyTimekeepingPage",
    "_timekeeping_employee_id",
    "aggregate_daily_display_rows",
    "invalidate_weekly_timekeeping_page_cache",
    "load_weekly_timekeeping_page",
    "normalize_work_date",
    "seed_week_days_session_cache",
]
