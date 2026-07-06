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
_ASSETS_PAGE_SIZE_OPTIONS = (50, 75, 100, 150)


def inject_assets_page_layout_css() -> None:
    """Always inject — assets page layout overrides."""
    st.markdown(
        """
<style id="ips-assets-page-layout-v5">
section[data-testid="stMain"]:has(.ips-assets-page) {
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) .block-container {
  background: #ffffff !important;
}
/* Main category tabs — Equipment, Serialized Tools, Small Tools */
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [data-baseweb="tab-list"],
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [role="tablist"] {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-bottom: none !important;
  border-radius: 12px 12px 0 0 !important;
  padding: 0.15rem 0.5rem 0 !important;
  margin-bottom: 0 !important;
  gap: 0 !important;
  box-shadow: none !important;
  overflow-x: auto !important;
  scrollbar-width: thin;
}
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] button[data-baseweb="tab"],
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [data-baseweb="tab"],
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [role="tab"] {
  background: #ffffff !important;
  border: none !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  color: #334155 !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
  padding: 0.65rem 1rem 0.55rem !important;
  margin: 0 !important;
  min-height: 2.75rem !important;
  white-space: nowrap !important;
  transition: color 0.15s ease, border-color 0.15s ease !important;
}
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] button[data-baseweb="tab"]:hover:not([aria-selected="true"]),
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [data-baseweb="tab"]:hover:not([aria-selected="true"]),
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]) {
  color: #2563eb !important;
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"],
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"],
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  color: #2563eb !important;
  font-weight: 700 !important;
  border: none !important;
  border-bottom: 2px solid #2563eb !important;
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] button[data-baseweb="tab"] p,
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] button[data-baseweb="tab"] span,
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [data-baseweb="tab"] p,
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [role="tab"] p {
  color: inherit !important;
  font-weight: inherit !important;
  font-size: inherit !important;
  margin: 0 !important;
  white-space: nowrap !important;
}
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabContent"],
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [data-baseweb="tab-panel"]:not([hidden]),
section[data-testid="stMain"]:has(.ips-assets-main-tabs-anchor) [data-testid="stTabs"] [role="tabpanel"]:not([hidden]) {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-top: none !important;
  border-radius: 0 0 12px 12px !important;
  padding: 1rem 1.1rem !important;
  margin-top: 0 !important;
  box-shadow: none !important;
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
.st-key-assets_table_wrap,
.st-key-assets_table_wrap > [data-testid="stVerticalBlock"],
.st-key-assets_table_wrap [data-testid="stVerticalBlock"],
.st-key-assets_small_tools_table_wrap,
.st-key-assets_small_tools_table_wrap > [data-testid="stVerticalBlock"] {
  background: #ffffff !important;
}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"],
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"],
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-table-header-marker),
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-header),
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {
  background: #ffffff !important;
}
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row),
.st-key-assets_table_wrap [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] > [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row) {
  min-height: 76px !important;
  border-bottom: 1px solid #e5eaf2 !important;
  transition: background-color 0.15s ease !important;
  position: relative !important;
  background: #ffffff !important;
  cursor: pointer !important;
}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-row-even),
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-row-odd) {
  background: #ffffff !important;
}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row):hover {
  background: #f8fafc !important;
}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row) > [data-testid="column"]:has(.asset-actions-cell),
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row) > [data-testid="column"]:has(.asset-actions-button),
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row) > [data-testid="column"]:has([data-testid="stCheckbox"]),
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row) > [data-testid="column"]:has([data-testid="stPopover"]) {
  position: relative !important;
  z-index: 4 !important;
}
.ips-assets-summary-cards {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0 0 1rem 0;
}
.ips-assets-stat-card {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.85rem 1rem;
  min-height: 72px;
  border-left-width: 4px;
  border-left-style: solid;
}
.ips-assets-stat-label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  margin: 0 0 0.35rem 0;
}
.ips-assets-stat-value {
  font-size: 1.5rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.ips-assets-stat-pct {
  font-size: 0.75rem;
  font-weight: 700;
  color: #64748b;
  margin: 0.2rem 0 0 0;
  font-variant-numeric: tabular-nums;
}
.ips-assets-stat-total {
  border-left-color: #1e3a8a;
}
.ips-assets-stat-total .ips-assets-stat-value { color: #1e3a8a; }
.ips-assets-stat-available {
  border-left-color: #15803d;
}
.ips-assets-stat-available .ips-assets-stat-value { color: #15803d; }
.ips-assets-stat-checked-out {
  border-left-color: #2563eb;
}
.ips-assets-stat-checked-out .ips-assets-stat-value { color: #2563eb; }
.ips-assets-stat-repair {
  border-left-color: #ea580c;
}
.ips-assets-stat-repair .ips-assets-stat-value { color: #ea580c; }
.ips-assets-stat-service {
  border-left-color: #dc2626;
}
.ips-assets-stat-service .ips-assets-stat-value { color: #dc2626; }
.ips-assets-stat-available .ips-assets-stat-pct { color: #15803d; }
.ips-assets-stat-checked-out .ips-assets-stat-pct { color: #2563eb; }
.ips-assets-stat-repair .ips-assets-stat-pct { color: #ea580c; }
.ips-assets-stat-service .ips-assets-stat-pct { color: #dc2626; }
.ips-assets-page-size-wrap {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.35rem;
  margin-bottom: 0.65rem;
}
section[data-testid="stMain"]:has(.ips-assets-page) [data-testid="column"]:has(.ips-assets-page-size-marker) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 0.35rem !important;
  margin-bottom: 0.65rem !important;
}
section[data-testid="stMain"]:has(.ips-assets-page) [data-testid="column"]:has(.ips-assets-page-size-marker) [data-testid="stSelectbox"] {
  max-width: 5.5rem;
}
section[data-testid="stMain"]:has(.ips-assets-page) [data-testid="column"]:has(.ips-assets-page-size-marker) [data-testid="stSelectbox"] > div > div {
  min-height: 34px !important;
  border-radius: 8px !important;
  border: 1px solid #dbe3ef !important;
  background: #ffffff !important;
  font-size: 0.8125rem !important;
  font-weight: 600 !important;
}
.ips-assets-show-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #475569;
  white-space: nowrap;
}
.st-key-assets_table_wrap .ips-asset-thumb-cell,
.st-key-assets_table_wrap .ips-asset-thumb-img,
.st-key-assets_table_wrap .ips-asset-thumb-placeholder {
  width: 60px !important;
  height: 60px !important;
  min-width: 60px !important;
  min-height: 60px !important;
}
.st-key-assets_table_wrap .ips-asset-thumb-img {
  object-fit: cover;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
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
.ips-asset-rental-badge,
.ips-asset-rentable-badge {
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
.ips-assets-name-text,
.asset-name-link.ips-assets-name-text,
a.asset-name-link {
  font-weight: 600 !important;
  color: #2563eb !important;
  font-size: 0.875rem;
  line-height: 1.25;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
  max-width: 100%;
  text-decoration: none;
}
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row):hover .ips-assets-name-text,
.st-key-assets_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-assets-equipment-table-row):hover a.asset-name-link {
  color: #1d4ed8 !important;
  text-decoration: underline;
}
a.asset-name-link:hover,
a.asset-name-link:focus {
  color: #1d4ed8 !important;
  text-decoration: underline;
}
.ips-asset-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 30px;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
  letter-spacing: 0.02em;
  border: 1px solid transparent;
}
.ips-asset-status-green {
  background: #bbf7d0;
  color: #14532d;
  border-color: #86efac;
}
.ips-asset-status-orange {
  background: #fed7aa;
  color: #7c2d12;
  border-color: #fdba74;
}
.ips-asset-status-blue {
  background: #bfdbfe;
  color: #1e3a8a;
  border-color: #93c5fd;
}
.ips-asset-status-red {
  background: #fecaca;
  color: #7f1d1d;
  border-color: #fca5a5;
}
.ips-asset-status-neutral {
  background: #e2e8f0;
  color: #334155;
  border-color: #cbd5e1;
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
section[data-testid="stMain"]:has(.ips-assets-page) .asset-actions-button {
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
    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore

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
      "button, input, select, textarea, label, a, [data-testid='stButton'], [data-testid='stPopover'], [data-testid='stCheckbox'], .asset-actions-cell, .asset-actions-button"
    ));
  }

  function tableScope() {
    const anchor = doc.querySelector(tblSel);
    if (!anchor) return null;
    return anchor.closest('[data-testid="stVerticalBlockBorderWrapper"]') || anchor.parentElement;
  }

  function bindNameLinks() {
    const scope = tableScope();
    if (!scope) return;
    scope.querySelectorAll(".asset-name-link[data-row-id]").forEach(function (link) {
      if (link.dataset.ipsAssetsNameBound === "1") return;
      link.dataset.ipsAssetsNameBound = "1";
      link.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        const id = link.getAttribute("data-row-id");
        if (id) sendValue(id);
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
    bindNameLinks();
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
    try:
        from app.components.table_pagination import DEFAULT_CATALOG_PAGE_SIZE
    except ImportError:
        from components.table_pagination import DEFAULT_CATALOG_PAGE_SIZE  # type: ignore

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
