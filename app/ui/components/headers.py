"""Page and section headers."""

from __future__ import annotations

try:
    from app.ui.page_shell import (
        render_page_header,
        render_section_desc_only,
        render_section_header,
    )
except ImportError:
    from ui.page_shell import (  # type: ignore
        render_page_header,
        render_section_desc_only,
        render_section_header,
    )

__all__ = ["render_page_header", "render_section_header", "render_section_desc_only"]
