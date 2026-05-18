"""Employee Documents module (Phase 2C)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_role
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.tables import render_data_table
    from app.pages.modules._data import ACTIVE_EMPLOYEE_KEY, get_employee, load_employee_documents, load_employees
    from app.styles import inject_global_css
    from app.utils.constants import DOCUMENT_TYPES
    from app.utils.formatting import fmt_date
    from app.utils.permissions import can_view_hr_documents, normalize_role
except ImportError:
    from auth import current_role  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from pages.modules._data import ACTIVE_EMPLOYEE_KEY, get_employee, load_employee_documents, load_employees  # type: ignore
    from styles import inject_global_css  # type: ignore
    from utils.constants import DOCUMENT_TYPES  # type: ignore
    from utils.formatting import fmt_date  # type: ignore
    from utils.permissions import can_view_hr_documents, normalize_role  # type: ignore


def _filter_docs(rows: list[dict], *, q: str, doc_type: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [d for d in out if ql in str(d.get("doc_type", "")).lower() or ql in str(d.get("file_name", "")).lower()]
    if doc_type and doc_type != "All Types":
        out = [d for d in out if str(d.get("doc_type", "")) == doc_type]
    return out


def render() -> None:
    inject_global_css()
    role_norm = normalize_role(current_role())
    hr_ok = can_view_hr_documents(role_norm)
    employees = load_employees()
    emp_opts = {str(e.get("name") or ""): str(e.get("id") or "") for e in employees}
    names = list(emp_opts.keys())
    active_id = str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or "")
    default_name = next((n for n, eid in emp_opts.items() if eid == active_id), names[0] if names else "")

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Employee Documents", "Store licenses, training records, and HR files.")
    with act_r:
        if st.button("+ Upload Document", key="doc_upload", type="primary", use_container_width=True):
            st.session_state["ips_doc_form_open"] = True

    if not hr_ok:
        st.markdown(
            '<p class="ips-alert-banner">Restricted HR documents are hidden. Administrators can view all files.</p>',
            unsafe_allow_html=True,
        )

    def _filters() -> None:
        c1, c2, c3 = st.columns([1.4, 1.2, 1])
        with c1:
            idx = names.index(default_name) if default_name in names else 0
            picked = st.selectbox("Employee", names, index=idx, key="doc_emp_filter", label_visibility="collapsed")
            st.session_state[ACTIVE_EMPLOYEE_KEY] = emp_opts.get(picked, "")
        with c2:
            st.selectbox("Document type", ["All Types", *DOCUMENT_TYPES], key="doc_type_filter", label_visibility="collapsed")
        with c3:
            st.text_input("Search", placeholder="Search files…", key="doc_search", label_visibility="collapsed")

    layout_filter_bar(_filters)

    eid = str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or "")
    docs = load_employee_documents(eid, role=role_norm) if eid else []
    if not eid:
        for e in employees[:3]:
            docs.extend(load_employee_documents(str(e.get("id")), role=role_norm))

    filtered = _filter_docs(
        docs,
        q=str(st.session_state.get("doc_search") or ""),
        doc_type=str(st.session_state.get("doc_type_filter") or "All Types"),
    )

    if st.session_state.get("ips_doc_form_open"):
        with st.expander("Upload document", expanded=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                st.selectbox("Document type", DOCUMENT_TYPES, key="doc_new_type")
                st.file_uploader("Attachment", key="doc_new_file")
            with fc2:
                st.date_input("Expiration date (optional)", key="doc_new_exp", value=None)
                st.checkbox("Restricted / private (HR only)", key="doc_new_restricted", disabled=not hr_ok)
            if st.button("Save upload", key="doc_save_new", type="primary"):
                st.success("Document uploaded (demo).")
                st.session_state["ips_doc_form_open"] = False
                st.rerun()

    def _cell(field: str, row: dict) -> str:
        if field == "access":
            if row.get("is_restricted"):
                return '<span class="ips-restricted-tag">RESTRICTED</span>'
            return '<span style="color:#64748b;font-size:0.75rem;">Standard</span>'
        if field in ("upload_date", "expiration_date"):
            return html.escape(fmt_date(row.get(field)))
        return html.escape(str(row.get(field) or "—"))

    render_data_table(
        filtered,
        [
            ("doc_type", "DOCUMENT TYPE"),
            ("file_name", "FILE"),
            ("upload_date", "UPLOADED"),
            ("uploaded_by", "UPLOADED BY"),
            ("expiration_date", "EXPIRES"),
            ("access", "ACCESS"),
        ],
        row_id_key="id",
        selected_id=None,
        session_select_key="_doc_list",
        col_fr=["1.1fr", "1.2fr", "0.85fr", "0.9fr", "0.8fr", "0.7fr"],
        cell_renderer=_cell,
        hide_select=True,
    )

    emp = get_employee(eid) if eid else None
    if emp:
        st.caption(f"Documents for **{emp.get('name')}** · {len(filtered)} file(s)")
