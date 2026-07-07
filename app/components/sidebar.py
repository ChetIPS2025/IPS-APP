"""Fixed left sidebar navigation (slug-based)."""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

try:
    from app.auth import current_profile, current_role, sign_out
    from app.components.sidebar_nav_icons import nav_icon_for_slug
    from app.components.sidebar_shell import (
        apply_pending_sidebar_collapse,
        is_sidebar_collapsed,
        request_sidebar_collapse_after_nav,
        request_sidebar_toggle,
        set_sidebar_collapsed,
        store_sidebar_nav_fallback,
    )
    from app.config import APP_VERSION, ROOT_DIR
    from app.navigation import set_nav_slug
    from app.utils.constants import EMPLOYEE_NAV_PAGES, FIELD_NAV_PAGES, NAV_PAGES
    from app.utils.permissions import (
        filter_employee_nav_for_role,
        filter_field_nav_for_role,
        filter_nav_for_role,
        normalize_role,
        role_can_access_page,
    )
except ImportError:
    from auth import current_profile, current_role, sign_out  # type: ignore
    from components.sidebar_nav_icons import nav_icon_for_slug  # type: ignore
    from components.sidebar_shell import (  # type: ignore
        apply_pending_sidebar_collapse,
        is_sidebar_collapsed,
        request_sidebar_collapse_after_nav,
        request_sidebar_toggle,
        set_sidebar_collapsed,
        store_sidebar_nav_fallback,
    )
    from config import APP_VERSION, ROOT_DIR  # type: ignore
    from navigation import set_nav_slug  # type: ignore
    from utils.constants import EMPLOYEE_NAV_PAGES, FIELD_NAV_PAGES, NAV_PAGES  # type: ignore
    from utils.permissions import (  # type: ignore
        filter_employee_nav_for_role,
        filter_field_nav_for_role,
        filter_nav_for_role,
        normalize_role,
        role_can_access_page,
    )

_OT, _CT = "d" + "iv", "/" + "d" + "iv"


def _logo_path(*, compact: bool = False) -> Path | None:
    names = (
        ("IPS Icon.png", "ips_logo_round.png", "ips_logo_header.png", "company_logo.png")
        if compact
        else ("ips_logo_header.png", "IPS Icon.png", "company_logo.png", "ips_logo_round.png")
    )
    for name in names:
        p = ROOT_DIR / "assets" / name
        if p.is_file():
            return p
    return None


def _nav_button_label(slug: str, label: str, *, collapsed: bool) -> str:
    icon = nav_icon_for_slug(slug)
    if collapsed:
        return icon
    return f"{icon}\u2002{label}"


def _section_for_slug(slug: str, sections: list[tuple[frozenset[str], str]]) -> str | None:
    for section_slugs, section_label in sections:
        if slug in section_slugs:
            return section_label
    return None


def _render_collapse_toggle(*, collapsed: bool) -> None:
    toggle_help = "Expand sidebar" if collapsed else "Collapse sidebar"
    toggle_icon = "»" if collapsed else "«"
    st.markdown(
        f'<span class="sidebar-collapse-btn" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    if st.button(
        toggle_icon,
        key="ips_sidebar_collapse_toggle",
        help=toggle_help,
        type="secondary",
    ):
        set_sidebar_collapsed(not collapsed)
        request_sidebar_toggle()
        st.rerun()


def _render_sidebar_header(*, collapsed: bool) -> None:
    header_cls = "sidebar-header sidebar-header--collapsed" if collapsed else "sidebar-header"
    st.markdown(f'<{_OT} class="{header_cls}">', unsafe_allow_html=True)
    st.markdown(f'<{_OT} class="sidebar-header-top">', unsafe_allow_html=True)
    brand_col, toggle_col = st.columns([8, 1], gap="small")
    with brand_col:
        st.markdown(f'<{_OT} class="sidebar-header-brand">', unsafe_allow_html=True)
        logo = _logo_path(compact=collapsed)
        logo_wrap_cls = "sidebar-logo-wrap sidebar-logo-wrap--collapsed" if collapsed else "sidebar-logo-wrap"
        st.markdown(f'<{_OT} class="{logo_wrap_cls}">', unsafe_allow_html=True)
        if logo:
            st.image(str(logo), width=44 if collapsed else 100)
        elif not collapsed:
            st.markdown('<p class="ips-sidebar-brand">IPS Operations</p>', unsafe_allow_html=True)
        st.markdown(f"<{_CT}>", unsafe_allow_html=True)
        if not collapsed:
            st.markdown('<p class="sidebar-logo-tagline">Industrial Plant Solutions</p>', unsafe_allow_html=True)
        st.markdown(f"<{_CT}>", unsafe_allow_html=True)
    with toggle_col:
        _render_collapse_toggle(collapsed=collapsed)
    st.markdown(f"<{_CT}>", unsafe_allow_html=True)
    st.markdown(f"<{_CT}>", unsafe_allow_html=True)
    if not collapsed:
        st.markdown('<hr class="sidebar-divider" />', unsafe_allow_html=True)


def render_sidebar(active_slug: str) -> None:
    apply_pending_sidebar_collapse()
    collapsed = is_sidebar_collapsed()
    role = normalize_role(current_role())
    field_mode = bool(st.session_state.get("ips_field_mode"))
    is_employee_nav = role == "employee"
    if is_employee_nav:
        nav_items = filter_employee_nav_for_role(EMPLOYEE_NAV_PAGES, role)
    elif field_mode:
        nav_items = filter_field_nav_for_role(FIELD_NAV_PAGES, role)
    else:
        nav_items = filter_nav_for_role(NAV_PAGES, role)
    store_sidebar_nav_fallback(nav_items)

    _ESTIMATING_SLUGS = frozenset({"estimates", "pricing_guide"})
    _OPERATIONS_SLUGS = frozenset({"inventory", "assets"})
    _LABOR_SLUGS = frozenset({"timekeeping"})
    _MANAGEMENT_SLUGS = frozenset({"tasks", "reports"})
    _ADMIN_SLUGS = frozenset({"employees", "admin", "settings"})
    _SCAN_SLUGS = frozenset({"scan_inventory", "scan_asset"})
    _SECTION_HEADERS: list[tuple[frozenset[str], str]] = [
        (_ESTIMATING_SLUGS, "Estimating"),
        (_OPERATIONS_SLUGS, "Operations"),
        (_LABOR_SLUGS, "Labor"),
        (_MANAGEMENT_SLUGS, "Management"),
        (_ADMIN_SLUGS, "Admin"),
    ]
    _shown_sections: set[str] = set()

    shell_cls = "ips-sidebar-shell ips-sidebar-collapsed" if collapsed else "ips-sidebar-shell ips-sidebar-expanded"

    with st.sidebar:
        st.markdown(
            f'<span class="{shell_cls}" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        _render_sidebar_header(collapsed=collapsed)

        nav_scroll_cls = (
            "ips-sidebar-nav-scroll sidebar-nav-scroll ips-sidebar-nav-expanded"
            if not collapsed
            else "ips-sidebar-nav-scroll sidebar-nav-scroll"
        )
        st.markdown(f'<{_OT} class="{nav_scroll_cls}">', unsafe_allow_html=True)
        for item in nav_items:
            if len(item) == 3:
                slug, label, _icon = item
            else:
                slug, label = item  # type: ignore[misc]
            section_label = _section_for_slug(slug, _SECTION_HEADERS)
            if collapsed:
                if section_label and section_label not in _shown_sections:
                    if _shown_sections:
                        st.markdown(
                            '<hr class="sidebar-nav-group-divider" aria-hidden="true" />',
                            unsafe_allow_html=True,
                        )
                    _shown_sections.add(section_label)
            elif section_label and section_label not in _shown_sections:
                st.markdown(
                    f'<p class="sidebar-section-title">{html.escape(section_label)}</p>',
                    unsafe_allow_html=True,
                )
                _shown_sections.add(section_label)
            is_active = slug == active_slug or (slug in _SCAN_SLUGS and active_slug in {"inventory", "assets"})
            if slug == "employee_qr_scan" and active_slug in {"inventory", "assets"}:
                is_active = True
            nav_cls = "sidebar-nav-item active" if is_active else "sidebar-nav-item"
            st.markdown(
                f'<span class="{nav_cls}" data-nav-slug="{html.escape(slug)}" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            btn_label = _nav_button_label(slug, label, collapsed=collapsed)
            if st.button(
                btn_label,
                key=f"nav_{slug}",
                use_container_width=not collapsed,
                type="secondary",
                help=label,
            ):
                if not is_active or slug in _SCAN_SLUGS:
                    set_nav_slug(slug)
                    request_sidebar_collapse_after_nav()
                    st.rerun()
        st.markdown(f"<{_CT}>", unsafe_allow_html=True)

        st.markdown(f'<{_OT} class="ips-sidebar-footer sidebar-footer">', unsafe_allow_html=True)

        if not collapsed and not is_employee_nav:
            st.markdown('<p class="sidebar-section-title sidebar-footer-label">View mode</p>', unsafe_allow_html=True)
        if not collapsed and not is_employee_nav:
            fm = st.toggle(
                "Field Supervisor Mode",
                value=field_mode,
                key="ips_field_mode_toggle",
                help="Field Supervisor Mode",
            )
            if fm != field_mode:
                st.session_state["ips_field_mode"] = fm
                if fm and role_can_access_page(role, "field_dashboard"):
                    set_nav_slug("field_dashboard")
                request_sidebar_collapse_after_nav()
                st.rerun()

        if not collapsed:
            prof = current_profile()
            name = html.escape(str(prof.get("full_name") or prof.get("email") or "User"))
            role_lbl = html.escape(role.replace("_", " ").title())
            st.markdown(
                f'<{_OT} class="ips-sidebar-user sidebar-user"><strong>{name}</strong><br>{role_lbl}<{_CT}>',
                unsafe_allow_html=True,
            )

        st.markdown('<span class="sidebar-footer-action" aria-hidden="true"></span>', unsafe_allow_html=True)
        logout_label = "⎋" if collapsed else "Log out"
        if st.button(logout_label, use_container_width=True, key="ips_logout", help="Log out", type="secondary"):
            sign_out()

        if not collapsed:
            st.markdown(
                f'<p class="ips-sidebar-version sidebar-version">App v{html.escape(APP_VERSION)}</p>',
                unsafe_allow_html=True,
            )
        st.markdown(f"<{_CT}>", unsafe_allow_html=True)
