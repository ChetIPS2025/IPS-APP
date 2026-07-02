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
<style id="ips-jobs-page-layout-v4">
section[data-testid="stMain"]:has(.ips-jobs-page) {
  background: #ffffff !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .block-container {
  background: #ffffff !important;
}
.ips-jobs-filter-bar-wrap {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  margin-bottom: 0.85rem;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .ips-jobs-filter-bar-wrap [data-testid="stTextInput"] input,
section[data-testid="stMain"]:has(.ips-jobs-page) .ips-jobs-filter-bar-wrap [data-testid="stSelectbox"] > div > div {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 8px !important;
  min-height: 38px !important;
}
.ips-jobs-table-wrap.jobs-table {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 12px;
  overflow: hidden;
}
.ips-jobs-summary-cards {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 0 0 1rem 0;
}
@media (max-width: 1400px) {
  .ips-jobs-summary-cards {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
.ips-jobs-stat-card {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.75rem 0.9rem;
  min-height: 68px;
  border-left-width: 4px;
  border-left-style: solid;
}
.ips-jobs-stat-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  margin: 0 0 0.3rem 0;
}
.ips-jobs-stat-value {
  font-size: 1.25rem;
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
section[data-testid="stMain"]:has(.ips-jobs-page) [data-testid="column"]:has(.ips-jobs-page-size-marker) > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 0.35rem !important;
  margin-bottom: 0.65rem !important;
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
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) {
  display: flex !important;
  align-items: center !important;
  min-height: 56px !important;
  padding: 5px 10px !important;
  background: #ffffff !important;
  border-bottom: 1px solid #e8edf4 !important;
  transition: background-color 0.15s ease !important;
  cursor: pointer;
}
@media (min-width: 768px) and (max-width: 1024px) {
  .st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) {
    min-height: 58px !important;
    padding: 6px 10px !important;
  }
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"] {
  display: flex !important;
  align-items: center !important;
  align-self: stretch !important;
  height: auto !important;
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
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:first-of-type {
  display: flex !important;
  align-items: center !important;
  background: #f8fafc !important;
  min-height: 36px !important;
  padding: 5px 10px !important;
  cursor: default !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover {
  background: #f8fbff !important;
}
.ips-jobs-table-row,
.ips-jobs-row-marker,
.job-row,
.jobs-table-row,
.job-checkbox-cell,
.ips-jobs-checkbox-cell,
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
.ips-jobs-number-text,
.job-number-link .ips-jobs-number-text {
  font-weight: 700 !important;
  color: #2563eb !important;
  font-size: 0.875rem;
  line-height: 1.25;
  cursor: pointer;
  white-space: nowrap;
  display: inline-block;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover .ips-jobs-number-text {
  color: #1d4ed8 !important;
  text-decoration: underline;
}
.st-key-jobs_table_wrap .ips-jobs-table-link [data-testid="stButton"],
.st-key-jobs_table_wrap .ips-jobs-table-link .stButton {
  width: 100%;
  min-width: 0;
  margin: 0;
}
.st-key-jobs_table_wrap .ips-jobs-table-link button,
.st-key-jobs_table_wrap .job-number-link button,
.st-key-jobs_table_wrap .ips-jobs-number-link button,
.st-key-jobs_table_wrap .ips-jobs-title-link button,
.st-key-jobs_table_wrap .job-project-link button {
  background: transparent !important;
  color: #2563eb !important;
  font-weight: 700 !important;
  font-size: 0.875rem !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  height: auto !important;
  min-height: 0 !important;
  justify-content: flex-start !important;
  text-align: left !important;
  width: auto !important;
  max-width: 100% !important;
}
.st-key-jobs_table_wrap .ips-jobs-number-link button,
.st-key-jobs_table_wrap .job-number-link button {
  white-space: nowrap !important;
}
.st-key-jobs_table_wrap .ips-jobs-title-link button,
.st-key-jobs_table_wrap .job-project-link button {
  white-space: normal !important;
  line-height: 1.3 !important;
  overflow-wrap: anywhere !important;
}
.st-key-jobs_table_wrap .ips-jobs-table-link button:hover,
.st-key-jobs_table_wrap .ips-jobs-table-link button:focus {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
  background: transparent !important;
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
.ips-jobs-title-text,
.job-project-text {
  font-weight: 700 !important;
  color: #2563eb !important;
  font-size: 0.875rem !important;
  word-break: normal !important;
  overflow-wrap: anywhere !important;
  white-space: normal !important;
  line-height: 1.3 !important;
  cursor: pointer !important;
}
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover .ips-jobs-title-text,
.st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row):hover .job-project-text {
  color: #1d4ed8 !important;
  text-decoration: underline !important;
}
.ips-jobs-cell,
.jobs-table-cell,
.job-cell {
  display: flex !important;
  align-items: center !important;
  height: 100% !important;
  min-height: 0 !important;
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
  justify-content: center !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-checkbox-cell),
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="stHorizontalBlock"]:has(.ips-jobs-table-row) > [data-testid="column"]:has([data-testid="stCheckbox"]) {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-status-cell),
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.ips-job-status-pill) {
  display: flex !important;
  align-items: center !important;
}
.ips-jobs-cell {
  color: #334155;
  font-size: 0.8125rem;
  line-height: 1.35;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-popover"] {
  min-width: 96px !important;
  min-height: 30px !important;
  height: 30px !important;
  padding: 0 0.75rem !important;
}
.ips-jobs-money-negative {
  color: #dc2626;
}
.ips-jobs-money-positive {
  color: #15803d;
}
.ips-jobs-money-empty {
  color: #94a3b8;
  font-weight: 500;
}
.ips-jobs-health-badge {
  display: inline-flex;
  align-items: center;
  min-height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  font-size: 0.625rem;
  font-weight: 700;
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
  min-height: 22px;
  height: 22px;
  padding: 0 10px;
  font-size: 0.6875rem;
  border: 1px solid transparent;
  line-height: 1;
}
.ips-job-status-draft {
  background: #e2e8f0;
  color: #334155;
  border-color: #cbd5e1;
}
.ips-job-status-active {
  background: #bfdbfe;
  color: #1e3a8a;
  border-color: #93c5fd;
}
.ips-job-status-awarded {
  background: #bbf7d0;
  color: #14532d;
  border-color: #86efac;
}
.ips-job-status-pending,
.ips-job-status-estimate-pending {
  background: #fef3c7;
  color: #92400e;
  border-color: #fcd34d;
}
.ips-job-status-on-hold {
  background: #e0e7ff;
  color: #3730a3;
  border-color: #c7d2fe;
}
.ips-job-status-completed,
.ips-job-status-closed {
  background: #166534;
  color: #ffffff;
  border-color: #14532d;
}
.ips-job-status-cancelled {
  background: #fed7aa;
  color: #9a3412;
  border-color: #fdba74;
}
section[data-testid="stMain"]:has(.ips-job-status-badge-editor-marker) [data-testid="stPopover"] > button {
  min-height: 28px !important;
  padding: 0 12px !important;
  border-radius: 999px !important;
  font-size: 0.75rem !important;
  font-weight: 700 !important;
  box-shadow: none !important;
}
section[data-testid="stMain"]:has(.ips-jobs-page) .st-key-jobs_table_wrap [data-testid="column"]:has(.job-actions-cell) button[data-testid="stBaseButton-popover"] {
  min-width: 96px !important;
  min-height: 30px !important;
  height: 30px !important;
  padding: 0 0.75rem !important;
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
        ("Active Jobs", f"{active:,}", "ips-jobs-stat-active"),
        ("On Hold", f"{on_hold:,}", "ips-jobs-stat-on-hold"),
        ("Completed", f"{completed:,}", "ips-jobs-stat-completed"),
        ("Cancelled", f"{cancelled:,}", "ips-jobs-stat-cancelled"),
        ("Open Subjobs", f"{open_subjobs:,}", "ips-jobs-stat-subjobs"),
        ("Total Contract Value", _summary_money(total_contract, has_data=has_contract_data), "ips-jobs-stat-contract"),
        ("Total Actual Cost", _summary_money(total_actual, has_data=has_actual_data), "ips-jobs-stat-actual"),
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
      "button, input, select, textarea, label, a, [data-testid='stButton'], [data-testid='stPopover'], [data-testid='stCheckbox'], .job-actions-cell, .job-actions-button, .job-row-actions-menu"
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
