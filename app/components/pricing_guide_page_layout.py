"""Pricing Guide catalog list page — layout styling aligned with Inventory."""

from __future__ import annotations

import streamlit as st


def inject_pricing_guide_page_layout_css() -> None:
    st.markdown(
        """
<style id="ips-pricing-guide-page-layout-v1">
section[data-testid="stMain"]:has(.ips-pricing-guide-page) {
  background: #ffffff !important;
}
.ips-pg-filter-bar-wrap {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.38rem 0.5rem;
  margin-bottom: 0.35rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.ips-pg-filter-bar-wrap [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  gap: 0.45rem !important;
}
section[data-testid="stMain"]:has(.ips-pricing-guide-page) .ips-pg-filter-bar-wrap [data-testid="stTextInput"] input,
section[data-testid="stMain"]:has(.ips-pricing-guide-page) .ips-pg-filter-bar-wrap [data-testid="stSelectbox"] > div > div {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 8px !important;
  min-height: 34px !important;
  font-size: 0.8125rem !important;
}
section[data-testid="stMain"]:has(.ips-pricing-guide-page) .ips-pg-filter-bar-wrap .stButton > button {
  min-height: 34px !important;
  height: 34px !important;
  font-size: 0.8125rem !important;
}
.st-key-pricing_guide_table_wrap {
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
.st-key-pricing_guide_table_wrap [data-testid="stMarkdownContainer"],
.st-key-pricing_guide_table_wrap [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
  padding: 0 !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-table-scroll {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow-x: auto !important;
  margin-top: 0 !important;
  -webkit-overflow-scrolling: touch;
  scrollbar-gutter: stable;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-html-table {
  width: 100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  table-layout: fixed !important;
  background: #ffffff !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-html-table tr {
  display: table-row !important;
  height: 46px !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-html-table thead tr {
  height: 44px !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-html-table th,
.st-key-pricing_guide_table_wrap .ips-dash-est-html-table td {
  display: table-cell !important;
  vertical-align: middle !important;
  padding: 0 10px !important;
  border-bottom: 1px solid #e8edf4 !important;
  overflow: hidden !important;
  box-sizing: border-box !important;
  background: #ffffff !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-html-table thead th {
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
.st-key-pricing_guide_table_wrap .ips-dash-est-html-table tbody tr {
  cursor: pointer !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-html-table tbody tr:hover td {
  background: #f8fbff !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-html-table .cell-wrapper {
  display: flex !important;
  align-items: center !important;
  min-height: 46px !important;
  width: 100% !important;
  min-width: 0 !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-cell-right {
  justify-content: flex-end !important;
  text-align: right !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-cell-center {
  justify-content: center !important;
  text-align: center !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-link,
.st-key-pricing_guide_table_wrap .ips-inventory-desc-link,
.st-key-pricing_guide_table_wrap .ips-pg-open-link {
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
  line-height: 1.25 !important;
  text-align: left !important;
  position: relative !important;
  z-index: 2 !important;
  -webkit-text-fill-color: currentColor !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-desc-link {
  display: inline-block !important;
  max-width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.st-key-pricing_guide_table_wrap .ips-dash-est-link:hover,
.st-key-pricing_guide_table_wrap .ips-dash-est-link:focus,
.st-key-pricing_guide_table_wrap .ips-inventory-desc-link:hover,
.st-key-pricing_guide_table_wrap .ips-inventory-desc-link:focus,
.st-key-pricing_guide_table_wrap .ips-pg-open-link:hover,
.st-key-pricing_guide_table_wrap .ips-pg-open-link:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}
.st-key-pricing_guide_table_wrap .ips-pg-html-catalog-table .ips-inventory-text-cell,
.st-key-pricing_guide_table_wrap .ips-pg-html-catalog-table .ips-inventory-muted,
.st-key-pricing_guide_table_wrap .ips-pg-html-catalog-table .ips-inventory-money-cell,
.st-key-pricing_guide_table_wrap .ips-pg-html-catalog-table .ips-dash-est-link,
.st-key-pricing_guide_table_wrap .ips-pg-html-catalog-table .ips-pg-open-link,
.st-key-pricing_guide_table_wrap .ips-pg-html-catalog-table [role="button"][data-pg-action="open"] {
  visibility: visible !important;
  opacity: 1 !important;
  display: inline-block !important;
  max-width: 100% !important;
  width: auto !important;
  min-width: 0 !important;
  height: auto !important;
  min-height: 0 !important;
  line-height: 1.25 !important;
  pointer-events: auto !important;
  position: relative !important;
  z-index: 2 !important;
  -webkit-text-fill-color: currentColor !important;
}
.st-key-pricing_guide_table_wrap .ips-inventory-text-cell,
.st-key-pricing_guide_table_wrap .ips-inventory-vendor-cell {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  color: #0f172a !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.st-key-pricing_guide_table_wrap .ips-inventory-muted {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  color: #64748b !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.st-key-pricing_guide_table_wrap .ips-inventory-money-cell {
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
  color: #0f172a !important;
  font-variant-numeric: tabular-nums !important;
}
.st-key-pricing_guide_table_wrap .ips-inventory-image-td {
  justify-content: center !important;
}
.st-key-pricing_guide_table_wrap .ips-pg-thumb-cell-link,
.st-key-pricing_guide_table_wrap .ips-inventory-thumb-cell-link {
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
.st-key-pricing_guide_table_wrap .ips-pg-thumb-img,
.st-key-pricing_guide_table_wrap .ips-pg-thumb-placeholder,
.st-key-pricing_guide_table_wrap .ips-inventory-thumb-img,
.st-key-pricing_guide_table_wrap .ips-inventory-thumb-placeholder {
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
.st-key-pricing_guide_table_wrap .ips-pg-thumb-placeholder,
.st-key-pricing_guide_table_wrap .ips-inventory-thumb-placeholder {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  color: #94a3b8 !important;
  font-size: 1.1rem !important;
  line-height: 1 !important;
}
.st-key-pricing_guide_table_wrap .ips-pg-status-pill {
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
.st-key-pricing_guide_table_wrap .ips-pg-status-active {
  background: #dcfce7 !important;
  color: #166534 !important;
}
.st-key-pricing_guide_table_wrap .ips-pg-status-inactive {
  background: #f1f5f9 !important;
  color: #475569 !important;
}
.st-key-pricing_guide_table_wrap .ips-pg-type-pill {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 22px !important;
  padding: 0 10px !important;
  border-radius: 999px !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  white-space: nowrap !important;
}
.st-key-pricing_guide_open_button_harness,
.st-key-pricing_guide_open_button_harness [data-testid="stVerticalBlock"],
.st-key-pricing_guide_open_button_harness [data-testid="stElementContainer"] {
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
.st-key-pricing_guide_open_button_harness [class*="st-key-pg_bridge_open_"] {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  pointer-events: auto !important;
}
.st-key-pricing_guide_open_button_harness [class*="st-key-pg_bridge_open_"] button {
  width: 1px !important;
  height: 1px !important;
  min-height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  opacity: 0 !important;
  pointer-events: auto !important;
}
.ips-pg-table-filter-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.65rem;
  background: #f8fafc;
  border-bottom: 1px solid #e8edf4;
}
.ips-pg-filter-toolbar-cell {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}
@media (max-width: 768px) {
  .st-key-pricing_guide_table_wrap .ips-dash-est-html-table {
    table-layout: auto !important;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_pricing_guide_filter_bar_shell() -> None:
    st.markdown(
        '<div class="ips-pg-filter-bar-wrap">'
        '<span class="ips-pg-filter-bar-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )


def close_pricing_guide_filter_bar_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
