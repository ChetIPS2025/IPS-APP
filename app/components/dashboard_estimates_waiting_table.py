"""Estimates Waiting Approval table for the operations dashboard (UI only)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.estimates_list_table import (
    build_approve_flags,
    build_estimates_html_table,
    filter_waiting_approval_rows,
    render_estimates_table_bridge,
)
_EST_WAITING_LAST_KEY = "_ips_dash_est_waiting_last"


def render_dashboard_estimates_waiting_table(
    estimates: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> None:
    """Render estimates waiting approval above Active Jobs on the dashboard."""
    waiting = filter_waiting_approval_rows(list(estimates))[: max(1, int(limit))]
    approve_flags = build_approve_flags(waiting)
    estimates_by_id = {
        str(est.get("id") or "").strip(): est
        for est in waiting
        if str(est.get("id") or "").strip()
    }

    with st.container(key="dashboard_estimates_waiting_table"):
        hdr_l, hdr_r = st.columns([4, 1], gap="small", vertical_alignment="center")
        with hdr_l:
            st.markdown(
                '<div class="ips-dash-est-waiting-head">'
                '<p class="ips-ops-section-title ips-dash-est-waiting-title">Estimates Waiting Approval</p>'
                '<p class="ips-dash-est-waiting-subtitle">Estimates that need review before approval</p>'
                "</div>",
                unsafe_allow_html=True,
            )
        with hdr_r:
            if st.button("View All", key="ips_dash_est_waiting_all", use_container_width=True):
                st.session_state["estimates_view"] = "Waiting Approval"
                from app.navigation import set_nav_slug
                set_nav_slug("estimates")
                st.rerun()

        if not waiting:
            st.markdown(
                '<p class="ips-dash-est-waiting-empty">No estimates waiting approval.</p>',
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            build_estimates_html_table(waiting, approve_flags=approve_flags),
            unsafe_allow_html=True,
        )
        render_estimates_table_bridge(
            estimates_by_id,
            component_key="ips_dash_est_waiting_bridge",
            hook_key="ipsDashEstWaiting::action",
            last_action_key=_EST_WAITING_LAST_KEY,
        )
