"""Autofill QYY### / JYY### numbers in New Estimate and New Job forms."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import streamlit as st

try:
    from app.services.shared_sequence import (
        peek_quote_job_number,
        quote_number_to_job_number,
    )
except ImportError:
    from services.shared_sequence import (  # type: ignore
        peek_quote_job_number,
        quote_number_to_job_number,
    )


def _year_from_value(value: Any) -> int:
    if isinstance(value, datetime):
        return value.year
    if isinstance(value, date):
        return value.year
    if value not in (None, ""):
        try:
            return date.fromisoformat(str(value)[:10]).year
        except ValueError:
            pass
    return date.today().year


def _mark_manual(manual_key: str) -> None:
    st.session_state[manual_key] = True


def clear_new_estimate_number_state() -> None:
    for key in (
        "est_new_num_seed",
        "est_new_num_manual",
        "est_new_num_year",
        "est_new_num",
    ):
        st.session_state.pop(key, None)


def clear_new_job_number_state() -> None:
    for key in (
        "job_new_num_seed",
        "job_new_num_manual",
        "job_new_num_year",
        "job_new_num",
    ):
        st.session_state.pop(key, None)


def sync_new_estimate_number(*, date_key: str = "est_new_est_date") -> None:
    """Allocate or refresh estimate # from estimate date unless the user edited it."""
    manual_key = "est_new_num_manual"
    seed_key = "est_new_num_seed"
    number_key = "est_new_num"
    year_key = "est_new_num_year"

    year = _year_from_value(st.session_state.get(date_key))

    if not st.session_state.get(seed_key):
        st.session_state[number_key] = peek_quote_job_number("Q", year)
        st.session_state[manual_key] = False
        st.session_state[year_key] = year
        st.session_state[seed_key] = True
        return

    if st.session_state.get(manual_key):
        return

    if st.session_state.get(year_key) != year:
        st.session_state[number_key] = peek_quote_job_number("Q", year)
        st.session_state[year_key] = year


def sync_new_job_number(*, date_key: str = "job_new_start") -> None:
    """Allocate or refresh job # from start date unless the user edited it."""
    manual_key = "job_new_num_manual"
    seed_key = "job_new_num_seed"
    number_key = "job_new_num"
    year_key = "job_new_num_year"

    raw_date = st.session_state.get(date_key)
    year = _year_from_value(raw_date if raw_date not in (None, "") else date.today())

    if not st.session_state.get(seed_key):
        st.session_state[number_key] = peek_quote_job_number("J", year)
        st.session_state[manual_key] = False
        st.session_state[year_key] = year
        st.session_state[seed_key] = True
        return

    if st.session_state.get(manual_key):
        return

    if st.session_state.get(year_key) != year:
        st.session_state[number_key] = peek_quote_job_number("J", year)
        st.session_state[year_key] = year


def linked_job_number_preview(quote_number: str) -> str:
    return quote_number_to_job_number(str(quote_number or "").strip())
