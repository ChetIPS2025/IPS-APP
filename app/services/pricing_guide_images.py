"""Pricing Guide item photo upload and URL resolution."""

from __future__ import annotations

from typing import Any

from app.services.item_images import (
    can_apply_item_image,
    clear_item_image_url_cache,
    persist_item_image,
    record_has_item_image,
    resolve_item_image_url,
)
from app.services.repository import ServiceResult

__all__ = [
    "can_apply_item_image",
    "clear_pricing_guide_image_cache",
    "get_pricing_guide_image_url",
    "pricing_guide_has_image",
    "upload_pricing_guide_image",
]


def clear_pricing_guide_image_cache() -> None:
    clear_item_image_url_cache()


def pricing_guide_has_image(row: dict[str, Any]) -> bool:
    return record_has_item_image(row)


def get_pricing_guide_image_url(row: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    return resolve_item_image_url(row, expires_in=expires_in)


def upload_pricing_guide_image(
    item_id: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
    existing: dict[str, Any] | None = None,
    force: bool = False,
) -> ServiceResult:
    iid = str(item_id or "").strip()
    if uploaded_file is None:
        return ServiceResult(ok=False, error="No file provided.")
    filename = str(getattr(uploaded_file, "name", "") or "item-image")
    raw = uploaded_file.getvalue()
    if not raw:
        return ServiceResult(ok=False, error="Uploaded file is empty.")
    return persist_item_image(
        table="pricing_guide_items",
        record_id=iid,
        entity_type="pricing_guide",
        image_bytes=raw,
        filename=filename,
        existing=existing,
        uploaded_by=uploaded_by,
        force=force,
    )
