"""Session-scoped derived page data with explicit invalidation hooks."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import streamlit as st

_PAGE_DATA_CACHE_KEY = "_ips_page_data_cache"

T = TypeVar("T")


def page_data_cache_get(cache_key: str, loader: Callable[[], T]) -> T:
    """Load and memoize derived page data for the current Streamlit session."""
    key = str(cache_key or "").strip()
    if not key:
        return loader()
    store = st.session_state.setdefault(_PAGE_DATA_CACHE_KEY, {})
    if key not in store:
        store[key] = loader()
    return store[key]


def clear_page_data_cache_key(cache_key: str) -> None:
    key = str(cache_key or "").strip()
    if not key:
        return
    store = st.session_state.get(_PAGE_DATA_CACHE_KEY)
    if isinstance(store, dict) and key in store:
        del store[key]


def clear_page_data_cache_keys(*cache_keys: str) -> None:
    for cache_key in cache_keys:
        clear_page_data_cache_key(cache_key)


def clear_page_data_cache_prefix(prefix: str) -> None:
    pref = str(prefix or "")
    if not pref:
        return
    store = st.session_state.get(_PAGE_DATA_CACHE_KEY)
    if not isinstance(store, dict):
        return
    for key in list(store.keys()):
        if str(key).startswith(pref):
            del store[key]


def clear_page_data_cache() -> None:
    st.session_state.pop(_PAGE_DATA_CACHE_KEY, None)


def clear_dashboard_page_data_cache() -> None:
    clear_page_data_cache_prefix("dashboard_")


def clear_customers_page_data_cache() -> None:
    clear_page_data_cache_keys("customers_enriched_list", "customers_page_list_rows")


def clear_inventory_page_data_cache() -> None:
    clear_page_data_cache_key("inventory_enriched_rows")


def clear_timekeeping_summaries_page_data_cache() -> None:
    clear_page_data_cache_prefix("timekeeping_summaries:")


__all__ = [
    "page_data_cache_get",
    "clear_page_data_cache",
    "clear_page_data_cache_key",
    "clear_page_data_cache_keys",
    "clear_page_data_cache_prefix",
    "clear_customers_page_data_cache",
    "clear_dashboard_page_data_cache",
    "clear_inventory_page_data_cache",
    "clear_timekeeping_summaries_page_data_cache",
]
