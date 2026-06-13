"""Assets list page — professional layout styling (UI only)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.table_pagination import (
        page_key,
        page_size_key,
        pagination_meta,
        reset_table_page,
    )
except ImportError:
    from components.table_pagination import (  # type: ignore
        page_key,
        page_size_key,
        pagination_meta,
        reset_table_page,
    )

_EQUIPMENT_BANNER = (
    "Large assets and rentable equipment — tool trailers, generators, pressure washers, "
    "dump trailers, and similar fleet items."
)


def inject_assets_page_layout_css() -> None:
    """Always inject — assets page layout overrides."""
    st.markdown(
        """
<style id="ips-assets-page-layout-v1">
section[data-testid="stMain"]:has(.ips-assets-page) {
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) .block-container {
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) [data-testid="stTabs"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) [data-testid="stTabs"] [data-baseweb="tab-list"] {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 12px 12px 0 0 !important;
  padding: 0.15rem 0.5rem 0 !important;
  margin-bottom: 0 !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) [data-testid="stTabContent"] {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-top: none !important;
  border-radius: 0 0 12px 12px !important;
  padding: 1rem 1.1rem !important;
}
.ips-assets-equipment-banner {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-left: 4px solid #4361EE;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  margin: 0 0 1rem 0;
  font-size: 0.875rem;
  color: #475569;
  line-height: 1.45;
}
.ips-assets-filter-bar-wrap {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  margin-bottom: 0.85rem;
}
section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-filter-bar-wrap [data-testid="stTextInput"] input,
section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-filter-bar-wrap [data-testid="stSelectbox"] > div > div {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 8px !important;
  min-height: 38px !important;
}
.asset-table,
.ips-assets-table-wrap.asset-table {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 12px;
  overflow: hidden;
}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row),
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row) {
  min-height: 72px !important;
  border-bottom: 1px solid #e5eaf2 !important;
}
.ips-assets-equipment-table-row,
.ips-assets-row-marker {
  display: block !important;
  width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  opacity: 0 !important;
  pointer-events: none !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .asset-name-link button,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .ips-assets-name-link button,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .asset-name-button button {
  background: transparent !important;
  color: #0f172a !important;
  font-weight: 700 !important;
  font-size: 0.875rem !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0 !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  width: auto !important;
  max-width: 100% !important;
  min-width: 0 !important;
  box-shadow: none !important;
  text-align: left !important;
  justify-content: flex-start !important;
  display: inline !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  cursor: pointer !important;
  transition: color 0.15s ease !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .asset-name-link button:hover,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .ips-assets-name-link button:hover,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .asset-name-button button:hover {
  background: transparent !important;
  color: #2563eb !important;
  text-decoration: underline !important;
  border: none !important;
  box-shadow: none !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .asset-name-link button > div,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .asset-name-link button p,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .asset-name-link button span,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .ips-assets-name-link button > div,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .ips-assets-name-link button p,
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap .ips-assets-name-link button span {
  color: inherit !important;
  font-weight: 700 !important;
  display: inline !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  text-align: left !important;
}
.asset-name-link {
  font-weight: 700;
  color: #0f172a;
  cursor: pointer;
  text-decoration: none;
}
.asset-name-link:hover {
  color: #2563eb;
  text-decoration: underline;
}
.ips-asset-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 800;
  white-space: nowrap;
  letter-spacing: 0.02em;
}
.ips-asset-status-green {
  background: #dcfce7;
  color: #15803d;
}
.ips-asset-status-orange {
  background: #ffedd5;
  color: #c2410c;
}
.ips-asset-status-blue {
  background: #dbeafe;
  color: #1d4ed8;
}
.ips-asset-status-red {
  background: #fee2e2;
  color: #b91c1c;
}
.ips-asset-status-neutral {
  background: #f1f5f9;
  color: #475569;
}
section[data-testid="stMain"]:has(.ips-assets-page) .st-key-assets_table_wrap [data-testid="column"]:has(.asset-actions-cell) button[data-testid="stBaseButton-popover"] {
  min-width: 100px !important;
}
.ips-assets-pagination-footer {
  margin-top: 0.85rem;
  padding: 0.65rem 0.25rem 0;
  border-top: 1px solid #e5eaf2;
}
.ips-assets-pagination-summary {
  font-size: 0.8125rem;
  color: #64748b;
  font-weight: 600;
  margin: 0;
  text-align: center;
}
section[data-testid="stMain"]:has(.ips-assets-page) [class*="st-key-assets_list_pg_footer"] [data-testid="stButton"] > button {
  white-space: nowrap !important;
  min-width: fit-content !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) [data-testid="column"]:has(.ips-assets-page-header-actions) [data-testid="stHorizontalBlock"] {
  flex-wrap: nowrap !important;
  justify-content: flex-end !important;
  gap: 0.45rem !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) [data-testid="column"]:has(.ips-assets-page-header-actions) [data-testid="stButton"] > button,
section[data-testid="stMain"]:has(.ips-assets-page) [data-testid="column"]:has(.ips-assets-page-header-actions) [data-testid="stDownloadButton"] > button {
  white-space: nowrap !important;
  min-width: fit-content !important;
  border-radius: 8px !important;
  min-height: 38px !important;
  font-weight: 600 !important;
}
button,
.stButton button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
section[data-testid="stMain"]:has(.ips-assets-page) .asset-actions-button,
section[data-testid="stMain"]:has(.ips-assets-page) .asset-name-button {
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_assets_equipment_banner() -> None:
    st.markdown(
        f'<div class="ips-assets-equipment-banner">{html.escape(_EQUIPMENT_BANNER)}</div>',
        unsafe_allow_html=True,
    )


def render_assets_filter_bar_shell() -> None:
    st.markdown('<div class="ips-assets-filter-bar-wrap"><span class="ips-assets-filter-bar-marker" aria-hidden="true"></span>', unsafe_allow_html=True)


def close_assets_filter_bar_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_assets_pagination_footer(total: int, table_key: str, *, item_label: str = "asset") -> None:
    """Showing X to Y of Z + centered page controls."""
    page, page_size, total_pages = pagination_meta(total, table_key)
    if total <= 0:
        start = end = 0
    else:
        start = (page - 1) * page_size + 1
        end = min(page * page_size, total)

    st.markdown('<div class="ips-assets-pagination-footer">', unsafe_allow_html=True)
    st.markdown(
        f'<p class="ips-assets-pagination-summary">Showing {start} to {end} of {total:,} {item_label}{"" if total == 1 else "s"}</p>',
        unsafe_allow_html=True,
    )

    with st.container(key=f"{table_key}_pg_footer"):
        if total_pages > 1:
            _, prev_col, mid_col, next_col, _ = st.columns([1.2, 0.75, 1, 0.75, 1.2], gap="small")
            with prev_col:
                if st.button(
                    "Previous",
                    key=f"{table_key}_pg_prev",
                    type="secondary",
                    disabled=page <= 1,
                    use_container_width=True,
                ):
                    st.session_state[page_key(table_key)] = max(1, page - 1)
                    st.rerun()
            with mid_col:
                st.markdown(
                    f'<p class="ips-assets-pagination-summary">Page {page} of {total_pages}</p>',
                    unsafe_allow_html=True,
                )
            with next_col:
                if st.button(
                    "Next",
                    key=f"{table_key}_pg_next",
                    type="secondary",
                    disabled=page >= total_pages,
                    use_container_width=True,
                ):
                    st.session_state[page_key(table_key)] = min(total_pages, page + 1)
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
