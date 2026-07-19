"""Kit UI styles and status pills."""

from __future__ import annotations

import html

import streamlit as st

from app.ui.css_inject import inject_css_once

_KIT_STATUS_CLASS = {
    "present": "ips-kit-status-present",
    "missing": "ips-kit-status-missing",
    "damaged": "ips-kit-status-damaged",
    "checked out": "ips-kit-status-checked-out",
    "needs repair": "ips-kit-status-needs-repair",
    "needs replacement": "ips-kit-status-needs-replacement",
    "retired": "ips-kit-status-retired",
    "good": "ips-kit-status-present",
    "new": "ips-kit-status-present",
    "fair": "ips-kit-status-needs-repair",
}


def kit_item_status_pill_html(status: str) -> str:
    key = str(status or "").strip().lower()
    cls = _KIT_STATUS_CLASS.get(key, "ips-kit-status-neutral")
    label = html.escape(str(status or "—"))
    return f'<span class="ips-kit-status-pill {cls}">{label}</span>'


def kit_badge_html() -> str:
    return '<span class="ips-kit-badge">Kit</span>'


def inject_kit_ui_styles() -> None:
    if not inject_css_once("ips-kit-ui-styles-v3"):
        return
    st.markdown(
        """
        <style id="ips-kit-ui-styles-v3">
        .ips-kit-badge {
            display: inline-block;
            margin-left: 0.35rem;
            padding: 0.08rem 0.4rem;
            border-radius: 999px;
            font-size: 0.65rem;
            font-weight: 700;
            color: #1d4ed8;
            background: #dbeafe;
            border: 1px solid #93c5fd;
            vertical-align: middle;
        }
        .ips-kit-summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
            gap: 0.45rem;
            margin: 0.35rem 0 0.65rem;
        }
        .ips-kit-metric {
            background: #fff;
            border: 1px solid #e5eaf2;
            border-radius: 10px;
            padding: 0.45rem 0.55rem;
        }
        .ips-kit-metric-label {
            font-size: 0.68rem;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }
        .ips-kit-metric-value {
            font-size: 0.95rem;
            font-weight: 700;
            color: #0f172a;
            margin-top: 0.15rem;
        }
        .ips-kit-detail-panel {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.65rem 0.75rem;
            margin-top: 0.5rem;
        }
        .st-key-asset_kit_table_wrap .ips-dash-est-html-table {
            width: 100% !important;
            border-collapse: separate !important;
            table-layout: fixed !important;
        }
        .st-key-asset_kit_table_wrap .ips-dash-est-html-table thead th {
            background: #eef2f7 !important;
            color: #64748b !important;
            font-size: 0.68rem !important;
            font-weight: 800 !important;
            text-transform: uppercase !important;
            padding: 0.45rem 0.55rem !important;
        }
        .st-key-asset_kit_table_wrap .ips-dash-est-html-table tbody td {
            padding: 0.4rem 0.55rem !important;
            border-bottom: 1px solid #e8edf4 !important;
            vertical-align: middle !important;
            font-size: 0.8125rem !important;
        }
        .st-key-asset_kit_table_wrap .ips-kit-td-name,
        .st-key-asset_kit_table_wrap .ips-kit-th-name {
            white-space: normal !important;
            word-break: break-word !important;
            line-height: 1.35 !important;
        }
        .st-key-asset_kit_table_wrap .ips-kit-td-expected,
        .st-key-asset_kit_table_wrap .ips-kit-td-actual,
        .st-key-asset_kit_table_wrap .ips-kit-td-unit,
        .st-key-asset_kit_table_wrap .ips-kit-td-total,
        .st-key-asset_kit_table_wrap .ips-kit-th-expected,
        .st-key-asset_kit_table_wrap .ips-kit-th-actual,
        .st-key-asset_kit_table_wrap .ips-kit-th-unit,
        .st-key-asset_kit_table_wrap .ips-kit-th-total {
            text-align: right !important;
            white-space: nowrap !important;
        }
        .st-key-asset_kit_table_wrap .ips-kit-td-type,
        .st-key-asset_kit_table_wrap .ips-kit-td-condition,
        .st-key-asset_kit_table_wrap .ips-kit-td-status,
        .st-key-asset_kit_table_wrap .ips-kit-th-type,
        .st-key-asset_kit_table_wrap .ips-kit-th-condition,
        .st-key-asset_kit_table_wrap .ips-kit-th-status {
            white-space: nowrap !important;
        }
        .st-key-asset_kit_table_wrap .ips-kit-td-serial {
            font-size: 0.75rem !important;
            word-break: break-all !important;
        }
        .st-key-asset_kit_table_wrap .ips-kit-item-open-link {
            color: #2563eb !important;
            font-weight: 700 !important;
            text-decoration: none !important;
        }
        .st-key-asset_kit_table_wrap .ips-kit-item-open-link:hover {
            text-decoration: underline !important;
        }
        .st-key-asset_kit_table_wrap .ips-kit-item-row-selected td {
            background: #f0f7ff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
