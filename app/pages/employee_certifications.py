"""Employee Certifications module (Phase 2C)."""

from __future__ import annotations

import html
from datetime import date
from functools import partial
from typing import Any

import streamlit as st

try:
    from app.components.headers import render_page_brand_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.table_filters import (
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
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
    from app.components.action_styles import danger_outline, danger_solid
    from app.services.certification_helpers import (
        CERT_STATUS_VALUES,
        can_delete_employee_certifications,
        can_manage_employee_certifications,
        can_view_certification_attachment,
        cert_status_pill_html,
        certification_visible_to_user,
        coerce_date,
        days_until_expiration,
        resolve_logged_in_employee_id,
    )
    from app.services.certification_attachments_service import cert_has_attachment
    from app.services.employees_service import (
        clear_certifications_cache,
        create_employee_certification,
        delete_employee_certification,
        get_certification_attachment_url,
        update_employee_certification,
        upload_certification_attachment,
    )
    from app.styles import inject_certifications_module_css
    from app.utils.constants import CERTIFICATION_TYPES
    from app.utils.formatting import fmt_date
except ImportError:
    from components.headers import render_page_brand_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.table_filters import (  # type: ignore
        apply_column_filters,
        build_filter_options,
        clear_table_filters,
        render_table_header_cell,
    )
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
    from components.action_styles import danger_outline, danger_solid  # type: ignore
    from services.certification_helpers import (  # type: ignore
        CERT_STATUS_VALUES,
        can_delete_employee_certifications,
        can_manage_employee_certifications,
        can_view_certification_attachment,
        cert_status_pill_html,
        certification_visible_to_user,
        coerce_date,
        days_until_expiration,
        resolve_logged_in_employee_id,
    )
    from services.certification_attachments_service import cert_has_attachment  # type: ignore
    from services.employees_service import (  # type: ignore
        clear_certifications_cache,
        create_employee_certification,
        delete_employee_certification,
        get_certification_attachment_url,
        update_employee_certification,
        upload_certification_attachment,
    )
    from styles import inject_certifications_module_css  # type: ignore
    from utils.constants import CERTIFICATION_TYPES  # type: ignore
    from utils.formatting import fmt_date  # type: ignore

_MODULE = "employee_certifications"
_TABLE_KEY = "certifications_list"
_ALL_CERT_IDS_KEY = "_cert_page_all_ids"
_FILTER_FIELDS_ALL = ["employee_name", "cert_type", "status"]
_FILTER_FIELDS_EMP = ["cert_type", "status"]
_COLUMN_FILTER_SPECS_ALL: list[tuple[str, object]] = [
    ("employee_name", lambda r: str(r.get("employee_name") or "").strip() or "—"),
    ("cert_type", None),
    ("status", None),
]
_COLUMN_FILTER_SPECS_EMP: list[tuple[str, object]] = [
    ("cert_type", None),
    ("status", None),
]

_CERT_COLS_ALL = [0.35, 2.0, 1.4, 1.5, 1.6, 1.1, 1.1, 1.2, 0.9]
_CERT_HEADER_SPECS_ALL: list[tuple[str, str | None]] = [
    ("", None),
    ("EMPLOYEE", "employee_name"),
    ("TYPE", "cert_type"),
    ("NUMBER", None),
    ("ISSUING ORG", None),
    ("ISSUED", None),
    ("EXPIRES", None),
    ("STATUS", "status"),
    ("DOCUMENT", None),
]
_CERT_COLS_EMP = [0.35, 1.8, 1.6, 1.8, 1.2, 1.2, 1.2, 0.9]
_CERT_HEADER_SPECS_EMP: list[tuple[str, str | None]] = [
    ("", None),
    ("TYPE", "cert_type"),
    ("NUMBER", None),
    ("ISSUING ORG", None),
    ("ISSUED", None),
    ("EXPIRES", None),
    ("STATUS", "status"),
    ("DOCUMENT", None),
]


def _cert_upload_key(*, key_prefix: str, rk: str) -> str:
    return f"{key_prefix}cert_upload_{rk}"


def _resolve_saved_cert_id(cid: str, result: Any, row_id: str | None) -> str:
    saved_id = str(row_id or cid or "").strip()
    if saved_id and not is_demo_id(saved_id):
        return saved_id
    if isinstance(result, object) and getattr(result, "ok", False):
        data = getattr(result, "data", None)
        if isinstance(data, dict):
            new_id = str(data.get("id") or "").strip()
            if new_id and not is_demo_id(new_id):
                return new_id
    return ""


def _persist_certification_upload(
    *,
    cert_id: str,
    key_prefix: str,
    rk: str,
) -> tuple[bool, str]:
    upload_key = _cert_upload_key(key_prefix=key_prefix, rk=rk)
    uploaded_file = st.session_state.get(upload_key)
    if uploaded_file is None:
        return True, ""
    if not cert_id or is_demo_id(cert_id):
        return False, "Save the certification to Supabase before uploading a document."
    upload_result = upload_certification_attachment(
        cert_id,
        uploaded_file,
        uploaded_by=_current_user_id(),
    )
    if not upload_result.ok:
        return False, upload_result.error or "Could not upload certification document."
    st.session_state.pop(upload_key, None)
    return True, ""


def _cert_select_key(cert_id: str, *, prefix: str = "") -> str:
    return f"{prefix}certification_select_{cert_id}"


def _selected_id_key(*, prefix: str = "") -> str:
    return f"{prefix}selected_certification_id" if prefix else "selected_certification_id"


def _show_detail_key(*, prefix: str = "") -> str:
    return f"{prefix}show_certification_detail" if prefix else "show_certification_detail"


def _clear_certification_selection(cert_ids: list[str] | None = None, *, prefix: str = "") -> None:
    st.session_state[_selected_id_key(prefix=prefix)] = None
    st.session_state[_show_detail_key(prefix=prefix)] = False
    st.session_state.pop(_cert_pending_delete_key(prefix=prefix), None)
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


def _filter_certs(rows: list[dict], *, q: str, hide_employee: bool) -> list[dict]:
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
    specs = _COLUMN_FILTER_SPECS_EMP if hide_employee else _COLUMN_FILTER_SPECS_ALL
    return apply_column_filters(out, _TABLE_KEY, specs)


def _current_profile() -> dict:
    try:
        from app.auth import current_profile
    except ImportError:
        from auth import current_profile  # type: ignore
    prof = current_profile()
    return prof if isinstance(prof, dict) else {}


def _current_employee_id() -> str:
    return resolve_logged_in_employee_id(_current_profile())


def _can_manage_certifications() -> bool:
    return can_manage_employee_certifications(_effective_role())


def _can_delete_certifications() -> bool:
    return can_delete_employee_certifications(_effective_role())


def _cert_pending_delete_key(*, prefix: str = "") -> str:
    return f"{prefix}cert_pending_delete_id" if prefix else "cert_pending_delete_id"


def _execute_certification_delete(
    cert: dict,
    *,
    all_cert_ids: list[str],
    session_prefix: str,
) -> None:
    cid = str(cert.get("id") or "").strip()
    if not cid or is_demo_id(cid):
        st.error("This certification cannot be deleted.")
        return
    result = delete_employee_certification(cid)
    if not result.ok:
        st.error(result.error or "Could not delete certification.")
        return

    rk = record_session_key(cert, "id")
    st.session_state.pop(_cert_pending_delete_key(prefix=session_prefix), None)
    set_view_mode(_MODULE, rk)
    _clear_certification_selection(all_cert_ids, prefix=session_prefix)
    clear_certifications_cache()
    st.success("Certification deleted.")
    st.rerun()


def _render_certification_delete_actions(
    cert: dict,
    *,
    all_cert_ids: list[str],
    session_prefix: str = "",
) -> None:
    if not _can_delete_certifications():
        return

    cid = str(cert.get("id") or "").strip()
    if not cid:
        return

    rk = record_session_key(cert, "id")
    pending_key = _cert_pending_delete_key(prefix=session_prefix)
    pending_id = str(st.session_state.get(pending_key) or "").strip()

    st.markdown("---")
    if pending_id == cid:
        st.markdown(
            '<p class="ips-cert-delete-confirm-message">'
            "Are you sure you want to delete this certification?"
            "</p>",
            unsafe_allow_html=True,
        )
        confirm_col, cancel_col = st.columns(2, gap="small")
        with confirm_col:
            with danger_solid(f"cert_del_confirm_{session_prefix}_{rk}"):
                if st.button(
                    "Delete",
                    key=f"{session_prefix}cert_confirm_delete_{rk}",
                    use_container_width=True,
                ):
                    _execute_certification_delete(
                        cert,
                        all_cert_ids=all_cert_ids,
                        session_prefix=session_prefix,
                    )
        with cancel_col:
            if st.button(
                "Cancel",
                key=f"{session_prefix}cert_cancel_delete_{rk}",
                use_container_width=True,
            ):
                st.session_state.pop(pending_key, None)
                st.rerun()
    else:
        with danger_outline(f"cert_del_btn_{session_prefix}_{rk}"):
            if st.button(
                "Delete",
                key=f"{session_prefix}cert_delete_{rk}",
                use_container_width=False,
            ):
                st.session_state[pending_key] = cid
                st.rerun()


def _current_user_id() -> str | None:
    uid = str(_current_profile().get("id") or "").strip()
    return uid or None


def _effective_role() -> str:
    try:
        from app.auth import current_role, effective_role
    except ImportError:
        from auth import current_role, effective_role  # type: ignore
    return effective_role()


def _can_view_cert_attachment(cert: dict) -> bool:
    return can_view_certification_attachment(
        _effective_role(),
        cert,
        current_employee_id=_current_employee_id(),
    )


def _show_doc_key(cert_id: str, *, prefix: str = "") -> str:
    return f"{prefix}show_cert_doc_{cert_id}"


def _sanitize_cert_date_state(key: str, raw: object) -> None:
    if key not in st.session_state:
        coerced = coerce_date(raw)
        if coerced is not None:
            st.session_state[key] = coerced
        return
    val = st.session_state.get(key)
    if isinstance(val, date):
        return
    coerced = coerce_date(val if val not in (None, "") else raw)
    if coerced is not None:
        st.session_state[key] = coerced
    else:
        st.session_state.pop(key, None)


def _cert_attachment_file_name(cert: dict[str, Any]) -> str:
    fname = str(cert.get("attachment_file_name") or "").strip()
    if fname:
        return fname
    path = str(cert.get("attachment_path") or "").strip().replace("\\", "/")
    if path:
        return path.rsplit("/", 1)[-1]
    if str(cert.get("attachment_url") or "").strip():
        return "Attachment"
    return ""


def _attachment_view_label(cert: dict) -> str:
    mime = str(cert.get("attachment_mime_type") or "").lower()
    if mime.startswith("image/"):
        return "View Image"
    return "View Document"


def _render_attachment_preview(cert: dict, *, key_prefix: str = "") -> None:
    cid = str(cert.get("id") or "")
    has_attachment = cert_has_attachment(cert)
    if not _can_view_cert_attachment(cert):
        st.caption("You do not have permission to view this attachment.")
        return
    url = get_certification_attachment_url(cert)
    if not url:
        if has_attachment:
            st.warning("Attachment found but preview unavailable.")
        else:
            st.warning("Storage bucket not configured. Create certification-documents bucket in Supabase.")
        return

    mime = str(cert.get("attachment_mime_type") or "").lower()
    st.markdown('<div class="ips-attachment-preview">', unsafe_allow_html=True)
    if mime.startswith("image/"):
        st.image(url, use_container_width=True)
    elif mime == "application/pdf" or url.lower().endswith(".pdf"):
        st.markdown(
            f'<iframe src="{html.escape(url, quote=True)}" title="Certification PDF"></iframe>',
            unsafe_allow_html=True,
        )
        st.link_button("Open PDF", url, key=f"{key_prefix}cert_pdf_open_{cid}")
    else:
        st.link_button("Download file", url, key=f"{key_prefix}cert_file_open_{cid}")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_attachment_section(
    cert: dict,
    *,
    rk: str,
    key_prefix: str = "",
    edit_mode: bool = False,
) -> None:
    cid = str(cert.get("id") or "")
    has_attachment = cert_has_attachment(cert)
    fname = _cert_attachment_file_name(cert)
    uploaded_at = str(cert.get("attachment_uploaded_at") or "")[:19].replace("T", " ")

    st.markdown('<div class="ips-attachment-card">', unsafe_allow_html=True)

    if edit_mode:
        st.file_uploader(
            "Upload certification image or document",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            key=_cert_upload_key(key_prefix=key_prefix, rk=rk),
        )
        st.caption("Upload PNG, JPG, WEBP, or PDF. File is saved when you click Save Changes.")
        if has_attachment and fname:
            st.markdown(
                f'<p class="ips-attachment-file-name">Current file: {html.escape(fname)}</p>',
                unsafe_allow_html=True,
            )
    elif has_attachment:
        if fname:
            st.markdown(
                f'<p class="ips-attachment-file-name">{html.escape(fname)}</p>',
                unsafe_allow_html=True,
            )
        if uploaded_at:
            st.caption(f"Uploaded {uploaded_at}")
        if not _can_view_cert_attachment(cert):
            st.caption("Attachment on file. View restricted for your role.")
        else:
            url = get_certification_attachment_url(cert)
            toggle_key = _show_doc_key(cid, prefix=key_prefix)
            preview_col, download_col = st.columns(2, gap="small")
            with preview_col:
                if st.button(
                    "Preview",
                    key=f"{key_prefix}cert_preview_{cid}",
                    use_container_width=True,
                ):
                    st.session_state[toggle_key] = not st.session_state.get(toggle_key, False)
                    st.rerun()
            with download_col:
                if url:
                    st.link_button(
                        "Download",
                        url,
                        key=f"{key_prefix}cert_download_{cid}",
                        use_container_width=True,
                    )
                else:
                    st.caption("Download unavailable")
            if not url:
                st.warning("Attachment found but preview unavailable.")
            elif st.session_state.get(toggle_key, False):
                _render_attachment_preview(cert, key_prefix=key_prefix)
    else:
        st.caption("No certification document uploaded.")

    st.markdown("</div>", unsafe_allow_html=True)


def _employee_options() -> tuple[list[str], dict[str, str]]:
    employees = load_employees()
    emp_opts = {str(e.get("name") or ""): str(e.get("id") or "") for e in employees if str(e.get("id") or "").strip()}
    names = [n for n in emp_opts if n]
    return names, emp_opts


def _cert_document_button_label(cert: dict[str, Any]) -> str:
    fname = str(cert.get("attachment_file_name") or "").strip()
    if not fname:
        path = str(cert.get("attachment_path") or "").strip().replace("\\", "/")
        fname = path.rsplit("/", 1)[-1] if path else ""
    if not fname:
        return "View certificate"
    if len(fname) > 28:
        return f"{fname[:25]}..."
    return fname


def _render_cert_document_cell(cert: dict[str, Any], *, session_prefix: str = "") -> None:
    cid = str(cert.get("id") or "").strip()
    if not cert_has_attachment(cert):
        st.markdown('<span class="ips-cert-doc-empty">—</span>', unsafe_allow_html=True)
        return

    fname = _cert_attachment_file_name(cert)
    display_name = fname if len(fname) <= 22 else f"{fname[:19]}..."
    st.markdown(
        f'<div class="ips-cert-doc-name" title="{html.escape(fname, quote=True)}">'
        f"{html.escape(display_name)}"
        f"</div>",
        unsafe_allow_html=True,
    )
    if not _can_view_cert_attachment(cert):
        st.markdown('<span class="ips-cert-doc-empty">Restricted</span>', unsafe_allow_html=True)
        return

    url = get_certification_attachment_url(cert)
    if not url:
        st.markdown(
            '<span class="ips-cert-doc-empty">Preview unavailable</span>',
            unsafe_allow_html=True,
        )
        return

    action_col1, action_col2 = st.columns(2, gap="small")
    toggle_key = _show_doc_key(cid, prefix=session_prefix)
    with action_col1:
        if st.button(
            "Preview",
            key=f"{session_prefix}cert_doc_preview_{cid}",
            use_container_width=True,
        ):
            st.session_state[_selected_id_key(prefix=session_prefix)] = cid
            st.session_state[_show_detail_key(prefix=session_prefix)] = True
            st.session_state[toggle_key] = True
            st.rerun()
    with action_col2:
        st.link_button(
            "Download",
            url,
            key=f"{session_prefix}cert_doc_open_{cid}",
            use_container_width=True,
            help="Download certification document",
        )


def _render_certifications_table(
    certifications: list[dict],
    *,
    hide_employee: bool,
    table_wrap_key: str,
    session_prefix: str = "",
    filter_options: dict[str, list[str]],
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
    header_specs = _CERT_HEADER_SPECS_EMP if hide_employee else _CERT_HEADER_SPECS_ALL

    with st.container(key=table_wrap_key):
        st.markdown('<div class="ips-certifications-table-wrap">', unsafe_allow_html=True)

        header_cols = st.columns(col_ratios, gap="small", vertical_alignment="center")
        for col, (label, field) in zip(header_cols, header_specs):
            with col:
                if field:
                    render_table_header_cell(
                        label,
                        table_key=_TABLE_KEY,
                        filter_field=field,
                        filter_options=filter_options.get(field, []),
                        base_class="ips-certifications-header-row ips-certifications-cell",
                    )
                else:
                    render_table_header_cell(
                        label,
                        base_class="ips-certifications-header-row ips-certifications-cell",
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
            with cols[col_idx + 6]:
                _render_cert_document_cell(cert, session_prefix=session_prefix)

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
    _sanitize_cert_date_state(f"cert_edit_issue_{rk}", cert.get("issue_date"))
    _sanitize_cert_date_state(f"cert_edit_expiration_{rk}", cert.get("expiration_date"))
    st.session_state[f"cert_edit_notes_{rk}"] = str(cert.get("notes") or "")


def _render_cert_edit_form(
    cert: dict,
    employee_names: list[str],
    emp_opts: dict[str, str],
    *,
    key_prefix: str = "",
    lock_employee_id: str = "",
) -> None:
    rk = record_session_key(cert, "id")
    cid = str(cert.get("id") or "")
    locked_eid = str(lock_employee_id or cert.get("employee_id") or "").strip()
    if f"cert_edit_type_{rk}" not in st.session_state:
        _seed_cert_edit_form(cert, employee_names, emp_opts)

    issue_key = f"cert_edit_issue_{rk}"
    exp_key = f"cert_edit_expiration_{rk}"
    _sanitize_cert_date_state(issue_key, cert.get("issue_date"))
    _sanitize_cert_date_state(exp_key, cert.get("expiration_date"))
    issue_date_value = coerce_date(st.session_state.get(issue_key) or cert.get("issue_date"))
    expiration_date_value = coerce_date(st.session_state.get(exp_key) or cert.get("expiration_date"))

    render_edit_form_header("Edit Certification")
    ec1, ec2 = st.columns(2)
    with ec1:
        if lock_employee_id:
            locked_name = next(
                (n for n, eid in emp_opts.items() if eid == locked_eid),
                str(cert.get("employee_name") or "Employee"),
            )
            st.text_input(
                "Employee",
                value=locked_name,
                disabled=True,
                key=f"cert_edit_emp_locked_{rk}",
            )
        else:
            st.selectbox("Employee", employee_names, key=f"cert_edit_emp_{rk}")
        st.selectbox("Certification Type", CERTIFICATION_TYPES, key=f"cert_edit_type_{rk}")
        st.text_input("Certification Number", key=f"cert_edit_num_{rk}")
        st.text_input("Issuing Organization", key=f"cert_edit_issuer_{rk}")
    with ec2:
        st.date_input(
            "Issue Date",
            value=issue_date_value if issue_date_value is not None else date.today(),
            key=issue_key,
        )
        st.date_input(
            "Expiration Date",
            value=expiration_date_value if expiration_date_value is not None else date.today(),
            key=exp_key,
        )
    st.text_area("Notes", key=f"cert_edit_notes_{rk}", height=80)
    _render_attachment_section(cert, rk=rk, key_prefix=key_prefix, edit_mode=True)

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
        if lock_employee_id:
            resolved_employee_id = locked_eid
        else:
            emp_name = st.session_state.get(f"cert_edit_emp_{rk}")
            resolved_employee_id = emp_opts.get(str(emp_name or ""), str(cert.get("employee_id") or ""))
        ui = {
            "employee_id": resolved_employee_id,
            "cert_type": st.session_state.get(f"cert_edit_type_{rk}"),
            "cert_number": st.session_state.get(f"cert_edit_num_{rk}"),
            "issuer": st.session_state.get(f"cert_edit_issuer_{rk}"),
            "issue_date": st.session_state.get(issue_key),
            "expiration_date": st.session_state.get(exp_key),
            "notes": st.session_state.get(f"cert_edit_notes_{rk}"),
        }
        row_id = None if is_demo_id(cid) else cid
        if row_id:
            result = update_employee_certification(row_id, ui)
        else:
            result = create_employee_certification(ui)
        if not result.ok:
            st.error(result.error or "Could not save certification.")
            return

        saved_id = _resolve_saved_cert_id(cid, result, row_id)
        upload_ok, upload_msg = _persist_certification_upload(
            cert_id=saved_id,
            key_prefix=key_prefix,
            rk=rk,
        )
        if not upload_ok:
            st.error(upload_msg)
            return

        clear_certifications_cache()
        set_view_mode(_MODULE, rk)
        st.success("Certification saved.")
        st.rerun()


def _render_cert_detail_tabs(cert: dict, *, key_prefix: str = "") -> None:
    emp = get_employee(str(cert.get("employee_id") or ""))
    status = str(cert.get("status") or "")
    rk = record_session_key(cert, "id")

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
            f"{detail_field_html('Employee', cert.get('employee_name'))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Certification", overview_html), unsafe_allow_html=True)
        st.markdown("**Attachment**")
        _render_attachment_section(cert, rk=rk, key_prefix=key_prefix, edit_mode=False)

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
        _render_attachment_section(cert, rk=rk, key_prefix=key_prefix, edit_mode=False)

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
    lock_employee_id: str = "",
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
    if _can_manage_certifications():
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
        _render_cert_edit_form(
            cert,
            employee_names,
            emp_opts,
            key_prefix=session_prefix,
            lock_employee_id=lock_employee_id,
        )
    else:
        _render_cert_detail_tabs(cert, key_prefix=session_prefix)
        _render_certification_delete_actions(
            cert,
            all_cert_ids=all_cert_ids,
            session_prefix=session_prefix,
        )


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
    filter_options: dict[str, list[str]] | None = None,
    lock_employee_id: str = "",
) -> list[str]:
    all_cert_ids = _render_certifications_table(
        certifications,
        hide_employee=hide_employee,
        table_wrap_key=table_wrap_key,
        session_prefix=session_prefix,
        filter_options=filter_options or {},
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
                    lock_employee_id=lock_employee_id,
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
    st.file_uploader(
        "Upload certification image or document",
        type=["png", "jpg", "jpeg", "webp", "pdf"],
        key=_cert_upload_key(key_prefix="", rk="new"),
    )
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
                new_id = _resolve_saved_cert_id("", result, None)
                upload_ok, upload_msg = _persist_certification_upload(
                    cert_id=new_id,
                    key_prefix="",
                    rk="new",
                )
                if not upload_ok:
                    st.warning(upload_msg or "Certification saved, but attachment upload failed.")
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


def _cert_add_open_key(*, session_prefix: str) -> str:
    return f"{session_prefix}cert_add_open"


def _render_add_certification_form(
    default_employee_id: str,
    *,
    session_prefix: str = "emp_cert_",
    lock_employee: bool = False,
    employee_label: str = "",
) -> None:
    prefix = session_prefix
    rk = "new"

    with st.container(border=True):
        st.markdown("### New Certification")
        if lock_employee and employee_label:
            st.text_input(
                "Employee",
                value=employee_label,
                disabled=True,
                key=f"{prefix}new_emp_label",
            )
        c1, c2 = st.columns(2)
        with c1:
            if not lock_employee:
                employee_names, emp_opts = _employee_options()
                default_name = next(
                    (n for n, eid in emp_opts.items() if eid == default_employee_id),
                    employee_names[0] if employee_names else "",
                )
                idx = employee_names.index(default_name) if default_name in employee_names else 0
                st.selectbox("Employee", employee_names, index=idx, key=f"{prefix}new_emp")
            st.selectbox("Certification Type", CERTIFICATION_TYPES, key=f"{prefix}new_type")
            st.text_input("Certification Number", key=f"{prefix}new_number")
            st.text_input("Issuing Organization", key=f"{prefix}new_issuer")
        with c2:
            st.date_input("Issue Date", key=f"{prefix}new_issue")
            st.date_input("Expiration Date", key=f"{prefix}new_exp")
        st.file_uploader(
            "Upload certification image or document",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            key=_cert_upload_key(key_prefix=prefix, rk=rk),
        )
        st.text_area("Notes", key=f"{prefix}new_notes", height=80)

        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button(
                "Save Certification",
                key=f"{prefix}save_new",
                type="primary",
                use_container_width=True,
            ):
                if lock_employee:
                    resolved_employee_id = str(default_employee_id or "").strip()
                else:
                    employee_names, emp_opts = _employee_options()
                    picked = st.session_state.get(f"{prefix}new_emp")
                    resolved_employee_id = emp_opts.get(str(picked or ""), default_employee_id)
                ui = {
                    "employee_id": resolved_employee_id,
                    "cert_type": st.session_state.get(f"{prefix}new_type"),
                    "cert_number": st.session_state.get(f"{prefix}new_number"),
                    "issuer": st.session_state.get(f"{prefix}new_issuer"),
                    "issue_date": st.session_state.get(f"{prefix}new_issue"),
                    "expiration_date": st.session_state.get(f"{prefix}new_exp"),
                    "notes": st.session_state.get(f"{prefix}new_notes"),
                }
                result = create_employee_certification(ui)
                if result.ok:
                    new_id = _resolve_saved_cert_id("", result, None)
                    upload_ok, upload_msg = _persist_certification_upload(
                        cert_id=new_id,
                        key_prefix=prefix,
                        rk=rk,
                    )
                    if not upload_ok:
                        st.warning(upload_msg or "Certification saved, but attachment upload failed.")
                    clear_certifications_cache()
                    st.session_state.pop(_cert_add_open_key(session_prefix=prefix), None)
                    st.success("Certification saved.")
                    st.rerun()
                else:
                    st.error(result.error or "Could not save certification.")
        with bc2:
            if st.button("Cancel", key=f"{prefix}cancel_new", use_container_width=True):
                st.session_state.pop(_cert_add_open_key(session_prefix=prefix), None)
                st.rerun()


def render_employee_detail_certifications_tab(
    employee_id: str,
    *,
    employee: dict[str, Any] | None = None,
    session_prefix: str = "emp_cert_",
) -> None:
    """Full certification management inside Users > User Details > Certifications."""
    inject_certifications_module_css()
    eid = str(employee_id or "").strip()
    if not eid:
        st.caption("No employee selected.")
        return

    certs = load_certifications(eid)
    expired_n, expiring_n = certification_alerts(certs)
    if expired_n or expiring_n:
        parts = []
        if expired_n:
            parts.append(f"{expired_n} expired")
        if expiring_n:
            parts.append(f"{expiring_n} expiring within 30 days")
        st.markdown(
            f'<p class="ips-alert-banner">⚠ Certification alerts: {html.escape(" · ".join(parts))}</p>',
            unsafe_allow_html=True,
        )

    if _can_manage_certifications():
        if st.button(
            "+ Add Certification",
            key=f"{session_prefix}add_btn",
            type="primary",
        ):
            st.session_state[_cert_add_open_key(session_prefix=session_prefix)] = True
            st.rerun()
        if st.session_state.get(_cert_add_open_key(session_prefix=session_prefix)):
            employee_label = str((employee or {}).get("name") or "").strip()
            _render_add_certification_form(
                eid,
                session_prefix=session_prefix,
                lock_employee=True,
                employee_label=employee_label,
            )

    if not certs:
        if _can_manage_certifications():
            st.caption("No certifications on file yet. Use Add Certification above.")
        else:
            st.caption("No certifications on file.")
        return

    filter_options = build_filter_options(certs, _COLUMN_FILTER_SPECS_EMP)
    render_certifications_table_block(
        certs,
        hide_employee=True,
        table_wrap_key="emp_certifications_table_wrap",
        session_prefix=session_prefix,
        inline_detail=True,
        filter_options=filter_options,
        lock_employee_id=eid,
    )


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("employee_certifications"):
        return

    inject_certifications_module_css()

    manage_all = _can_manage_certifications()
    viewer_eid = _current_employee_id()

    if not manage_all and not viewer_eid:
        render_page_brand_header(
            "My Certifications",
            "Your credentials, expirations, and compliance status.",
        )
        st.warning(
            "Your login is not linked to an employee record yet. "
            "Contact an administrator to view your certifications."
        )
        return

    if manage_all:
        employee_names, emp_opts = _employee_options()
        filter_names = ["All Employees", *employee_names]
        active_id = str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or "")
        default_filter = next(
            (n for n, eid in emp_opts.items() if eid == active_id),
            "All Employees",
        )
        if default_filter not in filter_names:
            default_filter = "All Employees"

        def _cert_add() -> None:
            if st.button("+ Add Certification", key="cert_add", type="primary", use_container_width=True):
                st.session_state["ips_cert_form_open"] = True

        render_page_brand_header(
            "Employee Certifications",
            "Track credentials, expirations, and compliance.",
            actions=[_cert_add],
        )
        scope_certs = load_all_certifications()
    else:
        employee_names, emp_opts = [], {}
        st.session_state[ACTIVE_EMPLOYEE_KEY] = viewer_eid
        render_page_brand_header(
            "My Certifications",
            "Your credentials, expirations, and compliance status.",
        )
        scope_certs = load_certifications(viewer_eid)

    expired_n, expiring_n = certification_alerts(scope_certs)
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
        if manage_all:
            c1, c2, c3 = st.columns([1.2, 5, 0.6])
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
                if st.button("Clear", key="cert_clear", use_container_width=True):
                    eid_now = str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or "")
                    filter_fields = _FILTER_FIELDS_EMP if eid_now else _FILTER_FIELDS_ALL
                    clear_table_filters(
                        _TABLE_KEY,
                        filter_fields,
                        extra_keys=["cert_search", "cert_emp_filter", ACTIVE_EMPLOYEE_KEY],
                    )
                    st.session_state["cert_emp_filter"] = "All Employees"
                    st.session_state[ACTIVE_EMPLOYEE_KEY] = ""
                    _clear_certification_selection(st.session_state.get(_ALL_CERT_IDS_KEY))
                    st.rerun()
        else:
            c1, c2 = st.columns([5.6, 0.6])
            with c1:
                st.text_input(
                    "Search",
                    placeholder="Search type or number...",
                    key="cert_search",
                    label_visibility="collapsed",
                )
            with c2:
                if st.button("Clear", key="cert_clear", use_container_width=True):
                    clear_table_filters(
                        _TABLE_KEY,
                        _FILTER_FIELDS_EMP,
                        extra_keys=["cert_search"],
                    )
                    _clear_certification_selection(st.session_state.get(_ALL_CERT_IDS_KEY))
                    st.rerun()

    layout_filter_bar(_filters)

    eid = str(st.session_state.get(ACTIVE_EMPLOYEE_KEY) or "")
    hide_employee = bool(eid) or not manage_all
    if manage_all:
        scope = load_certifications(eid) if eid else scope_certs
    else:
        scope = [
            c
            for c in scope_certs
            if certification_visible_to_user(
                c,
                role=_effective_role(),
                viewer_employee_id=viewer_eid,
            )
        ]
    filter_specs = _COLUMN_FILTER_SPECS_EMP if hide_employee else _COLUMN_FILTER_SPECS_ALL
    filter_options = build_filter_options(scope, filter_specs)
    filtered = _filter_certs(
        scope,
        q=str(st.session_state.get("cert_search") or "").strip(),
        hide_employee=hide_employee,
    )

    st.caption(f"{len(filtered)} certification(s)")

    if manage_all and st.session_state.get("ips_cert_form_open"):
        _show_add_certification_dialog(eid)

    all_cert_ids = render_certifications_table_block(
        filtered,
        hide_employee=hide_employee,
        table_wrap_key="certifications_table_wrap",
        inline_detail=False,
        filter_options=filter_options,
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
