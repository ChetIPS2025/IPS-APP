"""Native Streamlit dataframe single-row selection for list tables."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

import pandas as pd
import streamlit as st

CellFormatter = Callable[[str, dict[str, Any]], str]
ColumnWidth = Literal["small", "medium", "large"]

_DEFAULT_WIDTHS: dict[str, ColumnWidth] = {
    "status": "small",
    "priority": "small",
    "last_login": "small",
    "due_date": "small",
    "start_date": "small",
    "end_date": "small",
    "job_number": "small",
    "estimate_number": "small",
}


def _df_gen_key(table_key: str) -> str:
    return f"ips_click_df_gen_{table_key}"


def dataframe_widget_key(table_key: str) -> str:
    """Session-state key for the underlying ``st.dataframe`` widget."""
    gen = int(st.session_state.get(_df_gen_key(table_key), 0) or 0)
    return f"ips_click_df_{table_key}_{gen}"


def clear_modal_selection_state(
    key: str,
    *,
    table_key: str | None = None,
    session_select_key: str | None = None,
    modal_key: str | None = None,
) -> None:
    """Clear modal/table selection without forcing a rerun (for ``on_dismiss``)."""
    version_key = f"{key}__table_version"
    st.session_state[f"{key}__modal_open"] = False
    st.session_state.pop(f"{key}__selected_id", None)
    st.session_state.pop(f"{key}__selected_record", None)
    st.session_state[version_key] = int(st.session_state.get(version_key, 0) or 0) + 1

    if table_key and session_select_key:
        st.session_state.pop(session_select_key, None)
        if modal_key:
            st.session_state.pop(modal_key, None)
        st.session_state.pop(dataframe_widget_key(table_key), None)
        st.session_state[_df_gen_key(table_key)] = int(st.session_state.get(_df_gen_key(table_key), 0) or 0) + 1


def close_modal_and_clear_selection(
    key: str,
    *,
    table_key: str | None = None,
    session_select_key: str | None = None,
    modal_key: str | None = None,
) -> None:
    """Clear list selection, reset the dataframe widget, and rerun."""
    clear_modal_selection_state(
        key,
        table_key=table_key,
        session_select_key=session_select_key,
        modal_key=modal_key,
    )
    st.rerun()


def clear_table_selection(*, table_key: str, session_select_key: str) -> None:
    """Reset native dataframe row selection (inline detail panels)."""
    clear_modal_selection_state(
        table_key,
        table_key=table_key,
        session_select_key=session_select_key,
        modal_key=None,
    )


def get_modal_record(
    *,
    cache_key: str,
    modal_key: str,
    session_select_key: str,
) -> dict[str, Any] | None:
    """Resolve the selected record for a detail modal."""
    from app.components.record_modal import get_modal_record as _get_modal_record
    return _get_modal_record(
        cache_key=cache_key,
        modal_key=modal_key,
        session_select_key=session_select_key,
    )


def _cell_value(
    field: str,
    row: dict[str, Any],
    *,
    format_cell: CellFormatter | None,
) -> str:
    if format_cell:
        return str(format_cell(field, row))
    val = row.get(field)
    return str(val).strip() if val is not None and str(val).strip() else "—"


def _column_width(field: str, column_widths: dict[str, ColumnWidth] | None) -> ColumnWidth:
    if column_widths and field in column_widths:
        return column_widths[field]
    return _DEFAULT_WIDTHS.get(field, "medium")


def render_selectable_table(
    records: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    table_key: str,
    *,
    row_id_key: str = "id",
    session_select_key: str,
    on_row_selected: Callable[[str, dict[str, Any]], None] | None = None,
    format_cell: CellFormatter | None = None,
    click_caption: str | None = None,
    column_widths: dict[str, ColumnWidth] | None = None,
) -> str | None:
    """
    Render a selectable list table using native ``st.dataframe`` row selection.

    Uses ``selection_mode="single-row"`` and ``on_select="rerun"`` — no Select buttons
    and no custom HTML click overlays. The checkbox selector opens the detail modal.
    """
    valid_records: list[dict[str, Any]] = []
    row_ids: list[str] = []
    records_by_id: dict[str, dict[str, Any]] = {}
    for rec in records:
        rid = str(rec.get(row_id_key) or "").strip()
        if not rid:
            continue
        valid_records.append(rec)
        row_ids.append(rid)
        records_by_id[rid] = rec

    if not valid_records:
        st.caption("No records to display.")
        st.session_state.pop(session_select_key, None)
        return None

    st.caption(click_caption or "Select a row to open details.")

    cur_sel = str(st.session_state.get(session_select_key) or "").strip()
    if cur_sel and cur_sel not in records_by_id:
        st.session_state.pop(session_select_key, None)
        cur_sel = ""

    rows: list[dict[str, str]] = []
    for rec in valid_records:
        rows.append(
            {
                field: _cell_value(field, rec, format_cell=format_cell)
                for field, _header in columns
            }
        )
    df = pd.DataFrame(rows)

    column_config = {
        field: st.column_config.TextColumn(
            header,
            width=_column_width(field, column_widths),
        )
        for field, header in columns
    }

    df_key = dataframe_widget_key(table_key)
    st.session_state[f"ips_click_table_map_{session_select_key}"] = table_key
    st.markdown(
        f'<span class="ips-selectable-table ips-native-click-table ips-native-click-table-{table_key}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    selection = st.dataframe(
        df,
        column_config=column_config,
        hide_index=True,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        key=df_key,
    )

    selected_id: str | None = None
    if selection.selection.rows:
        idx = int(selection.selection.rows[0])
        if 0 <= idx < len(row_ids):
            selected_id = row_ids[idx]
            st.session_state[session_select_key] = selected_id
            if on_row_selected and selected_id in records_by_id:
                on_row_selected(selected_id, records_by_id[selected_id])

    return selected_id


# Backward-compatible alias used across list pages.
render_clickable_table = render_selectable_table
