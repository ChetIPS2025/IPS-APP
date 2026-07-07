"""Filter bar layout helper."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st


def render_filter_bar(widgets_fn: Callable[[], None]) -> None:
    """Compact white card filter row with search + dropdowns."""
    with st.container(border=True):
        st.markdown('<span class="ips-filter-bar-marker" aria-hidden="true"></span>', unsafe_allow_html=True)
        widgets_fn()
