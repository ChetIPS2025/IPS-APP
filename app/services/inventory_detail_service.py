"""Focused Inventory item detail lookup and bounded modal cache."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.pages._core._data import inventory_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get
from app.services.catalog_stock_policy_service import enrich_inventory_rows
from app.services.inventory_service import get_inventory_item

_MODAL_CACHE_KEY = "_ips_inventory_modal_by_id"
_DETAIL_CACHE_PREFIX = "inventory_detail:"
_MAX_MODAL_CACHE = 50


def get_inventory_item_detail(item_id: str) -> dict[str, Any] | None:
    """Base item record for header/overview/edit — no tab payloads."""
    iid = str(item_id or "").strip()
    if not iid:
        return None
    version = inventory_catalog_data_version()
    cache_key = f"{_DETAIL_CACHE_PREFIX}{iid}:{version}"

    def _fetch() -> dict[str, Any] | None:
        row = get_inventory_item(iid)
        if not row:
            return None
        enriched = enrich_inventory_rows([row])
        return enriched[0] if enriched else row

    detail = page_data_cache_get(cache_key, _fetch)
    if isinstance(detail, dict):
        put_item_in_modal_cache(iid, detail)
    return detail if isinstance(detail, dict) else None


def put_item_in_modal_cache(item_id: str, item: dict[str, Any] | None) -> None:
    iid = str(item_id or "").strip()
    if not iid or not isinstance(item, dict):
        return
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if not isinstance(cache, dict):
        cache = {}
    else:
        cache = dict(cache)
    cache[iid] = item
    if len(cache) > _MAX_MODAL_CACHE:
        drop = max(0, len(cache) - _MAX_MODAL_CACHE)
        for key in list(cache.keys())[:drop]:
            if key != iid:
                cache.pop(key, None)
    st.session_state[_MODAL_CACHE_KEY] = cache


def get_item_from_modal_cache(item_id: str) -> dict[str, Any] | None:
    iid = str(item_id or "").strip()
    if not iid:
        return None
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if isinstance(cache, dict):
        row = cache.get(iid)
        if isinstance(row, dict):
            return row
    return get_inventory_item_detail(iid)


def invalidate_inventory_detail_cache(item_id: str = "") -> None:
    iid = str(item_id or "").strip()
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if isinstance(cache, dict):
        updated = dict(cache)
        if iid:
            updated.pop(iid, None)
        else:
            updated.clear()
        st.session_state[_MODAL_CACHE_KEY] = updated
