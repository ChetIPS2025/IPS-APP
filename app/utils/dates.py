"""Date utilities for timekeeping and filters."""

from __future__ import annotations

from datetime import date, timedelta


def week_start(d: date | None = None) -> date:
    ref = d or date.today()
    return ref - timedelta(days=ref.weekday())


def week_end(d: date | None = None) -> date:
    return week_start(d) + timedelta(days=6)


def week_dates(d: date | None = None) -> list[date]:
    start = week_start(d)
    return [start + timedelta(days=i) for i in range(7)]
