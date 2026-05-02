from __future__ import annotations

import streamlit as st

try:
    from app.config import settings
except ImportError:
    from config import settings  # type: ignore

from auth import (
    current_role,
    init_session,
    must_reset_password,
    require_login,
    run_auth_browser_cookie_effects,
    sign_in,
    start_phone_otp,
    try_restore_supabase_session_from_cookies,
    update_password,
    verify_phone_otp,
)
from errors import show_auth_error, show_page_error
from logging_config import configure_logging
from ui import IPS_ACTIVE_PAGE_KEY, IPS_NAV_PAGE_KEY, apply_pending_navigation, render_sidebar
from ui import role_can_open_page
from branding import apply_branding, render_header

try:
    from app.ips_app_shell import inject_ips_app_shell_styles
except ImportError:
    from ips_app_shell import inject_ips_app_shell_styles  # type: ignore
try:
    from app.pwa import inject_pwa_support
except ImportError:
    from pwa import inject_pwa_support  # type: ignore

from pages import dashboard
from pages import estimates
from pages import customers_jobs
from pages import job_database
from pages import supervisor_daily_reports
from pages import supervisor_planning
from pages import job_costing
from pages import asset_database
from pages import tool_dashboard
from pages import asset_detail
from pages import assets as assets_page
from pages import asset_scanner
from pages import tool_trailer_audits
from pages import sign_timesheet
from pages import labor
from pages import inventory
from pages import inventory_dashboard
from pages import inventory_scan
from pages import time_tracking
from pages import pm_matrix_entry
from pages import weekly_timesheet
from pages import employees
from pages import employee_toolbox
from pages import people
from pages import po_expenses
from pages import admin
from pages import users


PAGES = {
    "Dashboard": dashboard.render,
    # Estimates UI: app/pages/estimates.py → estimates.render
    "Estimates": estimates.render,
    "Job Database": job_database.render,
    "Daily crew report": supervisor_daily_reports.render,
    "Assign Tasks (PM)": supervisor_planning.render_pm,
    "Work & Plan (Supervisor)": supervisor_planning.render_supervisor,
    "Customers": customers_jobs.render_customers,
    "Job Costing": job_costing.render,
    "Labor": labor.render,
    "Inventory": inventory.render,
    "Scan Inventory": inventory_scan.render,
    "Inventory Usage": inventory_dashboard.render,
    "Time Tracking": time_tracking.render,
    "PM Matrix Time Entry": pm_matrix_entry.render,
    "Weekly Timesheet": weekly_timesheet.render,
    "People": people.render,
    "Employees": employees.render,
    "Employee Toolbox": employee_toolbox.render,
    "PO / Expenses": po_expenses.render,
    "Asset Database": asset_database.render,
    "Who Has What": tool_dashboard.render,
    "Asset Scanner": asset_scanner.render,
    "Tool Trailer Audits": tool_trailer_audits.render,
    "Admin": admin.render,
    "Users": users.render,
    "Asset Detail": asset_detail.render,
    "Asset Manager": assets_page.render,
}

# Catalog pages (Labor, Inventory) gate writes inside each page;
# non-admins may browse lists read-only.
_ADMIN_ONLY_PAGES = frozenset({"People", "Employees", "Admin", "Users"})


def main() -> None:
    configure_logging(settings.log_level)

    st.set_page_config(
        page_title=settings.app_name,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session()
    # Persisted Supabase tokens (browser cookies): clear after sign-out, write after sign-in (reloads once).
    run_auth_browser_cookie_effects()
    try_restore_supabase_session_from_cookies()
    # Camera / deep link: ``?code=INV-…`` must survive the login screen (see inventory_scan).
    try:
        inventory_scan.merge_inventory_scan_deeplink_from_query()
    except Exception:
        pass
    apply_branding()
    inject_ips_app_shell_styles()
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
            sign_timesheet.render_public(str(token).strip())
        except Exception as exc:
            show_page_error(exc, context="page:sign_timesheet_public")
        return

    if not require_login():
        render_header("Login")
        st.caption("Supabase-backed multi-user estimator for Industrial Plant Solutions, LLC")
        _pend = str(
            st.session_state.get("pending_scan_code")
            or st.session_state.get("_ips_inv_scan_deeplink_code")
            or ""
        ).strip()
        if _pend:
            st.info("You opened an **inventory scan** link. Sign in below, then we will take you to **Scan Inventory** for that code.")

        tab_email, tab_phone = st.tabs(["Email login", "Phone login (OTP)"])

        remember_device = st.checkbox(
            "Remember this device",
            value=True,
            help="Keeps you signed in on this phone or browser after refresh (uses secure cookies).",
        )

        with tab_email:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login", type="primary", use_container_width=True, key="login_email_go"):
                try:
                    sign_in(email, password, remember_device=remember_device)
                    st.rerun()
                except Exception as exc:
                    show_auth_error(exc)

        with tab_phone:
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
                        st.rerun()
                    except Exception as exc:
                        show_auth_error(exc)

        st.stop()

    if must_reset_password():
        render_header("Set New Password")
        st.caption("Your account requires a password reset before continuing.")

        p1 = st.text_input("New password", type="password")
        p2 = st.text_input("Confirm new password", type="password")

        if st.button("Update password", type="primary", use_container_width=True):
            if str(p1 or "").strip() != str(p2 or "").strip():
                st.error("Passwords do not match.")
                st.stop()
            try:
                update_password(str(p1 or ""))
                st.success("Password updated.")
                st.rerun()
            except Exception as exc:
                show_auth_error(exc)
                st.stop()

        st.stop()

    apply_pending_navigation()
    # After auth: ``?page=Scan%20Inventory`` and/or ``?code=INV-…`` from QR / camera links.
    _want_scan = bool(st.session_state.get("_ips_query_wants_scan_inventory"))
    _inv_deeplink = str(st.session_state.get("_ips_inv_scan_deeplink_code") or "").strip()
    if (
        (_want_scan or _inv_deeplink)
        and not st.session_state.get(IPS_ACTIVE_PAGE_KEY)
        and role_can_open_page(current_role(), "Scan Inventory")
    ):
        st.session_state[IPS_NAV_PAGE_KEY] = "Scan Inventory"
    sidebar_page = render_sidebar()
    if not st.session_state.pop("_ips_skip_nav_overlay_clear", False):
        prev = st.session_state.get("_ips_last_nav_page")
        if prev is not None and sidebar_page != prev:
            st.session_state.pop(IPS_ACTIVE_PAGE_KEY, None)
    st.session_state["_ips_last_nav_page"] = sidebar_page
    page = st.session_state.get(IPS_ACTIVE_PAGE_KEY) or sidebar_page

    if page in _ADMIN_ONLY_PAGES and current_role() != "admin":
        st.error("Admin access required.")
        return

    # Hard enforcement: do not rely only on sidebar hiding.
    if not role_can_open_page(current_role(), str(page or "")):
        st.error("You do not have access to this page.")
        return

    render_fn = PAGES.get(page)
    if render_fn is None:
        st.error(f"Unknown page: {page}")
        return

    try:
        render_fn()
    except Exception as exc:
        show_page_error(exc, context=f"page:{page}")


if __name__ == "__main__":
    main()
