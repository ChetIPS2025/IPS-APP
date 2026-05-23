"""Employee Certifications module (Phase 2C)."""

from __future__ import annotations

import html
from datetime import date
from functools import partial

import streamlit as st

try:
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.record_modal import (
        detail_field_html,
        dialog_card_html,
        edit_mode_key,
        is_edit_mode,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        set_view_mode,
    )
    from app.pages._core._crud import is_demo_id
    from app.pages._core._data import (
        ACTIVE_EMPLOYEE_KEY,
        certification_alerts,
        get_employee,
        load_all_certifications,
        load_certifications,
        load_employees,
    )
    from app.services.certification_helpers import (
        CERT_STATUS_VALUES,
        cert_status_pill_html,
        days_until_expiration,
    )
    from app.services.employees_service import (
        clear_certifications_cache,
        create_employee_certification,
        update_employee_certification,
    )
    from app.styles import inject_certifications_module_css
    from app.utils.constants import CERTIFICATION_TYPES
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.record_modal import (  # type: ignore
        detail_field_html,
        dialog_card_html,
        edit_mode_key,
        is_edit_mode,
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_save_cancel_actions,
        set_view_mode,
    )
    from pages._core._crud import is_demo_id  # type: ignore
    from pages._core._data import (  # type: ignore
        ACTIVE_EMPLOYEE_KEY,
        certification_alerts,
        get_employee,
        load_all_certifications,
        load_certifications,
        load_employees,
    )
    from services.certification_helpers import (  # type: ignore
        CERT_STATUS_VALUES,
        cert_status_pill_html,
        days_until_expiration,
    )
    from services.employees_service import (  # type: ignore
        clear_certifications_cache,
        create_employee_certification,
        update_employee_certification,
    )
    from styles import inject_certifications_module_css  # type: ignore
    from utils.constants import CERTIFICATION_TYPES  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_MODULE = "employee_certifications"
_ALL_CERT_IDS_KEY = "_cert_page_all_ids"
_STATUS_FILTERS = ["All Statuses", *CERT_STATUS_VALUES]

_CERT_COLS_ALL = [0.35, 2.2, 1.5, 1.6, 1.8, 1.2, 1.2, 1.4]
_CERT_HEADERS_ALL = ["", "EMPLOYEE", "TYPE", "NUMBER", "ISSUING ORG", "ISSUED", "EXPIRES", "STATUS"]
_CERT_COLS_EMP = [0.35, 2.0, 1.8, 2.0, 1.3, 1.3, 1.4]
_CERT_HEADERS_EMP = ["", "TYPE", "NUMBER", "ISSUING ORG", "ISSUED", "EXPIRES", "STATUS"]


def _cert_select_key(cert_id: str, *, prefix: str = "") -> str:
    return f"{prefix}certification_select_{cert_id}"


def _selected_id_key(*, prefix: str = "") -> str:
    return f"{prefix}selected_certification_id" if prefix else "selected_certification_id"


def _show_detail_key(*, prefix: str = "") -> str:
    return f"{prefix}show_certification_detail" if prefix else "show_certification_detail"


def _clear_certification_selection(cert_ids: list[str] | None = None, *, prefix: str = "") -> None:
    st.session_state[_selected_id_key(prefix=prefix)] = None
    st.session_state[_show_detail_key(prefix=prefix)] = False
    if cert_ids:
        for cid in cert_ids:
            st.session_state[_cert_select_key(cid, prefix=prefix)] = False


def _on_certification_checkbox_change(cert_id: str, all_cert_ids: list[str], *, prefix: str = "") -> None:
    key = _cert_select_key(cert_id, prefix=prefix)
    if st.session_state.get(key):
        for cid in all_cert_ids:
            if cid != cert_id:
                st.session_state[_cert_select_key(cid, prefix=prefix)] = False
        st.session_state[_selected_id_key(prefix=prefix)] = cert_id
        st.session_state[_show_detail_key(prefix=prefix)] = True
    elif st.session_state.get(_selected_id_key(prefix=prefix)) == cert_id:
        st.session_state[_selected_id_key(prefix=prefix)] = None
        st.session_state[_show_detail_key(prefix=prefix)] = False


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
            or ql in str(c.get("issuer", "")).lower()
        ]
    if status and status != "All Statuses":
        out = [c for c in out if str(c.get("status", "")) == status]
    if cert_type and cert_type != "All Types":
        out = [c for c in out if str(c.get("cert_type", "")) == cert_type]
    return out


def _as_date(value: object):
    if isinstance(value, date):
        return value
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _employee_options() -> tuple[list[str], dict[str, str]]:
    employees = load_employees()
    emp_opts = {str(e.get("name") or ""): str(e.get("id") or "") for e in employees if str(e.get("id") or "").strip()}
    names = [n for n in emp_opts if n]
    return names, emp_opts


def _render_certifications_table(
    certifications: list[dict],
    *,
    hide_employee: bool,
    table_wrap_key: str,
    session_prefix: str = "",
) -> list[str]:
    if not certifications:
        st.info("No certifications match your filters.")
        st.session_state[_ALL_CERT_IDS_KEY] = []
        return []

    all_cert_ids = [
        str(c.get("id") or "").strip() for c in certifications if str(c.get("id") or "").strip()
    ]
    st.session_state[_ALL_CERT_IDS_KEY] = all_cert_ids

    col_ratios = _CERT_COLS_EMP if hide_employee else _CERT_COLS_ALL
    headers = _CERT_HEADERS_EMP if hide_employee else _CERT_HEADERS_ALL

    with st.container(key=table_wrap_key):
        st.markdown('<div class="ips-certifications-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(col_ratios, gap="small", vertical_alignment="center")
        for col, label in zip(header_cols, headers):
            with col:
                st.markdown(
                    f'<div class="ips-certifications-header-row ips-certifications-cell">{html.escape(label)}</div>',
                    unsafe_allow_html=True,
                )

        for cert in certifications:
            cid = str(cert.get("id") or "").strip()
            if not cid:
                continue

            cert_type = str(cert.get("cert_type") or "—")
            cert_number = str(cert.get("cert_number") or "—")
            issuer = str(cert.get("issuer") or "—")
            issued = fmt_date(cert.get("issue_date"))
            expires = fmt_date(cert.get("expiration_date"))
            status = str(cert.get("status") or "—")
            employee_name = str(cert.get("employee_name") or "—")

            cols = st.columns(col_ratios, gap="small", vertical_alignment="center")

            with cols[0]:
                st.checkbox(
                    "",
                    key=_cert_select_key(cid, prefix=session_prefix),
                    label_visibility="collapsed",
                    on_change=partial(
                        _on_certification_checkbox_change,
                        cid,
                        all_cert_ids,
                        prefix=session_prefix,
                    ),
                )

            col_idx = 1
            if not hide_employee:
                with cols[col_idx]:
                    st.markdown(
                        f'<div class="ips-certifications-cell">{html.escape(employee_name)}</div>',
                        unsafe_allow_html=True,
                    )
                col_idx += 1

            with cols[col_idx]:
                st.markdown(
                    f'<div class="ips-certifications-type">{html.escape(cert_type)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[col_idx + 1]:
                st.markdown(
                    f'<div class="ips-certifications-cell ips-certifications-muted">{html.escape(cert_number)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[col_idx + 2]:
                st.markdown(
                    f'<div class="ips-certifications-cell ips-certifications-muted">{html.escape(issuer)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[col_idx + 3]:
                st.markdown(
                    f'<div class="ips-certifications-cell ips-certifications-muted">{html.escape(issued)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[col_idx + 4]:
                st.markdown(
                    f'<div class="ips-certifications-cell ips-certifications-muted">{html.escape(expires)}</div>',
                    unsafe_allow_html=True,
                )
            with cols[col_idx + 5]:
                st.markdown(
                    f'<div class="ips-certifications-cell">{cert_status_pill_html(status)}</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)

    st.caption("Select a certification to view details.")
    return all_cert_ids


def _seed_cert_edit_form(cert: dict, employee_names: list[str], emp_opts: dict[str, str]) -> None:
    rk = record_session_key(cert, "id")
    emp_name = next(
        (n for n, eid in emp_opts.items() if eid == str(cert.get("employee_id") or "")),
        employee_names[0] if employee_names else "",
    )
    st.session_state[f"cert_edit_emp_{rk}"] = emp_name if emp_name in employee_names else (employee_names[0] if employee_names else "")
    st.session_state[f"cert_edit_type_{rk}"] = str(cert.get("cert_type") or CERTIFICATION_TYPES[0])
    st.session_state[f"cert_edit_num_{rk}"] = str(cert.get("cert_number") or "")
    st.session_state[f"cert_edit_issuer_{rk}"] = str(cert.get("issuer") or "")
    st.session_state[f"cert_edit_issue_{rk}"] = _as_date(cert.get("issue_date"))
    st.session_state[f"cert_edit_exp_{rk}"] = _as_date(cert.get("expiration_date"))
    st.session_state[f"cert_edit_notes_{rk}"] = str(cert.get("notes") or "")


def _render_cert_edit_form(cert: dict, employee_names: list[str], emp_opts: dict[str, str]) -> None:
    rk = record_session_key(cert, "id")
    cid = str(cert.get("id") or "")
    if f"cert_edit_type_{rk}" not in st.session_state:
        _seed_cert_edit_form(cert, employee_names, emp_opts)

    render_edit_form_header("Edit Certification")
    ec1, ec2 = st.columns(2)
    with ec1:
        st.selectbox("Employee", employee_names, key=f"cert_edit_emp_{rk}")
        st.selectbox("Certification Type", CERTIFICATION_TYPES, key=f"cert_edit_type_{rk}")
        st.text_input("Certification Number", key=f"cert_edit_num_{rk}")
        st.text_input("Issuing Organization", key=f"cert_edit_issuer_{rk}")
    with ec2:
        st.date_input("Issue Date", key=f"cert_edit_issue_{rk}")
        st.date_input("Expiration Date", key=f"cert_edit_exp_{rk}")
        st.file_uploader("Attachment", key=f"cert_edit_file_{rk}", disabled=True)
        st.caption("File upload will be enabled in a later phase.")
    st.text_area("Notes", key=f"cert_edit_notes_{rk}", height=80)

    cancelled, saved = render_save_cancel_actions(
        module=_MODULE,
        record_key=rk,
        cancel_key=f"cert_edit_cancel_{rk}",
        save_key=f"cert_edit_save_{rk}",
    )
    if cancelled:
        set_view_mode(_MODULE, rk)
        st.rerun()
    if saved:
        emp_name = st.session_state.get(f"cert_edit_emp_{rk}")
        ui = {
            "employee_id": emp_opts.get(str(emp_name or ""), str(cert.get("employee_id") or "")),
            "cert_type": st.session_state.get(f"cert_edit_type_{rk}"),
            "cert_number": st.session_state.get(f"cert_edit_num_{rk}"),
            "issuer": st.session_state.get(f"cert_edit_issuer_{rk}"),
            "issue_date": st.session_state.get(f"cert_edit_issue_{rk}"),
            "expiration_date": st.session_state.get(f"cert_edit_exp_{rk}"),
            "notes": st.session_state.get(f"cert_edit_notes_{rk}"),
        }
        row_id = None if is_demo_id(cid) else cid
        if row_id:
            result = update_employee_certification(row_id, ui)
        else:
            result = create_employee_certification(ui)
        if result.ok:
            clear_certifications_cache()
            set_view_mode(_MODULE, rk)
            st.success("Certification saved.")
            st.rerun()
        else:
            st.error(result.error or "Could not save certification.")


def _render_cert_detail_tabs(cert: dict) -> None:
    emp = get_employee(str(cert.get("employee_id") or ""))
    status = str(cert.get("status") or "")

    tab_overview, tab_employee, tab_attachment, tab_notes, tab_activity = st.tabs(
        ["Overview", "Employee", "Attachment", "Notes", "Activity"]
    )

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Certification Type', cert.get('cert_type'))}"
            f"{detail_field_html('Certification Number', cert.get('cert_number'))}"
            f"{detail_field_html('Issuing Organization', cert.get('issuer'))}"
            f"{detail_field_html('Issue Date', fmt_date(cert.get('issue_date')))}"
            f"{detail_field_html('Expiration Date', fmt_date(cert.get('expiration_date')))}"
            f'{detail_field_html("Status", status, html_value=cert_status_pill_html(status))}'
            f"{detail_field_html('Days Until Expiration', days_until_expiration(cert.get('expiration_date')))}"
            f"{detail_field_html('Notes', cert.get('notes') or '—')}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Certification", overview_html), unsafe_allow_html=True)

    with tab_employee:
        if emp:
            employee_html = (
                f'<div class="ips-detail-grid">'
                f"{detail_field_html('Name', emp.get('name'))}"
                f"{detail_field_html('Email', emp.get('email'))}"
                f"{detail_field_html('Role', emp.get('role'))}"
                f"{detail_field_html('Department', emp.get('department'))}"
                f"{detail_field_html('Status', emp.get('status'))}"
                f"</div>"
            )
            st.markdown(dialog_card_html("Employee", employee_html), unsafe_allow_html=True)
        else:
            st.caption("Employee record not found.")

    with tab_attachment:
        path = str(cert.get("attachment_path") or "").strip()
        if path:
            st.markdown(f"Attachment: `{html.escape(path)}`")
        else:
            placeholder_html("Attachment upload and preview will be enabled in a later phase.")

    with tab_notes:
        notes = str(cert.get("notes") or "").strip() or "No notes entered."
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Certification activity history will appear here.")


def render_certification_detail_dialog(
    selected_certification: dict,
    all_cert_ids: list[str],
    *,
    inline: bool = False,
    session_prefix: str = "",
) -> None:
    cert = selected_certification
    rk = record_session_key(cert, "id")
    st.session_state.setdefault(edit_mode_key(_MODULE, rk), False)
    edit_mode = is_edit_mode(_MODULE, rk)
    employee_names, emp_opts = _employee_options()

    render_modal_shell()
    render_modal_header(
        title=str(cert.get("cert_type") or "Certification"),
        subtitle=str(cert.get("cert_number") or ""),
        status=str(cert.get("status") or ""),
    )
    render_modal_edit_button(
        module=_MODULE,
        record_key=rk,
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
        _render_cert_edit_form(cert, employee_names, emp_opts)
    else:
        _render_cert_detail_tabs(cert)


def _clear_cert_detail_dialog() -> None:
    cert_ids = st.session_state.get(_ALL_CERT_IDS_KEY) or []
    _clear_certification_selection([str(cid) for cid in cert_ids])


@st.dialog("Certification Details", width="large", on_dismiss=_clear_cert_detail_dialog)
def _open_certification_detail_dialog(selected_certification: dict, all_cert_ids: list[str]) -> None:
    render_certification_detail_dialog(selected_certification, all_cert_ids, inline=True)


def render_certifications_table_block(
    certifications: list[dict],
    *,
    hide_employee: bool = False,
    table_wrap_key: str = "certifications_table_wrap",
    session_prefix: str = "",
    inline_detail: bool = False,
) -> list[str]:
    all_cert_ids = _render_certifications_table(
        certifications,
        hide_employee=hide_employee,
        table_wrap_key=table_wrap_key,
        session_prefix=session_prefix,
    )
    if inline_detail:
        selected_certification_id = st.session_state.get(_selected_id_key(prefix=session_prefix))
        show_detail = st.session_state.get(_show_detail_key(prefix=session_prefix), False)
        if selected_certification_id and show_detail:
            selected_certification = next(
                (
                    c
                    for c in certifications
                    if str(c.get("id")) == str(selected_certification_id)
                ),
                None,
            )
            if selected_certification:
                st.markdown("---")
                render_certification_detail_dialog(
                    selected_certification,
                    all_cert_ids,
                    inline=True,
                    session_prefix=session_prefix,
                )
    return all_cert_ids


@st.dialog("Add Certification", width="large")
def _show_add_certification_dialog(default_employee_id: str) -> None:
    employee_names, emp_opts = _employee_options()
    default_name = next(
        (n for n, eid in emp_opts.items() if eid == default_employee_id),
        employee_names[0] if employee_names else "",
    )
    idx = employee_names.index(default_name) if default_name in employee_names else 0

    st.markdown("### New Certification")
    c1, c2 = st.columns(2)
    with c1:
        picked = st.selectbox("Employee", employee_names, index=idx, key="cert_new_emp")
        st.selectbox("Certification Type", CERTIFICATION_TYPES, key="cert_new_type")
        st.text_input("Certification Number", key="cert_new_number")
        st.text_input("Issuing Organization", key="cert_new_issuer")
    with c2:
        st.date_input("Issue Date", key="cert_new_issue")
        st.date_input("Expiration Date", key="cert_new_exp")
        st.file_uploader("Attachment", key="cert_new_file", disabled=True)
        st.caption("File upload will be enabled in a later phase.")
    st.text_area("Notes", key="cert_new_notes", height=80)

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Save Certification", key="cert_save_new", type="primary", use_container_width=True):
            ui = {
                "employee_id": emp_opts.get(str(picked or ""), default_employee_id),
                "cert_type": st.session_state.get("cert_new_type"),
                "cert_number": st.session_state.get("cert_new_number"),
                "issuer": st.session_state.get("cert_new_issuer"),
                "issue_date": st.session_state.get("cert_new_issue"),
                "expiration_date": st.session_state.get("cert_new_exp"),
                "notes": st.session_state.get("cert_new_notes"),
            }
            result = create_employee_certification(ui)
            if result.ok:
                clear_certifications_cache()
                st.session_state["ips_cert_form_open"] = False
                st.success("Certification saved.")
                st.rerun()
            else:
                st.error(result.error or "Could not save certification.")
    with bc2:
        if st.button("Cancel", key="cert_cancel_new", use_container_width=True):
            st.session_state["ips_cert_form_open"] = False
            st.rerun()


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("employee_certifications"):
        return

    inject_certifications_module_css()

    employee_names, emp_opts = _employee_options()
    filter_names = ["All Employees", *employee_names]
    active_id = str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or "")
    default_filter = next(
        (n for n, eid in emp_opts.items() if eid == active_id),
        "All Employees",
    )
    if default_filter not in filter_names:
        default_filter = "All Employees"

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
        c1, c2, c3, c4, c5 = st.columns([1.2, 1.2, 1, 1, 0.6])
        with c1:
            idx = filter_names.index(default_filter) if default_filter in filter_names else 0
            picked = st.selectbox(
                "Employee",
                filter_names,
                index=idx,
                key="cert_emp_filter",
                label_visibility="collapsed",
            )
            if picked == "All Employees":
                st.session_state[ACTIVE_EMPLOYEE_KEY] = ""
            else:
                st.session_state[ACTIVE_EMPLOYEE_KEY] = emp_opts.get(picked, "")
        with c2:
            st.text_input(
                "Search",
                placeholder="Search type or number...",
                key="cert_search",
                label_visibility="collapsed",
            )
        with c3:
            st.selectbox(
                "Status",
                _STATUS_FILTERS,
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
        with c5:
            if st.button("Clear", key="cert_clear", use_container_width=True):
                st.session_state["cert_search"] = ""
                st.session_state["cert_status_filter"] = "All Statuses"
                st.session_state["cert_type_filter"] = "All Types"
                st.session_state["cert_emp_filter"] = "All Employees"
                st.session_state[ACTIVE_EMPLOYEE_KEY] = ""
                _clear_certification_selection(st.session_state.get(_ALL_CERT_IDS_KEY))
                st.rerun()

    layout_filter_bar(_filters)

    eid = str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or "")
    scope = load_certifications(eid) if eid else all_certs
    filtered = _filter_certs(
        scope,
        q=str(st.session_state.get("cert_search") or "").strip(),
        status=str(st.session_state.get("cert_status_filter") or "All Statuses"),
        cert_type=str(st.session_state.get("cert_type_filter") or "All Types"),
    )

    st.caption(f"{len(filtered)} certification(s)")

    if st.session_state.get("ips_cert_form_open"):
        _show_add_certification_dialog(eid)

    all_cert_ids = render_certifications_table_block(
        filtered,
        hide_employee=bool(eid),
        table_wrap_key="certifications_table_wrap",
        inline_detail=False,
    )

    selected_certification_id = st.session_state.get("selected_certification_id")
    show_detail = st.session_state.get("show_certification_detail", False)
    if selected_certification_id and show_detail:
        selected_certification = next(
            (c for c in filtered if str(c.get("id")) == str(selected_certification_id)),
            None,
        )
        if selected_certification:
            _open_certification_detail_dialog(selected_certification, all_cert_ids)
