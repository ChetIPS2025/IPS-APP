"""Labor rates admin page (delegates to shared panel)."""

from __future__ import annotations

import streamlit as st

try:
    from app.components.labor_rates_panel import render_labor_rates_panel
except ImportError:
    from components.labor_rates_panel import render_labor_rates_panel  # type: ignore


def _migrate_legacy_labor_session() -> None:
    if st.session_state.get("labor_edit_id"):
        st.session_state["labor_panel_mode"] = "edit"
        st.session_state["labor_panel_id"] = st.session_state.pop("labor_edit_id")
    if st.session_state.get("labor_view_id"):
        st.session_state["labor_panel_mode"] = "view"
        st.session_state["labor_panel_id"] = st.session_state.pop("labor_view_id")


def render() -> None:
    _migrate_legacy_labor_session()
    render_labor_rates_panel(key_prefix="labor", show_header=True)
