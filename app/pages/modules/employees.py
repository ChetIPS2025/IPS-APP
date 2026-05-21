"""Employees / Users module (Phase 2C)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_role
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.layout import render_tab_placeholder
    from app.components.modals import render_record_detail_dialog
    from app.components.status import status_pill_html
    from app.components.tables import render_clickable_table, render_data_table
    from app.components.tabs import render_tabs
    from app.pages.modules._data import (
        ACTIVE_EMPLOYEE_KEY,
        get_employee,
        load_certifications,
        load_employee_documents,
        load_employees,
        lookup_options,
        persist_employee,
    )
    from app.pages.modules._crud import apply_persist_feedback, is_demo_id
    from app.pages.modules._session import select_key, tab_key
    from app.styles import inject_global_css
    from app.utils.constants import DEPARTMENTS, ROLES, SESSION_NAV_KEY
    from app.utils.formatting import fmt_date
    from app.utils.permissions import can_view_hr_documents, normalize_role
except ImportError:
    from auth import current_role  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.layout import render_tab_placeholder  # type: ignore
    from components.modals import render_record_detail_dialog  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_clickable_table, render_data_table  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from pages.modules._data import (  # type: ignore
        ACTIVE_EMPLOYEE_KEY,
        get_employee,
        load_certifications,
        load_employee_documents,
        load_employees,
        lookup_options,
        persist_employee,
    )
    from pages.modules._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages.modules._session import select_key, tab_key  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.constants import DEPARTMENTS, ROLES, SESSION_NAV_KEY  # type: ignore
    from utils.formatting import fmt_date  # type: ignore
    from utils.permissions import can_view_hr_documents, normalize_role  # type: ignore

_SEL = select_key("employees")
_TAB = tab_key("employees")

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


def _filter_employees(rows: list[dict], *, q: str, dept: str, status: str, role: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            e
            for e in out
            if ql in str(e.get("name", "")).lower()
            or ql in str(e.get("email", "")).lower()
            or ql in str(e.get("username", "")).lower()
        ]
    if dept and dept != "All Departments":
        out = [e for e in out if str(e.get("department", "")) == dept]
    if status and status != "All Statuses":
        out = [e for e in out if str(e.get("status", "")) == status]
    if role and role != "All Roles":
        out = [e for e in out if str(e.get("role", "")) == role]
    return out


def _cert_table(certs: list[dict]) -> None:
    if not certs:
        st.caption("No certifications on file.")
        return

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
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


def _render_detail(emp: dict) -> None:
    eid = str(emp.get("id") or "")
    title = str(emp.get("name") or "Employee")
    role_norm = normalize_role(current_role())

    def _tabs() -> None:
        render_tabs(_EMPLOYEE_TABS, session_key=_TAB, default="Overview")

    def _body() -> None:
        tab = str(st.session_state.get(_TAB) or "Overview")
        ot = "d" + "iv"
        st.markdown(
            f'<{ot} class="ips-detail-meta-row">'
            f"<span>Status<br>{status_pill_html(str(emp.get('status') or ''))}</span>"
            f"<span>Role<br><strong>{html.escape(str(emp.get('role') or '—'))}</strong></span>"
            f"<span>Department<br><strong>{html.escape(str(emp.get('department') or '—'))}</strong></span>"
            f"</{ot}>",
            unsafe_allow_html=True,
        )

        if tab == "Overview":
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Contact**")
                st.markdown(
                    f'<dl class="ips-info-grid">'
                    f"<dt>Email</dt><dd>{html.escape(str(emp.get('email') or '—'))}</dd>"
                    f"<dt>Phone</dt><dd>{html.escape(str(emp.get('phone') or '—'))}</dd>"
                    f"<dt>Username</dt><dd>{html.escape(str(emp.get('username') or '—'))}</dd>"
                    f"</dl>",
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown("**Account**")
                st.markdown(
                    f'<dl class="ips-info-grid">'
                    f"<dt>Last Login</dt><dd>{html.escape(str(emp.get('last_login') or '—'))}</dd>"
                    f"<dt>Member Since</dt><dd>{html.escape(fmt_date(emp.get('member_since')))}</dd>"
                    f"</dl>",
                    unsafe_allow_html=True,
                )
            if not is_demo_id(eid):
                with st.expander("Edit employee", expanded=False):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        st.text_input("Name", value=str(emp.get("name") or ""), key=f"emp_edit_name_{eid}")
                        st.text_input("Email", value=str(emp.get("email") or ""), key=f"emp_edit_email_{eid}")
                        st.selectbox("Department", lookup_options("departments"), key=f"emp_edit_dept_{eid}")
                    with ec2:
                        st.selectbox("Role", lookup_options("user_roles"), key=f"emp_edit_role_{eid}")
                        st.selectbox("Status", ["Active", "Inactive"], key=f"emp_edit_status_{eid}")
                    if st.button("Save employee", key=f"emp_save_{eid}", type="primary"):
                        ok, msg = persist_employee(
                            {
                                "name": st.session_state.get(f"emp_edit_name_{eid}"),
                                "email": st.session_state.get(f"emp_edit_email_{eid}"),
                                "department": st.session_state.get(f"emp_edit_dept_{eid}"),
                                "role": st.session_state.get(f"emp_edit_role_{eid}"),
                                "status": st.session_state.get(f"emp_edit_status_{eid}"),
                            },
                            row_id=eid,
                        )
                        if apply_persist_feedback(ok, msg):
                            st.rerun()
            return

        if tab == "Role & Permissions":
            c1, c2 = st.columns(2)
            with c1:
                role_opts = list(ROLES)
                cur_role = str(emp.get("role") or "Employee")
                role_idx = next(
                    (i for i, r in enumerate(role_opts) if r.lower() in cur_role.lower() or cur_role.lower() in r.lower()),
                    0,
                )
                st.selectbox("System Role", role_opts, index=role_idx, key=f"emp_role_{eid}")
            with c2:
                st.multiselect("Page Access", ["Dashboard", "Jobs", "Timekeeping", "Reports"], default=["Dashboard", "Jobs"], key=f"emp_pages_{eid}")
            st.caption("Permission changes save to Supabase when connected.")
            return

        if tab == "Departments":
            st.multiselect("Assigned Departments", list(DEPARTMENTS), default=[str(emp.get("department") or DEPARTMENTS[0])], key=f"emp_depts_{eid}")
            return

        if tab == "Certifications":
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
                    f'<p class="ips-alert-banner">⚠ Certification alerts: {html.escape(", ".join(msg))}</p>',
                    unsafe_allow_html=True,
                )
            _cert_table(certs)
            if st.button("Open Certifications Module", key=f"emp_open_certs_{eid}"):
                st.session_state[ACTIVE_EMPLOYEE_KEY] = eid
                st.session_state[SESSION_NAV_KEY] = "employee_certifications"
                st.rerun()
            return

        if tab == "Documents":
            docs = load_employee_documents(eid, role=role_norm)
            if not can_view_hr_documents(role_norm):
                st.caption("Restricted HR documents are visible to administrators only.")
            _doc_table(docs)
            if st.button("Open Documents Module", key=f"emp_open_docs_{eid}"):
                st.session_state[ACTIVE_EMPLOYEE_KEY] = eid
                st.session_state[SESSION_NAV_KEY] = "employee_documents"
                st.rerun()
            return

        if tab in ("Activity Log", "Assigned Jobs", "Time History", "Notes"):
            render_tab_placeholder(f"{tab} will load from Supabase in a later phase.")
            return

        render_tab_placeholder(f"{tab} content will connect to Supabase in a later phase.")

    render_record_detail_dialog(
        f"{title} — Employee Details",
        module_name="employees",
        session_select_key=_SEL,
        tabs_fn=_tabs,
        body_fn=_body,
    )


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
    if not begin_module("employees"):
        return
    all_emp = load_employees()
    departments = sorted({str(e.get("department") or "") for e in all_emp if e.get("department")})
    roles = sorted({str(e.get("role") or "") for e in all_emp if e.get("role")})

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Employees", "Manage users, roles, certifications, and HR documents.")
    with act_r:
        if st.button("+ Add User", key="emp_add", type="primary", use_container_width=True):
            st.session_state["ips_emp_form"] = True

    if st.session_state.get("ips_emp_form"):
        with st.expander("New employee", expanded=True):
            st.text_input("Name", key="emp_new_name")
            st.text_input("Email", key="emp_new_email")
            st.selectbox("Department", lookup_options("departments"), key="emp_new_dept")
            st.selectbox("Role", lookup_options("user_roles"), key="emp_new_role")
            if st.button("Save employee", key="emp_save_new", type="primary"):
                ok, msg = persist_employee(
                    {
                        "name": st.session_state.get("emp_new_name"),
                        "email": st.session_state.get("emp_new_email"),
                        "department": st.session_state.get("emp_new_dept"),
                        "role": st.session_state.get("emp_new_role"),
                        "status": "Active",
                    }
                )
                if apply_persist_feedback(ok, msg, clear_keys=("ips_emp_form",)):
                    st.rerun()

    def _filters() -> None:
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            st.text_input("Search", placeholder="Search name, email, username…", key="emp_search", label_visibility="collapsed")
        with c2:
            st.selectbox("Department", ["All Departments", *departments], key="emp_dept", label_visibility="collapsed")
        with c3:
            st.selectbox("Status", ["All Statuses", "Active", "Inactive"], key="emp_status", label_visibility="collapsed")
        with c4:
            st.selectbox("Role", ["All Roles", *roles], key="emp_role_filter", label_visibility="collapsed")

    layout_filter_bar(_filters)

    filtered = _filter_employees(
        all_emp,
        q=str(st.session_state.get("emp_search") or ""),
        dept=str(st.session_state.get("emp_dept") or "All Departments"),
        status=str(st.session_state.get("emp_status") or "All Statuses"),
        role=str(st.session_state.get("emp_role_filter") or "All Roles"),
    )

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(e.get("id")) == selected_id for e in filtered):
        st.session_state.pop(_SEL, None)
        selected_id = ""

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        return html.escape(str(row.get(field) or "—"))

    def _plain_cell(field: str, row: dict) -> str:
        return str(row.get(field) or "—")

    sel = render_clickable_table(
        filtered,
        [
            ("name", "NAME"),
            ("email", "EMAIL"),
            ("role", "ROLE"),
            ("department", "DEPARTMENT"),
            ("status", "STATUS"),
            ("last_login", "LAST LOGIN"),
        ],
        "employees_list",
        row_id_key="id",
        session_select_key=_SEL,
        selected_id=selected_id or None,
        plain_cell=_plain_cell,
        html_cell=_cell,
    )

    if sel:
        emp = get_employee(sel) or next((e for e in filtered if str(e.get("id")) == sel), None)
        if emp:
            st.session_state[ACTIVE_EMPLOYEE_KEY] = str(emp.get("id"))
            _render_detail(emp)
