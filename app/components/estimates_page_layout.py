"""Estimates list page — layout styling aligned with Jobs page (UI only)."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.table_pagination import (
        DEFAULT_CATALOG_PAGE_SIZE,
        page_key,
        page_size_key,
        pagination_meta,
        reset_table_page,
    )
except ImportError:
    from components.table_pagination import (  # type: ignore
        DEFAULT_CATALOG_PAGE_SIZE,
        page_key,
        page_size_key,
        pagination_meta,
        reset_table_page,
    )

_PAGE_SIZE_OPTIONS = (50, 75, 100, 150)


def _money(value: float) -> str:
    return f"${float(value or 0):,.2f}"


def _summary_money(value: float, *, has_data: bool) -> str:
    if not has_data:
        return "—"
    if abs(float(value or 0)) < 0.005:
        return "—"
    return _money(value)


def estimate_col_marker(name: str) -> str:
    safe = html.escape(str(name or "").strip())
    return (
        f'<span class="ips-estimates-col-marker ips-estimates-col-{safe}" '
        f'aria-hidden="true"></span>'
    )


def inject_estimates_page_layout_css() -> None:
    st.markdown(
        """
<style id="ips-estimates-page-layout-v2">
section[data-testid="stMain"]:has(.ips-estimates-page) {
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-estimates-page) .block-container {
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-estimates-page) [data-testid="stVerticalBlock"] {
  gap: 0.35rem !important;
}
section[data-testid="stMain"]:has(.ips-estimates-page) [data-testid="stElementContainer"] {
  margin-bottom: 0.15rem !important;
}
section[data-testid="stMain"]:has(.ips-estimates-page) .ips-page-header {
  margin-bottom: 0.15rem !important;
  padding-bottom: 0 !important;
}
section[data-testid="stMain"]:has(.ips-estimates-page) .ips-page-title {
  font-size: 1.35rem !important;
  margin: 0 !important;
  line-height: 1.15 !important;
}
section[data-testid="stMain"]:has(.ips-estimates-page) .ips-page-subtitle {
  font-size: 0.78rem !important;
  margin: 0.12rem 0 0 !important;
  line-height: 1.3 !important;
}
section[data-testid="stMain"]:has(.ips-estimates-page) .ips-page-actions-marker + [data-testid="stHorizontalBlock"] {
  gap: 0.4rem !important;
  justify-content: flex-end !important;
}
.ips-estimates-filter-bar-wrap {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.38rem 0.5rem;
  margin-bottom: 0.35rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.ips-estimates-filter-bar-wrap [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  gap: 0.45rem !important;
}
section[data-testid="stMain"]:has(.ips-estimates-page) .ips-estimates-filter-bar-wrap [data-testid="stTextInput"] input,
section[data-testid="stMain"]:has(.ips-estimates-page) .ips-estimates-filter-bar-wrap [data-testid="stSelectbox"] > div > div {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 8px !important;
  min-height: 34px !important;
  font-size: 0.8125rem !important;
}
section[data-testid="stMain"]:has(.ips-estimates-page) .ips-estimates-filter-bar-wrap .stButton > button {
  min-height: 34px !important;
  height: 34px !important;
  font-size: 0.8125rem !important;
}
.ips-estimates-summary-cards {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0.4rem;
  margin: 0 0 0.35rem 0;
}
@media (max-width: 1400px) {
  .ips-estimates-summary-cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 900px) {
  .ips-estimates-summary-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.ips-estimates-stat-card {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.45rem 0.55rem 0.5rem;
  min-height: 52px;
  border-left-width: 4px;
  border-left-style: solid;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: box-shadow 0.12s ease, border-color 0.12s ease;
}
.ips-estimates-stat-card:hover {
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.1);
  border-color: #bfd3f2;
}
.ips-estimates-stat-label {
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  margin: 0 0 0.15rem 0;
  line-height: 1.2;
}
.ips-estimates-stat-value {
  font-size: 1.05rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.ips-estimates-stat-total { border-left-color: #1e3a8a; }
.ips-estimates-stat-total .ips-estimates-stat-value { color: #1e3a8a; }
.ips-estimates-stat-active { border-left-color: #2563eb; }
.ips-estimates-stat-active .ips-estimates-stat-value { color: #2563eb; }
.ips-estimates-stat-draft { border-left-color: #64748b; }
.ips-estimates-stat-draft .ips-estimates-stat-value { color: #64748b; }
.ips-estimates-stat-sent { border-left-color: #d97706; }
.ips-estimates-stat-sent .ips-estimates-stat-value { color: #d97706; }
.ips-estimates-stat-approved { border-left-color: #15803d; }
.ips-estimates-stat-approved .ips-estimates-stat-value { color: #15803d; }
.ips-estimates-stat-value-card { border-left-color: #15803d; }
.ips-estimates-stat-value-card .ips-estimates-stat-value { color: #15803d; }
.ips-estimates-summary-bar {
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
.ips-estimates-summary-chip {
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
.ips-estimates-summary-chip strong {
  font-weight: 800;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}
.ips-estimates-summary-chip.ips-estimates-chip-accent strong {
  color: #2563eb;
}
.ips-estimates-summary-chip.ips-estimates-chip-money strong {
  color: #15803d;
}
section[data-testid="stMain"]:has(.ips-estimates-page) [data-testid="column"]:has(.ips-estimates-page-size-marker) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 0.35rem !important;
  margin-bottom: 0.25rem !important;
}
.ips-estimates-show-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #475569;
  white-space: nowrap;
}
section[data-testid="stMain"]:has(.ips-estimates-page) [data-testid="column"]:has(.ips-estimates-page-size-marker) [data-testid="stSelectbox"] {
  max-width: 5.5rem;
}
section[data-testid="stMain"]:has(.ips-estimates-page) [data-testid="column"]:has(.ips-estimates-page-size-marker) [data-testid="stSelectbox"] > div > div {
  min-height: 34px !important;
  border-radius: 8px !important;
  border: 1px solid #dbe3ef !important;
  background: #ffffff !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
}
.ips-estimates-pagination-footer {
  margin-top: 0.85rem;
  padding: 0.65rem 0.25rem 0;
  border-top: 1px solid #e5eaf2;
}
.ips-estimates-pagination-summary {
  font-size: 0.8125rem;
  color: #64748b;
  font-weight: 600;
  margin: 0;
  text-align: center;
}
.st-key-estimates_table_wrap {
  max-height: min(calc(100vh - 200px), 980px);
  min-height: 520px;
  overflow-x: auto !important;
  overflow-y: auto !important;
  position: relative;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  padding-right: 6px;
  scrollbar-gutter: stable;
}
.ips-estimates-table-wrap {
  background: #ffffff;
  border: none;
  border-radius: 0;
  overflow: visible;
  min-width: min(100%, max-content);
  margin-bottom: 0;
}
.st-key-estimates_table_wrap .ips-estimates-col-marker {
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
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"] {
  gap: 0.25rem !important;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-estimates-table-row) {
  display: flex !important;
  align-items: center !important;
  min-height: 48px !important;
  max-height: 52px !important;
  height: 50px !important;
  min-width: max-content !important;
  padding: 0 10px 0 8px !important;
  background: #ffffff !important;
  border-bottom: 1px solid #e8edf4 !important;
  transition: background-color 0.12s ease !important;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-estimates-row-even) {
  background: #f8fafc !important;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-estimates-row-odd) {
  background: #ffffff !important;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-estimates-table-row):hover {
  background: #eff6ff !important;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:has([data-testid="stCheckbox"] input:checked) {
  background: #eaf2ff !important;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {
  display: flex !important;
  align-items: center !important;
  background: #eef2f7 !important;
  min-height: 40px !important;
  max-height: 44px !important;
  height: 42px !important;
  min-width: max-content !important;
  padding: 0 10px 0 8px !important;
  cursor: default !important;
  position: sticky !important;
  top: 0 !important;
  z-index: 12 !important;
  box-shadow: 0 1px 0 #dbe3ef !important;
  border-bottom: 1px solid #dbe3ef !important;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:first-of-type .ips-estimates-header-row {
  font-size: 0.58rem !important;
  font-weight: 800 !important;
  letter-spacing: 0.03em;
  color: #64748b !important;
  text-transform: uppercase;
  padding: 0 !important;
  white-space: normal !important;
  word-break: break-word !important;
  line-height: 1.15 !important;
  background: transparent !important;
  border: none !important;
  min-height: 0 !important;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-estimates-table-row) > [data-testid="column"],
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:first-of-type > [data-testid="column"] {
  display: flex !important;
  flex-direction: column !important;
  justify-content: center !important;
  align-items: stretch !important;
  align-self: stretch !important;
  min-height: 0 !important;
  padding: 0 0.2rem !important;
  min-width: 0 !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-sel) {
  flex: 0 0 36px !important;
  min-width: 36px !important;
  max-width: 40px !important;
  flex-shrink: 0 !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-num) {
  flex: 0 0 108px !important;
  min-width: 108px !important;
  max-width: none !important;
  flex-shrink: 0 !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-desc) {
  flex: 2.2 1 200px !important;
  min-width: 200px !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-customer) {
  flex: 1.55 1 140px !important;
  min-width: 140px !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-job) {
  flex: 1.05 1 110px !important;
  min-width: 110px !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-status) {
  flex: 1.05 1 110px !important;
  min-width: 110px !important;
  align-items: center !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-date) {
  flex: 1.15 1 120px !important;
  min-width: 120px !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-total) {
  flex: 0.95 1 100px !important;
  min-width: 100px !important;
  align-items: flex-end !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-actions) {
  flex: 0 0 110px !important;
  min-width: 110px !important;
  width: 110px !important;
  max-width: 110px !important;
  flex-shrink: 0 !important;
  position: sticky !important;
  right: 0 !important;
  z-index: 3 !important;
  background: inherit !important;
  box-shadow: -1px 0 0 #eef2f7;
}
.st-key-estimates_table_wrap [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:has(.ips-estimates-col-actions) {
  z-index: 5 !important;
  background: #eef2f7 !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-total) .ips-estimates-number,
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-total) .ips-estimates-cell {
  text-align: right !important;
  width: 100% !important;
}
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-status) [data-testid="stMarkdown"],
.st-key-estimates_table_wrap [data-testid="column"]:has(.ips-estimates-col-status) [data-testid="stElementContainer"] {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 100% !important;
}
.st-key-estimates_table_wrap .stButton > button {
  min-height: 28px !important;
  height: 28px !important;
  padding: 0 0.45rem !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  width: auto !important;
  max-width: 100% !important;
}
.ips-est-revision-banner {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-left: 4px solid #2563eb;
  border-radius: 8px;
  padding: 0.65rem 0.85rem;
  margin: 0 0 0.75rem 0;
  font-size: 0.8125rem;
  color: #1e3a8a;
  line-height: 1.45;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_estimates_filter_bar_shell() -> None:
    st.markdown(
        '<div class="ips-estimates-filter-bar-wrap">'
        '<span class="ips-estimates-filter-bar-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )


def close_estimates_filter_bar_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_estimates_summary_cards(
    *,
    total: int,
    active: int,
    draft: int,
    sent: int,
    approved: int,
    total_customer_value: float,
    has_value_data: bool = False,
) -> None:
    cards = [
        ("Total Estimates", f"{total:,}", "ips-estimates-stat-total"),
        ("Active Estimates", f"{active:,}", "ips-estimates-stat-active"),
        ("Draft Estimates", f"{draft:,}", "ips-estimates-stat-draft"),
        ("Sent Estimates", f"{sent:,}", "ips-estimates-stat-sent"),
        ("Approved Estimates", f"{approved:,}", "ips-estimates-stat-approved"),
        (
            "Total Customer Value",
            _summary_money(total_customer_value, has_data=has_value_data),
            "ips-estimates-stat-value-card",
        ),
    ]
    parts = ['<div class="ips-estimates-summary-cards">']
    for label, value, cls in cards:
        parts.append(
            f'<div class="ips-estimates-stat-card {cls}">'
            f'<p class="ips-estimates-stat-label">{html.escape(label)}</p>'
            f'<p class="ips-estimates-stat-value">{html.escape(value)}</p>'
            f"</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_estimates_summary_badge_bar(
    *,
    total: int,
    active: int,
    draft: int,
    sent: int,
    total_customer_value: float,
    has_value_data: bool = False,
) -> None:
    value_label = _summary_money(total_customer_value, has_data=has_value_data)
    chips = [
        ("ips-estimates-summary-chip", f"<strong>{total:,}</strong> Estimates"),
        ("ips-estimates-summary-chip ips-estimates-chip-accent", f"<strong>{active:,}</strong> Active"),
        ("ips-estimates-summary-chip", f"<strong>{draft:,}</strong> Draft"),
        ("ips-estimates-summary-chip", f"<strong>{sent:,}</strong> Sent"),
    ]
    if has_value_data and value_label != "—":
        chips.append(
            (
                "ips-estimates-summary-chip ips-estimates-chip-money",
                f"<strong>{html.escape(value_label)}</strong> Customer Value",
            )
        )
    parts = ['<div class="ips-estimates-summary-bar">']
    for cls, inner in chips:
        parts.append(f'<span class="{cls}">{inner}</span>')
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_estimates_table_pagination_header(total: int, table_key: str) -> tuple[int, int, int]:
    page, page_size, total_pages = pagination_meta(total, table_key)
    _, size_col = st.columns([4.5, 1])
    with size_col:
        st.markdown(
            '<span class="ips-estimates-page-size-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        label_col, sel_col = st.columns([0.38, 0.62], gap="small")
        with label_col:
            st.markdown('<span class="ips-estimates-show-label">Show:</span>', unsafe_allow_html=True)
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


def render_estimates_pagination_footer(total: int, table_key: str, *, item_label: str = "estimate") -> None:
    page, page_size, total_pages = pagination_meta(total, table_key)
    if total <= 0:
        start = end = 0
    else:
        start = (page - 1) * page_size + 1
        end = min(page * page_size, total)

    st.markdown('<div class="ips-estimates-pagination-footer">', unsafe_allow_html=True)
    st.markdown(
        f'<p class="ips-estimates-pagination-summary">Showing {start} to {end} of {total:,} '
        f'{item_label}{"" if total == 1 else "s"}</p>',
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
                    f'<p class="ips-estimates-pagination-summary">Page {page} of {total_pages}</p>',
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
