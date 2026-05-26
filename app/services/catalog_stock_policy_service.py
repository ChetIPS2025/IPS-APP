"""Pricing guide stock policy — mandatory vs optional inventory tracking."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from app.services.inventory_service import clear_inventory_cache, get_inventory_item
    from app.services.pricing_guide_service import clear_pricing_guide_cache
    from app.services.repository import ServiceResult
except ImportError:
    from services.inventory_service import clear_inventory_cache, get_inventory_item  # type: ignore
    from services.pricing_guide_service import clear_pricing_guide_cache  # type: ignore
    from services.repository import ServiceResult  # type: ignore

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
    "enrich_inventory_rows",
    "inventory_needs_reorder",
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


def _inventory_qty(row: dict[str, Any]) -> float:
    for key in ("qty_on_hand", "quantity_on_hand", "quantity"):
        val = row.get(key)
        if val is not None and str(val).strip() != "":
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return 0.0


def _reorder_point(row: dict[str, Any]) -> float:
    try:
        return float(row.get("reorder_point") or row.get("default_reorder_point") or 0)
    except (TypeError, ValueError):
        return 0.0


def pricing_guide_lookup_maps() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Return (by_inventory_id, by_pricing_id) maps for linked pricing rows."""
    try:
        from app.services.pricing_guide_service import cached_pricing_guide_rows
    except ImportError:
        from services.pricing_guide_service import cached_pricing_guide_rows  # type: ignore

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
        enriched.append(item)
    return enriched


def inventory_needs_reorder(row: dict[str, Any]) -> bool:
    if normalize_stock_policy(row.get("stock_policy")) != "mandatory":
        return False
    qty = _inventory_qty(row)
    rp = _reorder_point(row)
    return qty <= rp


def passes_inventory_view_filter(row: dict[str, Any], *, view: str) -> bool:
    view_s = str(view or "In stock").strip()
    qty = _inventory_qty(row)
    if view_s == "All tracked":
        return True
    if view_s == "Needs reorder":
        return inventory_needs_reorder(row)
    if view_s == "Zero stock":
        return qty <= 0
    return qty > 0


def apply_pricing_stock_settings_to_inventory(pg_row: dict[str, Any]) -> ServiceResult:
    """Copy default reorder point to the linked inventory row."""
    inv_id = _linked_inventory_id(pg_row)
    if not inv_id:
        return ServiceResult(ok=True, data={"skipped": True})
    inv = get_inventory_item(inv_id)
    if not inv:
        return ServiceResult(ok=True, data={"skipped": True})
    try:
        from app.db import update_rows_admin
    except ImportError:
        from db import update_rows_admin  # type: ignore
    rp = float(pg_row.get("default_reorder_point") or 0)
    try:
        update_rows_admin(
            "inventory_items",
            {"reorder_point": rp, "updated_at": _now_iso()},
            {"id": inv_id},
        )
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))
    clear_inventory_cache()
    return ServiceResult(ok=True, data={"inventory_id": inv_id, "reorder_point": rp})


def sync_linked_inventory_reorder(pricing_item_id: str) -> ServiceResult:
    pid = str(pricing_item_id or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing pricing item id.")
    try:
        from app.services.pricing_guide_service import cached_pricing_guide_rows
    except ImportError:
        from services.pricing_guide_service import cached_pricing_guide_rows  # type: ignore
    row = next(
        (r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id") or "") == pid),
        None,
    )
    if not row:
        return ServiceResult(ok=False, error="Pricing item not found.")
    return apply_pricing_stock_settings_to_inventory(row)


def save_pricing_stock_settings(
    pg_row: dict[str, Any],
    *,
    stock_policy: str,
    default_reorder_point: float,
    ensure_inventory: bool = True,
) -> ServiceResult:
    """Persist stock policy on pricing guide and sync linked inventory."""
    pid = str(pg_row.get("id") or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing pricing item id.")

    policy = normalize_stock_policy(stock_policy)
    try:
        rp = max(float(default_reorder_point or 0), 0.0)
    except (TypeError, ValueError):
        rp = 0.0

    try:
        from app.db import update_rows_admin
    except ImportError:
        from db import update_rows_admin  # type: ignore

    try:
        update_rows_admin(
            "pricing_guide_items",
            {
                "stock_policy": policy,
                "default_reorder_point": rp,
                "updated_at": _now_iso(),
            },
            {"id": pid},
        )
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))

    clear_pricing_guide_cache()

    try:
        from app.services.pricing_guide_service import cached_pricing_guide_rows
    except ImportError:
        from services.pricing_guide_service import cached_pricing_guide_rows  # type: ignore
    fresh = next(
        (r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id") or "") == pid),
        {**pg_row, "stock_policy": policy, "default_reorder_point": rp},
    )

    messages: list[str] = ["Stock policy saved."]

    if policy == "mandatory" and ensure_inventory and not _linked_inventory_id(fresh):
        try:
            from app.services.catalog_presence_service import apply_catalog_presence, resolve_catalog_presence
        except ImportError:
            from services.catalog_presence_service import apply_catalog_presence, resolve_catalog_presence  # type: ignore
        presence = resolve_catalog_presence(fresh)
        result = apply_catalog_presence(
            fresh,
            pricing_guide=bool(presence.get("pricing_guide")),
            inventory=True,
            assets=bool(presence.get("assets")),
        )
        if not result.ok:
            return result
        messages.append("Inventory record created for mandatory item.")
        fresh = next(
            (r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id") or "") == pid),
            fresh,
        )

    if policy in {"mandatory", "optional"} and _linked_inventory_id(fresh):
        sync_result = apply_pricing_stock_settings_to_inventory({**fresh, "default_reorder_point": rp})
        if not sync_result.ok:
            return sync_result
        if policy == "mandatory" and rp > 0:
            messages.append(f"Reorder point set to {rp:g} on linked inventory.")

    return ServiceResult(ok=True, data={"message": " ".join(messages)})
