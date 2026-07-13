"""
IPS modal / ``st.dialog`` styling (shared with CRUD pages).

Implementation lives in :mod:`ips_crud_list_styles`; helpers live in :mod:`app.ui.ips_modal_form`.
"""

from __future__ import annotations

from app.ips_crud_list_styles import IPS_MODAL_STYLES_KEY, inject_ips_modal_styles
from app.ui.ips_modal_form import ensure_modal_styles, modal_wide_marker
__all__ = [
    "IPS_MODAL_STYLES_KEY",
    "ensure_modal_styles",
    "inject_ips_modal_styles",
    "modal_wide_marker",
]
