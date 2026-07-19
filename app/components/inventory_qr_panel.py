"""Lazy Inventory QR tools — generate only after explicit request."""

from __future__ import annotations

import base64
import html

import streamlit as st

from app.services.inventory_display_helpers import resolve_inventory_sku
from app.services.inventory_service import generate_inventory_qr_value


def _inventory_qr_loaded_key(item_id: str) -> str:
    return f"ips_inventory_qr_loaded_{str(item_id or '').strip() or 'item'}"


def render_inventory_qr_panel(item: dict) -> None:
    """Compact QR summary with Load/Hide QR Tools."""
    iid = str(item.get("id") or "").strip() or "item"
    loaded_key = _inventory_qr_loaded_key(iid)
    st.markdown(
        '<p style="margin:0 0 0.35rem;font-weight:700;font-size:0.9rem;">Inventory QR</p>',
        unsafe_allow_html=True,
    )
    sku = resolve_inventory_sku(item)
    st.caption(f"SKU: **{html.escape(sku)}**", unsafe_allow_html=True)

    if not st.session_state.get(loaded_key):
        if st.button("Load QR Tools", key=f"inv_qr_load_{iid}", use_container_width=True):
            st.session_state[loaded_key] = True
            st.rerun()
        return

    from app.components.qr_label_toolbar import render_qr_label_png_buttons
    from app.services.inventory_qr_labels import (
        inventory_label_download_basename,
        inventory_label_png_bytes,
        inventory_qr_subject,
    )
    from app.services.inventory_display_helpers import inventory_qr_png_bytes

    scan_url = generate_inventory_qr_value(item)
    subject = inventory_qr_subject(item)
    qr_png = inventory_qr_png_bytes(item)

    with st.container(border=True):
        if qr_png and scan_url:
            b64 = base64.b64encode(qr_png).decode("ascii")
            safe_url = html.escape(scan_url, quote=True)
            st.markdown(
                f'<a href="{safe_url}" target="_self" title="Open use form">'
                f'<img src="data:image/png;base64,{b64}" width="132" alt="Inventory QR code" '
                f'style="display:block;border:1px solid #e2e8f0;border-radius:8px;" />'
                f"</a>",
                unsafe_allow_html=True,
            )
        elif qr_png:
            st.image(qr_png, width=132)
        else:
            st.caption(str(item.get("qr_code_value") or "—"))
        if scan_url:
            st.caption("Scan with a phone or tap to record material use.")
            st.link_button("Open Use Form", scan_url, use_container_width=True)
            if scan_url.startswith("http"):
                st.caption("Scan URL")
                st.code(scan_url, language=None)
        render_qr_label_png_buttons(
            key_prefix=f"inv_qr_{iid}",
            basename=inventory_label_download_basename(item),
            build_png=lambda size_key: inventory_label_png_bytes(item, subject, size=size_key),
        )
        cols = st.columns(2)
        with cols[0]:
            if st.button("Hide QR Tools", key=f"inv_qr_hide_{iid}", use_container_width=True):
                st.session_state.pop(loaded_key, None)
                st.rerun()
        with cols[1]:
            if st.button("Refresh QR", key=f"inv_qr_refresh_{iid}", use_container_width=True):
                st.rerun()
