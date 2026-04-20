from __future__ import annotations

from collections.abc import Callable

import pandas as pd
import streamlit as st

from app.table_actions import render_selectable_dataframe


def render_crud_table(
    df: pd.DataFrame,
    *,
    table_key: str,
    id_column: str = "id",
    columns: list[str],
    editor_key: str,
    hide_id_column: bool = True,
    num_rows: str = "fixed",
    action_bar: Callable[[list[str]], None] | None = None,
    toolbar_above: bool = False,
) -> list[str]:
    """
    Wrapper around :func:`render_selectable_dataframe`.

    If ``toolbar_above`` is True and ``action_bar`` is set, reserves a slot above the table
    (Streamlit ``st.empty``) so the action bar renders above the dataframe, matching existing
    IPS CRUD pages.
    """
    if df.empty:
        st.info("No rows found.")
        return []
    if toolbar_above and action_bar is not None:
        bar_ph = st.empty()
        _, sel = render_selectable_dataframe(
            df,
            table_key=table_key,
            id_column=id_column,
            columns=columns,
            editor_key=editor_key,
            num_rows=num_rows,
            hide_id_column=hide_id_column,
        )
        with bar_ph.container():
            action_bar(sel)
        return sel
    _, sel = render_selectable_dataframe(
        df,
        table_key=table_key,
        id_column=id_column,
        columns=columns,
        editor_key=editor_key,
        num_rows=num_rows,
        hide_id_column=hide_id_column,
    )
    if action_bar is not None:
        action_bar(sel)
    return sel
