"""Keep item preview image metadata aligned across linked catalog rows."""

from __future__ import annotations

from typing import Any

try:
    from app.services.inventory_service import clear_inventory_cache, get_inventory_item
    from app.services.item_images import (
        copy_item_image_metadata,
        has_owned_stored_item_image,
        has_stored_item_image,
        is_image_approved,
        record_has_item_image,
        record_has_foreign_image_path,
    )
    from app.services.pricing_guide_service import cached_pricing_guide_rows, clear_pricing_guide_cache
    from app.services.repository import ServiceResult
except ImportError:
    from services.inventory_service import clear_inventory_cache, get_inventory_item  # type: ignore
    from services.item_images import (  # type: ignore
        copy_item_image_metadata,
        has_owned_stored_item_image,
        has_stored_item_image,
        is_image_approved,
        record_has_item_image,
        record_has_foreign_image_path,
    )
    from services.pricing_guide_service import cached_pricing_guide_rows, clear_pricing_guide_cache  # type: ignore
    from services.repository import ServiceResult  # type: ignore

__all__ = [
    "clear_catalog_image_sync_cache",
    "preserve_catalog_image_before_catalog_remove",
    "sync_catalog_images_for_inventory_item",
    "sync_catalog_images_for_asset",
    "sync_linked_catalog_images",
]

def clear_catalog_image_sync_cache() -> None:
    try:
        from app.services.pricing_guide_images import clear_catalog_image_maps_cache
    except ImportError:
        from services.pricing_guide_images import clear_catalog_image_maps_cache  # type: ignore
    clear_catalog_image_maps_cache()
    clear_pricing_guide_cache()
    clear_inventory_cache()
    try:
        from app.services.assets_service import clear_assets_cache
    except ImportError:
        from services.assets_service import clear_assets_cache  # type: ignore
    clear_assets_cache()
    try:
        from app.services.item_images import clear_item_image_url_cache
    except ImportError:
        from services.item_images import clear_item_image_url_cache  # type: ignore
    clear_item_image_url_cache()


def _linked_inventory_id(row: dict[str, Any]) -> str:
    return str(row.get("linked_inventory_id") or row.get("inventory_item_id") or "").strip()


def _linked_asset_id(row: dict[str, Any]) -> str:
    return str(row.get("linked_asset_id") or row.get("asset_id") or "").strip()


def _pricing_id_from_inventory(item: dict[str, Any]) -> str:
    return str(item.get("pricing_guide_id") or item.get("pricing_item_id") or "").strip()


def _pricing_id_from_asset(asset: dict[str, Any]) -> str:
    return str(asset.get("pricing_guide_id") or asset.get("pricing_item_id") or "").strip()


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


def _pick_best_image_source(*rows: dict[str, Any] | None) -> dict[str, Any] | None:
    candidates = [row for row in rows if row and has_owned_stored_item_image(row)]
    if not candidates:
        return None
    approved = [row for row in candidates if is_image_approved(row)]
    return (approved or candidates)[0]


def _target_needs_image_sync(target: dict[str, Any] | None, source: dict[str, Any]) -> bool:
    if not target:
        return False
    if record_has_foreign_image_path(target):
        return True
    if not has_stored_item_image(target):
        return True
    target_path = str(target.get("image_path") or "").strip()
    source_path = str(source.get("image_path") or "").strip()
    if target_path and source_path and target_path != source_path:
        return True
    return not record_has_item_image(target) and record_has_item_image(source)


def _sync_targets(source: dict[str, Any], targets: list[tuple[str, str, dict[str, Any] | None]]) -> ServiceResult:
    synced = 0
    for table, record_id, existing in targets:
        if not _target_needs_image_sync(existing, source):
            continue
        result = copy_item_image_metadata(
            source,
            table=table,
            record_id=record_id,
            existing=existing,
            force=True,
        )
        if not result.ok:
            return result
        synced += 1
    if synced:
        clear_catalog_image_sync_cache()
    return ServiceResult(ok=True, data={"synced": synced})


def sync_linked_catalog_images(pricing_row: dict[str, Any]) -> ServiceResult:
    """Copy the best linked image metadata onto every linked catalog row."""
    pid = str(pricing_row.get("id") or "").strip()
    if not pid:
        return ServiceResult(ok=False, error="Missing pricing item id.")

    pg_row = _fresh_pricing_row(pid) or pricing_row
    item_class = str(pg_row.get("item_class") or "").strip()
    inv_id = _linked_inventory_id(pg_row)
    ast_id = _linked_asset_id(pg_row)
    inv_row = get_inventory_item(inv_id) if inv_id and item_class == "Inventory" else None
    ast_row = _load_asset_row(ast_id) if ast_id and item_class == "Asset" else None

    candidates: list[dict[str, Any] | None] = [pg_row]
    targets: list[tuple[str, str, dict[str, Any] | None]] = [
        ("pricing_guide_items", pid, pg_row),
    ]
    if item_class == "Inventory" and inv_row:
        candidates.append(inv_row)
        targets.append(("inventory_items", str(inv_row.get("id") or ""), inv_row))
    elif item_class == "Asset" and ast_row:
        candidates.append(ast_row)
        targets.append(("assets", str(ast_row.get("id") or ""), ast_row))

    source = _pick_best_image_source(*candidates)
    if not source:
        return ServiceResult(ok=True, data={"synced": 0})

    return _sync_targets(source, targets)


def preserve_catalog_image_before_catalog_remove(
    pricing_row: dict[str, Any],
    *,
    removed_row: dict[str, Any] | None,
    remaining_inventory: dict[str, Any] | None = None,
    remaining_asset: dict[str, Any] | None = None,
) -> ServiceResult:
    """Keep the preview image on remaining linked rows before deleting a catalog record."""
    source = _pick_best_image_source(removed_row, pricing_row, remaining_inventory, remaining_asset)
    if not source:
        return ServiceResult(ok=True, data={"synced": 0})

    pid = str(pricing_row.get("id") or "").strip()
    targets: list[tuple[str, str, dict[str, Any] | None]] = [("pricing_guide_items", pid, pricing_row)]
    if remaining_inventory:
        targets.append(
            (
                "inventory_items",
                str(remaining_inventory.get("id") or ""),
                remaining_inventory,
            )
        )
    if remaining_asset:
        targets.append(("assets", str(remaining_asset.get("id") or ""), remaining_asset))
    return _sync_targets(source, targets)


def sync_catalog_images_for_inventory_item(item: dict[str, Any]) -> ServiceResult:
    pid = _pricing_id_from_inventory(item)
    if not pid:
        return ServiceResult(ok=True, data={"synced": 0})
    pg_row = _fresh_pricing_row(pid)
    if not pg_row:
        return ServiceResult(ok=True, data={"synced": 0})
    return sync_linked_catalog_images(pg_row)


def sync_catalog_images_for_asset(asset: dict[str, Any]) -> ServiceResult:
    pid = _pricing_id_from_asset(asset)
    if not pid:
        return ServiceResult(ok=True, data={"synced": 0})
    pg_row = _fresh_pricing_row(pid)
    if not pg_row:
        return ServiceResult(ok=True, data={"synced": 0})
    return sync_linked_catalog_images(pg_row)
