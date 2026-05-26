"""Resize, upload, and resolve inventory item images."""

from __future__ import annotations

from typing import Any

from app.services.item_images import (
    INVENTORY_IMAGE_BUCKET,
    clear_item_image_url_cache,
    persist_item_image,
    record_has_item_image,
    resolve_item_image_url,
    resize_item_image_bytes,
)
from app.services.repository import ServiceResult

__all__ = [
    "INVENTORY_IMAGE_BUCKET",
    "clear_inventory_image_url_cache",
    "get_inventory_image_url",
    "inventory_has_image",
    "inventory_item_image_storage_path",
    "resize_inventory_image_bytes",
    "upload_inventory_image",
]

# Backward-compatible aliases
resize_inventory_image_bytes = resize_item_image_bytes


def inventory_item_image_storage_path(item_id: str) -> str:
    """Legacy stable storage key for an item thumbnail (default bucket)."""
    return f"inventory/items/{str(item_id).strip()}.jpg"


def clear_inventory_image_url_cache() -> None:
    clear_item_image_url_cache()


def inventory_has_image(item: dict[str, Any]) -> bool:
    return record_has_item_image(item)


def get_inventory_image_url(item: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    return resolve_item_image_url(item, expires_in=expires_in)


def upload_inventory_image(
    item_id: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
    existing: dict[str, Any] | None = None,
    force: bool = False,
) -> ServiceResult:
    iid = str(item_id or "").strip()
    if not iid:
        return ServiceResult(ok=False, error="Missing inventory item id.")
    if uploaded_file is None:
        return ServiceResult(ok=False, error="No file provided.")
    filename = str(getattr(uploaded_file, "name", "") or "item-image")
    raw = uploaded_file.getvalue()
    if not raw:
        return ServiceResult(ok=False, error="Uploaded file is empty.")
    return persist_item_image(
        table="inventory_items",
        record_id=iid,
        entity_type="inventory",
        image_bytes=raw,
        filename=filename,
        existing=existing,
        uploaded_by=uploaded_by,
        force=force,
    )

