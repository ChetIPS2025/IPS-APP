"""
Reusable Streamlit control: open a local document (e.g. PDF) in a **new browser tab**
via a ``data:`` URL (base64). Styled for IPS dark theme.
"""

from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any, Union

import streamlit as st

try:
    from app.config import ROOT_DIR
except ImportError:
    from config import ROOT_DIR  # type: ignore

PathLike = Union[str, Path]


def _resolve_path(file_path: PathLike) -> Path:
    p = Path(file_path)
    if p.is_absolute():
        return p
    return (ROOT_DIR / p).resolve()


def render_document_button(
    title: str,
    file_path: PathLike,
    *,
    container: Any | None = None,
) -> bool:
    """
    Render a clickable control that opens a PDF (or other browser-supported type)
    in a **new tab** using a base64 ``data:`` URL.

    Parameters
    ----------
    title
        Visible label (e.g. ``"AWG Wire Size Chart"``).
    file_path
        Path to the file. Relative paths are resolved from the **project root**
        (parent of ``app/``), e.g. ``"assets/awg_wire_chart.pdf"``.
    container
        Streamlit parent to render into (default ``st``). Pass ``st.sidebar`` when
        placing the control in the sidebar.

    Returns
    -------
    bool
        ``True`` if the control was rendered, ``False`` if the file was missing.
    """
    dg = container if container is not None else st

    path = _resolve_path(file_path)
    if not path.is_file():
        dg.warning(f"Document not found: `{path}`")
        return False

    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    mime = "application/pdf"
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }[path.suffix.lower()]
    href = f"data:{mime};base64,{b64}"
    safe_title = html.escape(title, quote=True)

    # IPS dark: deep blue panel + soft outer glow + rounded corners (inline = no global CSS deps).
    style = (
        "display:inline-block;padding:0.55rem 1.15rem;margin:0.15rem 0;"
        "background:linear-gradient(180deg,#102a47 0%,#0a1628 100%);"
        "color:#e8f4ff;text-decoration:none;font-weight:600;font-size:0.95rem;"
        "border-radius:12px;border:1px solid rgba(120,190,255,0.55);"
        "box-shadow:0 0 12px rgba(64,150,255,0.45),0 0 2px rgba(180,220,255,0.35) inset;"
        "letter-spacing:0.02em;transition:box-shadow 0.15s ease,transform 0.15s ease;"
    )
    dg.markdown(
        f'<a href="{href}" target="_blank" rel="noopener noreferrer" style="{style}">{safe_title}</a>',
        unsafe_allow_html=True,
    )
    return True


# --- Example usage (copy into any ``render()``) ---
#
#   from app.utils.document_button import render_document_button
#   render_document_button("AWG Wire Size Chart", "assets/awg_wire_chart.pdf")
#
#   # In the sidebar (e.g. inside ``with st.sidebar.expander("TOOLS")``):
#   render_document_button("AWG Wire Size Chart", "assets/awg_wire_chart.pdf", container=st)
