"""Assets list page — professional layout styling (UI only)."""

from __future__ import annotations

import html

import streamlit as st

from app.ui.css_inject import inject_css_once

from app.components.table_pagination import (
    page_key,
    page_size_key,
    pagination_meta,
    reset_table_page,
)
_EQUIPMENT_BANNER = (
    "Large assets and rentable equipment — tool trailers, generators, pressure washers, "
    "dump trailers, and similar fleet items."
)
_ASSETS_PAGE_SIZE_OPTIONS = (50, 75, 100, 150)


def inject_assets_page_layout_css() -> None:
    """Assets page layout overrides."""
    if not inject_css_once("ips-assets-page-layout-v8"):
        return
    with st.sidebar:
        st.markdown(
            """
<style id="ips-assets-page-layout-v8">
section[data-testid="stMain"]:has(.ips-assets-page) {
  background: #ffffff !important;
}
.ips-assets-filter-bar-wrap {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.38rem 0.5rem;
  margin-bottom: 0.35rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.ips-assets-filter-bar-wrap [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  gap: 0.45rem !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-filter-bar-wrap [data-testid="stTextInput"] input,
section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-filter-bar-wrap [data-testid="stSelectbox"] > div > div {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 8px !important;
  min-height: 34px !important;
  font-size: 0.8125rem !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) .ips-assets-filter-bar-wrap .stButton > button {
  min-height: 34px !important;
  height: 34px !important;
  font-size: 0.8125rem !important;
}
.st-key-assets_table_wrap {
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
.st-key-assets_table_wrap [data-testid="stMarkdownContainer"],
.st-key-assets_table_wrap [data-testid="stMarkdownContainer"] p {
  margin: 0 !important;
  padding: 0 !important;
}
.st-key-assets_table_wrap .ips-dash-est-table-scroll {
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow-x: auto !important;
  margin-top: 0 !important;
  -webkit-overflow-scrolling: touch;
  scrollbar-gutter: stable;
}
.st-key-assets_table_wrap .ips-dash-est-html-table {
  width: 100% !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
  table-layout: fixed !important;
  background: #ffffff !important;
}
.st-key-assets_table_wrap .ips-dash-est-html-table tr {
  display: table-row !important;
  height: 46px !important;
}
.st-key-assets_table_wrap .ips-dash-est-html-table thead tr {
  height: 44px !important;
}
.st-key-assets_table_wrap .ips-dash-est-html-table th,
.st-key-assets_table_wrap .ips-dash-est-html-table td {
  display: table-cell !important;
  vertical-align: middle !important;
  padding: 0 10px !important;
  border-bottom: 1px solid #e8edf4 !important;
  overflow: hidden !important;
  box-sizing: border-box !important;
  background: #ffffff !important;
}
.st-key-assets_table_wrap .ips-dash-est-html-table thead th {
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
.st-key-assets_table_wrap .ips-dash-est-html-table tbody tr {
  cursor: pointer !important;
}
.st-key-assets_table_wrap .ips-dash-est-html-table tbody tr:hover td {
  background: #f8fbff !important;
}
.st-key-assets_table_wrap .ips-dash-est-html-table tbody tr.ips-inventory-row-expanded td {
  background: #f0f7ff !important;
}
.st-key-assets_table_wrap .ips-dash-est-html-table .cell-wrapper {
  display: flex !important;
  align-items: center !important;
  min-height: 46px !important;
  width: 100% !important;
  min-width: 0 !important;
}
.st-key-assets_table_wrap .ips-dash-est-cell-right {
  justify-content: flex-end !important;
  text-align: right !important;
}
.st-key-assets_table_wrap .ips-dash-est-cell-center {
  justify-content: center !important;
  text-align: center !important;
}
.st-key-assets_table_wrap .ips-dash-est-link,
.st-key-assets_table_wrap .ips-inventory-desc-link,
.st-key-assets_table_wrap .ips-assets-open-link,
.st-key-assets_table_wrap button.ips-assets-open-link {
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
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-dash-est-desc-cell {
  flex-direction: column !important;
  align-items: flex-start !important;
  justify-content: center !important;
  gap: 0.08rem !important;
}
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-inventory-text-cell,
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-inventory-muted,
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-dash-est-link,
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-inventory-desc-link,
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-assets-open-link,
.st-key-assets_table_wrap .ips-assets-html-equipment-table [role="button"][data-asset-action="open"] {
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
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-inventory-text-cell {
  color: #0f172a !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
}
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-inventory-muted {
  color: #64748b !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
}
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-dash-est-link,
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-inventory-desc-link,
.st-key-assets_table_wrap .ips-assets-html-equipment-table .ips-assets-open-link,
.st-key-assets_table_wrap .ips-assets-html-equipment-table [role="button"][data-asset-action="open"] {
  color: #2563eb !important;
  -webkit-text-fill-color: #2563eb !important;
}
.st-key-assets_table_wrap [data-testid="stMarkdownContainer"] .ips-assets-html-equipment-table,
.st-key-assets_table_wrap [data-testid="stMarkdownContainer"] .ips-assets-html-equipment-table * {
  pointer-events: auto;
}
.st-key-assets_table_wrap [data-testid="stMarkdownContainer"]:has(.ips-assets-html-equipment-table) {
  overflow: visible !important;
  width: 100% !important;
  max-width: 100% !important;
}
.st-key-assets_table_wrap .ips-dash-est-desc-link {
  display: inline-block !important;
  max-width: 100% !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.st-key-assets_table_wrap .ips-dash-est-link:hover,
.st-key-assets_table_wrap .ips-dash-est-link:focus,
.st-key-assets_table_wrap .ips-inventory-desc-link:hover,
.st-key-assets_table_wrap .ips-inventory-desc-link:focus,
.st-key-assets_table_wrap .ips-assets-open-link:hover,
.st-key-assets_table_wrap .ips-assets-open-link:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}
.st-key-assets_table_wrap .ips-inventory-text-cell,
.st-key-assets_table_wrap .ips-inventory-muted {
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  color: #0f172a !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}
.st-key-assets_table_wrap .ips-inventory-muted {
  color: #64748b !important;
}
.st-key-assets_table_wrap .ips-inventory-image-td {
  justify-content: center !important;
}
.st-key-assets_table_wrap .ips-inventory-thumb-cell-link {
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
.st-key-assets_table_wrap .ips-inventory-thumb-img,
.st-key-assets_table_wrap .ips-inventory-thumb-placeholder {
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
.st-key-assets_table_wrap .ips-inventory-status-pill {
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
.st-key-assets_table_wrap .ips-inventory-status-in-stock {
  background: #dcfce7 !important;
  color: #166534 !important;
}
.st-key-assets_table_wrap .ips-inventory-status-low-stock {
  background: #fef3c7 !important;
  color: #92400e !important;
}
.st-key-assets_table_wrap .ips-inventory-status-out-of-stock {
  background: #ffedd5 !important;
  color: #c2410c !important;
}
.st-key-assets_table_wrap .ips-inventory-status-on-order {
  background: #dbeafe !important;
  color: #1d4ed8 !important;
}
.st-key-assets_table_wrap .ips-inventory-status-discontinued {
  background: #f1f5f9 !important;
  color: #475569 !important;
}
.ips-assets-table-filter-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0.65rem;
  background: #f8fafc;
  border-bottom: 1px solid #e8edf4;
}
.ips-assets-filter-toolbar-cell {
  font-size: 0.68rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #64748b;
}
.ips-asset-rental-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0.12rem 0 0;
  padding: 0.12rem 0.42rem;
  border-radius: 4px;
  font-size: 0.58rem;
  font-weight: 800;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: #0f766e;
  background: #ecfdf5;
  border: 1px solid #99f6e4;
  vertical-align: middle;
  white-space: nowrap;
}
.ips-assets-name-badges {
  margin-top: 0.05rem;
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
@media (max-width: 768px) {
  .st-key-assets_table_wrap .ips-dash-est-html-table {
    table-layout: auto !important;
  }
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


def _stat_pct(part: int, whole: int) -> str:
    if whole <= 0:
        return "0%"
    return f"{round(part / whole * 100)}%"


def render_assets_summary_cards(
    *,
    total: int,
    available: int,
    checked_out: int,
    out_for_repair: int,
    service_due: int,
) -> None:
    """Equipment tab KPI strip above the table."""
    cards = [
        ("Total Assets", f"{total:,}", "", "ips-assets-stat-total"),
        ("Available", f"{available:,}", _stat_pct(available, total), "ips-assets-stat-available"),
        ("Checked Out", f"{checked_out:,}", _stat_pct(checked_out, total), "ips-assets-stat-checked-out"),
        ("Out For Repair", f"{out_for_repair:,}", _stat_pct(out_for_repair, total), "ips-assets-stat-repair"),
        ("Service Due", f"{service_due:,}", _stat_pct(service_due, total), "ips-assets-stat-service"),
    ]
    parts = ['<div class="ips-assets-summary-cards">']
    for label, value, pct, cls in cards:
        pct_html = f'<p class="ips-assets-stat-pct">{html.escape(pct)}</p>' if pct else ""
        parts.append(
            f'<div class="ips-assets-stat-card {cls}">'
            f'<p class="ips-assets-stat-label">{html.escape(label)}</p>'
            f'<p class="ips-assets-stat-value">{html.escape(value)}</p>'
            f"{pct_html}"
            f"</div>"
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_assets_equipment_row_click_bridge() -> str | None:
    """Zero-height bridge: row click opens asset detail via marker data-row-id."""
    from app.ui.clean_table import _components_html
    st.markdown(
        '<span class="ips-assets-row-click-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    return _components_html(
        """
<script>
(function () {
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = "ipsAssetsRowClick::equipment";
  const tblSel = ".st-key-assets_table_wrap";
  const rowSel = '[data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row)';

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
      "button, input, select, textarea, label, a, [data-testid='stButton'], [data-testid='stPopover'], [data-testid='stCheckbox'], .asset-actions-cell, .asset-actions-button, .ips-assets-name-cell-link, .ips-assets-thumb-cell-link"
    ));
  }

  function tableScope() {
    const anchor = doc.querySelector(tblSel);
    if (!anchor) return null;
    return anchor.closest('[data-testid="stVerticalBlockBorderWrapper"]') || anchor.parentElement;
  }

  function bindAssetOpenLinks() {
    const scope = tableScope();
    if (!scope) return;
    scope.querySelectorAll(".ips-assets-name-cell-link[data-row-id], .ips-assets-thumb-cell-link[data-row-id]").forEach(function (cell) {
      if (cell.dataset.ipsAssetsOpenBound === "1") return;
      cell.dataset.ipsAssetsOpenBound = "1";
      function openAssetDetail(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const id = cell.getAttribute("data-row-id");
        if (id) sendValue(id);
      }
      cell.addEventListener("click", openAssetDetail);
      cell.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") openAssetDetail(ev);
      });
      cell.querySelectorAll("a.asset-name-link[data-row-id]").forEach(function (link) {
        link.addEventListener("click", openAssetDetail);
      });
    });
  }

  function bindRows() {
    const scope = tableScope();
    if (!scope) return;
    scope.querySelectorAll(rowSel).forEach(function (row) {
      if (row.dataset.ipsAssetsRowBound === "1") return;
      row.dataset.ipsAssetsRowBound = "1";
      row.addEventListener("click", function (e) {
        if (isInteractive(e.target)) return;
        const marker = row.querySelector(".ips-assets-equipment-table-row[data-row-id]");
        const id = marker && marker.getAttribute("data-row-id");
        if (!id) return;
        e.preventDefault();
        e.stopPropagation();
        sendValue(id);
      });
    });
    bindAssetOpenLinks();
  }

  if (!doc.ipsAssetsRowClickRegistry) doc.ipsAssetsRowClickRegistry = {};
  doc.ipsAssetsRowClickRegistry[hookKey] = { bind: bindRows };
  bindRows();
  if (!doc.ipsAssetsRowBindObserver) {
    doc.ipsAssetsRowBindObserver = new MutationObserver(function () {
      Object.values(doc.ipsAssetsRowClickRegistry || {}).forEach(function (cfg) {
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      });
    });
    doc.ipsAssetsRowBindObserver.observe(doc.body, { childList: true, subtree: true });
  }
})();
</script>
        """,
        component_key="ips_assets_equipment_row_click",
        height=1,
    )


def render_assets_table_pagination_header(total: int, table_key: str) -> tuple[int, int, int]:
    """Show: [page size] selector aligned above the table."""
    from app.components.table_pagination import DEFAULT_CATALOG_PAGE_SIZE
    page, page_size, total_pages = pagination_meta(total, table_key)
    _, size_col = st.columns([4.5, 1])
    with size_col:
        st.markdown(
            '<span class="ips-assets-page-size-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        label_col, sel_col = st.columns([0.38, 0.62], gap="small")
        with label_col:
            st.markdown('<span class="ips-assets-show-label">Show:</span>', unsafe_allow_html=True)
        with sel_col:
            picked = st.selectbox(
                "Show",
                list(_ASSETS_PAGE_SIZE_OPTIONS),
                index=_ASSETS_PAGE_SIZE_OPTIONS.index(page_size)
                if page_size in _ASSETS_PAGE_SIZE_OPTIONS
                else _ASSETS_PAGE_SIZE_OPTIONS.index(DEFAULT_CATALOG_PAGE_SIZE),
                key=f"{table_key}_pg_size_select",
                label_visibility="collapsed",
            )
        if int(picked) != page_size:
            st.session_state[page_size_key(table_key)] = int(picked)
            reset_table_page(table_key)
            st.rerun()
    return page, page_size, total_pages


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
