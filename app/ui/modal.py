"""
IPS modal / ``st.dialog`` styling (shared with CRUD pages).

Implementation lives in :mod:`ips_crud_list_styles`; this module exposes modal helpers under ``app.ui.modal``.
"""

from __future__ import annotations

try:
    from app.ips_crud_list_styles import IPS_MODAL_STYLES_KEY, inject_ips_modal_styles
except ImportError:
    from ips_crud_list_styles import IPS_MODAL_STYLES_KEY, inject_ips_modal_styles  # type: ignore

__all__ = ["IPS_MODAL_STYLES_KEY", "inject_ips_modal_styles"]
