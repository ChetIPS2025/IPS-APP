"""Paginated Inventory directory — list projection, filters, reorder counts, exports."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable

import streamlit as st

from app.components.inventory_list_table import (
    inventory_category,
    inventory_description,
    inventory_location,
    inventory_vendor,
    normalize_inventory_status,
)
from app.components.table_filters import apply_column_filters
from app.pages._core._data import inventory_catalog_data_version
from app.pages._core.page_data_cache import page_data_cache_get
from app.services.catalog_stock_policy_service import (
    enrich_inventory_rows,
    inventory_needs_reorder,
    passes_inventory_view_filter,
)
from app.services.inventory_display_helpers import resolve_inventory_sku

_INVENTORY_FILTER_OPTIONS_PREFIX = "inventory_filter_options:"
_INVENTORY_TABLE_KEY = "inventory_list"
_EXPORT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class InventoryPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    filter_options: dict[str, list[str]]
    reorder_count: int
    is_live: bool
    warning: str | None = None


@dataclass(frozen=True)
class InventoryExportRequest:
    search: str
    stock_view: str
    category_filters: tuple[str, ...]
    location_filters: tuple[str, ...]
    status_filters: tuple[str, ...]
    vendor_filters: tuple[str, ...]
    inventory_version: int
    export_version: int = _EXPORT_SCHEMA_VERSION

    def cache_key(self) -> str:
        payload = {
            "search": self.search,
            "stock_view": self.stock_view,
            "category": list(self.category_filters),
            "location": list(self.location_filters),
            "status": list(self.status_filters),
            "vendor": list(self.vendor_filters),
            "inventory_version": self.inventory_version,
            "export_version": self.export_version,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


_COLUMN_FILTER_SPECS: list[tuple[str, Callable[[dict[str, Any]], str]]] = [
    ("category", inventory_category),
    ("location", inventory_location),
    ("status", lambda r: normalize_inventory_status(r.get("status"))),
    ("vendor", inventory_vendor),
]


def _inventory_sku(row: dict[str, Any]) -> str:
    return resolve_inventory_sku(row)


def _load_enriched_catalog() -> list[dict[str, Any]]:
    from app.pages._core._data import load_inventory
    from app.perf_debug import perf_span

    version = inventory_catalog_data_version()

    def _build() -> list[dict[str, Any]]:
        with perf_span("inventory.list_query"):
            return enrich_inventory_rows(load_inventory())

    return page_data_cache_get(f"inventory_enriched_catalog:{version}", _build)


def _filter_inventory_rows(
    rows: list[dict[str, Any]],
    *,
    search: str = "",
    stock_view: str = "In stock",
    categories: list[str] | None = None,
    locations: list[str] | None = None,
    statuses: list[str] | None = None,
    vendors: list[str] | None = None,
) -> list[dict[str, Any]]:
    out = [r for r in rows if passes_inventory_view_filter(r, view=stock_view)]
    query = str(search or "").strip()
    if query:
        ql = query.lower()
        out = [
            r
            for r in out
            if ql in _inventory_sku(r).lower()
            or ql in str(r.get("qr_code_value") or "").lower()
            or ql in inventory_description(r).lower()
            or ql in inventory_category(r).lower()
            or ql in inventory_location(r).lower()
            or ql in inventory_vendor(r).lower()
            or ql in normalize_inventory_status(r.get("status")).lower()
            or ql in str(r.get("stock_policy_label") or "").lower()
        ]
    if categories:
        wanted = {str(c).strip() for c in categories if str(c).strip()}
        if wanted:
            out = [r for r in out if inventory_category(r) in wanted]
    if locations:
        wanted = {str(v).strip() for v in locations if str(v).strip()}
        if wanted:
            out = [r for r in out if inventory_location(r) in wanted]
    if statuses:
        wanted = {normalize_inventory_status(s) for s in statuses if str(s).strip()}
        if wanted:
            out = [r for r in out if normalize_inventory_status(r.get("status")) in wanted]
    if vendors:
        wanted = {str(v).strip() for v in vendors if str(v).strip()}
        if wanted:
            out = [r for r in out if inventory_vendor(r) in wanted]
    return apply_column_filters(out, _INVENTORY_TABLE_KEY, _COLUMN_FILTER_SPECS)


def load_inventory_filter_options() -> dict[str, list[str]]:
    version = inventory_catalog_data_version()
    cache_key = f"{_INVENTORY_FILTER_OPTIONS_PREFIX}{version}"

    def _build() -> dict[str, list[str]]:
        rows = _load_enriched_catalog()
        categories: set[str] = set()
        locations: set[str] = set()
        statuses: set[str] = set()
        vendors: set[str] = set()
        for row in rows:
            cat = inventory_category(row)
            if cat and cat != "—":
                categories.add(cat)
            loc = inventory_location(row)
            if loc and loc != "—":
                locations.add(loc)
            statuses.add(normalize_inventory_status(row.get("status")))
            ven = inventory_vendor(row)
            if ven and ven != "—":
                vendors.add(ven)
        return {
            "category": sorted(categories),
            "location": sorted(locations),
            "status": sorted(statuses),
            "vendor": sorted(vendors),
        }

    return page_data_cache_get(cache_key, _build)


def count_inventory_needing_reorder(*, rows: list[dict[str, Any]] | None = None) -> int:
    from app.perf_debug import perf_span

    version = inventory_catalog_data_version()

    def _count() -> int:
        catalog = rows if rows is not None else _load_enriched_catalog()
        return sum(1 for r in catalog if inventory_needs_reorder(r))

    with perf_span("inventory.reorder_count"):
        return page_data_cache_get(f"inventory_reorder_count:{version}", _count)


def list_inventory_page(
    *,
    search: str = "",
    stock_view: str = "In stock",
    categories: list[str] | None = None,
    locations: list[str] | None = None,
    statuses: list[str] | None = None,
    vendors: list[str] | None = None,
    page: int = 1,
    page_size: int = 25,
    table_key: str = _INVENTORY_TABLE_KEY,
) -> InventoryPage:
    from app.components.table_pagination import pagination_meta
    from app.perf_debug import perf_span

    with perf_span("inventory.list_query"):
        catalog = _load_enriched_catalog()
        filter_options = load_inventory_filter_options()
        filtered = _filter_inventory_rows(
            catalog,
            search=search,
            stock_view=stock_view,
            categories=categories,
            locations=locations,
            statuses=statuses,
            vendors=vendors,
        )
        reorder_count = count_inventory_needing_reorder(rows=catalog)
        page_num, size, _total_pages = pagination_meta(len(filtered), table_key)
        if page > 0 and page_size > 0:
            page_num = max(1, int(page))
            size = max(1, int(page_size))
        start = (page_num - 1) * size
        page_rows = filtered[start : start + size]
        return InventoryPage(
            rows=page_rows,
            total_count=len(filtered),
            page=page_num,
            page_size=size,
            filter_options=filter_options,
            reorder_count=reorder_count,
            is_live=True,
            warning=None,
        )


def build_export_request(
    *,
    search: str,
    stock_view: str,
) -> InventoryExportRequest:
    from app.components.table_filters import get_column_filter_values

    return InventoryExportRequest(
        search=str(search or "").strip(),
        stock_view=str(stock_view or "In stock").strip(),
        category_filters=tuple(get_column_filter_values(_INVENTORY_TABLE_KEY, "category")),
        location_filters=tuple(get_column_filter_values(_INVENTORY_TABLE_KEY, "location")),
        status_filters=tuple(get_column_filter_values(_INVENTORY_TABLE_KEY, "status")),
        vendor_filters=tuple(get_column_filter_values(_INVENTORY_TABLE_KEY, "vendor")),
        inventory_version=inventory_catalog_data_version(),
    )


def list_inventory_export_rows(
    *,
    search: str = "",
    stock_view: str = "In stock",
    categories: list[str] | None = None,
    locations: list[str] | None = None,
    statuses: list[str] | None = None,
    vendors: list[str] | None = None,
) -> list[dict[str, Any]]:
    from app.perf_debug import perf_span

    with perf_span("inventory.export_query"):
        catalog = _load_enriched_catalog()
        return _filter_inventory_rows(
            catalog,
            search=search,
            stock_view=stock_view,
            categories=categories,
            locations=locations,
            statuses=statuses,
            vendors=vendors,
        )


def clear_prepared_export_bytes() -> None:
    for key in (
        "inv_label_export_cache_key",
        "inv_label_export_zip_bytes",
        "inv_label_export_csv_bytes",
        "inv_label_export_item_count",
    ):
        st.session_state.pop(key, None)


def invalidate_inventory_directory_cache() -> None:
    from app.pages._core._data import clear_inventory_catalog_cache
    from app.services.inventory_detail_service import invalidate_inventory_detail_cache
    from app.services.inventory_images import clear_inventory_image_url_cache
    from app.services.repository import clear_data_cache_for_table

    clear_data_cache_for_table("inventory_items")
    clear_inventory_image_url_cache()
    try:
        from app.services.pricing_guide_images import clear_catalog_image_maps_cache

        clear_catalog_image_maps_cache()
    except ImportError:
        pass
    clear_inventory_catalog_cache()
    clear_prepared_export_bytes()
    invalidate_inventory_detail_cache()
