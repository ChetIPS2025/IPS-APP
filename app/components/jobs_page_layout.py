"""Jobs list page — professional layout styling (UI only)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.table_pagination import (
        page_key,
        page_size_key,
        pagination_meta,
        reset_table_page,
        DEFAULT_CATALOG_PAGE_SIZE,
    )
except ImportError:
    from components.table_pagination import (  # type: ignore
        page_key,
        page_size_key,
        pagination_meta,
        reset_table_page,
        DEFAULT_CATALOG_PAGE_SIZE,
    )

_PAGE_SIZE_OPTIONS = (50, 75, 100, 150)
_HIDE_IF_EMPTY_COLUMNS: frozenset[str] = frozenset({"estimated", "actual"})
_JOB_COL_WEIGHTS = [0.72, 2.75, 1.15, 0.68, 0.95, 0.95]
_JOB_COL_MARKERS: tuple[str, ...] = (
    "num",
    "desc",
    "customer",
    "status",
    "estimated",
    "actual",
)
_JOB_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("JOB #", None),
    ("PROJECT / DESCRIPTION", None),
    ("CUSTOMER", "customer"),
    ("STATUS", "status"),
    ("ESTIMATED COST", None),
    ("ACTUAL COST", None),
]


def _money(value: float) -> str:
    return f"${float(value or 0):,.2f}"


def _summary_money(value: float, *, has_data: bool) -> str:
    if not has_data:
        return "—"
    if abs(float(value or 0)) < 0.005:
        return "—"
    return _money(value)


def inject_jobs_page_layout_css() -> None:
    st.markdown(
        """
<style id="ips-jobs-page-layout-v18">
section[data-testid="stMain"]:has(.ips-jobs-page) {
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .block-container {
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) [data-testid="stVerticalBlock"] {
  gap: 0.35rem !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) [data-testid="stElementContainer"] {
  margin-bottom: 0.15rem !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .ips-page-header {
  margin-bottom: 0.15rem !important;
  padding-bottom: 0 !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .ips-page-title {
  font-size: 1.35rem !important;
  margin: 0 !important;
  line-height: 1.15 !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .ips-page-subtitle {
  font-size: 0.78rem !important;
  margin: 0.12rem 0 0 !important;
  line-height: 1.3 !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .ips-page-actions-marker + [data-testid="stHorizontalBlock"] {
  gap: 0.4rem !important;
  justify-content: flex-end !important;
}
.ips-jobs-filter-bar-wrap {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.38rem 0.5rem;
  margin-bottom: 0.35rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.ips-jobs-filter-bar-wrap [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  gap: 0.45rem !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .ips-jobs-filter-bar-wrap [data-testid="stTextInput"] input,
section[data-testid="stMain"]:has(.ips-jobs-page) .ips-jobs-filter-bar-wrap [data-testid="stSelectbox"] > div > div {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 8px !important;
  min-height: 34px !important;
  font-size: 0.8125rem !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .ips-jobs-filter-bar-wrap .stButton > button {
  min-height: 34px !important;
  height: 34px !important;
  font-size: 0.8125rem !important;
}
.ips-jobs-table-wrap.jobs-table {
  background: #ffffff;
  border: none;
  border-radius: 0;
  overflow: visible;
  min-width: min(100%, max-content);
  margin-bottom: 0;
}
.st-key-jobs_table_wrap {
  max-height: min(calc(100vh - 220px), 920px);
  min-height: 0;
  overflow-x: auto !important;
  overflow-y: auto !important;
  position: relative;
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 12px !important;
  box-shadow: none !important;
  padding: 0 !important;
  scrollbar-gutter: stable;
  margin-top: 0.25rem !important;
}
.st-key-jobs_table_wrap [data-testid="stVerticalBlockBorderWrapper"] {
  background: #ffffff !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}
.st-key-jobs_table_wrap [data-testid="stVerticalBlockBorderWrapper"] > div {
  padding: 0 !important;
  background: #ffffff !important;
}
.st-key-jobs_table_wrap .ips-jobs-col-marker {
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
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"] {
  gap: 0 !important;
}
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row),
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row),
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) {
  display: flex !important;
  align-items: center !important;
  min-height: 46px !important;
  max-height: 46px !important;
  height: 46px !important;
  min-width: max-content !important;
  padding: 0 !important;
  margin: 0 !important;
  background: #ffffff !important;
  background-color: #ffffff !important;
  border-bottom: 1px solid #e5e7eb !important;
  transition: background 0.15s ease !important;
  cursor: pointer;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"] > [data-testid="stVerticalBlock"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"] > [data-testid="stElementContainer"] {
  background: #ffffff !important;
  background-color: #ffffff !important;
}
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover,
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover > [data-testid="column"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover > [data-testid="column"] > [data-testid="stVerticalBlock"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover > [data-testid="column"] > [data-testid="stElementContainer"] {
  background: #f8fbff !important;
  background-color: #f8fbff !important;
}
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-jobs_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:first-of-type,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {
  display: flex !important;
  align-items: center !important;
  background: #eef2f7 !important;
  min-height: 44px !important;
  max-height: 44px !important;
  height: 44px !important;
  min-width: max-content !important;
  padding: 0 !important;
  margin: 0 !important;
  cursor: default !important;
  position: sticky !important;
  top: 0 !important;
  z-index: 12 !important;
  box-shadow: 0 1px 0 #dbe3ef !important;
  border-bottom: 1px solid #dbe3ef !important;
}
.st-key-jobs_table_wrap .ips-jobs-header-row {
  padding: 0 !important;
  min-height: 0 !important;
  background: transparent !important;
  border: none !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type .ips-jobs-header-row {
  font-size: 0.68rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.03em;
  color: #64748b !important;
  text-transform: uppercase;
  padding: 0 !important;
  margin: 0 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  line-height: 1.2 !important;
  background: transparent !important;
  border: none !important;
  height: 100% !important;
  min-height: 0 !important;
  display: flex !important;
  align-items: center !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  align-items: stretch !important;
  align-self: stretch !important;
  height: 100% !important;
  min-height: 46px !important;
  padding: 0 10px !important;
  min-width: 0 !important;
  box-sizing: border-box !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {
  min-height: 44px !important;
  padding: 0 10px !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) [data-testid="stVerticalBlock"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stVerticalBlock"] {
  justify-content: center !important;
  align-items: stretch !important;
  gap: 0 !important;
  width: 100% !important;
  min-height: 0 !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) [data-testid="stElementContainer"],
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="stElementContainer"] {
  margin-bottom: 0 !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  width: 100% !important;
}
.st-key-jobs_table_wrap .ips-jobs-row-marker {
  display: block !important;
  width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
  line-height: 0 !important;
  font-size: 0 !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-num) {
  flex: 0 0 96px !important;
  min-width: 96px !important;
  max-width: none !important;
  flex-shrink: 0 !important;
  align-items: center !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-desc) {
  flex: 2.6 1 260px !important;
  min-width: 260px !important;
  align-items: center !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-customer) {
  flex: 1.8 1 180px !important;
  min-width: 180px !important;
  align-items: center !important;
  justify-content: flex-start !important;
  text-align: left !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-status) {
  flex: 0 0 96px !important;
  min-width: 96px !important;
  align-items: center !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-estimated),
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-actual) {
  flex: 0 0 108px !important;
  min-width: 108px !important;
  align-items: center !important;
  justify-content: flex-end !important;
}
.ips-jobs-customer-cell {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  color: #0f172a !important;
  text-align: left !important;
  justify-content: flex-start !important;
}
.ips-jobs-list-link {
  color: #2563eb !important;
  font-weight: 800 !important;
  font-size: 0.8125rem !important;
  text-decoration: none !important;
  cursor: pointer !important;
  background: transparent !important;
  border: none !important;
  display: inline-block !important;
  max-width: 100% !important;
}
.ips-jobs-list-link.ips-jobs-desc-link,
.ips-jobs-list-link.ips-jobs-title-link,
.ips-jobs-list-link.job-project-link {
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
  width: 100% !important;
}
.ips-jobs-list-link:hover,
.ips-jobs-list-link:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-num) .ips-jobs-list-link,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-desc) .ips-jobs-list-link {
  pointer-events: auto !important;
}
.ips-jobs-cell-truncate,
.ips-jobs-customer-cell {
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
  max-width: 100% !important;
  min-width: 0 !important;
  display: flex !important;
  align-items: center !important;
  vertical-align: middle !important;
  line-height: 1.25 !important;
}
.ips-jobs-table-link.ips-jobs-cell-truncate {
  min-width: 0 !important;
  max-width: 100% !important;
  overflow: hidden !important;
}
.ips-jobs-table-link.ips-jobs-cell-truncate button {
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
  max-width: 100% !important;
  width: 100% !important;
  display: block !important;
  text-align: left !important;
}
.ips-jobs-col-money {
  justify-content: flex-end !important;
  text-align: right !important;
  width: 100% !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:has(.ips-jobs-col-num) .ips-jobs-header-row,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:has(.ips-jobs-col-desc) .ips-jobs-header-row,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:has(.ips-jobs-col-customer) .ips-jobs-header-row {
  justify-content: flex-start !important;
  text-align: left !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:has(.ips-jobs-col-estimated) .ips-jobs-header-row,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:has(.ips-jobs-col-actual) .ips-jobs-header-row {
  justify-content: flex-end !important;
  text-align: right !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:has(.ips-jobs-col-status) .ips-jobs-header-row {
  justify-content: center !important;
  text-align: center !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-estimated) .ips-jobs-money {
  justify-content: flex-end !important;
  text-align: right !important;
  color: #2563eb !important;
  font-weight: 800 !important;
  font-size: 0.8125rem !important;
  font-variant-numeric: tabular-nums !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-actual) .ips-jobs-money {
  justify-content: flex-end !important;
  text-align: right !important;
  color: #0f172a !important;
  font-weight: 600 !important;
  font-size: 0.8125rem !important;
  font-variant-numeric: tabular-nums !important;
}
.ips-jobs-summary-cards {
  display: grid;
  grid-template-columns: repeat(8, minmax(0, 1fr));
  gap: 0.4rem;
  margin: 0 0 0.35rem 0;
}
@media (max-width: 1500px) {
  .ips-jobs-summary-cards {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
@media (max-width: 900px) {
  .ips-jobs-summary-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.ips-jobs-stat-card {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.45rem 0.55rem 0.5rem;
  min-height: 52px;
  border-left-width: 4px;
  border-left-style: solid;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
}
.ips-jobs-stat-card:hover {
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.1);
  border-color: #bfd3f2;
}
.ips-jobs-stat-label {
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  margin: 0 0 0.15rem 0;
  line-height: 1.2;
}
.ips-jobs-stat-value {
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.ips-jobs-stat-total { border-left-color: #1e3a8a; }
.ips-jobs-stat-total .ips-jobs-stat-value { color: #1e3a8a; }
.ips-jobs-stat-active { border-left-color: #2563eb; }
.ips-jobs-stat-active .ips-jobs-stat-value { color: #2563eb; }
.ips-jobs-stat-on-hold { border-left-color: #d97706; }
.ips-jobs-stat-on-hold .ips-jobs-stat-value { color: #d97706; }
.ips-jobs-stat-completed { border-left-color: #15803d; }
.ips-jobs-stat-completed .ips-jobs-stat-value { color: #15803d; }
.ips-jobs-stat-cancelled { border-left-color: #64748b; }
.ips-jobs-stat-cancelled .ips-jobs-stat-value { color: #64748b; }
.ips-jobs-stat-awarded { border-left-color: #15803d; }
.ips-jobs-stat-awarded .ips-jobs-stat-value { color: #15803d; }
.ips-jobs-stat-pending { border-left-color: #d97706; }
.ips-jobs-stat-pending .ips-jobs-stat-value { color: #d97706; }
.ips-jobs-stat-draft { border-left-color: #64748b; }
.ips-jobs-stat-draft .ips-jobs-stat-value { color: #64748b; }
.ips-jobs-stat-subjobs { border-left-color: #ea580c; }
.ips-jobs-stat-subjobs .ips-jobs-stat-value { color: #ea580c; }
.ips-jobs-stat-contract { border-left-color: #15803d; }
.ips-jobs-stat-contract .ips-jobs-stat-value { color: #15803d; }
.ips-jobs-stat-actual { border-left-color: #2563eb; }
.ips-jobs-stat-actual .ips-jobs-stat-value { color: #2563eb; }
.ips-jobs-summary-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  margin: 0 0 0.35rem 0;
  padding: 0.35rem 0.45rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.ips-jobs-summary-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.72rem;
  font-weight: 600;
  color: #475569;
  padding: 0.15rem 0.45rem;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  white-space: nowrap;
  line-height: 1.2;
}
.ips-jobs-summary-chip strong {
  font-weight: 800;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}
.ips-jobs-summary-chip.ips-jobs-chip-accent strong {
  color: #2563eb;
}
.ips-jobs-summary-chip.ips-jobs-chip-money strong {
  color: #15803d;
}
.ips-jobs-view-nav {
  margin: 0 0 0.4rem 0;
  padding: 0.2rem 0;
}
.ips-jobs-view-nav [data-testid="stRadio"],
.ips-jobs-view-nav [data-testid="stSegmentedControl"] {
  margin: 0 !important;
}
.ips-jobs-view-nav [data-testid="stRadio"] > div {
  gap: 0.35rem !important;
  flex-wrap: wrap !important;
}
.ips-jobs-view-nav [data-testid="stRadio"] label,
.ips-jobs-view-nav [data-testid="stSegmentedControl"] label {
  background: #f8fafc !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 999px !important;
  padding: 0.35rem 0.85rem !important;
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
  color: #475569 !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) [data-testid="column"]:has(.ips-jobs-page-size-marker) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 0.35rem !important;
  margin-bottom: 0.25rem !important;
}
.ips-jobs-show-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #475569;
  white-space: nowrap;
}
section[data-testid="stMain"]:has(.ips-jobs-page) [data-testid="column"]:has(.ips-jobs-page-size-marker) [data-testid="stSelectbox"] {
  max-width: 5.5rem;
}
section[data-testid="stMain"]:has(.ips-jobs-page) [data-testid="column"]:has(.ips-jobs-page-size-marker) [data-testid="stSelectbox"] > div > div {
  min-height: 34px !important;
  border-radius: 8px !important;
  border: 1px solid #dbe3ef !important;
  background: #ffffff !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"] > [data-testid="stVerticalBlock"] {
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  align-items: stretch !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 100% !important;
  gap: 0 !important;
}
.ips-jobs-table-row,
.ips-jobs-row-marker,
.job-row,
.jobs-table-row,
.job-status-cell,
.ips-jobs-status-cell {
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
.ips-jobs-row-marker {
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
.st-key-jobs_table_wrap .ips-jobs-table-link {
  display: flex !important;
  align-items: center !important;
  width: 100% !important;
  min-width: 0 !important;
  height: 100% !important;
  pointer-events: auto !important;
}
.job-link,
.st-key-jobs_table_wrap .job-link-wrap button,
.st-key-jobs_table_wrap .job-link-wrap button p,
.st-key-jobs_table_wrap .job-link-wrap button span {
  color: var(--ips-blue, #2563eb) !important;
  font-weight: 700 !important;
  cursor: pointer !important;
  text-decoration: none !important;
}
.st-key-jobs_table_wrap .job-link-wrap button:hover,
.st-key-jobs_table_wrap .job-link-wrap button:focus,
.st-key-jobs_table_wrap .job-link-wrap button:hover p,
.st-key-jobs_table_wrap .job-link-wrap button:focus p {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
  background: transparent !important;
  box-shadow: none !important;
}
.st-key-jobs_table_wrap .ips-jobs-table-link.ips-jobs-cell-truncate {
  max-width: 100% !important;
  overflow: hidden !important;
}
.st-key-jobs_table_wrap .ips-jobs-table-link [data-testid="stButton"],
.st-key-jobs_table_wrap .ips-jobs-table-link .stButton {
  width: 100% !important;
  min-width: 0 !important;
  margin: 0 !important;
  pointer-events: auto !important;
}
.st-key-jobs_table_wrap .ips-jobs-table-link button,
.st-key-jobs_table_wrap .job-number-link button,
.st-key-jobs_table_wrap .ips-jobs-number-link button,
.st-key-jobs_table_wrap .ips-jobs-title-link button,
.st-key-jobs_table_wrap .job-project-link button {
  background: transparent !important;
  background-color: transparent !important;
  color: #2563eb !important;
  font-weight: 800 !important;
  font-size: 0.8125rem !important;
  line-height: 1.2 !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
  height: auto !important;
  min-height: 0 !important;
  max-height: none !important;
  justify-content: flex-start !important;
  text-align: left !important;
  width: auto !important;
  max-width: 100% !important;
  min-width: 0 !important;
  outline: none !important;
  display: inline-flex !important;
  align-items: center !important;
  cursor: pointer !important;
  pointer-events: auto !important;
  transition: color 0.15s ease !important;
}
.st-key-jobs_table_wrap .ips-jobs-number-link [data-testid="stButton"],
.st-key-jobs_table_wrap .job-number-link [data-testid="stButton"] {
  width: auto !important;
  max-width: none !important;
  flex-shrink: 0 !important;
}
.st-key-jobs_table_wrap .ips-jobs-number-link button,
.st-key-jobs_table_wrap .job-number-link button {
  white-space: nowrap !important;
  overflow: visible !important;
  text-overflow: clip !important;
  width: auto !important;
  max-width: none !important;
}
.st-key-jobs_table_wrap .ips-jobs-number-link button p,
.st-key-jobs_table_wrap .job-number-link button p {
  overflow: visible !important;
  text-overflow: clip !important;
  white-space: nowrap !important;
}
.st-key-jobs_table_wrap .ips-jobs-title-link button,
.st-key-jobs_table_wrap .job-project-link button {
  white-space: nowrap !important;
  line-height: 1.2 !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  width: 100% !important;
  max-width: 100% !important;
}
.st-key-jobs_table_wrap .ips-jobs-table-link button:hover,
.st-key-jobs_table_wrap .ips-jobs-table-link button:focus,
.st-key-jobs_table_wrap .job-number-link button:hover,
.st-key-jobs_table_wrap .job-number-link button:focus,
.st-key-jobs_table_wrap .ips-jobs-number-link button:hover,
.st-key-jobs_table_wrap .ips-jobs-number-link button:focus,
.st-key-jobs_table_wrap .ips-jobs-title-link button:hover,
.st-key-jobs_table_wrap .ips-jobs-title-link button:focus,
.st-key-jobs_table_wrap .job-project-link button:hover,
.st-key-jobs_table_wrap .job-project-link button:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
.st-key-jobs_table_wrap .ips-jobs-table-link button p,
.st-key-jobs_table_wrap .ips-jobs-table-link button span,
.st-key-jobs_table_wrap .ips-jobs-number-link button p,
.st-key-jobs_table_wrap .ips-jobs-title-link button p,
.st-key-jobs_table_wrap .job-project-link button p {
  color: inherit !important;
  font-weight: inherit !important;
  font-size: inherit !important;
  line-height: inherit !important;
  margin: 0 !important;
  padding: 0 !important;
}
.ips-jobs-title-link,
.job-project-link {
  display: flex !important;
  align-items: center !important;
  height: 100% !important;
  min-height: 0 !important;
  width: 100% !important;
  cursor: pointer !important;
}
.ips-jobs-cell,
.jobs-table-cell,
.job-cell {
  display: flex !important;
  align-items: center !important;
  min-height: 0 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  vertical-align: middle !important;
  line-height: 1.25 !important;
}
.ips-jobs-money {
  display: flex !important;
  align-items: center !important;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  font-size: 0.8125rem;
  font-weight: 600;
  color: #0f172a;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell),
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-actions-cell) {
  display: flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-status-cell),
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-pill) {
  display: flex !important;
  align-items: center !important;
}
.ips-jobs-cell {
  color: #0f172a;
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.2;
}
.ips-jobs-money-empty {
  color: #64748b;
  font-weight: 700;
}
.ips-jobs-money-negative {
  color: #dc2626;
  font-weight: 700;
}
.ips-jobs-actual-over-estimate {
  color: #dc2626 !important;
  font-weight: 700 !important;
}
.ips-jobs-actual-over-icon {
  margin-left: 0.25rem;
  color: #dc2626;
  font-size: 0.75rem;
  line-height: 1;
  cursor: help;
  flex-shrink: 0;
}
.ips-jobs-money-positive {
  color: #15803d;
  font-weight: 700;
}
.ips-jobs-health-badge {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  font-size: 0.625rem;
  font-weight: 800;
  white-space: nowrap;
  margin-top: 0;
}
.ips-jobs-health-healthy {
  background: #dcfce7;
  color: #14532d;
}
.ips-jobs-health-warning {
  background: #fef3c7;
  color: #92400e;
}
.ips-jobs-health-danger {
  background: #fee2e2;
  color: #991b1b;
}
.ips-jobs-health-neutral {
  background: #f1f5f9;
  color: #64748b;
}
.ips-job-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 22px;
  height: 22px;
  padding: 0 10px;
  font-size: 11px;
  font-weight: 800;
  border: none;
  line-height: 1;
  border-radius: 999px;
  white-space: nowrap;
}
.ips-job-status-active {
  background: #dcfce7;
  color: #166534;
}
.ips-job-status-pending,
.ips-job-status-estimate-pending {
  background: #fef3c7;
  color: #92400e;
}
.ips-job-status-scheduled {
  background: #ffedd5;
  color: #c2410c;
}
.ips-job-status-on-hold {
  background: #fee2e2;
  color: #991b1b;
}
.ips-job-status-completed {
  background: #dbeafe;
  color: #1d4ed8;
}
.ips-job-status-closed,
.ips-job-status-cancelled,
.ips-job-status-archived,
.ips-job-status-deleted {
  background: #f1f5f9;
  color: #64748b;
}
.ips-job-status-draft {
  background: #f1f5f9;
  color: #475569;
}
.ips-job-status-awarded {
  background: #dcfce7;
  color: #166534;
}
.ips-job-status-table-pill {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  pointer-events: auto;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) [data-testid="stPopover"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-pill) [data-testid="stPopover"] {
  margin: 0 !important;
  width: auto !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) [data-testid="stPopover"] > button,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) button[data-testid="stBaseButton-secondary"],
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) [data-testid="stPopover"] > button,
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) button[data-testid="stBaseButton-secondary"] {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 0.25rem !important;
  min-height: 30px !important;
  height: 30px !important;
  min-width: 58px !important;
  padding: 0 10px !important;
  border-radius: 8px !important;
  font-size: 0.75rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  white-space: nowrap !important;
  cursor: pointer !important;
  box-sizing: border-box !important;
  background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
  background-color: #2563eb !important;
  color: #ffffff !important;
  border: 1px solid #1e40af !important;
  box-shadow: none !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) [data-testid="stPopover"] > button:hover,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) button[data-testid="stBaseButton-secondary"]:hover,
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) [data-testid="stPopover"] > button:hover {
  background: linear-gradient(180deg, #1d4ed8 0%, #1e40af 100%) !important;
  background-color: #1d4ed8 !important;
  border-color: #1e3a8a !important;
  color: #ffffff !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) [data-testid="stPopover"] > button:focus-visible,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) button[data-testid="stBaseButton-secondary"]:focus-visible {
  outline: 2px solid #93c5fd !important;
  outline-offset: 1px !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) [data-testid="stPopover"] > button > div,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) [data-testid="stPopover"] > button p,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) [data-testid="stPopover"] > button span,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) button[data-testid="stBaseButton-secondary"] > div,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) button[data-testid="stBaseButton-secondary"] p,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) button[data-testid="stBaseButton-secondary"] span {
  color: #ffffff !important;
  font-weight: 700 !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) [data-testid="stPopover"] > button [data-testid="stIconMaterial"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-table-editor-marker) button[data-testid="stBaseButton-secondary"] [data-testid="stIconMaterial"] {
  color: #ffffff !important;
  fill: #ffffff !important;
}
.st-key-jobs_table_wrap .ips-job-status-table-pill .ips-job-status-pill {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-height: 30px !important;
  height: 30px !important;
  padding: 0 10px !important;
  border-radius: 8px !important;
  font-size: 0.75rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
  color: #ffffff !important;
  border: 1px solid #1e40af !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-popover"],
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.job-row-actions-menu) button[data-testid="stBaseButton-popover"],
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.ips-jobs-row-menu-marker) button[data-testid="stBaseButton-popover"] {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-width: 28px !important;
  width: 28px !important;
  max-width: 28px !important;
  min-height: 28px !important;
  height: 28px !important;
  padding: 0 !important;
  font-size: 1rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  border-radius: 6px !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  box-shadow: none !important;
  color: #64748b !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-popover"]:hover,
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) [data-testid="column"]:has(.ips-jobs-row-menu-marker) button[data-testid="stBaseButton-popover"]:hover {
  background: #f1f5f9 !important;
  border-color: #e2e8f0 !important;
  color: #0f172a !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-primary"] {
  display: none !important;
}
.ips-jobs-pagination-footer {
  margin-top: 0.85rem;
  padding: 0.65rem 0.25rem 0;
  border-top: 1px solid #e5eaf2;
}
.ips-jobs-pagination-summary {
  font-size: 0.8125rem;
  color: #64748b;
  font-weight: 600;
  margin: 0;
  text-align: center;
}
button,
.stButton button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
section[data-testid="stMain"]:has(.ips-jobs-page) .job-actions-button {
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
  min-width: fit-content !important;
}
/* Job # + Project / Description — bold blue links */
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-num) .ips-jobs-table-link button,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-desc) .ips-jobs-table-link button,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-num) .ips-jobs-table-link button p,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-desc) .ips-jobs-table-link button p,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-num) .ips-jobs-table-link button span,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-desc) .ips-jobs-table-link button span,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-num) button[kind="tertiary"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-desc) button[kind="tertiary"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-num) button[data-testid="stBaseButton-tertiary"],
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-desc) button[data-testid="stBaseButton-tertiary"] {
  color: #2563eb !important;
  font-weight: 800 !important;
  font-size: 0.8125rem !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  cursor: pointer !important;
  pointer-events: auto !important;
  transition: color 0.15s ease !important;
}
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-num) .ips-jobs-table-link button:hover,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-desc) .ips-jobs-table-link button:hover,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-num) .ips-jobs-table-link button:focus,
.st-key-jobs_table_wrap [data-testid="column"]:has(.ips-jobs-col-desc) .ips-jobs-table-link button:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_jobs_filter_bar_shell() -> None:
    st.markdown(
        '<div class="ips-jobs-filter-bar-wrap"><span class="ips-jobs-filter-bar-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )


def close_jobs_filter_bar_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def jobs_column_has_data(
    filtered: list[dict],
    cost_fields_fn,
    marker: str,
) -> bool:
    return any(
        (marker == "estimated" and bool(cost_fields_fn(job).get("has_estimated")))
        or (marker == "actual" and bool(cost_fields_fn(job).get("has_actual")))
        for job in filtered
    )


def jobs_visible_table_layout(
    filtered: list[dict],
    cost_fields_fn,
) -> tuple[tuple[str, ...], list[tuple[str, str | None]], list[float]]:
    markers: list[str] = []
    headers: list[tuple[str, str | None]] = []
    weights: list[float] = []
    for idx, marker in enumerate(_JOB_COL_MARKERS):
        if marker in _HIDE_IF_EMPTY_COLUMNS and not jobs_column_has_data(filtered, cost_fields_fn, marker):
            continue
        markers.append(marker)
        headers.append(_JOB_HEADER_SPECS[idx])
        weights.append(_JOB_COL_WEIGHTS[idx])
    return tuple(markers), headers, weights


def render_jobs_summary_cards(
    *,
    total: int,
    active: int,
    on_hold: int,
    completed: int,
    cancelled: int,
    open_subjobs: int,
    total_contract: float,
    total_actual: float,
    has_contract_data: bool = False,
    has_actual_data: bool = False,
) -> None:
    cards = [
        ("Total Jobs", f"{total:,}", "ips-jobs-stat-total"),
        ("Active", f"{active:,}", "ips-jobs-stat-active"),
        ("On Hold", f"{on_hold:,}", "ips-jobs-stat-on-hold"),
        ("Completed", f"{completed:,}", "ips-jobs-stat-completed"),
        ("Cancelled", f"{cancelled:,}", "ips-jobs-stat-cancelled"),
        ("Open Subjobs", f"{open_subjobs:,}", "ips-jobs-stat-subjobs"),
        ("Contract Value", _summary_money(total_contract, has_data=has_contract_data), "ips-jobs-stat-contract"),
        ("Actual Cost", _summary_money(total_actual, has_data=has_actual_data), "ips-jobs-stat-actual"),
    ]
    parts = ['<div class="ips-jobs-summary-cards">']
    for label, value, cls in cards:
        parts.append(
            f'<div class="ips-jobs-stat-card {cls}">'
            f'<p class="ips-jobs-stat-label">{html.escape(label)}</p>'
            f'<p class="ips-jobs-stat-value">{html.escape(value)}</p>'
            f"</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_jobs_summary_badge_bar(
    *,
    total: int,
    active: int,
    on_hold: int,
    open_subjobs: int,
    total_contract: float,
    has_contract_data: bool = False,
) -> None:
    contract_label = _summary_money(total_contract, has_data=has_contract_data)
    chips = [
        ("ips-jobs-summary-chip", f"<strong>{total:,}</strong> Jobs"),
        ("ips-jobs-summary-chip ips-jobs-chip-accent", f"<strong>{active:,}</strong> Active"),
        ("ips-jobs-summary-chip", f"<strong>{on_hold:,}</strong> Hold"),
        ("ips-jobs-summary-chip", f"<strong>{open_subjobs:,}</strong> Subjobs"),
    ]
    if has_contract_data and contract_label != "—":
        chips.append(
            ("ips-jobs-summary-chip ips-jobs-chip-money", f"<strong>{html.escape(contract_label)}</strong> Contract Value")
        )
    parts = ['<div class="ips-jobs-summary-bar">']
    for cls, inner in chips:
        parts.append(f'<span class="{cls}">{inner}</span>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_jobs_table_pagination_header(total: int, table_key: str) -> tuple[int, int, int]:
    page, page_size, total_pages = pagination_meta(total, table_key)
    _, size_col = st.columns([4.5, 1])
    with size_col:
        st.markdown(
            '<span class="ips-jobs-page-size-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        label_col, sel_col = st.columns([0.38, 0.62], gap="small")
        with label_col:
            st.markdown('<span class="ips-jobs-show-label">Show:</span>', unsafe_allow_html=True)
        with sel_col:
            picked = st.selectbox(
                "Show",
                list(_PAGE_SIZE_OPTIONS),
                index=_PAGE_SIZE_OPTIONS.index(page_size)
                if page_size in _PAGE_SIZE_OPTIONS
                else _PAGE_SIZE_OPTIONS.index(DEFAULT_CATALOG_PAGE_SIZE),
                key=f"{table_key}_pg_size_select",
                label_visibility="collapsed",
            )
        if int(picked) != page_size:
            st.session_state[page_size_key(table_key)] = int(picked)
            reset_table_page(table_key)
            st.rerun()
    return page, page_size, total_pages


def render_jobs_pagination_footer(total: int, table_key: str, *, item_label: str = "job") -> None:
    page, page_size, total_pages = pagination_meta(total, table_key)
    if total <= 0:
        start = end = 0
    else:
        start = (page - 1) * page_size + 1
        end = min(page * page_size, total)

    st.markdown('<div class="ips-jobs-pagination-footer">', unsafe_allow_html=True)
    st.markdown(
        f'<p class="ips-jobs-pagination-summary">Showing {start} to {end} of {total:,} {item_label}{"" if total == 1 else "s"}</p>',
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
                    f'<p class="ips-jobs-pagination-summary">Page {page} of {total_pages}</p>',
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


def render_jobs_view_navigation(
    options: list[str],
    *,
    session_key: str = "jobs_view",
    default: str | None = None,
) -> None:
    """Horizontal navigation tabs for job list views."""
    opts = [str(option).strip() for option in options if str(option).strip()]
    if not opts:
        return

    if session_key not in st.session_state:
        st.session_state[session_key] = default or opts[0]
    current = str(st.session_state.get(session_key) or "").strip()
    if current not in opts:
        st.session_state[session_key] = default or opts[0]

    st.markdown(
        '<span class="ips-jobs-view-nav-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ips-jobs-view-nav">', unsafe_allow_html=True)
    if hasattr(st, "segmented_control"):
        st.segmented_control(
            "Job view",
            opts,
            key=session_key,
            label_visibility="collapsed",
        )
    else:
        st.radio(
            "Job view",
            opts,
            key=session_key,
            horizontal=True,
            label_visibility="collapsed",
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_jobs_row_click_bridge() -> str | None:
    """Zero-height bridge: row click opens job detail via marker data-row-id."""
    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore

    st.markdown(
        '<span class="ips-jobs-row-click-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    return _components_html(
        """
<script>
(function () {
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = "ipsJobsRowClick::list";
  const tblSel = ".st-key-jobs_table_wrap";
  const rowSel = '[data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row)';

  function sendValue(id) {
    const payload = { type: "streamlit:setComponentValue", value: id };
    const frames = [window, window.parent, w].filter(function (f, i, arr) {
      return f && arr.indexOf(f) === i;
    });
    for (var i = 0; i < frames.length; i++) {
      try {
        if (frames[i].Streamlit && typeof frames[i].Streamlit.setComponentValue === "function") {
          frames[i].Streamlit.setComponentValue(id);
          return;
        }
      } catch (err) {}
    }
    for (var j = 0; j < frames.length; j++) {
      try { frames[j].postMessage(payload, "*"); } catch (err) {}
    }
  }

  function isInteractive(target) {
    return !!(target && target.closest && target.closest(
      "button, input, select, textarea, label, a, [data-testid='stButton'], [data-testid='stPopover'], [data-testid='stCheckbox'], .job-actions-cell, .job-actions-button, .job-row-actions-menu, .ips-jobs-table-link, .ips-jobs-list-link, .ips-job-status-table-editor-marker, .ips-job-status-table-pill"
    ));
  }

  function tableScope() {
    const anchor = doc.querySelector(tblSel);
    if (!anchor) return null;
    return anchor.closest('[data-testid="stVerticalBlockBorderWrapper"]') || anchor.parentElement;
  }

  function bindRows() {
    const scope = tableScope();
    if (!scope) return;
    scope.querySelectorAll(rowSel).forEach(function (row) {
      if (row.dataset.ipsJobsRowBound === "1") return;
      row.dataset.ipsJobsRowBound = "1";
      row.addEventListener("click", function (e) {
        if (isInteractive(e.target)) return;
        const marker = row.querySelector(".ips-jobs-table-row[data-row-id]");
        const id = marker && marker.getAttribute("data-row-id");
        if (!id) return;
        e.preventDefault();
        e.stopPropagation();
        sendValue(id);
      });
    });
  }

  if (!doc.ipsJobsRowClickRegistry) doc.ipsJobsRowClickRegistry = {};
  doc.ipsJobsRowClickRegistry[hookKey] = { bind: bindRows };
  bindRows();
  if (!doc.ipsJobsRowBindObserver) {
    doc.ipsJobsRowBindObserver = new MutationObserver(function () {
      Object.values(doc.ipsJobsRowClickRegistry || {}).forEach(function (cfg) {
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      });
    });
    doc.ipsJobsRowBindObserver.observe(doc.body, { childList: true, subtree: true });
  }
})();
</script>
        """,
        component_key="ips_jobs_list_row_click",
        height=1,
    )


def job_health_badge_html(cost_summary: dict) -> str:
    estimated = float(cost_summary.get("estimated_cost") or 0)
    actual = float(cost_summary.get("actual_cost") or 0)
    projected = float(cost_summary.get("projected_final_cost") or 0)
    if estimated <= 0:
        return ""
    if actual > estimated:
        label, tone = "Over Budget", "danger"
    elif projected > estimated * 1.05:
        label, tone = "At Risk", "warning"
    else:
        label, tone = "On Budget", "healthy"
    return (
        f'<span class="ips-jobs-health-badge ips-jobs-health-{tone}">'
        f"{html.escape(label)}</span>"
    )


def inject_dashboard_active_jobs_table_css() -> None:
    """Scope real HTML table styling to the dashboard Active Jobs panel."""
    st.markdown(
        """
<style id="ips-dashboard-active-jobs-table-v10">
.st-key-dashboard_active_jobs_table {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 11px !important;
  padding: 0.75rem !important;
  margin-top: 20px !important;
  margin-bottom: 20px !important;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06) !important;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow: visible !important;
  box-sizing: border-box !important;
}
.st-key-dashboard_active_jobs_table [data-testid="stMarkdownContainer"],
.st-key-dashboard_active_jobs_table [data-testid="stMarkdownContainer"] .stMarkdown,
.st-key-dashboard_active_jobs_table [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
  padding: 0 !important;
}
.st-key-dashboard_active_jobs_table [data-testid="stMarkdownContainer"] p:has(.ips-dash-jobs-table-scroll) {
  display: block !important;
}
.ips-ops-jobs-table-title {
  margin: 0 !important;
  font-size: 1.25rem !important;
  font-weight: 800 !important;
}
.ips-dash-jobs-table-scroll {
  width: 100%;
  max-width: 100%;
  max-height: min(420px, 48vh);
  overflow: auto;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  background: #ffffff;
  box-sizing: border-box;
  scrollbar-gutter: stable;
}
.ips-dash-jobs-html-table {
  display: table !important;
  width: 100%;
  min-width: 1400px;
  border-collapse: collapse;
  table-layout: fixed;
  border-spacing: 0;
}
.ips-dash-jobs-html-table col {
  display: table-column !important;
}
.ips-dash-jobs-html-table thead {
  display: table-header-group !important;
}
.ips-dash-jobs-html-table tbody {
  display: table-row-group !important;
}
.ips-dash-jobs-html-table tr {
  display: table-row !important;
  height: 46px !important;
  min-height: 46px !important;
  max-height: 46px !important;
}
.ips-dash-jobs-html-table thead tr {
  height: 44px !important;
  min-height: 44px !important;
  max-height: 44px !important;
}
.ips-dash-jobs-html-table th,
.ips-dash-jobs-html-table td {
  display: table-cell !important;
  vertical-align: middle !important;
  padding: 8px 12px;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  box-sizing: border-box;
  border-bottom: 1px solid #eef2f7;
  position: static !important;
  float: none !important;
  transform: none !important;
}
.ips-dash-jobs-html-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #eef2f7;
  color: #64748b;
  font-size: 0.58rem;
  font-weight: 800;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  border-bottom: 1px solid #dbe3ef;
  box-shadow: 0 1px 0 #dbe3ef;
}
.ips-dash-jobs-html-table tbody tr:hover {
  background: #eff6ff;
}
.ips-dash-row-even {
  background: #f8fafc;
}
.ips-dash-row-odd {
  background: #ffffff;
}
.ips-dash-th-contract,
.ips-dash-th-estimated,
.ips-dash-th-actual,
.ips-dash-th-profit,
.ips-dash-th-margin,
.ips-dash-td-contract,
.ips-dash-td-estimated,
.ips-dash-td-actual,
.ips-dash-td-profit,
.ips-dash-td-margin {
  text-align: right;
}
.ips-dash-th-status,
.ips-dash-th-subjobs,
.ips-dash-td-status,
.ips-dash-td-subjobs {
  text-align: center;
}
.ips-dash-jobs-html-table .cell-wrapper {
  display: flex;
  align-items: center;
  height: 100%;
  min-height: 0;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ips-dash-cell-right {
  justify-content: flex-end;
  text-align: right;
}
.ips-dash-cell-center {
  justify-content: center;
  text-align: center;
}
.ips-dash-job-link {
  color: #2563eb;
  font-weight: 700;
  font-size: 0.78rem;
  text-decoration: none;
  cursor: pointer;
  transition: color 0.15s ease;
}
.ips-dash-job-link:hover,
.ips-dash-job-link:focus {
  color: #1d4ed8;
  text-decoration: underline;
}
.ips-dash-customer-cell,
.ips-dash-money-cell {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #0f172a;
}
.ips-dash-money-cell.ips-jobs-money-positive {
  color: #15803d !important;
  font-weight: 700 !important;
}
.ips-dash-money-cell.ips-jobs-money-negative {
  color: #ea580c !important;
  font-weight: 700 !important;
}
.ips-dash-money-cell.ips-jobs-money-empty {
  color: #94a3b8 !important;
}
.ips-dash-jobs-html-table .ips-job-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 22px;
  min-height: 22px;
  max-height: 22px;
  padding: 0 10px;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
  margin: 0 auto;
}
.ips-dash-job-link-bridge-marker {
  display: none !important;
}
@media (max-width: 1200px) {
  .ips-dash-col-estimated,
  .ips-dash-th-estimated,
  .ips-dash-td-estimated,
  .ips-dash-col-actual,
  .ips-dash-th-actual,
  .ips-dash-td-actual {
    display: none;
  }
}
@media (max-width: 960px) {
  .ips-dash-col-profit,
  .ips-dash-th-profit,
  .ips-dash-td-profit,
  .ips-dash-col-margin,
  .ips-dash-th-margin,
  .ips-dash-td-margin,
  .ips-dash-col-subjobs,
  .ips-dash-th-subjobs,
  .ips-dash-td-subjobs {
    display: none;
  }
}
</style>
        """,
        unsafe_allow_html=True,
    )
