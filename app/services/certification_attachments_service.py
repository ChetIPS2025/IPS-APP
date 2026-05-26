"""Supabase Storage helpers for employee certification attachments."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

try:
    from app.db import create_signed_url, upload_bytes_admin
    from app.services.repository import ServiceResult, update_row
except ImportError:
    from db import create_signed_url, upload_bytes_admin  # type: ignore
    from services.repository import ServiceResult, update_row  # type: ignore

CERTIFICATION_STORAGE_BUCKET = "certification-documents"
_ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}
_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
}


def _safe_filename(name: str) -> str:
    base = str(name or "attachment").strip().replace("\\", "/").split("/")[-1]
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return base[:180] or "attachment"


def _extension(name: str) -> str:
    dot = str(name or "").lower().rfind(".")
    if dot < 0:
        return ""
    return str(name[dot:]).lower()


def _resolve_mime_type(filename: str, uploaded_type: str | None) -> str:
    mime = str(uploaded_type or "").strip()
    if mime:
        return mime
    ext = _extension(filename)
    return _MIME_BY_EXT.get(ext, "application/octet-stream")


def _storage_path_for_cert(cert_id: str, filename: str) -> str:
    cid = str(cert_id or "").strip()
    if not cid:
        raise ValueError("Missing certification id.")
    safe = _safe_filename(filename)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"employee-certifications/{cid}/{ts}_{safe}"


def _storage_not_configured_message(exc: Exception) -> str | None:
    msg = str(exc or "").lower()
    if any(token in msg for token in ("bucket", "not found", "does not exist", "404")):
        return "Storage bucket not configured. Create certification-documents bucket in Supabase."
    return None


def cert_has_attachment(cert: dict[str, Any]) -> bool:
    return bool(
        str(cert.get("attachment_path") or "").strip()
        or str(cert.get("attachment_url") or "").strip()
    )


def upload_certification_attachment(
    cert_id: str,
    uploaded_file: Any,
    *,
    uploaded_by: str | None = None,
) -> ServiceResult:
    """Upload file to certification-documents bucket and persist metadata on the row."""
    cid = str(cert_id or "").strip()
    if not cid:
        return ServiceResult(ok=False, error="Missing certification id.")
    if uploaded_file is None:
        return ServiceResult(ok=False, error="No file provided.")

    filename = str(getattr(uploaded_file, "name", "") or "attachment")
    ext = _extension(filename)
    if ext not in _ALLOWED_EXTENSIONS:
        return ServiceResult(
            ok=False,
            error="Unsupported file type. Upload PNG, JPG, WEBP, or PDF.",
        )

    data = uploaded_file.getvalue()
    if not data:
        return ServiceResult(ok=False, error="Uploaded file is empty.")

    mime = _resolve_mime_type(filename, getattr(uploaded_file, "type", None))
    storage_path = _storage_path_for_cert(cid, filename)

    try:
        upload_bytes_admin(
            storage_path,
            data,
            mime,
            bucket=CERTIFICATION_STORAGE_BUCKET,
        )
    except Exception as exc:
        configured = _storage_not_configured_message(exc)
        if configured:
            return ServiceResult(ok=False, error=configured)
        return ServiceResult(ok=False, error=f"Upload failed: {exc}")

    payload = {
        "attachment_path": storage_path,
        "attachment_url": "",
        "attachment_file_name": filename,
        "attachment_mime_type": mime,
        "attachment_uploaded_at": datetime.now(timezone.utc).isoformat(),
        "attachment_uploaded_by": uploaded_by or None,
    }
    try:
        from app.services.repository import table_column_names
    except ImportError:
        from services.repository import table_column_names  # type: ignore
    cols = table_column_names("employee_certifications")
    if cols and "attachment_path" not in cols:
        return ServiceResult(
            ok=False,
            error="Certification attachment columns are missing. Run sql/070_employee_certification_attachments.sql in Supabase.",
        )
    result = update_row("employee_certifications", payload, {"id": cid})
    if not result.ok:
        return ServiceResult(ok=False, error=result.error or "Could not save attachment metadata.")
    if cols:
        saved = {k: v for k, v in payload.items() if k in cols}
        if "attachment_path" not in saved:
            return ServiceResult(
                ok=False,
                error="Certification attachment metadata could not be saved. Check Supabase schema migrations.",
            )
    return ServiceResult(ok=True, data={"attachment_path": storage_path, **payload})


def get_certification_attachment_url(cert: dict[str, Any], *, expires_in: int = 3600) -> str | None:
    """Return a viewable URL for the certification attachment (signed when private)."""
    public_url = str(cert.get("attachment_url") or "").strip()
    if public_url.startswith("http"):
        return public_url

    storage_path = str(cert.get("attachment_path") or "").strip()
    if not storage_path:
        return None

    try:
        signed = create_signed_url(
            storage_path,
            expires_in=expires_in,
            bucket=CERTIFICATION_STORAGE_BUCKET,
        )
    except Exception as exc:
        configured = _storage_not_configured_message(exc)
        if configured:
            return None
        return None

    signed = str(signed or "").strip()
    return signed or None
