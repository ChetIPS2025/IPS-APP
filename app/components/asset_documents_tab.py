"""Asset detail Documents tab — upload, table, preview, and delete."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from app.pages._core._crud import is_demo_id
from app.services.asset_document_util import (
    ASSET_DOCUMENT_UPLOAD_TYPES,
    delete_asset_document_record,
    file_type_label,
    is_image_document,
    is_pdf_document,
    persist_asset_document_upload,
)
from app.services.assets_service import (
    delete_asset_document,
    get_asset_document_view_url,
    get_asset_documents,
)
from app.utils.formatting import fmt_date
AST_DOC_PREVIEW_KEY = "ast_doc_preview_spec"
AST_DOC_DELETE_KEY = "ast_doc_delete_confirm"


def asset_documents_count(asset_id: str) -> int:
    return len(get_asset_documents(str(asset_id or "").strip()))


def _current_uploader_id() -> str | None:
    from app.auth import current_profile
    pid = str((current_profile() or {}).get("id") or "").strip()
    return pid or None


def _upload_signature(files: list[Any]) -> tuple[tuple[str, int], ...]:
    return tuple(
        (str(getattr(f, "name", "") or ""), len(f.getvalue() if f else b""))
        for f in files
    )


def _process_uploads(asset: dict, *, files: list[Any], key_prefix: str) -> bool:
    if not files:
        return False
    uploaded_any = False
    for up in files:
        if up is None or not up.getvalue():
            continue
        persist_asset_document_upload(
            asset_row=asset,
            uploaded=up,
            document_type="Document",
            expiration_date=None,
            notes="",
            uploaded_by=_current_uploader_id(),
        )
        uploaded_any = True
    if uploaded_any:
        st.session_state.pop(f"{key_prefix}_upload_sig", None)
        st.session_state.pop(f"{key_prefix}_uploader", None)
    return uploaded_any


@st.dialog("Document preview", width="large")
def _asset_document_preview_dialog() -> None:
    spec = st.session_state.get(AST_DOC_PREVIEW_KEY)
    if not isinstance(spec, dict):
        return
    fname = str(spec.get("file_name") or "Document")
    url = str(spec.get("url") or "").strip()
    kind = str(spec.get("kind") or "")
    st.markdown(f"### {html.escape(fname)}")
    if not url:
        st.warning("Preview is not available for this file.")
        return
    if kind == "pdf":
        safe_url = html.escape(url, quote=True)
        components.html(
            f'<iframe src="{safe_url}" style="width:100%;height:72vh;border:1px solid #e2e8f0;border-radius:8px;" '
            f'title="{html.escape(fname)}"></iframe>',
            height=520,
            scrolling=True,
        )
    elif kind == "image":
        st.image(url, use_container_width=True)
    if st.button("Close", key="ast_doc_preview_close", use_container_width=True):
        st.session_state.pop(AST_DOC_PREVIEW_KEY, None)
        st.rerun()


def _open_preview(doc: dict[str, Any]) -> None:
    fname = str(doc.get("file_name") or "Document")
    ctype = str(doc.get("content_type") or "")
    url = str(doc.get("view_url") or get_asset_document_view_url(doc) or "").strip()
    if is_pdf_document(fname, ctype):
        kind = "pdf"
    elif is_image_document(fname, ctype):
        kind = "image"
    else:
        return
    st.session_state[AST_DOC_PREVIEW_KEY] = {
        "file_name": fname,
        "url": url,
        "kind": kind,
    }
    _asset_document_preview_dialog()


def _render_documents_table(
    docs: list[dict[str, Any]],
    *,
    asset: dict,
    key_prefix: str,
    readonly: bool,
) -> None:
    st.markdown(
        '<div class="ips-asset-doc-table-marker" aria-hidden="true"></div>'
        '<div class="ips-asset-doc-table-head">'
        "<span>File Name</span><span>Type</span><span>Uploaded By</span>"
        "<span>Upload Date</span><span>Download</span><span>Delete</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    for i, doc in enumerate(docs):
        doc_id = str(doc.get("id") or i)
        fname = str(doc.get("file_name") or "Document")
        dtype = file_type_label(fname, str(doc.get("content_type") or ""))
        uploader = str(doc.get("uploaded_by_name") or "—")
        when = fmt_date(str(doc.get("created_at") or "")[:10]) if doc.get("created_at") else "—"
        view_url = str(doc.get("view_url") or get_asset_document_view_url(doc) or "").strip()
        cols = st.columns([2.4, 0.55, 1.0, 0.85, 0.65, 0.55], gap="small")
        with cols[0]:
            label = html.escape(fname)
            if is_pdf_document(fname, str(doc.get("content_type") or "")) or is_image_document(
                fname, str(doc.get("content_type") or "")
            ):
                if st.button(
                    fname[:48] + ("…" if len(fname) > 48 else ""),
                    key=f"{key_prefix}_open_{doc_id}",
                    use_container_width=True,
                ):
                    _open_preview(doc)
            else:
                st.markdown(
                    f'<p class="ips-asset-doc-name">{label}</p>',
                    unsafe_allow_html=True,
                )
        with cols[1]:
            st.markdown(f'<p class="ips-asset-doc-cell">{html.escape(dtype)}</p>', unsafe_allow_html=True)
        with cols[2]:
            st.markdown(
                f'<p class="ips-asset-doc-cell">{html.escape(uploader)}</p>',
                unsafe_allow_html=True,
            )
        with cols[3]:
            st.markdown(f'<p class="ips-asset-doc-cell">{html.escape(when)}</p>', unsafe_allow_html=True)
        with cols[4]:
            if view_url:
                st.link_button(
                    "Download",
                    view_url,
                    use_container_width=True,
                    key=f"{key_prefix}_dl_{doc_id}",
                )
            else:
                st.caption("—")
        with cols[5]:
            if readonly:
                st.caption("—")
            elif st.button(
                "Delete",
                key=f"{key_prefix}_del_{doc_id}",
                use_container_width=True,
            ):
                st.session_state[AST_DOC_DELETE_KEY] = doc
                st.rerun()


def render_asset_documents_tab(
    asset: dict,
    *,
    key_prefix: str = "ast_doc",
    include_restricted: bool = False,
) -> None:
    """Documents tab body for Asset Details modal."""
    aid = str(asset.get("id") or "").strip()
    readonly = not aid or is_demo_id(aid)

    if st.session_state.get(AST_DOC_PREVIEW_KEY):
        _asset_document_preview_dialog()

    pending_delete = st.session_state.get(AST_DOC_DELETE_KEY)
    if isinstance(pending_delete, dict) and str(pending_delete.get("id") or ""):
        fname = str(pending_delete.get("file_name") or "this file")
        st.warning(f"Delete **{html.escape(fname)}**? This cannot be undone.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm delete", type="primary", key=f"{key_prefix}_del_ok"):
                try:
                    delete_asset_document(pending_delete)
                    st.session_state.pop(AST_DOC_DELETE_KEY, None)
                    st.success("Document deleted.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        with c2:
            if st.button("Cancel", key=f"{key_prefix}_del_cancel"):
                st.session_state.pop(AST_DOC_DELETE_KEY, None)
                st.rerun()

    if not readonly:
        st.markdown(
            '<div class="ips-asset-doc-upload-zone-marker" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "Upload Document",
            type="primary",
            key=f"{key_prefix}_upload_cta",
            help="Choose or drop files below — each file saves as soon as it is added.",
        ):
            st.session_state[f"{key_prefix}_focus_upload"] = True
        uploads = st.file_uploader(
            "Drop files here or click to browse",
            type=ASSET_DOCUMENT_UPLOAD_TYPES,
            accept_multiple_files=True,
            key=f"{key_prefix}_uploader",
            help="PDF, DOCX, XLSX, JPG, PNG, or TXT. Uploads save immediately without Edit mode.",
        )
        if uploads:
            raw = uploads if isinstance(uploads, list) else [uploads]
            sig = _upload_signature(raw)
            last_sig = st.session_state.get(f"{key_prefix}_upload_sig")
            if sig != last_sig:
                try:
                    if _process_uploads(asset, files=raw, key_prefix=key_prefix):
                        st.success(
                            f"Uploaded {len(raw)} file(s)."
                            if len(raw) > 1
                            else "Document uploaded."
                        )
                        st.rerun()
                except Exception as exc:
                    st.error(f"Upload failed: {exc}")
                else:
                    st.session_state[f"{key_prefix}_upload_sig"] = sig

    docs = get_asset_documents(aid, include_restricted=include_restricted)
    if not docs:
        st.info("No documents attached to this asset.")
        return

    _render_documents_table(docs, asset=asset, key_prefix=key_prefix, readonly=readonly)
