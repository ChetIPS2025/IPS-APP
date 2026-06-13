"""Reusable job cost summary cards for Job Details and list views."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st


def _money(v: float) -> str:
    return f"${float(v or 0):,.2f}"


def _pct(v: float) -> str:
    return f"{float(v or 0):,.1f}%"


def render_job_cost_summary_cards(summary: dict[str, Any], *, compact: bool = False) -> None:
    """Top summary strip: Contract, Estimate, Actual, Remaining, Profit, Margin %."""
    st.markdown(
        '<span class="ips-job-cost-summary-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    profit = float(summary.get("profit") or 0)
    remaining = float(summary.get("remaining_budget") or 0)
    profit_cls = "ips-jc-card-profit" if profit >= 0 else "ips-jc-card-negative"
    remaining_cls = "ips-jc-card-remaining" if remaining >= 0 else "ips-jc-card-negative"
    cards = [
        ("Contract Value", _money(summary.get("contract_value", 0)), "ips-jc-card-contract"),
        ("Estimated Cost", _money(summary.get("estimated_cost", 0)), "ips-jc-card-estimate"),
        ("Actual Cost", _money(summary.get("actual_cost", 0)), "ips-jc-card-actual"),
        ("Remaining Budget", _money(summary.get("remaining_budget", 0)), remaining_cls),
        ("Profit", _money(summary.get("profit", 0)), profit_cls),
        ("Margin %", _pct(summary.get("margin_pct", 0)), "ips-jc-card-margin" if profit >= 0 else "ips-jc-card-negative"),
    ]
    if compact:
        cols = st.columns(len(cards), gap="small")
        for col, (label, value, cls) in zip(cols, cards):
            with col:
                st.markdown(
                    f'<div class="ips-jc-summary-card ips-jc-summary-compact {cls}">'
                    f'<div class="ips-jc-summary-label">{html.escape(label)}</div>'
                    f'<div class="ips-jc-summary-value">{html.escape(value)}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        return
    cols = st.columns(len(cards), gap="medium")
    for col, (label, value, cls) in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="ips-jc-summary-card {cls}">'
                f'<div class="ips-jc-summary-label">{html.escape(label)}</div>'
                f'<div class="ips-jc-summary-value">{html.escape(value)}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


def render_job_cost_detail_metrics(summary: dict[str, Any]) -> None:
    """Extended metrics row for Job Costing tab."""
    rows = [
        ("Estimated Cost", _money(summary.get("estimated_cost", 0))),
        ("Actual Cost", _money(summary.get("actual_cost", 0))),
        ("Remaining Budget", _money(summary.get("remaining_budget", 0))),
        ("Projected Final Cost", _money(summary.get("projected_final_cost", 0))),
        ("Variance", _money(summary.get("variance", 0))),
        ("Margin %", _pct(summary.get("margin_pct", 0))),
    ]
    c1, c2, c3 = st.columns(3)
    for i, (label, value) in enumerate(rows):
        col = (c1, c2, c3)[i % 3]
        with col:
            st.markdown(
                f'<div class="ips-jc-metric-row">'
                f'<span class="ips-jc-metric-label">{html.escape(label)}</span>'
                f'<span class="ips-jc-metric-value">{html.escape(value)}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
    st.markdown(
        '<div class="ips-jc-category-breakdown-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    b1, b2, b3, b4 = st.columns(4)
    breakdown = [
        (b1, "Labor Cost", summary.get("labor_cost", 0)),
        (b2, "Material Cost", summary.get("material_cost", 0)),
        (b3, "Equipment Cost", summary.get("equipment_cost", 0)),
        (b4, "Subcontract Cost", summary.get("subcontract_cost", 0)),
    ]
    for col, label, amt in breakdown:
        with col:
            st.metric(label, _money(amt))
