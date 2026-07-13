"""Shared IPS application page header."""

from __future__ import annotations

import html
from collections.abc import Callable

import streamlit as st

_ActionFn = Callable[[], None]

_ICON_SVG_ATTRS = (
    'class="ips-app-header-icon-svg" xmlns="http://www.w3.org/2000/svg" '
    'width="22" height="22" viewBox="0 0 24 24" fill="none" '
    'stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
)

_PAGE_HEADER_ICON_SVGS: dict[str, str] = {
    "dashboard": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<rect x="3" y="3" width="7" height="7" rx="1"/>'
        '<rect x="14" y="3" width="7" height="7" rx="1"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1"/>'
        '<rect x="14" y="14" width="7" height="7" rx="1"/>'
        "</svg>"
    ),
    "jobs": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>'
        '<rect x="4" y="6" width="16" height="14" rx="2"/>'
        "</svg>"
    ),
    "pipeline": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M4 6h16"/><path d="M4 12h10"/><path d="M4 18h14"/>'
        "</svg>"
    ),
    "customers": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M3 21h18"/><path d="M5 21V7l7-4 7 4v14"/>'
        '<path d="M9 21v-6h6v6"/>'
        "</svg>"
    ),
    "estimates": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
        '<path d="M14 2v6h6"/><path d="M8 13h8"/><path d="M8 17h8"/>'
        "</svg>"
    ),
    "inventory": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>'
        "</svg>"
    ),
    "assets": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<rect x="2" y="7" width="20" height="14" rx="2"/>'
        '<path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/>'
        "</svg>"
    ),
    "timekeeping": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="M12 6v6l4 2"/>'
        "</svg>"
    ),
    "employees": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
        "</svg>"
    ),
    "users": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/>'
        '<circle cx="9" cy="7" r="4"/>'
        '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'
        "</svg>"
    ),
    "reports": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M3 3v18h18"/><path d="M7 16l4-5 4 3 5-7"/>'
        "</svg>"
    ),
    "tasks": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>'
        "</svg>"
    ),
    "documents": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>'
        '<path d="M13 2v7h7"/>'
        "</svg>"
    ),
    "settings": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>'
        "</svg>"
    ),
    "admin": (
        f"<svg {_ICON_SVG_ATTRS}>"
        '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
        "</svg>"
    ),
}

_DEFAULT_PAGE_ICON_SVG = (
    f"<svg {_ICON_SVG_ATTRS}>"
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    '<path d="M14 2v6h6"/>'
    "</svg>"
)

DEFAULT_PAGE_SUBTITLES: dict[str, str] = {
    "dashboard": "Overview of key operational metrics and performance.",
    "jobs": "Manage and track all company jobs.",
    "pipeline": "Quotes and jobs in one operational pipeline.",
    "customers": "Customer companies and contacts.",
    "estimates": "Manage and track all company estimates.",
    "pricing_guide": "Master estimating catalog and default rates.",
    "inventory": "Inventory management and stock levels.",
    "assets": "Track and manage all company assets and equipment.",
    "timekeeping": "Weekly employee timecards.",
    "weekly_timesheets": "Weekly job timesheets and crew hours.",
    "employees": "Employee management.",
    "users": "Employee management.",
    "employee_certifications": "Track credentials, expirations, and compliance.",
    "employee_documents": "Store licenses, training records, and HR files.",
    "company_updates": "Share announcements, safety alerts, events, and company news.",
    "documents": "Central document hub for jobs, assets, and employees.",
    "tasks": "Office and management to-dos.",
    "reports": "Analytics and reporting.",
    "admin": "System administration and lookups.",
    "settings": "Application settings and preferences.",
    "field_dashboard": "Today's jobs, reports, crew time, and quick field actions.",
    "field_day": "Pick a job once, then move through report, crew time, hours, and tasks.",
    "field_daily_reports": "Field daily reports with crew, photos, and safety.",
    "field_crew_time": "Supervisors enter crew hours in Timekeeping.",
    "coupling_inspection": "Coupling inspection forms and records.",
}


def render_main_brand_bar(*, brand_actions: list[_ActionFn] | None = None, show_menu: bool = True) -> None:
    """Deprecated: replaced by :func:`render_page_header`."""
    _ = (brand_actions, show_menu)


def _initials(name: str) -> str:
    parts = [p for p in str(name or "").strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _resolve_icon(icon: str | None) -> str:
    if icon and str(icon).strip().startswith("<svg"):
        return str(icon).strip()
    try:
        from app.navigation import current_nav_slug
    except ImportError:
        from navigation import current_nav_slug  # type: ignore
    slug = current_nav_slug()
    if icon:
        return str(icon).strip()
    return _PAGE_HEADER_ICON_SVGS.get(slug, _DEFAULT_PAGE_ICON_SVG)


def _resolve_subtitle(title: str, subtitle: str | None) -> str | None:
    if subtitle:
        return str(subtitle).strip() or None
    try:
        from app.navigation import current_nav_slug
    except ImportError:
        from navigation import current_nav_slug  # type: ignore
    return DEFAULT_PAGE_SUBTITLES.get(current_nav_slug())


def _can_navigate_back() -> bool:
    try:
        from app.navigation import IPS_NAV_HISTORY_KEY
    except ImportError:
        from navigation import IPS_NAV_HISTORY_KEY  # type: ignore
    history = st.session_state.get(IPS_NAV_HISTORY_KEY) or []
    return bool(history)


def _request_sidebar_toggle() -> None:
    try:
        from app.components.sidebar_shell import IPS_SIDEBAR_TOGGLE_REQUEST_KEY
    except ImportError:
        from components.sidebar_shell import IPS_SIDEBAR_TOGGLE_REQUEST_KEY  # type: ignore
    st.session_state[IPS_SIDEBAR_TOGGLE_REQUEST_KEY] = True
    st.rerun()


def _navigate_back() -> None:
    try:
        from app.navigation import navigate_back
    except ImportError:
        from navigation import navigate_back  # type: ignore
    navigate_back()


def _unread_notification_count() -> int:
    try:
        from app.services.field_dashboard import load_field_dashboard_snapshot
    except ImportError:
        try:
            from services.field_dashboard import load_field_dashboard_snapshot  # type: ignore
        except Exception:
            return 0
    try:
        snap = load_field_dashboard_snapshot()
        return int(snap.get("unread_notifications", 0) or 0)
    except Exception:
        return 0


def _render_page_actions(actions: list[_ActionFn]) -> None:
    n = len(actions)
    if n == 1:
        actions[0]()
    elif n == 2:
        bc1, bc2 = st.columns([1.72, 0.88], gap="small")
        with bc1:
            actions[0]()
        with bc2:
            actions[1]()
    elif n == 3:
        bc1, bc2, bc3 = st.columns([1.05, 1.45, 0.95], gap="small")
        with bc1:
            actions[0]()
        with bc2:
            actions[1]()
        with bc3:
            actions[2]()
    else:
        cols = st.columns(min(n, 4), gap="small")
        for i, widget in enumerate(actions):
            with cols[i % len(cols)]:
                widget()


def _render_header_utilities(*, header_key: str) -> None:
    try:
        from app.auth import current_user_display_name, effective_role, sign_out
        from app.navigation import set_nav_slug
        from app.utils.permissions import role_can_access_page
    except ImportError:
        from auth import current_user_display_name, effective_role, sign_out  # type: ignore
        from navigation import set_nav_slug  # type: ignore
        from utils.permissions import role_can_access_page  # type: ignore

    role = effective_role()
    unread = _unread_notification_count()
    display = current_user_display_name()
    initials = _initials(display)

    u1, u2, u3, u4 = st.columns([1, 1, 1, 1.2], gap="small")
    with u1:
        st.markdown('<span class="ips-app-header-util-bell-slot" aria-hidden="true"></span>', unsafe_allow_html=True)
        badge_html = (
            f'<span class="ips-app-header-badge">{int(unread)}</span>'
            if unread > 0
            else ""
        )
        if badge_html:
            st.markdown(badge_html, unsafe_allow_html=True)
        if role_can_access_page(role, "company_updates"):
            if st.button(" ", key=f"{header_key}_bell", help="Notifications"):
                set_nav_slug("company_updates")
                st.rerun()
        else:
            st.button(" ", key=f"{header_key}_bell", help="Notifications", disabled=True)
    with u2:
        st.markdown('<span class="ips-app-header-util-help-slot" aria-hidden="true"></span>', unsafe_allow_html=True)
        with st.popover(" ", help="Help"):
            st.markdown("**Help**")
            st.caption("Use the sidebar to switch modules. Contact your administrator for access changes.")
    with u3:
        st.markdown('<span class="ips-app-header-util-settings-slot" aria-hidden="true"></span>', unsafe_allow_html=True)
        if role_can_access_page(role, "settings"):
            if st.button(" ", key=f"{header_key}_settings", help="Settings"):
                set_nav_slug("settings")
                st.rerun()
        else:
            st.button(" ", key=f"{header_key}_settings", help="Settings", disabled=True)
    with u4:
        st.markdown(
            f'<span class="ips-app-header-util-user-slot" data-initials="{html.escape(initials)}" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        with st.popover(initials, help=display):
            st.markdown(
                f'<span class="ips-app-header-avatar-lg">{html.escape(initials)}</span> '
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
    actions: list[_ActionFn] | None = None,
    show_back: bool = True,
    on_back: Callable[[], None] | None = None,
    actions_column_ratio: tuple[float, float] | None = None,
    actions_cols: list[_ActionFn] | None = None,
    brand_actions: list[_ActionFn] | None = None,
    include_brand_bar: bool = False,
    show_logo: bool = True,
) -> None:
    """
    Standard IPS page header — back, logo, title, actions, and utility icons.

    Every module page should call this once at the top of ``render()``.
    """
    _ = (actions_column_ratio, brand_actions, include_brand_bar, show_logo, actions_cols)
    merged_actions = actions or actions_cols or brand_actions
    resolved_subtitle = _resolve_subtitle(title, subtitle)
    resolved_icon = _resolve_icon(icon)

    try:
        from app.branding import wording_logo_html
        from app.navigation import current_nav_slug
    except ImportError:
        from branding import wording_logo_html  # type: ignore
        from navigation import current_nav_slug  # type: ignore

    slug = current_nav_slug()
    header_key = f"ips_hdr_{slug}"
    shell_marker = '<span class="ips-page-shell-marker" aria-hidden="true"></span>'
    header_marker = '<span class="ips-app-page-header-marker" aria-hidden="true"></span>'
    can_back = show_back and (on_back is not None or _can_navigate_back())

    sub_html = (
        f'<p class="ips-app-header-subtitle">{html.escape(resolved_subtitle)}</p>'
        if resolved_subtitle
        else ""
    )
    icon_html = (
        f'<span class="ips-app-header-icon-svg-wrap" aria-hidden="true">{resolved_icon}</span>'
        if resolved_icon
        else ""
    )
    title_html = (
        f'<div class="ips-app-header-page-info">'
        f'<span class="ips-app-header-divider" aria-hidden="true"></span>'
        f'<div class="ips-app-header-title-block">'
        f"{icon_html}"
        f'<div class="ips-app-header-text">'
        f'<h1 class="ips-app-header-title">{html.escape(str(title or "").strip())}</h1>'
        f"{sub_html}"
        f"</div></div></div>"
    )

    st.markdown(f"{shell_marker}{header_marker}", unsafe_allow_html=True)

    with st.container(key="ips_app_page_header"):
        st.markdown('<span class="ips-page-header ips-page-header-shell" aria-hidden="true"></span>', unsafe_allow_html=True)
        if merged_actions:
            left_col, actions_col, util_col = st.columns(
                [3.35, 1.55, 0.82],
                gap="small",
                vertical_alignment="center",
            )
        else:
            left_col, util_col = st.columns(
                [4.35, 0.82],
                gap="small",
                vertical_alignment="center",
            )
            actions_col = None

        with left_col:
            st.markdown('<span class="ips-header-left-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
            back_col, logo_col, title_col = st.columns(
                [0.48, 0.72, 2.55],
                gap="small",
                vertical_alignment="center",
            )
            with back_col:
                st.markdown('<span class="ips-app-header-back-slot" aria-hidden="true"></span>', unsafe_allow_html=True)
                if can_back:
                    st.markdown('<span class="ips-app-header-back-active" aria-hidden="true"></span>', unsafe_allow_html=True)
                    if st.button("← Back", key=f"{header_key}_back", help="Go back"):
                        if on_back is not None:
                            on_back()
                        else:
                            _navigate_back()
                else:
                    st.markdown(
                        '<span class="ips-app-header-back-spacer" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                st.markdown('<span class="ips-app-header-menu-slot" aria-hidden="true"></span>', unsafe_allow_html=True)
                if st.button(" ", key=f"{header_key}_menu", help="Open menu"):
                    _request_sidebar_toggle()
            with logo_col:
                st.markdown(
                    wording_logo_html(height=46, css_class="ips-app-header-logo ips-header-logo"),
                    unsafe_allow_html=True,
                )
            with title_col:
                st.markdown(title_html, unsafe_allow_html=True)

        if merged_actions and actions_col is not None:
            with actions_col:
                st.markdown(
                    '<span class="ips-page-actions-marker ips-app-header-actions-marker ips-header-actions-marker" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                _render_page_actions(merged_actions)

        with util_col:
            st.markdown(
                '<span class="ips-app-header-utils-marker ips-header-utils-marker" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            _render_header_utilities(header_key=header_key)


def render_page_brand_header(
    title: str,
    subtitle: str | None = None,
    *,
    actions: list[_ActionFn] | None = None,
    actions_column_ratio: tuple[float, float] | None = None,
    brand_actions: list[_ActionFn] | None = None,
    include_brand_bar: bool = False,
    icon: str | None = None,
    show_back: bool = True,
    on_back: Callable[[], None] | None = None,
) -> None:
    """Backward-compatible alias for :func:`render_page_header`."""
    render_page_header(
        title,
        subtitle,
        icon=icon,
        actions=actions,
        show_back=show_back,
        on_back=on_back,
        actions_column_ratio=actions_column_ratio,
        brand_actions=brand_actions,
        include_brand_bar=include_brand_bar,
    )


def render_users_page_header(
    title: str,
    subtitle: str | None = None,
    *,
    actions: list[_ActionFn] | None = None,
) -> None:
    """Deprecated — use :func:`render_page_header`."""
    render_page_header(title, subtitle, icon="👥", actions=actions)


def render_person_profile_header(
    name: str,
    *,
    role: str = "",
    department: str = "",
    status: str = "Active",
    email: str = "",
    phone: str = "",
    last_login: str = "",
    status_html: str = "",
) -> None:
    """Profile summary row matching Coastal/IPS Users detail header."""
    ot, ct = "d" + "iv", "/" + "d" + "iv"
    pill = status_html or ""
    if not pill and status:
        try:
            from app.components.status import status_pill_html
        except ImportError:
            from components.status import status_pill_html  # type: ignore
        pill = status_pill_html(status)
    sub_parts = [html.escape(x) for x in (role, department) if str(x or "").strip()]
    sub = " · ".join(sub_parts)
    contact_lines = []
    if email:
        contact_lines.append(html.escape(email))
    if phone:
        contact_lines.append(html.escape(phone))
    if last_login:
        contact_lines.append(f"Last login: {html.escape(last_login)}")
    contact = "<br>".join(contact_lines)
    st.markdown(
        f"""
<{ot} class="ips-profile-header">
  <{ot} class="ips-profile-avatar">{html.escape(_initials(name))}</{ct}>
  <{ot} class="ips-profile-main">
    <p class="ips-profile-name">{html.escape(name)} {pill}</p>
    <p class="ips-profile-sub">{sub}</p>
    <{ot} class="ips-profile-contact">{contact}</{ct}>
  </{ct}>
</{ct}>
""",
        unsafe_allow_html=True,
    )


def _navigate_ops_quick_action(slug: str) -> None:
    """Navigate from operations dashboard quick actions."""
    picked = str(slug or "").strip()
    if not picked:
        return
    try:
        from app.auth import effective_role
        from app.navigation import normalize_nav_slug, set_nav_slug
        from app.utils.permissions import role_can_access_page
    except ImportError:
        from auth import effective_role  # type: ignore
        from navigation import normalize_nav_slug, set_nav_slug  # type: ignore
        from utils.permissions import role_can_access_page  # type: ignore

    if picked == "job_costing":
        if not role_can_access_page(effective_role(), "jobs"):
            st.warning("You do not have access to that page.")
            return
        try:
            from app.navigation import open_jobs_job_costing
        except ImportError:
            from navigation import open_jobs_job_costing  # type: ignore
        open_jobs_job_costing()
        st.rerun()
        return

    target = normalize_nav_slug(picked)
    if not role_can_access_page(effective_role(), target):
        st.warning("You do not have access to that page.")
        return
    set_nav_slug(target)
    st.rerun()


def render_ops_quick_action_tiles(
    actions: list[tuple[str, str, str]],
    *,
    key_prefix: str = "ips_ops_qa",
    title: str = "Quick Actions",
) -> None:
    """Compact Quick Actions toolbar for the operations dashboard."""
    with st.container(key="dashboard_ops_quick_actions"):
        st.markdown(
            f'<p class="ips-ops-quick-toolbar-title quick-actions-title">'
            f'{html.escape(title.upper())}</p>',
            unsafe_allow_html=True,
        )
        cols = st.columns(len(actions), gap="small")
        for idx, col in enumerate(cols):
            icon, label, slug = actions[idx]
            with col:
                if st.button(
                    f"{icon} {label}",
                    key=f"{key_prefix}_{idx}",
                    use_container_width=True,
                ):
                    _navigate_ops_quick_action(slug)


def render_dashboard_quick_actions(
    actions: list[tuple[str, str, str]],
    *,
    key_prefix: str = "ips_dash_qa",
    title: str = "Quick Actions",
) -> None:
    """
    Compact dashboard quick-action card with a 4-column button grid.

    Each item: (icon, label, nav_slug_or_empty).
    """
    with st.container(key="dashboard_quick_actions"):
        st.markdown(
            f'<div class="ips-quick-actions-header">'
            f'<p class="ips-quick-actions-title">{html.escape(title)}</p>'
            f"</div>",
            unsafe_allow_html=True,
        )
        row_size = 4
        for row_start in range(0, len(actions), row_size):
            cols = st.columns(row_size, gap="small")
            for j, col in enumerate(cols):
                idx = row_start + j
                if idx >= len(actions):
                    break
                icon, label, slug = actions[idx]
                with col:
                    if st.button(
                        f"{icon}\n{label}",
                        key=f"{key_prefix}_{idx}",
                        use_container_width=True,
                    ):
                        if slug:
                            _navigate_ops_quick_action(slug)
