"""Compact form helpers."""

from __future__ import annotations

import streamlit as st


def render_dropdown(
    label: str,
    options: list[str],
    *,
    key: str,
    default: str | None = None,
    allow_empty: bool = False,
) -> str:
    opts = list(options)
    if allow_empty:
        opts = [""] + opts
    idx = 0
    if default and default in opts:
        idx = opts.index(default)
    return str(st.selectbox(label, opts, index=idx, key=key))
