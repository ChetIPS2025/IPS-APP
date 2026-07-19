"""Focused Inventory / Pricing Guide search for Estimate Materials takeoff."""

from __future__ import annotations

from typing import Any, Callable

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.estimate_builder_helpers import _dedupe_label

_CUSTOM_INVENTORY_LABEL = "— Custom item —"


def _pricing_guide_version() -> int:
    try:
        from app.pages._core._data import pricing_guide_catalog_data_version

        return pricing_guide_catalog_data_version()
    except ImportError:
        return 0


def _inventory_catalog_version() -> int:
    try:
        from app.pages._core._data import inventory_catalog_data_version

        return inventory_catalog_data_version()
    except ImportError:
        return 0


def _match_query(*parts: str, search: str) -> bool:
    query = str(search or "").strip().casefold()
    if not query:
        return True
    hay = " ".join(str(p or "") for p in parts).casefold()
    return query in hay


def _option_id(*, pricing_item_id: str = "", inventory_item_id: str = "") -> str:
    pid = str(pricing_item_id or "").strip()
    iid = str(inventory_item_id or "").strip()
    if pid:
        return f"pg:{pid}"
    if iid:
        return f"inv:{iid}"
    return ""


def search_estimate_inventory_options(
    *,
    search: str = "",
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return capped inventory/pricing options for material takeoff search."""
    from app.perf_debug import perf_span

    pg_ver = _pricing_guide_version()
    inv_ver = _inventory_catalog_version()
    cache_key = f"est_mat_inv_opts:{pg_ver}:{inv_ver}:{search}:{limit}"

    def _build() -> list[dict[str, Any]]:
        with perf_span("estimate_materials.inventory_search"):
            from app.services.pricing_guide_service import (
                cached_pricing_guide_rows,
                pricing_item_to_estimate_option,
            )
            from app.services.repository import fetch_rows

            seen: dict[str, int] = {}
            out: list[dict[str, Any]] = []
            seen_ids: set[str] = set()

            for row in cached_pricing_guide_rows(include_inactive=False):
                if row.get("is_active") is False:
                    continue
                itype = str(row.get("item_type") or "").strip()
                if itype and itype.lower() not in {"material", "materials", ""}:
                    continue
                opt = pricing_item_to_estimate_option(row)
                pid = str(opt.get("pricing_item_id") or opt.get("id") or "").strip()
                iid = str(opt.get("inventory_item_id") or "").strip() or None
                oid = _option_id(pricing_item_id=pid, inventory_item_id=iid or "")
                if not oid or oid in seen_ids:
                    continue
                sku = str(opt.get("sku") or opt.get("item_number") or "—").strip()
                name = str(opt.get("description") or "Item").strip()
                base_label = f"{sku} — {name}" if sku and sku != "—" else name
                label = _dedupe_label(base_label, seen, sku or name)
                if not _match_query(label, sku, name, opt.get("category"), opt.get("vendor"), search=search):
                    continue
                seen_ids.add(oid)
                out.append(
                    {
                        "option_id": oid,
                        "pricing_item_id": pid or None,
                        "inventory_item_id": iid,
                        "sku": sku,
                        "item_number": sku,
                        "description": name,
                        "category": str(opt.get("category") or ""),
                        "unit": str(opt.get("unit") or "EA"),
                        "unit_cost": float(opt.get("unit_cost") or 0),
                        "markup_pct": float(opt.get("markup_pct") or 0),
                        "taxable": bool(opt.get("taxable", True)),
                        "vendor_id": opt.get("vendor_id"),
                        "vendor": str(opt.get("vendor") or opt.get("vendor_name") or ""),
                        "label": label,
                        "display_label": label,
                    }
                )
                if len(out) >= limit:
                    return out

            rows, err = fetch_rows("inventory_items", limit=min(400, limit * 4), order_by="item_name", alt_tables=("inventory",))
            if not err:
                for row in rows:
                    if row.get("is_deleted") or row.get("is_active") is False:
                        continue
                    iid = str(row.get("id") or "").strip()
                    if not iid:
                        continue
                    oid = _option_id(inventory_item_id=iid)
                    if oid in seen_ids:
                        continue
                    sku = str(row.get("sku") or row.get("item_code") or "—").strip()
                    name = str(row.get("item_name") or row.get("name") or "Item").strip()
                    base_label = f"{sku} — {name}" if sku and sku != "—" else name
                    label = _dedupe_label(base_label, seen, sku or iid[:8])
                    if not _match_query(label, sku, name, row.get("category"), row.get("vendor"), search=search):
                        continue
                    seen_ids.add(oid)
                    out.append(
                        {
                            "option_id": oid,
                            "pricing_item_id": None,
                            "inventory_item_id": iid,
                            "sku": sku,
                            "item_number": sku,
                            "description": name,
                            "category": str(row.get("category") or ""),
                            "unit": str(row.get("unit") or row.get("uom") or "EA"),
                            "unit_cost": float(row.get("unit_cost") or row.get("average_cost") or 0),
                            "markup_pct": 0.0,
                            "taxable": row.get("taxable") is not False,
                            "vendor_id": row.get("vendor_id"),
                            "vendor": str(row.get("vendor") or row.get("vendor_name") or ""),
                            "label": label,
                            "display_label": label,
                        }
                    )
                    if len(out) >= limit:
                        break
            return out

    return page_data_cache_get(cache_key, _build)


def inventory_option_labels(
    *,
    search: str = "",
    limit: int = 100,
    selected_option_id: str = "",
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    rows = search_estimate_inventory_options(search=search, limit=limit)
    labels = [_CUSTOM_INVENTORY_LABEL] + [str(r.get("option_id") or "") for r in rows if r.get("option_id")]
    label_map = {str(r.get("option_id") or ""): r for r in rows if r.get("option_id")}
    sel = str(selected_option_id or "").strip()
    if sel and sel not in label_map and sel != _CUSTOM_INVENTORY_LABEL:
        labels = [sel, *labels]
    return labels, label_map


def inventory_search_provider(
    *,
    limit: int = 100,
) -> Callable[[str], list[tuple[str, dict[str, Any]]]]:
    def _provider(query: str) -> list[tuple[str, dict[str, Any]]]:
        rows = search_estimate_inventory_options(search=query, limit=limit)
        return [(str(r.get("option_id") or ""), r) for r in rows if r.get("option_id")]

    return _provider


__all__ = [
    "_CUSTOM_INVENTORY_LABEL",
    "inventory_option_labels",
    "inventory_search_provider",
    "search_estimate_inventory_options",
]
