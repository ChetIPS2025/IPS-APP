"""Resize, upload, and resolve asset images."""

from __future__ import annotations

from typing import Any

from app.services.item_images import (
    ASSET_IMAGE_BUCKET,
    clear_item_image,
    clear_item_image_url_cache,
    persist_item_image,
    record_has_item_image,
    resolve_item_image_url,
    resize_item_image_bytes,
)
from app.services.repository import ServiceResult

__all__ = [
    "ASSET_IMAGE_BUCKET",
    "asset_has_image",
    "clear_asset_image",
    "clear_asset_image_url_cache",
    "get_asset_image_url",
    "resize_asset_image_bytes",
    "upload_asset_image",
]

resize_asset_image_bytes = resize_item_image_bytes


def clear_asset_image_url_cache() -> None:
    clear_item_image_url_cache()


def asset_has_image(asset: dict[str, Any]) -> bool:
    return record_has_item_image(asset)


def get_asset_image_url(asset: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    return resolve_item_image_url(asset, expires_in=expires_in)


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
    return persist_item_image(
        table="assets",
        record_id=aid,
        entity_type="assets",
        image_bytes=raw,
        filename=filename,
        existing=existing,
        uploaded_by=uploaded_by,
        force=force,
    )


def clear_asset_image(asset_id: str) -> ServiceResult:
    return clear_item_image(table="assets", record_id=asset_id)
