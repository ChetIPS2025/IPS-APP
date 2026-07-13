"""Date utilities for timekeeping and filters."""

from __future__ import annotations

from datetime import date, datetime, timedelta

# Streamlit st.date_input / st.datetime_input only accept these display formats.
DATE_INPUT_FORMAT = "MM/DD/YYYY"


def normalize_date(value: date | datetime | str | None) -> date | None:
    """Coerce session, query, or API values into a date for date-input widgets."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value[:10]).date()
        except ValueError:
            return None
    return None


def week_start(d: date | None = None) -> date:
    ref = d or date.today()
    return ref - timedelta(days=ref.weekday())


def week_end(d: date | None = None) -> date:
    return week_start(d) + timedelta(days=6)


def week_dates(d: date | None = None) -> list[date]:
    start = week_start(d)
    return [start + timedelta(days=i) for i in range(7)]
