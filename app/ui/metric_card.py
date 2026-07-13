"""Shared IPS metric / KPI card components."""

from __future__ import annotations

import html

import streamlit as st

from app.components.cards import render_kpi_card as _legacy_kpi_card
from app.components.cards import render_ops_kpi_row as _legacy_ops_kpi_row
_TONE_ACCENTS = {
    "default": "#e2e8f0",
    "primary": "#3158e6",
    "success": "#16a34a",
    "warning": "#d97706",
    "danger": "#dc2626",
}


def render_metric_card(
    label: str,
    value: str,
    *,
    icon: str | None = None,
    delta: str | None = None,
    tone: str = "default",
    clickable: bool = False,
    icon_bg: str | None = None,
) -> None:
    """Render one compact KPI/metric card."""
    _ = clickable
    accent = _TONE_ACCENTS.get(str(tone or "default").strip().lower(), _TONE_ACCENTS["default"])
    bg = icon_bg or "#eef2ff"
    if icon:
        _legacy_kpi_card(
            label,
            value,
            icon,
            bg,
            trend=str(delta or ""),
            trend_class="up" if delta else "",
        )
        return

    delta_html = (
        f'<p class="ips-metric-card-delta">{html.escape(str(delta))}</p>'
        if str(delta or "").strip()
        else ""
    )
    st.markdown(
        f'<div class="ips-metric-card ips-metric-card-accent" style="border-left-color:{html.escape(accent)};">'
        f'<p class="ips-metric-card-label">{html.escape(str(label))}</p>'
        f'<p class="ips-metric-card-value">{html.escape(str(value))}</p>'
        f"{delta_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_metric_row(items: list[tuple[str, str, str, str]]) -> None:
    """
    Render a row of metric cards in one grid.

    Each item: (label, value, icon, icon_background_color).
    Preserves dashboard ops KPI layout.
    """
    _legacy_ops_kpi_row(items)


__all__ = ["render_metric_card", "render_metric_row"]
