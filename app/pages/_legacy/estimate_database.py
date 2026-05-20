from __future__ import annotations

import streamlit as st

from ui import IPS_NAV_PENDING_KEY


def render() -> None:
    """Legacy entry: unified Estimates page replaced this listing."""
    st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
    st.rerun()
