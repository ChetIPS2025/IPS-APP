"""Paginated Pricing Guide directory — list projection, filters, and summary aggregates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import streamlit as st

from app.components.table_filters import apply_column_filters, get_column_filter_values
from app.pages._core._data import pricing_guide_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get
from app.services.pricing_guide_service import (
    PricingGuideFetchResult,
    fetch_pricing_guide_catalog,
    normalize_pricing_row,
    pricing_guide_summary,
    search_pricing_rows,
)

_PG_FILTER_OPTIONS_CACHE_PREFIX = "pg_filter_options:"
_PG_TABLE_KEY = "pg_list"

_PG_COLUMN_FILTER_SPECS: list[tuple[str, Callable[[dict[str, Any]], str]]] = [
    ("item_class", lambda r: str(r.get("item_class") or "Non-Inventory")),
    ("category", lambda r: str(r.get("category") or "—")),
    ("vendor", lambda r: str(r.get("vendor") or "—")),
    ("status", lambda r: str(r.get("status") or "Active")),
]

_LIST_PROJECTION_KEYS: tuple[str, ...] = (
    "id",
    "item",
    "description",
    "item_code",
    "item_key",
    "item_class",
    "item_type",
    "category",
    "vendor",
    "status",
    "is_active",
    "unit",
    "default_cost",
    "markup_pct",
    "default_markup_percent",
    "customer_price",
    "default_sell_price",
    "sku",
    "item_number",
    "model_number",
    "linked_inventory_id",
    "inventory_item_id",
    "linked_asset_id",
    "asset_id",
    "inventory_label",
    "asset_label",
    "image_path",
    "image_url",
    "image_file_name",
    "image_status",
)


@dataclass(frozen=True)
class PricingGuidePage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    filter_options: dict[str, list[str]]
    summary: dict[str, Any]
    is_live: bool
    warning: str | None = None


def _catalog_cache_key(*, include_inactive: bool) -> str:
    version = pricing_guide_catalog_data_version()
    return f"pg_catalog:{version}:inactive={include_inactive}"


def _load_catalog_result(*, include_inactive: bool = True) -> PricingGuideFetchResult:
    """Single authoritative catalog load per data version."""

    def _fetch() -> PricingGuideFetchResult:
        return fetch_pricing_guide_catalog(include_inactive=include_inactive)

    return page_data_cache_get(_catalog_cache_key(include_inactive=include_inactive), _fetch)


def _list_projection(row: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_pricing_row(row) if not row.get("item") else row
    return {key: normalized.get(key) for key in _LIST_PROJECTION_KEYS}


def _filter_pricing_rows(
    rows: list[dict[str, Any]],
    *,
    search: str = "",
    item_classes: list[str] | None = None,
    categories: list[str] | None = None,
    vendors: list[str] | None = None,
    statuses: list[str] | None = None,
    table_key: str = _PG_TABLE_KEY,
) -> list[dict[str, Any]]:
    out = search_pricing_rows(rows, search)
    if item_classes:
        wanted = {str(v).strip() for v in item_classes if str(v).strip()}
        if wanted:
            out = [r for r in out if str(r.get("item_class") or "Non-Inventory") in wanted]
    if categories:
        wanted = {str(v).strip() for v in categories if str(v).strip()}
        if wanted:
            out = [r for r in out if str(r.get("category") or "—") in wanted]
    if vendors:
        wanted = {str(v).strip() for v in vendors if str(v).strip()}
        if wanted:
            out = [r for r in out if str(r.get("vendor") or "—") in wanted]
    if statuses:
        wanted = {str(v).strip() for v in statuses if str(v).strip()}
        if wanted:
            out = [r for r in out if str(r.get("status") or "Active") in wanted]
    return apply_column_filters(out, table_key, _PG_COLUMN_FILTER_SPECS)


def load_pricing_guide_filter_options() -> dict[str, list[str]]:
    """Distinct filter values cached by Pricing Guide catalog data version."""
    version = pricing_guide_catalog_data_version()
    cache_key = f"{_PG_FILTER_OPTIONS_CACHE_PREFIX}{version}"

    def _build() -> dict[str, list[str]]:
        from app.perf_debug import perf_span

        with perf_span("pricing_guide.filter_options"):
            result = _load_catalog_result(include_inactive=True)
            classes: set[str] = set()
            categories: set[str] = set()
            vendors: set[str] = set()
            statuses: set[str] = set()
            for row in result.rows:
                classes.add(str(row.get("item_class") or "Non-Inventory"))
                cat = str(row.get("category") or "—").strip()
                if cat:
                    categories.add(cat)
                vendor = str(row.get("vendor") or "—").strip()
                if vendor and vendor != "—":
                    vendors.add(vendor)
                statuses.add(str(row.get("status") or "Active"))
            return {
                "item_class": sorted(classes),
                "category": sorted(categories),
                "vendor": sorted(vendors),
                "status": sorted(statuses),
            }

    return page_data_cache_get(cache_key, _build)


def load_pricing_guide_summary(
    *,
    search: str = "",
    item_classes: list[str] | None = None,
    categories: list[str] | None = None,
    vendors: list[str] | None = None,
    statuses: list[str] | None = None,
    filtered_rows: list[dict[str, Any]] | None = None,
    table_key: str = _PG_TABLE_KEY,
) -> dict[str, Any]:
    """Summary cards for all items matching current search/filters."""
    from app.perf_debug import perf_span

    with perf_span("pricing_guide.summary"):
        rows = filtered_rows
        if rows is None:
            catalog = _load_catalog_result(include_inactive=True)
            rows = _filter_pricing_rows(
                catalog.rows,
                search=search,
                item_classes=item_classes,
                categories=categories,
                vendors=vendors,
                statuses=statuses,
                table_key=table_key,
            )
        return pricing_guide_summary(rows)


def list_pricing_guide_page(
    *,
    search: str = "",
    item_classes: list[str] | None = None,
    categories: list[str] | None = None,
    vendors: list[str] | None = None,
    statuses: list[str] | None = None,
    page: int = 1,
    page_size: int = 25,
    include_inactive: bool = True,
    table_key: str = _PG_TABLE_KEY,
) -> PricingGuidePage:
    """Return one page of list projection rows plus filter metadata and summary."""
    from app.components.table_pagination import pagination_meta
    from app.perf_debug import perf_span

    with perf_span("pricing_guide.list_query"):
        catalog = _load_catalog_result(include_inactive=include_inactive)
        is_live = catalog.source == "pricing_guide_items"
        warning = catalog.warning
        if item_classes is None and table_key:
            item_classes = get_column_filter_values(table_key, "item_class") or None
        if categories is None and table_key:
            categories = get_column_filter_values(table_key, "category") or None
        if vendors is None and table_key:
            vendors = get_column_filter_values(table_key, "vendor") or None
        if statuses is None and table_key:
            statuses = get_column_filter_values(table_key, "status") or None
        filtered = _filter_pricing_rows(
            catalog.rows,
            search=search,
            item_classes=item_classes,
            categories=categories,
            vendors=vendors,
            statuses=statuses,
            table_key=table_key,
        )
        summary = load_pricing_guide_summary(
            search=search,
            item_classes=item_classes,
            categories=categories,
            vendors=vendors,
            statuses=statuses,
            filtered_rows=filtered,
            table_key=table_key,
        )
        filter_options = load_pricing_guide_filter_options()
        page_num, size, _total_pages = pagination_meta(len(filtered), table_key)
        if page > 0 and page_size > 0:
            page_num = max(1, int(page))
            size = max(1, int(page_size))
        start = (page_num - 1) * size
        page_rows = [_list_projection(r) for r in filtered[start : start + size]]
        return PricingGuidePage(
            rows=page_rows,
            total_count=len(filtered),
            page=page_num,
            page_size=size,
            filter_options=filter_options,
            summary=summary,
            is_live=is_live,
            warning=warning,
        )


def invalidate_pricing_guide_directory_cache() -> None:
    """Centralized Pricing Guide directory cache invalidation."""
    from app.pages._core._data import _bump_pricing_guide_catalog_data_version
    from app.services.pricing_guide_detail_service import invalidate_pricing_guide_detail_cache
    from app.services.pricing_guide_service import cached_pricing_guide_rows

    _bump_pricing_guide_catalog_data_version()
    cached_pricing_guide_rows.clear()
    st.session_state.pop("_pg_catalog_status_checked", None)
    st.session_state.pop("_ips_pg_directory_filter_options", None)
    invalidate_pricing_guide_detail_cache()
