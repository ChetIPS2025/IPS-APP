"""IPS UI component library — use across all pages."""

from __future__ import annotations

try:
    from app.ui.components.badges import render_badge
    from app.ui.components.buttons import toast_error, toast_info, toast_success, toast_warning
    from app.ui.components.cards import action_bar_card, render_card, render_kpi_card, render_kpi_grid
    from app.ui.components.empty_states import render_empty_state
    from app.ui.components.headers import render_page_header, render_section_desc_only, render_section_header
    from app.ui.components.loading import render_skeleton_rows, render_table_skeleton
    from app.ui.components.modals import ensure_modal_styles, render_modal
    from app.ui.components.tables import hide_internal_columns, prepare_display_table, render_filters, render_table
    from app.ui.components.topbar import render_top_bar
except ImportError:
    from ui.components.badges import render_badge  # type: ignore
    from ui.components.buttons import toast_error, toast_info, toast_success, toast_warning  # type: ignore
    from ui.components.cards import action_bar_card, render_card, render_kpi_card, render_kpi_grid  # type: ignore
    from ui.components.empty_states import render_empty_state  # type: ignore
    from ui.components.headers import render_page_header, render_section_desc_only, render_section_header  # type: ignore
    from ui.components.loading import render_skeleton_rows, render_table_skeleton  # type: ignore
    from ui.components.modals import ensure_modal_styles, render_modal  # type: ignore
    from ui.components.tables import hide_internal_columns, prepare_display_table, render_filters, render_table  # type: ignore
    from ui.components.topbar import render_top_bar  # type: ignore

__all__ = [
    "action_bar_card",
    "ensure_modal_styles",
    "hide_internal_columns",
    "prepare_display_table",
    "render_badge",
    "render_card",
    "render_empty_state",
    "render_filters",
    "render_kpi_card",
    "render_kpi_grid",
    "render_modal",
    "render_page_header",
    "render_section_desc_only",
    "render_section_header",
    "render_skeleton_rows",
    "render_table",
    "render_table_skeleton",
    "render_top_bar",
    "toast_error",
    "toast_info",
    "toast_success",
    "toast_warning",
]
