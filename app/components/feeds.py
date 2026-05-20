"""Activity feed, document list, and upload placeholders."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st


def render_activity_feed(items: list[dict[str, Any]], *, empty_message: str = "No activity yet.") -> None:
    ot = "d" + "iv"
    if not items:
        st.caption(empty_message)
        return
    for act in items:
        icon = html.escape(str(act.get("icon") or "📋"))
        bg = html.escape(str(act.get("icon_bg") or "#eff6ff"))
        title = html.escape(str(act.get("title") or ""))
        meta = html.escape(str(act.get("meta") or ""))
        st.markdown(
            f'<{ot} class="ips-activity-item">'
            f'<{ot} class="ips-activity-icon" style="background:{bg}">{icon}</{ot}>'
            f"<{ot}><strong>{title}</strong>"
            f'<{ot} class="ips-activity-meta">{meta}</{ot}></{ot}></{ot}>',
            unsafe_allow_html=True,
        )


def render_document_list(docs: list[dict[str, Any]], *, key_prefix: str = "doc") -> None:
    if not docs:
        st.caption("No documents.")
        return
    for i, doc in enumerate(docs):
        name = html.escape(str(doc.get("file_name") or doc.get("name") or "Document"))
        dtype = html.escape(str(doc.get("doc_type") or doc.get("document_type") or ""))
        uploaded = html.escape(str(doc.get("upload_date") or doc.get("created_at") or "")[:10])
        restricted = doc.get("is_restricted")
        tag = '<span class="ips-restricted-tag">RESTRICTED</span>' if restricted else ""
        c1, c2, c3 = st.columns([3, 1.2, 0.6])
        with c1:
            st.markdown(f"**{name}** {tag}", unsafe_allow_html=True)
            if dtype:
                st.caption(dtype)
        with c2:
            st.caption(uploaded or "—")
        with c3:
            st.button("View", key=f"{key_prefix}_view_{i}", use_container_width=True)


def render_upload_area(label: str = "Upload file", *, key: str = "ips_upload") -> None:
    ot = "d" + "iv"
    st.markdown(f'<{ot} class="ips-photo-card">{html.escape(label)}<br><small>Supabase Storage integration placeholder</small></{ot}>', unsafe_allow_html=True)
    st.file_uploader(label, key=key, label_visibility="collapsed")
