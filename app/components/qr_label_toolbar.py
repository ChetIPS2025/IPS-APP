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
    (LABEL_PNG_SIZE_1X4, '1"×4" label'),
    (LABEL_PNG_SIZE_2X6, '2"×6" label'),
)

_QR_LABEL_PNG_CSS = """
<style id="ips-qr-label-png-toolbar-v1">
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-qr-label-png-toolbar)
  [data-testid="stHorizontalBlock"]:has([data-testid="stDownloadButton"]) {
  gap: 0.35rem !important;
  width: 100% !important;
  align-items: stretch !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-qr-label-png-toolbar)
  [data-testid="stHorizontalBlock"]:has([data-testid="stDownloadButton"]) > [data-testid="column"] {
  min-width: 0 !important;
  flex: 1 1 0 !important;
  width: auto !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-qr-label-png-toolbar) [data-testid="stDownloadButton"] {
  width: 100% !important;
  max-width: 100% !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-qr-label-png-toolbar) [data-testid="stDownloadButton"] > button {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  min-height: 2rem !important;
  padding: 0.3rem 0.4rem !important;
  font-size: 0.72rem !important;
  line-height: 1.15 !important;
  white-space: normal !important;
  word-break: break-word !important;
  overflow-wrap: anywhere !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-qr-label-png-toolbar) [data-testid="stDownloadButton"] > button p,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-qr-label-png-toolbar) [data-testid="stDownloadButton"] > button span {
  font-size: 0.72rem !important;
  line-height: 1.15 !important;
  white-space: normal !important;
  word-break: break-word !important;
  overflow-wrap: anywhere !important;
  overflow: visible !important;
  text-overflow: clip !important;
}
</style>
"""


def _ensure_qr_label_png_css() -> None:
    if st.session_state.get("_ips_qr_label_png_css"):
        return
    st.session_state["_ips_qr_label_png_css"] = True
    st.markdown(_QR_LABEL_PNG_CSS, unsafe_allow_html=True)


def render_qr_label_png_buttons(
    *,
    key_prefix: str,
    basename: str,
    build_png: Callable[[str], bytes],
) -> None:
    """Two equal-width download buttons for horizontal 1×4 and 2×6 label PNGs."""
    _ensure_qr_label_png_css()
    st.markdown('<span class="ips-qr-label-png-toolbar"></span>', unsafe_allow_html=True)
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
