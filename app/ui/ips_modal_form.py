"""
Reusable helpers for IPS ``st.dialog`` modals (shared look via :func:`inject_ips_modal_styles`).

Pages should call :func:`ensure_modal_styles` at the start of each dialog body and optionally
:func:`modal_wide_marker` for catalog-sized forms (wider ``stDialog`` via CSS :has).
"""

from __future__ import annotations

import streamlit as st

from app.ips_crud_list_styles import inject_ips_modal_styles
def ensure_modal_styles() -> None:
    """Inject global IPS modal CSS once per browser session."""
    inject_ips_modal_styles()


def modal_wide_marker() -> None:
    """Hidden marker so ``inject_ips_modal_styles`` can widen the dialog shell."""
    st.markdown('<span class="ips-modal-wide" aria-hidden="true"></span>', unsafe_allow_html=True)
