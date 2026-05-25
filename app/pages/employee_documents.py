"""Employee Documents module (Phase 2C)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_role
    from app.components.clickable_table import render_clickable_table
    from app.components.headers import render_page_brand_header
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
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        show_modal_if_pending,
    )
    from app.pages._core._data import ACTIVE_EMPLOYEE_KEY, get_employee, load_employee_documents, load_employees
    from app.utils.constants import DOCUMENT_TYPES
    from app.utils.formatting import fmt_date
    from app.utils.permissions import can_view_hr_documents, normalize_role
    from app.pages._core._session import select_key
except ImportError:
    from auth import current_role  # type: ignore
    from components.clickable_table import render_clickable_table  # type: ignore
    from components.headers import render_page_brand_header  # type: ignore
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
        placeholder_html,
        record_session_key,
        render_edit_form_header,
        render_modal_edit_button,
        render_modal_header,
        render_modal_meta_grid,
        render_modal_shell,
        render_missing_record,
        render_save_cancel_actions,
        set_view_mode,
        show_modal_if_pending,
    )
    from pages._core._data import ACTIVE_EMPLOYEE_KEY, get_employee, load_employee_documents, load_employees  # type: ignore
    from utils.constants import DOCUMENT_TYPES  # type: ignore
    from utils.formatting import fmt_date  # type: ignore
    from utils.permissions import can_view_hr_documents, normalize_role  # type: ignore
    from pages._core._session import select_key  # type: ignore

_SEL = select_key("employee_documents")
_MODULE = "employee_documents"
_TABLE_KEY = "doc_list"
_MODAL_KEY = "ips_doc_detail_modal_id"
_CACHE_KEY = "_ips_emp_doc_modal_by_id"


def _filter_docs(rows: list[dict], *, q: str, doc_type: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [d for d in out if ql in str(d.get("doc_type", "")).lower() or ql in str(d.get("file_name", "")).lower()]
    if doc_type and doc_type != "All Types":
        out = [d for d in out if str(d.get("doc_type", "")) == doc_type]
    return out


def _access_label(row: dict) -> str:
    return "Restricted" if row.get("is_restricted") else "Standard"


def _clear_doc_modal() -> None:
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
    )


def _open_doc_modal(doc_id: str, doc: dict | None = None) -> None:
    open_record_modal(
        doc_id,
        doc,
        session_select_key=_SEL,
        modal_key=_MODAL_KEY,
        module=_MODULE,
        id_fields=("id",),
    )


def _seed_doc_edit_form(doc: dict) -> None:
    rk = record_session_key(doc, "id")
    st.session_state[f"doc_edit_type_{rk}"] = str(doc.get("doc_type") or DOCUMENT_TYPES[0])
    st.session_state[f"doc_edit_exp_{rk}"] = doc.get("expiration_date")
    st.session_state[f"doc_edit_restricted_{rk}"] = bool(doc.get("is_restricted"))


def _render_doc_view_tabs(doc: dict) -> None:
    tab_overview, tab_access, tab_attachments = st.tabs(["Overview", "Access", "Attachments"])
    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Document Type', doc.get('doc_type'))}"
            f"{detail_field_html('File Name', doc.get('file_name'))}"
            f"{detail_field_html('Uploaded', fmt_date(doc.get('upload_date')))}"
            f"{detail_field_html('Uploaded By', doc.get('uploaded_by'))}"
            f"{detail_field_html('Expiration', fmt_date(doc.get('expiration_date')) if doc.get('expiration_date') else '—')}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Document", overview_html), unsafe_allow_html=True)
    with tab_access:
        access_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Access Level', _access_label(doc))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Access", access_html), unsafe_allow_html=True)
    with tab_attachments:
        placeholder_html("Document preview and download will appear here when connected to Supabase.")


def _render_doc_edit_form(doc: dict, *, hr_ok: bool) -> None:
    rk = record_session_key(doc, "id")
    if f"doc_edit_type_{rk}" not in st.session_state:
        _seed_doc_edit_form(doc)

    render_edit_form_header("Edit Document")
    st.selectbox("Document type", DOCUMENT_TYPES, key=f"doc_edit_type_{rk}")
    st.date_input("Expiration date (optional)", key=f"doc_edit_exp_{rk}", value=None)
    st.checkbox("Restricted / private (HR only)", key=f"doc_edit_restricted_{rk}", disabled=not hr_ok)

    cancelled, saved = render_save_cancel_actions(
        module=_MODULE,
        record_key=rk,
        cancel_key=f"doc_edit_cancel_{rk}",
        save_key=f"doc_edit_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved:
        set_view_mode(_MODULE, rk)
        st.success("Document updated (demo).")
        st.rerun()


def render_doc_detail_dialog(doc: dict, *, hr_ok: bool) -> None:
    rk = record_session_key(doc, "id")
    st.session_state.setdefault(edit_mode_key(_MODULE, rk), False)
    edit_mode = is_edit_mode(_MODULE, rk)

    render_modal_shell()
    render_modal_header(
        title=str(doc.get("file_name") or "Document"),
        subtitle=str(doc.get("doc_type") or ""),
    )
    render_modal_edit_button(
        module=_MODULE,
        record_key=rk,
        key_prefix=f"doc_modal_{rk}",
    )
    render_modal_meta_grid(
        [
            ("Uploaded", fmt_date(doc.get("upload_date"))),
            ("Uploaded By", doc.get("uploaded_by")),
            ("Expires", fmt_date(doc.get("expiration_date")) if doc.get("expiration_date") else "—"),
            ("Access", _access_label(doc)),
        ]
    )

    if edit_mode:
        _render_doc_edit_form(doc, hr_ok=hr_ok)
    else:
        _render_doc_view_tabs(doc)
        st.button("Download", key=f"doc_modal_dl_{rk}", type="primary")


@st.dialog("Document Details", width="large", on_dismiss=_clear_doc_modal)
def _show_doc_detail_modal() -> None:
    doc = get_modal_record(
        cache_key=_CACHE_KEY,
        modal_key=_MODAL_KEY,
        session_select_key=_SEL,
    )
    if not doc:
        render_missing_record(_clear_doc_modal, close_key="doc_modal_missing_close")
        return
    role_norm = normalize_role(current_role())
    hr_ok = can_view_hr_documents(role_norm)
    render_doc_detail_dialog(doc, hr_ok=hr_ok)


def _doc_display_cell(field: str, row: dict) -> str:
    if field == "access":
        return _access_label(row)
    if field in ("upload_date", "expiration_date"):
        return fmt_date(row.get(field)) if row.get(field) else "—"
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("employee_documents"):
        return
    role_norm = normalize_role(current_role())
    hr_ok = can_view_hr_documents(role_norm)
    employees = load_employees()
    emp_opts = {str(e.get("name") or ""): str(e.get("id") or "") for e in employees}
    names = list(emp_opts.keys())
    active_id = str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or "")
    default_name = next((n for n, eid in emp_opts.items() if eid == active_id), names[0] if names else "")

    def _doc_upload() -> None:
        if st.button("+ Upload Document", key="doc_upload", type="primary", use_container_width=True):
            st.session_state["ips_doc_form_open"] = True

    render_page_brand_header(
        "Employee Documents",
        "Store licenses, training records, and HR files.",
        actions=[_doc_upload],
    )

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

    build_modal_cache(filtered, cache_key=_CACHE_KEY)
    render_clickable_table(
        filtered,
        [
            ("doc_type", "DOCUMENT TYPE"),
            ("file_name", "FILE"),
            ("upload_date", "UPLOADED"),
            ("uploaded_by", "UPLOADED BY"),
            ("expiration_date", "EXPIRES"),
            ("access", "ACCESS"),
        ],
        _TABLE_KEY,
        row_id_key="id",
        session_select_key=_SEL,
        format_cell=_doc_display_cell,
        click_caption="Click a row to open document details.",
        on_row_selected=_open_doc_modal,
    )
    show_modal_if_pending(_MODAL_KEY, _show_doc_detail_modal)

    emp = get_employee(eid) if eid else None
    if emp:
        st.caption(f"Documents for **{emp.get('name')}** · {len(filtered)} file(s)")
