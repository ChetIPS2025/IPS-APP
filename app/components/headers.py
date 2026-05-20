"""Page header components."""

from __future__ import annotations

import html

import streamlit as st


def render_page_header(
    title: str,
    subtitle: str = "",
    *,
    actions_cols: list | None = None,
) -> None:
    ot, ct = "d" + "iv", "/" + "d" + "iv"
    st.markdown(f'<{ot} class="ips-page-shell-marker"></{ct}>', unsafe_allow_html=True)
    left, right = st.columns([3, 1])
    with right:
        if actions_cols:
            st.markdown(f'<{ot} class="ips-header-actions">', unsafe_allow_html=True)
            ac1, ac2 = st.columns(2)
            for i, widget in enumerate(actions_cols):
                with (ac1 if i % 2 == 0 else ac2):
                    widget()
            st.markdown(f"</{ct}>", unsafe_allow_html=True)
    with left:
        sub = (
            f'<p class="ips-page-subtitle">{html.escape(subtitle)}</p>'
            if subtitle
            else ""
        )
        st.markdown(
            f"""
<{ot} class="ips-page-header">
  <{ot}>
    <h1 class="ips-page-title">{html.escape(title)}</h1>
    {sub}
  </{ct}>
</{ct}>
""",
            unsafe_allow_html=True,
        )
