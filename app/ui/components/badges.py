"""Status badges."""

from __future__ import annotations

import html

import streamlit as st

_TONES = frozenset({"neutral", "primary", "success", "warning", "danger"})


def render_badge(label: str, *, tone: str = "neutral") -> None:
    t = str(tone or "neutral").strip().lower()
    if t not in _TONES:
        t = "neutral"
    st.markdown(
        f'<span class="ips-badge ips-badge-{html.escape(t)}">{html.escape(str(label))}</span>',
        unsafe_allow_html=True,
    )
