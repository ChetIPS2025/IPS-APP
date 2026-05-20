"""Empty state placeholders."""

from __future__ import annotations

import html

import streamlit as st


def render_empty_state(title: str, message: str, *, icon: str = "📋") -> None:
    ot = "d" + "iv"
    st.markdown(
        f"""
<{ot} class="ips-empty-state">
  <{ot} style="font-size:2rem;">{html.escape(icon)}</{ot}>
  <h3>{html.escape(title)}</h3>
  <p>{html.escape(message)}</p>
</{ot}>
""",
        unsafe_allow_html=True,
    )
