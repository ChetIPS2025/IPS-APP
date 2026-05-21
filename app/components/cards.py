"""Card and metric components."""

from __future__ import annotations

import html

import streamlit as st


def render_card(title: str = "", body_html: str = "") -> None:
    title_html = (
        f"<h4 style='margin:0 0 0.5rem;font-size:0.95rem;'>{html.escape(title)}</h4>"
        if title
        else ""
    )
    ot = "d" + "iv"
    st.markdown(
        f'<{ot} class="ips-card">{title_html}{body_html}</{ot}>',
        unsafe_allow_html=True,
    )


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


def render_metric_card(label: str, value: str, *, delta: str = "") -> None:
    delta_html = (
        f"<p style='margin:0.15rem 0 0;font-size:0.75rem;color:#64748b;'>{html.escape(delta)}</p>"
        if delta
        else ""
    )
    ot = "d" + "iv"
    st.markdown(
        f"""
<{ot} class="ips-metric-card">
  <p class="ips-metric-label">{html.escape(label)}</p>
  <p class="ips-metric-value">{html.escape(value)}</p>
  {delta_html}
</{ot}>
""",
        unsafe_allow_html=True,
    )
