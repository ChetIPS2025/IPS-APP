from __future__ import annotations

from collections.abc import Callable

import streamlit as st


def render_side_detail_panel(*, title: str, body: Callable[[], None]) -> None:
    with st.container(border=True):
        st.markdown('<span class="ips-crud-side-anchor"></span>', unsafe_allow_html=True)
        st.markdown(f"### {title}")
        body()
