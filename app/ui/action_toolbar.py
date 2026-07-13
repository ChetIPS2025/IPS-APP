"""Shared IPS action toolbar for search, filters, and page actions."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from app.components.layout import render_filter_bar
_ActionFn = Callable[[], None]


def render_action_toolbar(
    *,
    search: _ActionFn | None = None,
    filters: _ActionFn | None = None,
    clear_action: _ActionFn | None = None,
    page_size: _ActionFn | None = None,
    primary_action: _ActionFn | None = None,
    secondary_actions: list[_ActionFn] | None = None,
    toolbar_key: str = "ips_action_toolbar",
) -> None:
    """
    Compact toolbar card: search/filters left, actions right.

    Pass widget render callables for each slot to preserve existing keys and logic.
    """
    with st.container(key=toolbar_key):
        st.markdown('<span class="ips-toolbar ips-toolbar-marker" aria-hidden="true"></span>', unsafe_allow_html=True)

        left_slots: list[_ActionFn] = []
        if search:
            left_slots.append(search)
        if filters:
            left_slots.append(filters)
        if clear_action:
            left_slots.append(clear_action)
        if page_size:
            left_slots.append(page_size)

        right_slots: list[_ActionFn] = list(secondary_actions or [])
        if primary_action:
            right_slots.append(primary_action)

        if not left_slots and not right_slots:
            return

        if left_slots and right_slots:
            left_col, right_col = st.columns([2.2, 1], gap="small", vertical_alignment="center")
            with left_col:
                _render_slot_group(left_slots)
            with right_col:
                _render_slot_group(right_slots, align_end=True)
        elif left_slots:
            _render_slot_group(left_slots)
        else:
            _render_slot_group(right_slots, align_end=True)


def render_filter_toolbar(widgets_fn: Callable[[], None]) -> None:
    """Backward-compatible compact filter row (white bordered card)."""
    render_filter_bar(widgets_fn)


def _render_slot_group(slots: list[_ActionFn], *, align_end: bool = False) -> None:
    if not slots:
        return
    if len(slots) == 1:
        slots[0]()
        return
    ratios = [1.0] * len(slots)
    cols = st.columns(ratios, gap="small")
    for col, slot in zip(cols, slots):
        with col:
            slot()


__all__ = ["render_action_toolbar", "render_filter_toolbar"]
