"""Shared kit/trailer audit line UI — status, condition, photo proof, notes."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.services.trailer_dashboard_service import (
    AUDIT_ITEM_CONDITIONS,
    AUDIT_ITEM_STATUSES,
    audit_item_requires_missing_note,
    audit_item_requires_photo,
    upload_audit_item_photo,
)
_PHOTO_STATE_PREFIX = "_kit_audit_photo"


def audit_photo_session_key(trailer_id: str, kit_item_id: str) -> str:
    return f"{_PHOTO_STATE_PREFIX}_{trailer_id}_{kit_item_id}"


def get_audit_item_photo(trailer_id: str, kit_item_id: str) -> dict[str, str]:
    raw = st.session_state.get(audit_photo_session_key(trailer_id, kit_item_id)) or {}
    if isinstance(raw, dict):
        return {
            "photo_path": str(raw.get("photo_path") or ""),
            "photo_url": str(raw.get("photo_url") or ""),
        }
    return {"photo_path": "", "photo_url": ""}


def clear_audit_item_photos(trailer_id: str, kit_item_ids: list[str]) -> None:
    for kid in kit_item_ids:
        st.session_state.pop(audit_photo_session_key(trailer_id, kid), None)


def _store_audit_photo(trailer_id: str, kit_item_id: str, photo_path: str, photo_url: str) -> None:
    st.session_state[audit_photo_session_key(trailer_id, kit_item_id)] = {
        "photo_path": photo_path,
        "photo_url": photo_url,
    }


def render_audit_item_header(it: dict[str, Any]) -> None:
    name = str(it.get("item_name") or "Tool").strip()
    serial = str(it.get("serial_number") or "").strip()
    exp_q = it.get("quantity_expected") or 1
    loc = str(it.get("location") or it.get("bin_location") or it.get("storage_location") or "").strip()
    meta_parts = [f"Expected qty: {exp_q}"]
    if serial:
        meta_parts.append(f"S/N {serial}")
    if loc:
        meta_parts.append(f"Location: {loc}")
    st.markdown(
        f"**{html.escape(name)}**"
        f'<div class="ips-trailer-muted">{html.escape(" · ".join(meta_parts))}</div>',
        unsafe_allow_html=True,
    )


def render_audit_item_photo_block(
    trailer_id: str,
    kit_item_id: str,
    *,
    uploaded_by: str | None,
    key_prefix: str,
    status: str,
) -> None:
    """Camera capture (mobile) with library upload fallback; shows preview when set."""
    stored = get_audit_item_photo(trailer_id, kit_item_id)
    requires_photo = audit_item_requires_photo(status)

    cam = st.camera_input(
        "Take Photo" if requires_photo else "Take Photo (optional)",
        key=f"{key_prefix}_cam_{kit_item_id}",
    )
    if cam is not None:
        path, url = upload_audit_item_photo(
            trailer_id,
            kit_item_id,
            cam,
            uploaded_by=uploaded_by,
        )
        if path or url:
            _store_audit_photo(trailer_id, kit_item_id, path, url)
            st.rerun()

    upload = st.file_uploader(
        "Upload Photo" if requires_photo else "Upload Photo (optional)",
        type=["png", "jpg", "jpeg", "webp"],
        key=f"{key_prefix}_up_{kit_item_id}",
        label_visibility="visible",
    )
    if upload is not None:
        path, url = upload_audit_item_photo(
            trailer_id,
            kit_item_id,
            upload,
            uploaded_by=uploaded_by,
        )
        if path or url:
            _store_audit_photo(trailer_id, kit_item_id, path, url)
            st.rerun()
        elif requires_photo:
            st.error("Photo upload failed — try again.")

    if stored.get("photo_url"):
        st.image(stored["photo_url"], width=120, caption="Photo attached")
    elif stored.get("photo_path"):
        st.caption("Photo saved — preview unavailable offline.")

    if requires_photo and not stored.get("photo_path") and not stored.get("photo_url"):
        st.caption("Photo required for this status before completing the audit.")


def render_audit_item_fields(
    it: dict[str, Any],
    *,
    trailer_id: str,
    key_prefix: str,
    uploaded_by: str | None,
    show_quantity: bool = True,
) -> dict[str, Any]:
    """Render one audit checklist row; returns collected line payload."""
    iid = str(it.get("id") or "")
    render_audit_item_header(it)

    c1, c2, c3 = st.columns([1.1, 1.1, 1.0])
    with c1:
        status = st.selectbox(
            "Status",
            AUDIT_ITEM_STATUSES,
            index=AUDIT_ITEM_STATUSES.index(str(it.get("status") or "Present"))
            if str(it.get("status") or "Present") in AUDIT_ITEM_STATUSES
            else 0,
            key=f"{key_prefix}_stat_{iid}",
        )
    with c2:
        default_cond = str(it.get("condition") or "Good")
        cond_index = AUDIT_ITEM_CONDITIONS.index(default_cond) if default_cond in AUDIT_ITEM_CONDITIONS else 1
        condition = st.selectbox(
            "Condition",
            AUDIT_ITEM_CONDITIONS,
            index=cond_index,
            key=f"{key_prefix}_cond_{iid}",
        )
    with c3:
        if show_quantity:
            qty = st.number_input(
                "Actual qty",
                min_value=0.0,
                value=float(it.get("quantity_actual") or it.get("quantity_expected") or 1),
                key=f"{key_prefix}_qty_{iid}",
            )
        else:
            qty = float(it.get("quantity_actual") or it.get("quantity_expected") or 1)

    render_audit_item_photo_block(
        trailer_id,
        iid,
        uploaded_by=uploaded_by,
        key_prefix=key_prefix,
        status=status,
    )

    note_label = (
        "Notes (required — where expected / what was checked)"
        if audit_item_requires_missing_note(status)
        else "Notes (optional)"
    )
    notes = st.text_area(
        note_label,
        key=f"{key_prefix}_note_{iid}",
        height=60,
        label_visibility="visible",
    )

    photo = get_audit_item_photo(trailer_id, iid)
    return {
        "kit_item_id": iid,
        "item_name": str(it.get("item_name") or "Tool"),
        "expected_quantity": it.get("quantity_expected") or 1,
        "actual_quantity": qty,
        "status": status,
        "condition": condition,
        "notes": notes,
        "photo_path": photo.get("photo_path"),
        "photo_url": photo.get("photo_url"),
    }


def collect_audit_line_from_session(
    it: dict[str, Any],
    *,
    trailer_id: str,
    key_prefix: str,
    show_quantity: bool = True,
) -> dict[str, Any]:
    """Build audit line payload from session state (supports paginated audit UI)."""
    iid = str(it.get("id") or "")
    status = st.session_state.get(
        f"{key_prefix}_stat_{iid}",
        str(it.get("status") or "Present"),
    )
    condition = st.session_state.get(
        f"{key_prefix}_cond_{iid}",
        str(it.get("condition") or "Good"),
    )
    default_qty = float(it.get("quantity_actual") or it.get("quantity_expected") or 1)
    qty = (
        float(st.session_state.get(f"{key_prefix}_qty_{iid}", default_qty))
        if show_quantity
        else default_qty
    )
    notes = str(st.session_state.get(f"{key_prefix}_note_{iid}", "") or "")
    photo = get_audit_item_photo(trailer_id, iid)
    return {
        "kit_item_id": iid,
        "item_name": str(it.get("item_name") or "Tool"),
        "expected_quantity": it.get("quantity_expected") or 1,
        "actual_quantity": qty,
        "status": status,
        "condition": condition,
        "notes": notes,
        "photo_path": photo.get("photo_path"),
        "photo_url": photo.get("photo_url"),
    }
