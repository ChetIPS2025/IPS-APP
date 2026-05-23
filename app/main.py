from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _APP_DIR.parent
_root_str = str(_ROOT_DIR)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)

import streamlit as st

try:
    from app.config import settings
except ImportError:
    from config import settings  # type: ignore

try:
    from app.auth import (
        bootstrap_auth_at_startup,
        init_session,
        is_authenticated,
        log_auth_state,
        must_reset_password,
        persist_auth_cookies_if_pending,
        sign_in,
        start_phone_otp,
        update_password,
        verify_phone_otp,
    )
except ImportError:
    from auth import (  # type: ignore
        bootstrap_auth_at_startup,
        init_session,
        is_authenticated,
        log_auth_state,
        must_reset_password,
        persist_auth_cookies_if_pending,
        sign_in,
        start_phone_otp,
        update_password,
        verify_phone_otp,
    )

try:
    from app.errors import show_auth_error, show_page_error
except ImportError:
    from errors import show_auth_error, show_page_error  # type: ignore

try:
    from app.logging_config import configure_logging
except ImportError:
    from logging_config import configure_logging  # type: ignore

try:
    from app.components.sidebar import render_sidebar
    from app.navigation import (
        current_nav_slug,
        ensure_nav_defaults,
        on_nav_change,
        render_module,
        set_nav_slug,
    )
    from app.styles import inject_authenticated_shell_css, inject_global_css, inject_unauthenticated_shell_css
    from app.utils.constants import SESSION_NAV_KEY
except ImportError:
    from components.sidebar import render_sidebar  # type: ignore
    from navigation import (  # type: ignore
        current_nav_slug,
        ensure_nav_defaults,
        on_nav_change,
        render_module,
        set_nav_slug,
    )
    from styles import inject_authenticated_shell_css, inject_global_css, inject_unauthenticated_shell_css  # type: ignore
    from utils.constants import SESSION_NAV_KEY  # type: ignore


def _render_login() -> None:
    inject_unauthenticated_shell_css()
    st.markdown('<div class="ips-login-wrap">', unsafe_allow_html=True)
    st.markdown(
        """
<div class="ips-login-brand">
  <h1 class="ips-page-title">IPS Operations</h1>
  <p class="ips-page-subtitle">Sign in to Industrial Plant Solutions company management</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("login_method", "Email login")
    st.radio(
        "Sign-in method",
        ["Email login", "Phone login (OTP)"],
        horizontal=True,
        key="login_method",
    )
    remember_device = st.checkbox(
        "Remember this device",
        value=True,
        help="Keeps you signed in on this browser after refresh.",
    )

    if str(st.session_state.get("login_method") or "").startswith("Email"):
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", type="primary", use_container_width=True, key="login_email_go"):
            try:
                sign_in(email, password, remember_device=remember_device)
                log_auth_state("email_login_success")
                st.rerun()
            except Exception as exc:
                show_auth_error(exc)
    else:
        phone = st.text_input("Phone number", placeholder="+1 555 123 4567", key="login_phone")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Send code", use_container_width=True, key="login_phone_send"):
                try:
                    start_phone_otp(phone_number=phone)
                    st.session_state["login_phone_otp_sent"] = True
                    st.success("Code sent. Check your text messages.")
                except Exception as exc:
                    show_auth_error(exc)
        with c2:
            if st.button("Clear", use_container_width=True, key="login_phone_clear"):
                st.session_state.pop("login_phone_otp_sent", None)
                st.rerun()

        if st.session_state.get("login_phone_otp_sent"):
            code = st.text_input("Enter code", key="login_phone_code")
            if st.button("Verify & login", type="primary", use_container_width=True, key="login_phone_verify"):
                try:
                    verify_phone_otp(phone_number=phone, code=code, remember_device=remember_device)
                    st.session_state.pop("login_phone_otp_sent", None)
                    log_auth_state("phone_login_success")
                    st.rerun()
                except Exception as exc:
                    show_auth_error(exc)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_password_reset() -> None:
    st.markdown("### Set New Password")
    st.caption("Your account requires a password reset before continuing.")
    p1 = st.text_input("New password", type="password", key="reset_pw1")
    p2 = st.text_input("Confirm new password", type="password", key="reset_pw2")
    if st.button("Update password", type="primary", use_container_width=True):
        if str(p1 or "").strip() != str(p2 or "").strip():
            st.error("Passwords do not match.")
        else:
            try:
                update_password(str(p1 or ""))
                st.success("Password updated.")
                st.rerun()
            except Exception as exc:
                show_auth_error(exc)


def main() -> None:
    configure_logging(settings.log_level)

    st.set_page_config(
        page_title=getattr(settings, "app_name", "IPS Operations"),
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session()
    bootstrap_auth_at_startup()
    inject_global_css()

    try:
        from app.services.asset_qr import capture_asset_deeplink_from_query
    except ImportError:
        from services.asset_qr import capture_asset_deeplink_from_query  # type: ignore
    capture_asset_deeplink_from_query()

    try:
        from app.pages.inventory_qr_action import capture_inventory_qr_from_query
    except ImportError:
        from pages.inventory_qr_action import capture_inventory_qr_from_query  # type: ignore
    capture_inventory_qr_from_query()

    if not is_authenticated():
        _render_login()
        if not is_authenticated():
            log_auth_state("login_gate_stop")
            st.stop()

    persist_auth_cookies_if_pending()
    inject_authenticated_shell_css()
    log_auth_state("app_authenticated")

    if must_reset_password():
        _render_password_reset()
        if must_reset_password():
            st.stop()

    try:
        qr_kind = str(st.query_params.get("qr") or "").strip().lower()
    except Exception:
        qr_kind = ""
    if qr_kind == "inventory" or st.session_state.get("_ips_qr_inventory_page"):
        try:
            from app.pages.inventory_qr_action import render_inventory_qr_action_page
        except ImportError:
            from pages.inventory_qr_action import render_inventory_qr_action_page  # type: ignore
        inject_authenticated_shell_css()
        render_inventory_qr_action_page()
        st.stop()

    ensure_nav_defaults()
    prev_slug = st.session_state.get("_ips_last_slug")
    slug = current_nav_slug()
    st.session_state[SESSION_NAV_KEY] = slug
    if prev_slug and prev_slug != slug:
        on_nav_change(str(prev_slug), slug)
    st.session_state["_ips_last_slug"] = slug

    try:
        from app.services.asset_qr import apply_asset_deeplink_navigation
    except ImportError:
        from services.asset_qr import apply_asset_deeplink_navigation  # type: ignore
    apply_asset_deeplink_navigation()
    slug = current_nav_slug()
    st.session_state[SESSION_NAV_KEY] = slug

    render_sidebar(slug)

    try:
        render_module(slug)
    except Exception as exc:
        show_page_error(exc, context=f"module:{slug}")


if __name__ == "__main__":
    main()
