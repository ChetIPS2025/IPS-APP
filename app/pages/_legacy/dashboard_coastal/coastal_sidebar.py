"""Dashboard sidebar chrome (IPS brand header, profile footer)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_profile, current_role
except ImportError:
    from auth import current_profile, current_role  # type: ignore


def inject_coastal_sidebar_header() -> None:
    """IPS company block directly under the round logo (Dashboard only)."""
    if st.session_state.get("_coastal_sidebar_header_done"):
        return
    st.sidebar.markdown(
        (
            '<div class="ips-coastal-sidebar-head">'
            '<p class="ips-coastal-sidebar-title">IPS</p>'
            '<p class="ips-coastal-sidebar-sub">INDUSTRIAL PROJECT SERVICES</p>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.session_state["_coastal_sidebar_header_done"] = True


def inject_coastal_sidebar_footer() -> None:
    """Profile + collapse hint pinned visually at the bottom of the sidebar."""
    if st.session_state.get("_coastal_sidebar_footer_done"):
        return
    prof = current_profile() or {}
    nm = str(prof.get("full_name") or prof.get("name") or "").strip()
    if not nm:
        nm = str(prof.get("email") or "User").split("@")[0]
    role = str(current_role() or "User").replace("_", " ").title()
    initials = "".join(p[0].upper() for p in nm.split()[:2]) or "U"
    st.sidebar.markdown(
        (
            '<div class="ips-coastal-profile">'
            f'<span class="ips-coastal-profile-avatar">{html.escape(initials)}</span>'
            '<div class="ips-coastal-profile-text">'
            f'<p class="ips-coastal-profile-name">{html.escape(nm)}</p>'
            f'<p class="ips-coastal-profile-role">{html.escape(role)}</p>'
            "</div></div>"
            '<p class="ips-coastal-collapse-hint">◀ Collapse</p>'
        ),
        unsafe_allow_html=True,
    )
    st.session_state["_coastal_sidebar_footer_done"] = True


def reset_coastal_sidebar_session() -> None:
    """Clear one-shot flags when leaving Dashboard."""
    for k in ("_coastal_sidebar_header_done", "_coastal_sidebar_footer_done"):
        st.session_state.pop(k, None)
