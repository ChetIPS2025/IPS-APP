"""Small hand tool photo upload and URL resolution."""

from __future__ import annotations

from typing import Any

from app.services.item_images import (
    CATALOG_IMAGE_FIELD_PRIORITY,
    ITEM_IMAGE_FIELDS,
    IMAGE_STATUS_MISSING,
    clear_item_image,
    clear_item_image_url_cache,
    has_owned_stored_item_image,
    has_stored_item_image,
    persist_item_image,
    record_has_item_image,
    resolve_image_url_by_field_priority,
    resolve_stored_item_image_url,
)
from app.services.repository import ServiceResult

__all__ = [
    "clear_small_hand_tool_image",
    "get_small_hand_tool_image_url",
    "get_small_hand_tool_stored_image_url",
    "small_hand_tool_has_image",
    "small_hand_tool_photo_preview_record",
    "upload_small_hand_tool_image",
]


def small_hand_tool_photo_preview_record(tool: dict[str, Any]) -> dict[str, Any]:
    """Owned photo only — exclude catalog fallbacks in the upload UI."""
    if has_owned_stored_item_image(tool):
        return tool
    cleared = dict(tool)
    for key in ITEM_IMAGE_FIELDS:
        if key == "image_status":
            cleared[key] = IMAGE_STATUS_MISSING
        else:
            cleared[key] = ""
    return cleared


def get_small_hand_tool_owned_image_url(tool: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    if not has_owned_stored_item_image(tool):
        return None
    return resolve_image_url_by_field_priority(
        tool,
        CATALOG_IMAGE_FIELD_PRIORITY,
        expires_in=expires_in,
    )


def get_small_hand_tool_stored_image_url(tool: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    preview = small_hand_tool_photo_preview_record(tool)
    return resolve_stored_item_image_url(preview, expires_in=expires_in)


def small_hand_tool_has_image(tool: dict[str, Any]) -> bool:
    return get_small_hand_tool_image_url(tool) is not None


def get_small_hand_tool_image_url(tool: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    """Owned tool photo URL only (catalog fallbacks handled by catalog_images)."""
    if record_has_item_image(tool) or has_stored_item_image(tool):
        owned = get_small_hand_tool_owned_image_url(tool, expires_in=expires_in)
        if owned:
            return owned
    return None


def upload_small_hand_tool_image(
    tool_id: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
    existing: dict[str, Any] | None = None,
    replace_existing: bool = False,
    force: bool | None = None,
) -> ServiceResult:
    if force is not None:
        replace_existing = force
    tid = str(tool_id or "").strip()
    if not tid:
        return ServiceResult(ok=False, error="Missing hand tool id.")
    if uploaded_file is None:
        return ServiceResult(ok=False, error="No file provided.")
    filename = str(getattr(uploaded_file, "name", "") or "item-image")
    raw = uploaded_file.getvalue()
    if not raw:
        return ServiceResult(ok=False, error="Uploaded file is empty.")
    result = persist_item_image(
        table="small_hand_tools",
        record_id=tid,
        entity_type="small_hand_tools",
        image_bytes=raw,
        filename=filename,
        existing=existing,
        uploaded_by=uploaded_by,
        replace_existing=replace_existing,
    )
    if result.ok and not (isinstance(result.data, dict) and result.data.get("skipped")):
        clear_item_image_url_cache()
    return result


def clear_small_hand_tool_image(tool_id: str) -> ServiceResult:
    return clear_item_image(table="small_hand_tools", record_id=tool_id)
