"""Fixed left sidebar navigation (slug-based)."""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

try:
    from app.auth import current_profile, current_role, effective_role, sign_out
    from app.components.sidebar_nav_icons import nav_icon_for_slug
    from app.components.sidebar_shell import (
        apply_pending_sidebar_collapse,
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
    from app.utils.view_as import is_real_admin, is_view_as_active, render_view_as_selector
except ImportError:
    from auth import current_profile, current_role, effective_role, sign_out  # type: ignore
    from components.sidebar_nav_icons import nav_icon_for_slug  # type: ignore
    from components.sidebar_shell import (  # type: ignore
        apply_pending_sidebar_collapse,
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
    from utils.view_as import is_real_admin, is_view_as_active, render_view_as_selector  # type: ignore

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


def _nav_button_label(slug: str, label: str) -> str:
    icon = nav_icon_for_slug(slug)
    return f"{icon}\u2002{label}"


def _section_for_slug(slug: str, sections: list[tuple[frozenset[str], str]]) -> str | None:
    for section_slugs, section_label in sections:
        if slug in section_slugs:
            return section_label
    return None


def _sidebar_rail_icon_html(*, size: int = 28) -> str:
    """Inline IPS icon for the collapsed sidebar rail header."""
    try:
        from app.branding import _logo_data_uri
    except ImportError:
        from branding import _logo_data_uri  # type: ignore
    logo = _logo_path(compact=True)
    if not logo:
        return '<span class="sidebar-logo-icon sidebar-logo-icon-fallback">IPS</span>'
    src = _logo_data_uri(str(logo))
    return (
        f'<img class="sidebar-logo-icon" src="{src}" alt="IPS" '
        f'width="{size}" height="{size}" style="width:{size}px;height:{size}px;" />'
    )


def _render_sidebar_header() -> None:
    st.markdown(
        f"""
<div class="sidebar-header sidebar-header--collapsed-rail">
  <span class="sidebar-header-anchor sidebar-header-anchor--collapsed" aria-hidden="true"></span>
  <div class="sidebar-logo-wrap sidebar-logo-wrap--collapsed">
    {_sidebar_rail_icon_html(size=28)}
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="sidebar_expanded_header_wrap"):
        st.markdown(
            '<span class="sidebar-header-expanded-rail-marker sidebar-header-anchor--expanded" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        brand_col, toggle_col = st.columns([8, 1], gap="small", vertical_alignment="center")
        with brand_col:
            st.markdown('<span class="sidebar-header-brand-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
            logo = _logo_path(compact=False)
            st.markdown('<span class="sidebar-logo-wrap sidebar-logo-wrap--expanded" aria-hidden="true"></span>', unsafe_allow_html=True)
            if logo:
                st.image(str(logo), width=100)
            else:
                st.markdown('<p class="ips-sidebar-brand">IPS Operations</p>', unsafe_allow_html=True)
            st.markdown(
                '<p class="sidebar-logo-tagline sidebar-brand-text">Industrial Plant Solutions</p>',
                unsafe_allow_html=True,
            )
        with toggle_col:
            _render_collapse_toggle(collapsed=True)
        st.markdown('<hr class="sidebar-divider sidebar-divider--expanded-rail" />', unsafe_allow_html=True)


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


def render_sidebar(active_slug: str) -> None:
    apply_pending_sidebar_collapse()
    role = normalize_role(effective_role())
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

    shell_cls = "ips-sidebar-shell ips-sidebar-collapsed ips-sidebar-hover-rail app-sidebar"

    with st.sidebar:
        st.markdown(
            f'<span class="{shell_cls}" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        _render_sidebar_header()

        nav_scroll_cls = "ips-sidebar-nav-scroll sidebar-nav-scroll ips-sidebar-nav-expanded"
        st.markdown(
            f'<span class="{nav_scroll_cls} sidebar-nav-scroll-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        for item in nav_items:
            if len(item) == 3:
                slug, label, _icon = item
            else:
                slug, label = item  # type: ignore[misc]
            section_label = _section_for_slug(slug, _SECTION_HEADERS)
            if section_label and section_label not in _shown_sections:
                st.markdown(
                    f'<p class="sidebar-section-title section-header">{html.escape(section_label)}</p>',
                    unsafe_allow_html=True,
                )
                _shown_sections.add(section_label)
            is_active = slug == active_slug or (slug in _SCAN_SLUGS and active_slug in {"inventory", "assets"})
            if slug == "employee_qr_scan" and active_slug in {"inventory", "assets"}:
                is_active = True
            nav_cls = "sidebar-nav-item active" if is_active else "sidebar-nav-item"
            st.markdown(
                f'<span class="{nav_cls} nav-item" data-nav-slug="{html.escape(slug)}" '
                f'data-nav-label="{html.escape(label)}" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            btn_label = _nav_button_label(slug, label)
            if st.button(
                btn_label,
                key=f"nav_{slug}",
                use_container_width=True,
                type="secondary",
                help=label,
            ):
                if not is_active or slug in _SCAN_SLUGS:
                    set_nav_slug(slug)
                    request_sidebar_collapse_after_nav()
                    st.rerun()

        st.markdown(f'<{_OT} class="ips-sidebar-footer sidebar-footer">', unsafe_allow_html=True)

        if not is_employee_nav:
            st.markdown('<p class="sidebar-section-title sidebar-footer-label section-header">View mode</p>', unsafe_allow_html=True)
        if not is_employee_nav and not is_view_as_active():
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

        if is_real_admin() and not is_view_as_active():
            render_view_as_selector()

        prof = current_profile()
        name = html.escape(str(prof.get("full_name") or prof.get("email") or "User"))
        role_lbl = html.escape(role.replace("_", " ").title())
        st.markdown(
            f'<{_OT} class="ips-sidebar-user sidebar-user sidebar-brand-text"><strong>{name}</strong><br>{role_lbl}<{_CT}>',
            unsafe_allow_html=True,
        )

        st.markdown('<span class="sidebar-footer-action" aria-hidden="true"></span>', unsafe_allow_html=True)
        if st.button("⎋\u2002Log out", use_container_width=True, key="ips_logout", help="Log out", type="secondary"):
            sign_out()

        st.markdown(
            f'<p class="ips-sidebar-version sidebar-version sidebar-brand-text">App v{html.escape(APP_VERSION)}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(f"<{_CT}>", unsafe_allow_html=True)
