from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ASSET_DOCUMENTS_BUCKET = "asset_documents"

ASSET_DOCUMENT_UPLOAD_TYPES = ["pdf", "docx", "xlsx", "jpg", "jpeg", "png", "txt"]

_EXT_TO_MIME: dict[str, str] = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "heic": "image/heic",
    "heif": "image/heif",
    "webp": "image/webp",
}


def guess_document_content_type(filename: str, streamlit_mime: str | None) -> str:
    """Prefer Streamlit-provided MIME when meaningful; otherwise map from file extension."""
    sn = (streamlit_mime or "").strip()
    if sn and sn.lower() not in ("application/octet-stream", "binary/octet-stream", ""):
        return sn
    name = (filename or "").strip()
    if "." not in name:
        return "application/octet-stream"
    ext = name.rsplit(".", 1)[-1].lower()
    return _EXT_TO_MIME.get(ext, "application/octet-stream")


def file_type_label(filename: str, content_type: str = "") -> str:
    name = str(filename or "").strip().lower()
    ct = str(content_type or "").strip().lower()
    if name.endswith(".pdf") or "pdf" in ct:
        return "PDF"
    if name.endswith(".docx") or "wordprocessingml" in ct:
        return "DOCX"
    if name.endswith(".xlsx") or "spreadsheetml" in ct:
        return "XLSX"
    if name.endswith((".jpg", ".jpeg")) or ct == "image/jpeg":
        return "JPG"
    if name.endswith(".png") or ct == "image/png":
        return "PNG"
    if name.endswith(".txt") or ct.startswith("text/"):
        return "TXT"
    ext = name.rsplit(".", 1)[-1].upper() if "." in name else ""
    return ext or "File"


def is_pdf_document(filename: str, content_type: str = "") -> bool:
    n = str(filename or "").lower()
    ct = str(content_type or "").lower()
    return n.endswith(".pdf") or "pdf" in ct


def is_image_document(filename: str, content_type: str = "") -> bool:
    n = str(filename or "").lower()
    ct = str(content_type or "").lower()
    if n.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".heif")):
        return True
    return ct.startswith("image/")


def _safe_storage_filename(raw_name: str) -> str:
    base = Path(str(raw_name or "upload.bin").strip()).name
    base = re.sub(r"[^\w.\- ]+", "_", base).strip("._ ") or "upload.bin"
    return base[:180]


def persist_asset_document_upload(
    *,
    asset_row: dict[str, Any],
    uploaded: Any,
    document_type: str = "Document",
    expiration_date: Any = None,
    notes: str = "",
    uploaded_by: str | None,
) -> dict[str, Any]:
    """
    Upload bytes to the ``asset_documents`` storage bucket and insert ``asset_documents``.
    """
    try:
        from app.db import delete_storage_object_admin, insert_row_admin, upload_bytes_admin
    except ImportError:
        from db import delete_storage_object_admin, insert_row_admin, upload_bytes_admin  # type: ignore

    asset_id = str(asset_row.get("id") or "").strip()
    if not asset_id:
        raise ValueError("Missing asset id.")
    raw_name = _safe_storage_filename(str(getattr(uploaded, "name", "") or "upload.bin"))
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else "bin"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = f"{asset_id}/{stamp}_{raw_name}"
    data = uploaded.getvalue()
    st_type = getattr(uploaded, "type", None)
    content_type = guess_document_content_type(raw_name, st_type if isinstance(st_type, str) else None)

    upload_bytes_admin(path, data, content_type=content_type, bucket=ASSET_DOCUMENTS_BUCKET)

    payload: dict[str, Any] = {
        "asset_id": asset_id,
        "document_type": str(document_type or "Document").strip() or "Document",
        "file_name": raw_name,
        "file_path": path,
        "expiration_date": expiration_date.isoformat() if expiration_date else None,
        "notes": str(notes or "").strip(),
        "uploaded_by": uploaded_by,
        "content_type": content_type,
        "original_filename": raw_name,
        "file_kind": "document",
    }

    try:
        row = insert_row_admin("asset_documents", payload)
    except Exception as first_exc:
        slim = {k: v for k, v in payload.items() if k not in ("content_type", "original_filename", "file_kind")}
        if slim == payload:
            try:
                delete_storage_object_admin(path, bucket=ASSET_DOCUMENTS_BUCKET)
            except Exception:
                pass
            raise first_exc
        try:
            row = insert_row_admin("asset_documents", slim)
        except Exception:
            try:
                delete_storage_object_admin(path, bucket=ASSET_DOCUMENTS_BUCKET)
            except Exception:
                pass
            raise
    try:
        from app.services.repository import clear_data_cache_for_table
    except ImportError:
        from services.repository import clear_data_cache_for_table  # type: ignore
    clear_data_cache_for_table("asset_documents")
    return row


def delete_asset_document_record(doc: dict[str, Any]) -> None:
    """Remove storage object and DB row for an asset document."""
    try:
        from app.db import delete_storage_object_admin, delete_rows_admin
    except ImportError:
        from db import delete_storage_object_admin, delete_rows_admin  # type: ignore

    path = str(doc.get("file_path") or doc.get("storage_path") or "").strip()
    doc_id = str(doc.get("id") or "").strip()
    if path:
        delete_storage_object_admin(path, bucket=ASSET_DOCUMENTS_BUCKET)
    if doc_id:
        delete_rows_admin("asset_documents", {"id": doc_id})
    try:
        from app.services.repository import clear_data_cache_for_table
    except ImportError:
        from services.repository import clear_data_cache_for_table  # type: ignore
    clear_data_cache_for_table("asset_documents")
