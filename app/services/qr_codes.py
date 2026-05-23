"""QR helpers for inventory items (PNG generation, stable values, uniqueness checks)."""

from __future__ import annotations

import io
import secrets
import uuid
from typing import Any, Callable
from urllib.parse import quote

_TABLE = "inventory_items"


def generate_inventory_qr_token() -> str:
    """Random URL-safe token for inventory QR deep links."""
    return secrets.token_urlsafe(24)


def inventory_qr_link_url(*, sku: str, qr_token: str, app_base_url: str) -> str:
    """
    Mobile inventory scan URL.

    Format: ``{APP_BASE_URL}/?qr=inventory&sku={sku}&token={qr_token}``
    """
    base = str(app_base_url or "").strip().rstrip("/")
    sku_q = quote(str(sku or "").strip(), safe="")
    token_q = quote(str(qr_token or "").strip(), safe="")
    if not base or not sku_q or not token_q:
        return ""
    return f"{base}/?qr=inventory&sku={sku_q}&token={token_q}"


def inventory_scan_link_url(*, qr_code_value: str, app_base_url: str, sku: str = "", qr_token: str = "") -> str:
    """
    Full URL for inventory QR labels.

    Prefers tokenized mobile URL when ``sku`` and ``qr_token`` are provided.
    Falls back to legacy ``?page=Scan%20Inventory&code=`` format.
    """
    if sku and qr_token:
        link = inventory_qr_link_url(sku=sku, qr_token=qr_token, app_base_url=app_base_url)
        if link:
            return link
    b = str(app_base_url or "").strip().rstrip("/")
    v = str(qr_code_value or "").strip()
    if not b or not v:
        return v
    page_q = quote("Scan Inventory", safe="")
    code_q = quote(v, safe="")
    return f"{b}/?page={page_q}&code={code_q}"


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
