"""Resize, upload, and resolve inventory item images.

Single display resolver: ``get_inventory_image_url`` → ``inventory_thumbnail_html`` /
``render_inventory_item_thumbnail``.

Fallback order:
  1. Inventory item image fields
  2. Linked Pricing Guide image fields
  3. None (UI shows category placeholder 📦)
"""

from __future__ import annotations

from typing import Any

import html

import streamlit as st

from app.services.item_images import (
    INVENTORY_IMAGE_BUCKET,
    ITEM_IMAGE_FIELDS,
    clear_item_image,
    clear_item_image_url_cache,
    has_stored_item_image,
    persist_item_image,
    record_has_item_image,
    resolve_image_url_by_field_priority,
    resolve_stored_item_image_url,
    resize_item_image_bytes,
)
from app.services.repository import ServiceResult

__all__ = [
    "INVENTORY_IMAGE_BUCKET",
    "clear_inventory_image",
    "clear_inventory_image_url_cache",
    "get_inventory_image_url",
    "inventory_display_record",
    "inventory_has_image",
    "inventory_image_is_inherited",
    "inventory_image_placeholder_html",
    "inventory_item_image_storage_path",
    "inventory_thumbnail_html",
    "render_inventory_item_thumbnail",
    "resize_inventory_image_bytes",
    "upload_inventory_image",
]

resize_inventory_image_bytes = resize_item_image_bytes


def inventory_item_image_storage_path(item_id: str) -> str:
    """Legacy stable storage key for an item thumbnail (default bucket)."""
    return f"inventory/items/{str(item_id).strip()}.jpg"


def clear_inventory_image_url_cache() -> None:
    clear_item_image_url_cache()


def _copy_image_fields(base: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key in ITEM_IMAGE_FIELDS:
        if key in source:
            merged[key] = source.get(key)
    return merged


def _linked_pricing_row(item: dict[str, Any]) -> dict[str, Any] | None:
    pid = str(item.get("pricing_guide_id") or item.get("pricing_item_id") or "").strip()
    if not pid:
        return None
    try:
        from app.services.pricing_guide_service import cached_pricing_guide_rows
    except ImportError:
        from services.pricing_guide_service import cached_pricing_guide_rows  # type: ignore
    return next((r for r in cached_pricing_guide_rows(include_inactive=True) if str(r.get("id") or "") == pid), None)


def _resolve_linked_image_source(item: dict[str, Any], *, approved_only: bool) -> dict[str, Any] | None:
    def _usable(record: dict[str, Any] | None) -> bool:
        if not record:
            return False
        if approved_only:
            return record_has_item_image(record)
        return has_stored_item_image(record)

    pg_row = _linked_pricing_row(item)
    if _usable(pg_row):
        return pg_row
    return None


def inventory_image_is_inherited(item: dict[str, Any]) -> bool:
    if has_stored_item_image(item):
        return False
    return _resolve_linked_image_source(item, approved_only=False) is not None


def inventory_display_record(item: dict[str, Any]) -> dict[str, Any]:
    if has_stored_item_image(item):
        return item
    linked = _resolve_linked_image_source(item, approved_only=False)
    if linked:
        return _copy_image_fields(item, linked)
    return item


def inventory_has_image(item: dict[str, Any]) -> bool:
    return get_inventory_image_url(item) is not None


_INVENTORY_IMAGE_FIELD_PRIORITY: tuple[str, ...] = (
    "image_url",
    "image_path",
)


def get_inventory_image_url(item: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    """Browser URL for every inventory display: item → linked Pricing Guide → None (placeholder in UI)."""
    url = resolve_image_url_by_field_priority(
        item,
        _INVENTORY_IMAGE_FIELD_PRIORITY,
        expires_in=expires_in,
    )
    if url:
        return url
    linked_pg = _linked_pricing_row(item)
    if linked_pg:
        try:
            from app.services.pricing_guide_images import get_pricing_guide_image_url
        except ImportError:
            from services.pricing_guide_images import get_pricing_guide_image_url  # type: ignore
        return get_pricing_guide_image_url(linked_pg, expires_in=expires_in)
    return None


def inventory_image_placeholder_html(*, category: str = "") -> str:
    _ = category
    return '<span class="ips-inventory-thumb-placeholder">📦</span>'


def inventory_thumbnail_html(
    item: dict[str, Any],
    *,
    css_class: str = "ips-inventory-thumb-img",
    cell_class: str = "ips-inventory-thumb-cell",
) -> str:
    image_url = get_inventory_image_url(item)
    if image_url:
        return (
            f'<span class="{html.escape(cell_class)}">'
            f'<img class="{html.escape(css_class)}" '
            f'src="{html.escape(image_url, quote=True)}" alt="Inventory item image" />'
            f"</span>"
        )
    return f'<span class="{html.escape(cell_class)}">{inventory_image_placeholder_html()}</span>'


def render_inventory_item_thumbnail(
    item: dict[str, Any],
    *,
    width: int = 80,
    use_markdown_cell: bool = True,
) -> None:
    """Streamlit thumbnail — product image or category placeholder."""
    image_url = get_inventory_image_url(item)
    if image_url:
        st.image(image_url, width=width)
        return
    if use_markdown_cell:
        st.markdown(inventory_thumbnail_html(item), unsafe_allow_html=True)
    else:
        st.markdown(
            f'<p style="font-size:2.5rem;margin:0;line-height:1;">📦</p>',
            unsafe_allow_html=True,
        )


def get_inventory_stored_image_url(item: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    display = inventory_display_record(item)
    return resolve_stored_item_image_url(display, expires_in=expires_in)


def upload_inventory_image(
    item_id: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
    existing: dict[str, Any] | None = None,
    replace_existing: bool = False,
    force: bool | None = None,
) -> ServiceResult:
    if force is not None:
        replace_existing = force
    iid = str(item_id or "").strip()
    if not iid:
        return ServiceResult(ok=False, error="Missing inventory item id.")
    if uploaded_file is None:
        return ServiceResult(ok=False, error="No file provided.")
    filename = str(getattr(uploaded_file, "name", "") or "item-image")
    raw = uploaded_file.getvalue()
    if not raw:
        return ServiceResult(ok=False, error="Uploaded file is empty.")
    result = persist_item_image(
        table="inventory_items",
        record_id=iid,
        entity_type="inventory",
        image_bytes=raw,
        filename=filename,
        existing=existing,
        uploaded_by=uploaded_by,
        replace_existing=replace_existing,
    )
    if result.ok and not (isinstance(result.data, dict) and result.data.get("skipped")):
        try:
            from app.services.catalog_image_sync import sync_catalog_images_for_inventory_item
            from app.services.inventory_service import get_inventory_item

            source = get_inventory_item(iid) or existing or {"id": iid}
            sync_catalog_images_for_inventory_item(source)
        except Exception:
            pass
    return result


def clear_inventory_image(item_id: str) -> ServiceResult:
    return clear_item_image(table="inventory_items", record_id=item_id)
