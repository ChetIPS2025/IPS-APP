"""
Business-logic layer for Inventory.

Orchestrates DB writes, QR code generation, image uploads, and cache management.
UI and dialogs should call these functions rather than touching the DB directly.
"""

from __future__ import annotations

import streamlit as st

from app.pages.inventory.queries import (
    bump_data_version,
    check_qr_value_in_use,
    create_inventory_item,
    fetch_all_qr_rows,
    update_inventory_item,
)
from app.pages.inventory.utils import qr_png_bytes


# ---------------------------------------------------------------------------
# QR helpers
# ---------------------------------------------------------------------------

def allocate_unique_qr(
    *, item_id: str, preferred: str | None, exclude_item_id: str | None
) -> str:
    """Allocate a unique INV-* QR value for the given item."""
    try:
        from app.db import fetch_by_match_admin
        from app.services.qr_codes import allocate_unique_inventory_qr_value
    except ImportError:
        from db import fetch_by_match_admin  # type: ignore
        from services.qr_codes import allocate_unique_inventory_qr_value  # type: ignore
    return allocate_unique_inventory_qr_value(
        fetch_by_match_admin=fetch_by_match_admin,
        item_id=item_id,
        preferred=preferred,
        exclude_item_id=exclude_item_id,
    )


def sync_qr_to_storage(item_id: str, qr_value: str) -> None:
    """Upload a QR PNG to storage and set ``qr_code_image_url`` on the row."""
    rid = str(item_id or "").strip()
    qv = str(qr_value or "").strip()
    if not rid or not qv:
        return
    png = qr_png_bytes(qv)
    if not png:
        return
    path = f"inventory/qr/{rid}.png"
    try:
        from app.db import upload_bytes_admin
    except ImportError:
        from db import upload_bytes_admin  # type: ignore
    try:
        upload_bytes_admin(path, png, content_type="image/png")
        update_inventory_item(rid, {"qr_code_image_url": path})
    except Exception:
        pass


def backfill_missing_qr_codes() -> int:
    """Assign ``qr_code_value`` (+ optional PNG) for items missing a QR value."""
    rows = fetch_all_qr_rows()
    n = 0
    for r in rows or []:
        if str(r.get("qr_code_value") or "").strip():
            continue
        rid = str(r.get("id") or "").strip()
        if not rid:
            continue
        try:
            from app.services.qr_codes import inventory_qr_from_item_id
        except ImportError:
            from services.qr_codes import inventory_qr_from_item_id  # type: ignore
        qv = allocate_unique_qr(
            item_id=rid,
            preferred=inventory_qr_from_item_id(rid),
            exclude_item_id=rid,
        )
        update_inventory_item(rid, {"qr_code_value": qv})
        sync_qr_to_storage(rid, qv)
        n += 1
    if n > 0:
        bump_data_version()
    return n


def regenerate_qr_pngs() -> int:
    """Re-upload QR PNGs using the current APP_BASE_URL (so scan URLs in images are current)."""
    try:
        from app.config import settings
    except ImportError:
        from config import settings  # type: ignore
    base = str(getattr(settings, "app_base_url", "") or "").strip()
    if not base:
        raise RuntimeError(
            "APP_BASE_URL is not set. Set it to your live app URL (no trailing slash), then retry."
        )
    rows = fetch_all_qr_rows()
    n = 0
    for r in rows or []:
        rid = str(r.get("id") or "").strip()
        qv = str(r.get("qr_code_value") or "").strip()
        if not rid or not qv:
            continue
        sync_qr_to_storage(rid, qv)
        n += 1
    if n > 0:
        bump_data_version()
    return n


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def get_signed_image_url(image_url: str | None) -> str | None:
    """Return a loadable URL: pass-through for https://, else get signed URL from storage."""
    s = str(image_url or "").strip()
    if not s:
        return None
    if s.startswith("http://") or s.startswith("https://"):
        return s
    try:
        from app.db import create_signed_url
        return create_signed_url(s, expires_in=3600) or None
    except Exception:
        return None


def upload_item_image(item_id: str, uploaded_file) -> str | None:
    """Resize and upload an item image; return the storage path."""
    if uploaded_file is None:
        return None
    raw = uploaded_file.getvalue()
    if not raw:
        return None
    try:
        from app.services.inventory_images import (
            inventory_item_image_storage_path,
            resize_inventory_image_bytes,
        )
    except ImportError:
        from services.inventory_images import (  # type: ignore
            inventory_item_image_storage_path,
            resize_inventory_image_bytes,
        )
    jpeg, ctype = resize_inventory_image_bytes(raw)
    path = inventory_item_image_storage_path(item_id)
    try:
        from app.db import upload_bytes_admin
    except ImportError:
        from db import upload_bytes_admin  # type: ignore
    upload_bytes_admin(path, jpeg, content_type=ctype)
    return path


# ---------------------------------------------------------------------------
# Create / update item orchestration
# ---------------------------------------------------------------------------

def save_new_item(
    *,
    name: str,
    category: str,
    unit: str,
    qty: float,
    reorder: float,
    unit_cost: float | None,
    vendor: str,
    storage_location: str,
    notes: str,
    is_active: bool,
    qr_value: str | None,
    sku: str | None,
    image_file=None,
) -> tuple[bool, str]:
    """
    Create a new inventory item. Returns ``(success, message)``.
    Handles QR allocation, QR image sync, and image upload.
    """
    payload: dict = {
        "item_name": name,
        "category": category,
        "unit": unit or "EA",
        "quantity_on_hand": qty,
        "reorder_point": reorder,
        "unit_cost": unit_cost if (unit_cost or 0) > 0 else None,
        "vendor": vendor,
        "storage_location": storage_location,
        "notes": notes,
        "is_active": is_active,
    }
    if qr_value:
        if check_qr_value_in_use(qr_value, exclude_item_id=None):
            return False, "That QR code value is already in use. Choose another or leave blank to auto-generate."
        payload["qr_code_value"] = qr_value
    if sku:
        payload["sku"] = sku

    try:
        row = create_inventory_item(payload)
    except Exception as exc:
        if "sku" in str(exc).lower():
            return False, (
                f"Could not save: {exc} — run migration "
                "**`sql/028_inventory_sku_txn_created_by.sql`** if SKU column is missing."
            )
        return False, f"Could not save: {exc}"

    rid = str(row.get("id") or "")
    if rid:
        qv = str(row.get("qr_code_value") or "").strip()
        if not qv:
            try:
                from app.services.qr_codes import inventory_qr_from_item_id
            except ImportError:
                from services.qr_codes import inventory_qr_from_item_id  # type: ignore
            qv = allocate_unique_qr(
                item_id=rid,
                preferred=inventory_qr_from_item_id(rid),
                exclude_item_id=rid,
            )
            update_inventory_item(rid, {"qr_code_value": qv})
        sync_qr_to_storage(rid, qv)

        if image_file is not None:
            _save_image_safe(rid, image_file)

    bump_data_version()
    return True, "Inventory item added."


def save_edited_item(
    *,
    item_id: str,
    name: str,
    category: str,
    unit: str,
    qty: float,
    reorder: float,
    unit_cost: float | None,
    vendor: str,
    storage_location: str,
    notes: str,
    is_active: bool,
    qr_value: str | None,
    old_qr_value: str | None,
    sku: str | None,
    image_file=None,
) -> tuple[bool, str]:
    """
    Update an existing inventory item. Returns ``(success, message)``.
    """
    qr_t = str(qr_value or "").strip()
    old_qr = str(old_qr_value or "").strip()
    if qr_t and qr_t != old_qr and check_qr_value_in_use(qr_t, exclude_item_id=item_id):
        return False, "That QR code value is already used by another item."

    payload: dict = {
        "item_name": name,
        "category": category,
        "unit": unit or "EA",
        "quantity_on_hand": qty,
        "reorder_point": reorder,
        "unit_cost": unit_cost if (unit_cost or 0) > 0 else None,
        "vendor": vendor,
        "storage_location": storage_location,
        "notes": notes,
        "is_active": is_active,
        "qr_code_value": qr_t or None,
        "sku": sku or None,
    }

    try:
        update_inventory_item(item_id, payload)
    except Exception as exc:
        if "sku" in str(exc).lower():
            return False, (
                f"Could not update: {exc} — apply "
                "**`sql/028_inventory_sku_txn_created_by.sql`** for SKU support."
            )
        return False, f"Could not update: {exc}"

    final_qr = str(qr_t or old_qr or "").strip()
    if not final_qr:
        try:
            from app.services.qr_codes import inventory_qr_from_item_id
        except ImportError:
            from services.qr_codes import inventory_qr_from_item_id  # type: ignore
        final_qr = allocate_unique_qr(
            item_id=item_id,
            preferred=inventory_qr_from_item_id(item_id),
            exclude_item_id=item_id,
        )
        update_inventory_item(item_id, {"qr_code_value": final_qr})
    sync_qr_to_storage(item_id, final_qr)

    if image_file is not None:
        _save_image_safe(item_id, image_file)

    bump_data_version()
    return True, "Inventory item updated."


def _save_image_safe(item_id: str, image_file) -> None:
    try:
        path = upload_item_image(item_id, image_file)
        if path:
            update_inventory_item(item_id, {"image_url": path})
    except Exception as exc:
        if "image_url" in str(exc).lower() or "column" in str(exc).lower():
            st.warning(
                f"Image was not saved — run migration **`sql/035_inventory_image_url.sql`** "
                f"then try again. ({exc})"
            )
        else:
            st.warning(f"Image upload skipped: {exc}")
