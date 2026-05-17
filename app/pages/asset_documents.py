from __future__ import annotations

import pandas as pd
import streamlit as st

try:
    from app.auth import current_profile, current_role
    from app.ui.page_shell import render_page_header
    from app.db import fetch_table, fetch_table_admin
    from app.services.asset_constants import DOCUMENT_TYPES
    from app.services.asset_document_util import persist_asset_document_upload
except ImportError:
    from auth import current_profile, current_role  # type: ignore
    from branding import render_header  # type: ignore
    from db import fetch_table, fetch_table_admin  # type: ignore
    from services.asset_constants import DOCUMENT_TYPES  # type: ignore
    from services.asset_document_util import persist_asset_document_upload  # type: ignore


def render() -> None:
    render_page_header("Asset Documents", "Files linked to assets.")

    assets = fetch_table("assets", limit=5000, order_by="asset_name")
    documents = fetch_table_admin("asset_documents", limit=5000, order_by="created_at")

    st.session_state.setdefault("asset_doc_panel", "Documents")
    st.radio(
        "Documents view",
        ["Documents", "Upload Document"],
        horizontal=True,
        key="asset_doc_panel",
        label_visibility="collapsed",
    )
    _dp = str(st.session_state.get("asset_doc_panel") or "Documents")
    if _dp == "Documents":
        if documents:
            st.dataframe(pd.DataFrame(documents), use_container_width=True, hide_index=True)
        else:
            st.info("No asset documents found.")

    else:
        if current_role() not in {"admin", "pm"}:
            st.info("Only admin or pm users can upload documents.")
            return

        asset_options = {f"{a.get('asset_id')} - {a.get('asset_name')}": a for a in assets}
        selected_label = st.selectbox("Asset", list(asset_options.keys()))
        selected_asset = asset_options[selected_label]

        doc_type = st.selectbox("Document Type", DOCUMENT_TYPES)
        expiration_date = st.date_input("Expiration Date", value=None)
        notes = st.text_area("Notes", height=72)
        uploaded = st.file_uploader(
            "Document",
            accept_multiple_files=False,
            type=["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "csv", "png", "jpg", "jpeg"],
        )

        if st.button("Upload Document", use_container_width=True):
            if not uploaded:
                st.error("Choose a document first.")
                return

            try:
                persist_asset_document_upload(
                    asset_row=selected_asset,
                    uploaded=uploaded,
                    document_type=doc_type,
                    expiration_date=expiration_date,
                    notes=notes,
                    uploaded_by=current_profile().get("id"),
                )
            except Exception as exc:
                st.error(f"Could not save document (storage or database): {exc}")
            else:
                st.success("Manual uploaded successfully.")
                st.rerun()
