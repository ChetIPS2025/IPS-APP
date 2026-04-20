"""
IPS CRUD list layout (toolbar + side panel + subtitles).

Implementation lives in :mod:`ips_crud_list_styles`; this module exposes the same API under ``app.ui.crud_list``.
"""

from __future__ import annotations

try:
    from app.ips_crud_list_styles import (
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        IPS_CRUD_LIST_STYLES_KEY,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )
except ImportError:
    from ips_crud_list_styles import (  # type: ignore
        IPS_CRUD_LIST_PAGE_GAP,
        IPS_CRUD_LIST_PAGE_SPLIT,
        IPS_CRUD_LIST_STYLES_KEY,
        inject_ips_crud_list_styles,
        render_crud_list_subtitle,
    )

__all__ = [
    "IPS_CRUD_LIST_PAGE_GAP",
    "IPS_CRUD_LIST_PAGE_SPLIT",
    "IPS_CRUD_LIST_STYLES_KEY",
    "inject_ips_crud_list_styles",
    "render_crud_list_subtitle",
]
