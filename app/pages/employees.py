"""Employees / Users module (Phase 2C)."""

from __future__ import annotations

import html
import re
from collections.abc import Callable

import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.components.user_actions import (
        is_user_action_confirm_open,
        render_user_action_button_row,
        render_user_action_confirm_panel,
    )
    from app.components.headers import render_page_brand_header
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        render_table_header_cell,
    )
    from app.components.record_modal import (
        build_modal_cache,
        clear_edit_modes,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_missing_record,
        render_compact_modal_header,
        render_compact_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_view_mode,
        status_pill_html,
    )
    from app.components.tables import render_data_table
    from app.components.status import status_pill_html as legacy_status_pill_html
    from app.pages._core._data import (
        ACTIVE_EMPLOYEE_KEY,
        load_certifications,
        load_employee_documents,
        load_employees,
        lookup_options,
        persist_employee,
    )
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.config import settings
    from app.db import invite_auth_user, resend_invite_by_email
    from app.services.repository import clear_all_data_caches
    from app.services.users_service import can_manage_user_actions, get_user_delete_context
    from app.styles import inject_users_module_css
    from app.utils.constants import DEPARTMENTS, SESSION_NAV_KEY
    from app.utils.formatting import fmt_date
    from app.utils.permissions import can_view_hr_documents, normalize_role
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from components.user_actions import (  # type: ignore
        is_user_action_confirm_open,
        render_user_action_button_row,
        render_user_action_confirm_panel,
    )
    from components.headers import render_page_brand_header  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        render_table_header_cell,
    )
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_edit_modes,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_missing_record,
        render_compact_modal_header,
        render_compact_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_view_mode,
        status_pill_html,
    )
    from components.tables import render_data_table  # type: ignore
    from components.status import status_pill_html as legacy_status_pill_html  # type: ignore
    from pages._core._data import (  # type: ignore
        ACTIVE_EMPLOYEE_KEY,
        load_certifications,
        load_employee_documents,
        load_employees,
        lookup_options,
        persist_employee,
    )
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from config import settings  # type: ignore
    from db import invite_auth_user, resend_invite_by_email  # type: ignore
    from services.repository import clear_all_data_caches  # type: ignore
    from services.users_service import can_manage_user_actions, get_user_delete_context  # type: ignore
    from styles import inject_users_module_css  # type: ignore
    from utils.constants import DEPARTMENTS, SESSION_NAV_KEY  # type: ignore
    from utils.formatting import fmt_date  # type: ignore
    from utils.permissions import can_view_hr_documents, normalize_role  # type: ignore

_SEL = select_key("employees")
_TABLE_KEY = "employees_list"
MODULE = "employees"
MODAL_KEY = "ips_employees_detail_modal_id"
CACHE_KEY = "_ips_employees_modal_by_id"
SELECTED_USER_KEY = "selected_user_id"
SHOW_MODAL_KEY = "show_user_detail_modal"
_ALL_USER_IDS_KEY = "_ips_users_visible_ids"
_USER_COLS = [1, 1, 1, 1, 1, 1, 1]
_USER_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("", None),
    ("NAME", None),
    ("EMAIL", None),
    ("PHONE", None),
    ("ROLE", "role"),
    ("EMPLOYEE", "employee_type"),
    ("STATUS", "status"),
]
_EMPLOYEE_TABS = [
    "Overview",
    "Role & Permissions",
    "Departments",
    "Assigned Jobs",
    "Certifications",
    "Documents",
    "Time History",
    "Notes",
    "Activity Log",
]


def _normalize_user_status(raw: object) -> str:
    s = str(raw or "").strip().lower()
    if s in ("", "active", "enabled"):
        return "Active"
    if s in ("inactive", "disabled"):
        return "Inactive"
    if s in ("deleted", "archived"):
        return "Deleted"
    if s in ("locked", "blocked"):
        return "Locked"
    if s in ("pending", "invited"):
        return "Pending"
    label = str(raw or "").strip()
    return label if label else "Active"


def _user_display_name(user: dict) -> str:
    for key in ("full_name", "name", "username", "email"):
        val = str(user.get(key) or "").strip()
        if val:
            return val
    return "Unnamed User"


def _user_display_role(user: dict) -> str:
    role = str(user.get("role") or user.get("role_name") or "").strip()
    return role or "—"


def _user_display_email(user: dict) -> str:
    email = str(user.get("email") or "").strip()
    return email or "—"


def _user_phone_raw(user: dict) -> str:
    for key in ("phone", "phone_number", "mobile", "cell", "contact_phone"):
        val = str(user.get(key) or "").strip()
        if val and val not in {"—", "None", "-"}:
            return val
    return ""


def _format_phone(value: object) -> str:
    raw = str(value or "").strip()
    if not raw or raw in {"—", "None", "null", "-"}:
        return "—"
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return raw


def _user_display_employee_number(user: dict) -> str:
    num = str(user.get("employee_number") or "").strip()
    return num if num and num != "—" else "—"


def _user_display_phone(user: dict) -> str:
    return _format_phone(_user_phone_raw(user))


def _fmt_last_login(val: object) -> str:
    from datetime import datetime

    if val is None or str(val).strip() in ("", "—"):
        return "—"
    s = str(val).strip()
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        elif len(s) >= 16 and " " in s:
            dt = datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
        else:
            return fmt_date(val)
        return dt.strftime("%b %d, %Y %I:%M %p").replace(" 0", " ")
    except Exception:
        return s


def _employee_type_pill_html(user: dict) -> str:
    if user.get("is_employee") is False:
        cls = "ips-user-system"
        label = "System User"
    else:
        cls = "ips-user-employee"
        label = "Employee"
    return f'<span class="ips-user-pill {cls}">{html.escape(label)}</span>'


def _users_cell_html(value: str, css_class: str) -> str:
    text = str(value or "—").strip() or "—"
    safe = html.escape(text)
    title = html.escape(text, quote=True)
    return f'<div class="{css_class}" title="{title}">{safe}</div>'


def _user_status_pill_html(status: str) -> str:
    cls_map = {
        "Active": "ips-user-status-active",
        "Inactive": "ips-user-status-inactive",
        "Deleted": "ips-user-status-deleted",
        "Locked": "ips-user-status-locked",
        "Pending": "ips-user-status-pending",
    }
    cls = cls_map.get(status, "ips-user-status-active")
    return f'<span class="ips-user-pill {cls}">{html.escape(status)}</span>'


def _filter_employees(rows: list[dict]) -> list[dict]:
    return apply_column_filters(rows, _TABLE_KEY, _USER_COLUMN_FILTER_SPECS)


def _user_select_key(user_id: str) -> str:
    return f"user_select_{user_id}"


def _clear_user_selection(user_ids: list[str] | None = None) -> None:
    st.session_state[SELECTED_USER_KEY] = None
    st.session_state[SHOW_MODAL_KEY] = False
    ids = list(user_ids or [])
    for uid in ids:
        st.session_state[_user_select_key(uid)] = False
    for key in list(st.session_state.keys()):
        if isinstance(key, str) and key.startswith("user_select_"):
            st.session_state[key] = False


def _on_user_checkbox_change(user_id: str, all_user_ids: list[str]) -> None:
    key = _user_select_key(user_id)
    if st.session_state.get(key):
        for uid in all_user_ids:
            if uid != user_id:
                st.session_state[_user_select_key(uid)] = False
        st.session_state[SELECTED_USER_KEY] = user_id
        st.session_state[SHOW_MODAL_KEY] = True
        cache = st.session_state.get(CACHE_KEY) or {}
        user = cache.get(user_id) if isinstance(cache, dict) else None
        open_record_modal(
            user_id,
            user if isinstance(user, dict) else None,
            session_select_key=_SEL,
            modal_key=MODAL_KEY,
            module=MODULE,
            id_fields=("id", "email"),
        )
        if isinstance(user, dict) and user.get("id"):
            st.session_state[ACTIVE_EMPLOYEE_KEY] = str(user.get("id"))
    elif st.session_state.get(SELECTED_USER_KEY) == user_id:
        st.session_state[SELECTED_USER_KEY] = None
        st.session_state[SHOW_MODAL_KEY] = False


def _clear_employee_modal() -> None:
    user_ids = st.session_state.get(_ALL_USER_IDS_KEY) or []
    _clear_user_selection([str(uid) for uid in user_ids])
    clear_edit_modes(MODULE)
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=MODAL_KEY,
        module=MODULE,
    )


def _render_custom_users_table(
    filtered: list[dict],
    *,
    filter_options: dict[str, list[str]],
) -> list[str]:
    if not filtered:
        st.info("No users match your filters.")
        st.session_state[_ALL_USER_IDS_KEY] = []
        return []

    all_user_ids = [
        str(u.get("id") or "").strip() for u in filtered if str(u.get("id") or "").strip()
    ]
    st.session_state[_ALL_USER_IDS_KEY] = all_user_ids

    with st.container(key="users_table_wrap"):
        st.markdown('<div class="ips-users-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(_USER_COLS, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, _USER_HEADER_SPECS):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-users-header-row ips-users-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-users-header-row ips-users-cell",
                    )

        for user in filtered:
            uid = str(user.get("id") or "").strip()
            if not uid:
                continue

            name = _user_display_name(user)
            email = _user_display_email(user)
            phone = _user_display_phone(user)
            role = _user_display_role(user)
            status = _normalize_user_status(user.get("status"))

            cols = st.columns(_USER_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.checkbox(
                    "",
                    key=_user_select_key(uid),
                    label_visibility="collapsed",
                    on_change=_on_user_checkbox_change,
                    args=(uid, all_user_ids),
                )

            with cols[1]:
                st.markdown(_users_cell_html(name, "ips-users-name ips-users-ellipsis"), unsafe_allow_html=True)

            with cols[2]:
                st.markdown(
                    _users_cell_html(email, "ips-users-muted ips-users-cell ips-users-ellipsis"),
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(
                    _users_cell_html(phone, "ips-users-cell ips-users-phone ips-users-ellipsis"),
                    unsafe_allow_html=True,
                )

            with cols[4]:
                st.markdown(
                    _users_cell_html(role, "ips-users-cell ips-users-role ips-users-ellipsis"),
                    unsafe_allow_html=True,
                )

            with cols[5]:
                st.markdown(
                    f'<div class="ips-users-pill-col">{_employee_type_pill_html(user)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[6]:
                st.markdown(
                    f'<div class="ips-users-pill-col">{_user_status_pill_html(status)}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    return all_user_ids


def _cert_table(certs: list[dict]) -> None:
    if not certs:
        st.caption("No certifications on file.")
        return
    try:
        from app.pages.employee_certifications import render_certifications_table_block
        from app.styles import inject_certifications_module_css
    except ImportError:
        from pages.employee_certifications import render_certifications_table_block  # type: ignore
        from styles import inject_certifications_module_css  # type: ignore
    inject_certifications_module_css()
    render_certifications_table_block(
        certs,
        hide_employee=True,
        table_wrap_key="emp_certifications_table_wrap",
        session_prefix="emp_cert_",
        inline_detail=True,
    )


def _doc_table(docs: list[dict]) -> None:
    if not docs:
        st.caption("No documents on file.")
        return

    def _cell(field: str, row: dict) -> str:
        if field == "access":
            if row.get("is_restricted"):
                return '<span class="ips-restricted-tag">RESTRICTED</span>'
            return '<span style="color:#64748b;font-size:0.75rem;">Standard</span>'
        return html.escape(str(row.get(field) or "—"))

    render_data_table(
        docs,
        [
            ("doc_type", "TYPE"),
            ("upload_date", "UPLOADED"),
            ("uploaded_by", "BY"),
            ("expiration_date", "EXPIRES"),
            ("access", "ACCESS"),
        ],
        row_id_key="id",
        selected_id=None,
        session_select_key="_emp_doc_nested",
        col_fr=["1.1fr", "0.8fr", "0.9fr", "0.75fr", "0.65fr"],
        cell_renderer=_cell,
        hide_select=True,
    )


def _seed_employee_edit_form(emp: dict) -> None:
    rk = record_session_key(emp, "id")
    st.session_state[f"emp_edit_name_{rk}"] = str(emp.get("name") or "")
    st.session_state[f"emp_edit_email_{rk}"] = str(emp.get("email") or "")
    st.session_state[f"emp_edit_phone_{rk}"] = _user_phone_raw(emp)
    st.session_state[f"emp_edit_empnum_{rk}"] = str(emp.get("employee_number") or "")
    role_opts = lookup_options("user_roles")
    role = str(emp.get("role") or "")
    st.session_state[f"emp_edit_role_{rk}"] = role if role in role_opts else (role_opts[0] if role_opts else role)
    status = str(emp.get("status") or "Active")
    st.session_state[f"emp_edit_status_{rk}"] = status if status in ("Active", "Inactive") else "Active"
    st.session_state[f"emp_edit_is_employee_{rk}"] = bool(emp.get("is_employee", False))


def _render_employee_detail_tabs(emp: dict) -> None:
    eid = str(emp.get("id") or "")
    role_norm = normalize_role(current_role())
    name = safe_value(emp.get("name"))
    email = safe_value(emp.get("email"))
    role = safe_value(emp.get("role"))
    dept = safe_value(emp.get("department"))
    status = safe_value(emp.get("status"))

    (
        tab_overview,
        tab_role,
        tab_depts,
        tab_jobs,
        tab_certs,
        tab_docs,
        tab_time,
        tab_notes,
        tab_activity,
    ) = st.tabs(_EMPLOYEE_TABS)

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Full Name', name)}"
            f"{detail_field_html('Employee #', emp.get('employee_number'))}"
            f"{detail_field_html('Email', email)}"
            f"{detail_field_html('Phone', _format_phone(_user_phone_raw(emp)))}"
            f"{detail_field_html('Position', emp.get('position'))}"
            f"{detail_field_html('Trade', emp.get('trade'))}"
            f"{detail_field_html('Hire Date', fmt_date(emp.get('hire_date')))}"
            f"{detail_field_html('Username', emp.get('username'))}"
            f"{detail_field_html('Member Since', fmt_date(emp.get('member_since')))}"
            f'{detail_field_html("Status", status, html_value=status_pill_html(status))}'
            f"</div>"
        )
        st.markdown(dialog_card_html("User Information", overview_html), unsafe_allow_html=True)
        security_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Last Login', emp.get('last_login'))}"
            f"{detail_field_html('Two-Factor Auth', 'Enabled')}"
            f"{detail_field_html('Failed Attempts', '0')}"
            f"{detail_field_html('Account Locked', 'No')}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Security", security_html), unsafe_allow_html=True)

    with tab_role:
        role_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('System Role', role)}"
            f"{detail_field_html('Department', dept)}"
            f"</div>"
            f'<p style="margin:0.75rem 0 0;font-size:0.8125rem;color:#64748b;">'
            f"View Dashboard · Create &amp; Edit Jobs · Manage Inventory"
            f"</p>"
        )
        st.markdown(dialog_card_html("Role & Permissions", role_html), unsafe_allow_html=True)

    with tab_depts:
        dept_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Primary Department', dept)}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Departments", dept_html), unsafe_allow_html=True)
        st.caption(f"Available departments: {', '.join(DEPARTMENTS)}")

    with tab_jobs:
        placeholder_html("Assigned jobs will load from Supabase in a later phase.")

    with tab_certs:
        certs = load_certifications(eid)
        expired = [c for c in certs if str(c.get("status", "")).lower() == "expired"]
        expiring = [c for c in certs if str(c.get("status", "")).lower() == "expiring soon"]
        if expired or expiring:
            msg = []
            if expired:
                msg.append(f"{len(expired)} expired")
            if expiring:
                msg.append(f"{len(expiring)} expiring soon")
            st.markdown(
                f'<p class="ips-alert-banner">Certification alerts: {html.escape(", ".join(msg))}</p>',
                unsafe_allow_html=True,
            )
        _cert_table(certs)
        if st.button("Open Certifications Module", key=f"emp_open_certs_{eid}"):
            st.session_state[ACTIVE_EMPLOYEE_KEY] = eid
            st.session_state[SESSION_NAV_KEY] = "employee_certifications"
            st.rerun()

    with tab_docs:
        docs = load_employee_documents(eid, role=role_norm)
        if not can_view_hr_documents(role_norm):
            st.caption("Restricted HR documents are visible to administrators only.")
        _doc_table(docs)
        if st.button("Open Documents Module", key=f"emp_open_docs_{eid}"):
            st.session_state[ACTIVE_EMPLOYEE_KEY] = eid
            st.session_state[SESSION_NAV_KEY] = "employee_documents"
            st.rerun()

    with tab_time:
        placeholder_html("Time history will load from Supabase in a later phase.")

    with tab_notes:
        notes_text = safe_value(emp.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Activity log will load from Supabase in a later phase.")


def _render_employee_edit_form(emp: dict) -> None:
    rk = record_session_key(emp, "id")
    eid = str(emp.get("id") or "")
    if f"emp_edit_name_{rk}" not in st.session_state:
        _seed_employee_edit_form(emp)

    render_edit_form_header("Edit User")
    if is_demo_id(eid):
        st.caption("Demo records cannot be saved to the database.")

    ec1, ec2 = st.columns(2, gap="medium")
    with ec1:
        st.text_input("Name", key=f"emp_edit_name_{rk}")
        st.text_input("Employee #", key=f"emp_edit_empnum_{rk}")
        st.text_input("Email", key=f"emp_edit_email_{rk}")
        st.text_input("Phone", key=f"emp_edit_phone_{rk}", placeholder="(337) 555-0100")
    with ec2:
        st.selectbox("Role", lookup_options("user_roles"), key=f"emp_edit_role_{rk}")
        st.selectbox("Status", ["Active", "Inactive"], key=f"emp_edit_status_{rk}")
        st.checkbox("This user is an employee", key=f"emp_edit_is_employee_{rk}")

    cancelled, saved = render_save_cancel_actions(
        module=MODULE,
        record_key=rk,
        cancel_key=f"emp_modal_save_cancel_{rk}",
        save_key=f"emp_modal_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved and not is_demo_id(eid):
        ok, msg = persist_employee(
            {
                "name": st.session_state.get(f"emp_edit_name_{rk}"),
                "employee_number": st.session_state.get(f"emp_edit_empnum_{rk}"),
                "email": st.session_state.get(f"emp_edit_email_{rk}"),
                "phone": st.session_state.get(f"emp_edit_phone_{rk}"),
                "role": st.session_state.get(f"emp_edit_role_{rk}"),
                "status": st.session_state.get(f"emp_edit_status_{rk}"),
                "is_employee": bool(st.session_state.get(f"emp_edit_is_employee_{rk}")),
            },
            row_id=eid or None,
        )
        if ok:
            set_view_mode(MODULE, rk)
            st.success(msg or "Employee saved.")
            st.rerun()
        st.error(msg or "Could not save employee.")


def _norm_invite_email(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _email_domain_allowed(email: str) -> bool:
    em = _norm_invite_email(email)
    if not em or "@" not in em:
        return False
    dom = em.split("@", 1)[1]
    allow = str(
        getattr(settings, "allowed_email_domain", "")
        or getattr(settings, "company_email_domain", "")
        or ""
    ).strip().lower()
    if not allow:
        return True
    return dom == allow


def _invite_role_from_employee(emp: dict) -> str:
    role_norm = normalize_role(str(emp.get("role") or "employee"))
    if role_norm in {"pm", "estimator", "project manager", "supervisor"}:
        return "manager"
    if role_norm in {"admin", "viewer", "employee", "manager"}:
        return role_norm
    return "employee"


def _employee_invite_email(emp: dict) -> str:
    ctx = get_user_delete_context(str(emp.get("id") or ""))
    email = _norm_invite_email(ctx.get("email") or emp.get("email"))
    if email in {"", "—", "none"}:
        return ""
    return email


def _send_employee_invite(emp: dict) -> str:
    eid = str(emp.get("id") or "").strip()
    email = _employee_invite_email(emp)
    if not email or "@" not in email:
        raise RuntimeError("Add a valid work email before sending an invite.")
    if "indfustrial" in email:
        raise RuntimeError("Check spelling of company domain (found 'indfustrial').")
    if not _email_domain_allowed(email):
        raise RuntimeError("Email domain is not allowed for app login.")

    ctx = get_user_delete_context(eid)
    if ctx.get("has_login"):
        raise RuntimeError("This user already has a login. Use Resend invite instead.")

    invite_auth_user(
        email=email,
        role=_invite_role_from_employee(emp),
        employee_id=eid or None,
        require_employee_link=False,
    )
    clear_all_data_caches()
    return email


def _resend_employee_invite(emp: dict) -> str:
    email = _employee_invite_email(emp)
    if not email or "@" not in email:
        raise RuntimeError("No email on file for this user.")
    resend_invite_by_email(email=email)
    return email


def _render_user_login_invite_panel(emp: dict, rk: str) -> None:
    """Send or resend Supabase magic-link invites from the user detail modal."""
    if not can_manage_user_actions():
        return
    eid = str(emp.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return

    ctx = get_user_delete_context(eid)
    email = _employee_invite_email(emp)
    has_login = bool(ctx.get("has_login"))

    st.markdown(
        '<p class="ips-user-actions-title">App Login</p>',
        unsafe_allow_html=True,
    )
    if not email or "@" not in email:
        st.caption("Add a valid work email on this user, then send an invite.")
        return

    if has_login:
        st.caption(f"Login linked · {email} · resend sends a password setup link")
        if st.button(
            "Resend invite",
            key=f"emp_resend_invite_{rk}",
            use_container_width=True,
        ):
            try:
                sent_to = _resend_employee_invite(emp)
                st.session_state["users_action_flash"] = ("success", f"Invite resent to {sent_to}.")
                st.rerun()
            except Exception as exc:
                st.error("Could not resend invite.")
                with st.expander("Technical details"):
                    st.code(repr(exc), language="text")
        return

    st.caption(f"No login yet · invite will go to {email}")
    if st.button(
        "Send invite",
        type="primary",
        key=f"emp_send_invite_{rk}",
        use_container_width=True,
    ):
        try:
            sent_to = _send_employee_invite(emp)
            st.session_state["users_action_flash"] = ("success", f"Invite sent to {sent_to}.")
            st.rerun()
        except Exception as exc:
            st.error("Could not send invite.")
            with st.expander("Technical details"):
                st.code(repr(exc), language="text")


def _user_action_callbacks() -> tuple[Callable[[], None], Callable[[], None]]:
    def _after_deactivate_or_delete() -> None:
        _clear_employee_modal()

    return _after_deactivate_or_delete, _after_deactivate_or_delete


def _render_user_header_actions(emp: dict, header_cols: list | None = None) -> None:
    if is_user_action_confirm_open(emp):
        return
    on_deactivate, on_delete = _user_action_callbacks()
    render_user_action_button_row(
        emp,
        layout="header",
        header_cols=header_cols,
        on_deactivate=on_deactivate,
        on_delete=on_delete,
    )


def _render_user_actions_panel(emp: dict, rk: str) -> None:
    """Confirm panel for activate/deactivate/delete when triggered from the header."""
    if is_edit_mode(MODULE, rk):
        return
    eid = str(emp.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return

    on_deactivate, on_delete = _user_action_callbacks()
    render_user_action_confirm_panel(
        emp,
        on_deactivate=on_deactivate,
        on_delete=on_delete,
    )


def _employee_type_label(emp: dict) -> str:
    return "Employee" if emp.get("is_employee") is not False else "System User"


_USER_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("role", _user_display_role),
    ("employee_type", _employee_type_label),
    ("status", lambda u: _normalize_user_status(u.get("status"))),
]


def render_employee_detail_dialog(emp: dict) -> None:
    rk = record_session_key(emp, "id", "email")
    name = safe_value(emp.get("name"))
    email = safe_value(emp.get("email"))
    role = safe_value(emp.get("role"))
    status = safe_value(emp.get("status"))
    subtitle = f"{role} · {email}" if role != "—" and email != "—" else (role if role != "—" else email)

    render_modal_shell(compact=True)
    if not is_edit_mode(MODULE, rk):
        eid = str(emp.get("id") or "").strip()
        show_header_actions = bool(eid) and not is_demo_id(eid)
        render_compact_modal_header(
            title=name,
            subtitle=subtitle,
            status=status,
            module=MODULE,
            record_key=rk,
            key_prefix=f"emp_modal_{rk}",
            extra_actions=(lambda cols: _render_user_header_actions(emp, header_cols=cols))
            if show_header_actions
            else None,
        )
        render_compact_modal_meta_grid(
            [
                ("Employee #", _user_display_employee_number(emp)),
                ("Role", role),
                ("Email", email),
                ("Phone", _user_display_phone(emp)),
                ("Employee", _employee_type_label(emp)),
                ("Status", status),
            ]
        )
        _render_user_login_invite_panel(emp, rk)
        _render_user_actions_panel(emp, rk)

    if is_edit_mode(MODULE, rk):
        _render_employee_edit_form(emp)
    else:
        _render_employee_detail_tabs(emp)


@st.dialog("User Details", width="large", on_dismiss=_clear_employee_modal)
def _show_employee_modal() -> None:
    emp = get_modal_record(
        cache_key=CACHE_KEY,
        modal_key=MODAL_KEY,
        session_select_key=_SEL,
    )
    if not emp:
        render_missing_record(_clear_employee_modal, close_key="emp_modal_missing_close")
        return
    render_employee_detail_dialog(emp)


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("employees"):
        return
    inject_users_module_css()
    st.markdown('<span class="ips-users-page ips-page-shell-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
    flash = st.session_state.pop("users_action_flash", None)
    if flash:
        kind, message = flash
        if kind == "warning":
            st.warning(message)
        else:
            st.success(message)
    if not st.session_state.get("_ips_core_employees_seeded"):
        try:
            from app.services.employee_seed_service import ensure_core_employee_seed
        except ImportError:
            from services.employee_seed_service import ensure_core_employee_seed  # type: ignore
        ensure_core_employee_seed()
        st.session_state["_ips_core_employees_seeded"] = True
    all_emp = load_employees()
    filter_options = build_filter_options(all_emp, _USER_COLUMN_FILTER_SPECS)

    def _users_export() -> None:
        st.button("Export", key="users_export", use_container_width=True)

    def _users_new() -> None:
        if st.button("+ New User", key="emp_add", type="primary", use_container_width=True):
            st.session_state["ips_emp_form"] = True

    render_page_brand_header(
        "Users",
        "Manage system users, roles, and permissions.",
        actions=[_users_export, _users_new],
    )

    if st.session_state.get("ips_emp_form"):
        with st.expander("New User", expanded=True):
            nc1, nc2 = st.columns(2)
            with nc1:
                st.text_input("Name", key="emp_new_name")
                st.text_input("Email", key="emp_new_email")
            with nc2:
                st.text_input(
                    "Phone",
                    key="emp_new_phone",
                    placeholder="(337) 555-0100",
                    help="Mobile or office number for this user.",
                )
                st.selectbox("Role", lookup_options("user_roles"), key="emp_new_role")
            if can_manage_user_actions():
                st.checkbox(
                    "Send invite email after save",
                    value=True,
                    key="emp_new_send_invite",
                    help="Emails a magic link so they can set a password and log in.",
                )
            if st.button("Save User", key="emp_save_new", type="primary"):
                new_email = str(st.session_state.get("emp_new_email") or "").strip()
                ok, msg = persist_employee(
                    {
                        "name": st.session_state.get("emp_new_name"),
                        "email": new_email,
                        "phone": st.session_state.get("emp_new_phone"),
                        "role": st.session_state.get("emp_new_role"),
                        "status": "Active",
                    }
                )
                if not ok:
                    st.error(msg or "Could not save employee.")
                else:
                    st.session_state.pop("ips_emp_form", None)
                    flash_kind = "success"
                    flash_msg = msg or "Employee saved."
                    if can_manage_user_actions() and st.session_state.get("emp_new_send_invite"):
                        fresh = next(
                            (
                                e
                                for e in load_employees()
                                if _norm_invite_email(e.get("email")) == _norm_invite_email(new_email)
                            ),
                            None,
                        )
                        if fresh:
                            try:
                                sent_to = _send_employee_invite(fresh)
                                flash_msg = f"Employee saved. Invite sent to {sent_to}."
                            except Exception as exc:
                                flash_kind = "warning"
                                flash_msg = f"Employee saved. Invite failed: {exc}"
                        elif new_email:
                            flash_kind = "warning"
                            flash_msg = "Employee saved, but could not send invite."
                    st.session_state["users_action_flash"] = (flash_kind, flash_msg)
                    st.rerun()

    filtered = _filter_employees(all_emp)

    st.caption(f"{len(filtered)} user(s)")

    modal_cache = build_modal_cache(filtered, cache_key=CACHE_KEY)
    selected_user_id = str(st.session_state.get(SELECTED_USER_KEY) or "").strip()
    if selected_user_id and st.session_state.get(SHOW_MODAL_KEY):
        for emp in all_emp:
            if str(emp.get("id") or "").strip() == selected_user_id:
                modal_cache[selected_user_id] = emp
                st.session_state[CACHE_KEY] = modal_cache
                break

    _render_custom_users_table(filtered, filter_options=filter_options)

    if selected_user_id and st.session_state.get(SHOW_MODAL_KEY):
        _show_employee_modal()
