"""Shared IPS page header component."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import streamlit as st

_ActionFn = Callable[[], None]

try:
    from app.components.headers import render_page_header as _render_core_header
except ImportError:
    from components.headers import render_page_header as _render_core_header  # type: ignore


def _date_range_action(
    *,
    key: str,
    value: tuple[date, date] | date | None,
    on_change: Callable[[tuple[date, date]], None] | None = None,
) -> _ActionFn:
    def _widget() -> None:
        picked = st.date_input(
            "Date range",
            value=value if value is not None else date.today(),
            key=key,
            label_visibility="collapsed",
            format="MMM D, YYYY",
        )
        if on_change and isinstance(picked, tuple) and len(picked) == 2:
            on_change((picked[0], picked[1]))

    return _widget


def _refresh_action(*, key: str) -> _ActionFn:
    def _widget() -> None:
        if st.button("↻ Refresh", key=key, use_container_width=True):
            st.rerun()

    return _widget


def render_page_header(
    title: str,
    subtitle: str | None = None,
    *,
    icon: str | None = None,
    primary_action: _ActionFn | None = None,
    secondary_actions: list[_ActionFn] | None = None,
    actions: list[_ActionFn] | None = None,
    show_back: bool = True,
    show_date_range: bool = False,
    date_range_value: tuple[date, date] | date | None = None,
    date_range_key: str = "ips_hdr_date_range",
    on_date_range_change: Callable[[tuple[date, date]], None] | None = None,
    show_refresh: bool = False,
    refresh_key: str = "ips_hdr_refresh",
    notification_count: int | None = None,
    user_initials: str | None = None,
    on_back: Callable[[], None] | None = None,
) -> None:
    """
    Standard IPS page header.

    Layout: Back | Logo | Divider | Title | Actions | Notification | Help | Settings | Avatar
    """
    _ = (notification_count, user_initials)

    merged_actions: list[_ActionFn] = []
    if actions:
        merged_actions.extend(actions)
    if show_date_range:
        merged_actions.append(
            _date_range_action(
                key=date_range_key,
                value=date_range_value,
                on_change=on_date_range_change,
            )
        )
    if show_refresh:
        merged_actions.append(_refresh_action(key=refresh_key))
    if secondary_actions:
        merged_actions.extend(secondary_actions)
    if primary_action:
        merged_actions.append(primary_action)

    try:
        from app.ui.styles import inject_ips_ui_styles
    except ImportError:
        from ui.styles import inject_ips_ui_styles  # type: ignore
    inject_ips_ui_styles()

    _render_core_header(
        title,
        subtitle,
        icon=icon,
        actions=merged_actions or None,
        show_back=show_back,
        on_back=on_back,
    )


def render_page_brand_header(
    title: str,
    subtitle: str | None = None,
    **kwargs: Any,
) -> None:
    """Backward-compatible alias."""
    render_page_header(title, subtitle, **kwargs)


__all__ = ["render_page_header", "render_page_brand_header"]
