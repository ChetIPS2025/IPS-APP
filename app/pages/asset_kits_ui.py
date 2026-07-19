"""Asset Kit / Tool Trailer UI — public compatibility entry points."""

from __future__ import annotations

import html

import streamlit as st

from app.components.asset_kit.fragment import render_kit_contents_fragment, render_kit_contents_tab
from app.components.asset_kit.mobile import render_mobile_kit_scan
from app.components.asset_kit.styles import inject_kit_ui_styles, kit_badge_html, kit_item_status_pill_html
from app.services.asset_kits_service import (
    get_missing_tools_report,
    get_overdue_kit_audits,
    get_tool_trailers,
)
from app.utils.formatting import fmt_currency


def render_kit_accountability_summary() -> None:
    """Report cards on Assets page — supervisor accountability (on-demand)."""
    from app.pages._core.page_data_cache import page_data_cache_get

    inject_kit_ui_styles()

    def _load_summary() -> dict:
        trailers = get_tool_trailers()
        missing_rows = get_missing_tools_report()
        overdue = get_overdue_kit_audits(days=30)
        total_val = sum(float(a.get("total_kit_value") or a.get("value") or 0) for a in trailers)
        missing_val = sum(float(r.get("missing_value") or 0) for r in missing_rows)
        damaged_val = sum(float(r.get("damaged_value") or 0) for r in missing_rows)
        return {
            "trailers": trailers,
            "missing_rows": missing_rows,
            "overdue": overdue,
            "total_val": total_val,
            "missing_val": missing_val,
            "damaged_val": damaged_val,
        }

    data = page_data_cache_get("kit_accountability_summary", _load_summary)
    trailers = data["trailers"]
    if not trailers:
        return

    c_refresh, _ = st.columns([1, 4])
    with c_refresh:
        if st.button("Refresh kit summary", key="ast_kit_summary_refresh"):
            from app.pages._core.page_data_cache import clear_page_data_cache_key

            clear_page_data_cache_key("kit_accountability_summary")
            st.rerun()

    missing_rows = data["missing_rows"]
    overdue = data["overdue"]

    st.markdown("#### Tool Trailers & Kits")
    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    c1.metric("Kits / Trailers", len(trailers))
    c2.metric("Total Kit Value", fmt_currency(data["total_val"]))
    c3.metric("Missing Tools Value", fmt_currency(data["missing_val"]))
    c4.metric("Damaged Value", fmt_currency(data["damaged_val"]))
    c5.metric("Audit Overdue", len(overdue))

    if missing_rows:
        with st.expander("Missing / damaged by supervisor", expanded=False):
            for row in missing_rows[:15]:
                st.markdown(
                    f"**{html.escape(str(row.get('asset_name') or '—'))}** · "
                    f"Supervisor: {html.escape(str(row.get('supervisor') or '—'))} · "
                    f"Missing: {fmt_currency(row.get('missing_value'))} · "
                    f"Damaged: {fmt_currency(row.get('damaged_value'))}"
                )


__all__ = [
    "inject_kit_ui_styles",
    "kit_badge_html",
    "kit_item_status_pill_html",
    "render_kit_accountability_summary",
    "render_kit_contents_fragment",
    "render_kit_contents_tab",
    "render_mobile_kit_scan",
]
