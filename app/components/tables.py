"""Selectable data table with row highlight."""

from __future__ import annotations

import html
from typing import Any, Callable

import streamlit as st


def render_data_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    *,
    row_id_key: str,
    selected_id: str | None,
    session_select_key: str,
    col_fr: list[str] | None = None,
    cell_renderer: Callable[[str, dict[str, Any]], str] | None = None,
) -> str | None:
    n = len(columns)
    if not col_fr:
        col_fr = ["1.1fr"] + ["1fr"] * max(n - 1, 0)
    grid = "grid-template-columns: " + " ".join(col_fr) + ";"
    open_tag = "d" + "iv"
    close_tag = "/" + open_tag
    header = "".join(
        f"<{open_tag}>{html.escape(h)}<{close_tag}>" for _, h in columns
    )
    st.markdown(
        f'<{open_tag} class="ips-data-table-wrap ips-data-table-stable">'
        f'<{open_tag} class="ips-data-table-scroll">'
        f'<{open_tag} class="ips-data-table-header" style="{grid}">{header}<{close_tag}>',
        unsafe_allow_html=True,
    )
    for row in rows:
        rid = str(row.get(row_id_key) or "")
        sel = " selected" if rid and rid == selected_id else ""
        parts = []
        for field, _ in columns:
            if cell_renderer:
                parts.append(f"<{open_tag}>{cell_renderer(field, row)}<{close_tag}>")
            else:
                parts.append(
                    f"<{open_tag}>{html.escape(str(row.get(field) or chr(8212)))}<{close_tag}>"
                )
        st.markdown(
            f'<{open_tag} class="ips-data-row{sel}" style="{grid}">{"".join(parts)}<{close_tag}>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<{open_tag} class="ips-row-select-btn">', unsafe_allow_html=True)
        if st.button("Select", key=f"sel_{session_select_key}_{rid}", type="secondary"):
            st.session_state[session_select_key] = rid
        st.markdown(f"<{close_tag}>", unsafe_allow_html=True)
    st.markdown(f"<{close_tag}><{close_tag}>", unsafe_allow_html=True)
    sel = st.session_state.get(session_select_key) or selected_id
    return str(sel) if sel else None
