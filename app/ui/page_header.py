"""Shared IPS page header — three-column grid layout."""

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
from app.ui.styles import inject_ips_ui_styles

_ActionFn = Callable[[], None]


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
) -> tuple[date, date] | date:
    if isinstance(value, tuple) and len(value) == 2:
        return (value[0], value[1])
    if isinstance(value, date):
        return value
    return date.today()


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


def _render_date_range(
    *,
    key: str,
    value: tuple[date, date] | date | None,
    on_change: Callable[[tuple[date, date]], None] | None,
) -> None:
    coerced = _coerce_date_range_value(value)
    if isinstance(coerced, tuple):
        label = _format_date_range_label(coerced[0], coerced[1])
    else:
        label = _format_date_range_label(coerced, coerced)
    st.markdown('<span class="ips-ph-date-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
    with st.popover(label, help="Select date range"):
        picked = st.date_input(
            "Date range",
            value=coerced,
            key=key,
            label_visibility="collapsed",
        )
    if on_change and isinstance(picked, tuple) and len(picked) == 2:
        on_change((picked[0], picked[1]))


def _render_refresh(*, key: str) -> None:
    if st.button("↻ Refresh", key=key, use_container_width=True):
        st.rerun()


def _header_auth_context() -> tuple[str, str, str, Callable[[], None]]:
    from app.auth import current_user_display_name, effective_role, sign_out
    from app.navigation import set_nav_slug
    from app.utils.permissions import role_can_access_page
    role = effective_role()
    display = current_user_display_name()
    initials = _initials(display)
    return role, display, initials, sign_out


def _render_bell(*, header_key: str, role: str) -> None:
    from app.navigation import set_nav_slug
    from app.utils.permissions import role_can_access_page
    st.markdown('<span class="ips-ph-util-bell" aria-hidden="true"></span>', unsafe_allow_html=True)
    unread = _unread_notification_count()
    if unread > 0:
        st.markdown(
            f'<span class="ips-ph-badge">{int(unread)}</span>',
            unsafe_allow_html=True,
        )
    if role_can_access_page(role, "company_updates"):
        if st.button(" ", key=f"{header_key}_bell", help="Notifications"):
            set_nav_slug("company_updates")
            st.rerun()
    else:
        st.button(" ", key=f"{header_key}_bell", help="Notifications", disabled=True)


def _render_help() -> None:
    st.markdown('<span class="ips-ph-util-help" aria-hidden="true"></span>', unsafe_allow_html=True)
    with st.popover(" ", help="Help"):
        st.markdown("**Help**")
        st.caption("Use the sidebar to switch modules. Contact your administrator for access changes.")


def _render_settings(*, header_key: str, role: str) -> None:
    from app.navigation import set_nav_slug
    from app.utils.permissions import role_can_access_page
    st.markdown('<span class="ips-ph-util-settings" aria-hidden="true"></span>', unsafe_allow_html=True)
    if role_can_access_page(role, "settings"):
        if st.button(" ", key=f"{header_key}_settings", help="Settings"):
            set_nav_slug("settings")
            st.rerun()
    else:
        st.button(" ", key=f"{header_key}_settings", help="Settings", disabled=True)


def _render_user_menu(*, header_key: str, role: str, display: str, initials: str, sign_out: Callable[[], None]) -> None:
    st.markdown(
        f'<span class="ips-ph-util-user" data-initials="{html.escape(initials)}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.popover(initials, help=display):
        st.markdown(
            f'<span class="ips-ph-avatar-lg">{html.escape(initials)}</span> '
            f"**{html.escape(display)}**",
            unsafe_allow_html=True,
        )
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
) -> None:
    """
    Standard IPS page header.

    Layout: [Back + Logo] | [Icon + Title + Subtitle] | [Actions + Utilities]
    """
    _ = (notification_count, user_initials)

    inject_ips_ui_styles()

    from app.branding import wording_logo_html
    from app.navigation import current_nav_slug
    resolved_subtitle = _resolve_subtitle(title, subtitle)
    resolved_icon = _resolve_icon(icon)
    slug = current_nav_slug()
    header_key = f"ips_hdr_{slug}"
    can_back = show_back and (on_back is not None or _can_navigate_back())

    sub_html = (
        f'<p class="ips-ph-subtitle">{html.escape(resolved_subtitle)}</p>'
        if resolved_subtitle
        else ""
    )
    icon_html = (
        f'<span class="ips-ph-icon-wrap" aria-hidden="true">{resolved_icon}</span>'
        if resolved_icon
        else ""
    )
    title_html = (
        f'<div class="ips-ph-title-block">'
        f"{icon_html}"
        f'<div class="ips-ph-text">'
        f'<h1 class="ips-ph-title">{html.escape(str(title or "").strip())}</h1>'
        f"{sub_html}"
        f"</div></div>"
    )

    right_slots: list[tuple[str, Callable[[], None]]] = []
    if show_date_range:
        right_slots.append(
            (
                "date",
                lambda: _render_date_range(
                    key=date_range_key,
                    value=date_range_value,
                    on_change=on_date_range_change,
                ),
            )
        )
    if show_refresh:
        right_slots.append(
            (
                "refresh",
                lambda rk=refresh_key: _render_refresh(key=rk),
            )
        )
    if secondary_actions:
        for idx, action in enumerate(secondary_actions):
            right_slots.append((f"secondary_{idx}", action))
    if primary_action:
        right_slots.append(("primary", primary_action))
    if actions:
        for idx, action in enumerate(actions):
            right_slots.append((f"action_{idx}", action))

    with st.container(key="ips_app_page_header"):
        st.markdown(
            '<span class="ips-page-shell-marker ips-ph-root ips-page-header" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        left_col, center_col, right_col = st.columns(
            [0.24, 1, 0.42],
            gap="small",
            vertical_alignment="center",
        )

        with left_col:
            st.markdown('<span class="ips-ph-left" aria-hidden="true"></span>', unsafe_allow_html=True)
            back_col, logo_col = st.columns([0.42, 0.58], gap="small", vertical_alignment="center")
            with back_col:
                st.markdown('<span class="ips-ph-back" aria-hidden="true"></span>', unsafe_allow_html=True)
                if can_back:
                    if st.button("← Back", key=f"{header_key}_back", help="Go back"):
                        if on_back is not None:
                            on_back()
                        else:
                            _navigate_back()
                elif show_back:
                    st.markdown('<span class="ips-ph-back-spacer" aria-hidden="true"></span>', unsafe_allow_html=True)
                st.markdown('<span class="ips-ph-menu" aria-hidden="true"></span>', unsafe_allow_html=True)
                if st.button(" ", key=f"{header_key}_menu", help="Open menu"):
                    _request_sidebar_toggle()
            with logo_col:
                if show_logo:
                    st.markdown(
                        wording_logo_html(height=48, css_class="ips-ph-logo"),
                        unsafe_allow_html=True,
                    )
                    st.markdown('<span class="ips-ph-logo-slot" aria-hidden="true"></span>', unsafe_allow_html=True)

        with center_col:
            st.markdown('<span class="ips-ph-center" aria-hidden="true"></span>', unsafe_allow_html=True)
            st.markdown(title_html, unsafe_allow_html=True)

        with right_col:
            st.markdown('<span class="ips-ph-right" aria-hidden="true"></span>', unsafe_allow_html=True)
            role, display, initials, sign_out_fn = _header_auth_context()
            util_count = 4
            slot_count = len(right_slots) + util_count
            ratios = [1.0] * slot_count
            cols = st.columns(ratios, gap="small")
            for idx, (_kind, widget) in enumerate(right_slots):
                with cols[idx]:
                    st.markdown('<span class="ips-ph-action-slot" aria-hidden="true"></span>', unsafe_allow_html=True)
                    widget()
            util_start = len(right_slots)
            with cols[util_start]:
                _render_bell(header_key=header_key, role=role)
            with cols[util_start + 1]:
                _render_help()
            with cols[util_start + 2]:
                _render_settings(header_key=header_key, role=role)
            with cols[util_start + 3]:
                _render_user_menu(
                    header_key=header_key,
                    role=role,
                    display=display,
                    initials=initials,
                    sign_out=sign_out_fn,
                )


def render_page_brand_header(
    title: str,
    subtitle: str | None = None,
    **kwargs: Any,
) -> None:
    """Backward-compatible alias."""
    render_page_header(title, subtitle, **kwargs)


__all__ = ["render_page_header", "render_page_brand_header"]
