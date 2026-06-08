"""
Normalize mixed uploads (PDF, HEIC, raster images) into PNG/JPEG/WebP bytes for asset AI autofill vision API.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Final

# Max PDF pages rendered per file (avoid huge API payloads).
_MAX_PDF_PAGES_PER_FILE: Final[int] = 12


def _register_heif_opener() -> bool:
    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()
        return True
    except ImportError:
        return False


_HEIF_AVAILABLE = _register_heif_opener()


def _ext(name: str) -> str:
    return Path(name).suffix.lower()


def _heic_to_png(raw: bytes, original_name: str) -> tuple[bytes, str]:
    if not _HEIF_AVAILABLE:
        raise ValueError(
            "HEIC support is not installed. Install the pillow-heif package (see requirements.txt) and restart the app."
        )
    from PIL import Image

    stem = Path(original_name).stem or "photo"
    out_name = f"{stem}.png"
    try:
        img = Image.open(io.BytesIO(raw))
        rgb = img.convert("RGB")
        buf = io.BytesIO()
        rgb.save(buf, format="PNG", optimize=True)
        out = buf.getvalue()
    except Exception as exc:
        raise ValueError(f"Could not decode HEIC file {original_name!r}: {exc}") from exc
    if not out:
        raise ValueError(f"HEIC conversion produced empty output for {original_name!r}.")
    return out, out_name


def _pdf_pages_to_pngs(raw: bytes, original_name: str) -> list[tuple[bytes, str]]:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ValueError("PDF support requires PyMuPDF (fitz). Install PyMuPDF.") from exc

    stem = Path(original_name).stem or "document"
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Could not open PDF {original_name!r} (corrupt or unsupported): {exc}") from exc
    try:
        n_pages = doc.page_count
        if n_pages <= 0:
            raise ValueError(f"PDF has no pages: {original_name!r}.")
        limit = min(n_pages, _MAX_PDF_PAGES_PER_FILE)
        out: list[tuple[bytes, str]] = []
        mat = fitz.Matrix(2.0, 2.0)
        for i in range(limit):
            page = doc[i]
            pix = page.get_pixmap(matrix=mat, alpha=False)
            png_bytes = pix.tobytes("png")
            if not png_bytes:
                raise ValueError(f"PDF page {i + 1} in {original_name!r} rendered empty.")
            out.append((png_bytes, f"{stem}_page{i + 1}.png"))
        return out
    finally:
        doc.close()


def prepare_asset_autofill_inputs(uploads: list[tuple[bytes, str]]) -> list[tuple[bytes, str]]:
    """
    Convert uploads to a flat list of (bytes, file_name) suitable for vision API (raster images).

    - JPG/JPEG/PNG/WEBP: passed through unchanged.
    - HEIC/HEIF: decoded to PNG bytes (requires pillow-heif).
    - PDF: each page rendered to PNG (PyMuPDF), up to _MAX_PDF_PAGES_PER_FILE pages per file.

    Raises ValueError with a user-facing message on empty/unsupported inputs.
    """
    if not uploads:
        raise ValueError("At least one file is required.")

    normalized: list[tuple[bytes, str]] = []
    for raw, name in uploads:
        if raw is None or len(raw) == 0:
            raise ValueError(f"Empty file: {name!r}. Choose a non-empty file or re-upload.")
        ext = _ext(name)

        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            normalized.append((raw, name))
        elif ext in (".heic", ".heif"):
            normalized.append(_heic_to_png(raw, name))
        elif ext == ".pdf":
            normalized.extend(_pdf_pages_to_pngs(raw, name))
        else:
            raise ValueError(
                f"Unsupported type for {name!r}. Use PDF, HEIC, HEIF, JPG, JPEG, PNG, or WEBP."
            )

    if not normalized:
        raise ValueError("No images could be produced from the uploaded files.")
    return normalized


def pdf_extracted_text_hints(
    uploads: list[tuple[bytes, str]],
    *,
    max_pages_per_pdf: int = 5,
    max_chars_total: int = 8000,
) -> str:
    """
    Best-effort text extraction from uploaded PDFs (same files as before prepare_asset_autofill_inputs).
    Used as supplemental context for the vision model; failures are ignored (rendered pages remain).
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ""

    chunks: list[str] = []
    for raw, name in uploads:
        if _ext(name) != ".pdf" or not raw:
            continue
        try:
            doc = fitz.open(stream=raw, filetype="pdf")
        except Exception:
            continue
        try:
            n = min(doc.page_count, max_pages_per_pdf)
            parts: list[str] = []
            for i in range(n):
                parts.append(doc[i].get_text() or "")
            txt = "\n".join(parts).strip()
            if txt:
                chunks.append(f"### {name}\n{txt}")
        finally:
            doc.close()

    if not chunks:
        return ""
    merged = "\n\n".join(chunks).strip()
    if len(merged) > max_chars_total:
        merged = merged[: max_chars_total - 3] + "..."
    return merged
