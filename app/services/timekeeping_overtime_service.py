"""Automatic straight-time / overtime classification for weekly timekeeping allocations."""

from __future__ import annotations

from datetime import date
from typing import Any

WEEKLY_ST_THRESHOLD = 40.0
_TIME_TYPE_ST = "ST"
_TIME_TYPE_OT = "OT"


def normalize_time_type(raw: object) -> str:
    s = str(raw or _TIME_TYPE_ST).strip().upper().replace(".", "").replace(" ", "").replace("/", "")
    if s in {_TIME_TYPE_OT, "OVERTIME"}:
        return _TIME_TYPE_OT
    return _TIME_TYPE_ST


def is_weekend_date(work_date: date) -> bool:
    return work_date.weekday() >= 5


def _line_hours(line: dict[str, Any]) -> float:
    try:
        return max(0.0, float(line.get("hours") or 0))
    except (TypeError, ValueError):
        return 0.0


def _line_has_valid_assignment(line: dict[str, Any]) -> bool:
    job = str(line.get("job") or "").strip()
    if not job:
        return False
    return job.casefold() != "— no assignment —"


def _line_is_locked(line: dict[str, Any]) -> bool:
    status = str(line.get("status") or "Draft").strip().title()
    return status in {"Approved", "Pending"}


def _counts_toward_weekday_st(
    work_date: date,
    final_type: str,
    *,
    weekend_counts_toward_40: bool,
) -> bool:
    if normalize_time_type(final_type) != _TIME_TYPE_ST:
        return False
    if is_weekend_date(work_date):
        return weekend_counts_toward_40
    return True


def peek_line_time_type(
    *,
    work_date: date,
    hours: float,
    weekday_st_used: float,
    weekend_counts_toward_40: bool = False,
) -> str:
    """Classify one line without mutating the running weekday S/T counter."""
    hrs = max(0.0, float(hours or 0))
    if hrs <= 0:
        return _TIME_TYPE_ST

    if is_weekend_date(work_date):
        if weekend_counts_toward_40:
            remaining_st = max(0.0, WEEKLY_ST_THRESHOLD - weekday_st_used)
            return _TIME_TYPE_ST if hrs <= remaining_st else _TIME_TYPE_OT
        return _TIME_TYPE_OT

    remaining_st = max(0.0, WEEKLY_ST_THRESHOLD - weekday_st_used)
    return _TIME_TYPE_ST if hrs <= remaining_st else _TIME_TYPE_OT


def recalculate_week_allocations(
    by_date: dict[str, list[dict[str, Any]]],
    week_start_d: date,
    *,
    week_dates_fn: Any,
    weekend_counts_toward_40: bool = False,
    preserve_locked: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """
    Assign calculated_time_type chronologically across the workweek.

    Weekend hours default to O/T and do not consume the 40-hour weekday S/T
    bucket unless ``weekend_counts_toward_40`` is enabled.
    Admin overrides and approved/pending rows keep their final type.
    """
    ordered: list[tuple[date, int, dict[str, Any]]] = []
    for day_d in week_dates_fn(week_start_d):
        iso = day_d.isoformat()
        for lix, line in enumerate(by_date.get(iso) or []):
            ordered.append((day_d, lix, dict(line)))

    weekday_st_used = 0.0
    updated: dict[str, list[dict[str, Any]]] = {iso: list(lines) for iso, lines in by_date.items()}

    for day_d, lix, line in ordered:
        iso = day_d.isoformat()
        lines = list(updated.get(iso) or [])
        if lix >= len(lines):
            continue

        hours = _line_hours(line)
        if hours <= 0 or not _line_has_valid_assignment(line):
            out = dict(line)
            out["calculated_time_type"] = _TIME_TYPE_ST
            out.setdefault("final_time_type", _TIME_TYPE_ST)
            out["hour_type"] = normalize_time_type(out.get("final_time_type"))
            lines[lix] = out
            updated[iso] = lines
            continue

        calculated = peek_line_time_type(
            work_date=day_d,
            hours=hours,
            weekday_st_used=weekday_st_used,
            weekend_counts_toward_40=weekend_counts_toward_40,
        )

        if line.get("overtime_override"):
            final = normalize_time_type(line.get("final_time_type") or line.get("hour_type") or calculated)
        elif preserve_locked and _line_is_locked(line):
            final = normalize_time_type(line.get("final_time_type") or line.get("hour_type") or calculated)
        else:
            final = calculated

        out = dict(line)
        out["calculated_time_type"] = calculated
        out["final_time_type"] = final
        out["hour_type"] = final
        lines[lix] = out
        updated[iso] = lines

        if _counts_toward_weekday_st(day_d, final, weekend_counts_toward_40=weekend_counts_toward_40):
            weekday_st_used += hours

    return updated


def summarize_week_hours(by_date: dict[str, list[dict[str, Any]]]) -> dict[str, float]:
    st_total = 0.0
    ot_total = 0.0
    for lines in by_date.values():
        for line in lines or []:
            hrs = _line_hours(line)
            if hrs <= 0 or not _line_has_valid_assignment(line):
                continue
            final = normalize_time_type(line.get("final_time_type") or line.get("hour_type"))
            if final == _TIME_TYPE_OT:
                ot_total += hrs
            else:
                st_total += hrs
    return {
        "st_total": round(st_total, 2),
        "ot_total": round(ot_total, 2),
        "total_hours": round(st_total + ot_total, 2),
    }


def overtime_policy_note(*, weekend_counts_toward_40: bool = False) -> str:
    base = "Saturday/Sunday hours are overtime. Weekday hours over 40 are overtime."
    if weekend_counts_toward_40:
        return base + " Weekend hours count toward the 40-hour straight-time threshold (company setting)."
    return base


def new_allocation_line_defaults(**extra: Any) -> dict[str, Any]:
    base = {
        "line_id": "",
        "job": "",
        "hour_type": _TIME_TYPE_ST,
        "hours": 0.0,
        "notes": "",
        "status": "Draft",
        "calculated_time_type": _TIME_TYPE_ST,
        "final_time_type": _TIME_TYPE_ST,
        "overtime_override": False,
        "overtime_override_by": None,
        "overtime_override_at": None,
        "overtime_override_reason": None,
    }
    base.update(extra)
    return base
