"""Focused Pricing Guide item detail lookup and bounded modal cache."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import streamlit as st

from app.pages._core._data import pricing_guide_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get
from app.services.pricing_guide_service import normalize_pricing_row

_MODAL_CACHE_KEY = "_ips_pg_modal_by_id"
_DETAIL_CACHE_PREFIX = "pg_detail:"
_MAX_MODAL_CACHE = 50


@dataclass(frozen=True)
class PricingHistoryPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int


def get_pricing_guide_item_detail(item_id: str) -> dict[str, Any] | None:
    """Load base detail record for modal header/tabs/edit — no tab payloads."""
    from app.perf_debug import perf_span

    pid = str(item_id or "").strip()
    if not pid:
        return None
    version = pricing_guide_catalog_data_version()
    cache_key = f"{_DETAIL_CACHE_PREFIX}{pid}:{version}"

    def _fetch() -> dict[str, Any] | None:
        from app.services.repository import fetch_by_id

        row = fetch_by_id("pricing_guide_items", pid)
        if not row:
            legacy = fetch_by_id("estimate_materials", pid)
            if legacy:
                row = {**legacy, "_source": "estimate_materials"}
        if not row:
            return None
        return normalize_pricing_row(row)

    with perf_span("pricing_guide.detail_lookup"):
        detail = page_data_cache_get(cache_key, _fetch)
    if isinstance(detail, dict):
        put_pricing_guide_in_modal_cache(pid, detail)
    return detail if isinstance(detail, dict) else None


def put_pricing_guide_in_modal_cache(item_id: str, row: dict[str, Any] | None) -> None:
    """Bounded modal cache: current page, selected, and recently opened items."""
    pid = str(item_id or "").strip()
    if not pid or not isinstance(row, dict):
        return
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if not isinstance(cache, dict):
        cache = {}
    else:
        cache = dict(cache)
    cache[pid] = row
    if len(cache) > _MAX_MODAL_CACHE:
        drop = max(0, len(cache) - _MAX_MODAL_CACHE)
        for key in list(cache.keys())[:drop]:
            if key != pid:
                cache.pop(key, None)
    st.session_state[_MODAL_CACHE_KEY] = cache


def get_pricing_guide_from_modal_cache(item_id: str) -> dict[str, Any] | None:
    pid = str(item_id or "").strip()
    if not pid:
        return None
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if isinstance(cache, dict):
        row = cache.get(pid)
        if isinstance(row, dict):
            return row
    return get_pricing_guide_item_detail(pid)


def invalidate_pricing_guide_detail_cache(item_id: str = "") -> None:
    pid = str(item_id or "").strip()
    cache = st.session_state.get(_MODAL_CACHE_KEY)
    if isinstance(cache, dict):
        updated = dict(cache)
        if pid:
            updated.pop(pid, None)
        else:
            updated.clear()
        st.session_state[_MODAL_CACHE_KEY] = updated


def list_pricing_price_history(
    item_id: str,
    *,
    page: int = 1,
    page_size: int = 25,
) -> PricingHistoryPage:
    """Paginated price history for one Pricing Guide item (newest first)."""
    from app.perf_debug import perf_span

    pid = str(item_id or "").strip()
    if not pid:
        return PricingHistoryPage([], 0, 1, page_size)
    with perf_span("pricing_guide.detail.price_history"):
        from app.db import fetch_by_match_admin

        try:
            rows = list(
                fetch_by_match_admin(
                    "pricing_guide_price_history",
                    {"pricing_item_id": pid},
                    limit=5000,
                    order_by="changed_at",
                )
                or []
            )
        except Exception:
            rows = []
        rows = [r for r in rows if isinstance(r, dict)]
        rows = list(reversed(rows))
        total = len(rows)
        page_num = max(1, int(page))
        size = max(1, int(page_size))
        start = (page_num - 1) * size
        return PricingHistoryPage(rows[start : start + size], total, page_num, size)
