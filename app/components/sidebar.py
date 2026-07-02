"""Fixed left sidebar navigation (slug-based)."""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

try:
    from app.auth import current_profile, current_role, sign_out
    from app.config import APP_VERSION, ROOT_DIR
    from app.navigation import set_nav_slug
    from app.utils.constants import FIELD_NAV_PAGES, NAV_PAGES
    from app.utils.permissions import (
        filter_field_nav_for_role,
        filter_nav_for_role,
        normalize_role,
        role_can_access_page,
    )
except ImportError:
    from auth import current_profile, current_role, sign_out  # type: ignore
    from config import APP_VERSION, ROOT_DIR  # type: ignore
    from navigation import set_nav_slug  # type: ignore
    from utils.constants import FIELD_NAV_PAGES, NAV_PAGES  # type: ignore
    from utils.permissions import (  # type: ignore
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


def render_sidebar(active_slug: str) -> None:
    role = normalize_role(current_role())
    field_mode = bool(st.session_state.get("ips_field_mode"))
    nav_items = (
        filter_field_nav_for_role(FIELD_NAV_PAGES, role)
        if field_mode
        else filter_nav_for_role(NAV_PAGES, role)
    )
    try:
        from app.components.sidebar_shell import store_sidebar_nav_fallback
    except ImportError:
        from components.sidebar_shell import store_sidebar_nav_fallback  # type: ignore
    store_sidebar_nav_fallback(nav_items)
    _ESTIMATING_SLUGS = frozenset({"estimates", "pricing_guide"})
    _SCAN_SLUGS = frozenset({"scan_inventory", "scan_asset"})

    with st.sidebar:
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

        st.markdown(f'<p class="ips-sidebar-nav-label">Navigation</p>', unsafe_allow_html=True)
        estimating_header_shown = False
        for item in nav_items:
            if len(item) == 3:
                slug, label, _icon = item
            else:
                slug, label = item  # type: ignore[misc]
            if slug in _ESTIMATING_SLUGS and not estimating_header_shown:
                st.markdown(
                    '<p class="ips-sidebar-nav-label" style="margin-top:0.75rem;">Estimating</p>',
                    unsafe_allow_html=True,
                )
                estimating_header_shown = True
            is_active = slug == active_slug or (slug in _SCAN_SLUGS and active_slug in {"inventory", "assets"})
            if st.button(
                label,
                key=f"nav_{slug}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if not is_active or slug in _SCAN_SLUGS:
                    set_nav_slug(slug)
                    st.rerun()

        st.markdown(f'<{_OT} class="ips-sidebar-spacer"><{_CT}>', unsafe_allow_html=True)

        fm = st.toggle("Field Supervisor Mode", value=field_mode, key="ips_field_mode_toggle")
        if fm != field_mode:
            st.session_state["ips_field_mode"] = fm
            if fm and role_can_access_page(role, "field_dashboard"):
                set_nav_slug("field_dashboard")
            st.rerun()

        prof = current_profile()
        name = html.escape(str(prof.get("full_name") or prof.get("email") or "User"))
        role_lbl = html.escape(role.replace("_", " ").title())
        st.markdown(
            f'<{_OT} class="ips-sidebar-user"><strong>{name}</strong><br>{role_lbl}<{_CT}>',
            unsafe_allow_html=True,
        )
        if st.button("Log out", use_container_width=True, key="ips_logout"):
            sign_out()

        st.markdown(
            f'<p class="ips-sidebar-version">App v{html.escape(APP_VERSION)}</p>',
            unsafe_allow_html=True,
        )
