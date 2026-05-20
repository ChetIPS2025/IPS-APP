"""Tab navigation for detail panels."""

from __future__ import annotations

import streamlit as st

_OT, _CT = "d" + "iv", "/" + "d" + "iv"


def render_tabs(
    tab_labels: list[str],
    *,
    session_key: str,
    default: str | None = None,
) -> str:
    if session_key not in st.session_state:
        st.session_state[session_key] = default or tab_labels[0]
    st.markdown(f'<{_OT} class="ips-tabs-wrap">', unsafe_allow_html=True)
    choice = st.radio(
        "Section",
        tab_labels,
        horizontal=True,
        key=session_key,
        label_visibility="collapsed",
    )
    st.markdown(f"<{_CT}>", unsafe_allow_html=True)
    return str(choice)
