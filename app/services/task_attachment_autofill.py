"""Best-effort text extraction + hazard-sheet heuristics for Add Task auto-fill."""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

try:
    from app.services import job_reference_attachments as jra
except ImportError:
    import services.job_reference_attachments as jra  # type: ignore

try:
    from app.db import create_signed_url
except ImportError:
    from db import create_signed_url  # type: ignore


_AUTOFILL_EXT = frozenset({"jpg", "jpeg", "png", "webp", "pdf"})


def is_autofill_supported_filename(name: str) -> bool:
    return jra.normalize_extension(name) in _AUTOFILL_EXT


def download_signed_url(url: str, *, timeout: float = 120.0) -> bytes | None:
    if not url or httpx is None:
        return None
    try:
        r = httpx.get(url, follow_redirects=True, timeout=timeout)
        r.raise_for_status()
        return bytes(r.content or b"")
    except Exception:
        return None


def extract_text_pdf(data: bytes) -> str:
    if not data:
        return ""
    # PyMuPDF first
    try:
        import fitz  # type: ignore  # PyMuPDF

        doc = fitz.open(stream=data, filetype="pdf")
        parts: list[str] = []
        for i in range(int(doc.page_count or 0)):
            try:
                page = doc.load_page(i)
                t = page.get_text() or ""
                if t.strip():
                    parts.append(t)
            except Exception:
                continue
        doc.close()
        out = "\n".join(parts).strip()
        if out:
            return out
    except Exception:
        pass
    # pdfplumber fallback
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            chunks: list[str] = []
            for page in pdf.pages or []:
                try:
                    t = page.extract_text() or ""
                    if t.strip():
                        chunks.append(t)
                except Exception:
                    continue
        return "\n".join(chunks).strip()
    except Exception:
        return ""


def extract_text_image(data: bytes) -> str:
    if not data:
        return ""
    try:
        from PIL import Image  # type: ignore

        import pytesseract  # type: ignore

        img = Image.open(io.BytesIO(data))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return str(pytesseract.image_to_string(img) or "").strip()
    except Exception:
        return ""


def extract_text_from_bytes(filename: str, data: bytes) -> str:
    ext = jra.normalize_extension(filename)
    if ext == "pdf":
        return extract_text_pdf(data)
    if ext in {"jpg", "jpeg", "png", "webp"}:
        return extract_text_image(data)
    return ""


def _norm_priority_token(s: str) -> str | None:
    t = str(s or "").strip().lower()
    if t in ("critical", "crit"):
        return "critical"
    if t in ("high", "hi"):
        return "high"
    if t in ("medium", "med", "normal", "moderate"):
        return "normal"
    if t in ("low",):
        return "low"
    return None


def parse_hazard_sheet_text(raw: str) -> dict[str, Any]:
    """
    Heuristic parse of hazard / task sheets.
    Returns keys: task_number, priority, location, issue, action_required, planned_date (date|None).
    """
    text = str(raw or "").replace("\r\n", "\n")
    out: dict[str, Any] = {}

    # Task / Hazard number → Task #
    for pat in (
        r"Hazard\s*#\s*[:\s]*\s*([^\n\r]+)",
        r"Hazard\s*Number\s*[:\s]*\s*([^\n\r]+)",
        r"Task\s*#\s*[:\s]*\s*([^\n\r]+)",
        r"Hazard\s*ID\s*[:\s]*\s*([^\n\r]+)",
    ):
        m = re.search(pat, text, re.I)
        if m:
            v = m.group(1).strip()
            v = re.split(r"\s{2,}|\t", v)[0].strip()
            out["task_number"] = v[:200]
            break

    # Priority: explicit label first
    m = re.search(
        r"Priority\s*[:\s#]*\s*(Critical|High|Medium|Low|Normal)\b",
        text,
        re.I,
    )
    if m:
        p = _norm_priority_token(m.group(1))
        if p:
            out["priority"] = p
    if "priority" not in out:
        m = re.search(r"\b(Critical|High|Medium|Low)\b(?=\s*(?:priority|risk|level)?)", text, re.I)
        if m:
            p = _norm_priority_token(m.group(1))
            if p:
                out["priority"] = p

    # Location
    m = re.search(r"Location\s*[:\s#]*\s*(.+?)(?=\n\s*(?:Issue|Action|Hazard|Task|Priority|Date)\b|\Z)", text, re.I | re.S)
    if m:
        loc = re.sub(r"\s+", " ", m.group(1).strip())
        out["location"] = loc[:500]

    # Issue
    m = re.search(r"Issue\s*[:\s#]*\s*(.+?)(?=\n\s*(?:Action|Location|Hazard|Task|Priority)\b|\Z)", text, re.I | re.S)
    if m:
        iss = re.sub(r"\s+", " ", m.group(1).strip())
        out["issue"] = iss[:4000]

    # Action required
    for pat in (
        r"Action\s*Required\s*[:\s#]*\s*(.+?)(?=\n\s*(?:Issue|Location|Hazard|Task|Priority|Notes)\b|\Z)",
        r"Action\s*[:\s#]*\s*(.+?)(?=\n\s*(?:Issue|Location|Hazard|Task|Priority|Notes)\b|\Z)",
    ):
        m = re.search(pat, text, re.I | re.S)
        if m:
            act = re.sub(r"\s+", " ", m.group(1).strip())
            out["action_required"] = act[:4000]
            break

    # Planned / target date
    def _parse_date_token(ds: str) -> date | None:
        s = str(ds or "").strip().split()[0][:32]
        if re.match(r"^\d{4}-\d{2}-\d{2}", s):
            try:
                return datetime.strptime(s[:10], "%Y-%m-%d").date()
            except Exception:
                pass
        s2 = s.replace(".", "/")
        for fmt in ("%m/%d/%Y", "%m/%d/%y", "%d/%m/%Y", "%d/%m/%y", "%Y/%m/%d"):
            try:
                return datetime.strptime(s2, fmt).date()
            except Exception:
                continue
        return None

    for pat in (
        r"(?:Planned|Plan|Target)\s*Date\s*[:\s#]*\s*([0-9]{1,4}[/-][0-9]{1,2}[/-][0-9]{1,4})",
        r"(?:Planned|Plan|Target)\s*Date\s*[:\s#]*\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        r"\b(20[0-9]{2}-[01][0-9]-[0-3][0-9])\b",
    ):
        m = re.search(pat, text, re.I)
        if m:
            pd = _parse_date_token(m.group(1))
            if pd:
                out["planned_date"] = pd
                break
    if "planned_date" not in out:
        m = re.search(r"\b(20[0-9]{2}-[01][0-9]-[0-3][0-9])\b", text)
        if m:
            pd = _parse_date_token(m.group(1))
            if pd:
                out["planned_date"] = pd

    return out


def attachment_signed_url(row: dict[str, Any], *, bucket: str) -> str:
    path = str((row or {}).get("file_url") or "").strip()
    if not path:
        return ""
    try:
        return create_signed_url(path, expires_in=3600, bucket=bucket)
    except Exception:
        return ""


def fetch_bytes_for_row(row: dict[str, Any], *, bucket: str) -> tuple[bytes | None, str]:
    fname = str((row or {}).get("file_name") or "file").strip()
    url = attachment_signed_url(row, bucket=bucket)
    if not url:
        return None, fname
    data = download_signed_url(url)
    return data, fname
