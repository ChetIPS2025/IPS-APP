"""Card and metric components."""

from __future__ import annotations

import html

import streamlit as st


def _ops_kpi_card_html(label: str, value: str, icon: str, icon_bg: str) -> str:
    ot = "d" + "iv"
    return (
        f'<{ot} class="ips-ops-kpi-card">'
        f'<{ot} class="ips-ops-kpi-icon-ring" style="background:{html.escape(icon_bg)}">{icon}</{ot}>'
        f'<{ot} class="ips-ops-kpi-text">'
        f'<p class="ips-ops-kpi-value">{html.escape(value)}</p>'
        f'<p class="ips-ops-kpi-label">{html.escape(label)}</p>'
        f"</{ot}></{ot}>"
    )


def render_ops_kpi_row(items: list[tuple[str, str, str, str]]) -> None:
    """Render all operations KPI tiles in one CSS grid (avoids Streamlit column width issues)."""
    ot = "d" + "iv"
    cards = "".join(_ops_kpi_card_html(label, value, icon, bg) for label, value, icon, bg in items)
    st.markdown(f'<{ot} class="ips-ops-kpi-grid">{cards}</{ot}>', unsafe_allow_html=True)


def render_kpi_card(
    label: str,
    value: str,
    icon: str,
    icon_bg: str,
    trend: str,
    trend_class: str = "up",
) -> None:
    ot = "d" + "iv"
    st.markdown(
        f"""
<{ot} class="ips-kpi-card">
  <{ot} class="ips-kpi-top">
    <{ot} class="ips-kpi-icon" style="background:{icon_bg}">{icon}</{ot}>
    <{ot}>
      <p class="ips-kpi-label">{html.escape(label)}</p>
      <p class="ips-kpi-value">{html.escape(value)}</p>
    </{ot}>
  </{ot}>
  <p class="ips-kpi-trend {html.escape(trend_class)}">{html.escape(trend)}</p>
</{ot}>
""",
        unsafe_allow_html=True,
    )
