"""Searchable select widgets (type-to-filter catalog picks)."""

from __future__ import annotations

import inspect
from typing import Any

import streamlit as st

from app.services.estimate_builder_helpers import filter_pricing_option_labels
def render_searchable_selectbox(
    label: str,
    options: list[str],
    *,
    key: str,
    placeholder: str = "Type to search…",
    label_visibility: str = "collapsed",
    searchable_options: list[tuple[str, dict[str, Any]]] | None = None,
) -> str:
    """
    Selectbox that supports typing to filter options.

    Uses Streamlit fuzzy filter when available; otherwise search field + filtered selectbox.
    """
    sig = inspect.signature(st.selectbox)
    if "filter_mode" in sig.parameters:
        return st.selectbox(
            label,
            options,
            key=key,
            label_visibility=label_visibility,
            placeholder=placeholder,
            filter_mode="fuzzy",
        )

    search_key = f"{key}__search"
    st.text_input(
        label,
        key=search_key,
        placeholder=placeholder,
        label_visibility=label_visibility,
    )
    query = str(st.session_state.get(search_key) or "")
    if searchable_options is not None:
        shown = filter_pricing_option_labels(searchable_options, query)
    else:
        q = query.strip().casefold()
        shown = [opt for opt in options if not q or q in opt.casefold()]
    current = st.session_state.get(key)
    if current and current not in shown:
        shown = [current, *shown]
    if not shown:
        shown = list(options[:1]) if options else [""]
    return st.selectbox(
        label,
        shown,
        key=key,
        label_visibility="collapsed",
    )
