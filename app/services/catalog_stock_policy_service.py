"""Pricing guide stock policy — mandatory vs optional inventory tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.inventory_service import clear_inventory_cache, get_inventory_item
from app.services.pricing_guide_service import clear_pricing_guide_cache
from app.services.repository import ServiceResult
STOCK_POLICIES: tuple[str, ...] = ("none", "optional", "mandatory")
STOCK_POLICY_LABELS: dict[str, str] = {
    "none": "Not stocked",
    "optional": "Optional (extras only)",
    "mandatory": "Mandatory (reorder when low)",
}
INVENTORY_VIEW_FILTERS: tuple[str, ...] = (
    "In stock",
    "All tracked",
    "Needs reorder",
    "Zero stock",
)

__all__ = [
    "INVENTORY_VIEW_FILTERS",
    "STOCK_POLICIES",
    "STOCK_POLICY_LABELS",
    "apply_pricing_stock_settings_to_inventory",
    "derive_inventory_stock_status",
    "enrich_inventory_rows",
    "load_enriched_inventory_rows",
    "inventory_needs_reorder",
    "inventory_status_fields_for_qty",
    "linked_inventory_quantity",
    "normalize_stock_policy",
    "passes_inventory_view_filter",
    "pricing_guide_lookup_maps",
    "save_pricing_stock_settings",
    "stock_policy_label",
    "sync_linked_inventory_reorder",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_stock_policy(raw: object) -> str:
    val = str(raw or "").strip().lower()
    if val in STOCK_POLICIES:
        return val
    return "none"


def stock_policy_label(policy: object) -> str:
    return STOCK_POLICY_LABELS.get(normalize_stock_policy(policy), STOCK_POLICY_LABELS["none"])


def _linked_inventory_id(row: dict[str, Any]) -> str:
    return str(row.get("linked_inventory_id") or row.get("inventory_item_id") or "").strip()


def _inventory_qty(row: dict[str, Any]) -> int:
    from app.utils.inventory_quantity import read_inventory_quantity
    return read_inventory_quantity(row, "qty_on_hand", "quantity_on_hand", "quantity")


def _reorder_point(row: dict[str, Any]) -> int:
    from app.utils.inventory_quantity import parse_inventory_quantity
    try:
        return parse_inventory_quantity(
            row.get("reorder_point") if row.get("reorder_point") is not None else row.get("default_reorder_point"),
            allow_zero=True,
            field_name="Reorder point",
        )
    except ValueError:
        return 0


def _parse_reorder_point(value: Any) -> tuple[int, str | None]:
    from app.utils.inventory_quantity import try_parse_inventory_quantity
    return try_parse_inventory_quantity(value, allow_zero=True, field_name="Reorder point")


def pricing_guide_lookup_maps() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return (by_inventory_id, by_pricing_id) maps for linked pricing rows."""
    from app.services.pricing_guide_service import cached_pricing_guide_rows
    by_inv: dict[str, dict[str, Any]] = {}
    by_pg: dict[str, dict[str, Any]] = {}
    for row in cached_pricing_guide_rows(include_inactive=True):
        pid = str(row.get("id") or "").strip()
        if pid:
            by_pg[pid] = row
        inv_id = _linked_inventory_id(row)
        if inv_id:
            by_inv[inv_id] = row
    return by_inv, by_pg


def enrich_inventory_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from app.perf_debug import perf_span
    with perf_span("inventory.enrich_rows"):
        return _enrich_inventory_rows_impl(rows)


def load_enriched_inventory_rows() -> list[dict[str, Any]]:
    from app.pages._core._data import load_inventory
    from app.pages._core.page_data_cache import page_data_cache_get

    return page_data_cache_get(
        "inventory_enriched_rows",
        lambda: enrich_inventory_rows(load_inventory()),
    )


def _enrich_inventory_rows_impl(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_inv, by_pg = pricing_guide_lookup_maps()
    enriched: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        pg = by_inv.get(str(item.get("id") or "").strip())
        if pg is None:
            pg_id = str(item.get("pricing_guide_id") or item.get("pricing_item_id") or "").strip()
            pg = by_pg.get(pg_id) if pg_id else None
        policy = normalize_stock_policy(pg.get("stock_policy") if pg else "none")
        default_rp = float(pg.get("default_reorder_point") or 0) if pg else 0.0
        item["stock_policy"] = policy
        item["stock_policy_label"] = stock_policy_label(policy)
        item["default_reorder_point"] = default_rp
        if pg:
            item["pricing_item_code"] = str(pg.get("item_code") or pg.get("sku") or "")
        item["status"] = derive_inventory_stock_status(item)
        enriched.append(item)
    return enriched


def inventory_needs_reorder(row: dict[str, Any]) -> bool:
    if normalize_stock_policy(row.get("stock_policy")) != "mandatory":
        return False
    qty = _inventory_qty(row)
    rp = _reorder_point(row)
    return qty <= rp


def _inventory_row_discontinued(row: dict[str, Any]) -> bool:
    if row.get("is_active") is False:
        return True
    status = str(row.get("status") or "").strip().lower().replace("_", " ")
    return status in {"discontinued", "inactive"}


def derive_inventory_stock_status(row: dict[str, Any]) -> str:
    """Derive display status from on-hand quantity and reorder policy."""
    if _inventory_row_discontinued(row):
        return "Discontinued"
    qty = _inventory_qty(row)
    if qty <= 0:
        return "Out of Stock"
    if inventory_needs_reorder(row):
        return "Needs Reorder"
    rp = _reorder_point(row)
    if rp > 0 and qty <= rp:
        return "Low Stock"
    return "In Stock"


def inventory_status_fields_for_qty(row: dict[str, Any], new_qty: float | int) -> dict[str, Any]:
    """Return inventory_items fields to persist after a quantity change."""
    from app.utils.inventory_quantity import parse_inventory_quantity
    qty_int = parse_inventory_quantity(new_qty, allow_negative=True, allow_zero=True)
    patched = dict(row)
    patched["quantity_on_hand"] = qty_int
    patched["qty_on_hand"] = qty_int
    return {"status": derive_inventory_stock_status(patched)}


def passes_inventory_view_filter(row: dict[str, Any], *, view: str) -> bool:
    view_s = str(view or "In stock").strip()
    qty = _inventory_qty(row)
    if view_s == "All tracked":
        return True
    if view_s == "Needs reorder":
        return inventory_needs_reorder(row)
    if view_s == "Zero stock":
        return qty <= 0
    # In stock — active catalog items remain visible even at zero on-hand.
    return not _inventory_row_discontinued(row)


def apply_pricing_stock_settings_to_inventory(pg_row: dict[str, Any]) -> ServiceResult:
    """Copy default reorder point to the linked inventory row."""
    inv_id = _linked_inventory_id(pg_row)
    if not inv_id:
        return ServiceResult(ok=True, data={"skipped": True})
    inv = get_inventory_item(inv_id)
    if not inv:
        return ServiceResult(ok=True, data={"skipped": True})
    from app.services.repository import update_row_admin
    rp, rp_err = _parse_reorder_point(pg_row.get("default_reorder_point"))
    if rp_err:
        return ServiceResult(ok=False, error=rp_err)
    res = update_row_admin(
        "inventory_items",
        {"reorder_point": rp, "updated_at": _now_iso()},
        {"id": inv_id},
    )
    if not res.ok:
        return ServiceResult(ok=False, error=res.error or str(res.error))
    clear_inventory_cache()
    return ServiceResult(ok=True, data={"inventory_id": inv_id, "reorder_point": rp})


def sync_linked_inventory_reorder(pricing_item_id: str) -> ServiceResult:
    pid = str(pricing_item_id or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing pricing item id.")
    from app.services.pricing_guide_service import cached_pricing_guide_rows
    row = next(
        (r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id") or "") == pid),
        None,
    )
    if not row:
        return ServiceResult(ok=False, error="Pricing item not found.")
    return apply_pricing_stock_settings_to_inventory(row)


def _linked_inventory_quantity(pg_row: dict[str, Any]) -> int:
    """Current on-hand qty for the pricing item's linked inventory row, if any."""
    inv_id = _linked_inventory_id(pg_row)
    if not inv_id:
        return 0
    inv = get_inventory_item(inv_id)
    return _inventory_qty(inv) if inv else 0


def linked_inventory_quantity(pg_row: dict[str, Any]) -> int:
    """Public alias for reading linked inventory on-hand quantity."""
    return _linked_inventory_quantity(pg_row)


def _ensure_inventory_link_for_policy(
    row: dict[str, Any],
    *,
    policy: str,
    quantity_on_hand: float | None,
) -> tuple[dict[str, Any], list[str], ServiceResult | None]:
    """Create linked inventory when mandatory, or optional with qty > 0."""
    fresh = row
    messages: list[str] = []
    if policy == "none" or _linked_inventory_id(fresh):
        return fresh, messages, None

    qty = 0
    if quantity_on_hand is not None:
        from app.utils.inventory_quantity import try_parse_inventory_quantity
        qty, qty_err = try_parse_inventory_quantity(
            quantity_on_hand,
            allow_zero=True,
            field_name="Quantity on hand",
        )
        if qty_err:
            return fresh, messages, ServiceResult(ok=False, error=qty_err)
    should_create = policy == "mandatory" or (policy == "optional" and (qty or 0) > 0)
    if not should_create:
        return fresh, messages, None

    from app.services.catalog_presence_service import apply_catalog_presence, resolve_catalog_presence
    presence = resolve_catalog_presence(fresh)
    result = apply_catalog_presence(
        fresh,
        pricing_guide=bool(presence.get("pricing_guide")),
        inventory=True,
        assets=bool(presence.get("assets")),
    )
    if not result.ok:
        return fresh, messages, result

    from app.services.pricing_guide_service import cached_pricing_guide_rows
    pid = str(fresh.get("id") or "").strip()
    fresh = next(
        (r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id") or "") == pid),
        fresh,
    )
    label = "mandatory" if policy == "mandatory" else "optional extras"
    messages.append(f"Inventory record created for {label} item.")
    return fresh, messages, None


def _apply_quantity_on_hand_to_inventory(
    pg_row: dict[str, Any],
    quantity_on_hand: int,
) -> tuple[list[str], ServiceResult | None]:
    """Set linked inventory quantity; records an adjustment transaction when qty changes."""
    inv_id = _linked_inventory_id(pg_row)
    if not inv_id:
        return [], None

    inv = get_inventory_item(inv_id)
    if not inv:
        return [], ServiceResult(ok=False, error="Linked inventory item not found.")

    new_qty = max(int(quantity_on_hand or 0), 0)
    prev_qty = _inventory_qty(inv)
    if new_qty == prev_qty:
        return [], None

    delta = new_qty - prev_qty
    if delta == 0:
        return [], None

    from app.services.inventory_service import record_inventory_transaction
    txn = record_inventory_transaction(
        {
            "inventory_id": inv_id,
            "transaction_type": "adjustment",
            "quantity": abs(delta),
            "signed_quantity": delta,
            "notes": "Quantity updated from Pricing Guide stock policy",
            "source": "pricing_guide",
        }
    )
    if not txn.ok:
        from app.services.repository import update_row_admin
        res = update_row_admin(
            "inventory_items",
            {
                "quantity_on_hand": new_qty,
                "qty_on_hand": new_qty,
                "updated_at": _now_iso(),
                **inventory_status_fields_for_qty(inv, new_qty),
            },
            {"id": inv_id},
        )
        if not res.ok:
            return [], ServiceResult(ok=False, error=txn.error or res.error or "Could not update quantity.")
        clear_inventory_cache()
    else:
        clear_inventory_cache()

    return [f"Quantity on hand set to {new_qty}."], None


def save_pricing_stock_settings(
    pg_row: dict[str, Any],
    *,
    stock_policy: str,
    default_reorder_point: float | int,
    quantity_on_hand: float | int | None = None,
    ensure_inventory: bool = True,
) -> ServiceResult:
    """Persist stock policy on pricing guide and sync linked inventory."""
    pid = str(pg_row.get("id") or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing pricing item id.")

    policy = normalize_stock_policy(stock_policy)
    rp, rp_err = _parse_reorder_point(default_reorder_point)
    if rp_err:
        return ServiceResult(ok=False, error=rp_err)

    from app.services.repository import update_row_admin
    res = update_row_admin(
        "pricing_guide_items",
        {
            "stock_policy": policy,
            "default_reorder_point": rp,
            "updated_at": _now_iso(),
        },
        {"id": pid},
    )
    if not res.ok:
        return ServiceResult(ok=False, error=res.error or "Could not save stock policy.")

    clear_pricing_guide_cache()

    from app.services.pricing_guide_service import cached_pricing_guide_rows
    fresh = next(
        (r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id") or "") == pid),
        {**pg_row, "stock_policy": policy, "default_reorder_point": rp},
    )

    messages: list[str] = ["Stock policy saved."]

    qty_value: int | None = None
    if policy in {"mandatory", "optional"} and quantity_on_hand is not None:
        from app.utils.inventory_quantity import try_parse_inventory_quantity
        qty_value, qty_err = try_parse_inventory_quantity(
            quantity_on_hand,
            allow_zero=True,
            field_name="Quantity on hand",
        )
        if qty_err:
            return ServiceResult(ok=False, error=qty_err)
        qty_value = max(qty_value or 0, 0)

    if ensure_inventory and policy in {"mandatory", "optional"}:
        fresh, ensure_msgs, ensure_err = _ensure_inventory_link_for_policy(
            fresh,
            policy=policy,
            quantity_on_hand=qty_value,
        )
        if ensure_err is not None:
            return ensure_err
        messages.extend(ensure_msgs)

    if policy in {"mandatory", "optional"} and _linked_inventory_id(fresh):
        sync_result = apply_pricing_stock_settings_to_inventory({**fresh, "default_reorder_point": rp})
        if not sync_result.ok:
            return sync_result
        if policy == "mandatory" and rp > 0:
            messages.append(f"Reorder point set to {rp} on linked inventory.")

        if qty_value is not None:
            qty_msgs, qty_err = _apply_quantity_on_hand_to_inventory(fresh, qty_value)
            if qty_err is not None:
                return qty_err
            messages.extend(qty_msgs)

    return ServiceResult(ok=True, data={"message": " ".join(messages)})
