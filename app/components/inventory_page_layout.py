"""Inventory list page layout — aligned with Estimates/Jobs table design."""

from __future__ import annotations

import streamlit as st

from app.ui.css_inject import inject_css_once


def inject_inventory_page_layout_css() -> None:
    if not inject_css_once("ips-inventory-page-layout-v3"):
        return
    st.markdown(
        """
<style id="ips-inventory-page-layout-v3">
section[data-testid="stMain"]:has(.ips-inventory-page) {
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-inventory-page)
[data-testid="stHorizontalBlock"]:has(.ips-inventory-reorder-alert-marker) {
  align-items: center !important;
  gap: 0.5rem !important;
  margin: 0 0 0.5rem 0 !important;
}
section[data-testid="stMain"]:has(.ips-inventory-page)
[data-testid="stHorizontalBlock"]:has(.ips-inventory-reorder-alert-marker)
[data-testid="stAlert"] {
  margin: 0 !important;
}
section[data-testid="stMain"]:has(.ips-inventory-page)
[data-testid="stHorizontalBlock"]:has(.ips-inventory-reorder-alert-marker)
.stButton > button[kind="tertiary"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #1d4ed8 !important;
  font-weight: 800 !important;
  text-decoration: underline !important;
  padding: 0 !important;
  min-height: auto !important;
  height: auto !important;
}
.ips-inventory-filter-bar-wrap {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.38rem 0.5rem;
  margin-bottom: 0.35rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.ips-inventory-filter-bar-wrap [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  gap: 0.45rem !important;
}
section[data-testid="stMain"]:has(.ips-inventory-page) .ips-inventory-filter-bar-wrap [data-testid="stTextInput"] input,
section[data-testid="stMain"]:has(.ips-inventory-page) .ips-inventory-filter-bar-wrap [data-testid="stSelectbox"] > div > div {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 8px !important;
  min-height: 34px !important;
  font-size: 0.8125rem !important;
}
section[data-testid="stMain"]:has(.ips-inventory-page) .ips-inventory-filter-bar-wrap .stButton > button {
  min-height: 34px !important;
  height: 34px !important;
  font-size: 0.8125rem !important;
}
.st-key-inventory_table_wrap {
  min-height: 0;
  overflow: hidden !important;
  position: relative;
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin-top: 0.25rem !important;
  width: 100% !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
.st-key-inventory_table_wrap [data-testid="stMarkdownContainer"],
.st-key-inventory_table_wrap [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
  padding: 0 !important;
}
.st-key-inventory_table_wrap .ips-dash-est-table-scroll {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow-x: auto !important;
  margin-top: 0 !important;
  -webkit-overflow-scrolling: touch;
  scrollbar-gutter: stable;
}
.st-key-inventory_table_wrap .ips-dash-est-html-table {
  width: 100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  table-layout: fixed !important;
  background: #ffffff !important;
}
.st-key-inventory_table_wrap .ips-dash-est-html-table tr {
  display: table-row !important;
  height: 46px !important;
}
.st-key-inventory_table_wrap .ips-dash-est-html-table thead tr {
  height: 44px !important;
}
.st-key-inventory_table_wrap .ips-dash-est-html-table th,
.st-key-inventory_table_wrap .ips-dash-est-html-table td {
  display: table-cell !important;
  vertical-align: middle !important;
  padding: 0 10px !important;
  border-bottom: 1px solid #e8edf4 !important;
  overflow: hidden !important;
  box-sizing: border-box !important;
  background: #ffffff !important;
}
.st-key-inventory_table_wrap .ips-dash-est-html-table thead th {
  background: #eef2f7 !important;
  color: #64748b !important;
  font-size: 0.68rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.04em !important;
  text-transform: uppercase !important;
  white-space: nowrap !important;
  position: sticky !important;
  top: 0 !important;
  z-index: 2 !important;
}
.st-key-inventory_table_wrap .ips-dash-est-html-table tbody tr {
  cursor: pointer !important;
}
.st-key-inventory_table_wrap .ips-dash-est-html-table tbody tr:hover td {
  background: #f8fbff !important;
}
.st-key-inventory_table_wrap .ips-dash-est-html-table tbody tr.ips-inventory-row-expanded td {
  background: #f0f7ff !important;
}
.st-key-inventory_table_wrap .ips-dash-est-html-table .cell-wrapper {
  display: flex !important;
  align-items: center !important;
  min-height: 46px !important;
  width: 100% !important;
  min-width: 0 !important;
}
.st-key-inventory_table_wrap .ips-dash-est-cell-right {
  justify-content: flex-end !important;
  text-align: right !important;
}
.st-key-inventory_table_wrap .ips-dash-est-cell-center {
  justify-content: center !important;
  text-align: center !important;
}
.st-key-inventory_table_wrap .ips-dash-est-link,
.st-key-inventory_table_wrap .ips-inventory-desc-link,
.st-key-inventory_table_wrap .ips-inventory-open-link {
  color: #2563eb !important;
  font-weight: 800 !important;
  font-size: 0.8125rem !important;
  text-decoration: none !important;
  cursor: pointer !important;
  pointer-events: auto !important;
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin: 0 !important;
  font-family: inherit !important;
  line-height: inherit !important;
  text-align: left !important;
}
.st-key-inventory_table_wrap .ips-inventory-open-link:hover,
.st-key-inventory_table_wrap .ips-inventory-open-link:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
  outline: none !important;
}
.st-key-inventory_open_button_harness,
.st-key-inventory_open_button_harness [data-testid="stVerticalBlock"],
.st-key-inventory_open_button_harness [data-testid="stElementContainer"] {
  display: block !important;
  width: 0 !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  opacity: 0 !important;
  pointer-events: none !important;
}
.st-key-inventory_open_button_harness [class*="st-key-inv_bridge_open_"] {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  pointer-events: auto !important;
}
.st-key-inventory_open_button_harness [class*="st-key-inv_bridge_open_"] button {
  width: 1px !important;
  height: 1px !important;
  min-height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  opacity: 0 !important;
  pointer-events: auto !important;
}
.st-key-inventory_table_wrap .ips-dash-est-link,
.st-key-inventory_table_wrap .ips-inventory-desc-link {
  color: #2563eb !important;
  font-weight: 800 !important;
  font-size: 0.8125rem !important;
  text-decoration: none !important;
  cursor: pointer !important;
  pointer-events: auto !important;
}
.st-key-inventory_table_wrap .ips-dash-est-desc-link {
  display: inline-block !important;
  max-width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.st-key-inventory_table_wrap .ips-dash-est-link:hover,
.st-key-inventory_table_wrap .ips-dash-est-link:focus,
.st-key-inventory_table_wrap .ips-inventory-desc-link:hover,
.st-key-inventory_table_wrap .ips-inventory-desc-link:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}
.st-key-inventory_table_wrap .ips-inventory-text-cell,
.st-key-inventory_table_wrap .ips-inventory-vendor-cell {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  color: #0f172a !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.st-key-inventory_table_wrap .ips-inventory-muted {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  color: #64748b !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.st-key-inventory_table_wrap .ips-inventory-qty,
.st-key-inventory_table_wrap .ips-inventory-money-cell {
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
  font-variant-numeric: tabular-nums !important;
}
.st-key-inventory_table_wrap .ips-inventory-image-td {
  justify-content: center !important;
}
.st-key-inventory_table_wrap .ips-inventory-thumb-cell-link {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
  background: transparent !important;
  cursor: pointer !important;
  pointer-events: auto !important;
  line-height: 0 !important;
}
.st-key-inventory_table_wrap .ips-inventory-thumb-cell-link:hover .ips-inventory-thumb-img,
.st-key-inventory_table_wrap .ips-inventory-thumb-cell-link:focus-visible .ips-inventory-thumb-img,
.st-key-inventory_table_wrap .ips-inventory-thumb-cell-link:hover .ips-inventory-thumb-placeholder,
.st-key-inventory_table_wrap .ips-inventory-thumb-cell-link:focus-visible .ips-inventory-thumb-placeholder {
  border-color: #93c5fd !important;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15) !important;
}
.st-key-inventory_table_wrap .ips-inventory-image-td .image-cell,
.st-key-inventory_table_wrap .ips-inventory-image-td .ips-inventory-image-cell,
.st-key-inventory_table_wrap .ips-inventory-image-td .ips-inventory-thumb-cell {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}
.st-key-inventory_table_wrap .ips-inventory-thumb-img,
.st-key-inventory_table_wrap .ips-inventory-thumb-placeholder {
  width: 52px !important;
  height: 52px !important;
  min-width: 52px !important;
  max-width: 52px !important;
  min-height: 52px !important;
  max-height: 52px !important;
  object-fit: cover !important;
  border-radius: 8px !important;
  border: 1px solid #e2e8f0 !important;
  background: #f8fafc !important;
  display: block !important;
  margin: 0 auto !important;
  box-sizing: border-box !important;
}
.st-key-inventory_table_wrap .ips-inventory-thumb-placeholder {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  color: #94a3b8 !important;
  font-size: 1.1rem !important;
  line-height: 1 !important;
}
.st-key-inventory_table_wrap .ips-inventory-status-pill {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 22px !important;
  min-height: 22px !important;
  max-height: 22px !important;
  padding: 0 10px !important;
  border-radius: 999px !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  white-space: nowrap !important;
  line-height: 1 !important;
}
.st-key-inventory_table_wrap .ips-inventory-status-in-stock {
  background: #dcfce7 !important;
  color: #166534 !important;
}
.st-key-inventory_table_wrap .ips-inventory-status-low-stock {
  background: #fef3c7 !important;
  color: #92400e !important;
}
.st-key-inventory_table_wrap .ips-inventory-status-out-of-stock {
  background: #ffedd5 !important;
  color: #c2410c !important;
}
.st-key-inventory_table_wrap .ips-inventory-status-on-order {
  background: #dbeafe !important;
  color: #1d4ed8 !important;
}
.st-key-inventory_table_wrap .ips-inventory-status-discontinued {
  background: #f1f5f9 !important;
  color: #475569 !important;
}
.ips-inventory-table-filter-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.65rem;
  background: #f8fafc;
  border-bottom: 1px solid #e8edf4;
}
.ips-inventory-filter-toolbar-cell {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}
@media (max-width: 768px) {
  .st-key-inventory_table_wrap .ips-dash-est-html-table {
    table-layout: auto !important;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_inventory_filter_bar_shell() -> None:
    st.markdown(
        '<div class="ips-inventory-filter-bar-wrap">'
        '<span class="ips-inventory-filter-bar-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )


def close_inventory_filter_bar_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
