from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def render_search_box(*, key: str, placeholder: str) -> str:
    return st.text_input("Search", placeholder=placeholder, key=key)


def render_status_filter(*, key: str, options: list[str]) -> str:
    return st.selectbox("Status", options, key=key)


def apply_text_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if df.empty or not str(query or "").strip():
        return df
    s = str(query).strip().lower()
    mask = df.astype(str).apply(
        lambda col: col.str.lower().str.contains(s, na=False, regex=False)
    )
    return df[mask.any(axis=1)]


def apply_boolean_status_filter(
    df: pd.DataFrame,
    *,
    column: str,
    selected: str,
    active_label: str = "Active only",
    inactive_label: str = "Inactive only",
    all_label: str = "All",
) -> pd.DataFrame:
    if df.empty or column not in df.columns or selected == all_label:
        return df
    if selected == active_label:
        return df[df[column] == True]  # noqa: E712
    if selected == inactive_label:
        return df[df[column] == False]  # noqa: E712
    return df


def safe_string(v: Any) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v).strip()
