"""Resolve and apply which catalog tables a pricing guide item appears in."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    from app.services.assets_service import (
        clear_assets_cache,
        delete_asset_record,
        set_asset_include_in_pricing_guide,
    )
    from app.services.inventory_service import clear_inventory_cache, get_inventory_item
    from app.services.phase2_modules_service import delete_inventory_item
    from app.services.pricing_guide_service import (
        cached_pricing_guide_rows,
        clear_pricing_guide_cache,
        link_asset_to_pricing_item,
        link_inventory_to_pricing_item,
        slug_item_code,
    )
    from app.services.repository import ServiceResult
except ImportError:
    from services.assets_service import (  # type: ignore
        clear_assets_cache,
        delete_asset_record,
        set_asset_include_in_pricing_guide,
    )
    from services.inventory_service import clear_inventory_cache, get_inventory_item  # type: ignore
    from services.phase2_modules_service import delete_inventory_item  # type: ignore
    from services.pricing_guide_service import (  # type: ignore
        cached_pricing_guide_rows,
        clear_pricing_guide_cache,
        link_asset_to_pricing_item,
        link_inventory_to_pricing_item,
        slug_item_code,
    )
    from services.repository import ServiceResult  # type: ignore

__all__ = [
    "apply_catalog_presence",
    "resolve_catalog_presence",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _filter_table_payload(table: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from app.services.repository import filter_payload_to_table
    except ImportError:
        from services.repository import filter_payload_to_table  # type: ignore
    return filter_payload_to_table(table, payload)


def _admin_insert_row(table: str, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    try:
        from app.db import insert_row_admin
    except ImportError:
        from db import insert_row_admin  # type: ignore
    try:
        inserted = insert_row_admin(table, _filter_table_payload(table, payload))
        return inserted, None
    except Exception as exc:
        return None, str(exc)


def _linked_inventory_id(row: dict[str, Any]) -> str:
    return str(row.get("linked_inventory_id") or row.get("inventory_item_id") or "").strip()


def _linked_asset_id(row: dict[str, Any]) -> str:
    return str(row.get("linked_asset_id") or row.get("asset_id") or "").strip()


def _load_asset_row(asset_id: str) -> dict[str, Any] | None:
    aid = str(asset_id or "").strip()
    if not aid:
        return None
    try:
        from app.pages._core._data import load_assets
    except ImportError:
        from pages._core._data import load_assets  # type: ignore
    return next((r for r in load_assets() if str(r.get("id") or "") == aid), None)


def _fresh_pricing_row(pricing_item_id: str) -> dict[str, Any] | None:
    pid = str(pricing_item_id or "").strip()
    if not pid:
        return None
    return next(
        (r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id") or "") == pid),
        None,
    )


def resolve_catalog_presence(row: dict[str, Any]) -> dict[str, Any]:
    """Return current table membership for a pricing guide item."""
    inv_id = _linked_inventory_id(row)
    ast_id = _linked_asset_id(row)
    inv_row = get_inventory_item(inv_id) if inv_id else None
    ast_row = _load_asset_row(ast_id) if ast_id else None

    pg_active = row.get("is_active") is not False
    pg_visible = pg_active
    if ast_row is not None:
        pg_visible = pg_active and bool(ast_row.get("include_in_pricing_guide", True))

    return {
        "pricing_guide": pg_visible,
        "pricing_guide_active": pg_active,
        "inventory": inv_row is not None,
        "assets": ast_row is not None,
        "linked_inventory_id": str(inv_row.get("id") or "") if inv_row else "",
        "linked_asset_id": str(ast_row.get("id") or "") if ast_row else "",
        "inventory_label": str(inv_row.get("name") or inv_row.get("item_name") or "").strip() if inv_row else "",
        "asset_label": str(ast_row.get("asset_name") or ast_row.get("name") or "").strip() if ast_row else "",
    }


def _recompute_item_class(
    *,
    pricing_item_id: str,
    inventory_id: str | None,
    asset_id: str | None,
    update_rows_admin,
) -> None:
    inv_id = str(inventory_id or "").strip()
    ast_id = str(asset_id or "").strip()
    if inv_id and ast_id:
        item_class = "Non-Inventory"
    elif inv_id:
        item_class = "Inventory"
    elif ast_id:
        item_class = "Asset"
    else:
        item_class = "Non-Inventory"
    update_rows_admin(
        "pricing_guide_items",
        {
            "item_class": item_class,
            "inventory_item_id": inv_id or None,
            "linked_inventory_id": inv_id or None,
            "asset_id": ast_id or None,
            "linked_asset_id": ast_id or None,
            "updated_at": _now_iso(),
        },
        {"id": pricing_item_id},
    )


def _set_pricing_guide_visibility(row: dict[str, Any], *, visible: bool) -> ServiceResult:
    pid = str(row.get("id") or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing pricing item id.")
    try:
        from app.db import update_rows_admin
    except ImportError:
        from db import update_rows_admin  # type: ignore

    try:
        update_rows_admin(
            "pricing_guide_items",
            {"is_active": bool(visible), "updated_at": _now_iso()},
            {"id": pid},
        )
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))

    ast_id = _linked_asset_id(row)
    if ast_id:
        result = set_asset_include_in_pricing_guide(ast_id, visible)
        if not result.ok:
            return result

    clear_pricing_guide_cache()
    clear_assets_cache()
    return ServiceResult(ok=True)


def _ensure_inventory(row: dict[str, Any]) -> ServiceResult:
    pid = str(row.get("id") or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing pricing item id.")

    inv_id = _linked_inventory_id(row)
    if inv_id and get_inventory_item(inv_id):
        ok, msg = link_inventory_to_pricing_item(inv_id, pid, sync_cost=True)
        if ok:
            try:
                from app.services.catalog_image_sync import sync_linked_catalog_images

                sync_linked_catalog_images(_fresh_pricing_row(pid) or row)
            except Exception:
                pass
        return ServiceResult(ok=ok, error=None if ok else msg)

    cost = float(row.get("default_cost") or 0)
    description = str(row.get("description") or row.get("item") or "Inventory Item").strip()
    now = _now_iso()
    payload: dict[str, Any] = {
        "item_name": description,
        "category": str(row.get("category") or "Inventory"),
        "unit": str(row.get("unit") or "EA"),
        "quantity_on_hand": 0,
        "unit_cost": cost,
        "last_purchase_cost": cost,
        "average_cost": cost,
        "vendor": str(row.get("vendor") or row.get("vendor_name") or ""),
        "sku": str(row.get("sku") or row.get("item_code") or row.get("item_key") or ""),
        "pricing_guide_id": pid,
        "pricing_item_id": pid,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    inserted, err = _admin_insert_row("inventory_items", payload)
    if err:
        return ServiceResult(ok=False, error=err)
    new_id = str((inserted or {}).get("id") or "")
    if not new_id:
        return ServiceResult(ok=False, error="Could not create inventory item.")

    ok, msg = link_inventory_to_pricing_item(new_id, pid, sync_cost=True)
    if not ok:
        return ServiceResult(ok=False, error=msg)
    clear_inventory_cache()
    clear_pricing_guide_cache()
    try:
        from app.services.catalog_image_sync import sync_linked_catalog_images

        fresh = _fresh_pricing_row(pid) or row
        sync_linked_catalog_images(fresh)
    except Exception:
        pass
    return ServiceResult(ok=True, data={"inventory_id": new_id})


def _remove_inventory(row: dict[str, Any]) -> ServiceResult:
    inv_id = _linked_inventory_id(row)
    if not inv_id:
        return ServiceResult(ok=True)

    inv_row = get_inventory_item(inv_id)
    if not inv_row:
        return ServiceResult(ok=True)

    pid = str(row.get("id") or "").strip()
    try:
        from app.db import update_rows_admin
    except ImportError:
        from db import update_rows_admin  # type: ignore

    ast_id = _linked_asset_id(row)
    ast_row = _load_asset_row(ast_id) if ast_id else None
    remaining_ast = str(ast_row.get("id") or "") if ast_row else ""
    try:
        from app.services.catalog_image_sync import preserve_catalog_image_before_catalog_remove

        preserve_catalog_image_before_catalog_remove(
            row,
            removed_row=inv_row,
            remaining_inventory=None,
            remaining_asset=ast_row,
        )
    except Exception:
        pass
    try:
        _recompute_item_class(
            pricing_item_id=pid,
            inventory_id=None,
            asset_id=remaining_ast or None,
            update_rows_admin=update_rows_admin,
        )
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))

    delete_result = delete_inventory_item(inv_id)
    if not delete_result.ok:
        return delete_result

    clear_inventory_cache()
    clear_pricing_guide_cache()
    return ServiceResult(ok=True)


def _slug_asset_number(text: str) -> str:
    return slug_item_code(text, prefix="AST")


def _ensure_asset(row: dict[str, Any], *, visible_on_pricing_guide: bool) -> ServiceResult:
    pid = str(row.get("id") or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing pricing item id.")

    ast_id = _linked_asset_id(row)
    ast_row = _load_asset_row(ast_id) if ast_id else None
    if ast_row:
        ok, msg = link_asset_to_pricing_item(ast_id, pid)
        if not ok:
            return ServiceResult(ok=False, error=msg)
        set_asset_include_in_pricing_guide(ast_id, visible_on_pricing_guide)
        clear_assets_cache()
        clear_pricing_guide_cache()
        try:
            from app.services.catalog_image_sync import sync_linked_catalog_images

            sync_linked_catalog_images(_fresh_pricing_row(pid) or row)
        except Exception:
            pass
        return ServiceResult(ok=True, data={"asset_id": ast_id})

    description = str(row.get("description") or row.get("item") or "Equipment").strip()
    cost = float(row.get("default_cost") or 0)
    asset_no = (
        str(row.get("model_number") or row.get("item_number") or row.get("sku") or "").strip()
        or _slug_asset_number(description)
    )
    now = _now_iso()
    payload: dict[str, Any] = {
        "asset_id": asset_no,
        "asset_number": asset_no,
        "asset_name": description,
        "category": str(row.get("category") or "Equipment"),
        "subcategory": str(row.get("subcategory") or ""),
        "model": str(row.get("model_number") or ""),
        "serial_number": str(row.get("sku") or ""),
        "status": "Available",
        "purchase_cost": cost,
        "current_value": cost,
        "pricing_guide_id": pid,
        "pricing_item_id": pid,
        "include_in_pricing_guide": bool(visible_on_pricing_guide),
        "notes": str(row.get("notes") or ""),
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    inserted, err = _admin_insert_row("assets", payload)
    if err:
        return ServiceResult(ok=False, error=err)
    new_id = str((inserted or {}).get("id") or "")
    if not new_id:
        return ServiceResult(ok=False, error="Could not create asset.")

    ok, msg = link_asset_to_pricing_item(new_id, pid)
    if not ok:
        return ServiceResult(ok=False, error=msg)
    clear_assets_cache()
    clear_pricing_guide_cache()
    try:
        from app.services.catalog_image_sync import sync_linked_catalog_images

        sync_linked_catalog_images(_fresh_pricing_row(pid) or row)
    except Exception:
        pass
    return ServiceResult(ok=True, data={"asset_id": new_id})


def _remove_asset(row: dict[str, Any]) -> ServiceResult:
    ast_id = _linked_asset_id(row)
    if not ast_id:
        return ServiceResult(ok=True)

    ast_row = _load_asset_row(ast_id)
    if not ast_row:
        return ServiceResult(ok=True)

    pid = str(row.get("id") or "").strip()
    try:
        from app.db import update_rows_admin
    except ImportError:
        from db import update_rows_admin  # type: ignore

    inv_id = _linked_inventory_id(row)
    inv_row = get_inventory_item(inv_id) if inv_id else None
    remaining_inv = str(inv_row.get("id") or "") if inv_row else ""
    try:
        from app.services.catalog_image_sync import preserve_catalog_image_before_catalog_remove

        preserve_catalog_image_before_catalog_remove(
            row,
            removed_row=ast_row,
            remaining_inventory=inv_row,
            remaining_asset=None,
        )
    except Exception:
        pass
    try:
        _recompute_item_class(
            pricing_item_id=pid,
            inventory_id=remaining_inv or None,
            asset_id=None,
            update_rows_admin=update_rows_admin,
        )
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))

    delete_result = delete_asset_record(ast_id)
    if not delete_result.ok:
        return delete_result

    clear_assets_cache()
    clear_pricing_guide_cache()
    return ServiceResult(ok=True)


def apply_catalog_presence(
    row: dict[str, Any],
    *,
    pricing_guide: bool,
    inventory: bool,
    assets: bool,
) -> ServiceResult:
    """Apply desired table membership for a pricing guide item."""
    current = resolve_catalog_presence(row)
    messages: list[str] = []

    if pricing_guide != current["pricing_guide"]:
        result = _set_pricing_guide_visibility(row, visible=pricing_guide)
        if not result.ok:
            return result
        messages.append("Pricing Guide visibility updated.")

    if inventory and not current["inventory"]:
        result = _ensure_inventory(row)
        if not result.ok:
            return result
        messages.append("Inventory record created and linked.")
        row = _fresh_pricing_row(str(row.get("id") or "")) or row
    elif not inventory and current["inventory"]:
        result = _remove_inventory(row)
        if not result.ok:
            return result
        messages.append("Removed from Inventory.")
        row = _fresh_pricing_row(str(row.get("id") or "")) or row

    if assets and not current["assets"]:
        result = _ensure_asset(row, visible_on_pricing_guide=pricing_guide)
        if not result.ok:
            return result
        messages.append("Asset record created and linked.")
        row = _fresh_pricing_row(str(row.get("id") or "")) or row
    elif not assets and current["assets"]:
        result = _remove_asset(row)
        if not result.ok:
            return result
        messages.append("Removed from Assets.")
        row = _fresh_pricing_row(str(row.get("id") or "")) or row

    fresh_row = _fresh_pricing_row(str(row.get("id") or "")) or row
    try:
        from app.services.catalog_image_sync import sync_linked_catalog_images

        sync_linked_catalog_images(fresh_row)
    except Exception:
        pass

    if (
        pricing_guide == current["pricing_guide"]
        and inventory == current["inventory"]
        and assets == current["assets"]
        and not messages
    ):
        return ServiceResult(ok=True, data={"message": "No changes to apply."})

    return ServiceResult(ok=True, data={"message": " ".join(messages) or "Catalog presence updated."})
