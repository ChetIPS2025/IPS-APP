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


def _logo_path() -> Path | None:
    for name in ("ips_logo_header.png", "IPS Icon.png", "company_logo.png", "ips_logo_round.png"):
        p = ROOT_DIR / "assets" / name
        if p.is_file():
            return p
    return None


def _nav_button_label(slug: str, label: str, *, collapsed: bool) -> str:
    icon = nav_icon_for_slug(slug)
    if collapsed:
        return icon
    return f"{icon}  {label}"


def _render_collapse_toggle(*, collapsed: bool) -> None:
    toggle_help = "Expand sidebar" if collapsed else "Collapse sidebar"
    toggle_icon = "›" if collapsed else "‹"
    st.markdown(
        f'<span class="ips-sidebar-collapse-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    if st.button(
        toggle_icon,
        key="ips_sidebar_collapse_toggle",
        help=toggle_help,
        use_container_width=collapsed,
    ):
        set_sidebar_collapsed(not collapsed)
        request_sidebar_toggle()
        st.rerun()


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
    _OPERATIONS_SLUGS = frozenset({"inventory", "assets", "rental_equipment"})
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
    st.markdown(
        f'<span class="{shell_cls}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown(f'<{_OT} class="ips-sidebar-topbar">', unsafe_allow_html=True)
        _render_collapse_toggle(collapsed=collapsed)
        st.markdown(f"<{_CT}>", unsafe_allow_html=True)

        if not collapsed:
            st.markdown(f'<{_OT} class="ips-sidebar-logo-wrap">', unsafe_allow_html=True)
            logo = _logo_path()
            if logo:
                st.image(str(logo), use_container_width=True)
            else:
                st.markdown('<p class="ips-sidebar-brand">IPS Operations</p>', unsafe_allow_html=True)
            st.markdown(
                f'<p class="ips-sidebar-tagline">Industrial Plant Solutions</p><{_CT}>',
                unsafe_allow_html=True,
            )
            st.markdown('<p class="ips-sidebar-nav-label">Navigation</p>', unsafe_allow_html=True)

        st.markdown(f'<{_OT} class="ips-sidebar-nav-scroll">', unsafe_allow_html=True)
        for item in nav_items:
            if len(item) == 3:
                slug, label, _icon = item
            else:
                slug, label = item  # type: ignore[misc]
            if not collapsed:
                for section_slugs, section_label in _SECTION_HEADERS:
                    if slug in section_slugs and section_label not in _shown_sections:
                        st.markdown(
                            f'<p class="ips-sidebar-nav-label ips-sidebar-section-label">{html.escape(section_label)}</p>',
                            unsafe_allow_html=True,
                        )
                        _shown_sections.add(section_label)
                        break
            is_active = slug == active_slug or (slug in _SCAN_SLUGS and active_slug in {"inventory", "assets"})
            if slug == "employee_qr_scan" and active_slug in {"inventory", "assets"}:
                is_active = True
            btn_label = _nav_button_label(slug, label, collapsed=collapsed)
            st.markdown(
                f'<span class="ips-nav-btn-wrap ips-nav-btn-{"active" if is_active else "idle"}" '
                f'data-nav-slug="{html.escape(slug)}" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            if st.button(
                btn_label,
                key=f"nav_{slug}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
                help=label,
            ):
                if not is_active or slug in _SCAN_SLUGS:
                    set_nav_slug(slug)
                    request_sidebar_collapse_after_nav()
                    st.rerun()
        st.markdown(f"<{_CT}>", unsafe_allow_html=True)

        st.markdown(f'<{_OT} class="ips-sidebar-footer">', unsafe_allow_html=True)

        if not collapsed and not is_employee_nav:
            st.markdown('<p class="ips-sidebar-field-toggle-label">View mode</p>', unsafe_allow_html=True)
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
                f'<{_OT} class="ips-sidebar-user"><strong>{name}</strong><br>{role_lbl}<{_CT}>',
                unsafe_allow_html=True,
            )

        logout_label = "⎋" if collapsed else "Log out"
        if st.button(logout_label, use_container_width=True, key="ips_logout", help="Log out"):
            sign_out()

        if not collapsed:
            st.markdown(
                f'<p class="ips-sidebar-version">App v{html.escape(APP_VERSION)}</p>',
                unsafe_allow_html=True,
            )
        st.markdown(f"<{_CT}>", unsafe_allow_html=True)
