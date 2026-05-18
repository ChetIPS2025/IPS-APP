"""
Pure utility functions for Inventory — no Streamlit, no DB, no side effects.
"""

from __future__ import annotations

import base64
import html
import urllib.parse


_PLACEHOLDER_THUMB = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def qr_embed_subject(qr_value: str) -> str:
    """Return the string encoded inside the printed QR (app scan URL when APP_BASE_URL is set)."""
    try:
        from app.config import settings
        from app.services.qr_codes import inventory_scan_link_url
    except ImportError:
        from config import settings  # type: ignore
        from services.qr_codes import inventory_scan_link_url  # type: ignore
    return inventory_scan_link_url(
        qr_code_value=qr_value,
        app_base_url=getattr(settings, "app_base_url", "") or "",
    )


def qr_png_bytes(qr_value: str) -> bytes | None:
    """Generate a QR PNG for the given value (scan URL preferred). Returns None on failure."""
    try:
        from app.services.qr_codes import generate_qr_png_bytes
    except ImportError:
        from services.qr_codes import generate_qr_png_bytes  # type: ignore
    subj = qr_embed_subject(qr_value)
    for cand in (subj, str(qr_value or "").strip()):
        if not cand:
            continue
        try:
            return generate_qr_png_bytes(cand)
        except Exception:
            continue
    return None


def qr_img_html(data: str, *, size: int = 180) -> str:
    """Return an HTML ``<img>`` block for the given QR value; empty string if no value."""
    raw = str(data or "").strip()
    if not raw:
        return ""
    png = qr_png_bytes(raw)
    if png:
        b64 = base64.b64encode(png).decode("ascii")
        src = f"data:image/png;base64,{b64}"
    else:
        enc = urllib.parse.quote(qr_embed_subject(raw), safe="")
        src = html.escape(
            f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={enc}",
            quote=True,
        )
    return (
        f'<div class="ips-inv-qr-wrap">'
        f'<img src="{src}" width="{size}" height="{size}" alt="QR code"/>'
        f"</div>"
    )


def inventory_label_html(
    *, item_name: str, sku: str, qr_value: str, item_id: str
) -> str:
    """Printable label: item name + QR image + scan code."""
    _ = sku  # kept in signature; label uses name + QR + code only
    nm = html.escape(str(item_name or "").strip() or "—")
    qv = html.escape(str(qr_value or "").strip() or "—")
    qr_block = qr_img_html(str(qr_value or "").strip(), size=240)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Inventory label</title>"
        "<style>body{font-family:system-ui,sans-serif;padding:16px;color:#111;} "
        ".code{font-size:1.25rem;font-weight:700;letter-spacing:0.02em;margin-top:8px;} "
        "h1{font-size:1.1rem;}</style></head><body>"
        f"<h1>{nm}</h1>"
        f"{qr_block}"
        f'<p class="code">{qv}</p>'
        f"<p style='font-size:0.75rem;color:#555;margin-top:16px;'>"
        f"Item id: {html.escape(str(item_id or '')[:36])}</p>"
        "</body></html>"
    )


def thumb_placeholder() -> str:
    return _PLACEHOLDER_THUMB


def inv_thumb_html(image_url: str | None, *, size: int = 36) -> str:
    """Return an HTML img tag for a thumbnail, or a box emoji placeholder."""
    from app.pages.inventory.queries import fetch_inventory_image_signed_url_cached  # avoid circular

    raw = str(image_url or "").strip()
    url = fetch_inventory_image_signed_url_cached(raw) if raw else None
    if not url:
        return '<p style="font-size:1.35rem;margin:0;line-height:1;">📦</p>'
    esc = html.escape(url, quote=True)
    return (
        f'<img src="{esc}" width="{size}" height="{size}" loading="lazy" '
        f'decoding="async" alt="" style="object-fit:cover;border-radius:4px;display:block;"/>'
    )


def thumb_display_url(image_url: str | None) -> str:
    """URL suitable for a dataframe ImageColumn; falls back to placeholder."""
    from app.pages.inventory.queries import fetch_inventory_image_signed_url_cached

    raw = str(image_url or "").strip()
    return fetch_inventory_image_signed_url_cached(raw) or _PLACEHOLDER_THUMB


def format_stock_status(quantity_on_hand: float, reorder_point: float) -> str:
    """Return a human-readable stock status string."""
    if quantity_on_hand <= 0:
        return "Out of Stock"
    if quantity_on_hand <= reorder_point:
        return "Low Stock"
    return "In Stock"


def render_inventory_status_badge(is_active: bool) -> str:
    """Return an HTML badge for active/inactive status."""
    if is_active:
        return (
            '<span style="background:#dcfce7;color:#166534;border-radius:4px;'
            'padding:2px 8px;font-size:0.75rem;font-weight:600;">Active</span>'
        )
    return (
        '<span style="background:#f1f5f9;color:#64748b;border-radius:4px;'
        'padding:2px 8px;font-size:0.75rem;font-weight:600;">Inactive</span>'
    )


def render_stock_level_badge(quantity_on_hand: float, reorder_point: float) -> str:
    """Return an HTML badge for stock level."""
    status = format_stock_status(quantity_on_hand, reorder_point)
    if status == "Out of Stock":
        color = "#fef2f2"
        text_color = "#991b1b"
    elif status == "Low Stock":
        color = "#fff7ed"
        text_color = "#9a3412"
    else:
        color = "#f0fdf4"
        text_color = "#166534"
    return (
        f'<span style="background:{color};color:{text_color};border-radius:4px;'
        f'padding:2px 8px;font-size:0.75rem;font-weight:600;">{status}</span>'
    )


def render_purchase_link(url: str, label: str | None = None) -> str:
    """Return a clean clickable HTML anchor for a purchase/vendor URL."""
    u = str(url or "").strip()
    if not u:
        return ""
    if not u.startswith("http://") and not u.startswith("https://"):
        u = "https://" + u
    display = str(label or "").strip() or _shorten_url(u)
    esc_u = html.escape(u, quote=True)
    esc_d = html.escape(display)
    return (
        f'<a href="{esc_u}" target="_blank" rel="noopener noreferrer" '
        f'style="color:#2563eb;text-decoration:underline;">{esc_d}</a>'
    )


def _shorten_url(url: str) -> str:
    """Return hostname + first path segment, e.g. 'grainger.com/…'."""
    try:
        p = urllib.parse.urlparse(url)
        host = p.netloc or url[:40]
        path = p.path.split("/")[1] if p.path and len(p.path) > 1 else ""
        return f"{host}/{path}…" if path else host
    except Exception:
        return url[:40] + ("…" if len(url) > 40 else "")
