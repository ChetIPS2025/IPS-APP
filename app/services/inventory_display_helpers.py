"""Display helpers for inventory SKU labels and QR codes."""

from __future__ import annotations

import re
from typing import Any

_UUID_FRAG_RE = re.compile(r"^[0-9a-f]{8}$", re.I)


def resolve_inventory_sku(row: dict[str, Any]) -> str:
    """Return a friendly SKU; recreate from item id when missing or uuid-like."""
    sku = str(row.get("sku") or row.get("item_number") or "").strip()
    iid = str(row.get("id") or "").strip()
    compact = iid.replace("-", "")
    generated = f"INV-{compact[:8].upper()}" if len(compact) >= 8 else ""

    if sku and not _UUID_FRAG_RE.match(sku):
        if iid and sku == iid[:8]:
            return generated or sku
        return sku
    if generated:
        return generated
    return sku or "—"


def resolve_inventory_qr_value(row: dict[str, Any]) -> str:
    """Stable scan token for an inventory row."""
    qrv = str(row.get("qr_code_value") or "").strip()
    if qrv:
        return qrv
    iid = str(row.get("id") or "").strip()
    if not iid:
        return ""
    try:
        from app.services.qr_codes import inventory_qr_from_item_id
    except ImportError:
        from services.qr_codes import inventory_qr_from_item_id  # type: ignore
    return inventory_qr_from_item_id(iid)


def inventory_qr_embed_subject(qr_code_value: str) -> str:
    """Payload encoded in inventory QR images."""
    qrv = str(qr_code_value or "").strip()
    if not qrv:
        return ""
    try:
        from app.config import settings
        from app.services.qr_codes import inventory_scan_link_url
    except ImportError:
        from config import settings  # type: ignore
        from services.qr_codes import inventory_scan_link_url  # type: ignore
    base = str(getattr(settings, "app_base_url", "") or "").strip().rstrip("/")
    if base:
        return inventory_scan_link_url(qr_code_value=qrv, app_base_url=base)
    return qrv


def inventory_qr_png_bytes(row: dict[str, Any]) -> bytes | None:
    """PNG bytes for the inventory item QR, or None if generation fails."""
    qrv = resolve_inventory_qr_value(row)
    if not qrv:
        return None
    try:
        from app.services.qr_codes import generate_qr_png_bytes
    except ImportError:
        from services.qr_codes import generate_qr_png_bytes  # type: ignore
    for cand in (inventory_qr_embed_subject(qrv), qrv):
        if not cand:
            continue
        try:
            return generate_qr_png_bytes(cand)
        except Exception:
            continue
    return None
