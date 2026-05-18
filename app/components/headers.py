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
    with right:
        if actions_cols:
            for widget in actions_cols:
                widget()
