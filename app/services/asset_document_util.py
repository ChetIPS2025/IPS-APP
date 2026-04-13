from __future__ import annotations

from datetime import datetime
from typing import Any

_EXT_TO_MIME: dict[str, str] = {
    "pdf": "application/pdf",
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "txt": "text/plain",
    "csv": "text/csv",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
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


def persist_asset_document_upload(
    *,
    asset_row: dict[str, Any],
    uploaded: Any,
    document_type: str,
    expiration_date: Any,
    notes: str,
    uploaded_by: str | None,
) -> dict[str, Any]:
    """
    Upload bytes to storage (same bucket layout as existing callers) and insert ``asset_documents``.

    On DB failure after a successful storage upload, attempts to remove the orphaned object.
    """
    try:
        from app.db import delete_storage_object_admin, insert_row_admin, upload_bytes_admin
    except ImportError:
        from db import delete_storage_object_admin, insert_row_admin, upload_bytes_admin  # type: ignore

    asset_key = str(asset_row.get("asset_id") or "").strip() or "unknown"
    raw_name = str(getattr(uploaded, "name", "") or "upload.bin")
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else "bin"
    path = f"asset_documents/{asset_key}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{ext}"
    data = uploaded.getvalue()
    st_type = getattr(uploaded, "type", None)
    content_type = guess_document_content_type(raw_name, st_type if isinstance(st_type, str) else None)

    upload_bytes_admin(path, data, content_type=content_type)

    payload: dict[str, Any] = {
        "asset_id": asset_row["id"],
        "document_type": document_type,
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
        return insert_row_admin("asset_documents", payload)
    except Exception as first_exc:
        slim = {k: v for k, v in payload.items() if k not in ("content_type", "original_filename", "file_kind")}
        if slim == payload:
            try:
                delete_storage_object_admin(path)
            except Exception:
                pass
            raise first_exc
        try:
            return insert_row_admin("asset_documents", slim)
        except Exception:
            try:
                delete_storage_object_admin(path)
            except Exception:
                pass
            raise first_exc
