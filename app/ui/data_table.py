"""Shared IPS data table component."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.components.status import status_pill_html
    from app.components.table_filters import apply_column_filters, build_filter_options
    from app.components.table_pagination import (
        paginate_rows,
        render_table_pagination_footer,
        render_table_pagination_header,
    )
    from app.components.tables import render_data_table as _render_core_table
    from app.ui.status_badge import status_badge_html
except ImportError:
    from components.status import status_pill_html  # type: ignore
    from components.table_filters import apply_column_filters, build_filter_options  # type: ignore
    from components.table_pagination import (  # type: ignore
        paginate_rows,
        render_table_pagination_footer,
        render_table_pagination_header,
    )
    from components.tables import render_data_table as _render_core_table  # type: ignore
    from ui.status_badge import status_badge_html  # type: ignore

HtmlCellFn = Callable[[str, dict[str, Any]], str]


def _default_status_cell(_field: str, row: dict[str, Any]) -> str:
    status_field = "status"
    for candidate in ("status", "job_status", "estimate_status", "user_status"):
        if row.get(candidate) not in (None, ""):
            status_field = candidate
            break
    return status_badge_html(str(row.get(status_field) or "—"))


def render_data_table(
    columns: list[tuple[str, str]],
    rows: list[dict[str, Any]],
    row_key: str,
    *,
    table_key: str,
    clickable_columns: list[str] | None = None,
    actions: list[Callable[[], None]] | None = None,
    status_column: str | None = None,
    image_column: str | None = None,
    empty_message: str = "No records to display.",
    compact: bool = True,
    horizontal_scroll: bool = True,
    session_select_key: str | None = None,
    selected_id: str | None = None,
    col_fr: list[str] | None = None,
    cell_renderer: HtmlCellFn | None = None,
    plain_cell: Callable[[str, dict[str, Any]], str] | None = None,
    use_native: bool = True,
    page_size: int | None = None,
    show_pagination: bool = False,
) -> str | None:
    """
    Shared IPS list table pattern.

    Wraps the existing clickable table implementation with consistent styling hooks.
    """
    _ = (clickable_columns, actions, image_column, compact, horizontal_scroll, page_size)

    if not rows:
        st.info(empty_message)
        return None

    display_rows = list(rows)
    if show_pagination and page_size:
        render_table_pagination_header(len(display_rows), table_key)
        display_rows, _page_num, _page_size, _total = paginate_rows(
            display_rows, table_key, default_page_size=page_size
        )

    scroll_cls = " ips-mobile-scroll" if horizontal_scroll else ""
    st.markdown(
        f'<span class="ips-table ips-table-marker{scroll_cls}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    renderer = cell_renderer
    if status_column and renderer is None:
        status_field = status_column

        def _renderer(field: str, row: dict[str, Any]) -> str:
            if field == status_field:
                return _default_status_cell(field, row)
            val = row.get(field)
            return str(val) if val is not None else "—"

        renderer = _renderer

    sel_key = session_select_key or f"{table_key}_selected"
    result = _render_core_table(
        display_rows,
        columns,
        row_id_key=row_key,
        selected_id=selected_id,
        session_select_key=sel_key,
        col_fr=col_fr,
        cell_renderer=renderer,
        plain_cell=plain_cell,
        use_native=use_native,
        table_key=table_key,
    )

    if show_pagination and page_size:
        render_table_pagination_footer(len(rows), table_key)

    return result


__all__ = [
    "render_data_table",
    "apply_column_filters",
    "build_filter_options",
    "paginate_rows",
    "status_pill_html",
]
