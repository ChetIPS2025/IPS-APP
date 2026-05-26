"""Resize, upload, and resolve asset images."""

from __future__ import annotations

from typing import Any

from app.services.item_images import (
    ASSET_IMAGE_BUCKET,
    ITEM_IMAGE_FIELDS,
    clear_item_image,
    clear_item_image_url_cache,
    has_stored_item_image,
    persist_item_image,
    record_has_item_image,
    resolve_item_image_url,
    resolve_stored_item_image_url,
    resize_item_image_bytes,
)
from app.services.repository import ServiceResult

__all__ = [
    "ASSET_IMAGE_BUCKET",
    "asset_display_record",
    "asset_has_image",
    "asset_image_is_inherited",
    "clear_asset_image",
    "clear_asset_image_url_cache",
    "get_asset_image_url",
    "resize_asset_image_bytes",
    "upload_asset_image",
]

resize_asset_image_bytes = resize_item_image_bytes


def clear_asset_image_url_cache() -> None:
    clear_item_image_url_cache()


def _copy_image_fields(base: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key in ITEM_IMAGE_FIELDS:
        if key in source:
            merged[key] = source.get(key)
    return merged


def _linked_pricing_row(asset: dict[str, Any]) -> dict[str, Any] | None:
    pid = str(asset.get("pricing_guide_id") or asset.get("pricing_item_id") or "").strip()
    if not pid:
        return None
    try:
        from app.services.pricing_guide_service import cached_pricing_guide_rows
    except ImportError:
        from services.pricing_guide_service import cached_pricing_guide_rows  # type: ignore
    return next((r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id") or "") == pid), None)


def _linked_inventory_row(asset: dict[str, Any]) -> dict[str, Any] | None:
    pg_row = _linked_pricing_row(asset)
    if not pg_row:
        return None
    inv_id = str(pg_row.get("linked_inventory_id") or pg_row.get("inventory_item_id") or "").strip()
    if not inv_id:
        return None
    try:
        from app.services.inventory_service import get_inventory_item
    except ImportError:
        from services.inventory_service import get_inventory_item  # type: ignore
    return get_inventory_item(inv_id)


def _resolve_linked_image_source(asset: dict[str, Any], *, approved_only: bool) -> dict[str, Any] | None:
    def _usable(record: dict[str, Any] | None) -> bool:
        if not record:
            return False
        if approved_only:
            return record_has_item_image(record)
        return has_stored_item_image(record)

    pg_row = _linked_pricing_row(asset)
    if _usable(pg_row):
        return pg_row
    inv_row = _linked_inventory_row(asset)
    if _usable(inv_row):
        return inv_row
    return None


def asset_image_is_inherited(asset: dict[str, Any]) -> bool:
    if has_stored_item_image(asset):
        return False
    return _resolve_linked_image_source(asset, approved_only=False) is not None


def asset_display_record(asset: dict[str, Any]) -> dict[str, Any]:
    if has_stored_item_image(asset):
        return asset
    linked = _resolve_linked_image_source(asset, approved_only=False)
    if linked:
        return _copy_image_fields(asset, linked)
    return asset


def asset_has_image(asset: dict[str, Any]) -> bool:
    return get_asset_image_url(asset) is not None


def get_asset_image_url(asset: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    if record_has_item_image(asset):
        return resolve_item_image_url(asset, expires_in=expires_in)
    linked = _resolve_linked_image_source(asset, approved_only=True)
    if linked:
        return resolve_item_image_url(linked, expires_in=expires_in)
    return None


def get_asset_stored_image_url(asset: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    display = asset_display_record(asset)
    return resolve_stored_item_image_url(display, expires_in=expires_in)


def upload_asset_image(
    asset_id: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
    existing: dict[str, Any] | None = None,
    force: bool = False,
) -> ServiceResult:
    aid = str(asset_id or "").strip()
    if not aid:
        return ServiceResult(ok=False, error="Missing asset id.")
    if uploaded_file is None:
        return ServiceResult(ok=False, error="No file provided.")
    filename = str(getattr(uploaded_file, "name", "") or "asset-image")
    raw = uploaded_file.getvalue()
    if not raw:
        return ServiceResult(ok=False, error="Uploaded file is empty.")
    result = persist_item_image(
        table="assets",
        record_id=aid,
        entity_type="assets",
        image_bytes=raw,
        filename=filename,
        existing=existing,
        uploaded_by=uploaded_by,
        force=force,
    )
    if result.ok and not (isinstance(result.data, dict) and result.data.get("skipped")):
        try:
            from app.services.catalog_image_sync import sync_catalog_images_for_asset

            try:
                from app.pages._core._data import load_assets
            except ImportError:
                from pages._core._data import load_assets  # type: ignore
            source = next((r for r in load_assets() if str(r.get("id") or "") == aid), None) or existing or {"id": aid}
            sync_catalog_images_for_asset(source)
        except Exception:
            pass
    return result


def clear_asset_image(asset_id: str) -> ServiceResult:
    return clear_item_image(table="assets", record_id=asset_id)
