from __future__ import annotations

import re
from typing import Any, Callable

# Canonical inventory category for estimate / quote “materials” lines.
INVENTORY_MATERIALS_CATEGORY = "Materials"


def _norm_cat(val: Any) -> str:
    return str(val or "").strip().lower()


def is_inventory_materials_category(row: dict[str, Any]) -> bool:
    return _norm_cat(row.get("category")) == _norm_cat(INVENTORY_MATERIALS_CATEGORY)


def _item_key_from_inventory_row(row: dict[str, Any]) -> str:
    sku = str(row.get("sku") or "").strip()
    if sku:
        return sku
    name = str(row.get("item_name") or "").strip()
    base = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")
    return base or str(row.get("id") or "")[:12].upper()


def item_key_from_inventory_row(row: dict[str, Any]) -> str:
    """Public alias for catalog / import code."""
    return _item_key_from_inventory_row(row)


def estimate_materials_payload_from_inventory(
    row: dict[str, Any],
    *,
    item_key: str | None = None,
) -> dict[str, Any]:
    """
    Map ``inventory_items`` → column payload for ``estimate_materials`` insert/update.

    Preserves inventory **category** when set; otherwise ``Quote Catalog``.
    ``inventory_ref_id`` is always the inventory row id (UUID string).
    """
    pc = float(row.get("unit_cost") or 0)
    raw_sell = row.get("sell_price")
    if raw_sell is not None and str(raw_sell).strip() != "":
        try:
            sp = float(raw_sell)
        except (TypeError, ValueError):
            sp = round(pc * 1.25, 2) if pc else 0.0
    else:
        sp = round(pc * 1.25, 2) if pc else 0.0

    ik = (item_key or _item_key_from_inventory_row(row)).strip()
    desc = str(row.get("item_name") or "").strip() or str(row.get("sku") or "").strip() or ik
    cat = str(row.get("category") or "").strip() or "Pricing Guide"
    iid = str(row.get("id") or "").strip()

    return {
        "item_key": ik[:500],
        "description": desc[:2000],
        "category": cat[:200],
        "subgroup": str(row.get("subgroup") or "")[:500],
        "unit": str(row.get("unit") or "EA").strip()[:32] or "EA",
        "purchase_price": float(pc),
        "sell_price": float(sp),
        "vendor_item_number": str(row.get("vendor_item_number") or "")[:200],
        "is_active": True,
        "inventory_ref_id": iid or None,
    }


def inventory_row_to_material_catalog_shape(row: dict[str, Any]) -> dict[str, Any]:
    """
    Map ``inventory_items`` → shape expected by estimate ``compute_totals`` / material quote matching.

    ``sell_price`` is optional on inventory; when missing, uses 25% markup over ``unit_cost`` (legacy catalog default).
    """
    pc = float(row.get("unit_cost") or 0)
    raw_sell = row.get("sell_price")
    if raw_sell is not None and str(raw_sell).strip() != "":
        try:
            sp = float(raw_sell)
        except (TypeError, ValueError):
            sp = round(pc * 1.25, 2) if pc else 0.0
    else:
        sp = round(pc * 1.25, 2) if pc else 0.0

    qr = str(row.get("qr_code_value") or "").strip()
    inv_display = qr if qr.upper().startswith("INV-") else ""

    return {
        "id": row.get("id"),
        "item_key": _item_key_from_inventory_row(row),
        "description": str(row.get("item_name") or "").strip(),
        "category": INVENTORY_MATERIALS_CATEGORY,
        "subgroup": str(row.get("subgroup") or "").strip(),
        "unit": str(row.get("unit") or "EA").strip() or "EA",
        "purchase_price": pc,
        "sell_price": sp,
        "vendor_item_number": str(row.get("vendor_item_number") or "").strip(),
        "inventory_id": inv_display,
        "is_active": bool(row.get("is_active", True)),
        "_source": "inventory_items",
    }


def fetch_merged_materials_catalog_rows(
    *,
    fetch_table: Callable[..., list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """
    Legacy merge of inventory **Materials** rows plus non-colliding ``materials_catalog`` keys.

    **Estimates / editor** use ``estimate_materials`` only (see ``estimate_materials_catalog``).
    Kept for scripts or imports that still expect a merged list.
    """
    inv_rows: list[dict[str, Any]] = []
    try:
        inv_rows = fetch_table("inventory_items", limit=5000, order_by="item_name")
    except Exception:
        inv_rows = []

    from_inv = [inventory_row_to_material_catalog_shape(r) for r in inv_rows if is_inventory_materials_category(r)]
    seen_keys = {str(x.get("item_key") or "").strip().upper() for x in from_inv if str(x.get("item_key") or "").strip()}

    legacy: list[dict[str, Any]] = []
    try:
        legacy = fetch_table("materials_catalog", limit=5000, order_by="item_key")
    except Exception:
        legacy = []

    out: list[dict[str, Any]] = list(from_inv)
    for m in legacy:
        if not isinstance(m, dict):
            continue
        k = str(m.get("item_key") or "").strip().upper()
        if k and k in seen_keys:
            continue
        if k:
            seen_keys.add(k)
        row = {**m, "_source": "materials_catalog"}
        out.append(row)
    return out
