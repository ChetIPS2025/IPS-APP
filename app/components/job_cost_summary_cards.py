"""Reusable job cost summary cards for Job Details and list views."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st


def _money(v: float, *, available: bool = True) -> str:
    if not available or abs(float(v or 0)) < 0.005:
        return "—"
    return f"${float(v):,.2f}"


def _pct(v: float, *, available: bool = True) -> str:
    if not available:
        return "—"
    return f"{float(v or 0):,.1f}%"


def render_job_cost_summary_cards(summary: dict[str, Any], *, compact: bool = False) -> None:
    """Top summary strip: Contract, Estimate, Actual, Remaining, Profit, Margin %."""
    st.markdown(
        '<span class="ips-job-cost-summary-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    has_contract = bool(summary.get("has_contract_value"))
    has_estimated = bool(summary.get("has_estimated_cost"))
    has_actual = int(summary.get("transaction_count") or 0) > 0 or float(summary.get("actual_cost") or 0) > 0
    profit = float(summary.get("profit") or 0)
    remaining_raw = summary.get("remaining_budget")
    remaining = float(remaining_raw or 0) if remaining_raw is not None else 0.0
    profit_cls = "ips-jc-card-negative" if profit < 0 else "ips-jc-card-profit"
    remaining_available = has_contract or has_estimated
    remaining_cls = "ips-jc-card-remaining" if (remaining_available and remaining >= 0) else "ips-jc-card-negative"
    margin_available = has_contract
    cards = [
        ("Contract Value", _money(summary.get("contract_value", 0), available=has_contract), "ips-jc-card-contract"),
        ("Estimated Cost", _money(summary.get("estimated_cost", 0), available=has_estimated), "ips-jc-card-estimate"),
        ("Actual Cost", _money(summary.get("actual_cost", 0), available=has_actual), "ips-jc-card-actual"),
        (
            "Remaining Budget",
            _money(remaining, available=remaining_available),
            remaining_cls if remaining_available else "ips-jc-card-neutral",
        ),
        (
            "Profit",
            _money(profit, available=has_contract or has_actual),
            profit_cls if (has_contract or has_actual) else "ips-jc-card-neutral",
        ),
        (
            "Margin %",
            _pct(summary.get("margin_pct", 0), available=margin_available),
            "ips-jc-card-margin" if profit >= 0 and margin_available else "ips-jc-card-negative",
        ),
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
    has_estimated = bool(summary.get("has_estimated_cost"))
    has_actual = int(summary.get("transaction_count") or 0) > 0
    rows = [
        ("Estimated Cost", _money(summary.get("estimated_cost", 0), available=has_estimated)),
        ("Actual Cost", _money(summary.get("actual_cost", 0), available=has_actual)),
        ("Remaining Budget", _money(summary.get("remaining_budget", 0), available=has_estimated)),
        ("Projected Final Cost", _money(summary.get("projected_final_cost", 0), available=has_actual or has_estimated)),
        ("Variance", _money(summary.get("variance", 0), available=has_estimated)),
        (
            "Margin %",
            _pct(summary.get("margin_pct", 0), available=bool(summary.get("has_contract_value"))),
        ),
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


def render_job_cost_breakdown(summary: dict[str, Any]) -> None:
    """Category breakdown: Labor, Materials, Equipment/Rental, Subcontract, Other."""
    st.markdown(
        '<div class="ips-jc-category-breakdown-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown("**Cost breakdown**")
    equip_rental = float(summary.get("equipment_cost") or 0) + float(summary.get("rental_cost") or 0)
    b1, b2, b3, b4, b5 = st.columns(5)
    breakdown = [
        (b1, "Labor", summary.get("labor_cost", 0)),
        (b2, "Materials", summary.get("material_cost", 0)),
        (b3, "Equipment / Rental", equip_rental),
        (b4, "Subcontract", summary.get("subcontract_cost", 0)),
        (b5, "Other", summary.get("other_cost", 0)),
    ]
    has_data = int(summary.get("transaction_count") or 0) > 0
    for col, label, amt in breakdown:
        with col:
            amt_f = float(amt or 0)
            if not has_data:
                display = "—"
            elif amt_f > 0:
                display = f"${amt_f:,.2f}"
            else:
                display = "$0.00"
            st.metric(label, display)
