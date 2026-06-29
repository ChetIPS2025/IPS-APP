"""Employee HR documents — Supabase rows and Storage uploads."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

try:
    from app.auth import current_profile
    from app.db import create_signed_url, upload_bytes_admin
    from app.services.certification_helpers import date_to_iso
    from app.services.phase2_modules_service import save_employee_document as _save_row
    from app.services.repository import ServiceResult, clear_data_cache_for_table, update_row
except ImportError:
    from auth import current_profile  # type: ignore
    from db import create_signed_url, upload_bytes_admin  # type: ignore
    from services.certification_helpers import date_to_iso  # type: ignore
    from services.phase2_modules_service import save_employee_document as _save_row  # type: ignore
    from services.repository import ServiceResult, clear_data_cache_for_table, update_row  # type: ignore

EMPLOYEE_DOCUMENTS_BUCKET = "employee-documents"
_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".doc", ".docx", ".xls", ".xlsx"}
_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

__all__ = [
    "EMPLOYEE_DOCUMENTS_BUCKET",
    "get_employee_document_url",
    "save_employee_document",
    "upload_employee_document_file",
]


def _safe_filename(name: str) -> str:
    base = str(name or "document").strip().replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return base[:180] or "document"


def _extension(name: str) -> str:
    dot = str(name or "").lower().rfind(".")
    if dot < 0:
        return ""
    return str(name[dot:]).lower()


def _resolve_mime_type(filename: str, uploaded_type: str | None) -> str:
    mime = str(uploaded_type or "").strip()
    if mime:
        return mime
    return _MIME_BY_EXT.get(_extension(filename), "application/octet-stream")


def _storage_path_for_doc(doc_id: str, filename: str) -> str:
    did = str(doc_id or "").strip()
    if not did:
        raise ValueError("Missing document id.")
    safe = _safe_filename(filename)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"employee-documents/{did}/{ts}_{safe}"


def _storage_not_configured_message(exc: Exception) -> str | None:
    msg = str(exc or "").lower()
    if any(token in msg for token in ("bucket", "not found", "does not exist", "404")):
        return "Storage bucket not configured. Create employee-documents bucket in Supabase."
    return None


def _current_uploader_name() -> str:
    prof = current_profile() or {}
    return str(prof.get("full_name") or prof.get("email") or "User")


def _row_payload(ui: dict[str, Any]) -> dict[str, Any]:
    filename = str(ui.get("file_name") or "").strip()
    return {
        "employee_id": ui.get("employee_id"),
        "doc_type": ui.get("doc_type"),
        "file_name": filename or "document",
        "uploaded_by": str(ui.get("uploaded_by") or _current_uploader_name()),
        "expiration_date": date_to_iso(ui.get("expiration_date")) or None,
        "is_restricted": bool(ui.get("is_restricted")),
        "storage_path": str(ui.get("storage_path") or ""),
        "notes": str(ui.get("notes") or ""),
    }


def upload_employee_document_file(
    doc_id: str,
    uploaded_file: Any,
) -> ServiceResult:
    """Upload file to employee-documents bucket and persist storage_path on the row."""
    did = str(doc_id or "").strip()
    if not did:
        return ServiceResult(ok=False, error="Missing document id.")
    if uploaded_file is None:
        return ServiceResult(ok=False, error="No file provided.")

    filename = str(getattr(uploaded_file, "name", "") or "document")
    ext = _extension(filename)
    if ext not in _ALLOWED_EXTENSIONS:
        return ServiceResult(
            ok=False,
            error="Unsupported file type. Upload PDF, Office docs, or common images.",
        )

    data = uploaded_file.getvalue()
    if not data:
        return ServiceResult(ok=False, error="Uploaded file is empty.")

    mime = _resolve_mime_type(filename, getattr(uploaded_file, "type", None))
    storage_path = _storage_path_for_doc(did, filename)

    try:
        upload_bytes_admin(
            storage_path,
            data,
            mime,
            bucket=EMPLOYEE_DOCUMENTS_BUCKET,
        )
    except Exception as exc:
        configured = _storage_not_configured_message(exc)
        if configured:
            return ServiceResult(ok=False, error=configured)
        return ServiceResult(ok=False, error=f"Upload failed: {exc}")

    result = update_row(
        "employee_documents",
        {"storage_path": storage_path, "file_name": _safe_filename(filename)},
        {"id": did},
    )
    if not result.ok:
        return ServiceResult(ok=False, error=result.error or "Could not save document file path.")
    clear_data_cache_for_table("employee_documents")
    return ServiceResult(ok=True, data={"storage_path": storage_path, "file_name": filename})


def get_employee_document_url(doc: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    storage_path = str(doc.get("storage_path") or "").strip()
    if not storage_path:
        return None
    try:
        signed = create_signed_url(
            storage_path,
            expires_in=expires_in,
            bucket=EMPLOYEE_DOCUMENTS_BUCKET,
        )
    except Exception:
        return None
    signed = str(signed or "").strip()
    return signed or None


def save_employee_document(
    ui: dict[str, Any],
    *,
    row_id: str | None = None,
    uploaded_file: Any = None,
) -> ServiceResult:
    """Persist employee document metadata and optionally upload the attachment."""
    payload = _row_payload(ui)
    eid = str(payload.get("employee_id") or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Select an employee before uploading.")
    if not str(payload.get("doc_type") or "").strip():
        return ServiceResult(ok=False, error="Document type is required.")

    is_new = not str(row_id or "").strip()
    if is_new and uploaded_file is None:
        return ServiceResult(ok=False, error="Choose a file to upload.")
    if is_new:
        payload["file_name"] = _safe_filename(str(getattr(uploaded_file, "name", "") or payload["file_name"]))

    result = _save_row(payload, row_id=row_id)
    if not result.ok:
        return result

    saved_row = result.data if isinstance(result.data, dict) else {}
    saved_id = str(row_id or saved_row.get("id") or "").strip()

    if uploaded_file is not None and saved_id:
        upload_result = upload_employee_document_file(saved_id, uploaded_file)
        if not upload_result.ok:
            if is_new:
                return ServiceResult(
                    ok=False,
                    error=upload_result.error or "Document saved but file upload failed.",
                )
            return upload_result

    clear_data_cache_for_table("employee_documents")
    msg = "Document uploaded." if is_new else "Document updated."
    return ServiceResult(ok=True, data={"message": msg, "id": saved_id})
