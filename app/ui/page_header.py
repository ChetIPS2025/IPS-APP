"""Shared IPS page header — four-column layout with nested action row."""

from __future__ import annotations

import html
from collections.abc import Callable
from datetime import date
from typing import Any

import streamlit as st

from app.components.headers import (
    DEFAULT_PAGE_SUBTITLES,
    _DEFAULT_PAGE_ICON_SVG,
    _PAGE_HEADER_ICON_SVGS,
    _initials,
)
from app.ui.page_header_styles import inject_page_header_styles

_ActionFn = Callable[[], None]

_MAIN_COLS = [0.35, 3.2, 3.5, 7.5]
_ACTION_COLS = [2.05, 0.5, 1.55, 0.55, 0.55, 0.55, 0.75]


def _resolve_icon(icon: str | None) -> str:
    if icon and str(icon).strip().startswith("<svg"):
        return str(icon).strip()
    from app.navigation import current_nav_slug

    slug = current_nav_slug()
    if icon:
        return str(icon).strip()
    return _PAGE_HEADER_ICON_SVGS.get(slug, _DEFAULT_PAGE_ICON_SVG)


def _resolve_subtitle(title: str, subtitle: str | None) -> str | None:
    if subtitle:
        return str(subtitle).strip() or None
    from app.navigation import current_nav_slug

    return DEFAULT_PAGE_SUBTITLES.get(current_nav_slug())


def _can_navigate_back() -> bool:
    from app.navigation import IPS_NAV_HISTORY_KEY

    history = st.session_state.get(IPS_NAV_HISTORY_KEY) or []
    return bool(history)


def _navigate_back() -> None:
    from app.navigation import navigate_back

    navigate_back()


def _request_sidebar_toggle() -> None:
    from app.components.sidebar_shell import IPS_SIDEBAR_TOGGLE_REQUEST_KEY

    st.session_state[IPS_SIDEBAR_TOGGLE_REQUEST_KEY] = True
    st.rerun()


def _unread_notification_count() -> int:
    from app.services.field_dashboard import load_field_dashboard_snapshot

    try:
        snap = load_field_dashboard_snapshot()
        return int(snap.get("unread_notifications", 0) or 0)
    except Exception:
        return 0


def _coerce_date_range_value(
    value: tuple[date, date] | date | None,
) -> tuple[date, date]:
    if isinstance(value, tuple) and len(value) == 2:
        return (value[0], value[1])
    if isinstance(value, date):
        return (value, value)
    today = date.today()
    return (today, today)


def _format_date_range_label(start: date, end: date) -> str:
    def _part(d: date, *, include_year: bool) -> str:
        text = f"{d.strftime('%b')} {d.day}"
        if include_year:
            text += f", {d.year}"
        return text

    if start == end:
        return _part(start, include_year=True)
    if start.year == end.year:
        return f"{_part(start, include_year=False)} – {_part(end, include_year=True)}"
    return f"{_part(start, include_year=True)} – {_part(end, include_year=True)}"


def _header_auth_context() -> tuple[str, str, str, Callable[[], None]]:
    from app.auth import current_user_display_name, effective_role, sign_out

    role = effective_role()
    display = current_user_display_name()
    initials = _initials(display)
    return role, display, initials, sign_out


def _render_date_range(
    *,
    key: str,
    value: tuple[date, date] | date | None,
    on_change: Callable[[tuple[date, date]], None] | None,
) -> None:
    coerced = _coerce_date_range_value(value)
    with st.container(key="header_date_range"):
        picked = st.date_input(
            "Date range",
            value=coerced,
            format="MM/DD/YYYY",
            key=key,
            label_visibility="collapsed",
        )
    if on_change and isinstance(picked, tuple) and len(picked) == 2:
        state_key = f"{key}__applied"
        current = (picked[0], picked[1])
        if st.session_state.get(state_key) != current:
            st.session_state[state_key] = current
            on_change(current)


def _render_back(*, header_key: str, can_back: bool, on_back: Callable[[], None] | None) -> None:
    with st.container(key="header_back"):
        if can_back:
            if st.button(
                "←",
                key=f"{header_key}_back",
                help="Return to previous page",
                use_container_width=True,
            ):
                if on_back is not None:
                    on_back()
                else:
                    _navigate_back()


def _render_menu(*, header_key: str) -> None:
    with st.container(key="header_menu"):
        if st.button("☰", key=f"{header_key}_menu", help="Open menu", use_container_width=True):
            _request_sidebar_toggle()


def _render_refresh(*, key: str) -> None:
    with st.container(key="header_refresh"):
        if st.button("↻", key=key, help="Refresh", use_container_width=True):
            st.rerun()


def _render_bell(*, header_key: str, role: str) -> None:
    from app.navigation import set_nav_slug
    from app.utils.permissions import role_can_access_page

    unread = _unread_notification_count()
    label = "🔔"
    if unread > 0:
        label = f"🔔 {int(unread)}"
    with st.container(key="header_notifications"):
        if role_can_access_page(role, "company_updates"):
            if st.button(label, key=f"{header_key}_bell", help="Notifications", use_container_width=True):
                set_nav_slug("company_updates")
                st.rerun()
        else:
            st.button(label, key=f"{header_key}_bell", help="Notifications", disabled=True, use_container_width=True)


def _render_help(*, header_key: str) -> None:
    with st.container(key="header_help"):
        with st.popover("?", help="Help"):
            st.markdown("**Help**")
            st.caption("Use the sidebar to switch modules. Contact your administrator for access changes.")


def _render_settings(*, header_key: str, role: str) -> None:
    from app.navigation import set_nav_slug
    from app.utils.permissions import role_can_access_page

    with st.container(key="header_settings"):
        if role_can_access_page(role, "settings"):
            if st.button("⚙", key=f"{header_key}_settings", help="Settings", use_container_width=True):
                set_nav_slug("settings")
                st.rerun()
        else:
            st.button("⚙", key=f"{header_key}_settings", help="Settings", disabled=True, use_container_width=True)


def _render_user_menu(
    *,
    header_key: str,
    role: str,
    display: str,
    initials: str,
    sign_out: Callable[[], None],
) -> None:
    with st.container(key="header_avatar"):
        with st.popover(initials, help=display):
            st.markdown(f"**{html.escape(display)}**")
            st.caption(role.replace("_", " ").title())
            if st.button("Log out", key=f"{header_key}_logout", use_container_width=True):
                sign_out()


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
    show_logo: bool = True,
    layout_marker: str | None = None,
) -> None:
    """
    Standard IPS page header.

    Layout: [Back] [Logo] | [Icon + Title + Subtitle] | [Date] [Refresh] [Primary] [Bell] [Help] [Settings] [Avatar]
    """
    _ = (notification_count, user_initials, _format_date_range_label)

    inject_page_header_styles()

    from app.branding import wording_logo_html
    from app.navigation import current_nav_slug

    resolved_subtitle = _resolve_subtitle(title, subtitle)
    resolved_icon = _resolve_icon(icon)
    slug = current_nav_slug()
    header_key = f"ips_hdr_{slug}"
    can_back = show_back and (on_back is not None or _can_navigate_back())

    sub_html = (
        f'<p class="ips-header-subtitle">{html.escape(resolved_subtitle)}</p>'
        if resolved_subtitle
        else ""
    )
    icon_html = (
        f'<span class="ips-header-icon-wrap" aria-hidden="true">{resolved_icon}</span>'
        if resolved_icon
        else ""
    )
    title_html = (
        f'<div class="ips-header-title-block">'
        f"{icon_html}"
        f'<div class="ips-header-text">'
        f'<h1 class="ips-header-title">{html.escape(str(title or "").strip())}</h1>'
        f"{sub_html}"
        f"</div></div>"
    )

    extra_actions: list[_ActionFn] = []
    if secondary_actions:
        extra_actions.extend(secondary_actions)
    if actions:
        extra_actions.extend(actions)

    with st.container(key=f"ips_page_header_{slug}"):
        marker_classes = "ips-page-shell-marker ips-header-root ips-page-header ips-app-page-header-marker"
        if str(layout_marker or "").strip():
            marker_classes += f" {html.escape(str(layout_marker).strip())}"
        st.markdown(
            f'<span class="{marker_classes}" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        back_col, logo_col, title_col, actions_col = st.columns(
            _MAIN_COLS,
            gap="small",
            vertical_alignment="center",
        )

        with back_col:
            if can_back:
                _render_back(header_key=header_key, can_back=True, on_back=on_back)
            else:
                _render_menu(header_key=header_key)

        with logo_col:
            if show_logo:
                st.markdown(
                    wording_logo_html(height=56, css_class="ips-header-logo"),
                    unsafe_allow_html=True,
                )

        with title_col:
            st.markdown(title_html, unsafe_allow_html=True)

        with actions_col:
            (
                date_col,
                refresh_col,
                primary_col,
                notification_col,
                help_col,
                settings_col,
                avatar_col,
            ) = st.columns(
                _ACTION_COLS,
                gap="small",
                vertical_alignment="center",
            )

            with date_col:
                if show_date_range:
                    _render_date_range(
                        key=date_range_key,
                        value=date_range_value,
                        on_change=on_date_range_change,
                    )

            with refresh_col:
                if show_refresh:
                    _render_refresh(key=refresh_key)

            with primary_col:
                if extra_actions:
                    extra_cols = st.columns([1.0] * len(extra_actions), gap="small")
                    for col, action in zip(extra_cols, extra_actions):
                        with col:
                            action()
                if primary_action:
                    with st.container(key="header_primary_action"):
                        primary_action()

            role, display, initials, sign_out_fn = _header_auth_context()

            with notification_col:
                _render_bell(header_key=header_key, role=role)

            with help_col:
                _render_help(header_key=header_key)

            with settings_col:
                _render_settings(header_key=header_key, role=role)

            with avatar_col:
                _render_user_menu(
                    header_key=header_key,
                    role=role,
                    display=display,
                    initials=initials,
                    sign_out=sign_out_fn,
                )

    from app.ui.app_shell_styles import (
        _app_shell_pre_header_cleanup_script,
        inject_app_shell_script,
    )

    with st.sidebar:
        inject_app_shell_script(_app_shell_pre_header_cleanup_script())


def render_page_brand_header(
    title: str,
    subtitle: str | None = None,
    **kwargs: Any,
) -> None:
    """Backward-compatible alias."""
    render_page_header(title, subtitle, **kwargs)


__all__ = ["render_page_header", "render_page_brand_header", "_format_date_range_label"]
