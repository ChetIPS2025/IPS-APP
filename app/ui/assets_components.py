"""Assets management page — shared layout, badges, and summary visuals."""

from __future__ import annotations

import html

import streamlit as st

IPS_ASSETS_PAGE_STYLES_KEY = "ips_assets_page_styles_v24"

_STATUS_PILL: dict[str, tuple[str, str, str]] = {
    "in service": ("#15803d", "#dcfce7", "In Service"),
    "out of service": ("#b91c1c", "#fee2e2", "Out of Service"),
    "maintenance": ("#b45309", "#fef3c7", "Maintenance"),
    "retired": ("#475569", "#f1f5f9", "Retired"),
}

_TAB_ICONS: dict[str, str] = {
    "Overview": "▦",
    "Kit / Contents": "🧰",
    "Maintenance": "🔧",
    "Documents": "📄",
    "Assignments": "👤",
    "Depreciation": "📉",
    "Notes": "📝",
    "Activity": "🕐",
}


def inject_assets_page_styles() -> None:
    try:
        from app.ui.clean_table import inject_clean_table_css
    except ImportError:
        from ui.clean_table import inject_clean_table_css  # type: ignore
    inject_clean_table_css()
    if st.session_state.get(IPS_ASSETS_PAGE_STYLES_KEY):
        return
    st.session_state[IPS_ASSETS_PAGE_STYLES_KEY] = True
    try:
        from app.ui.page_shell import inject_ips_dashboard_layout
    except ImportError:
        from ui.page_shell import inject_ips_dashboard_layout  # type: ignore
    inject_ips_dashboard_layout()
    st.markdown(
        """
        <style>
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-header-anchor),
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-filter-anchor),
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-anchor) {
            background: #ffffff !important;
            border: 1px solid #e5eaf2 !important;
            border-radius: 14px !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
            margin-bottom: 0.65rem !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-header-anchor) > div {
            padding: 0.85rem 1rem !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-filter-anchor) > div {
            padding: 0.6rem 0.85rem !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-anchor) > div {
            padding: 0.35rem 0.65rem 0.5rem !important;
        }
        /* Assets header: Export | CSV Template | Import CSV | Quick Add | New Asset */
        .ips-assets-page-header-actions {
            display: none !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions) .ips-page-actions-marker {
            display: none !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions) {
            align-items: flex-end !important;
            justify-content: flex-end !important;
            min-width: 0 !important;
            overflow-x: auto !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions)
        [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: flex-end !important;
            gap: 0.45rem !important;
            width: max-content !important;
            max-width: 100% !important;
            margin-left: auto !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions)
        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            flex: 0 0 auto !important;
            width: auto !important;
            min-width: max-content !important;
            max-width: none !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions) .stButton,
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions) [data-testid="stDownloadButton"] {
            margin: 0 !important;
            width: auto !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions) .stButton > button,
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions) [data-testid="stDownloadButton"] > button {
            width: auto !important;
            min-width: max-content !important;
            max-width: none !important;
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
            font-weight: 600 !important;
            padding-left: 0.85rem !important;
            padding-right: 0.85rem !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions) .stButton > button p,
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions) [data-testid="stButton"] > button p,
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions) [data-testid="stDownloadButton"] > button p,
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions) [data-testid="stDownloadButton"] > button span {
            white-space: nowrap !important;
            word-break: keep-all !important;
            overflow-wrap: normal !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions)
        [class*="st-key-ast_export"] .stButton > button,
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions)
        [class*="st-key-ast_hand_tool_csv_template"] [data-testid="stDownloadButton"] > button,
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions)
        [class*="st-key-ast_hand_tool_import"] .stButton > button,
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions)
        [class*="st-key-ast_new"] .stButton > button {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            color: #374151 !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        [data-testid="column"]:has(.ips-assets-page-header-actions)
        [class*="st-key-ast_quick_add"] .stButton > button[kind="primary"] {
            background: #2563eb !important;
            border: 1px solid #2563eb !important;
            color: #ffffff !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap):not(:has(.ips-hand-tools-table-wrap))
        button[data-testid="stBaseButton-popover"] {
            min-width: 2rem !important;
            padding: 0.15rem 0.35rem !important;
            font-weight: 700 !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        .ips-assets-title {
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            word-break: normal !important;
        }
        /* Assets table row Open — fixed-width horizontal blue label */
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap):not(:has(.ips-hand-tools-table-wrap))
        [data-testid="column"]:has(.asset-open-button),
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap):not(:has(.ips-hand-tools-table-wrap))
        [data-testid="column"]:has([class*="st-key-ast_open_"]) {
            flex: 0 0 auto !important;
            width: auto !important;
            min-width: 86px !important;
            max-width: none !important;
            overflow: visible !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        .asset-open-button,
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        .asset-open-button * {
            writing-mode: horizontal-tb !important;
            word-break: normal !important;
            white-space: nowrap !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        [class*="st-key-ast_open_"] [data-testid="stButton"],
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        [class*="st-key-ast_open_"] .stButton {
            width: auto !important;
            min-width: 80px !important;
            max-width: none !important;
            overflow: visible !important;
            margin: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        [class*="st-key-ast_open_"] [data-testid="stButton"] > button,
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        [class*="st-key-ast_open_"] .stButton > button {
            background: #2563eb !important;
            color: #ffffff !important;
            border: 1px solid #2563eb !important;
            border-radius: 8px !important;
            height: 36px !important;
            min-height: 36px !important;
            width: 80px !important;
            min-width: 80px !important;
            max-width: 80px !important;
            padding: 0 14px !important;
            font-size: 0.8125rem !important;
            font-weight: 700 !important;
            line-height: 1 !important;
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
            writing-mode: horizontal-tb !important;
            word-break: normal !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        [class*="st-key-ast_open_"] [data-testid="stButton"] > button p,
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        [class*="st-key-ast_open_"] .stButton > button p,
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        [class*="st-key-ast_open_"] [data-testid="stButton"] > button span,
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        [class*="st-key-ast_open_"] .stButton > button span {
            white-space: nowrap !important;
            word-break: normal !important;
            overflow-wrap: normal !important;
            writing-mode: horizontal-tb !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        [class*="st-key-ast_open_"] [data-testid="stButton"] > button:hover,
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap)
        [class*="st-key-ast_open_"] .stButton > button:hover {
            background: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
            color: #ffffff !important;
        }
        /* Small Hand Tools tab — CSS grid rows with fixed Actions column */
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-header),
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) {
            display: grid !important;
            grid-template-columns:
                28px
                56px
                minmax(280px, 2fr)
                minmax(130px, 0.85fr)
                72px
                72px
                minmax(130px, 0.85fr)
                minmax(140px, 0.9fr)
                110px
                140px !important;
            column-gap: 14px !important;
            align-items: center !important;
            width: 100% !important;
            box-sizing: border-box !important;
            flex-wrap: nowrap !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) {
            min-height: 0 !important;
            padding: 0.15rem 0 !important;
            margin: 0 !important;
            border-bottom: 1px solid #f1f5f9 !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-header) > [data-testid="column"],
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"] {
            flex: none !important;
            width: auto !important;
            min-width: 0 !important;
            max-width: none !important;
            overflow: visible !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child,
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-header) > [data-testid="column"]:last-child {
            min-width: 140px !important;
            overflow: visible !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
        [data-testid="stVerticalBlock"],
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
        [data-testid="stElementContainer"] {
            width: 100% !important;
            min-width: 140px !important;
            overflow: visible !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap .ips-hand-tools-cell,
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap .ips-assets-muted.ips-hand-tools-cell {
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            word-break: normal !important;
            line-height: 1.25 !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap .ips-hand-tools-qty {
            text-align: center !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap .ips-asset-status-pill {
            white-space: nowrap !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
        [data-testid="stPopover"],
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
        .stButton {
            width: 100% !important;
            min-width: 5.5rem !important;
            max-width: none !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
        button[data-testid="stBaseButton-popover"] {
            display: inline-flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: center !important;
            min-height: 1.85rem !important;
            height: 1.85rem !important;
            min-width: 5.5rem !important;
            width: 100% !important;
            max-width: none !important;
            padding: 0 0.85rem !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            white-space: nowrap !important;
            writing-mode: horizontal-tb !important;
            word-break: normal !important;
            overflow-wrap: normal !important;
            color: #ffffff !important;
            background: #2563eb !important;
            border: 1px solid #2563eb !important;
            box-shadow: none !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
        button[data-testid="stBaseButton-popover"] p,
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
        button[data-testid="stBaseButton-popover"] span,
        section[data-testid="stMain"]:has(.ips-assets-page)
        .st-key-assets_hand_tools_table_wrap
        [data-testid="stHorizontalBlock"]:has(.small-tools-table-row) > [data-testid="column"]:last-child
        button[data-testid="stBaseButton-popover"] div {
            display: inline !important;
            white-space: nowrap !important;
            word-break: keep-all !important;
            overflow-wrap: normal !important;
            line-height: 1.1 !important;
        }
        .ips-assets-header-inner {
            display: flex;
            align-items: flex-start;
            gap: 0.7rem;
            min-width: 0;
        }
        .ips-assets-header-icon {
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 10px;
            background: #eff6ff;
            color: #2563eb;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            flex-shrink: 0;
        }
        .ips-assets-header-title {
            margin: 0;
            font-size: 1.35rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.15;
        }
        .ips-assets-header-sub {
            margin: 0.15rem 0 0;
            font-size: 0.8125rem;
            color: #6b7280;
            font-weight: 500;
        }
        /* Table header row — light gray band */
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-assets-th-row) {
            background: #ffffff !important;
            border-bottom: 1px solid #e5eaf2 !important;
            margin: 0 -0.35rem 0.15rem -0.35rem !important;
            padding: 0.2rem 0.35rem !important;
            border-radius: 6px 6px 0 0 !important;
        }
        .ips-assets-th {
            color: #9ca3af !important;
            font-size: 0.65rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 0 !important;
            padding: 0.35rem 0 !important;
        }
        .ips-assets-th-sort {
            opacity: 0.5;
            font-size: 0.58rem;
            margin-left: 0.15rem;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-assets-row-selected) {
            background: #eff6ff !important;
            border-left: 4px solid #2563eb !important;
            border-radius: 0 6px 6px 0 !important;
            margin: 0 -0.35rem !important;
            padding: 0.18rem 0 0.18rem 0.35rem !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-assets-row-marker):not(:has(.ips-assets-row-selected)) {
            border-bottom: 1px solid #f1f5f9;
        }
        section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-link-btn button {
            color: #2563eb !important;
            font-weight: 600 !important;
            font-size: 0.8125rem !important;
            padding: 0 !important;
            min-height: 1.35rem !important;
            height: auto !important;
            border: none !important;
            background: #ffffff !important;
            box-shadow: none !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }
        .ips-assets-num-qr-cell {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            min-width: 0;
        }
        .ips-assets-row-qr {
            width: 32px;
            height: 32px;
            flex-shrink: 0;
            border: 1px solid #e5eaf2;
            border-radius: 4px;
            background: #ffffff;
            image-rendering: pixelated;
        }
        .ips-assets-num-label {
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-name-cell {
            font-size: 0.8125rem;
            color: #111827;
            font-weight: 600;
        }
        section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-muted-cell {
            font-size: 0.8rem;
            color: #6b7280;
            font-weight: 500;
        }
        section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-action-btn button {
            min-height: 1.75rem !important;
            width: 1.75rem !important;
            padding: 0 !important;
            font-size: 0.95rem !important;
            border-radius: 6px !important;
            border: 1px solid #e5eaf2 !important;
            background: #ffffff !important;
            color: #64748b !important;
        }
        /* Detail panel inside table card */
        .ips-assets-detail-wrap {
            margin: 0.65rem 0 0.15rem;
            padding: 0.85rem 0.75rem 0.75rem;
            border: 1px solid #93c5fd;
            border-radius: 14px;
            background: #ffffff;
            box-shadow: 0 1px 4px rgba(37, 99, 235, 0.08);
        }
        .ips-assets-detail-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.75rem;
            flex-wrap: wrap;
            padding-bottom: 0.7rem;
            border-bottom: 1px solid #e5eaf2;
            margin-bottom: 0.55rem;
        }
        .ips-assets-detail-id-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex-wrap: wrap;
        }
        .ips-assets-detail-id {
            margin: 0;
            font-size: 1.05rem;
            font-weight: 800;
            color: #111827;
            line-height: 1.2;
        }
        .ips-assets-detail-name-lg {
            margin: 0.35rem 0 0;
            font-size: 1.12rem;
            font-weight: 700;
            color: #111827;
            line-height: 1.25;
        }
        .ips-assets-meta-strip {
            display: flex;
            align-items: flex-start;
            gap: 1.25rem;
            flex-wrap: wrap;
            flex: 1;
            justify-content: center;
            padding: 0.25rem 0.5rem 0;
        }
        .ips-assets-meta-block .lbl {
            display: block;
            font-size: 0.65rem;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 600;
        }
        .ips-assets-meta-block .val {
            display: block;
            font-size: 0.8125rem;
            color: #111827;
            font-weight: 600;
            margin-top: 0.08rem;
        }
        /* Tab bar */
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-assets-tabs-anchor) {
            border-bottom: 1px solid #e5eaf2 !important;
            margin: 0.35rem 0 0.65rem !important;
            gap: 0.15rem !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-assets-tabs-anchor) .stButton > button {
            background: #ffffff !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            color: #6b7280 !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            min-height: 2.1rem !important;
            padding: 0.35rem 0.5rem 0.55rem !important;
            border-bottom: 2px solid transparent !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-assets-tabs-anchor) .stButton > button[kind="primary"] {
            color: #2563eb !important;
            border-bottom: 2px solid #2563eb !important;
            background: #ffffff !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-assets-tabs-anchor) .stButton > button p {
            margin: 0 !important;
        }
        .ips-assets-summary-card {
            background: #ffffff;
            border: 1px solid #e5eaf2;
            border-radius: 12px;
            padding: 0.75rem 0.85rem;
            height: 100%;
            box-sizing: border-box;
        }
        .ips-assets-summary-card h4 {
            margin: 0 0 0.55rem;
            font-size: 0.84rem;
            font-weight: 700;
            color: #111827;
        }
        .ips-assets-kv { width: 100%; border-collapse: collapse; }
        .ips-assets-kv td {
            padding: 0.3rem 0;
            font-size: 0.78rem;
            vertical-align: top;
        }
        .ips-assets-kv td.k {
            color: #6b7280;
            width: 46%;
            font-weight: 500;
        }
        .ips-assets-kv td.v {
            color: #111827;
            font-weight: 600;
        }
        .ips-assets-img-wrap {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #e5eaf2;
            background: #ffffff;
            min-height: 160px;
        }
        .ips-assets-img-empty {
            text-align: center;
            color: #94a3b8;
            font-size: 0.78rem;
            font-weight: 600;
            padding: 2rem 0.75rem;
        }
        .ips-assets-maint-section {
            margin-top: 0.85rem;
            padding-top: 0.65rem;
            border-top: 1px solid #e5eaf2;
        }
        .ips-assets-maint-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.45rem;
        }
        .ips-assets-maint-head h4 {
            margin: 0;
            font-size: 0.84rem;
            font-weight: 700;
            color: #111827;
        }
        .ips-assets-maint-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.78rem;
        }
        .ips-assets-maint-table th {
            text-align: left;
            color: #9ca3af;
            font-size: 0.65rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            padding: 0.4rem 0.35rem;
            border-bottom: 1px solid #e5eaf2;
        }
        .ips-assets-maint-table td {
            padding: 0.45rem 0.35rem;
            color: #374151;
            border-bottom: 1px solid #f1f5f9;
            vertical-align: middle;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .ips-assets-detail-actions .stButton > button {
            min-height: 2rem !important;
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .ips-assets-detail-actions .ips-assets-maint-primary button {
            background: #2563eb !important;
            border-color: #2563eb !important;
            color: #fff !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        .ips-assets-clear-filters button {
            background: #fff !important;
            border: 1px solid #e2e8f0 !important;
            color: #374151 !important;
            font-size: 0.8rem !important;
        }
        .asset-meta-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.35rem 0.85rem;
        }
        .asset-meta-cell .asset-meta-label,
        .ips-assets-meta-block .lbl {
            font-size: 0.65rem;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            font-weight: 600;
        }
        .asset-meta-cell .asset-meta-value,
        .ips-assets-meta-block .val {
            font-size: 0.8125rem;
            color: #111827;
            font-weight: 600;
            margin-top: 0.06rem;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-filter-anchor) input {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
            min-height: 2.1rem !important;
            font-size: 0.84rem !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-filter-anchor)
        [data-baseweb="select"] > div {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
            min-height: 2.1rem !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-view-all-maint button {
            background: #ffffff !important;
            border: none !important;
            color: #2563eb !important;
            font-weight: 600 !important;
            font-size: 0.8rem !important;
            box-shadow: none !important;
            text-decoration: none !important;
            justify-content: flex-end !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-view-all-maint button:hover {
            text-decoration: underline !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stHorizontalBlock"]:has(.ips-assets-table-head-row) {
            background: #ffffff !important;
            border-bottom: 1px solid #e5eaf2 !important;
            margin: 0 -0.35rem 0.12rem -0.35rem !important;
            padding: 0.22rem 0.35rem !important;
            border-radius: 6px 6px 0 0 !important;
        }
        .ips-assets-page .ips-assets-summary-table.ips-data-table-html .ips-assets-table-head-row,
        .ips-assets-page .ips-assets-summary-table.ips-data-table-html .ips-assets-row {
            display: grid !important;
            box-sizing: border-box !important;
            align-items: center;
        }
        .ips-assets-page .ips-assets-summary-table.ips-data-table-html .ips-assets-row {
            min-height: 2.75rem;
            cursor: pointer;
        }
        .ips-assets-page .ips-assets-summary-table.ips-data-table-html .ips-assets-row:hover {
            background: #eef5ff;
        }
        .ips-assets-page .ips-assets-summary-table.ips-data-table-html .ips-assets-row.selected {
            background: #eef5ff;
            border-left: 4px solid #2563eb;
        }
        .ips-assets-page .ips-assets-summary-table .ips-assets-th {
            margin: 0;
        }
        /* Assets list: invisible full-row select button layered under HTML row */
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-click-table)
        div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap) {
            position: relative !important;
            min-height: 2.75rem !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-click-table)
        div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
        > [data-testid="stElementContainer"] {
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-click-table)
        div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn) {
            height: 0 !important;
            min-height: 0 !important;
            max-height: 0 !important;
            overflow: hidden !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-click-table)
        div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
        + [data-testid="stElementContainer"] {
            position: absolute !important;
            inset: 0 !important;
            z-index: 1 !important;
            height: auto !important;
            min-height: 2.75rem !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: visible !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            pointer-events: auto !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-click-table)
        div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
        + [data-testid="stElementContainer"] [data-testid="stButton"],
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-click-table)
        div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
        + [data-testid="stElementContainer"] .stButton {
            width: 100% !important;
            height: 100% !important;
            min-height: 2.75rem !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-click-table)
        div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
        + [data-testid="stElementContainer"] [data-testid="stButton"] > button,
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-click-table)
        div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-clean-row-select-btn)
        + [data-testid="stElementContainer"] .stButton > button {
            width: 100% !important;
            height: 100% !important;
            min-height: 2.75rem !important;
            margin: 0 !important;
            padding: 0 !important;
            opacity: 0 !important;
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
            color: transparent !important;
            cursor: pointer !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-click-table)
        div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
        > [data-testid="stElementContainer"]:has(.ips-assets-row) {
            position: absolute !important;
            inset: 0 !important;
            z-index: 2 !important;
            pointer-events: none !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        section[data-testid="stMain"]:has(.ips-assets-page)
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-click-table)
        div[data-testid="stVerticalBlock"]:has(.ips-clean-row-wrap)
        .ips-assets-row {
            cursor: pointer;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def render_assets_header_inner_html() -> str:
    return (
        '<div class="ips-assets-header-inner">'
        '<div class="ips-assets-header-icon" aria-hidden="true">🚛</div>'
        "<div>"
        '<p class="ips-assets-header-title">Assets</p>'
        '<p class="ips-assets-header-sub">Track and manage all company assets and equipment.</p>'
        "</div></div>"
    )

def table_header_html(label: str, *, sortable: bool = True) -> str:
    sort = '<span class="ips-assets-th-sort">⇅</span>' if sortable else ""
    return f'<p class="ips-assets-th">{html.escape(label)}{sort}</p>'


def asset_number_cell_html(asset: dict) -> str:
    """Asset # column: compact QR thumbnail beside the asset number."""
    try:
        from app.services.asset_qr import qr_embed_subject, qr_thumb_data_uri
    except ImportError:
        from services.asset_qr import qr_embed_subject, qr_thumb_data_uri  # type: ignore

    num = str(asset.get("asset_number") or "—")
    num_esc = html.escape(num)
    qr_asset = {
        **asset,
        "asset_id": str(asset.get("asset_number") or asset.get("asset_id") or "").strip(),
    }
    subject = qr_embed_subject(qr_asset)
    uri = qr_thumb_data_uri(subject) if subject else ""
    if not uri:
        return f'<span class="ips-clean-link">{num_esc}</span>'
    alt = html.escape(f"QR code for {num}", quote=True)
    return (
        f'<span class="ips-assets-num-qr-cell">'
        f'<img class="ips-assets-row-qr" src="{uri}" alt="{alt}" width="32" height="32" loading="lazy" />'
        f'<span class="ips-clean-link ips-assets-num-label">{num_esc}</span>'
        f"</span>"
    )

def status_pill_category(status: str) -> str:
    s = str(status or "").strip().lower()
    if s in ("retired", "inactive"):
        return "Retired"
    if s in ("maintenance", "in shop"):
        return "Maintenance"
    if s in ("out for repair", "lost"):
        return "Out of Service"
    return "In Service"

def status_badge_html(status: str) -> str:
    cat = status_pill_category(status)
    fg, bg, label = _STATUS_PILL.get(cat.lower(), ("#64748b", "#f1f5f9", cat))
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:999px;'
        f"font-size:0.68rem;font-weight:700;color:{fg};background:{bg};"
        f'white-space:nowrap;">{html.escape(label)}</span>'
    )

def completed_badge_html() -> str:
    fg, bg, _ = _STATUS_PILL["in service"]
    return (
        f'<span style="display:inline-block;padding:3px 10px;border-radius:999px;'
        f"font-size:0.68rem;font-weight:700;color:{fg};background:{bg};"
        f'white-space:nowrap;">Completed</span>'
    )

def summary_card_html(
    title: str,
    rows: list[tuple[str, str]],
    *,
    html_value_keys: frozenset[str] | None = None,
) -> str:
    raw_keys = html_value_keys or frozenset()
    body_parts: list[str] = []
    for k, v in rows:
        if k in raw_keys:
            val_cell = f'<td class="v">{v}</td>'
        else:
            val_cell = f'<td class="v">{html.escape(str(v or "—"))}</td>'
        body_parts.append(f'<tr><td class="k">{html.escape(k)}</td>{val_cell}</tr>')
    body = "".join(body_parts)
    return (
        f'<div class="ips-assets-summary-card">'
        f"<h4>{html.escape(title)}</h4>"
        f'<table class="ips-assets-kv"><tbody>{body}</tbody></table>'
        "</div>"
    )

def detail_header_html(*, asset_id: str, asset_name: str, status: str) -> str:
    return (
        '<div class="ips-assets-detail-top-left">'
        '<div class="ips-assets-detail-id-row">'
        f'<span class="ips-assets-detail-id">{html.escape(asset_id)}</span>'
        f"{status_badge_html(status)}"
        "</div>"
        f'<p class="ips-assets-detail-name-lg">{html.escape(asset_name)}</p>'
        "</div>"
    )

def detail_meta_grid_html(items: list[tuple[str, str]]) -> str:
    """Render compact asset detail metadata grid."""
    safe_items = items or []
    cells: list[str] = []
    for label, value in safe_items:
        cells.append(
            f'<div class="asset-meta-cell">'
            f'<div class="asset-meta-label">{html.escape(str(label or ""))}</div>'
            f'<div class="asset-meta-value">{html.escape(str(value if value is not None else "—"))}</div>'
            "</div>"
        )
    return f'<div class="asset-meta-grid">{"".join(cells)}</div>'


def detail_meta_strip_html(items: list[tuple[str, str]]) -> str:
    """Horizontal metadata row (reference mockup center strip)."""
    blocks = "".join(
        f'<div class="ips-assets-meta-block">'
        f'<span class="lbl">{html.escape(str(k))}</span>'
        f'<span class="val">{html.escape(str(v or "—"))}</span>'
        "</div>"
        for k, v in (items or [])
    )
    return f'<div class="ips-assets-meta-strip">{blocks}</div>'


def maintenance_table_html(rows: list[dict[str, str]]) -> str:
    if not rows:
        return '<p style="color:#9ca3af;font-size:0.8rem;margin:0;">No maintenance records yet.</p>'
    head = (
        "<tr><th>Date</th><th>Type</th><th>Description</th><th>Performed By</th>"
        "<th>Cost</th><th>Next Due</th><th>Status</th></tr>"
    )
    body_parts: list[str] = []
    for r in rows:
        st_cell = r.get("status_html") or completed_badge_html()
        body_parts.append(
            "<tr>"
            f"<td>{html.escape(r.get('date', '—'))}</td>"
            f"<td>{html.escape(r.get('type', '—'))}</td>"
            f"<td>{html.escape(r.get('description', '—'))}</td>"
            f"<td>{html.escape(r.get('performed_by', '—'))}</td>"
            f"<td>{html.escape(r.get('cost', '—'))}</td>"
            f"<td>{html.escape(r.get('next_due', '—'))}</td>"
            f"<td>{st_cell}</td>"
            "</tr>"
        )
    return (
        '<table class="ips-assets-maint-table"><thead>'
        f"{head}</thead><tbody>{''.join(body_parts)}</tbody></table>"
    )

def tab_button_label(tab: str) -> str:
    icon = _TAB_ICONS.get(tab, "")
    return f"{icon}  {tab}" if icon else tab
