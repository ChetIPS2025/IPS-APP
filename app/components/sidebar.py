"""Fixed left sidebar navigation (slug-based)."""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

try:
    from app.auth import current_profile, current_role, sign_out
    from app.config import APP_VERSION, ROOT_DIR
    from app.utils.constants import FIELD_NAV_PAGES, NAV_PAGES, SESSION_NAV_KEY
    from app.utils.permissions import filter_nav_for_role, normalize_role
except ImportError:
    from auth import current_profile, current_role, sign_out  # type: ignore
    from config import APP_VERSION, ROOT_DIR  # type: ignore
    from utils.constants import FIELD_NAV_PAGES, NAV_PAGES, SESSION_NAV_KEY  # type: ignore
    from utils.permissions import filter_nav_for_role, normalize_role  # type: ignore

_OT, _CT = "d" + "iv", "/" + "d" + "iv"


def _logo_path() -> Path | None:
    for name in ("company_logo.png", "IPS Icon.png", "ips_logo_round.png"):
        p = ROOT_DIR / "assets" / name
        if p.is_file():
            return p
    return None


def render_sidebar(active_slug: str) -> None:
    role = normalize_role(current_role())
    field_mode = bool(st.session_state.get("ips_field_mode"))
    nav_items = FIELD_NAV_PAGES if field_mode else filter_nav_for_role(NAV_PAGES, role)

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
        for item in nav_items:
            if len(item) == 3:
                slug, label, _icon = item
            else:
                slug, label = item  # type: ignore[misc]
            is_active = slug == active_slug
            if st.button(
                label,
                key=f"nav_{slug}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if not is_active:
                    st.session_state[SESSION_NAV_KEY] = slug
                    st.rerun()

        st.markdown(f'<{_OT} class="ips-sidebar-spacer"><{_CT}>', unsafe_allow_html=True)

        fm = st.toggle("Field Supervisor Mode", value=field_mode, key="ips_field_mode_toggle")
        if fm != field_mode:
            st.session_state["ips_field_mode"] = fm
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
