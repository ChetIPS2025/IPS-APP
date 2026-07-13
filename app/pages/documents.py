"""Central Documents hub (Phase 2D)."""

from __future__ import annotations

import html

import streamlit as st

from app.auth import current_profile, current_role, effective_role
from app.components.clickable_table import render_clickable_table
from app.components.headers import render_page_brand_header
from app.components.layout import render_filter_bar as layout_filter_bar
from app.components.table_filters import (
    apply_column_filters,
    build_filter_options,
    clear_table_filters,
    render_table_header_cell,
)
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
)
from app.pages._core._crud import apply_persist_feedback, is_demo_id
from app.pages._core._data import (
    document_link_ref_options,
    load_documents_hub,
    lookup_options,
    persist_document,
)
from app.pages._core._session import select_key
from app.styles import inject_documents_module_css
from app.utils.constants import DOCUMENT_LINK_MODULES
from app.utils.formatting import fmt_date
from app.utils.permissions import can_view_hr_documents, normalize_role
_SEL = select_key("documents")
_TABLE_KEY = "documents_list"
MODULE = "documents"
MODAL_KEY = "ips_documents_detail_modal_id"
CACHE_KEY = "_ips_documents_modal_by_id"

_LINK_MODULES = [m for m in DOCUMENT_LINK_MODULES if m != "All Modules"]

_DOCUMENT_TABS = [
    "Overview",
    "Linked Record",
    "Access",
    "Expiration",
    "Notes",
    "Activity",
]
_FILTER_FIELDS = ["doc_type", "linked_module", "access"]
_COLUMN_FILTER_SPECS: list[tuple[str, object]] = [
    ("doc_type", None),
    ("linked_module", None),
    ("access", lambda r: _doc_access_value(r)),
]
_DOC_FILTER_COLS = [2.5, 1, 1, 1.5, 1.3, 0.9, 0.9, 1]
_DOC_FILTER_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("FILE", None),
    ("TYPE", "doc_type"),
    ("MODULE", "linked_module"),
    ("LINKED TO", None),
    ("UPLOADED BY", None),
    ("DATE", None),
    ("EXPIRES", None),
    ("ACCESS", "access"),
]


def _doc_access_value(row: dict) -> str:
    return "RESTRICTED" if row.get("is_restricted") else "Standard"


def _filter_docs(rows: list[dict], *, q: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            d
            for d in out
            if ql in str(d.get("file_name", "")).lower()
            or ql in str(d.get("linked_ref", "")).lower()
            or ql in str(d.get("doc_type", "")).lower()
        ]
    return apply_column_filters(out, _TABLE_KEY, _COLUMN_FILTER_SPECS)


def _render_documents_column_filters(*, filter_options: dict[str, list[str]]) -> None:
    header_cols = st.columns(_DOC_FILTER_COLS, gap="small", vertical_alignment="center")
    for col, (label, field) in zip(header_cols, _DOC_FILTER_HEADER_SPECS):
        with col:
            if field:
                render_table_header_cell(
                    label,
                    table_key=_TABLE_KEY,
                    filter_field=field,
                    filter_options=filter_options.get(field, []),
                    base_class="ips-documents-header-row ips-documents-cell",
                )
            else:
                render_table_header_cell(
                    label,
                    base_class="ips-documents-header-row ips-documents-cell",
                )


def _upload_file_name() -> str:
    up = st.session_state.get("doc_hub_new_file")
    if up is not None and hasattr(up, "name"):
        return str(up.name)
    return "upload.pdf"


def _render_upload_form(*, hr_ok: bool) -> None:
    with st.expander("Upload document", expanded=True):
        u1, u2 = st.columns(2)
        with u1:
            st.selectbox("Document type", lookup_options("document_types"), key="doc_hub_new_type")
            st.selectbox("Link to module", _LINK_MODULES, key="doc_hub_new_module")
            refs = document_link_ref_options(str(st.session_state.get("doc_hub_new_module") or ""))
            if refs:
                st.selectbox("Linked record", refs, key="doc_hub_new_ref")
            else:
                st.text_input("Linked record", key="doc_hub_new_ref", placeholder="Job #, employee name, etc.")
        with u2:
            st.file_uploader("File", key="doc_hub_new_file")
            st.date_input("Expiration (optional)", key="doc_hub_new_exp", value=None)
            st.checkbox("Restricted / private", key="doc_hub_new_restricted", disabled=not hr_ok)
        if st.button("Save upload", key="doc_hub_save", type="primary"):
            prof = current_profile() or {}
            ui = {
                "file_name": _upload_file_name(),
                "doc_type": st.session_state.get("doc_hub_new_type"),
                "linked_module": st.session_state.get("doc_hub_new_module"),
                "linked_ref": st.session_state.get("doc_hub_new_ref"),
                "uploaded_by": str(prof.get("full_name") or prof.get("email") or "User"),
                "expiration_date": st.session_state.get("doc_hub_new_exp"),
                "is_restricted": st.session_state.get("doc_hub_new_restricted"),
            }
            ok, msg = persist_document(ui)
            if apply_persist_feedback(ok, msg, clear_keys=("ips_doc_hub_form",)):
                st.rerun()


def _clear_document_modal() -> None:
    clear_record_modal(
        table_key=_TABLE_KEY,
        session_select_key=_SEL,
        modal_key=MODAL_KEY,
        module=MODULE,
    )


def _open_document_modal(document_id: str, document: dict | None = None) -> None:
    open_record_modal(
        document_id,
        document,
        session_select_key=_SEL,
        modal_key=MODAL_KEY,
        module=MODULE,
        id_fields=("id", "file_name"),
    )


def _documents_display_cell(field: str, row: dict) -> str:
    if field == "access":
        return _doc_access_value(row)
    if field in ("upload_date", "expiration_date"):
        return fmt_date(row.get(field)) if row.get(field) else "—"
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def _access_label(doc: dict) -> str:
    return _doc_access_value(doc) if doc.get("is_restricted") else "Standard access"


def _seed_document_edit_form(doc: dict, *, hr_ok: bool) -> None:
    rk = record_session_key(doc, "id")
    mod = str(doc.get("linked_module") or "")
    if mod in _LINK_MODULES:
        st.session_state[f"doc_edit_mod_{rk}"] = mod
    elif _LINK_MODULES:
        st.session_state[f"doc_edit_mod_{rk}"] = _LINK_MODULES[0]
    type_opts = lookup_options("document_types")
    dtype = str(doc.get("doc_type") or "")
    st.session_state[f"doc_edit_type_{rk}"] = dtype if dtype in type_opts else (type_opts[0] if type_opts else dtype)
    st.session_state[f"doc_edit_ref_{rk}"] = str(doc.get("linked_ref") or "")
    exp = doc.get("expiration_date")
    if exp:
        try:
            from datetime import date

            if isinstance(exp, date):
                st.session_state[f"doc_edit_exp_{rk}"] = exp
            else:
                st.session_state[f"doc_edit_exp_{rk}"] = date.fromisoformat(str(exp)[:10])
        except ValueError:
            st.session_state[f"doc_edit_exp_{rk}"] = None
    else:
        st.session_state[f"doc_edit_exp_{rk}"] = None
    st.session_state[f"doc_edit_rest_{rk}"] = bool(doc.get("is_restricted")) and hr_ok


def _restricted_pill_html(restricted: bool) -> str:
    if restricted:
        return '<span class="ips-doc-restricted-pill">Restricted</span>'
    return html.escape("No")


def _render_document_detail_tabs(doc: dict) -> None:
    restricted = bool(doc.get("is_restricted"))
    access = _access_label(doc)
    file_name = safe_value(doc.get("file_name"))
    doc_type = safe_value(doc.get("doc_type"))
    linked_module = safe_value(doc.get("linked_module"))
    linked_ref = safe_value(doc.get("linked_ref"))

    (
        tab_overview,
        tab_linked,
        tab_access,
        tab_expiration,
        tab_notes,
        tab_activity,
    ) = st.tabs(_DOCUMENT_TABS)

    with tab_overview:
        overview_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('File Name', file_name)}"
            f"{detail_field_html('Document Type', doc_type)}"
            f"{detail_field_html('Uploaded By', doc.get('uploaded_by'))}"
            f"{detail_field_html('Upload Date', fmt_date(doc.get('upload_date')))}"
            f"{detail_field_html('Access', access)}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Overview", overview_html), unsafe_allow_html=True)
        st.button("Download", key=f"doc_dl_{doc.get('id')}", type="primary")

    with tab_linked:
        linked_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Module', linked_module)}"
            f"{detail_field_html('Linked Record', linked_ref)}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Linked Record", linked_html), unsafe_allow_html=True)

    with tab_access:
        access_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Access Level', access)}"
            f"{detail_field_html('Restricted', 'Yes' if restricted else 'No', html_value=_restricted_pill_html(restricted))}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Access", access_html), unsafe_allow_html=True)

    with tab_expiration:
        exp_html = (
            f'<div class="ips-detail-grid">'
            f"{detail_field_html('Expiration Date', fmt_date(doc.get('expiration_date')) if doc.get('expiration_date') else '—')}"
            f"</div>"
        )
        st.markdown(dialog_card_html("Expiration", exp_html), unsafe_allow_html=True)

    with tab_notes:
        notes_text = safe_value(doc.get("notes"), "No notes entered.")
        notes_html = (
            f'<p style="margin:0;font-size:0.875rem;color:#0f172a;line-height:1.5;white-space:pre-wrap;">'
            f"{html.escape(notes_text)}"
            f"</p>"
        )
        st.markdown(dialog_card_html("Notes", notes_html), unsafe_allow_html=True)

    with tab_activity:
        placeholder_html("Document activity history will load from Supabase in a later phase.")


def _render_document_edit_form(doc: dict, *, hr_ok: bool) -> None:
    rk = record_session_key(doc, "id")
    did = str(doc.get("id") or "")
    if f"doc_edit_type_{rk}" not in st.session_state:
        _seed_document_edit_form(doc, hr_ok=hr_ok)

    render_edit_form_header("Edit Document")
    if is_demo_id(did):
        st.caption("Demo records cannot be saved to the database.")

    ec1, ec2 = st.columns(2, gap="medium")
    with ec1:
        st.selectbox("Document type", lookup_options("document_types"), key=f"doc_edit_type_{rk}")
        st.selectbox("Module", _LINK_MODULES, key=f"doc_edit_mod_{rk}")
        refs = document_link_ref_options(str(st.session_state.get(f"doc_edit_mod_{rk}") or ""))
        if refs:
            st.selectbox("Linked record", refs, key=f"doc_edit_ref_{rk}")
        else:
            st.text_input("Linked record", key=f"doc_edit_ref_{rk}")
    with ec2:
        st.date_input("Expiration", key=f"doc_edit_exp_{rk}", value=None)
        st.checkbox("Restricted", key=f"doc_edit_rest_{rk}", disabled=not hr_ok)

    cancelled, saved = render_save_cancel_actions(
        module=MODULE,
        record_key=rk,
        cancel_key=f"doc_modal_cancel_{rk}",
        save_key=f"doc_modal_save_{rk}",
    )
    if cancelled:
        st.rerun()
    if saved and not is_demo_id(did):
        ok, msg = persist_document(
            {
                "file_name": doc.get("file_name"),
                "doc_type": st.session_state.get(f"doc_edit_type_{rk}"),
                "linked_module": st.session_state.get(f"doc_edit_mod_{rk}"),
                "linked_ref": st.session_state.get(f"doc_edit_ref_{rk}"),
                "uploaded_by": doc.get("uploaded_by"),
                "expiration_date": st.session_state.get(f"doc_edit_exp_{rk}"),
                "is_restricted": st.session_state.get(f"doc_edit_rest_{rk}"),
            },
            row_id=did or None,
        )
        if ok:
            set_view_mode(MODULE, rk)
            st.success(msg or "Document saved.")
            st.rerun()
        st.error(msg or "Could not save document.")


def render_document_detail_dialog(doc: dict, *, hr_ok: bool) -> None:
    rk = record_session_key(doc, "id", "file_name")
    file_name = safe_value(doc.get("file_name"))
    doc_type = safe_value(doc.get("doc_type"))
    linked_module = safe_value(doc.get("linked_module"))
    linked_ref = safe_value(doc.get("linked_ref"))

    render_modal_shell()
    render_modal_header(
        title=file_name,
        subtitle=doc_type,
        status=_access_label(doc) if doc.get("is_restricted") else None,
    )
    render_modal_edit_button(
        module=MODULE,
        record_key=rk,
        key_prefix=f"doc_modal_{rk}",
    )
    render_modal_meta_grid(
        [
            ("Type", doc_type),
            ("Module", linked_module),
            ("Linked To", linked_ref),
            ("Uploaded", fmt_date(doc.get("upload_date"))),
        ]
    )

    if is_edit_mode(MODULE, rk):
        _render_document_edit_form(doc, hr_ok=hr_ok)
    else:
        _render_document_detail_tabs(doc)


@st.dialog("Document Details", width="large", on_dismiss=_clear_document_modal)
def _show_document_modal() -> None:
    doc = get_modal_record(
        cache_key=CACHE_KEY,
        modal_key=MODAL_KEY,
        session_select_key=_SEL,
    )
    if not doc:
        render_missing_record(_clear_document_modal, close_key="doc_modal_missing_close")
        return
    role_norm = normalize_role(effective_role())
    hr_ok = can_view_hr_documents(role_norm)
    render_document_detail_dialog(doc, hr_ok=hr_ok)


def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("documents"):
        return
    inject_documents_module_css()
    st.markdown('<span class="ips-documents-page ips-page-shell-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
    role_norm = normalize_role(effective_role())
    hr_ok = can_view_hr_documents(role_norm)
    all_docs = load_documents_hub(role=role_norm)

    def _doc_upload() -> None:
        if st.button("+ Upload Document", key="doc_hub_upload", type="primary", use_container_width=True):
            st.session_state["ips_doc_hub_form"] = True

    render_page_brand_header(
        "Documents",
        "Central document hub — link files to jobs, estimates, assets, employees, certifications, inventory, and updates.",
        actions=[_doc_upload],
    )

    if not hr_ok:
        st.markdown(
            '<p class="ips-alert-banner">Restricted documents are hidden. Administrators see all files.</p>',
            unsafe_allow_html=True,
        )

    def _filters() -> None:
        c1, c2 = st.columns([5, 0.6])
        with c1:
            st.text_input("Search", placeholder="Search file or linked record…", key="doc_hub_search", label_visibility="collapsed")
        with c2:
            if st.button("Clear", key="doc_hub_clear", use_container_width=True):
                clear_table_filters(_TABLE_KEY, _FILTER_FIELDS, extra_keys=["doc_hub_search"])
                st.rerun()

    layout_filter_bar(_filters)

    filter_options = build_filter_options(all_docs, _COLUMN_FILTER_SPECS)
    filtered = _filter_docs(
        all_docs,
        q=str(st.session_state.get("doc_hub_search") or "").strip(),
    )

    st.caption(f"{len(filtered)} document(s)")

    if st.session_state.get("ips_doc_hub_form"):
        _render_upload_form(hr_ok=hr_ok)

    build_modal_cache(filtered, cache_key=CACHE_KEY)

    _render_documents_column_filters(filter_options=filter_options)

    render_clickable_table(
        filtered,
        [
            ("file_name", "FILE"),
            ("doc_type", "TYPE"),
            ("linked_module", "MODULE"),
            ("linked_ref", "LINKED TO"),
            ("uploaded_by", "UPLOADED BY"),
            ("upload_date", "DATE"),
            ("expiration_date", "EXPIRES"),
            ("access", "ACCESS"),
        ],
        _TABLE_KEY,
        row_id_key="id",
        session_select_key=_SEL,
        format_cell=_documents_display_cell,
        click_caption="Click a row to open details.",
        on_row_selected=_open_document_modal,
    )

    show_modal_if_pending(MODAL_KEY, _show_document_modal)
