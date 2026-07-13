"""
IPS shared UI component library — public API.

Import from this module for the standardized page chrome, tables, cards, badges,
toolbars, detail layouts, and dialogs.
"""

from __future__ import annotations

try:
    from app.ui.action_toolbar import render_action_toolbar, render_filter_toolbar
    from app.ui.data_table import render_data_table
    from app.ui.detail_layout import (
        render_detail_header,
        render_detail_metadata_grid,
        render_detail_modal_header,
        render_detail_tabs,
    )
    from app.ui.metric_card import render_metric_card, render_metric_row
    from app.ui.modal_dialog import (
        build_modal_cache,
        clear_record_modal,
        get_modal_record,
        open_record_modal,
        render_dialog_footer,
        render_dialog_header,
        render_dialog_shell,
        show_modal_if_pending,
    )
    from app.ui.page_header import render_page_brand_header, render_page_header
    from app.ui.status_badge import render_status_badge, status_badge_html
    from app.ui.styles import inject_ips_ui_styles
except ImportError:
    from ui.action_toolbar import render_action_toolbar, render_filter_toolbar  # type: ignore
    from ui.data_table import render_data_table  # type: ignore
    from ui.detail_layout import (  # type: ignore
        render_detail_header,
        render_detail_metadata_grid,
        render_detail_modal_header,
        render_detail_tabs,
    )
    from ui.metric_card import render_metric_card, render_metric_row  # type: ignore
    from ui.modal_dialog import (  # type: ignore
        build_modal_cache,
        clear_record_modal,
        get_modal_record,
        open_record_modal,
        render_dialog_footer,
        render_dialog_header,
        render_dialog_shell,
        show_modal_if_pending,
    )
    from ui.page_header import render_page_brand_header, render_page_header  # type: ignore
    from ui.status_badge import render_status_badge, status_badge_html  # type: ignore
    from ui.styles import inject_ips_ui_styles  # type: ignore

__all__ = [
    "inject_ips_ui_styles",
    "render_page_header",
    "render_page_brand_header",
    "render_data_table",
    "render_detail_header",
    "render_detail_tabs",
    "render_detail_modal_header",
    "render_detail_metadata_grid",
    "render_metric_card",
    "render_metric_row",
    "render_status_badge",
    "status_badge_html",
    "render_action_toolbar",
    "render_filter_toolbar",
    "render_dialog_shell",
    "render_dialog_header",
    "render_dialog_footer",
    "build_modal_cache",
    "clear_record_modal",
    "get_modal_record",
    "open_record_modal",
    "show_modal_if_pending",
]
