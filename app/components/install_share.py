"""IPS App install link — share URL, admin tools, and welcome announcement."""

from __future__ import annotations

import html
import urllib.parse
from datetime import date
from typing import Any

import streamlit as st

WELCOME_INSTALL_UPDATE_ID = "cu-welcome-ips-app-install"


def install_share_url() -> str:
    from app.pwa import install_page_url
    return install_page_url()


def _install_share_mailto(*, share_url: str) -> str:
    subject = urllib.parse.quote("Install the IPS App")
    body = urllib.parse.quote(
        "Open this link to install IPS Operations. The page shows the right steps for "
        f"iPhone, Android, or computer:\n\n{share_url}"
    )
    return f"mailto:?subject={subject}&body={body}"


def welcome_install_company_update() -> dict[str, Any]:
    """Pinned welcome announcement with the live install link."""
    url = install_share_url()
    return {
        "id": WELCOME_INSTALL_UPDATE_ID,
        "category": "Announcements",
        "title": "Welcome — Install the IPS App on Your Phone",
        "body": (
            "Open the install link on any device. iPhone/iPad: Safari → Add to Home Screen. "
            "Android: Chrome → Install app. Computer: Open the app or install in Chrome/Edge.\n\n"
            f"Install link: {url}"
        ),
        "date": date.today().isoformat(),
        "pinned": True,
        "is_new": True,
    }


def with_welcome_install_update(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prepend the welcome install post when it is not already present."""
    if any(str(r.get("id") or "") == WELCOME_INSTALL_UPDATE_ID for r in rows or []):
        return list(rows or [])
    if any("install the ips app" in str(r.get("title") or "").lower() for r in rows or []):
        return list(rows or [])
    welcome = welcome_install_company_update()
    return [welcome, *list(rows or [])]


def render_install_share_admin(*, compact: bool = False) -> None:
    """Admin copy/email workflow for the public install page."""
    from app.services.users_service import can_manage_user_actions
    if not can_manage_user_actions():
        return

    share_url = install_share_url()
    mailto = _install_share_mailto(share_url=share_url)
    if compact:
        st.markdown("**Share IPS App install link**")
        st.caption(
            "One link for every device — the install page shows the right steps automatically."
        )
        st.code(share_url, language=None)
        c1, c2 = st.columns(2)
        with c1:
            st.link_button("Email link", mailto, use_container_width=True)
        with c2:
            st.link_button("Open /install", share_url, use_container_width=True)
        return

    st.markdown("---")
    st.markdown("**Admin: share install link**")
    st.caption(
        "Send this link so someone can install IPS on iPhone, Android, or computer."
    )
    st.code(share_url, language=None)
    col_a, col_b = st.columns(2)
    with col_a:
        st.link_button("Email install link", mailto, use_container_width=True)
    with col_b:
        st.link_button("Open install page", share_url, use_container_width=True)


def render_install_share_user_details() -> None:
    """Compact install link block inside User Details (admins)."""
    from app.services.users_service import can_manage_user_actions
    if not can_manage_user_actions():
        return
    share_url = install_share_url()
    mailto = _install_share_mailto(share_url=share_url)
    st.markdown(
        '<p class="ips-user-actions-title">Install IPS App</p>',
        unsafe_allow_html=True,
    )
    st.caption("Send the install link so this user can add IPS to their phone home screen.")
    st.code(share_url, language=None)
    c1, c2 = st.columns(2)
    with c1:
        st.link_button("Email install link", mailto, use_container_width=True)
    with c2:
        st.link_button("Open install page", share_url, use_container_width=True)


def render_install_share_settings() -> None:
    """Install link section on Settings / Application Settings."""
    share_url = install_share_url()
    mailto = _install_share_mailto(share_url=share_url)
    st.markdown("**Mobile app install link**")
    st.caption(
        "Share this link with employees. The page adapts for iPhone, Android, or computer."
    )
    st.code(share_url, language=None)
    c1, c2 = st.columns(2)
    with c1:
        st.link_button("Email install link", mailto, use_container_width=True)
    with c2:
        st.link_button("Open install page", share_url, use_container_width=True)


def render_install_share_login_footer() -> None:
    """Public install link on the login page footer."""
    share_url = install_share_url()
    safe_url = html.escape(share_url)
    st.markdown(
        f"""
<div class="ips-login-install-footer">
  <p class="ips-login-install-footer-title">Install on your phone</p>
  <p class="ips-login-install-footer-text">
    Open the IPS install page for device-specific steps (iPhone, Android, or computer).
  </p>
  <a class="ips-login-install-footer-link" href="{safe_url}">Install IPS App</a>
</div>
""",
        unsafe_allow_html=True,
    )
