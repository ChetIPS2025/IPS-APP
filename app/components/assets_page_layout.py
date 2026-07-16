"""Assets list page — professional layout styling (UI only)."""

from __future__ import annotations

import html

import streamlit as st

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
    """Legacy full layout inject — prefer :func:`app.components.assets_css.inject_assets_page_css`."""
    from app.components.assets_css import (
        inject_assets_equipment_css,
        inject_assets_shell_css,
    )

    inject_assets_shell_css()
    inject_assets_equipment_css()


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
