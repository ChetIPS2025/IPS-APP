"""Professional data tables."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

try:
    from app.ui.catalog_inventory_display import (
        HIDDEN_SYSTEM_COLUMNS,
        drop_hidden_system_columns,
        prepare_catalog_inventory_display_df,
    )
    from app.ui.page_shell import render_filter_row
    from app.ui.page_shell import render_table as _render_table
except ImportError:
    from ui.catalog_inventory_display import (  # type: ignore
        HIDDEN_SYSTEM_COLUMNS,
        drop_hidden_system_columns,
        prepare_catalog_inventory_display_df,
    )
    from ui.page_shell import render_filter_row  # type: ignore
    from ui.page_shell import render_table as _render_table  # type: ignore

_NUMERIC_HINTS = frozenset(
    {
        "amount",
        "cost",
        "price",
        "total",
        "hours",
        "qty",
        "quantity",
        "count",
        "rate",
        "balance",
        "on_hand",
        "reorder",
    }
)


def hide_internal_columns(
    df: pd.DataFrame,
    *,
    extra_hidden: frozenset[str] | None = None,
    keep: frozenset[str] | None = None,
) -> pd.DataFrame:
    return drop_hidden_system_columns(df, extra_hidden=extra_hidden, keep=keep)


def prepare_display_table(
    data: pd.DataFrame | list[dict[str, Any]] | None,
    **kwargs: Any,
) -> pd.DataFrame:
    return prepare_catalog_inventory_display_df(data, **kwargs)


def render_filters(
    specs: list[dict[str, Any]],
    *,
    gap: str = "small",
    clear_key: str | None = None,
    on_clear=None,
) -> dict[str, Any]:
    """Alias for :func:`page_shell.render_filter_row`."""
    return render_filter_row(specs, gap=gap, clear_key=clear_key, on_clear=on_clear)


def _numeric_column_config(df: pd.DataFrame) -> dict[str, Any]:
    cfg: dict[str, Any] = {}
    for col in df.columns:
        cl = str(col).lower().replace(" ", "_")
        if any(h in cl for h in _NUMERIC_HINTS):
            try:
                cfg[col] = st.column_config.NumberColumn(format="%.2f")
            except Exception:
                pass
    return cfg


def render_table(
    df: pd.DataFrame,
    *,
    height: int | None = None,
    hide_internal: bool = True,
    column_config: dict[str, Any] | None = None,
    zebra: bool = True,
    **dataframe_kwargs: Any,
) -> None:
    """Display table with IPS styling, hidden system columns, optional numeric alignment."""
    st.markdown('<span class="ips-table-surface" aria-hidden="true"></span>', unsafe_allow_html=True)
    disp = hide_internal_columns(df) if hide_internal else df
    cfg = dict(_numeric_column_config(disp))
    if column_config:
        cfg.update(column_config)
    _render_table(
        disp,
        height=height,
        hide_internal=False,
        column_config=cfg or None,
        **dataframe_kwargs,
    )
