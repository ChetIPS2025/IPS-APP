"""Cards, KPIs, and action bars."""

from __future__ import annotations

import html
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import streamlit as st

try:
    from app.ui.components.headers import render_section_header
    from app.ui.page_shell import action_bar_card as _action_bar_card
    from app.ui.page_shell import render_card as _render_card
except ImportError:
    from ui.components.headers import render_section_header  # type: ignore
    from ui.page_shell import action_bar_card as _action_bar_card  # type: ignore
    from ui.page_shell import render_card as _render_card  # type: ignore


@contextmanager
def render_card(
    *,
    title: str | None = None,
    subtitle: str | None = None,
    bordered: bool = False,
) -> Iterator[None]:
    with _render_card(title=title, subtitle=subtitle, bordered=bordered):
        yield


@contextmanager
def action_bar_card(*, title: str | None = "Quick Actions") -> Iterator[None]:
    with _action_bar_card(title=title):
        yield


def render_kpi_card(
    label: str,
    value: str | int,
    *,
    sub: str | None = None,
    clickable: bool = False,
    key: str | None = None,
    on_click: Callable[[], None] | None = None,
) -> bool:
    """Render one KPI tile. Returns True if clicked (when clickable)."""
    lbl = html.escape(str(label))
    val = html.escape(str(value))
    sub_html = f'<p class="ips-kpi-sub">{html.escape(sub)}</p>' if sub else ""
    cls = "ips-kpi-card ips-kpi-clickable" if clickable else "ips-kpi-card"
    st.markdown(
        f'<div class="{cls}"><div class="ips-kpi-label">{lbl}</div>'
        f'<div class="ips-kpi-value">{val}</div>{sub_html}</div>',
        unsafe_allow_html=True,
    )
    if clickable and key and on_click:
        if st.button("Open", key=key, type="secondary", use_container_width=True):
            on_click()
            return True
    return False


def render_kpi_grid(specs: list[dict[str, Any]], *, columns: int = 5) -> None:
    """
    KPI row using Streamlit metrics (accessible) with shared styling.

    Each spec: ``label``, ``value``, optional ``delta``, ``help``, ``nav_page`` (sets pending nav on click).
    """
    if not specs:
        return
    st.markdown('<span class="ips-kpi-grid-anchor ips-flat-section" aria-hidden="true"></span>', unsafe_allow_html=True)
    n = max(1, min(columns, len(specs)))
    cols = st.columns(n, gap="small")
    try:
        from app.ui import IPS_NAV_PENDING_KEY
    except ImportError:
        from ui import IPS_NAV_PENDING_KEY  # type: ignore

    nav_queue: list[str] = []
    for i, spec in enumerate(specs):
        with cols[i % n]:
            label = str(spec.get("label", ""))
            val = spec.get("value", "—")
            help_txt = spec.get("help")
            delta = spec.get("delta")
            nav = spec.get("nav_page")
            hint = f"Open {nav}" if nav else help_txt
            st.metric(label, val, delta=delta, help=hint)
            if nav and st.button("→", key=f"ips_kpi_nav_{spec.get('key', i)}", help=f"Go to {nav}"):
                nav_queue.append(str(nav))
    if nav_queue:
        st.session_state[IPS_NAV_PENDING_KEY] = nav_queue[-1]
        st.rerun()
