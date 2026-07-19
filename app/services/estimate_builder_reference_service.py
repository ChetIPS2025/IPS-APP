"""Focused searchable reference options for Estimate Cost Builder."""

from __future__ import annotations

from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.estimate_builder_helpers import (
    DEFAULT_LABOR_RATES,
    OT_MULTIPLIER,
    TRAVEL_DEFAULTS,
    _dedupe_label,
    filter_pricing_option_labels,
    get_labor_rate_options,
)


def _pricing_guide_version() -> int:
    try:
        from app.pages._core._data import pricing_guide_catalog_data_version

        return pricing_guide_catalog_data_version()
    except ImportError:
        return 0


def _assets_version() -> int:
    try:
        from app.pages._core._data import assets_catalog_data_version

        return assets_catalog_data_version()
    except ImportError:
        return 0


def _labor_rates_version() -> int:
    try:
        from app.services.labor_rates_service import list_labor_rates

        return len(list_labor_rates())
    except Exception:
        return 0


def _company_settings_version() -> int:
    try:
        from app.services.company_settings_service import load_app_settings

        row = load_app_settings()
        return 1 if row.get("from_db") else 0
    except Exception:
        return 0


def _match_query(*parts: str, search: str) -> bool:
    query = str(search or "").strip().casefold()
    if not query:
        return True
    hay = " ".join(str(p or "") for p in parts).casefold()
    return query in hay


_CUSTOM_MATERIAL_LABEL = "— Custom item —"


def search_estimate_material_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, Any]]:
    from app.perf_debug import perf_span

    version = _pricing_guide_version()
    cache_key = f"ecb_mat_opts:{version}:{search}:{limit}"

    def _build() -> list[dict[str, Any]]:
        with perf_span("estimate_builder.materials.options"):
            from app.services.pricing_guide_service import (
                cached_pricing_guide_rows,
                pricing_item_to_estimate_option,
            )

            seen: dict[str, int] = {}
            out: list[dict[str, Any]] = []
            for row in cached_pricing_guide_rows(include_inactive=False):
                if row.get("is_active") is False:
                    continue
                opt = pricing_item_to_estimate_option(row)
                base_label = f"{opt['description']} — {opt.get('item_type') or 'Material'}"
                label = _dedupe_label(base_label, seen, str(opt.get("item_type") or ""))
                if not _match_query(
                    label,
                    opt.get("description"),
                    opt.get("sku"),
                    opt.get("category"),
                    search=search,
                ):
                    continue
                out.append(
                    {
                        "pricing_item_id": str(opt.get("id") or ""),
                        "inventory_item_id": str(opt.get("inventory_item_id") or "") or None,
                        "description": str(opt.get("description") or label),
                        "sku": str(opt.get("sku") or ""),
                        "category": str(opt.get("category") or ""),
                        "unit": str(opt.get("unit") or "EA"),
                        "unit_cost": float(opt.get("unit_cost") or 0),
                        "markup_pct": float(opt.get("markup_pct") or 0),
                        "taxable": bool(opt.get("taxable", True)),
                        "vendor_id": opt.get("vendor_id"),
                        "vendor": str(opt.get("vendor") or opt.get("vendor_name") or ""),
                        "item_type": str(opt.get("item_type") or "Material"),
                        "label": label,
                    }
                )
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def material_option_labels(
    *,
    search: str = "",
    limit: int = 100,
    selected_label: str = "",
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    rows = search_estimate_material_options(search=search, limit=limit)
    labels = [_CUSTOM_MATERIAL_LABEL] + [str(r.get("label") or "") for r in rows if r.get("label")]
    label_map = {str(r.get("label") or ""): r for r in rows if r.get("label")}
    sel = str(selected_label or "").strip()
    if sel and sel not in label_map and sel != _CUSTOM_MATERIAL_LABEL:
        labels = [sel, *labels]
    return labels, label_map


def search_rentable_asset_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, Any]]:
    from app.perf_debug import perf_span

    version = _assets_version()
    cache_key = f"ecb_asset_opts:{version}:{search}:{limit}"

    def _build() -> list[dict[str, Any]]:
        with perf_span("estimate_builder.equipment.options"):
            from app.pages._core._data import load_assets
            from app.services.asset_rental_service import normalize_rental_rate_unit
            from app.services.phase2_modules_service import asset_is_rentable

            seen: dict[str, int] = {}
            out: list[dict[str, Any]] = []
            for row in load_assets():
                if not asset_is_rentable(row):
                    continue
                asset_name = str(row.get("asset_name") or row.get("name") or "").strip()
                asset_number = str(row.get("asset_number") or "").strip()
                category = str(row.get("category") or row.get("asset_type") or "").strip()
                if not asset_name:
                    continue
                suffix = category if category and category != "—" else "Equipment"
                label = _dedupe_label(asset_name, seen, suffix)
                if not _match_query(label, asset_name, asset_number, category, search=search):
                    continue
                rental_daily = float(row.get("rental_daily_rate") or row.get("daily_rate") or 0)
                rental_weekly = float(row.get("rental_weekly_rate") or row.get("weekly_rate") or 0)
                hourly = float(row.get("hourly_rate") or 0)
                out.append(
                    {
                        "id": str(row.get("id") or ""),
                        "asset_number": asset_number,
                        "asset_name": asset_name,
                        "category": category,
                        "rental_rate": rental_daily or hourly or rental_weekly,
                        "rental_rate_unit": normalize_rental_rate_unit(row.get("rental_rate_unit")),
                        "default_markup": float(row.get("rental_default_markup_percent") or 0),
                        "hourly_rate": hourly,
                        "daily_rate": rental_daily,
                        "weekly_rate": rental_weekly,
                        "label": label,
                    }
                )
                if len(out) >= limit:
                    break
            return out

    return page_data_cache_get(cache_key, _build)


def search_active_vendor_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, str]]:
    from app.perf_debug import perf_span
    from app.services.estimate_reference_service import search_vendor_estimate_options

    with perf_span("estimate_builder.subcontractors.options"):
        names = search_vendor_estimate_options(search=search, limit=limit)
        return [{"id": name, "label": name} for name in names]


def cached_labor_options_as_select() -> list[tuple[str, dict[str, Any]]]:
    version = _labor_rates_version()

    def _build() -> list[tuple[str, dict[str, Any]]]:
        opts = get_labor_rate_options()
        return [(str(o.get("label") or o.get("role_name") or ""), o) for o in opts]

    return page_data_cache_get(f"ecb_labor_opts:{version}", _build)


def cached_travel_defaults() -> dict[str, float]:
    version = _company_settings_version()

    def _build() -> dict[str, float]:
        return dict(TRAVEL_DEFAULTS)

    return page_data_cache_get(f"ecb_travel_defaults:{version}", _build)


def invalidate_labor_options_cache() -> None:
    try:
        from app.pages._core.page_data_cache import clear_page_data_cache_prefix

        clear_page_data_cache_prefix("ecb_labor_opts:")
    except Exception:
        pass


__all__ = [
    "DEFAULT_LABOR_RATES",
    "OT_MULTIPLIER",
    "_CUSTOM_MATERIAL_LABEL",
    "cached_labor_options_as_select",
    "cached_travel_defaults",
    "filter_pricing_option_labels",
    "invalidate_labor_options_cache",
    "material_option_labels",
    "search_active_vendor_options",
    "search_estimate_material_options",
    "search_rentable_asset_options",
]
