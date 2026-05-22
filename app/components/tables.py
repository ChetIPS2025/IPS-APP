"""Clickable list tables — row selection opens detail modal (no Select buttons)."""

from __future__ import annotations

import html
import re
from typing import Any, Callable

import streamlit as st

PlainCellFn = Callable[[str, dict[str, Any]], str]
HtmlCellFn = Callable[[str, dict[str, Any]], str]


def _cell_content(
    field: str,
    row: dict[str, Any],
    *,
    plain_cell: PlainCellFn | None,
    html_cell: HtmlCellFn | None,
) -> str:
    if html_cell:
        return str(html_cell(field, row))
    if plain_cell:
        return html.escape(plain_cell(field, row))
    val = row.get(field)
    return html.escape(str(val)) if val is not None and str(val).strip() else "—"


def _index_clickable_rows(
    records: list[dict[str, Any]],
    row_id_key: str,
) -> tuple[dict[str, dict[str, Any]], list[str], list[tuple[int, str, dict[str, Any]]]]:
    """
    Build row index for clickable tables.

    Returns ``(records_by_id, id_order, row_entries)`` where ``row_entries`` is
    ``(row_index, canonical_id, record)``. Canonical ids are stripped; the first
    record wins when ids collide after strip. ``row_index`` keeps Streamlit keys unique.
    """
    records_by_id: dict[str, dict[str, Any]] = {}
    id_order: list[str] = []
    row_entries: list[tuple[int, str, dict[str, Any]]] = []
    for idx, rec in enumerate(records):
        rid = str(rec.get(row_id_key) or "").strip()
        if not rid:
            continue
        row_entries.append((idx, rid, rec))
        if rid not in records_by_id:
            records_by_id[rid] = rec
            id_order.append(rid)
    return records_by_id, id_order, row_entries


def _row_label(row: dict[str, Any], columns: list[tuple[str, str]]) -> str:
    if not columns:
        return "row"
    field = columns[0][0]
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "row"


def render_clickable_table(
    records: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    key: str,
    *,
    row_id_key: str = "id",
    session_select_key: str | None = None,
    selected_id: str | None = None,
    plain_cell: PlainCellFn | None = None,
    html_cell: HtmlCellFn | None = None,
    on_row_click: Callable[[str, dict[str, Any]], None] | None = None,
    col_fr: list[str] | None = None,
    html_rows: bool | None = None,
) -> str | None:
    """
    HTML grid table — click anywhere on a row to select (invisible overlay button per row).

    Stores selected record id in ``session_select_key`` and returns it.

    When ``html_rows`` is False (default), each row gets an invisible Streamlit button overlay
    so clicks reliably open details. Set ``html_rows=True`` for read-only nested tables.
    """
    try:
        from app.ui.clean_table import (
            apply_clean_table_row_selection,
            render_clean_table_click_bridge,
        )
    except ImportError:
        from ui.clean_table import (  # type: ignore
            apply_clean_table_row_selection,
            render_clean_table_click_bridge,
        )

    # Table row CSS is injected globally via styles.inject_global_css()

    sel_key = session_select_key or key
    table_class = "ips-click-table-" + re.sub(r"[^a-zA-Z0-9_-]", "_", key)

    if not records:
        st.caption("No records to display.")
        st.session_state.pop(sel_key, None)
        return None

    records_by_id, id_order, row_entries = _index_clickable_rows(records, row_id_key)
    if len(row_entries) > len(id_order):
        st.caption(
            "Some rows share the same id after trimming whitespace; only the first is selectable."
        )

    active_id = str(st.session_state.get(sel_key) or selected_id or "").strip()
    if active_id and active_id not in id_order:
        st.session_state.pop(sel_key, None)
        active_id = ""

    n = len(columns)
    grid = "grid-template-columns: " + " ".join(
        col_fr or ["1.1fr"] + ["1fr"] * max(n - 1, 0)
    ) + ";"
    ot = "d" + "iv"
    ct = "/" + ot

    use_html_rows = False if html_rows is None else html_rows

    st.caption("Click a row to open details.")

    if use_html_rows:
        row_html_parts: list[str] = []
        for _row_idx, rid, rec in row_entries:
            sel = " selected" if rid and rid == active_id else ""
            rid_attr = html.escape(rid, quote=True)
            cells = "".join(
                f'<span class="ips-data-cell">{_cell_content(field, rec, plain_cell=plain_cell, html_cell=html_cell)}</span>'
                for field, _ in columns
            )
            row_html_parts.append(
                f'<{ot} class="ips-clean-row ips-data-row{sel}" style="{grid}" '
                f'data-row-id="{rid_attr}" role="button" tabindex="0">{cells}</{ot}>'
            )
        with st.container(border=True):
            st.markdown(
                f'<{ot} class="ips-data-table-wrap ips-data-table-stable ips-data-table-html">'
                f'<{ot} class="ips-data-table-scroll">'
                f'<span class="ips-clean-table ips-data-table-anchor {table_class}" aria-hidden="true"></span>'
                f'<{ot} class="ips-data-table-header ips-clean-header" style="{grid}">'
                + "".join(f"<span>{html.escape(h)}</span>" for _, h in columns)
                + f"</{ot}>"
                + "".join(row_html_parts)
                + f"</{ct}></{ct}>",
                unsafe_allow_html=True,
            )
        picked = render_clean_table_click_bridge(
            table_selector=f".{table_class}",
            row_selector=".ips-data-row[data-row-id]",
            component_key=f"{key}_row_click_bridge",
        )
        if picked:
            pid = str(picked).strip()
            if pid and pid in records_by_id:
                apply_clean_table_row_selection(
                    pid,
                    session_select_key=sel_key,
                    records_by_id=records_by_id,
                    on_row_click=on_row_click,
                )
                st.rerun()
    else:
        with st.container(border=True):
            st.markdown(
                f'<span class="ips-clean-table ips-data-table-anchor {table_class}" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<{ot} class="ips-data-table-wrap ips-data-table-stable ips-data-table-html ips-click-table-host">'
                f'<{ot} class="ips-data-table-scroll">'
                f'<{ot} class="ips-data-table-header ips-clean-header" style="{grid}">'
                + "".join(f"<span>{html.escape(h)}</span>" for _, h in columns)
                + f"</{ot}></{ct}></{ct}>",
                unsafe_allow_html=True,
            )

            for row_idx, rid, rec in row_entries:
                sel = " selected" if rid and rid == active_id else ""
                rid_attr = html.escape(rid, quote=True)
                cells = "".join(
                    f'<span class="ips-data-cell">{_cell_content(field, rec, plain_cell=plain_cell, html_cell=html_cell)}</span>'
                    for field, _ in columns
                )
                label = _row_label(rec, columns)
                row_html = (
                    f'<{ot} class="ips-clean-row ips-data-row{sel}" style="{grid}" '
                    f'data-row-id="{rid_attr}" role="button" tabindex="0">{cells}</{ot}>'
                )

                def _select_row(_rid: str = rid) -> None:
                    apply_clean_table_row_selection(
                        _rid,
                        session_select_key=sel_key,
                        records_by_id=records_by_id,
                        on_row_click=on_row_click,
                    )

                with st.container():
                    st.markdown(
                        '<span class="ips-clean-row-host ips-clean-row-wrap ips-clean-row-select-btn" aria-hidden="true"></span>',
                        unsafe_allow_html=True,
                    )
                    st.button(
                        " ",
                        key=f"{key}_row_sel_{row_idx}",
                        help=f"Select {label}",
                        on_click=_select_row,
                    )
                    st.markdown(row_html, unsafe_allow_html=True)

        picked = render_clean_table_click_bridge(
            table_selector=f".{table_class}",
            row_selector=".ips-data-row[data-row-id]",
            component_key=f"{key}_row_click_bridge",
        )
        if picked:
            pid = str(picked).strip()
            if pid and pid in records_by_id:
                if apply_clean_table_row_selection(
                    pid,
                    session_select_key=sel_key,
                    records_by_id=records_by_id,
                    on_row_click=on_row_click,
                ):
                    st.rerun()

    return str(st.session_state.get(sel_key) or "").strip() or None


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
    _ = hide_select
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
            col_fr=col_fr,
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
            f'<{open_tag} class="ips-clean-row ips-data-row{sel}" style="{grid}">{"".join(parts)}<{close_tag}>',
            unsafe_allow_html=True,
        )
    st.markdown(f"<{close_tag}><{close_tag}>", unsafe_allow_html=True)
    sel = st.session_state.get(session_select_key) or selected_id
    return str(sel) if sel else None
