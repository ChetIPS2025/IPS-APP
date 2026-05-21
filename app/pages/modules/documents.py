"""Central Documents hub (Phase 2D)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.modals import render_record_detail_dialog
    from app.components.tables import render_clickable_table, render_data_table
    from app.pages.modules._crud import apply_persist_feedback, is_demo_id
    from app.pages.modules._data import (
        document_link_ref_options,
        load_documents_hub,
        lookup_options,
        persist_document,
    )
    from app.pages.modules._session import select_key
    from app.utils.constants import DOCUMENT_LINK_MODULES
    from app.utils.formatting import fmt_date
    from app.utils.permissions import can_view_hr_documents, normalize_role
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.modals import render_record_detail_dialog  # type: ignore
    from components.tables import render_clickable_table, render_data_table  # type: ignore
    from pages.modules._crud import apply_persist_feedback, is_demo_id  # type: ignore
    from pages.modules._data import (  # type: ignore
        document_link_ref_options,
        load_documents_hub,
        lookup_options,
        persist_document,
    )
    from pages.modules._session import select_key  # type: ignore
    from utils.constants import DOCUMENT_LINK_MODULES  # type: ignore
    from utils.formatting import fmt_date  # type: ignore
    from utils.permissions import can_view_hr_documents, normalize_role  # type: ignore

_SEL = select_key("documents")
_LINK_MODULES = [m for m in DOCUMENT_LINK_MODULES if m != "All Modules"]


def _filter_docs(rows: list[dict], *, q: str, module: str, doc_type: str) -> list[dict]:
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
    if module and module != "All Modules":
        out = [d for d in out if str(d.get("linked_module", "")) == module]
    if doc_type and doc_type != "All Types":
        out = [d for d in out if str(d.get("doc_type", "")) == doc_type]
    return out


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


def _render_detail(doc: dict, *, hr_ok: bool) -> None:
    did = str(doc.get("id") or "")
    title = str(doc.get("file_name") or "Document")

    def _body() -> None:
        restricted = bool(doc.get("is_restricted"))
        flag = '<span class="ips-restricted-tag">RESTRICTED</span>' if restricted else "Standard access"
        st.markdown(
            f'<dl class="ips-info-grid">'
            f"<dt>Document type</dt><dd>{html.escape(str(doc.get('doc_type') or '—'))}</dd>"
            f"<dt>Linked module</dt><dd>{html.escape(str(doc.get('linked_module') or '—'))}</dd>"
            f"<dt>Linked record</dt><dd>{html.escape(str(doc.get('linked_ref') or '—'))}</dd>"
            f"<dt>Uploaded by</dt><dd>{html.escape(str(doc.get('uploaded_by') or '—'))}</dd>"
            f"<dt>Upload date</dt><dd>{html.escape(fmt_date(doc.get('upload_date')))}</dd>"
            f"<dt>Expiration</dt><dd>{html.escape(fmt_date(doc.get('expiration_date')) if doc.get('expiration_date') else '—')}</dd>"
            f"<dt>Access</dt><dd>{flag}</dd>"
            f"</dl>",
            unsafe_allow_html=True,
        )
        st.button("Download", key=f"doc_dl_{did}", type="primary")
        if not is_demo_id(did):
            with st.expander("Edit metadata", expanded=False):
                st.selectbox("Document type", lookup_options("document_types"), key=f"doc_edit_type_{did}")
                st.selectbox("Module", _LINK_MODULES, key=f"doc_edit_mod_{did}")
                refs = document_link_ref_options(str(st.session_state.get(f"doc_edit_mod_{did}") or ""))
                if refs:
                    st.selectbox("Linked record", refs, key=f"doc_edit_ref_{did}")
                else:
                    st.text_input("Linked record", value=str(doc.get("linked_ref") or ""), key=f"doc_edit_ref_{did}")
                st.date_input("Expiration", key=f"doc_edit_exp_{did}", value=None)
                st.checkbox("Restricted", key=f"doc_edit_rest_{did}", value=restricted, disabled=not hr_ok)
                if st.button("Save changes", key=f"doc_save_{did}", type="primary"):
                    ok, msg = persist_document(
                        {
                            "file_name": doc.get("file_name"),
                            "doc_type": st.session_state.get(f"doc_edit_type_{did}"),
                            "linked_module": st.session_state.get(f"doc_edit_mod_{did}"),
                            "linked_ref": st.session_state.get(f"doc_edit_ref_{did}"),
                            "uploaded_by": doc.get("uploaded_by"),
                            "expiration_date": st.session_state.get(f"doc_edit_exp_{did}"),
                            "is_restricted": st.session_state.get(f"doc_edit_rest_{did}"),
                        },
                        row_id=did,
                    )
                    if apply_persist_feedback(ok, msg):
                        st.rerun()

    render_record_detail_dialog(
        f"{title} — Document Details",
        module_name="documents",
        session_select_key=_SEL,
        body_fn=_body,
    )


def render() -> None:
    try:
        from app.pages.modules._access import begin_module
    except ImportError:
        from pages.modules._access import begin_module  # type: ignore
    if not begin_module("documents"):
        return
    role_norm = normalize_role(current_role())
    hr_ok = can_view_hr_documents(role_norm)
    all_docs = load_documents_hub(role=role_norm)

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header(
            "Documents",
            "Central document hub — link files to jobs, estimates, assets, employees, certifications, inventory, and updates.",
        )
    with act_r:
        if st.button("+ Upload Document", key="doc_hub_upload", type="primary", use_container_width=True):
            st.session_state["ips_doc_hub_form"] = True

    if not hr_ok:
        st.markdown(
            '<p class="ips-alert-banner">Restricted documents are hidden. Administrators see all files.</p>',
            unsafe_allow_html=True,
        )

    def _filters() -> None:
        c1, c2, c3, c4, c5 = st.columns([1.3, 1, 1, 0.9, 0.6])
        with c1:
            st.text_input("Search", placeholder="Search file or linked record…", key="doc_hub_search", label_visibility="collapsed")
        with c2:
            st.selectbox("Module", DOCUMENT_LINK_MODULES, key="doc_hub_module", label_visibility="collapsed")
        with c3:
            st.selectbox("Type", ["All Types", *lookup_options("document_types")], key="doc_hub_type", label_visibility="collapsed")
        with c4:
            st.selectbox("Access", ["All", "Standard", "Restricted"], key="doc_hub_access", label_visibility="collapsed")
        with c5:
            if st.button("Clear", key="doc_hub_clear", use_container_width=True):
                st.session_state["doc_hub_search"] = ""
                st.session_state["doc_hub_module"] = "All Modules"
                st.session_state["doc_hub_type"] = "All Types"
                st.session_state["doc_hub_access"] = "All"
                st.rerun()

    layout_filter_bar(_filters)

    filtered = _filter_docs(
        all_docs,
        q=str(st.session_state.get("doc_hub_search") or "").strip(),
        module=str(st.session_state.get("doc_hub_module") or "All Modules"),
        doc_type=str(st.session_state.get("doc_hub_type") or "All Types"),
    )
    access = str(st.session_state.get("doc_hub_access") or "All")
    if access == "Standard":
        filtered = [d for d in filtered if not d.get("is_restricted")]
    elif access == "Restricted":
        filtered = [d for d in filtered if d.get("is_restricted")]

    st.caption(f"{len(filtered)} document(s)")

    if st.session_state.get("ips_doc_hub_form"):
        _render_upload_form(hr_ok=hr_ok)

    selected_id = str(st.session_state.get(_SEL) or "")
    if selected_id and not any(str(d.get("id")) == selected_id for d in filtered):
        st.session_state.pop(_SEL, None)
        selected_id = ""

    def _cell(field: str, row: dict) -> str:
        if field == "access":
            if row.get("is_restricted"):
                return '<span class="ips-restricted-tag">RESTRICTED</span>'
            return '<span style="color:#64748b;font-size:0.75rem;">Standard</span>'
        if field == "linked_module":
            return f'<span style="color:#2563eb;font-weight:600">{html.escape(str(row.get(field) or ""))}</span>'
        if field in ("upload_date", "expiration_date"):
            return html.escape(fmt_date(row.get(field)) if row.get(field) else "—")
        return html.escape(str(row.get(field) or "—"))

    def _plain_cell(field: str, row: dict) -> str:
        if field == "access":
            return "Restricted" if row.get("is_restricted") else "Standard"
        if field in ("upload_date", "expiration_date"):
            return fmt_date(row.get(field)) if row.get(field) else "—"
        return str(row.get(field) or "—")

    sel = render_clickable_table(
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
        "documents_list",
        row_id_key="id",
        session_select_key=_SEL,
        selected_id=selected_id or None,
        plain_cell=_plain_cell,
        html_cell=_cell,
    )

    if sel:
        doc = next((d for d in filtered if str(d.get("id")) == sel), None)
        if doc:
            _render_detail(doc, hr_ok=hr_ok)
