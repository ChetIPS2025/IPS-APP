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


def _label_fonts():
    from PIL import ImageFont

    try:
        return ImageFont.truetype("arial.ttf", 17), ImageFont.truetype("arial.ttf", 13)
    except OSError:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", 17), ImageFont.truetype("DejaVuSans.ttf", 13)
        except OSError:
            default = ImageFont.load_default()
            return default, default


def inventory_label_pdf_bytes(item: dict[str, Any], qr_text: str) -> bytes:
    """
    Portrait label (2.0\" × 2.5\"): thumbnail, description, SKU, QR scan code.
    """
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    w_pt, h_pt = 2.0 * inch, 2.5 * inch
    c = canvas.Canvas(buf, pagesize=(w_pt, h_pt))
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w_pt, h_pt, fill=1, stroke=0)

    margin = 0.12 * inch
    sku = resolve_inventory_sku(item)
    description = inventory_item_description(item)

    y_top = h_pt - margin
    thumb_bytes = load_inventory_thumbnail_bytes(item)
    if thumb_bytes:
        try:
            from PIL import Image

            thumb_h = 0.55 * inch
            thumb_w = w_pt - 2 * margin
            img = Image.open(io.BytesIO(thumb_bytes)).convert("RGB")
            img.thumbnail((int(thumb_w), int(thumb_h)), Image.Resampling.LANCZOS)
            thumb_out = io.BytesIO()
            img.save(thumb_out, format="JPEG", quality=88)
            thumb_out.seek(0)
            ir = ImageReader(thumb_out)
            draw_w, draw_h = img.size
            x_thumb = margin + (thumb_w - draw_w) / 2
            y_thumb = y_top - draw_h
            c.drawImage(ir, x_thumb, y_thumb, width=draw_w, height=draw_h, mask="auto")
            y_top = y_thumb - 0.08 * inch
        except Exception:
            pass

    qr_sz = 0.82 * inch
    y_qr = margin
    c.drawImage(
        ImageReader(io.BytesIO(generate_qr_png_bytes(qr_text))),
        (w_pt - qr_sz) / 2,
        y_qr,
        width=qr_sz,
        height=qr_sz,
        mask="auto",
    )

    y = y_top
    line_gap = 8.5
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 8)
    for line in textwrap.wrap(description, width=34)[:3]:
        if y <= y_qr + qr_sz + 0.08 * inch:
            break
        c.drawString(margin, y, line[:120])
        y -= line_gap

    y -= 1
    c.setFont("Helvetica", 7)
    for line in textwrap.wrap(f"SKU: {sku}", width=40)[:2]:
        if y <= y_qr + qr_sz + 0.06 * inch:
            break
        c.drawString(margin, y, line[:120])
        y -= line_gap - 1

    c.save()
    return buf.getvalue()


def inventory_label_2x1_sticker_pdf_bytes(item: dict[str, Any], qr_text: str) -> bytes:
    """Landscape 2\" × 1\" sticker: QR left, thumbnail + text right."""
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    w_pt, h_pt = 2.0 * inch, 1.0 * inch
    c = canvas.Canvas(buf, pagesize=(w_pt, h_pt))
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w_pt, h_pt, fill=1, stroke=0)

    margin = 0.06 * inch
    gap = 0.05 * inch
    qr_sz = min(0.72 * inch, h_pt - 2 * margin)
    x_qr = margin
    y_qr = (h_pt - qr_sz) / 2
    c.drawImage(
        ImageReader(io.BytesIO(generate_qr_png_bytes(qr_text))),
        x_qr,
        y_qr,
        width=qr_sz,
        height=qr_sz,
        mask="auto",
    )

    text_x = x_qr + qr_sz + gap
    text_right = w_pt - margin
    max_w_pt = text_right - text_x
    wrap_chars = max(8, min(24, int(max_w_pt / 3.4)))

    sku = resolve_inventory_sku(item)
    description = inventory_item_description(item)
    y = y_qr + qr_sz - 5
    line_h = 7.5

    thumb_bytes = load_inventory_thumbnail_bytes(item)
    if thumb_bytes and max_w_pt > 0.35 * inch:
        try:
            from PIL import Image

            mini_h = min(0.28 * inch, qr_sz * 0.45)
            mini_w = max_w_pt * 0.35
            img = Image.open(io.BytesIO(thumb_bytes)).convert("RGB")
            img.thumbnail((int(mini_w), int(mini_h)), Image.Resampling.LANCZOS)
            thumb_out = io.BytesIO()
            img.save(thumb_out, format="JPEG", quality=88)
            thumb_out.seek(0)
            ir = ImageReader(thumb_out)
            draw_w, draw_h = img.size
            c.drawImage(ir, text_x, y - draw_h + 2, width=draw_w, height=draw_h, mask="auto")
            text_x += draw_w + gap * 0.6
            max_w_pt = text_right - text_x
            wrap_chars = max(8, min(22, int(max_w_pt / 3.4)))
        except Exception:
            pass

    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 6.5)
    for line in textwrap.wrap(description, width=wrap_chars)[:2]:
        if y < margin + line_h:
            break
        c.drawString(text_x, y, line[:100])
        y -= line_h

    if y >= margin:
        c.setFont("Helvetica", 5.8)
        c.drawString(text_x, max(margin, y - 1), f"SKU: {sku}"[:100])

    c.save()
    return buf.getvalue()


def inventory_label_2x1_sticker_download_filename(item: dict[str, Any]) -> str:
    return f"{inventory_label_download_basename(item)}_2x1.pdf"


def inventory_label_png_bytes(item: dict[str, Any], qr_text: str) -> bytes:
    from PIL import Image, ImageDraw

    w_px, h_px = 400, 520
    im = Image.new("RGB", (w_px, h_px), "white")
    draw = ImageDraw.Draw(im)
    font_title, font_meta = _label_fonts()

    y = 12
    margin = 14
    thumb_bytes = load_inventory_thumbnail_bytes(item)
    if thumb_bytes:
        try:
            thumb = Image.open(io.BytesIO(thumb_bytes)).convert("RGB")
            thumb.thumbnail((w_px - 2 * margin, 120), Image.Resampling.LANCZOS)
            x_thumb = (w_px - thumb.width) // 2
            im.paste(thumb, (x_thumb, y))
            y += thumb.height + 10
        except Exception:
            pass

    qr_raw = generate_qr_png_bytes(qr_text)
    qr_img = Image.open(io.BytesIO(qr_raw)).convert("RGB")
    qr_target = 180
    qr_img = qr_img.resize((qr_target, qr_target), Image.Resampling.LANCZOS)
    qx = (w_px - qr_target) // 2
    qy = h_px - qr_target - 16
    im.paste(qr_img, (qx, qy))

    sku = resolve_inventory_sku(item)
    description = inventory_item_description(item)
    gap_title = 16
    gap_meta = 12
    for line in textwrap.wrap(description, width=28)[:3]:
        if y >= qy - 8:
            break
        draw.text((margin, y), line[:120], fill=(0, 0, 0), font=font_title)
        y += gap_title

    y += 2
    draw.text((margin, min(y, qy - gap_meta)), f"SKU: {sku}"[:120], fill=(0, 0, 0), font=font_meta)

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
        if load_inventory_thumbnail_bytes(item):
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
