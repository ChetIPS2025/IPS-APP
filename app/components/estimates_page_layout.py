"""Estimates list page — filter bar shell and summary cards (UI only)."""

from __future__ import annotations

import html

import streamlit as st


def _money(value: float) -> str:
    return f"${float(value or 0):,.2f}"


def _summary_money(value: float, *, has_data: bool) -> str:
    if not has_data:
        return "—"
    if abs(float(value or 0)) < 0.005:
        return "—"
    return _money(value)


def inject_estimates_page_layout_css() -> None:
    st.markdown(
        """
<style id="ips-estimates-page-layout-v1">
section[data-testid="stMain"]:has(.ips-estimates-page) {
  background: #ffffff !important;
}
.ips-estimates-filter-bar-wrap {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  margin-bottom: 0.85rem;
}
section[data-testid="stMain"]:has(.ips-estimates-page) .ips-estimates-filter-bar-wrap [data-testid="stTextInput"] input,
section[data-testid="stMain"]:has(.ips-estimates-page) .ips-estimates-filter-bar-wrap [data-testid="stSelectbox"] > div > div {
  background: #ffffff !important;
  border: 1px solid #dbe3ef !important;
  border-radius: 8px !important;
  min-height: 38px !important;
}
.ips-estimates-summary-cards {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 0 0 1rem 0;
}
@media (max-width: 1400px) {
  .ips-estimates-summary-cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 768px) {
  .ips-estimates-summary-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.ips-estimates-stat-card {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.75rem 0.9rem;
  min-height: 68px;
  border-left-width: 4px;
  border-left-style: solid;
}
.ips-estimates-stat-label {
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  margin: 0 0 0.3rem 0;
}
.ips-estimates-stat-value {
  font-size: 1.25rem;
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
        '<div class="ips-estimates-filter-bar-wrap"><span class="ips-est-filter-anchor" aria-hidden="true"></span>',
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
