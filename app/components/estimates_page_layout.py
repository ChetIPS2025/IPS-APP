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

ESTIMATES_LIST_HEADER_SPECS: list[tuple[str, str | None]] = [
    ("ESTIMATE #", None),
    ("PROJECT / DESCRIPTION", None),
    ("CUSTOMER", "customer"),
    ("STATUS", "status"),
    ("TOTAL / CONTRACT VALUE", None),
    ("ACTIONS", None),
]


def estimates_list_header_specs() -> list[tuple[str, str | None]]:
    return list(ESTIMATES_LIST_HEADER_SPECS)


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
<style id="ips-estimates-page-layout-v7">
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
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 0.4rem;
  margin: 0 0 0.35rem 0;
}
.ips-estimates-stat-label,
.ips-estimates-stat-value {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
@media (max-width: 1500px) {
  .ips-estimates-summary-cards {
    grid-template-columns: repeat(auto-fit, minmax(128px, 1fr));
  }
}
@media (max-width: 900px) {
  .ips-estimates-summary-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.ips-estimates-stat-card {
  min-width: 0;
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
.ips-estimates-view-nav {
  margin: 0 0 0.4rem 0;
  padding: 0.2rem 0;
}
.ips-estimates-view-nav [data-testid="stRadio"],
.ips-estimates-view-nav [data-testid="stSegmentedControl"] {
  margin: 0 !important;
}
.ips-estimates-view-nav [data-testid="stRadio"] > div {
  gap: 0.35rem !important;
  flex-wrap: wrap !important;
}
.ips-estimates-view-nav [data-testid="stRadio"] label,
.ips-estimates-view-nav [data-testid="stSegmentedControl"] label {
  background: #f8fafc !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 999px !important;
  padding: 0.35rem 0.85rem !important;
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
  color: #475569 !important;
}
.st-key-estimates_table_wrap {
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
.st-key-estimates_table_wrap [data-testid="stMarkdownContainer"],
.st-key-estimates_table_wrap [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
  padding: 0 !important;
}
.st-key-estimates_table_wrap .ips-dash-est-table-scroll {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow-x: auto !important;
  margin-top: 0 !important;
  -webkit-overflow-scrolling: touch;
  scrollbar-gutter: stable;
}
.st-key-estimates_table_wrap .ips-dash-est-html-table {
  width: 100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  table-layout: fixed !important;
  background: #ffffff !important;
}
.st-key-estimates_table_wrap .ips-dash-est-html-table tr {
  display: table-row !important;
  height: 46px !important;
}
.st-key-estimates_table_wrap .ips-dash-est-html-table thead tr {
  height: 44px !important;
}
.st-key-estimates_table_wrap .ips-dash-est-html-table th,
.st-key-estimates_table_wrap .ips-dash-est-html-table td {
  display: table-cell !important;
  vertical-align: middle !important;
  padding: 0 10px !important;
  border-bottom: 1px solid #e8edf4 !important;
  overflow: hidden !important;
  box-sizing: border-box !important;
  background: #ffffff !important;
}
.st-key-estimates_table_wrap .ips-dash-est-html-table thead th {
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
.st-key-estimates_table_wrap .ips-dash-est-html-table tbody tr:hover td {
  background: #f8fbff !important;
}
.st-key-estimates_table_wrap .ips-dash-est-html-table tbody tr[data-estimate-id] {
  cursor: pointer !important;
}
.st-key-estimates_table_wrap .ips-dash-est-html-table .cell-wrapper {
  display: flex !important;
  align-items: center !important;
  min-height: 46px !important;
  width: 100% !important;
  min-width: 0 !important;
}
.st-key-estimates_table_wrap .ips-dash-est-cell-right {
  justify-content: flex-end !important;
  text-align: right !important;
}
.st-key-estimates_table_wrap .ips-dash-est-cell-center {
  justify-content: center !important;
  text-align: center !important;
}
.st-key-estimates_table_wrap .ips-dash-est-link,
.st-key-estimates_table_wrap .ips-estimates-open-link {
  color: #2563eb !important;
  font-weight: 800 !important;
  font-size: 0.8125rem !important;
  text-decoration: none !important;
  cursor: pointer !important;
  pointer-events: auto !important;
  position: relative !important;
  z-index: 2 !important;
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin: 0 !important;
  font-family: inherit !important;
  line-height: inherit !important;
  text-align: left !important;
}
.st-key-estimates_table_wrap .ips-estimates-open-link:hover,
.st-key-estimates_table_wrap .ips-estimates-open-link:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
  outline: none !important;
}
.st-key-estimates_table_wrap .ips-dash-est-desc-link {
  display: inline-block !important;
  max-width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.st-key-estimates_table_wrap .ips-dash-est-link:hover,
.st-key-estimates_table_wrap .ips-dash-est-link:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}
.st-key-estimates_open_button_harness,
.st-key-estimates_open_button_harness [data-testid="stVerticalBlock"],
.st-key-estimates_open_button_harness [data-testid="stElementContainer"] {
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
.st-key-estimates_open_button_harness [class*="st-key-est_bridge_open_"] {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  pointer-events: auto !important;
}
.st-key-estimates_open_button_harness [class*="st-key-est_bridge_open_"] button {
  width: 1px !important;
  height: 1px !important;
  min-height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  opacity: 0 !important;
  pointer-events: auto !important;
}
.st-key-estimates_table_wrap .ips-dash-est-customer-cell {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  color: #0f172a !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.st-key-estimates_table_wrap .ips-dash-est-total-cell {
  font-size: 0.8125rem !important;
  font-weight: 800 !important;
  color: #2563eb !important;
  font-variant-numeric: tabular-nums !important;
}
.st-key-estimates_table_wrap .ips-estimate-status-pill {
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
.st-key-estimates_table_wrap .ips-dash-est-actions {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 6px !important;
  flex-wrap: nowrap !important;
}
.st-key-estimates_table_wrap .ips-dash-est-action {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 30px !important;
  min-width: 58px !important;
  padding: 0 10px !important;
  border-radius: 8px !important;
  font-size: 0.75rem !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  cursor: pointer !important;
  white-space: nowrap !important;
  box-sizing: border-box !important;
  border: none !important;
  pointer-events: auto !important;
  position: relative !important;
  z-index: 2 !important;
}
.st-key-estimates_table_wrap .ips-dash-est-approve {
  background: #ffffff !important;
  color: #2563eb !important;
  border: 1px solid #bfdbfe !important;
}
.st-key-estimates_table_wrap .ips-dash-est-approve:hover,
.st-key-estimates_table_wrap .ips-dash-est-approve:focus {
  background: #eff6ff !important;
  border-color: #93c5fd !important;
  color: #1d4ed8 !important;
}
.st-key-estimates_table_wrap .ips-dash-est-view {
  background: linear-gradient(180deg, #2563eb 0%, #1d4ed8 100%) !important;
  color: #ffffff !important;
  border: 1px solid #1e40af !important;
}
.st-key-estimates_table_wrap .ips-dash-est-view:hover,
.st-key-estimates_table_wrap .ips-dash-est-view:focus {
  background: linear-gradient(180deg, #1d4ed8 0%, #1e40af 100%) !important;
  color: #ffffff !important;
}
.st-key-estimates_table_wrap .ips-est-approve-done {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  height: 30px !important;
  padding: 0 8px !important;
  font-size: 0.68rem !important;
  font-weight: 700 !important;
  color: #15803d !important;
  white-space: nowrap !important;
}
.ips-estimates-table-filter-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.65rem;
  background: #f8fafc;
  border-bottom: 1px solid #e8edf4;
}
.ips-estimates-filter-toolbar-cell {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}
@media (max-width: 768px) {
  .st-key-estimates_table_wrap .ips-dash-est-html-table {
    table-layout: auto !important;
  }
  .st-key-estimates_table_wrap .ips-dash-est-action {
    min-width: 52px !important;
    padding: 0 8px !important;
    font-size: 0.7rem !important;
  }
}
.st-key-estimates_table_wrap [data-testid="stVerticalBlockBorderWrapper"] {
  background: #ffffff !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
}
.st-key-estimates_table_wrap [data-testid="stVerticalBlockBorderWrapper"] > div {
  padding: 0 !important;
  background: #ffffff !important;
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


def render_estimates_view_navigation(
    options: list[str],
    *,
    session_key: str = "estimates_view",
    default: str | None = None,
) -> None:
    """Horizontal navigation tabs for estimate list views."""
    opts = [str(option).strip() for option in options if str(option).strip()]
    if not opts:
        return

    if session_key not in st.session_state:
        st.session_state[session_key] = default or opts[0]
    current = str(st.session_state.get(session_key) or "").strip()
    if current not in opts:
        st.session_state[session_key] = default or opts[0]

    st.markdown(
        '<span class="ips-estimates-view-nav-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ips-estimates-view-nav">', unsafe_allow_html=True)
    if hasattr(st, "segmented_control"):
        st.segmented_control(
            "Estimate view",
            opts,
            key=session_key,
            label_visibility="collapsed",
        )
    else:
        st.radio(
            "Estimate view",
            opts,
            key=session_key,
            horizontal=True,
            label_visibility="collapsed",
        )
    st.markdown("</div>", unsafe_allow_html=True)
