"""Kit summary metric cards."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

from app.utils.formatting import fmt_currency


def render_kit_summary_cards(asset: dict, summary: dict[str, Any]) -> None:
    cards = [
        ("Total Kit Value", fmt_currency(summary.get("total_kit_value"))),
        ("Expected Items", str(summary.get("expected_items") or 0)),
        ("Present Items", str(summary.get("present_items") or 0)),
        ("Missing Items", str(summary.get("missing_items") or 0)),
        ("Damaged Items", str(summary.get("damaged_items") or 0)),
        ("Assigned Supervisor", str(summary.get("assigned_supervisor") or "—")),
        ("Last Audit", summary.get("last_audit") or "—"),
        ("Replacement Est.", fmt_currency(summary.get("replacement_cost"))),
    ]
    parts = ['<div class="ips-kit-summary-grid">']
    for label, val in cards:
        parts.append(
            f'<div class="ips-kit-metric"><div class="ips-kit-metric-label">{html.escape(label)}</div>'
            f'<div class="ips-kit-metric-value">{html.escape(str(val))}</div></div>'
        )
    parts.append("</div>")
    st.markdown("".join(parts), unsafe_allow_html=True)
    kt = str(asset.get("kit_type") or "").strip()
    if kt:
        st.caption(f"Kit type: **{kt}** · Status: **{asset.get('kit_status') or 'Active'}**")
