"""Clickable list tables — row selection opens detail modal (no Select buttons)."""

from __future__ import annotations

import html
from typing import Any, Callable

import pandas as pd
import streamlit as st

PlainCellFn = Callable[[str, dict[str, Any]], str]


def _selection_rows(state_key: str) -> list[int]:
    raw = st.session_state.get(state_key)
    if raw is None:
        return []
    if hasattr(raw, "selection") and raw.selection is not None:
        return list(raw.selection.rows or [])
    if isinstance(raw, dict):
        sel = raw.get("selection") or {}
        if isinstance(sel, dict):
            return list(sel.get("rows") or [])
    return []


def _plain_value(
    field: str,
    row: dict[str, Any],
    *,
    plain_cell: PlainCellFn | None,
    html_cell: Callable[[str, dict[str, Any]], str] | None,
) -> str:
    if plain_cell:
        return plain_cell(field, row)
    if html_cell:
        raw = html_cell(field, row)
        return html.unescape(str(raw).replace("<br>", " ").strip()) or "—"
    val = row.get(field)
    return str(val) if val is not None and str(val).strip() else "—"


def render_clickable_table(
    records: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    key: str,
    *,
    row_id_key: str = "id",
    session_select_key: str | None = None,
    selected_id: str | None = None,
    plain_cell: PlainCellFn | None = None,
    html_cell: Callable[[str, dict[str, Any]], str] | None = None,
    on_row_click: Callable[[str, dict[str, Any]], None] | None = None,
) -> str | None:
    """
    Native Streamlit table — click a row to select (no Select button, no checkboxes).

    Stores selected record id in ``session_select_key`` and returns it.
    """
    sel_key = session_select_key or key
    df_key = f"{key}_ips_df"

    if not records:
        st.caption("No records to display.")
        st.session_state.pop(sel_key, None)
        return None

    id_by_index: list[str] = []
    rows_out: list[dict[str, str]] = []
    for rec in records:
        rid = str(rec.get(row_id_key) or "")
        id_by_index.append(rid)
        row_display: dict[str, str] = {}
        for field, header in columns:
            row_display[header] = _plain_value(
                field, rec, plain_cell=plain_cell, html_cell=html_cell
            )
        rows_out.append(row_display)

    df = pd.DataFrame(rows_out)
    st.caption("Click a row to open details.")
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=df_key,
    )

    picked_idx: int | None = None
    for idx in _selection_rows(df_key):
        if 0 <= idx < len(id_by_index):
            picked_idx = idx
            break

    if picked_idx is not None:
        rid = id_by_index[picked_idx]
        if rid:
            st.session_state[sel_key] = rid
            if on_row_click:
                on_row_click(rid, records[picked_idx])

    active = str(st.session_state.get(sel_key) or selected_id or "").strip()
    if active and active not in id_by_index:
        st.session_state.pop(sel_key, None)
        return None
    return active or None


def render_data_table(
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    *,
    row_id_key: str,
    selected_id: str | None,
    session_select_key: str,
    col_fr: list[str] | None = None,
    cell_renderer: Callable[[str, dict[str, Any]], str] | None = None,
    hide_select: bool = False,
    use_native: bool = False,
    table_key: str | None = None,
    plain_cell: PlainCellFn | None = None,
) -> str | None:
    """
    List table helper.

    - ``use_native=True`` (main lists): ``render_clickable_table`` — row click only.
    - ``use_native=False`` (nested lists in modals): compact HTML grid, no Select buttons.
    """
    _ = col_fr, hide_select
    tkey = table_key or session_select_key
    if use_native:
        return render_clickable_table(
            rows,
            columns,
            tkey,
            row_id_key=row_id_key,
            session_select_key=session_select_key,
            selected_id=selected_id,
            plain_cell=plain_cell,
            html_cell=cell_renderer,
        )

    n = len(columns)
    grid = "grid-template-columns: " + " ".join(col_fr or ["1.1fr"] + ["1fr"] * max(n - 1, 0)) + ";"
    open_tag = "d" + "iv"
    close_tag = "/" + open_tag
    header = "".join(
        f"<{open_tag}>{html.escape(h)}<{close_tag}>" for _, h in columns
    )
    st.markdown(
        f'<{open_tag} class="ips-data-table-wrap ips-data-table-stable ips-data-table-nested">'
        f'<{open_tag} class="ips-data-table-scroll">'
        f'<{open_tag} class="ips-data-table-header" style="{grid}">{header}<{close_tag}>',
        unsafe_allow_html=True,
    )
    active_id = str(st.session_state.get(session_select_key) or selected_id or "")
    for row in rows:
        rid = str(row.get(row_id_key) or "")
        sel = " selected" if rid and rid == active_id else ""
        parts = []
        for field, _ in columns:
            if cell_renderer:
                parts.append(
                    f'<{open_tag} class="ips-data-cell">{cell_renderer(field, row)}<{close_tag}>'
                )
            else:
                parts.append(
                    f'<{open_tag} class="ips-data-cell">'
                    f"{html.escape(str(row.get(field) or chr(8212)))}"
                    f"<{close_tag}>"
                )
        st.markdown(
            f'<{open_tag} class="ips-data-row{sel}" style="{grid}">{"".join(parts)}<{close_tag}>',
            unsafe_allow_html=True,
        )
    st.markdown(f"<{close_tag}><{close_tag}>", unsafe_allow_html=True)
    sel = st.session_state.get(session_select_key) or selected_id
    return str(sel) if sel else None
