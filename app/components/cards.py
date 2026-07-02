"""Card and metric components."""

from __future__ import annotations

import html

import streamlit as st


def render_panel_card(
    title: str,
    body_html: str = "",
    *,
    subtitle: str = "",
    compact: bool = False,
    extra_class: str = "",
) -> None:
    """Dashboard panel — title and body in one HTML block so Streamlit keeps content inside the card."""
    cls = "ips-panel-card ips-panel-card-compact" if compact else "ips-panel-card"
    if extra_class.strip():
        cls = f"{cls} {extra_class.strip()}"
    ot = "d" + "iv"
    subtitle_html = (
        f'<p class="ips-panel-subtitle">{html.escape(subtitle)}</p>'
        if str(subtitle or "").strip()
        else ""
    )
    st.markdown(
        f'<{ot} class="{html.escape(cls)}">'
        f'<p class="ips-panel-title">{html.escape(title)}</p>'
        f"{subtitle_html}"
        f"{body_html}"
        f"</{ot}>",
        unsafe_allow_html=True,
    )


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


def render_ops_kpi_card(label: str, value: str, icon: str, icon_bg: str) -> None:
    """Compact operations KPI tile — icon ring, bold value, small label (~80–90px)."""
    ot = "d" + "iv"
    st.markdown(
        f"""
<{ot} class="ips-ops-kpi-card">
  <{ot} class="ips-ops-kpi-icon-ring" style="background:{icon_bg}">{icon}</{ot}>
  <{ot} class="ips-ops-kpi-text">
    <p class="ips-ops-kpi-value">{html.escape(value)}</p>
    <p class="ips-ops-kpi-label">{html.escape(label)}</p>
  </{ot}>
</{ot}>
""",
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
