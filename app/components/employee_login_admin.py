"""Lazy App Login administration panel for User Details."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.config import settings
from app.db import invite_auth_user, resend_invite_by_email
from app.pages._core._crud import is_demo_id
from app.services.employee_role_service import auth_role_from_permission_label
from app.services.people_directory_service import PeoplePermissions
from app.services.repository import clear_data_cache_for_table
from app.services.users_service import (
    admin_reset_employee_password,
    get_user_delete_context,
    resolve_employee_auth_login,
)


def _manage_login_key(employee_id: str) -> str:
    return f"ips_manage_user_login_{employee_id}"


def _norm_invite_email(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _employee_invite_email(emp: dict[str, Any]) -> str:
    ctx = get_user_delete_context(str(emp.get("id") or ""))
    email = _norm_invite_email(ctx.get("email") or emp.get("email"))
    if email in {"", "—", "none"}:
        return ""
    return email


def _invite_role_from_employee(emp: dict[str, Any]) -> str:
    perm = str(emp.get("permission_role") or emp.get("role") or "Employee")
    return auth_role_from_permission_label(perm)


def _login_panel_error_message(exc: Exception, *, action: str) -> str:
    text = str(exc or "").strip()
    if not text:
        return f"Could not {action.lower()}."
    lower = text.lower()
    if "user_id=" in lower or "exc)" in lower or "raw_result=" in lower:
        return f"Could not {action.lower()}. Try again or contact an administrator."
    if any(
        phrase in lower
        for phrase in (
            "no app login account",
            "no supabase login",
            "user not found",
            "create login",
            "contact an administrator",
            "already exists",
            "password does not meet",
            "valid work email",
            "email is required",
            "email domain",
            "at least 6",
            "indfustrial",
            "could not sync the app profile",
            "app login could not be updated",
            "service role",
            "admin api key",
            "reset this user's password",
            "password reset is not available",
            "could not reset this user's password",
        )
    ):
        return text
    return f"Could not {action.lower()}. Try again or contact an administrator."


def _admin_allowed_email_domain() -> str:
    return (
        str(
            getattr(settings, "allowed_email_domain", "")
            or getattr(settings, "company_email_domain", "")
            or ""
        )
        .strip()
        .lower()
        or "industrialplantsolution.com"
    )


def _admin_reset_employee_login_password(emp: dict[str, Any], password: str) -> tuple[str, bool]:
    eid = str(emp.get("id") or "").strip()
    result = admin_reset_employee_password(
        eid,
        password,
        employee=emp,
        role=_invite_role_from_employee(emp),
        allowed_email_domain=_admin_allowed_email_domain(),
    )
    if not result.ok:
        raise RuntimeError(result.error or "Could not reset this user's password.")
    email = str((result.data or {}).get("email") or _employee_invite_email(emp) or "").strip()
    created = bool((result.data or {}).get("created_login"))
    return email, created


def _send_employee_invite(emp: dict[str, Any]) -> str:
    eid = str(emp.get("id") or "").strip()
    email = _employee_invite_email(emp)
    if not email or "@" not in email:
        raise RuntimeError("Add a valid work email before sending an invite.")
    login = resolve_employee_auth_login(eid, employee=emp)
    if login.get("has_login"):
        raise RuntimeError("This user already has a login. Use Resend invite instead.")
    invite_auth_user(
        email=email,
        role=_invite_role_from_employee(emp),
        employee_id=eid or None,
        require_employee_link=False,
    )
    clear_data_cache_for_table("users")
    return email


def _resend_employee_invite(emp: dict[str, Any]) -> str:
    email = _employee_invite_email(emp)
    if not email or "@" not in email:
        raise RuntimeError("No email on file for this user.")
    resend_invite_by_email(email=email)
    return email


def _admin_auth_status_label(login: dict[str, Any]) -> tuple[str, str]:
    if login.get("auth_link_stale"):
        return "Stale", "stale"
    if login.get("has_login"):
        return "Connected", "connected"
    if login.get("auth_unlinked"):
        return "Unlinked", "stale"
    return "Missing", "missing"


def _admin_auth_status_html(*, login: dict[str, Any], email: str) -> str:
    status, modifier = _admin_auth_status_label(login)
    email_bit = (
        f'<span class="ips-admin-auth-status-email">{html.escape(email)}</span>'
        if email and "@" in email
        else ""
    )
    return (
        f'<p class="ips-admin-auth-status ips-admin-auth-status--{modifier}">'
        f'<span class="ips-admin-auth-status-label">Auth Status:</span> '
        f'<span class="ips-admin-auth-status-value">{html.escape(status)}</span>'
        f"{email_bit}</p>"
    )


def _clear_login_password_field(key: str) -> None:
    if key in st.session_state:
        del st.session_state[key]


def render_lazy_login_panel(
    emp: dict[str, Any],
    rk: str,
    *,
    permissions: PeoplePermissions,
) -> None:
    from app.perf_debug import perf_span

    if not permissions.can_manage_auth_login:
        return
    eid = str(emp.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return

    manage_key = _manage_login_key(eid)
    st.markdown(
        '<p class="ips-user-actions-title">App Login</p>',
        unsafe_allow_html=True,
    )
    if not st.session_state.get(manage_key):
        if st.button("Manage Login", key=f"emp_manage_login_{rk}", use_container_width=False):
            st.session_state[manage_key] = True
            st.rerun()
        return

    with perf_span("people.detail.login_status"):
        login = resolve_employee_auth_login(eid, employee=emp)
        email = _employee_invite_email(emp)
        has_login = bool(login.get("has_login"))

        st.markdown('<div class="ips-admin-pw-reset-marker"></div>', unsafe_allow_html=True)
        st.caption("Set a new password for this user's app login.")
        st.markdown(_admin_auth_status_html(login=login, email=email), unsafe_allow_html=True)

        if not email or "@" not in email:
            st.caption("Add a work email on this user before resetting their login.")
        else:
            status_value, _ = _admin_auth_status_label(login)
            if status_value == "Missing":
                st.caption("No app login is linked yet. Reset Password will create one for this email.")
            elif status_value == "Unlinked":
                st.caption(
                    "A login or profile exists for this email but is not linked to this employee. "
                    "Reset Password will link the account and set the password."
                )
            elif status_value == "Stale":
                st.caption("Auth link is stale. Reset Password will refresh the link to the correct login.")

            pw_key = f"emp_login_pw_{rk}"
            pw = st.text_input(
                "New password for this user",
                type="password",
                key=pw_key,
                placeholder="At least 6 characters",
            )
            reset_col, email_col, close_col = st.columns(3)
            with reset_col:
                reset_clicked = st.button(
                    "Reset Password",
                    type="primary",
                    key=f"emp_set_login_pw_{rk}",
                    use_container_width=True,
                )
            with email_col:
                if has_login:
                    email_link_clicked = st.button(
                        "Email Password Reset Link",
                        key=f"emp_resend_invite_{rk}",
                        use_container_width=True,
                    )
                else:
                    email_link_clicked = st.button(
                        "Send Invite Email",
                        key=f"emp_send_invite_{rk}",
                        use_container_width=True,
                    )
            with close_col:
                if st.button("Close Login Management", key=f"emp_close_login_{rk}", use_container_width=True):
                    st.session_state.pop(manage_key, None)
                    _clear_login_password_field(pw_key)
                    st.rerun()
            if st.button("Refresh Login Status", key=f"emp_refresh_login_{rk}"):
                st.rerun()

            if reset_clicked:
                if len(str(pw or "").strip()) < 6:
                    st.error("Enter a password of at least 6 characters.")
                    _clear_login_password_field(pw_key)
                else:
                    try:
                        reset_email, created = _admin_reset_employee_login_password(emp, str(pw))
                        _clear_login_password_field(pw_key)
                        flash_msg = (
                            f"Login created for {reset_email}."
                            if created
                            else f"Password reset for {reset_email}."
                        )
                        st.session_state["users_action_flash"] = ("success", flash_msg)
                        st.rerun()
                    except Exception as exc:
                        _clear_login_password_field(pw_key)
                        st.error(_login_panel_error_message(exc, action="Reset Password"))

            if email_link_clicked:
                try:
                    if has_login:
                        sent_to = _resend_employee_invite(emp)
                        st.session_state["users_action_flash"] = (
                            "success",
                            f"Password reset link sent to {sent_to}.",
                        )
                    else:
                        sent_to = _send_employee_invite(emp)
                        st.session_state["users_action_flash"] = ("success", f"Invite sent to {sent_to}.")
                    st.rerun()
                except Exception as exc:
                    action = "Email Password Reset Link" if has_login else "Send Invite Email"
                    st.error(_login_panel_error_message(exc, action=action))


def render_lazy_install_share(*, permissions: PeoplePermissions) -> None:
    if not permissions.can_manage_actions:
        return
    show_key = "ips_user_install_share_open"
    st.markdown(
        '<p class="ips-user-actions-title">Install / Share Access</p>',
        unsafe_allow_html=True,
    )
    if not st.session_state.get(show_key):
        if st.button("Show Options", key="ips_user_install_share_toggle"):
            st.session_state[show_key] = True
            st.rerun()
        return
    from app.components.install_share import render_install_share_user_details

    render_install_share_user_details()
    if st.button("Hide Options", key="ips_user_install_share_hide"):
        st.session_state.pop(show_key, None)
        st.rerun()


__all__ = ["render_lazy_install_share", "render_lazy_login_panel"]
