"""Employees / Users module (Phase 2C)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_role
    from app.components.clickable_table import render_clickable_table
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.record_modal import (
        build_modal_cache,
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
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_view_mode,
        show_modal_if_pending,
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
    from app.styles import inject_users_module_css
    from app.utils.constants import DEPARTMENTS, SESSION_NAV_KEY
    from app.utils.formatting import fmt_date
    from app.utils.permissions import can_view_hr_documents, normalize_role
except ImportError:
    from auth import current_role  # type: ignore
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.record_modal import (  # type: ignore
        build_modal_cache,
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
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        safe_value,
        set_view_mode,
        show_modal_if_pending,
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
    from styles import inject_users_module_css  # type: ignore
    from utils.constants import DEPARTMENTS, SESSION_NAV_KEY  # type: ignore
    from utils.formatting import fmt_date  # type: ignore
    from utils.permissions import can_view_hr_documents, normalize_role  # type: ignore

_SEL = select_key("employees")
_TABLE_KEY = "employees_list"
MODULE = "employees"
MODAL_KEY = "ips_employees_detail_modal_id"
CACHE_KEY = "_ips_employees_modal_by_id"

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


def _filter_employees(rows: list[dict], *, q: str, status: str, role: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            e
            for e in out
            if ql in str(e.get("name", "")).lower()
            or ql in str(e.get("email", "")).lower()
            or ql in str(e.get("username", "")).lower()
            or ql in str(e.get("phone", "")).lower()
        ]
    if status and status != "All Statuses":
        out = [e for e in out if str(e.get("status", "")) == status]
    if role and role != "All Roles":
        out = [e for e in out if str(e.get("role", "")) == role]
    return out


def _clear_employee_modal() -> None:
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=MODAL_KEY,
        module=MODULE,
    )


def _open_employee_modal(employee_id: str, employee: dict | None = None) -> None:
    open_record_modal(
        employee_id,
        employee,
        session_select_key=_SEL,
        modal_key=MODAL_KEY,
        module=MODULE,
        id_fields=("id", "email"),
    )
    if isinstance(employee, dict) and employee.get("id"):
        st.session_state[ACTIVE_EMPLOYEE_KEY] = str(employee.get("id"))


def _employees_display_cell(field: str, row: dict) -> str:
    if field == "last_login":
        return safe_value(row.get(field))
    if field == "is_employee":
        return "Employee" if row.get("is_employee") is not False else "System User"
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def _cert_table(certs: list[dict]) -> None:
    if not certs:
        st.caption("No certifications on file.")
        return

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return legacy_status_pill_html(str(row.get("status") or ""))
        return html.escape(str(row.get(field) or "—"))

    render_data_table(
        certs,
        [
            ("cert_type", "TYPE"),
            ("cert_number", "NUMBER"),
            ("issuer", "ISSUER"),
            ("issue_date", "ISSUED"),
            ("expiration_date", "EXPIRES"),
            ("status", "STATUS"),
        ],
        row_id_key="id",
        selected_id=None,
        session_select_key="_emp_cert_nested",
        col_fr=["1fr", "0.9fr", "1fr", "0.75fr", "0.75fr", "0.7fr"],
        cell_renderer=_cell,
        hide_select=True,
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
    st.session_state[f"emp_edit_phone_{rk}"] = str(emp.get("phone") or "").replace("—", "")
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
            f"{detail_field_html('Email', email)}"
            f"{detail_field_html('Phone', emp.get('phone'))}"
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


def render_employee_detail_dialog(emp: dict) -> None:
    rk = record_session_key(emp, "id", "email")
    name = safe_value(emp.get("name"))
    email = safe_value(emp.get("email"))
    role = safe_value(emp.get("role"))
    dept = safe_value(emp.get("department"))
    status = safe_value(emp.get("status"))

    render_modal_shell()
    render_modal_header(
        title=name,
        subtitle=f"{role} · {dept}" if role != "—" or dept != "—" else email,
        status=status,
    )
    render_modal_edit_button(
        module=MODULE,
        record_key=rk,
        key_prefix=f"emp_modal_{rk}",
    )
    render_modal_meta_grid(
        [
            ("Role", role),
            ("Department", dept),
            ("Email", email),
            ("Last Login", emp.get("last_login")),
        ]
    )

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
    all_emp = load_employees()
    roles = sorted({str(e.get("role") or "") for e in all_emp if e.get("role")})

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Users", "Manage system users, roles, and permissions.")
    with act_r:
        st.button("Export", key="users_export", use_container_width=True)
        if st.button("+ New User", key="emp_add", type="primary", use_container_width=True):
            st.session_state["ips_emp_form"] = True

    if st.session_state.get("ips_emp_form"):
        with st.expander("New employee", expanded=True):
            nc1, nc2 = st.columns(2)
            with nc1:
                st.text_input("Name", key="emp_new_name")
                st.text_input("Email", key="emp_new_email")
            with nc2:
                st.text_input(
                    "Phone",
                    key="emp_new_phone",
                    placeholder="(337) 555-0100",
                    help="Mobile or office number for this employee.",
                )
                st.selectbox("Department", lookup_options("departments"), key="emp_new_dept")
            st.selectbox("Role", lookup_options("user_roles"), key="emp_new_role")
            if st.button("Save employee", key="emp_save_new", type="primary"):
                ok, msg = persist_employee(
                    {
                        "name": st.session_state.get("emp_new_name"),
                        "email": st.session_state.get("emp_new_email"),
                        "phone": st.session_state.get("emp_new_phone"),
                        "department": st.session_state.get("emp_new_dept"),
                        "role": st.session_state.get("emp_new_role"),
                        "status": "Active",
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_emp_form",)):
                    st.rerun()

    def _filters() -> None:
        c1, c2, c3 = st.columns([2, 1, 1])
        with c1:
            st.text_input("Search", placeholder="Search name, email, username…", key="emp_search", label_visibility="collapsed")
        with c2:
            st.selectbox("Status", ["All Statuses", "Active", "Inactive"], key="emp_status", label_visibility="collapsed")
        with c3:
            st.selectbox("Role", ["All Roles", *roles], key="emp_role_filter", label_visibility="collapsed")

    layout_filter_bar(_filters)

    filtered = _filter_employees(
        all_emp,
        q=str(st.session_state.get("emp_search") or ""),
        status=str(st.session_state.get("emp_status") or "All Statuses"),
        role=str(st.session_state.get("emp_role_filter") or "All Roles"),
    )

    st.caption(f"{len(filtered)} user(s)")

    build_modal_cache(filtered, cache_key=CACHE_KEY)

    render_clickable_table(
        filtered,
        [
            ("name", "NAME"),
            ("email", "EMAIL"),
            ("role", "ROLE"),
            ("is_employee", "EMPLOYEE"),
            ("status", "STATUS"),
            ("last_login", "LAST LOGIN"),
        ],
        _TABLE_KEY,
        row_id_key="id",
        session_select_key=_SEL,
        format_cell=_employees_display_cell,
        column_widths={
            "name": "medium",
            "email": "large",
            "role": "small",
            "is_employee": "small",
            "status": "small",
            "last_login": "small",
        },
        on_row_selected=_open_employee_modal,
    )

    show_modal_if_pending(MODAL_KEY, _show_employee_modal)
