"""Employee Certifications module (Phase 2C)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.clickable_table import render_clickable_table
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.record_modal import (
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        edit_mode_key,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        record_session_key,
        render_edit_form_header,
        render_modal_actions,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        show_modal_if_pending,
        status_pill_html,
    )
    from app.pages._core._data import (
        ACTIVE_EMPLOYEE_KEY,
        certification_alerts,
        get_employee,
        load_all_certifications,
        load_certifications,
        load_employees,
        persist_certification,
    )
    from app.pages._core._crud import apply_persist_feedback, is_demo_id
    from app.pages._core._session import select_key
    from app.utils.constants import CERTIFICATION_TYPES
    from app.utils.formatting import fmt_date
except ImportError:
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.record_modal import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        detail_field_html,
        dialog_card_html,
        edit_mode_key,
        get_modal_record,
        is_edit_mode,
        open_record_modal,
        record_session_key,
        render_edit_form_header,
        render_modal_actions,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        show_modal_if_pending,
        status_pill_html,
    )
    from pages._core._data import (  # type: ignore
        ACTIVE_EMPLOYEE_KEY,
        certification_alerts,
        get_employee,
        load_all_certifications,
        load_certifications,
        load_employees,
        persist_certification,
    )
    from pages._core._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages._core._session import select_key  # type: ignore
    from utils.constants import CERTIFICATION_TYPES  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_SEL = select_key("employee_certifications")
_MODULE = "employee_certifications"
_TABLE_KEY = "cert_list"
_MODAL_KEY = "ips_cert_detail_modal_id"
_CACHE_KEY = "_ips_cert_modal_by_id"


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


def _clear_cert_modal() -> None:
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _open_cert_modal(cert_id: str, cert: dict | None = None) -> None:
    open_record_modal(
        cert_id,
        cert,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
        id_fields=("id",),
    )


def _seed_cert_edit_form(cert: dict) -> None:
    rk = record_session_key(cert, "id")
    st.session_state[f"cert_edit_type_{rk}"] = str(cert.get("cert_type") or CERTIFICATION_TYPES[0])
    st.session_state[f"cert_edit_num_{rk}"] = str(cert.get("cert_number") or "")
    st.session_state[f"cert_edit_issuer_{rk}"] = str(cert.get("issuer") or "")
    st.session_state[f"cert_edit_issue_{rk}"] = cert.get("issue_date")
    st.session_state[f"cert_edit_exp_{rk}"] = cert.get("expiration_date")
    st.session_state[f"cert_edit_status_{rk}"] = str(cert.get("status") or "Active")
    st.session_state[f"cert_edit_notes_{rk}"] = str(cert.get("notes") or "")


def _render_cert_view_tabs(cert: dict) -> None:
    tab_overview, tab_notes = st.tabs(["Overview", "Notes"])
    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Type', cert.get('cert_type'))}"
            f"{detail_field_html('Number', cert.get('cert_number'))}"
            f"{detail_field_html('Issuing Organization', cert.get('issuer'))}"
            f"{detail_field_html('Issue Date', fmt_date(cert.get('issue_date')))}"
            f"{detail_field_html('Expiration', fmt_date(cert.get('expiration_date')))}"
            f'{detail_field_html("Status", cert.get("status"), html_value=status_pill_html(str(cert.get("status") or "")))}'
            f"{detail_field_html('Employee', cert.get('employee_name'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Certification", overview_html), unsafe_allow_html=True)
    with tab_notes:
        notes = str(cert.get("notes") or "").strip() or "No notes entered."
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)


def _render_cert_edit_form(cert: dict) -> None:
    rk = record_session_key(cert, "id")
    cid = str(cert.get("id") or "")
    if f"cert_edit_type_{rk}" not in st.session_state:
        _seed_cert_edit_form(cert)

    render_edit_form_header("Edit Certification")
    ec1, ec2 = st.columns(2)
    with ec1:
        st.selectbox("Type", CERTIFICATION_TYPES, key=f"cert_edit_type_{rk}")
        st.text_input("Certificate number", key=f"cert_edit_num_{rk}")
        st.text_input("Issuing organization", key=f"cert_edit_issuer_{rk}")
    with ec2:
        st.date_input("Issue date", key=f"cert_edit_issue_{rk}")
        st.date_input("Expiration date", key=f"cert_edit_exp_{rk}")
        st.selectbox("Status", ["Active", "Expiring Soon", "Expired"], key=f"cert_edit_status_{rk}")
    st.text_area("Notes", key=f"cert_edit_notes_{rk}", height=80)

    cancelled, saved = render_save_cancel_actions(
        module=_MODULE,
        record_key=rk,
        cancel_key=f"cert_edit_cancel_{rk}",
        save_key=f"cert_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved:
        ui = {
            "employee_id": str(cert.get("employee_id") or ""),
            "cert_type": st.session_state.get(f"cert_edit_type_{rk}"),
            "cert_number": st.session_state.get(f"cert_edit_num_{rk}"),
            "issuer": st.session_state.get(f"cert_edit_issuer_{rk}"),
            "issue_date": st.session_state.get(f"cert_edit_issue_{rk}"),
            "expiration_date": st.session_state.get(f"cert_edit_exp_{rk}"),
            "status": st.session_state.get(f"cert_edit_status_{rk}"),
            "notes": st.session_state.get(f"cert_edit_notes_{rk}"),
        }
        row_id = None if is_demo_id(cid) else cid
        ok, msg = persist_certification(ui, row_id=row_id)
        if ok:
            set_view_mode(_MODULE, rk)
            st.success(msg or "Certification saved.")
            st.rerun()
        else:
            st.error(msg or "Could not save certification.")


def render_cert_detail_dialog(cert: dict) -> None:
    rk = record_session_key(cert, "id")
    st.session_state.setdefault(edit_mode_key(_MODULE, rk), False)
    edit_mode = is_edit_mode(_MODULE, rk)

    render_modal_shell()
    render_modal_header(
        title=str(cert.get("cert_type") or "Certification"),
        subtitle=str(cert.get("cert_number") or ""),
        status=str(cert.get("status") or ""),
    )
    render_modal_actions(
        module=_MODULE,
        record_key=rk,
        record=cert,
        on_close=_clear_cert_modal,
        key_prefix=f"cert_modal_{rk}",
    )
    render_modal_meta_grid(
        [
            ("Issuer", cert.get("issuer")),
            ("Issued", fmt_date(cert.get("issue_date"))),
            ("Expires", fmt_date(cert.get("expiration_date"))),
            ("Employee", cert.get("employee_name")),
        ]
    )

    if edit_mode:
        _render_cert_edit_form(cert)
    else:
        _render_cert_view_tabs(cert)


@st.dialog("Certification Details", width="large", on_dismiss=_clear_cert_modal)
def _show_cert_detail_modal() -> None:
    cert = get_modal_record(
        cache_key=_CACHE_KEY,
        modal_key=_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not cert:
        render_missing_record(_clear_cert_modal, close_key="cert_modal_missing_close")
        return
    render_cert_detail_dialog(cert)


def _cert_display_cell(field: str, row: dict) -> str:
    if field in ("issue_date", "expiration_date"):
        return fmt_date(row.get(field))
    if field == "status":
        return str(row.get("status") or "—")
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
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

    columns = [
        ("cert_type", "TYPE"),
        ("cert_number", "NUMBER"),
        ("issuer", "ISSUING ORG"),
        ("issue_date", "ISSUED"),
        ("expiration_date", "EXPIRES"),
        ("status", "STATUS"),
    ]
    if not eid:
        columns.insert(0, ("employee_name", "EMPLOYEE"))

    build_modal_cache(filtered, cache_key=_CACHE_KEY)
    render_clickable_table(
        filtered,
        columns,
        _TABLE_KEY,
        row_id_key="id",
        session_select_key=_SEL,
        format_cell=_cert_display_cell,
        click_caption="Click a row to open certification details.",
        on_row_selected=_open_cert_modal,
    )
    show_modal_if_pending(_MODAL_KEY, _show_cert_detail_modal)

    emp = get_employee(eid) if eid else None
    if emp:
        st.caption(f"Showing certifications for **{emp.get('name')}**")
