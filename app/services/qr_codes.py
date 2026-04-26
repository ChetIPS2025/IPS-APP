"""QR helpers for inventory items (PNG generation, stable values, uniqueness checks)."""

from __future__ import annotations

import io
import uuid
from typing import Any, Callable

_TABLE = "inventory_items"


def generate_qr_png_bytes(value: str) -> bytes:
    """Render ``value`` as a QR code PNG (requires ``qrcode`` + ``Pillow``)."""
    import qrcode  # type: ignore[import-not-found]

    qr = qrcode.QRCode(version=None, box_size=6, border=2)
    qr.add_data(str(value or "").strip())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def inventory_qr_from_item_id(item_id: str) -> str:
    """Stable token derived from item UUID, e.g. ``INV-`` + first 12 hex chars of id (no dashes)."""
    s = str(item_id or "").replace("-", "").strip()
    if len(s) < 8:
        return f"INV-{uuid.uuid4().hex[:8].upper()}"
    return f"INV-{s[:12].upper()}"


def _qr_taken(
    *,
    fetch_by_match_admin: Callable[..., list[dict[str, Any]]],
    qr_value: str,
    exclude_item_id: str | None,
) -> bool:
    v = str(qr_value or "").strip()
    if not v:
        return True
    rows = fetch_by_match_admin(_TABLE, {"qr_code_value": v}, limit=5)
    if not rows:
        return False
    if exclude_item_id is None:
        return True
    for r in rows:
        if str(r.get("id") or "").strip() != str(exclude_item_id).strip():
            return True
    return False


def allocate_unique_inventory_qr_value(
    *,
    fetch_by_match_admin: Callable[..., list[dict[str, Any]]],
    item_id: str,
    preferred: str | None = None,
    exclude_item_id: str | None = None,
) -> str:
    """
    Return a unique ``qr_code_value`` for an inventory row.

    - If ``preferred`` is set and unique, returns it.
    - Otherwise uses ``INV-{compact_uuid_prefix}`` with collision retries.
    """
    if preferred:
        pv = str(preferred).strip()
        if pv and not _qr_taken(fetch_by_match_admin=fetch_by_match_admin, qr_value=pv, exclude_item_id=exclude_item_id):
            return pv

    base = inventory_qr_from_item_id(item_id)
    if not _qr_taken(fetch_by_match_admin=fetch_by_match_admin, qr_value=base, exclude_item_id=exclude_item_id):
        return base

    for _ in range(40):
        cand = f"INV-{uuid.uuid4().hex[:8].upper()}"
        if not _qr_taken(fetch_by_match_admin=fetch_by_match_admin, qr_value=cand, exclude_item_id=exclude_item_id):
            return cand

    raise RuntimeError("Could not allocate a unique inventory QR code after many attempts.")
