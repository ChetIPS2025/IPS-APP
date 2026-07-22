"""Paginated Equipment directory — filtered projection without full-page catalog loading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.components.table_filters import apply_column_filters
from app.pages._core._data import assets_catalog_data_version
from app.pages._core.page_data_cache import clear_page_data_cache_prefix, page_data_cache_get
from app.services.asset_classification_service import is_equipment_tab_asset
from app.services.status_maps import normalize_asset_status

_EQUIPMENT_DIR_PREFIX = "assets_equipment_dir:"
_EQUIPMENT_FILTER_PREFIX = "assets_equipment_filter_options:"
_EQUIPMENT_TABLE_KEY = "assets_list"

_EQUIPMENT_LIST_COLUMNS = (
    "id",
    "asset_number",
    "asset_id",
    "asset_name",
    "name",
    "category",
    "status",
    "location",
    "location_name",
    "department",
    "current_operator",
    "assigned_to_name",
    "assigned_to",
    "operator",
    "next_service_due",
    "next_service",
    "service_due",
    "model_number",
    "model",
    "serial_number",
    "is_rentable",
    "rental_default_markup_percent",
    "image_url",
    "photo_url",
    "thumbnail_url",
)


def _asset_category(row: dict[str, Any]) -> str:
    return str(row.get("category") or "").strip() or "—"


def _asset_location(row: dict[str, Any]) -> str:
    for key in ("location_name", "location"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _asset_department(row: dict[str, Any]) -> str:
    return str(row.get("department") or "").strip() or "—"


def _asset_assigned_to(row: dict[str, Any]) -> str:
    for key in ("current_operator", "assigned_to_name", "assigned_to", "operator"):
        val = str(row.get(key) or "").strip()
        if val and val != "—":
            return val
    return "—"


def _project_equipment_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {k: row.get(k) for k in _EQUIPMENT_LIST_COLUMNS if k in row}
    out.setdefault("id", row.get("id"))
    out.setdefault("asset_number", row.get("asset_number") or row.get("asset_id"))
    out.setdefault("asset_name", row.get("asset_name") or row.get("name"))
    out.setdefault("category", _asset_category(row))
    out.setdefault("location", _asset_location(row))
    out.setdefault("department", _asset_department(row))
    out.setdefault("current_operator", _asset_assigned_to(row))
    return out


_COLUMN_FILTER_SPECS: list[tuple[str, Callable[[dict[str, Any]], str]]] = [
    ("category", _asset_category),
    ("location", _asset_location),
    ("status", lambda r: normalize_asset_status(r.get("status"))),
    ("department", _asset_department),
]


@dataclass(frozen=True)
class AssetsDirectoryPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    filter_options: dict[str, list[str]]
    summary: dict[str, int]
    is_live: bool
    warning: str | None = None


def _load_equipment_catalog() -> tuple[list[dict[str, Any]], bool]:
    from app.pages._core._data import _cached_assets_rows
    from app.perf_debug import perf_span

    version = assets_catalog_data_version()

    def _build() -> tuple[list[dict[str, Any]], bool]:
        with perf_span("assets.equipment.list_query"):
            rows, used = _cached_assets_rows()
            rows = list(rows)
            equipment = [
                _project_equipment_row(r)
                for r in rows
                if isinstance(r, dict) and is_equipment_tab_asset(r)
            ]
            equipment.sort(
                key=lambda r: (
                    str(r.get("asset_number") or r.get("asset_id") or "").lower(),
                    str(r.get("asset_name") or r.get("name") or "").lower(),
                )
            )
            is_live = not used
            return equipment, is_live

    return page_data_cache_get(f"{_EQUIPMENT_DIR_PREFIX}catalog:{version}", _build)


def load_equipment_filter_options() -> dict[str, list[str]]:
    version = assets_catalog_data_version()
    cache_key = f"{_EQUIPMENT_FILTER_PREFIX}{version}"

    def _build() -> dict[str, list[str]]:
        from app.perf_debug import perf_span

        with perf_span("assets.equipment.filter_options"):
            rows, _ = _load_equipment_catalog()
            categories: set[str] = set()
            locations: set[str] = set()
            statuses: set[str] = set()
            departments: set[str] = set()
            for row in rows:
                cat = _asset_category(row)
                if cat and cat != "—":
                    categories.add(cat)
                loc = _asset_location(row)
                if loc and loc != "—":
                    locations.add(loc)
                statuses.add(normalize_asset_status(row.get("status")))
                dept = _asset_department(row)
                if dept and dept != "—":
                    departments.add(dept)
            return {
                "category": sorted(categories),
                "location": sorted(locations),
                "status": sorted(statuses),
                "department": sorted(departments),
            }

    return page_data_cache_get(cache_key, _build)


def _apply_search(rows: list[dict[str, Any]], search: str) -> list[dict[str, Any]]:
    query = str(search or "").strip()
    if not query:
        return rows
    ql = query.lower()
    return [
        r
        for r in rows
        if ql in str(r.get("asset_number") or r.get("asset_id") or "").lower()
        or ql in str(r.get("asset_name") or r.get("name") or "").lower()
        or ql in _asset_category(r).lower()
        or ql in _asset_location(r).lower()
        or ql in _asset_department(r).lower()
        or ql in normalize_asset_status(r.get("status")).lower()
    ]


def _equipment_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "total": len(rows),
        "available": 0,
        "checked_out": 0,
        "out_for_repair": 0,
        "service_due": 0,
    }
    for row in rows:
        status = normalize_asset_status(row.get("status"))
        if status in ("Available", "In Service"):
            counts["available"] += 1
        elif status in ("Checked Out", "Assigned"):
            counts["checked_out"] += 1
        elif status == "Out for Repair":
            counts["out_for_repair"] += 1
        if status == "Maintenance Due":
            counts["service_due"] += 1
    return counts


def list_equipment_page(
    *,
    search: str = "",
    statuses: list[str] | None = None,
    categories: list[str] | None = None,
    locations: list[str] | None = None,
    departments: list[str] | None = None,
    page: int = 1,
    page_size: int = 25,
) -> AssetsDirectoryPage:
    from app.perf_debug import perf_span

    pg = max(1, int(page or 1))
    size = max(1, min(200, int(page_size or 25)))

    with perf_span("assets.equipment.list_query"):
        catalog, is_live = _load_equipment_catalog()
        filter_options = load_equipment_filter_options()
        filtered = _apply_search(catalog, search)
        status_val = statuses[0] if statuses and len(statuses) == 1 else None
        if status_val and str(status_val).strip() not in {"", "All Statuses"}:
            wanted = normalize_asset_status(status_val)
            filtered = [r for r in filtered if normalize_asset_status(r.get("status")) == wanted]
        if categories:
            wanted_cats = {str(c).strip() for c in categories if str(c).strip()}
            if wanted_cats:
                filtered = [r for r in filtered if _asset_category(r) in wanted_cats]
        if locations:
            wanted_locs = {str(v).strip() for v in locations if str(v).strip()}
            if wanted_locs:
                filtered = [r for r in filtered if _asset_location(r) in wanted_locs]
        if departments:
            wanted_depts = {str(v).strip() for v in departments if str(v).strip()}
            if wanted_depts:
                filtered = [r for r in filtered if _asset_department(r) in wanted_depts]
        filtered = apply_column_filters(filtered, _EQUIPMENT_TABLE_KEY, _COLUMN_FILTER_SPECS)
        summary = _equipment_summary(filtered)
        total = len(filtered)
        start = (pg - 1) * size
        page_rows = filtered[start : start + size]
        return AssetsDirectoryPage(
            rows=page_rows,
            total_count=total,
            page=pg,
            page_size=size,
            filter_options=filter_options,
            summary=summary,
            is_live=is_live,
            warning=None,
        )


def invalidate_assets_directory_cache() -> None:
    clear_page_data_cache_prefix(_EQUIPMENT_DIR_PREFIX)
    clear_page_data_cache_prefix(_EQUIPMENT_FILTER_PREFIX)


__all__ = [
    "AssetsDirectoryPage",
    "invalidate_assets_directory_cache",
    "list_equipment_page",
    "load_equipment_filter_options",
]
