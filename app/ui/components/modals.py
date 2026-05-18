"""Modal / dialog styling."""

from __future__ import annotations

try:
    from app.ui.page_shell import ensure_modal_styles, render_modal
except ImportError:
    from ui.page_shell import ensure_modal_styles, render_modal  # type: ignore

__all__ = ["ensure_modal_styles", "render_modal"]
