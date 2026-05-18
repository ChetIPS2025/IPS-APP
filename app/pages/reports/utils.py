"""Shared formatting and helper utilities for the Reports module."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


def safe_float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def money_str(value: Any) -> str:
    try:
        return f"${float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "—"


def pct_str(value: Any, decimals: int = 1) -> str:
    try:
        return f"{float(value or 0):.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def date_range_for_preset(preset: str, *, today: date | None = None) -> tuple[date, date]:
    """Return (start, end) dates for common preset labels."""
    if today is None:
        today = date.today()
    if preset == "This Week":
        start = today - timedelta(days=today.weekday())
        return start, today
    if preset == "Last 7 Days":
        return today - timedelta(days=6), today
    if preset == "Last 30 Days":
        return today - timedelta(days=29), today
    if preset == "Last 90 Days":
        return today - timedelta(days=89), today
    if preset == "This Month":
        return today.replace(day=1), today
    if preset == "This Year":
        return today.replace(month=1, day=1), today
    # All Time
    return date(2000, 1, 1), today


DATE_RANGE_PRESETS: tuple[str, ...] = (
    "This Week",
    "Last 7 Days",
    "Last 30 Days",
    "Last 90 Days",
    "This Month",
    "This Year",
    "All Time",
    "Custom",
)


def parse_iso_date(v: Any) -> date | None:
    if v is None:
        return None
    s = str(v).strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def parse_iso_datetime(v: Any) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip().replace("Z", "+00:00")
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def in_date_range(v: Any, *, start: date, end: date) -> bool:
    d = parse_iso_date(v)
    if d is None:
        return False
    return start <= d <= end


def truncate(s: Any, length: int = 60) -> str:
    t = str(s or "").strip()
    return t[:length] + "…" if len(t) > length else t
