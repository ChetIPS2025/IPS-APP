"""Card and metric components."""

from __future__ import annotations

import html

import streamlit as st


def _dashboard_metric_card_html(
    label: str,
    value: str,
    icon: str,
    icon_bg: str,
    *,
    card_class: str,
    icon_class: str,
    text_class: str,
    value_class: str,
    label_class: str,
    caption: str = "",
    title: str = "",
) -> str:
    ot = "d" + "iv"
    title_attr = f' title="{html.escape(title)}"' if title else ""
    caption_html = (
        f'<p class="dashboard-value-caption">{html.escape(caption)}</p>' if caption else ""
    )
    return (
        f'<{ot} class="{card_class}"{title_attr}>'
        f'<{ot} class="{icon_class}" style="background:{html.escape(icon_bg)}">{icon}</{ot}>'
        f'<{ot} class="{text_class}">'
        f'<p class="{value_class}">{html.escape(value)}</p>'
        f'<p class="{label_class}">{html.escape(label)}</p>'
        f"{caption_html}"
        f"</{ot}></{ot}>"
    )


def _ops_kpi_card_html(label: str, value: str, icon: str, icon_bg: str) -> str:
    return _dashboard_metric_card_html(
        label,
        value,
        icon,
        icon_bg,
        card_class="dashboard-kpi-card",
        icon_class="dashboard-kpi-icon-ring",
        text_class="dashboard-kpi-text",
        value_class="dashboard-kpi-value",
        label_class="dashboard-kpi-label",
    )


def _ops_value_card_html(
    label: str,
    value: str,
    icon: str,
    icon_bg: str,
    *,
    caption: str = "",
    title: str = "",
) -> str:
    return _dashboard_metric_card_html(
        label,
        value,
        icon,
        icon_bg,
        card_class="dashboard-value-card",
        icon_class="dashboard-value-icon-ring",
        text_class="dashboard-value-text",
        value_class="dashboard-value-amount",
        label_class="dashboard-value-label",
        caption=caption,
        title=title,
    )


def render_ops_kpi_grid(items: list[tuple[str, str, str, str]]) -> None:
    """Render primary operations KPI tiles in a responsive CSS grid."""
    ot = "d" + "iv"
    cards = "".join(_ops_kpi_card_html(label, value, icon, bg) for label, value, icon, bg in items)
    st.markdown(f'<{ot} class="dashboard-kpi-grid">{cards}</{ot}>', unsafe_allow_html=True)


def render_ops_value_grid(items: list[tuple[str, ...]]) -> None:
    """Render inventory/asset value tiles in their own row."""
    ot = "d" + "iv"
    cards = []
    for item in items:
        label, value, icon, bg = item[0], item[1], item[2], item[3]
        caption = item[4] if len(item) > 4 else ""
        title = item[5] if len(item) > 5 else ""
        cards.append(_ops_value_card_html(label, value, icon, bg, caption=caption, title=title))
    st.markdown(f'<{ot} class="dashboard-value-grid">{"".join(cards)}</{ot}>', unsafe_allow_html=True)


def render_ops_kpi_row(items: list[tuple[str, str, str, str]]) -> None:
    """Backward-compatible alias: first six KPIs plus value row when present."""
    primary = items[:6]
    value_items = items[6:8]
    if primary:
        render_ops_kpi_grid(primary)
    if value_items:
        render_ops_value_grid(value_items)


def render_kpi_card(
    label: str,
    value: str,
    icon: str,
    icon_bg: str,
    trend: str = "",
    trend_class: str = "up",
) -> None:
    ot = "d" + "iv"
    trend_html = ""
    if str(trend or "").strip():
        trend_html = (
            f'<p class="ips-kpi-trend {html.escape(trend_class)}">{html.escape(trend)}</p>'
        )
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
  {trend_html}
</{ot}>
""",
        unsafe_allow_html=True,
    )
