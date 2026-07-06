"""Printable inventory QR labels (PDF/PNG) and DuraLabel bulk export (CSV/ZIP)."""

from __future__ import annotations

import csv
import io
import re
import textwrap
import zipfile
from datetime import date
from typing import Any

try:
    from app.services.inventory_display_helpers import (
        inventory_qr_embed_subject,
        resolve_inventory_qr_value,
        resolve_inventory_sku,
    )
    from app.services.qr_codes import generate_qr_png_bytes
except ImportError:
    from services.inventory_display_helpers import (  # type: ignore
        inventory_qr_embed_subject,
        resolve_inventory_qr_value,
        resolve_inventory_sku,
    )
    from services.qr_codes import generate_qr_png_bytes  # type: ignore


def inventory_item_description(item: dict[str, Any]) -> str:
    for key in ("description", "item_name", "name"):
        val = str(item.get(key) or "").strip()
        if val:
            return val
    return "(no description)"


def inventory_label_download_basename(item: dict[str, Any]) -> str:
    sku = resolve_inventory_sku(item)
    safe = re.sub(r"[^\w.-]+", "_", sku, flags=re.UNICODE)
    safe = safe.strip("._") or "inventory_item"
    return f"{safe}_inv_label"


def inventory_qr_subject(item: dict[str, Any]) -> str:
    try:
        from app.services.inventory_service import generate_inventory_qr_value
    except ImportError:
        from services.inventory_service import generate_inventory_qr_value  # type: ignore
    url = str(generate_inventory_qr_value(item) or "").strip()
    if url.startswith("http"):
        return url
    return inventory_qr_embed_subject(item)


def inventory_item_has_thumbnail(item: dict[str, Any]) -> bool:
    """True when item has a stored image path (no network/local read)."""
    try:
        from app.services.inventory_images import inventory_display_record
        from app.services.item_images import has_stored_item_image
    except ImportError:
        from services.inventory_images import inventory_display_record  # type: ignore
        from services.item_images import has_stored_item_image  # type: ignore
    return has_stored_item_image(inventory_display_record(item))


def load_inventory_thumbnail_bytes(item: dict[str, Any]) -> bytes | None:
    """Load stored thumbnail bytes for label rendering."""
    try:
        from app.db import _local_file_path_for_storage, _storage_is_local, create_signed_url
        from app.services.inventory_images import inventory_display_record
        from app.services.item_images import _bucket_for_image_path, has_stored_item_image
    except ImportError:
        from db import _local_file_path_for_storage, _storage_is_local, create_signed_url  # type: ignore
        from services.inventory_images import inventory_display_record  # type: ignore
        from services.item_images import _bucket_for_image_path, has_stored_item_image  # type: ignore

    display = inventory_display_record(item)
    if not has_stored_item_image(display):
        return None

    path = str(display.get("image_path") or "").strip()
    if path:
        bucket = _bucket_for_image_path(path)
        if _storage_is_local():
            try:
                local_path = _local_file_path_for_storage(path, bucket)
                if local_path.is_file():
                    return local_path.read_bytes()
            except Exception:
                pass
        else:
            try:
                import urllib.request

                signed = create_signed_url(path, expires_in=600, bucket=bucket)
                if signed.startswith("http"):
                    with urllib.request.urlopen(signed, timeout=30) as resp:
                        return resp.read()
            except Exception:
                pass

    public = str(display.get("image_url") or "").strip()
    if public.startswith("http"):
        try:
            import urllib.request

            with urllib.request.urlopen(public, timeout=30) as resp:
                return resp.read()
        except Exception:
            pass
    return None


def _fit_label_text_layout(
    description: str,
    sku: str,
    text_w: float,
    text_h: float,
    *,
    unit_scale: float = 1.0,
) -> dict[str, Any]:
    """Pick the largest description/SKU fonts that fit the text region."""
    sku_pt = 10.0
    sku_line_h = (sku_pt + 2.5) * unit_scale
    best: dict[str, Any] | None = None

    for desc_pt in (14.0, 13.0, 12.0, 11.0, 10.0, 9.0, 8.0):
        line_h = (desc_pt + 2.5) * unit_scale
        char_w = max(desc_pt * 0.5 * unit_scale, 1.0)
        wrap_chars = max(6, min(48, int(text_w / char_w)))
        lines = textwrap.wrap(description, width=wrap_chars)[:3]
        if not lines:
            lines = [(description or "—")[:wrap_chars]]
        block_h = len(lines) * line_h + sku_line_h
        if block_h <= text_h:
            best = {
                "desc_pt": desc_pt,
                "desc_size": desc_pt * unit_scale,
                "sku_pt": sku_pt,
                "sku_size": sku_pt * unit_scale,
                "line_h": line_h,
                "sku_line_h": sku_line_h,
                "lines": lines,
                "block_h": block_h,
            }
            break

    if best is None:
        desc_pt = 8.0
        line_h = (desc_pt + 2.5) * unit_scale
        wrap_chars = max(6, int(text_w / max(desc_pt * 0.5 * unit_scale, 1.0)))
        lines = textwrap.wrap(description, width=wrap_chars)[:3] or [(description or "—")[:wrap_chars]]
        block_h = len(lines) * line_h + sku_line_h
        best = {
            "desc_pt": desc_pt,
            "desc_size": desc_pt * unit_scale,
            "sku_pt": sku_pt,
            "sku_size": sku_pt * unit_scale,
            "line_h": line_h,
            "sku_line_h": sku_line_h,
            "lines": lines,
            "block_h": min(block_h, text_h),
        }
    best["sku_text"] = f"SKU: {sku}"[:120]
    return best


def _pil_font(size_px: int, *, bold: bool = False):
    from PIL import ImageFont

    size_px = max(8, int(size_px))
    names = ("arialbd.ttf", "arial.ttf") if bold else ("arial.ttf", "DejaVuSans.ttf")
    for name in names:
        try:
            return ImageFont.truetype(name, size_px)
        except OSError:
            continue
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size_px)
    except OSError:
        return ImageFont.load_default()


def _draw_pdf_label_text(
    c,
    *,
    text_x: float,
    y_bottom: float,
    text_w: float,
    text_h: float,
    description: str,
    sku: str,
) -> None:
    layout = _fit_label_text_layout(description, sku, text_w, text_h, unit_scale=1.0)
    padding = max(0.0, (text_h - layout["block_h"]) / 2)
    y = y_bottom + padding + layout["block_h"] - layout["desc_pt"] * 0.85

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", layout["desc_pt"])
    for line in layout["lines"]:
        c.drawString(text_x, y, str(line)[:120])
        y -= layout["line_h"]

    y -= layout["line_h"] * 0.12
    c.setFont("Helvetica-Bold", layout["sku_pt"])
    c.drawString(text_x, max(y_bottom + 2, y), layout["sku_text"])


def _draw_png_label_text(
    draw,
    *,
    text_x: int,
    y_top: int,
    text_w: int,
    text_h: int,
    description: str,
    sku: str,
) -> None:
    unit_scale = text_h / 64.0
    layout = _fit_label_text_layout(description, sku, float(text_w), float(text_h), unit_scale=unit_scale)
    desc_font = _pil_font(int(layout["desc_size"]), bold=True)
    sku_font = _pil_font(int(layout["sku_size"]), bold=True)

    y = int(y_top + (text_h - layout["block_h"]) / 2)
    for line in layout["lines"]:
        draw.text((text_x, y), str(line)[:120], fill=(0, 0, 0), font=desc_font)
        y += int(layout["line_h"])

    y += int(layout["line_h"] * 0.1)
    draw.text((text_x, min(y_top + text_h - int(layout["sku_size"]) - 2, y)), layout["sku_text"], fill=(0, 0, 0), font=sku_font)


def _square_image_bytes(image_bytes: bytes, size_px: int) -> bytes:
    """Fit image into a square canvas (same aspect treatment as QR block)."""
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((size_px, size_px), Image.Resampling.LANCZOS)
    sq = Image.new("RGB", (size_px, size_px), "white")
    ox = (size_px - img.width) // 2
    oy = (size_px - img.height) // 2
    sq.paste(img, (ox, oy))
    out = io.BytesIO()
    sq.save(out, format="JPEG", quality=88)
    return out.getvalue()


def inventory_label_pdf_bytes(item: dict[str, Any], qr_text: str) -> bytes:
    """
    Landscape label (4.0\" × 1.0\"): QR and product image equal squares, description + SKU on the right.
    """
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    w_pt, h_pt = 4.0 * inch, 1.0 * inch
    margin = 0.05 * inch
    gap = 0.05 * inch
    square_sz = h_pt - 2 * margin

    c = canvas.Canvas(buf, pagesize=(w_pt, h_pt))
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w_pt, h_pt, fill=1, stroke=0)

    sku = resolve_inventory_sku(item)
    description = inventory_item_description(item)
    y_square = (h_pt - square_sz) / 2
    x = margin

    c.drawImage(
        ImageReader(io.BytesIO(generate_qr_png_bytes(qr_text))),
        x,
        y_square,
        width=square_sz,
        height=square_sz,
        mask="auto",
    )
    x += square_sz + gap

    thumb_bytes = load_inventory_thumbnail_bytes(item)
    if thumb_bytes:
        try:
            sq_bytes = _square_image_bytes(thumb_bytes, max(48, int(square_sz)))
            c.drawImage(
                ImageReader(io.BytesIO(sq_bytes)),
                x,
                y_square,
                width=square_sz,
                height=square_sz,
                mask="auto",
            )
            x += square_sz + gap
        except Exception:
            pass

    text_x = x
    text_right = w_pt - margin
    text_w = text_right - text_x
    text_h = square_sz
    _draw_pdf_label_text(
        c,
        text_x=text_x,
        y_bottom=margin,
        text_w=text_w,
        text_h=text_h,
        description=description,
        sku=sku,
    )

    c.save()
    return buf.getvalue()


def inventory_label_2x1_sticker_pdf_bytes(item: dict[str, Any], qr_text: str) -> bytes:
    """Landscape 4\" × 1\" sticker (same layout as Print Label)."""
    return inventory_label_pdf_bytes(item, qr_text)


def inventory_label_2x1_sticker_download_filename(item: dict[str, Any]) -> str:
    return f"{inventory_label_download_basename(item)}_4x1.pdf"


def inventory_label_png_bytes(item: dict[str, Any], qr_text: str) -> bytes:
    """PNG fallback matching 4\" × 1\" layout at 300 DPI."""
    from PIL import Image, ImageDraw

    dpi = 300
    w_px, h_px = 4 * dpi, 1 * dpi
    margin = int(0.05 * dpi)
    gap = int(0.05 * dpi)
    square_px = h_px - 2 * margin

    im = Image.new("RGB", (w_px, h_px), "white")
    draw = ImageDraw.Draw(im)

    x = margin
    y_square = margin

    qr_raw = generate_qr_png_bytes(qr_text)
    qr_img = Image.open(io.BytesIO(qr_raw)).convert("RGB")
    qr_img = qr_img.resize((square_px, square_px), Image.Resampling.LANCZOS)
    im.paste(qr_img, (x, y_square))
    x += square_px + gap

    thumb_bytes = load_inventory_thumbnail_bytes(item)
    if thumb_bytes:
        try:
            sq_bytes = _square_image_bytes(thumb_bytes, square_px)
            thumb = Image.open(io.BytesIO(sq_bytes)).convert("RGB")
            im.paste(thumb, (x, y_square))
            x += square_px + gap
        except Exception:
            pass

    sku = resolve_inventory_sku(item)
    description = inventory_item_description(item)
    text_x = x
    text_w = w_px - margin - text_x
    text_h = square_px
    _draw_png_label_text(
        draw,
        text_x=text_x,
        y_top=y_square,
        text_w=text_w,
        text_h=text_h,
        description=description,
        sku=sku,
    )

    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


def inventory_label_for_download(item: dict[str, Any], qr_text: str) -> tuple[bytes, str, str]:
    base = inventory_label_download_basename(item)
    try:
        return inventory_label_pdf_bytes(item, qr_text), "application/pdf", f"{base}.pdf"
    except Exception:
        return inventory_label_png_bytes(item, qr_text), "image/png", f"{base}.png"


def build_inventory_labels_csv(items: list[dict[str, Any]]) -> str:
    """CSV for DuraLabel variable import: SKU, description, scan URL, image path."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "sku",
            "description",
            "scan_url",
            "qr_code_value",
            "image_file",
            "label_pdf",
        ]
    )
    for item in items:
        slug = inventory_label_download_basename(item)
        thumb_ext = ""
        if inventory_item_has_thumbnail(item):
            thumb_ext = f"images/{slug}.jpg"
        writer.writerow(
            [
                resolve_inventory_sku(item),
                inventory_item_description(item),
                inventory_qr_subject(item),
                resolve_inventory_qr_value(item),
                thumb_ext,
                f"labels/{slug}.pdf",
            ]
        )
    return buf.getvalue()


def build_inventory_labels_zip(items: list[dict[str, Any]]) -> bytes:
    """ZIP bundle: CSV + per-item PDF labels, QR PNGs, and thumbnail images."""
    if not items:
        items = []
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("inventory_labels.csv", build_inventory_labels_csv(items))
        for item in items:
            slug = inventory_label_download_basename(item)
            subject = inventory_qr_subject(item)
            try:
                pdf_bytes = inventory_label_pdf_bytes(item, subject)
                zf.writestr(f"labels/{slug}.pdf", pdf_bytes)
            except Exception:
                zf.writestr(f"labels/{slug}.png", inventory_label_png_bytes(item, subject))
            zf.writestr(f"qr/{slug}_qr.png", generate_qr_png_bytes(subject))
            thumb = load_inventory_thumbnail_bytes(item)
            if thumb:
                zf.writestr(f"images/{slug}.jpg", thumb)
    return buf.getvalue()


def inventory_labels_zip_filename(*, item_count: int | None = None) -> str:
    stamp = date.today().isoformat()
    suffix = f"_{item_count}_items" if item_count else ""
    return f"inventory_labels_{stamp}{suffix}.zip"


def inventory_labels_csv_filename(*, item_count: int | None = None) -> str:
    stamp = date.today().isoformat()
    suffix = f"_{item_count}_items" if item_count else ""
    return f"inventory_labels_{stamp}{suffix}.csv"
