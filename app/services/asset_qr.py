from __future__ import annotations

import base64
import io
import re
import textwrap
from functools import lru_cache
from typing import Any
from urllib.parse import parse_qs, quote, unquote, unquote_plus, urlparse

try:
    from db import fetch_table
    from services.asset_service import build_qr_value
except ImportError:
    from app.db import fetch_table  # type: ignore
    from app.services.asset_service import build_qr_value  # type: ignore


def _app_base_url() -> str:
    try:
        from app.config import settings
    except ImportError:
        from config import settings  # type: ignore
    return str(getattr(settings, "app_base_url", "") or "").strip().rstrip("/")


def asset_mobile_scan_link_url(*, asset_id: str, qr_token: str, app_base_url: str | None = None) -> str:
    """
    Mobile asset scan URL.

    Format: ``{APP_BASE_URL}/?scan=asset&asset_id={uuid}&token={qr_token}``
    """
    b = str(app_base_url or _app_base_url() or "").strip().rstrip("/")
    aid = quote(str(asset_id or "").strip(), safe="")
    token = quote(str(qr_token or "").strip(), safe="")
    if not b or not aid or not token:
        return ""
    return f"{b}/?scan=asset&asset_id={aid}&token={token}"


def asset_scan_link_url(
    *,
    qr_code_value: str = "",
    asset_id: str = "",
    qr_token: str = "",
    app_base_url: str | None = None,
) -> str:
    """
    Full URL encoded in asset QR labels for phone scans.

    Prefers ``?scan=asset&asset_id=&token=`` when id/token provided; legacy ``?page=Assets&code=`` fallback.
    """
    if asset_id and qr_token:
        link = asset_mobile_scan_link_url(
            asset_id=asset_id,
            qr_token=qr_token,
            app_base_url=app_base_url,
        )
        if link:
            return link
    b = str(app_base_url or _app_base_url() or "").strip().rstrip("/")
    v = str(qr_code_value or "").strip()
    if not b or not v:
        return v
    page_q = quote("Assets", safe="")
    code_q = quote(v, safe="")
    return f"{b}/?page={page_q}&code={code_q}"


def qr_payload(asset: dict[str, Any]) -> str:
    """Stable scan token for an asset (matches DB ``qr_code_value`` when set)."""
    v = str(asset.get("qr_code_value") or "").strip()
    if v:
        return v
    aid = str(asset.get("asset_id") or asset.get("asset_number") or "").strip()
    return build_qr_value(aid) if aid else ""


def qr_embed_subject(asset: dict[str, Any], *, app_base_url: str | None = None) -> str:
    """Value encoded inside the QR image — mobile scan URL when ``APP_BASE_URL`` is configured."""
    try:
        from app.services.assets_service import generate_asset_qr_value
    except ImportError:
        from services.assets_service import generate_asset_qr_value  # type: ignore
    url = generate_asset_qr_value(asset)
    if url and str(url).startswith("http"):
        return url
    token = qr_payload(asset)
    if not token:
        return ""
    base = str(app_base_url or _app_base_url() or "").strip().rstrip("/")
    if base:
        return asset_scan_link_url(qr_code_value=token, app_base_url=base)
    return token


def _first_query_param(name: str) -> str:
    import streamlit as st

    try:
        v = st.query_params.get(name)
    except Exception:
        return ""
    if isinstance(v, list):
        return str(v[0]).strip() if v else ""
    return str(v or "").strip()


def _normalize_scan_input(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    low = s.lower()
    if "code=" in low or "qr=" in low:
        try:
            u = urlparse(s if "://" in s else f"https://placeholder.local{s if s.startswith('/') else '/' + s}")
            qs = parse_qs(u.query)
            for key in ("code", "qr"):
                vals = qs.get(key) or []
                if vals:
                    return str(vals[0]).strip()
        except Exception:
            return s
    return s


def resolve_asset_uuid_from_scan(raw: str) -> str | None:
    """Resolve a scanned token or URL to the assets table UUID (includes demo fallback)."""
    rid = find_asset_id_by_scan(raw)
    if rid:
        return rid
    token = _normalize_scan_token(_normalize_scan_input(raw))
    if not token:
        return None
    try:
        from app.pages._core._data import load_assets
    except ImportError:
        from pages._core._data import load_assets  # type: ignore
    su = token.upper()
    for asset in load_assets():
        uuid = str(asset.get("id") or "").strip()
        if not uuid:
            continue
        if uuid.upper() == su:
            return uuid
        num = str(asset.get("asset_number") or asset.get("asset_id") or "").strip().upper()
        if num and num == su:
            return uuid
        qv = str(asset.get("qr_code_value") or "").strip().upper()
        if qv and qv == su:
            return uuid
        if su.startswith("IPS-") and num and su == f"IPS-{num}":
            return uuid
    return None


def capture_asset_deeplink_from_query() -> None:
    """Read ``?page=Assets&code=…`` (or ``?qr=``) from the URL and stash for post-nav apply."""
    import streamlit as st

    if _first_query_param("scan") in {"inventory", "asset"}:
        return

    pg = _first_query_param("page")
    if pg:
        decoded = unquote_plus(pg).strip().lower()
        if decoded in {"scan inventory", "inventory scan", "asset scan", "scan asset"}:
            return

    raw_code = _first_query_param("code") or _first_query_param("qr")
    if str(raw_code or "").strip().lower() == "inventory":
        raw_code = ""
    wants_assets = False
    if pg:
        decoded = unquote_plus(pg).strip().lower()
        if decoded in {"assets", "asset", "asset database"}:
            wants_assets = True

    scan_raw = _normalize_scan_input(raw_code) if raw_code else ""
    if wants_assets:
        st.session_state["_ips_asset_deeplink_nav"] = True
    if scan_raw:
        st.session_state["_ips_asset_deeplink_code"] = scan_raw

    if wants_assets or scan_raw:
        for key in ("page", "code", "qr"):
            try:
                if key in st.query_params:
                    del st.query_params[key]
            except Exception:
                try:
                    st.query_params.pop(key, None)  # type: ignore[attr-defined]
                except Exception:
                    pass


def apply_asset_deeplink_navigation() -> None:
    """Open Assets with the scanned asset selected (call after nav-change clears)."""
    import streamlit as st

    try:
        from app.utils.constants import SESSION_NAV_KEY
    except ImportError:
        from utils.constants import SESSION_NAV_KEY  # type: ignore

    wants_assets = bool(st.session_state.pop("_ips_asset_deeplink_nav", False))
    scan_raw = str(st.session_state.pop("_ips_asset_deeplink_code", "") or "").strip()
    if not wants_assets and not scan_raw:
        return

    st.session_state[SESSION_NAV_KEY] = "assets"
    asset_uuid = resolve_asset_uuid_from_scan(scan_raw) if scan_raw else None
    if asset_uuid:
        st.session_state["ips_sel_assets"] = asset_uuid
        st.session_state["ips_tab_assets"] = "Overview"
    elif scan_raw:
        st.session_state["_ips_asset_deeplink_pending"] = scan_raw


def merge_asset_deeplink_from_query() -> None:
    """Capture URL params and apply navigation (single-call helper for tests)."""
    capture_asset_deeplink_from_query()
    apply_asset_deeplink_navigation()


def apply_pending_asset_deeplink() -> None:
    """Resolve a deferred scan token once assets data is available."""
    import streamlit as st

    pending = str(st.session_state.pop("_ips_asset_deeplink_pending", "") or "").strip()
    if not pending:
        return
    asset_uuid = resolve_asset_uuid_from_scan(pending)
    if asset_uuid:
        st.session_state["ips_sel_assets"] = asset_uuid
        st.session_state["ips_tab_assets"] = "Overview"


def qr_png_bytes(payload: str, box_size: int = 6, border: int = 2) -> bytes:
    """Render QR as PNG bytes for Streamlit st.image."""
    import qrcode

    qr = qrcode.QRCode(version=None, box_size=box_size, border=border)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@lru_cache(maxsize=512)
def qr_thumb_data_uri(subject: str) -> str:
    """Small QR thumbnail as a data URI for inline HTML table cells."""
    s = str(subject or "").strip()
    if not s:
        return ""
    png = qr_png_bytes(s, box_size=3, border=1)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def qr_label_download_basename(asset: dict[str, Any]) -> str:
    """Filesystem-safe base name without extension (e.g. for `<base>_qr_label.pdf`)."""
    aid = str(asset.get("asset_id") or "asset").strip()
    safe = re.sub(r"[^\w.-]+", "_", aid, flags=re.UNICODE)
    safe = safe.strip("._") or "asset"
    return f"{safe}_qr_label"


def qr_label_pdf_bytes(asset: dict[str, Any], qr_text: str) -> bytes:
    """
    Single-page compact portrait label (2.0\" × 2.5\") for sticker printing.
    Reuses qr_png_bytes() for the QR image (same encoding as on-screen QR).
    """
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    buf = io.BytesIO()
    w_pt, h_pt = 2.0 * inch, 2.5 * inch
    c = canvas.Canvas(buf, pagesize=(w_pt, h_pt))
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w_pt, h_pt, fill=1, stroke=0)

    margin = 0.14 * inch
    qr_sz = 1.1 * inch
    x = (w_pt - qr_sz) / 2
    y_qr = h_pt - margin - qr_sz
    ir = ImageReader(io.BytesIO(qr_png_bytes(qr_text)))
    c.drawImage(ir, x, y_qr, width=qr_sz, height=qr_sz, mask="auto")

    aid = str(asset.get("asset_id") or "").strip()
    name = str(asset.get("asset_name") or "").strip()
    serial = str(asset.get("serial_number") or "").strip()
    model = str(asset.get("model") or "").strip()

    c.setFillColorRGB(0, 0, 0)
    y = y_qr - 0.11 * inch
    line_gap = 9.0

    c.setFont("Helvetica-Bold", 9)
    for line in textwrap.wrap(name or "(no name)", width=34)[:4]:
        if y < margin:
            break
        c.drawString(margin, y, line[:120])
        y -= line_gap

    y -= 1
    c.setFont("Helvetica", 7)
    meta_lines: list[str] = []
    if aid:
        meta_lines.append(f"ID: {aid}")
    if serial:
        meta_lines.append(f"S/N: {serial}")
    if model:
        meta_lines.append(f"Model: {model}")
    for block in meta_lines:
        for line in textwrap.wrap(block, width=42)[:3]:
            if y < margin:
                break
            c.drawString(margin, y, line[:120])
            y -= line_gap - 1

    c.save()
    return buf.getvalue()


def qr_label_2x1_sticker_pdf_bytes(asset: dict[str, Any], qr_text: str) -> bytes:
    """
    Physical 2\" × 1\" sticker (landscape): QR on the left, asset name + asset_id on the right.
    High-contrast black on white; same QR payload as qr_png_bytes(qr_text).
    """
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    buf = io.BytesIO()
    w_pt, h_pt = 2.0 * inch, 1.0 * inch
    c = canvas.Canvas(buf, pagesize=(w_pt, h_pt))
    c.setFillColorRGB(1, 1, 1)
    c.rect(0, 0, w_pt, h_pt, fill=1, stroke=0)

    margin = 0.07 * inch
    gap = 0.05 * inch
    qr_sz = min(0.72 * inch, h_pt - 2 * margin)
    x_qr = margin
    y_qr = (h_pt - qr_sz) / 2
    ir = ImageReader(io.BytesIO(qr_png_bytes(qr_text)))
    c.drawImage(ir, x_qr, y_qr, width=qr_sz, height=qr_sz, mask="auto")

    aid = str(asset.get("asset_id") or "").strip()
    name = str(asset.get("asset_name") or "").strip()

    text_x = x_qr + qr_sz + gap
    text_right = w_pt - margin
    max_w_pt = text_right - text_x
    wrap_chars = max(10, min(28, int(max_w_pt / 3.6)))

    c.setFillColorRGB(0, 0, 0)
    line_h_name = 8.5
    line_h_id = 7.0
    y = y_qr + qr_sz - 6

    c.setFont("Helvetica-Bold", 7)
    for line in textwrap.wrap(name or "(no name)", width=wrap_chars)[:2]:
        if y < margin + line_h_id:
            break
        c.drawString(text_x, y, line[:100])
        y -= line_h_name

    y -= 1
    if aid and y >= margin:
        c.setFont("Helvetica", 6)
        id_line = f"ID: {aid}"
        for line in textwrap.wrap(id_line, width=wrap_chars + 4)[:2]:
            if y < margin:
                break
            c.drawString(text_x, y, line[:100])
            y -= line_h_id

    c.save()
    return buf.getvalue()


def qr_label_2x1_sticker_download_filename(asset: dict[str, Any]) -> str:
    """Filename for the 2×1 sticker PDF (e.g. `<id>_qr_label_2x1.pdf`)."""
    return f"{qr_label_download_basename(asset)}_2x1.pdf"


def qr_label_png_bytes(asset: dict[str, Any], qr_text: str) -> bytes:
    """
    Fallback printable label as PNG (same layout intent as PDF).
    Uses qr_png_bytes() for the QR; Pillow default font if no TTF available.
    """
    from PIL import Image, ImageDraw, ImageFont

    w_px, h_px = 400, 500
    im = Image.new("RGB", (w_px, h_px), "white")
    draw = ImageDraw.Draw(im)

    qr_raw = qr_png_bytes(qr_text)
    qr_img = Image.open(io.BytesIO(qr_raw)).convert("RGB")
    qr_target = 220
    qr_img = qr_img.resize((qr_target, qr_target), Image.Resampling.LANCZOS)
    qx = (w_px - qr_target) // 2
    qy = 18
    im.paste(qr_img, (qx, qy))

    use_bitmap_font = False
    try:
        font_title = ImageFont.truetype("arial.ttf", 17)
        font_meta = ImageFont.truetype("arial.ttf", 13)
    except OSError:
        try:
            font_title = ImageFont.truetype("DejaVuSans.ttf", 17)
            font_meta = ImageFont.truetype("DejaVuSans.ttf", 13)
        except OSError:
            font_title = font_meta = ImageFont.load_default()
            use_bitmap_font = True

    aid = str(asset.get("asset_id") or "").strip()
    name = str(asset.get("asset_name") or "").strip()
    serial = str(asset.get("serial_number") or "").strip()
    model = str(asset.get("model") or "").strip()

    y = qy + qr_target + 14
    margin = 14
    gap_title = 11 if use_bitmap_font else 20
    gap_meta = 10 if use_bitmap_font else 16
    for line in textwrap.wrap(name or "(no name)", width=28)[:4]:
        draw.text((margin, y), line[:120], fill=(0, 0, 0), font=font_title)
        y += gap_title

    y += 4
    for block in [
        f"ID: {aid}" if aid else "",
        f"S/N: {serial}" if serial else "",
        f"Model: {model}" if model else "",
    ]:
        if not block:
            continue
        for line in textwrap.wrap(block, width=32)[:2]:
            draw.text((margin, y), line[:120], fill=(0, 0, 0), font=font_meta)
            y += gap_meta

    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


def qr_label_for_download(asset: dict[str, Any], qr_text: str) -> tuple[bytes, str, str]:
    """
    Build bytes for st.download_button: prefers PDF, falls back to PNG.
    qr_text must match what is shown on the page (typically qr_payload(asset)).
    """
    base = qr_label_download_basename(asset)
    try:
        return qr_label_pdf_bytes(asset, qr_text), "application/pdf", f"{base}.pdf"
    except Exception:
        return qr_label_png_bytes(asset, qr_text), "image/png", f"{base}.png"


def _normalize_scan_token(s: str) -> str:
    return re.sub(r"\s+", "", s.strip())


def decode_qr_image_bytes(raw: bytes) -> str | None:
    """
    Decode the first QR code found in an image (camera capture or file upload).
    Uses pyzbar (zbar) + Pillow — no OpenCV. Returns None if nothing found or pyzbar unavailable.
    """
    if not raw:
        return None
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode as pyzbar_decode
    except ImportError:
        return None
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        for obj in pyzbar_decode(img):
            data = getattr(obj, "data", None) or b""
            if not data:
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("latin-1", errors="replace")
            if text.strip():
                return text.strip()
    except Exception:
        return None
    return None


def find_asset_id_by_scan(raw: str) -> str | None:
    """
    Resolve scanned/pasted text or URL to an assets.id (uuid string).
    Accepts qr_code_value, asset_id, IPS-{asset_id}, or ?qr= / path fragments.
    """
    s = _normalize_scan_token(raw)
    if not s:
        return None

    if s.startswith("http://") or s.startswith("https://"):
        try:
            p = urlparse(s)
            qs = parse_qs(p.query)
            if "qr" in qs and qs["qr"]:
                s = unquote(qs["qr"][0].strip())
            elif "code" in qs and qs["code"]:
                s = unquote(qs["code"][0].strip())
            else:
                parts = [x for x in p.path.split("/") if x]
                if parts:
                    s = unquote(parts[-1])
        except Exception:
            pass

    s = _normalize_scan_token(s)
    if not s:
        return None

    assets = fetch_table("assets", limit=5000, order_by="asset_name")
    if not assets:
        return None

    su = s.upper()

    for a in assets:
        rid = str(a.get("id") or "").strip()
        if rid and rid.upper() == su:
            return rid

    for a in assets:
        qv = str(a.get("qr_code_value") or "").strip()
        if qv and qv.upper() == su:
            return str(a.get("id"))

    for a in assets:
        aid = str(a.get("asset_id") or "").strip()
        if aid and aid.upper() == su:
            return str(a.get("id"))

    if su.startswith("IPS-"):
        tail = s[4:].strip()
        for a in assets:
            if str(a.get("asset_id") or "").strip().upper() == tail.upper():
                return str(a.get("id"))
        for a in assets:
            qv = str(a.get("qr_code_value") or "").strip()
            if qv.upper() == su:
                return str(a.get("id"))

    return None
