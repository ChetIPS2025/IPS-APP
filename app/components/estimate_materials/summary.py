"""Estimate Materials summary presentation (pure renderer)."""

from __future__ import annotations

import html

from app.services.estimate_materials_page_service import EstimateMaterialsSummary
from app.utils.formatting import fmt_currency


def render_materials_summary_panel(summary: EstimateMaterialsSummary, *, tax_label: str | None = None) -> None:
    rate = summary.tax_rate
    tax_lbl = tax_label or (f"Tax ({rate:g}%)" if rate else "Tax")
    lines = [
        ("Material cost", summary.material_cost),
        ("Material markup", summary.material_markup),
        ("Material customer price", summary.material_price),
        ("Taxable material subtotal", summary.taxable_material_subtotal),
        (tax_lbl, summary.material_tax),
    ]
    st = __import__("streamlit")
    st.markdown('<div class="ips-side-panel">', unsafe_allow_html=True)
    st.markdown("<h4>Materials Summary</h4>", unsafe_allow_html=True)
    for lbl, val in lines:
        st.markdown(
            f'<div class="ips-side-line"><span>{html.escape(lbl)}</span>'
            f"<span>{html.escape(fmt_currency(val))}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_materials_summary_breakdown(summary: EstimateMaterialsSummary, *, tax_label: str | None = None) -> None:
    rate = summary.tax_rate
    tax_lbl = tax_label or (f"Tax ({rate:g}%)" if rate else "Tax")
    import streamlit as st

    st.markdown('<div class="ips-panel-card">', unsafe_allow_html=True)
    st.markdown("**Full materials breakdown**")
    rows = [
        ("Material cost", summary.material_cost),
        ("Material markup", summary.material_markup),
        ("Material customer price", summary.material_price),
        ("Taxable material subtotal", summary.taxable_material_subtotal),
        (tax_lbl, summary.material_tax),
    ]
    for lbl, val in rows:
        st.markdown(f"**{html.escape(lbl)}:** {html.escape(fmt_currency(val))}")
    st.markdown("</div>", unsafe_allow_html=True)


__all__ = ["render_materials_summary_breakdown", "render_materials_summary_panel"]
