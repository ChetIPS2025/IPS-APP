"""Reusable IPS UI components (Phase 1 foundation)."""

from __future__ import annotations

try:
    from app.components.buttons import render_action_buttons, render_detail_actions
    from app.components.cards import render_card, render_metric_card
    from app.components.empty_states import render_empty_state
    from app.components.forms import render_dropdown
    from app.components.headers import render_page_header
    from app.components.layout import (
        render_filter_bar,
        render_page_shell,
        render_selected_detail_panel,
        render_tab_placeholder,
    )
    from app.components.modals import confirm_dialog, render_record_detail_dialog
    from app.components.tables import render_clickable_table, render_data_table
    from app.components.sidebar import render_sidebar as render_slug_sidebar
    from app.components.status import render_status_pill, status_pill_html
    from app.components.tabs import render_tabs
    from app.components.feeds import render_activity_feed, render_document_list, render_upload_area
except ImportError:
    from components.buttons import render_action_buttons, render_detail_actions  # type: ignore
    from components.cards import render_card, render_metric_card  # type: ignore
    from components.empty_states import render_empty_state  # type: ignore
    from components.forms import render_dropdown  # type: ignore
    from components.headers import render_page_header  # type: ignore
    from components.layout import (  # type: ignore
        render_filter_bar,
        render_page_shell,
        render_selected_detail_panel,
        render_tab_placeholder,
    )
    from components.modals import confirm_dialog, render_record_detail_dialog  # type: ignore
    from components.tables import render_clickable_table, render_data_table  # type: ignore
    from components.sidebar import render_sidebar as render_slug_sidebar  # type: ignore
    from components.status import render_status_pill, status_pill_html  # type: ignore
    from components.tabs import render_tabs  # type: ignore
    from components.feeds import render_activity_feed, render_document_list, render_upload_area  # type: ignore

__all__ = [
    "confirm_dialog",
    "render_clickable_table",
    "render_record_detail_dialog",
    "render_action_buttons",
    "render_detail_actions",
    "render_card",
    "render_data_table",
    "render_dropdown",
    "render_empty_state",
    "render_filter_bar",
    "render_tab_placeholder",
    "render_metric_card",
    "render_page_header",
    "render_page_shell",
    "render_selected_detail_panel",
    "render_slug_sidebar",
    "render_status_pill",
    "render_tabs",
    "status_pill_html",
    "render_activity_feed",
    "render_document_list",
    "render_upload_area",
]
