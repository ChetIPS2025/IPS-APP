"""Reusable touch-friendly signature pad (iPad / Apple Pencil) with clear/re-sign."""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

import streamlit as st

try:
    from streamlit_drawable_canvas import st_canvas
except ImportError:
    st_canvas = None  # type: ignore[misc, assignment]


def signature_from_canvas(canvas_result: Any) -> str:
    if canvas_result is None or getattr(canvas_result, "image_data", None) is None:
        return ""
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return ""
    arr = canvas_result.image_data
    if arr.size == 0 or not np.any(arr[:, :, 3] > 0):
        return ""
    rgb = arr[:, :, :3].astype("uint8")
    img = Image.fromarray(rgb)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def render_signature_pad(
    *,
    label: str,
    key: str,
    existing_data: str = "",
    width: int = 700,
    height: int = 160,
    disabled: bool = False,
) -> str:
    """Render a signature capture widget; returns base64 PNG data URL."""
    st.markdown(f"**{label}**")
    sig_data = str(existing_data or "").strip()
    if disabled and sig_data:
        st.image(sig_data, use_container_width=True)
        return sig_data
    if disabled:
        st.caption("No signature captured.")
        return ""

    if st_canvas is not None:
        canvas = st_canvas(
            fill_color="rgba(255,255,255,0)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#ffffff",
            height=height,
            width=width,
            drawing_mode="freedraw",
            key=key,
        )
        drawn = signature_from_canvas(canvas)
        if drawn:
            return drawn
        return sig_data

    st.warning("Install `streamlit-drawable-canvas` for touch signatures, or upload PNG below.")
    up = st.file_uploader("Upload signature (PNG)", type=["png"], key=f"{key}_upload")
    if up is not None:
        return "data:image/png;base64," + base64.b64encode(up.read()).decode("ascii")
    return sig_data


def render_signature_field(
    *,
    label: str,
    role_key: str,
    existing: dict[str, Any] | None,
    disabled: bool = False,
    required: bool = False,
) -> dict[str, Any]:
    """
    V7 signature box: signer name, tap-to-sign canvas, clear/re-sign, timestamp.
    Returns {signer_name, signature_image, signed_at}.
    """
    entry = dict(existing or {})
    sk = f"ci_sig_{role_key}"
    req = " *" if required else ""
    st.markdown(f"**{label}{req}**")

    signer_name = st.text_input(
        "Printed name",
        value=str(entry.get("signer_name") or ""),
        disabled=disabled,
        key=f"{sk}_name",
    ).strip()

    sig_image = str(entry.get("signature_image") or "").strip()
    state_key = f"{sk}_image"
    if state_key in st.session_state:
        sig_image = str(st.session_state[state_key] or sig_image)

    btn_col, clear_col = st.columns([1, 1], gap="small")
    show_pad = st.session_state.get(f"{sk}_show_pad", not bool(sig_image))

    with btn_col:
        if not disabled and st.button("Sign / Re-sign", key=f"{sk}_sign_btn", use_container_width=True):
            st.session_state[f"{sk}_show_pad"] = True
            st.rerun()
    with clear_col:
        if not disabled and sig_image and st.button("Clear", key=f"{sk}_clear_btn", use_container_width=True):
            st.session_state[state_key] = ""
            st.session_state[f"{sk}_show_pad"] = True
            st.rerun()

    if sig_image and not show_pad and not disabled:
        st.image(sig_image, use_container_width=True)
        st.caption(f"Signed {entry.get('signed_at') or ''}".strip() or "Signature on file")
    elif sig_image and disabled:
        st.image(sig_image, use_container_width=True)
    elif show_pad and not disabled:
        drawn = render_signature_pad(
            label="Draw signature (finger or stylus)",
            key=f"{sk}_pad",
            existing_data=sig_image,
            width=680,
            height=150,
        )
        if drawn and drawn != sig_image:
            sig_image = drawn
            st.session_state[state_key] = drawn
            st.session_state[f"{sk}_show_pad"] = False
            entry["signed_at"] = _utc_now_iso()
    elif not disabled:
        st.caption("Tap **Sign / Re-sign** to open the signature pad.")

    if not sig_image:
        entry["signed_at"] = ""

    return {
        "signer_name": signer_name,
        "signature_image": sig_image,
        "signed_at": str(entry.get("signed_at") or (_utc_now_iso() if sig_image else "")),
    }
