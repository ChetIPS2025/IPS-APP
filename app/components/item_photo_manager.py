"""Shared preview/remove/replace controls for catalog item photos."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.services.item_images import (
        ITEM_IMAGE_UPLOAD_TYPES,
        has_stored_item_image,
        normalize_image_status,
        resolve_image_url_by_field_priority,
        resolve_stored_item_image_url,
    )
    from app.services.repository import ServiceResult
except ImportError:
    from services.item_images import (  # type: ignore
        ITEM_IMAGE_UPLOAD_TYPES,
        has_stored_item_image,
        normalize_image_status,
        resolve_image_url_by_field_priority,
        resolve_stored_item_image_url,
    )
    from services.repository import ServiceResult  # type: ignore

_STATUS_LABELS = {
    "missing": "No photo",
    "needs_review": "Needs review (hidden from lists)",
    "approved": "Approved",
    "rejected": "Removed",
}


def _patch_modal_cache(cache_key: str | None, record_id: str, updates: dict[str, Any]) -> None:
    if not cache_key:
        return
    cache = st.session_state.get(cache_key)
    if not isinstance(cache, dict):
        return
    existing = cache.get(record_id)
    if isinstance(existing, dict):
        cache[record_id] = {**existing, **updates}


def render_item_photo_manager(
    record: dict[str, Any],
    *,
    record_id: str,
    session_prefix: str,
    image_css_class: str,
    upload_image: Callable[..., ServiceResult],
    clear_image: Callable[[str], ServiceResult],
    uploaded_by: str | None = None,
    cache_key: str | None = None,
    on_change: Callable[[], None] | None = None,
    readonly: bool = False,
    preview_record: dict[str, Any] | None = None,
) -> None:
    """Show current preview plus remove/replace actions without entering edit mode."""
    rid = str(record_id or "").strip()
    if not rid:
        st.caption("Save this record before adding a photo.")
        return

    preview = preview_record if isinstance(preview_record, dict) else record
    image_url = None
    try:
        from app.services.inventory_images import get_inventory_image_url
    except ImportError:
        from services.inventory_images import get_inventory_image_url  # type: ignore
    image_url = get_inventory_image_url(preview) or get_inventory_image_url(record)
    if not image_url:
        image_url = resolve_image_url_by_field_priority(preview) or resolve_stored_item_image_url(preview)
    status = normalize_image_status(preview.get("image_status"))
    status_label = _STATUS_LABELS.get(status, status.replace("_", " ").title())

    if image_url:
        st.image(image_url, width=260)
    else:
        st.caption("No item photo uploaded.")

    st.caption(f"Photo status: {status_label}")

    if readonly:
        return

    upload_key = f"{session_prefix}_upload"
    remove_key = f"{session_prefix}_remove"
    save_key = f"{session_prefix}_save"

    st.file_uploader(
        "Replace photo",
        type=list(ITEM_IMAGE_UPLOAD_TYPES),
        key=upload_key,
        help="Choose a new image, then click Save Photo.",
    )

    action_left, action_right = st.columns(2)
    with action_left:
        save_clicked = st.button("Save Photo", key=save_key, type="primary")
    with action_right:
        remove_clicked = st.button(
            "Remove Photo",
            key=remove_key,
            disabled=not has_stored_item_image(record),
        )

    if remove_clicked:
        result = clear_image(rid)
        if result.ok:
            if on_change:
                on_change()
            _patch_modal_cache(cache_key, rid, dict(result.data or {}))
            st.success("Photo removed.")
            st.rerun()
        st.error(result.error or "Could not remove photo.")

    if save_clicked:
        uploaded_file = st.session_state.get(upload_key)
        if uploaded_file is None:
            st.warning("Choose an image file first.")
            return
        result = upload_image(
            rid,
            uploaded_file,
            uploaded_by=uploaded_by,
            existing=record,
            replace_existing=True,
        )
        if result.ok:
            if on_change:
                on_change()
            _patch_modal_cache(cache_key, rid, dict(result.data or {}))
            st.session_state.pop(upload_key, None)
            st.success("Photo saved.")
            st.rerun()
        st.error(result.error or "Could not save photo.")
