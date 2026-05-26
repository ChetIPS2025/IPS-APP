"""Pricing Guide item photo upload and URL resolution."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.services.item_images import (
    can_apply_item_image,
    clear_item_image,
    clear_item_image_url_cache,
    has_stored_item_image,
    persist_item_image,
    record_has_item_image,
    resolve_item_image_url,
    resolve_stored_item_image_url,
)
from app.services.repository import ServiceResult

__all__ = [
    "can_apply_item_image",
    "clear_catalog_image_maps_cache",
    "clear_pricing_guide_image",
    "clear_pricing_guide_image_cache",
    "get_pricing_guide_image_url",
    "pricing_guide_display_record",
    "pricing_guide_has_image",
    "pricing_guide_image_is_inherited",
    "upload_pricing_guide_image",
]

_IMAGE_FIELDS: tuple[str, ...] = (
    "image_path",
    "image_url",
    "image_file_name",
    "image_mime_type",
    "image_uploaded_at",
    "image_uploaded_by",
    "image_status",
)


def clear_pricing_guide_image_cache() -> None:
    clear_item_image_url_cache()
    clear_catalog_image_maps_cache()


def clear_catalog_image_maps_cache() -> None:
    _catalog_image_maps_cached.clear()


@st.cache_data(ttl=120, show_spinner=False)
def _catalog_image_maps_cached() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Normalized inventory and asset rows keyed by id for linked photo inheritance."""
    try:
        from app.db import fetch_table_admin
        from app.services.phase2_modules_service import normalize_asset, normalize_inventory
    except ImportError:
        from db import fetch_table_admin  # type: ignore
        from services.phase2_modules_service import normalize_asset, normalize_inventory  # type: ignore

    inventory_by_id: dict[str, dict[str, Any]] = {}
    asset_by_id: dict[str, dict[str, Any]] = {}
    try:
        inv_rows = fetch_table_admin("inventory_items", limit=10000, order_by="item_name") or []
    except Exception:
        inv_rows = []
    for raw in inv_rows:
        if not isinstance(raw, dict):
            continue
        norm = normalize_inventory(raw)
        iid = str(norm.get("id") or "").strip()
        if iid:
            inventory_by_id[iid] = norm

    try:
        ast_rows = fetch_table_admin("assets", limit=10000, order_by="asset_id") or []
    except Exception:
        ast_rows = []
    for raw in ast_rows:
        if not isinstance(raw, dict):
            continue
        norm = normalize_asset(raw)
        aid = str(norm.get("id") or "").strip()
        if aid:
            asset_by_id[aid] = norm

    return inventory_by_id, asset_by_id


def _linked_inventory_id(row: dict[str, Any]) -> str:
    return str(row.get("linked_inventory_id") or row.get("inventory_item_id") or "").strip()


def _linked_asset_id(row: dict[str, Any]) -> str:
    return str(row.get("linked_asset_id") or row.get("asset_id") or "").strip()


def _copy_image_fields(base: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key in _IMAGE_FIELDS:
        if key in source:
            merged[key] = source.get(key)
    return merged


def _resolve_linked_catalog_row(
    row: dict[str, Any],
    *,
    approved_only: bool,
) -> dict[str, Any] | None:
    inventory_by_id, asset_by_id = _catalog_image_maps_cached()
    inv_id = _linked_inventory_id(row)
    ast_id = _linked_asset_id(row)
    item_class = str(row.get("item_class") or "").strip()

    def _usable(record: dict[str, Any] | None) -> bool:
        if not record:
            return False
        if approved_only:
            return record_has_item_image(record)
        return has_stored_item_image(record)

    if item_class == "Inventory" and inv_id:
        linked = inventory_by_id.get(inv_id)
        if _usable(linked):
            return linked
    if item_class == "Asset" and ast_id:
        linked = asset_by_id.get(ast_id)
        if _usable(linked):
            return linked
    if inv_id:
        linked = inventory_by_id.get(inv_id)
        if _usable(linked):
            return linked
    if ast_id:
        linked = asset_by_id.get(ast_id)
        if _usable(linked):
            return linked
    return None


def pricing_guide_image_is_inherited(row: dict[str, Any]) -> bool:
    if has_stored_item_image(row):
        return False
    return _resolve_linked_catalog_row(row, approved_only=False) is not None


def pricing_guide_display_record(row: dict[str, Any]) -> dict[str, Any]:
    """Row shape for preview UI, inheriting photo fields from linked inventory/asset when needed."""
    if has_stored_item_image(row):
        return row
    linked = _resolve_linked_catalog_row(row, approved_only=False)
    if linked:
        return _copy_image_fields(row, linked)
    return row


def pricing_guide_has_image(row: dict[str, Any]) -> bool:
    return get_pricing_guide_image_url(row) is not None


def get_pricing_guide_image_url(row: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    if record_has_item_image(row):
        return resolve_item_image_url(row, expires_in=expires_in)
    linked = _resolve_linked_catalog_row(row, approved_only=True)
    if linked:
        return resolve_item_image_url(linked, expires_in=expires_in)
    return None


def get_pricing_guide_stored_image_url(row: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    """Detail preview URL, including inherited stored photos."""
    display = pricing_guide_display_record(row)
    return resolve_stored_item_image_url(display, expires_in=expires_in)


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


def clear_pricing_guide_image(item_id: str) -> ServiceResult:
    return clear_item_image(table="pricing_guide_items", record_id=item_id)
