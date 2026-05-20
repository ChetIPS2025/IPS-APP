"""Employee Certifications module (Phase 2C)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.status import status_pill_html
    from app.components.tables import render_data_table
    from app.pages.modules._data import (
        ACTIVE_EMPLOYEE_KEY,
        certification_alerts,
        get_employee,
        load_all_certifications,
        load_certifications,
        load_employees,
    )
    from app.styles import inject_global_css
    from app.utils.constants import CERTIFICATION_TYPES
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.status import status_pill_html  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from pages.modules._data import (  # type: ignore
        ACTIVE_EMPLOYEE_KEY,
        certification_alerts,
        get_employee,
        load_all_certifications,
        load_certifications,
        load_employees,
    )
    from styles import inject_global_css  # type: ignore
    from utils.constants import CERTIFICATION_TYPES  # type: ignore
    from utils.formatting import fmt_date  # type: ignore


def _filter_certs(rows: list[dict], *, q: str, status: str, cert_type: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            c
            for c in out
            if ql in str(c.get("cert_type", "")).lower()
            or ql in str(c.get("cert_number", "")).lower()
            or ql in str(c.get("employee_name", "")).lower()
        ]
    if status and status != "All Statuses":
        out = [c for c in out if str(c.get("status", "")) == status]
    if cert_type and cert_type != "All Types":
        out = [c for c in out if str(c.get("cert_type", "")) == cert_type]
    return out


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
    if not begin_module("employee_certifications"):
        return
    employees = load_employees()
    emp_opts = {str(e.get("name") or ""): str(e.get("id") or "") for e in employees}
    names = list(emp_opts.keys())
    active_id = str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or "")
    default_name = next((n for n, eid in emp_opts.items() if eid == active_id), names[0] if names else "")

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header("Employee Certifications", "Track credentials, expirations, and compliance.")
    with act_r:
        if st.button("+ Add Certification", key="cert_add", type="primary", use_container_width=True):
            st.session_state["ips_cert_form_open"] = True

    all_certs = load_all_certifications()
    expired_n, expiring_n = certification_alerts(all_certs)
    if expired_n or expiring_n:
        parts = []
        if expired_n:
            parts.append(f"{expired_n} expired")
        if expiring_n:
            parts.append(f"{expiring_n} expiring within 30 days")
        st.markdown(
            f'<p class="ips-alert-banner">⚠ {html.escape(" · ".join(parts))}</p>',
            unsafe_allow_html=True,
        )

    def _filters() -> None:
        c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1])
        with c1:
            idx = names.index(default_name) if default_name in names else 0
            picked = st.selectbox("Employee", names, index=idx, key="cert_emp_filter", label_visibility="collapsed")
            st.session_state[ACTIVE_EMPLOYEE_KEY] = emp_opts.get(picked, "")
        with c2:
            st.text_input("Search", placeholder="Search type or number…", key="cert_search", label_visibility="collapsed")
        with c3:
            st.selectbox(
                "Status",
                ["All Statuses", "Active", "Expiring Soon", "Expired"],
                key="cert_status_filter",
                label_visibility="collapsed",
            )
        with c4:
            st.selectbox(
                "Type",
                ["All Types", *CERTIFICATION_TYPES],
                key="cert_type_filter",
                label_visibility="collapsed",
            )

    layout_filter_bar(_filters)

    eid = str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or "")
    scope = load_certifications(eid) if eid else all_certs
    filtered = _filter_certs(
        scope,
        q=str(st.session_state.get("cert_search") or ""),
        status=str(st.session_state.get("cert_status_filter") or "All Statuses"),
        cert_type=str(st.session_state.get("cert_type_filter") or "All Types"),
    )

    if st.session_state.get("ips_cert_form_open"):
        with st.expander("New certification", expanded=True):
            fc1, fc2 = st.columns(2)
            with fc1:
                st.selectbox("Type", CERTIFICATION_TYPES, key="cert_new_type")
                st.text_input("Certificate number", key="cert_new_number")
                st.text_input("Issuing organization", key="cert_new_issuer")
            with fc2:
                st.date_input("Issue date", key="cert_new_issue")
                st.date_input("Expiration date", key="cert_new_exp")
                st.text_area("Notes", key="cert_new_notes", height=68)
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("Save", key="cert_save_new", type="primary"):
                    try:
                        from app.pages.modules._data import persist_certification
                    except ImportError:
                        from pages.modules._data import persist_certification  # type: ignore
                    ui = {
                        "employee_id": str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or ""),
                        "cert_type": st.session_state.get("cert_new_type"),
                        "cert_number": st.session_state.get("cert_new_number"),
                        "issuer": st.session_state.get("cert_new_issuer"),
                        "issue_date": st.session_state.get("cert_new_issue"),
                        "expiration_date": st.session_state.get("cert_new_exp"),
                        "status": "Active",
                        "notes": st.session_state.get("cert_new_notes"),
                    }
                    ok, msg = persist_certification(ui)
                    if ok:
                        st.success(msg)
                        st.session_state["ips_cert_form_open"] = False
                        st.rerun()
                    else:
                        st.error(msg)
            with bc2:
                if st.button("Cancel", key="cert_cancel_new"):
                    st.session_state["ips_cert_form_open"] = False
                    st.rerun()

    def _cell(field: str, row: dict) -> str:
        if field == "status":
            return status_pill_html(str(row.get("status") or ""))
        if field in ("issue_date", "expiration_date"):
            return html.escape(fmt_date(row.get(field)))
        return html.escape(str(row.get(field) or "—"))

    cols = [
        ("cert_type", "TYPE"),
        ("cert_number", "NUMBER"),
        ("issuer", "ISSUING ORG"),
        ("issue_date", "ISSUED"),
        ("expiration_date", "EXPIRES"),
        ("status", "STATUS"),
    ]
    if not eid:
        cols.insert(0, ("employee_name", "EMPLOYEE"))

    render_data_table(
        filtered,
        cols,
        row_id_key="id",
        selected_id=None,
        session_select_key="_cert_list",
        col_fr=None,
        cell_renderer=_cell,
        hide_select=True,
    )

    emp = get_employee(eid) if eid else None
    if emp:
        st.caption(f"Showing certifications for **{emp.get('name')}**")
