"""Loading placeholders."""

from __future__ import annotations

import streamlit as st


def render_skeleton_rows(n: int = 5) -> None:
    n = max(1, min(int(n), 12))
    parts = "".join('<div class="ips-skeleton-row"></div>' for _ in range(n))
    st.markdown(parts, unsafe_allow_html=True)


def render_table_skeleton(*, rows: int = 6) -> None:
    st.markdown('<span class="ips-table-surface" aria-hidden="true"></span>', unsafe_allow_html=True)
    render_skeleton_rows(rows)
