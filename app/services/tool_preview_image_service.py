"""Resolve preview images for Quick Add Tool photo intake.

Three-tier model:
1. Source files — all user uploads (saved as evidence; not auto-used as primary).
2. Primary image — default best converted upload; user may approve a product suggestion instead.
3. Product suggestions — optional catalog matches from model/manufacturer/name.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from app.services.item_images import (
        description_image_match_key,
        has_stored_item_image,
        normalize_image_match_key,
        record_has_item_image,
    )
    from app.services.task_attachment_autofill import download_signed_url
except ImportError:
    from services.item_images import (  # type: ignore
        description_image_match_key,
        has_stored_item_image,
        normalize_image_match_key,
        record_has_item_image,
    )
    from services.task_attachment_autofill import download_signed_url  # type: ignore

_RASTER_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
_MAX_SUGGESTIONS = 4


@dataclass(frozen=True)
class ToolPreviewImage:
    preview_bytes: bytes
    preview_filename: str
    source: str  # upload | catalog_pricing_guide | catalog_asset | catalog_inventory
    source_label: str
    suggestion_id: str = ""


def _ext(name: str) -> str:
    return Path(str(name or "")).suffix.lower()


def _preview_fingerprint(data: bytes) -> str:
    return hashlib.sha256(data[:8192]).hexdigest()


def pick_best_upload_preview(uploads: list[tuple[bytes, str]]) -> ToolPreviewImage:
    """Choose the best user upload for the default primary thumbnail."""
    if not uploads:
        raise ValueError("At least one upload is required.")

    try:
        from app.services.upload_media_strategy import build_display_preview
    except ImportError:
        from services.upload_media_strategy import build_display_preview  # type: ignore

    rasters = [(b, n) for b, n in uploads if _ext(n) in _RASTER_EXTENSIONS]
    candidates = rasters or list(uploads)
    best_bytes, best_name = max(candidates, key=lambda pair: len(pair[0]))
    preview_bytes, preview_name = build_display_preview(best_bytes, best_name)
    return ToolPreviewImage(
        preview_bytes=preview_bytes,
        preview_filename=preview_name,
        source="upload",
        source_label=f"Best uploaded file ({best_name})",
        suggestion_id="upload",
    )


def _row_has_preview(row: dict[str, Any]) -> bool:
    return has_stored_item_image(row) or record_has_item_image(row)


def _download_row_preview(row: dict[str, Any], *, kind: str) -> tuple[bytes, str] | None:
    url: str | None = None
    filename = "catalog-preview.jpg"
    if kind == "pricing_guide":
        try:
            from app.services.pricing_guide_images import get_pricing_guide_stored_image_url, pricing_guide_display_record
        except ImportError:
            from services.pricing_guide_images import (  # type: ignore
                get_pricing_guide_stored_image_url,
                pricing_guide_display_record,
            )
        display = pricing_guide_display_record(row)
        url = get_pricing_guide_stored_image_url(display)
        filename = str(display.get("image_file_name") or display.get("model_number") or "pricing-guide") + ".jpg"
    elif kind == "asset":
        try:
            from app.services.asset_images import get_asset_stored_image_url
        except ImportError:
            from services.asset_images import get_asset_stored_image_url  # type: ignore
        url = get_asset_stored_image_url(row)
        filename = str(row.get("image_file_name") or row.get("asset_id") or "asset") + ".jpg"
    elif kind == "inventory":
        try:
            from app.services.inventory_images import get_inventory_stored_image_url
        except ImportError:
            from services.inventory_images import get_inventory_stored_image_url  # type: ignore
        url = get_inventory_stored_image_url(row)
        filename = str(row.get("image_file_name") or row.get("item_name") or "inventory") + ".jpg"

    if not url:
        return None
    data = download_signed_url(url)
    if not data:
        return None
    return data, filename


def _row_matches_fields(row: dict[str, Any], *, model_key: str, name_key: str) -> bool:
    if not _row_has_preview(row):
        return False
    if model_key:
        for field in ("model_number", "item_number", "model", "sku"):
            if normalize_image_match_key(row.get(field)) == model_key:
                return True
    if name_key:
        desc_key = description_image_match_key(
            row.get("description") or row.get("item_name") or row.get("asset_name")
        )
        if desc_key and desc_key == name_key:
            return True
    return False


def _append_suggestion(
    suggestions: list[ToolPreviewImage],
    seen: set[str],
    *,
    row: dict[str, Any],
    kind: str,
    source: str,
    label_prefix: str,
    suggestion_id: str,
) -> None:
    if len(suggestions) >= _MAX_SUGGESTIONS:
        return
    downloaded = _download_row_preview(row, kind=kind)
    if not downloaded:
        return
    data, filename = downloaded
    fingerprint = _preview_fingerprint(data)
    if fingerprint in seen:
        return
    seen.add(fingerprint)
    label = str(
        row.get("description")
        or row.get("asset_name")
        or row.get("item_name")
        or row.get("model_number")
        or row.get("model")
        or suggestion_id
    ).strip()
    suggestions.append(
        ToolPreviewImage(
            preview_bytes=data,
            preview_filename=filename,
            source=source,
            source_label=f"{label_prefix} — {label}",
            suggestion_id=suggestion_id,
        )
    )


def find_product_image_suggestions(fields: dict[str, Any]) -> list[ToolPreviewImage]:
    """Optional catalog product images matched by model, manufacturer, or name."""
    model_key = normalize_image_match_key(fields.get("model"))
    mfr_key = normalize_image_match_key(fields.get("manufacturer"))
    name_key = description_image_match_key(fields.get("tool_name") or fields.get("asset_name"))
    if not model_key and not name_key and not mfr_key:
        return []

    suggestions: list[ToolPreviewImage] = []
    seen: set[str] = set()

    try:
        from app.services.pricing_guide_service import cached_pricing_guide_rows
    except ImportError:
        from services.pricing_guide_service import cached_pricing_guide_rows  # type: ignore

    for idx, row in enumerate(cached_pricing_guide_rows(include_inactive=True)):
        if model_key and normalize_image_match_key(row.get("model_number")) == model_key:
            _append_suggestion(
                suggestions,
                seen,
                row=row,
                kind="pricing_guide",
                source="catalog_pricing_guide",
                label_prefix="Pricing Guide",
                suggestion_id=f"pg_{idx}",
            )
        elif model_key and normalize_image_match_key(row.get("item_number")) == model_key:
            _append_suggestion(
                suggestions,
                seen,
                row=row,
                kind="pricing_guide",
                source="catalog_pricing_guide",
                label_prefix="Pricing Guide",
                suggestion_id=f"pg_item_{idx}",
            )
        elif name_key and _row_matches_fields(row, model_key="", name_key=name_key):
            _append_suggestion(
                suggestions,
                seen,
                row=row,
                kind="pricing_guide",
                source="catalog_pricing_guide",
                label_prefix="Pricing Guide",
                suggestion_id=f"pg_name_{idx}",
            )

    try:
        from app.pages._core._data import load_assets, load_inventory
    except ImportError:
        from pages._core._data import load_assets, load_inventory  # type: ignore

    for idx, row in enumerate(load_assets()):
        if _row_matches_fields(row, model_key=model_key, name_key=name_key):
            _append_suggestion(
                suggestions,
                seen,
                row=row,
                kind="asset",
                source="catalog_asset",
                label_prefix="Existing asset",
                suggestion_id=f"asset_{idx}",
            )

    for idx, row in enumerate(load_inventory()):
        if _row_matches_fields(row, model_key=model_key, name_key=name_key):
            _append_suggestion(
                suggestions,
                seen,
                row=row,
                kind="inventory",
                source="catalog_inventory",
                label_prefix="Inventory item",
                suggestion_id=f"inv_{idx}",
            )

    return suggestions[:_MAX_SUGGESTIONS]


def preview_image_to_dict(image: ToolPreviewImage) -> dict[str, Any]:
    return {
        "id": image.suggestion_id or image.source,
        "preview_bytes": image.preview_bytes,
        "preview_filename": image.preview_filename,
        "source": image.source,
        "source_label": image.source_label,
    }


def resolve_tool_primary_preview(
    fields: dict[str, Any],
    uploads: list[tuple[bytes, str]],
) -> ToolPreviewImage:
    """Default primary is always the best upload preview (not auto-catalog)."""
    return pick_best_upload_preview(uploads)


def find_catalog_product_preview(fields: dict[str, Any]) -> ToolPreviewImage | None:
    """First product suggestion, if any (legacy helper)."""
    suggestions = find_product_image_suggestions(fields)
    return suggestions[0] if suggestions else None


__all__ = [
    "ToolPreviewImage",
    "find_catalog_product_preview",
    "find_product_image_suggestions",
    "pick_best_upload_preview",
    "preview_image_to_dict",
    "resolve_tool_primary_preview",
]
