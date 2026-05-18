"""Dashboard-only sidebar branding (IPS, profile footer)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_profile, current_role
except ImportError:
    from auth import current_profile, current_role  # type: ignore


def inject_coastal_sidebar_footer() -> None:
    """Profile block at bottom of sidebar when Dashboard is active."""
    if st.session_state.get("_coastal_sidebar_footer_done"):
        return
    prof = current_profile() or {}
    nm = str(prof.get("full_name") or prof.get("name") or "").strip()
    if not nm:
        nm = str(prof.get("email") or "User").split("@")[0]
    role = str(current_role() or "User").replace("_", " ").title()
    st.sidebar.markdown(
        (
            '<p class="ips-coastal-sidebar-brand">IPS · INDUSTRIAL PROJECT SERVICES</p>'
            f'<div class="ips-coastal-profile">'
            f'<p class="ips-coastal-profile-name">{html.escape(nm)}</p>'
            f'<p class="ips-coastal-profile-role">{html.escape(role)}</p>'
            f"</div>"
        ),
        unsafe_allow_html=True,
    )
    st.session_state["_coastal_sidebar_footer_done"] = True
