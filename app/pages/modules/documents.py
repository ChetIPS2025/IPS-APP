"""Central Documents hub (Phase 2D)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.auth import current_role
    from app.components.headers import render_page_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.layout import render_selected_detail_panel
    from app.components.tables import render_data_table
    from app.pages.modules._data import load_documents_hub
    from app.pages.modules._session import select_key
    from app.styles import inject_global_css
    from app.pages.modules._data import lookup_options
    from app.utils.constants import DOCUMENT_LINK_MODULES
    from app.utils.formatting import fmt_date
    from app.utils.permissions import can_view_hr_documents, normalize_role
except ImportError:
    from auth import current_role  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.layout import render_selected_detail_panel  # type: ignore
    from components.tables import render_data_table  # type: ignore
    from pages.modules._data import load_documents_hub  # type: ignore
    from pages.modules._session import select_key  # type: ignore
    from styles import inject_global_css  # type: ignore
    from pages.modules._data import lookup_options  # type: ignore
    from utils.constants import DOCUMENT_LINK_MODULES  # type: ignore
    from utils.formatting import fmt_date  # type: ignore
    from utils.permissions import can_view_hr_documents, normalize_role  # type: ignore

_SEL = select_key("documents")


def _filter_docs(rows: list[dict], *, q: str, module: str, doc_type: str) -> list[dict]:
    out = rows
    if q:
        ql = q.lower()
        out = [
            d
            for d in out
            if ql in str(d.get("file_name", "")).lower()
            or ql in str(d.get("linked_ref", "")).lower()
        ]
    if module and module != "All Modules":
        out = [d for d in out if str(d.get("linked_module", "")) == module]
    if doc_type and doc_type != "All Types":
        out = [d for d in out if str(d.get("doc_type", "")) == doc_type]
    return out


def _render_detail(doc: dict) -> None:
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
        st.button("Download", key=f"doc_dl_{doc.get('id')}", type="primary")

    render_selected_detail_panel(title, body_fn=_body)


def render() -> None:
    inject_global_css()
    role_norm = normalize_role(current_role())
    hr_ok = can_view_hr_documents(role_norm)
    all_docs = load_documents_hub(role=role_norm)

    act_l, act_r = st.columns([3, 1])
    with act_l:
        render_page_header(
            "Documents",
            "Central document hub — link files to jobs, estimates, assets, employees, and more.",
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
        c1, c2, c3, c4 = st.columns([1.4, 1.1, 1.1, 1])
        with c1:
            st.text_input("Search", placeholder="Search file or linked record…", key="doc_hub_search", label_visibility="collapsed")
        with c2:
            st.selectbox("Module", DOCUMENT_LINK_MODULES, key="doc_hub_module", label_visibility="collapsed")
        with c3:
            st.selectbox("Type", ["All Types", *lookup_options("document_types")], key="doc_hub_type", label_visibility="collapsed")
        with c4:
            st.selectbox("Access", ["All", "Standard", "Restricted"], key="doc_hub_access", label_visibility="collapsed")

    layout_filter_bar(_filters)

    filtered = _filter_docs(
        all_docs,
        q=str(st.session_state.get("doc_hub_search") or ""),
        module=str(st.session_state.get("doc_hub_module") or "All Modules"),
        doc_type=str(st.session_state.get("doc_hub_type") or "All Types"),
    )
    access = str(st.session_state.get("doc_hub_access") or "All")
    if access == "Standard":
        filtered = [d for d in filtered if not d.get("is_restricted")]
    elif access == "Restricted":
        filtered = [d for d in filtered if d.get("is_restricted")]

    if st.session_state.get("ips_doc_hub_form"):
        with st.expander("Upload document", expanded=True):
            u1, u2 = st.columns(2)
            with u1:
                st.selectbox("Document type", lookup_options("document_types"), key="doc_hub_new_type")
                st.selectbox("Link to module", [m for m in DOCUMENT_LINK_MODULES if m != "All Modules"], key="doc_hub_new_module")
                st.text_input("Linked record", key="doc_hub_new_ref", placeholder="Job #, employee name, etc.")
            with u2:
                st.file_uploader("File", key="doc_hub_new_file")
                st.date_input("Expiration (optional)", key="doc_hub_new_exp", value=None)
                st.checkbox("Restricted / private", key="doc_hub_new_restricted", disabled=not hr_ok)
            if st.button("Save upload", key="doc_hub_save", type="primary"):
                try:
                    from app.auth import current_profile
                    from app.pages.modules._data import persist_document
                except ImportError:
                    from auth import current_profile  # type: ignore
                    from pages.modules._data import persist_document  # type: ignore
                prof = current_profile() or {}
                ui = {
                    "file_name": str(st.session_state.get("doc_hub_new_file") or "upload.pdf"),
                    "doc_type": st.session_state.get("doc_hub_new_type"),
                    "linked_module": st.session_state.get("doc_hub_new_module"),
                    "linked_ref": st.session_state.get("doc_hub_new_ref"),
                    "uploaded_by": str(prof.get("full_name") or prof.get("email") or "User"),
                    "expiration_date": st.session_state.get("doc_hub_new_exp"),
                    "is_restricted": st.session_state.get("doc_hub_new_restricted"),
                }
                ok, msg = persist_document(ui)
                if ok:
                    st.success(msg)
                    st.session_state["ips_doc_hub_form"] = False
                    st.rerun()
                else:
                    st.error(msg)

    selected_id = str(st.session_state.get(_SEL) or "")

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

    sel = render_data_table(
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
        row_id_key="id",
        selected_id=selected_id or None,
        session_select_key=_SEL,
        col_fr=["1.2fr", "0.9fr", "0.75fr", "1.2fr", "0.9fr", "0.75fr", "0.7fr", "0.65fr"],
        cell_renderer=_cell,
    )

    if sel:
        doc = next((d for d in filtered if str(d.get("id")) == sel), None)
        if doc:
            _render_detail(doc)
