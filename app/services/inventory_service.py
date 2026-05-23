"""
Inventory module — Supabase reads/writes.

Schema assumptions: ``inventory_items`` (or ``inventory``) with sku, item_name, category,
storage_location, quantity_on_hand, reorder_point, unit_cost, vendor, status, image fields.
"""

from __future__ import annotations

from typing import Any

from app.services.inventory_images import (
    clear_inventory_image_url_cache,
    get_inventory_image_url,
    inventory_has_image,
    upload_inventory_image as _upload_inventory_image_storage,
)
from app.services.phase2_modules_service import (
    delete_inventory_item,
    list_inventory,
    normalize_inventory,
    save_inventory_item,
)
from app.services.repository import ServiceResult, clear_all_data_caches

__all__ = [
    "clear_inventory_cache",
    "delete_inventory_item",
    "get_inventory",
    "get_inventory_image_url",
    "get_inventory_item",
    "inventory_has_image",
    "list_inventory",
    "normalize_inventory",
    "save_inventory_item",
    "update_inventory_item",
    "upload_inventory_image",
]


def clear_inventory_cache() -> None:
    clear_all_data_caches()
    clear_inventory_image_url_cache()


def get_inventory() -> list[dict[str, Any]]:
    try:
        from app.pages._core._data import _DEMO_INVENTORY
    except ImportError:
        from pages._core._data import _DEMO_INVENTORY  # type: ignore
    rows, _ = list_inventory(demo=list(_DEMO_INVENTORY))
    return rows


def get_inventory_item(item_id: str) -> dict[str, Any] | None:
    iid = str(item_id or "").strip()
    if not iid:
        return None
    for row in get_inventory():
        if str(row.get("id") or "") == iid:
            return row
    return None


def update_inventory_item(item_id: str, data: dict[str, Any]) -> ServiceResult:
    result = save_inventory_item(data, row_id=str(item_id or "").strip())
    if result.ok:
        clear_inventory_cache()
    return result


def upload_inventory_image(item_id: str, uploaded_file: Any, *, uploaded_by: str | None = None) -> ServiceResult:
    result = _upload_inventory_image_storage(item_id, uploaded_file, uploaded_by=uploaded_by)
    if result.ok:
        clear_inventory_cache()
    return result
