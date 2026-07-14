"""Users list page — layout styling aligned with Inventory."""

from __future__ import annotations

import streamlit as st

from app.ui.css_inject import inject_css_once


def inject_users_page_layout_css() -> None:
    if not inject_css_once("ips-users-page-layout-v1"):
        return
    st.markdown(
        """
<style id="ips-users-page-layout-v1">
section[data-testid="stMain"]:has(.ips-users-page) {
  background: #ffffff !important;
}
.ips-users-filter-bar-wrap {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.38rem 0.5rem;
  margin-bottom: 0.35rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.ips-users-filter-bar-wrap [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  gap: 0.45rem !important;
}
section[data-testid="stMain"]:has(.ips-users-page) .ips-users-filter-bar-wrap [data-testid="stTextInput"] input,
section[data-testid="stMain"]:has(.ips-users-page) .ips-users-filter-bar-wrap [data-testid="stSelectbox"] > div > div {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 8px !important;
  min-height: 34px !important;
  font-size: 0.8125rem !important;
}
section[data-testid="stMain"]:has(.ips-users-page) .ips-users-filter-bar-wrap .stButton > button {
  min-height: 34px !important;
  height: 34px !important;
  font-size: 0.8125rem !important;
}
.st-key-users_table_wrap {
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
.st-key-users_table_wrap [data-testid="stMarkdownContainer"],
.st-key-users_table_wrap [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
  padding: 0 !important;
}
.st-key-users_table_wrap .ips-dash-est-table-scroll {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow-x: auto !important;
  margin-top: 0 !important;
  -webkit-overflow-scrolling: touch;
  scrollbar-gutter: stable;
}
.st-key-users_table_wrap .ips-dash-est-html-table {
  width: 100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  table-layout: fixed !important;
  background: #ffffff !important;
}
.st-key-users_table_wrap .ips-dash-est-html-table tr {
  display: table-row !important;
  height: 52px !important;
}
.st-key-users_table_wrap .ips-dash-est-html-table thead tr {
  height: 44px !important;
}
.st-key-users_table_wrap .ips-dash-est-html-table th,
.st-key-users_table_wrap .ips-dash-est-html-table td {
  display: table-cell !important;
  vertical-align: middle !important;
  padding: 0 10px !important;
  border-bottom: 1px solid #e8edf4 !important;
  overflow: hidden !important;
  box-sizing: border-box !important;
  background: #ffffff !important;
}
.st-key-users_table_wrap .ips-dash-est-html-table thead th {
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
.st-key-users_table_wrap .ips-dash-est-html-table tbody tr {
  cursor: pointer !important;
}
.st-key-users_table_wrap .ips-dash-est-html-table tbody tr:hover td {
  background: #f8fbff !important;
}
.st-key-users_table_wrap .ips-dash-est-html-table .cell-wrapper {
  display: flex !important;
  align-items: center !important;
  min-height: 52px !important;
  width: 100% !important;
  min-width: 0 !important;
}
.st-key-users_table_wrap .ips-dash-est-cell-right {
  justify-content: flex-end !important;
  text-align: right !important;
}
.st-key-users_table_wrap .ips-dash-est-cell-center {
  justify-content: center !important;
  text-align: center !important;
}
.st-key-users_table_wrap .ips-users-open-link,
.st-key-users_table_wrap .ips-users-action-link {
  color: #2563eb !important;
  font-weight: 700 !important;
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
}
.st-key-users_table_wrap .ips-users-open-link:hover,
.st-key-users_table_wrap .ips-users-open-link:focus,
.st-key-users_table_wrap .ips-users-action-link:hover,
.st-key-users_table_wrap .ips-users-action-link:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}
.st-key-users_table_wrap .ips-users-name-link {
  display: inline-block !important;
  max-width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
  font-weight: 800 !important;
}
.st-key-users_table_wrap .ips-users-text-cell {
  font-size: 0.8125rem !important;
  color: #0f172a !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.st-key-users_table_wrap .ips-users-muted-cell {
  font-size: 0.8125rem !important;
  color: #64748b !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.st-key-users_table_wrap .ips-users-avatar,
.st-key-users_table_wrap .ips-users-avatar-initials {
  width: 48px !important;
  height: 48px !important;
  min-width: 48px !important;
  max-width: 48px !important;
  min-height: 48px !important;
  max-height: 48px !important;
  border-radius: 50% !important;
  object-fit: cover !important;
  border: 1px solid #e2e8f0 !important;
  background: #f8fafc !important;
  display: block !important;
  margin: 0 auto !important;
  box-sizing: border-box !important;
}
.st-key-users_table_wrap .ips-users-avatar-initials {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  color: #0b1f3a !important;
  font-size: 0.82rem !important;
  font-weight: 800 !important;
  line-height: 1 !important;
}
.st-key-users_table_wrap .ips-user-pill {
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
.st-key-users_table_wrap .ips-user-status-active {
  background: #dcfce7 !important;
  color: #166534 !important;
}
.st-key-users_table_wrap .ips-user-status-inactive {
  background: #f1f5f9 !important;
  color: #475569 !important;
}
.st-key-users_table_wrap .ips-user-status-deleted {
  background: #fee2e2 !important;
  color: #b91c1c !important;
}
.st-key-users_table_wrap .ips-user-status-locked {
  background: #ffedd5 !important;
  color: #c2410c !important;
}
.st-key-users_table_wrap .ips-user-status-pending {
  background: #dbeafe !important;
  color: #1d4ed8 !important;
}
.st-key-users_open_button_harness,
.st-key-users_open_button_harness [data-testid="stVerticalBlock"],
.st-key-users_open_button_harness [data-testid="stElementContainer"] {
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
.st-key-users_open_button_harness [class*="st-key-user_bridge_open_"] {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  pointer-events: auto !important;
}
.st-key-users_open_button_harness [class*="st-key-user_bridge_open_"] button {
  width: 1px !important;
  height: 1px !important;
  min-height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  opacity: 0 !important;
  pointer-events: auto !important;
}
.ips-users-table-filter-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.65rem;
  background: #f8fafc;
  border-bottom: 1px solid #e8edf4;
}
.ips-users-filter-toolbar-cell {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}
@media (max-width: 768px) {
  .st-key-users_table_wrap .ips-dash-est-html-table {
    table-layout: auto !important;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_users_filter_bar_shell() -> None:
    st.markdown(
        '<div class="ips-users-filter-bar-wrap">'
        '<span class="ips-users-filter-bar-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )


def close_users_filter_bar_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
