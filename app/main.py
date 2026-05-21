from __future__ import annotations

import sys
from pathlib import Path

# Streamlit runs this file from app/ — ensure project root is on sys.path for `import app.*`
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
    from app.perf_debug import perf_span
except ImportError:
    from perf_debug import perf_span  # type: ignore

from auth import (
    bootstrap_auth_at_startup,
    current_role,
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
from errors import show_auth_error, show_page_error
from logging_config import configure_logging
from ui import (
    IPS_ACTIVE_PAGE_KEY,
    IPS_NAV_PAGE_KEY,
    IPS_ROUTE_SLUG_KEY,
    apply_pending_navigation,
    sync_session_route_slug_to_nav_page,
)
from branding import apply_branding, render_header

try:
    from app.ui.theme import (
        apply_global_app_styles,
        apply_global_css,
        inject_force_white_final_override,
    )
    from app.ui.clean_table import inject_clean_table_css
except ImportError:
    from ui.theme import (  # type: ignore
        apply_global_app_styles,
        apply_global_css,
        inject_force_white_final_override,
    )
    from ui.clean_table import inject_clean_table_css  # type: ignore
try:
    from app.pwa import inject_pwa_support, trigger_pwa_install_prompt
except ImportError:
    from pwa import inject_pwa_support, trigger_pwa_install_prompt  # type: ignore

try:
    from app.styles import inject_global_css as inject_ips_foundation_css
except ImportError:
    from styles import inject_global_css as inject_ips_foundation_css  # type: ignore

try:
    from app.navigation import (
        current_nav_slug,
        ensure_nav_defaults,
        normalize_nav_slug,
        on_nav_change,
        render_module,
        set_nav_slug,
    )
    from app.components.sidebar import render_sidebar as render_foundation_sidebar
    from app.utils.constants import SESSION_NAV_KEY
except ImportError:
    from navigation import (  # type: ignore
        current_nav_slug,
        ensure_nav_defaults,
        normalize_nav_slug,
        on_nav_change,
        render_module,
        set_nav_slug,
    )
    from components.sidebar import render_sidebar as render_foundation_sidebar  # type: ignore
    from utils.constants import SESSION_NAV_KEY  # type: ignore

try:
    from pages import inventory_scan
except ImportError:
    inventory_scan = None  # type: ignore


def main() -> None:
    configure_logging(settings.log_level)

    st.set_page_config(
        page_title=settings.app_name,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    with perf_span("main.auth_session"):
        init_session()
        bootstrap_auth_at_startup()
    # Camera / deep link: ``?code=INV-…`` must survive the login screen (see inventory_scan).
    with perf_span("main.deeplink_query"):
        if inventory_scan is not None:
            try:
                inventory_scan.merge_inventory_scan_deeplink_from_query()
            except Exception:
                pass
    with perf_span("main.shell_branding"):
        apply_branding()
        apply_global_app_styles()
        apply_global_css()
        inject_ips_foundation_css()
        inject_clean_table_css()
        inject_pwa_support()

    # Public customer signing flow (no login): `?tsign=<uuid>`
    try:
        tok = st.query_params.get("tsign")
    except Exception:
        tok = None
    token = None
    if isinstance(tok, list):
        token = str(tok[0]) if tok else None
    elif tok is not None:
        token = str(tok)
    if token and str(token).strip():
        try:
            try:
                from pages import sign_timesheet
            except ImportError:
                from pages import sign_timesheet  # type: ignore
            sign_timesheet.render_public(str(token).strip())
        except Exception as exc:
            show_page_error(exc, context="page:sign_timesheet_public")
        return

    # Single gate for the whole app: pages must not duplicate login checks.
    if not is_authenticated():
        inject_ips_foundation_css()
        st.markdown('<div class="ips-login-wrap">', unsafe_allow_html=True)
        render_header("IPS Operations")
        st.caption("Sign in to Industrial Plant Solutions company management")
        _pend = str(
            st.session_state.get("pending_scan_code")
            or st.session_state.get("_ips_inv_scan_deeplink_code")
            or ""
        ).strip()
        if _pend:
            st.info("You opened an **inventory scan** link. Sign in below, then we will take you to **Scan Inventory** for that code.")

        st.session_state.setdefault("login_method", "Email login")
        st.radio(
            "Sign-in method",
            ["Email login", "Phone login (OTP)"],
            horizontal=True,
            key="login_method",
            label_visibility="visible",
        )
        _login_tab = str(st.session_state.get("login_method") or "Email login")

        remember_device = st.checkbox(
            "Remember this device",
            value=True,
            help="Keeps you signed in on this phone or browser after refresh (uses secure cookies).",
        )

        if _login_tab.startswith("Email"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", type="primary", use_container_width=True, key="login_email_go"):
                try:
                    sign_in(email, password, remember_device=remember_device)
                    log_auth_state("email_login_success")
                except Exception as exc:
                    show_auth_error(exc)

        else:
            st.caption("Enter your phone number to receive a one-time code via SMS.")
            phone = st.text_input("Phone number", placeholder="+1 555 123 4567", key="login_phone")
            c1, c2 = st.columns([1, 1], gap="small")
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
                    st.session_state["login_phone"] = ""
                    st.rerun()

            if st.session_state.get("login_phone_otp_sent"):
                code = st.text_input("Enter code", key="login_phone_code")
                if st.button("Verify & login", type="primary", use_container_width=True, key="login_phone_verify"):
                    try:
                        verify_phone_otp(phone_number=phone, code=code, remember_device=remember_device)
                        st.session_state.pop("login_phone_otp_sent", None)
                        st.session_state.pop("login_phone_code", None)
                        log_auth_state("phone_login_success")
                    except Exception as exc:
                        show_auth_error(exc)

        if not is_authenticated():
            log_auth_state("login_gate_stop")
            st.markdown("</div>", unsafe_allow_html=True)
            st.stop()
        st.markdown("</div>", unsafe_allow_html=True)

    persist_auth_cookies_if_pending()
    log_auth_state("app_authenticated")

    if must_reset_password():
        render_header("Set New Password")
        st.caption("Your account requires a password reset before continuing.")

        p1 = st.text_input("New password", type="password")
        p2 = st.text_input("Confirm new password", type="password")

        if st.button("Update password", type="primary", use_container_width=True):
            if str(p1 or "").strip() != str(p2 or "").strip():
                st.error("Passwords do not match.")
            else:
                try:
                    update_password(str(p1 or ""))
                    st.success("Password updated.")
                except Exception as exc:
                    show_auth_error(exc)

        if must_reset_password():
            st.stop()

    with perf_span("main.page_routing"):
        apply_pending_navigation()
        sync_session_route_slug_to_nav_page()
        _want_scan = bool(st.session_state.get("_ips_query_wants_scan_inventory"))
        _inv_deeplink = str(st.session_state.get("_ips_inv_scan_deeplink_code") or "").strip()
        if _want_scan or _inv_deeplink:
            set_nav_slug("inventory")
        ensure_nav_defaults()
        prev_slug = st.session_state.get("_ips_last_slug")
        slug = current_nav_slug()
        st.session_state[SESSION_NAV_KEY] = slug
        if prev_slug and prev_slug != slug:
            on_nav_change(str(prev_slug), slug)
        st.session_state["_ips_last_slug"] = slug
    with perf_span("main.sidebar"):
        render_foundation_sidebar(slug)
    trigger_pwa_install_prompt()
    with perf_span(f"main.page_render:{slug}"):
        try:
            inject_clean_table_css()
            render_module(slug)
            inject_force_white_final_override()
        except Exception as exc:
            show_page_error(exc, context=f"module:{slug}")


if __name__ == "__main__":
    main()