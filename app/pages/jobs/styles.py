"""CSS injection helpers for the Jobs module (injected once per session)."""
from __future__ import annotations

import streamlit as st

from .constants import STYLE_KEY_DETAIL_VIEW, STYLE_KEY_RESPONSIVE


def inject_job_database_responsive_styles() -> None:
    """Jobs page tablet/mobile layout overrides. Keeps desktop split/table unchanged."""
    if st.session_state.get(STYLE_KEY_RESPONSIVE):
        return
    st.session_state[STYLE_KEY_RESPONSIVE] = True
    st.markdown(
        """
        <style>
        section[data-testid="stMain"]:has(.ips-job-db-page) [data-testid="stImage"] {
            margin: 0 0 0.08rem 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-job-db-page) .ips-page-title {
            margin: 0 0 0.1rem 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-job-db-page) .ips-page-subtitle {
            margin-bottom: 0.35rem !important;
        }
        .ips-jdb-section-title {
            color: #111827 !important;
            font-size: 0.95rem !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em;
            margin: 0 0 0.3rem 0 !important;
            padding: 0 !important;
            line-height: 1.25 !important;
        }
        .ips-jdb-section-desc {
            color: #4b5563 !important;
            font-size: 0.8125rem !important;
            font-weight: 500 !important;
            margin: 0 0 0.45rem 0 !important;
            padding: 0 !important;
            line-height: 1.4 !important;
        }
        .ips-jdb-muted {
            color: #6b7280 !important;
            font-size: 0.78rem !important;
            font-weight: 500 !important;
            margin: 0.28rem 0 0 0 !important;
            line-height: 1.35 !important;
        }
        section[data-testid="stMain"]:has(.ips-job-db-page) .ips-action-bar-anchor.ips-job-db-quick-actions {
            margin-bottom: 0.28rem !important;
        }
        section[data-testid="stMain"]:has(.ips-job-db-page) .ips-action-bar-anchor.ips-job-db-quick-actions
            ~ div[data-testid="stHorizontalBlock"] {
            gap: 0.4rem !important;
            align-items: stretch !important;
        }
        section[data-testid="stMain"]:has(.ips-job-db-page) .ips-action-bar-anchor.ips-job-db-quick-actions
            ~ div[data-testid="stHorizontalBlock"] .stButton > button {
            min-height: 2.25rem !important;
            padding: 0.36rem 0.7rem !important;
            font-size: 0.875rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-joblist-section-anchor) {
            padding-top: 0.15rem !important;
            padding-bottom: 0.35rem !important;
        }
        section[data-testid="stMain"]:has(.ips-job-db-page) .ips-job-action-bar-anchor {
            display: block;
            border-top: 1px solid rgba(15, 23, 42, 0.07);
            margin: 0.22rem 0 0.12rem 0;
            padding-top: 0.28rem;
        }
        p.ips-job-list-view-label {
            margin: 0.35rem 0 0.1rem 0 !important;
            font-size: 0.76rem !important;
            font-weight: 600 !important;
            color: #6b7280 !important;
        }
        .ips-job-card-title {
            color: #111827 !important;
            font-size: 1rem;
            font-weight: 700;
            line-height: 1.25;
            margin: 0 0 0.1rem 0;
            overflow-wrap: anywhere;
        }
        .ips-job-card-meta {
            color: #4b5563 !important;
            font-size: 0.88rem;
            line-height: 1.45;
            margin: 0.15rem 0 0.4rem;
            overflow-wrap: anywhere;
        }
        .ips-job-card-pill {
            display: inline-flex;
            align-items: center;
            border: 1px solid #cbd5e1;
            border-radius: 999px;
            color: #334155 !important;
            background: #f8fafc;
            font-size: 0.78rem;
            font-weight: 650;
            line-height: 1;
            margin: 0.2rem 0.25rem 0.1rem 0;
            max-width: 100%;
            padding: 0.35rem 0.55rem;
            overflow-wrap: anywhere;
        }
        .ips-status-badge {
            align-items: center;
            background: color-mix(in srgb, var(--ips-status-color) 12%, white);
            border: 1px solid color-mix(in srgb, var(--ips-status-color) 38%, white);
            border-radius: 999px;
            color: var(--ips-status-color);
            display: inline-flex;
            font-size: 0.78rem;
            font-weight: 700;
            line-height: 1;
            margin: 0.2rem 0.25rem 0.1rem 0;
            padding: 0.35rem 0.55rem;
            white-space: nowrap;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="column"] .stMarkdown,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="column"] .stMarkdown p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="column"] .stMarkdown span,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="column"] [data-testid="stText"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="column"] pre {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="stCaptionContainer"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="stCaptionContainer"] p {
            color: #4b5563 !important;
        }
        div[data-testid="stVerticalBlock"]:has(.ips-job-table-scroll-anchor),
        div[data-testid="element-container"]:has(.ips-job-table-scroll-anchor) {
            overflow-x: auto !important;
            -webkit-overflow-scrolling: touch;
            max-width: 100%;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            align-items: center !important;
            column-gap: 0.75rem !important;
            width: 100% !important;
            min-width: 1260px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            min-width: 0 !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) {
            flex: 0 0 auto !important; min-width: 44px !important; max-width: 56px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
            min-width: 76px !important; max-width: 110px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3) {
            min-width: 160px !important; max-width: 280px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(4) {
            min-width: 140px !important; max-width: 220px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5) {
            min-width: 120px !important; max-width: 200px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(6) {
            min-width: 120px !important; max-width: 200px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(7) {
            min-width: 100px !important; max-width: 150px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(8) {
            min-width: 120px !important; max-width: 200px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(9) {
            min-width: 100px !important; max-width: 180px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(10) {
            min-width: 88px !important; max-width: 120px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(11) {
            flex: 0 0 auto !important; min-width: 52px !important; max-width: 76px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(12) {
            flex: 0 0 auto !important;
            min-width: 52px !important;
            max-width: 72px !important;
            position: relative !important;
            z-index: 2 !important;
            isolation: isolate !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) .ips-job-list-cell {
            display: block;
            box-sizing: border-box;
            width: 100%;
            max-width: 100%;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor) .ips-job-money-cell {
            text-align: right;
            font-variant-numeric: tabular-nums;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] > div[data-testid="column"] .stMarkdown {
            min-width: 0 !important; overflow: hidden !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stHorizontalBlock"] [data-testid="column"] p:has(.ips-job-list-cell) {
            margin: 0 !important; min-width: 0 !important; overflow: hidden !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-desktop-table-anchor)
            [data-testid="stCaptionContainer"] p {
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            min-width: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) h5,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) .stMarkdown,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-list-anchor) .stMarkdown p,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stMarkdown,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stMarkdown p {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) {
            background: #ffffff !important;
            border: 1px solid rgba(15, 23, 42, 0.08) !important;
            border-radius: 8px !important;
            margin-bottom: 0.28rem !important;
            padding: 0.4rem 0.52rem !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-card-anchor) .stButton > button,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) .stButton > button,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) .stButton > button {
            min-height: 48px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="base-input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) textarea,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="base-input"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stFileUploader"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) textarea {
            background: #ffffff !important;
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] > div > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] > div > div {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] span,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] span,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] input {
            background: transparent !important;
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-baseweb="select"] *,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-baseweb="select"] *,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stFileUploader"] * {
            color: #111827 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) input,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) textarea {
            max-width: 100% !important;
            min-height: 42px !important;
            box-sizing: border-box !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) {
            background: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 12px !important;
            color: #111827 !important;
            padding: 0.75rem !important;
            margin-top: 0.5rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) h3,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) h4 {
            color: #111827 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"],
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            align-items: center !important;
            gap: 6px !important;
            padding: 6px !important;
            margin: 0 0 0.75rem 0 !important;
            background: #d1d5db !important;
            border: none !important;
            border-bottom: none !important;
            border-radius: 10px !important;
            box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.05) !important;
            overflow-x: auto !important;
            overflow-y: visible !important;
            scrollbar-width: thin;
            -webkit-overflow-scrolling: touch !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"] {
            flex: 0 1 auto !important;
            min-height: 0 !important;
            height: auto !important;
            min-width: 0 !important;
            margin: 0 !important;
            padding: 8px 14px !important;
            border-radius: 10px !important;
            white-space: nowrap !important;
            background: transparent !important;
            border: 1px solid transparent !important;
            box-shadow: none !important;
            color: #111827 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"] p {
            color: #111827 !important;
            font-weight: 500 !important;
            margin: 0 !important;
            overflow: visible !important;
            text-overflow: clip !important;
            white-space: nowrap !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"],
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button[aria-selected="true"],
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-bottom-color: #cbd5e1 !important;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 1px 2px rgba(15, 23, 42, 0.04) !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button[aria-selected="true"] p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button[aria-selected="true"] p,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"][aria-selected="true"] p {
            color: #111827 !important;
            font-weight: 600 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button:hover:not(:disabled):not([aria-selected="true"]),
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button:hover:not(:disabled):not([aria-selected="true"]),
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
            background: rgba(255, 255, 255, 0.42) !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) {
            background: #d1d5db !important;
            border: 1px solid #c4c4cc !important;
            border-radius: 12px !important;
            padding: 0.65rem 0.75rem 0.75rem !important;
            margin: 0 0 0.85rem 0 !important;
            box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.04) !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) h4 {
            color: #111827 !important; font-weight: 700 !important; margin: 0 0 0.5rem 0 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .stCaption,
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .stCaption p {
            color: #374151 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .ips-jes-card {
            background: #ffffff !important;
            border-radius: 10px !important;
            padding: 0.65rem 0.85rem !important;
            margin: 0 0 0.5rem 0 !important;
            border: 1px solid #e5e7eb !important;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .ips-jes-grid {
            display: grid !important;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)) !important;
            gap: 0.45rem 1rem !important;
            color: #111827 !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .ips-jes-lbl {
            display: block !important;
            font-weight: 700 !important;
            font-size: 0.78rem !important;
            color: #374151 !important;
            margin-bottom: 0.12rem !important;
        }
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-estimate-summary-host) .ips-jes-val {
            display: block !important;
            font-weight: 600 !important;
            font-size: 0.92rem !important;
            color: #111827 !important;
            line-height: 1.35 !important;
            overflow-wrap: anywhere !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="column"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor) [data-testid="column"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-joblist-section-anchor) [data-testid="column"] {
            min-width: 0 !important;
        }
        @media (max-width: 1260px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor)
                div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important; gap: 0.65rem !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor)
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 calc(50% - 0.65rem) !important;
                max-width: calc(50% - 0.35rem) !important;
                min-width: min(260px, 100%) !important;
                width: calc(50% - 0.35rem) !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor)
                div[data-testid="stTabs"] div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 calc(50% - 0.65rem) !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor)
                [data-testid="stWidgetLabel"] p {
                font-size: 0.9rem !important;
            }
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-joblist-section-anchor) h5 {
            margin: 0 0 0.28rem 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-joblist-section-anchor) .ips-job-list-view-label {
            margin: 0 !important; padding: 0 !important;
            font-size: 0.8rem !important; font-weight: 600 !important;
            color: #374151 !important; line-height: 1.2 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-joblist-section-anchor)
            div[data-testid="stHorizontalBlock"]:has([data-testid="stRadio"]) {
            margin-top: 0.05rem !important; margin-bottom: 0.1rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-joblist-section-anchor)
            [data-testid="stElementContainer"] {
            margin-bottom: 0.14rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-joblist-section-anchor)
            .ips-job-desktop-table-anchor {
            display: block; margin-top: 0 !important; padding-top: 0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-joblist-section-anchor)
            [data-testid="stWidgetLabel"] p {
            font-size: 0.78rem !important; margin-bottom: 0.08rem !important;
        }
        @media (max-width: 1100px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor)
                div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important; gap: 0.75rem !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor)
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex: 1 1 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                width: 100% !important;
            }
        }
        @media (max-width: 640px) {
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-filter-anchor)
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor)
                div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                flex-basis: 100% !important; max-width: 100% !important;
                min-width: 0 !important; width: 100% !important;
            }
            section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"] button,
            section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tablist"] button,
            section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-edit-panel-anchor) [data-testid="stTabs"] [role="tab"] {
                font-size: 0.86rem !important; padding: 7px 12px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_job_detail_view_page_css() -> None:
    """Sticky-header + hero card CSS for the read-only job detail page."""
    if st.session_state.get(STYLE_KEY_DETAIL_VIEW):
        return
    st.session_state[STYLE_KEY_DETAIL_VIEW] = True
    st.markdown(
        """
        <style>
        section[data-testid="stMain"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-job-detail-sticky-host) {
            position: sticky;
            top: 0.5rem;
            z-index: 50;
            background: linear-gradient(180deg, #f8fafc 92%, transparent);
            padding-bottom: 0.35rem;
            margin-bottom: 0.25rem;
        }
        .ips-job-detail-hero {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 1.1rem 1.25rem;
            margin: 0.5rem 0 1rem 0;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
        }
        .ips-job-detail-hero h1 {
            font-size: 1.55rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 0.35rem 0;
            line-height: 1.2;
        }
        .ips-job-detail-meta {
            color: #475569;
            font-size: 0.95rem;
            line-height: 1.5;
        }
        .ips-job-detail-section-title {
            font-size: 1.12rem;
            font-weight: 750;
            color: #0f172a;
            margin: 0 0 0.5rem 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
