"""Reusable touch-friendly signature pad (iPad / Apple Pencil)."""

from __future__ import annotations

import base64
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
            stroke_width=2,
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


def render_compact_signature_pad(
    *,
    label: str,
    key: str,
    existing_data: str = "",
    disabled: bool = False,
) -> str:
    return render_signature_pad(
        label=label,
        key=key,
        existing_data=existing_data,
        width=220,
        height=72,
        disabled=disabled,
    )
