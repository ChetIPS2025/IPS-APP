"""Scheduling week navigation and view mode tabs."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable

import streamlit as st

from app.components.tabs import render_tabs
from app.perf_debug import perf_span
from app.services.scheduling_service import week_range
from app.ui.streamlit_perf import fragment_rerun

_VIEW_MODES = ("Week", "Day", "Crew", "Jobs", "Equipment")


def scheduling_view_modes() -> tuple[str, ...]:
    return _VIEW_MODES


def week_anchor(session_key: str) -> date:
    from app.services.scheduling_service import monday_of

    raw = st.session_state.get(session_key)
    if isinstance(raw, date):
        return raw
    return monday_of(date.today())


def set_week_anchor(session_key: str, d: date) -> None:
    from app.services.scheduling_service import monday_of

    st.session_state[session_key] = monday_of(d)


def clamp_day_to_week(*, week_key: str, day_key: str) -> None:
    week_start, week_end = week_range(week_anchor(week_key))
    raw = st.session_state.get(day_key)
    if not isinstance(raw, date) or not (week_start <= raw < week_end):
        st.session_state[day_key] = week_start


def render_week_navigation(
    *,
    week_key: str,
    day_key: str,
    on_week_change: Callable[[], None] | None = None,
) -> tuple[date, date, date]:
    with perf_span("scheduling.context"):
        anchor = week_anchor(week_key)
        week_start, week_end = week_range(anchor)

    nav1, nav2, nav3, nav4 = st.columns(4)

    def _today() -> None:
        set_week_anchor(week_key, date.today())
        st.session_state[day_key] = date.today()
        if on_week_change:
            on_week_change()
        fragment_rerun()

    def _prev_week() -> None:
        set_week_anchor(week_key, anchor - timedelta(days=7))
        clamp_day_to_week(week_key=week_key, day_key=day_key)
        if on_week_change:
            on_week_change()
        fragment_rerun()

    def _next_week() -> None:
        set_week_anchor(week_key, anchor + timedelta(days=7))
        clamp_day_to_week(week_key=week_key, day_key=day_key)
        if on_week_change:
            on_week_change()
        fragment_rerun()

    with nav1:
        st.button("Today", key="sched_hdr_today", on_click=_today, use_container_width=True)
    with nav2:
        st.button("Previous Week", key="sched_hdr_prev", on_click=_prev_week, use_container_width=True)
    with nav3:
        st.button("Next Week", key="sched_hdr_next", on_click=_next_week, use_container_width=True)
    with nav4:
        st.caption(
            f"Week: {week_start.strftime('%b %d')} – {(week_end - timedelta(days=1)).strftime('%b %d, %Y')}"
        )
    clamp_day_to_week(week_key=week_key, day_key=day_key)
    selected_day = st.session_state.get(day_key)
    if not isinstance(selected_day, date):
        selected_day = week_start
    return week_start, week_end, selected_day


def render_view_tabs(*, session_key: str, default: str = "Week") -> str:
    return render_tabs(list(_VIEW_MODES), session_key=session_key, default=default)
