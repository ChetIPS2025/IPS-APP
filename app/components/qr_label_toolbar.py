"""Side-by-side PNG label download buttons for inventory and asset QR blocks."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

try:
    from app.services.inventory_qr_labels import (
        LABEL_PNG_SIZE_1X4,
        LABEL_PNG_SIZE_2X6,
        label_png_download_filename,
    )
except ImportError:
    from services.inventory_qr_labels import (  # type: ignore
        LABEL_PNG_SIZE_1X4,
        LABEL_PNG_SIZE_2X6,
        label_png_download_filename,
    )

_LABEL_PNG_BUTTONS: tuple[tuple[str, str], ...] = (
    (LABEL_PNG_SIZE_1X4, '1" x 4" Label PNG'),
    (LABEL_PNG_SIZE_2X6, '2" x 6" Label PNG'),
)


def render_qr_label_png_buttons(
    *,
    key_prefix: str,
    basename: str,
    build_png: Callable[[str], bytes],
) -> None:
    """Two equal-width download buttons for horizontal 1×4 and 2×6 label PNGs."""
    col1, col2 = st.columns(2, gap="small")
    for col, (size_key, label) in zip((col1, col2), _LABEL_PNG_BUTTONS):
        with col:
            try:
                st.download_button(
                    label,
                    data=build_png(size_key),
                    file_name=label_png_download_filename(basename, size_key),
                    mime="image/png",
                    key=f"{key_prefix}_label_png_{size_key}",
                    use_container_width=True,
                )
            except Exception:
                pass
