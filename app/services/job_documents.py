"""Job documents via ``documents_hub`` with optional subjob/task linkage."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from services.field_ops_util import fetch_fn, table_exists, write_fn

_LOG = logging.getLogger(__name__)

TABLE = "documents_hub"
JOB_MODULE = "jobs"
CUSTOMER_PO_DOC_TYPE = "Customer PO"
CUSTOMER_PO_LINKED_REF = "customer_po"


def _upload_fn(*, admin: bool):
    try:
        from app.db import upload_bytes, upload_bytes_admin
    except ImportError:
        from db import upload_bytes, upload_bytes_admin  # type: ignore
    return upload_bytes_admin if admin else upload_bytes


def _is_user_job_document(row: dict[str, Any]) -> bool:
    """Exclude auto-generated weekly timesheet hub rows."""
    ref = str(row.get("linked_ref") or "")
    if ref.startswith("weekly_timesheet:"):
        return False
    mod = str(row.get("linked_module") or "").strip().lower()
    return mod in ("jobs", "job") or bool(row.get("linked_record_id"))


def fetch_job_documents(
    job_id: str,
    *,
    admin: bool = False,
    task_id: str | None = None,
    unlinked_only: bool = False,
    limit: int = 200,
) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid or not table_exists(TABLE, admin=admin):
        return []
    fn = fetch_fn(admin=admin)
    rows = fn(TABLE, {"linked_record_id": jid}, limit=limit)
    out = [r for r in (rows or []) if isinstance(r, dict) and _is_user_job_document(r)]
    tid = str(task_id or "").strip()
    if tid:
        out = [r for r in out if str(r.get("task_id") or "").strip() == tid]
    elif unlinked_only:
        out = [r for r in out if not str(r.get("task_id") or "").strip()]
    out.sort(key=lambda r: str(r.get("upload_date") or r.get("created_at") or ""), reverse=True)
    return out


def upload_job_document(
    *,
    job_id: str,
    file_data: bytes,
    file_name: str,
    content_type: str = "application/octet-stream",
    uploaded_by: str = "",
    doc_type: str = "Job Document",
    notes: str = "",
    task_id: str | None = None,
    admin: bool = False,
) -> dict[str, Any]:
    jid = str(job_id or "").strip()
    if not jid:
        raise ValueError("job_id required")
    if not file_data:
        raise ValueError("Empty file")
    if not table_exists(TABLE, admin=admin):
        raise RuntimeError("documents_hub table not found — run sql/008_documents.sql")
    try:
        from app.config import settings
    except ImportError:
        from config import settings  # type: ignore
    bucket = getattr(settings, "storage_bucket", "ips-storage")
    insert_fn, _, _ = write_fn(admin=admin)
    upload = _upload_fn(admin=admin)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(file_name or "document").strip())[:160] or "document"
    storage_path = f"job_documents/{jid}/{ts}_{safe}"
    upload(storage_path, file_data, content_type=content_type or "application/octet-stream", bucket=bucket)
    payload: dict[str, Any] = {
        "file_name": str(file_name or Path(storage_path).name)[:200],
        "doc_type": str(doc_type or "Job Document").strip()[:120],
        "linked_module": JOB_MODULE,
        "linked_ref": f"job:{jid}",
        "linked_record_id": jid,
        "upload_date": date.today().isoformat(),
        "uploaded_by": str(uploaded_by or "").strip()[:200],
        "storage_path": storage_path,
        "notes": str(notes or "").strip()[:2000],
    }
    tid = str(task_id or "").strip()
    if tid:
        payload["task_id"] = tid
    return insert_fn(TABLE, payload)


def _is_customer_po_document(row: dict[str, Any]) -> bool:
    dtype = str(row.get("doc_type") or "").strip().lower()
    ref = str(row.get("linked_ref") or "").strip().lower()
    if dtype == "customer po":
        return True
    return ref == CUSTOMER_PO_LINKED_REF or ref.startswith(f"{CUSTOMER_PO_LINKED_REF}:")


def fetch_customer_po_document(job_id: str, *, admin: bool = False) -> dict[str, Any] | None:
    """Most recent Customer PO document for a job, if any."""
    for doc in fetch_job_documents(job_id, admin=admin, limit=500):
        if _is_customer_po_document(doc):
            return doc
    return None


def upload_customer_po_document(
    *,
    job_id: str,
    file_data: bytes,
    file_name: str,
    content_type: str = "application/octet-stream",
    uploaded_by: str = "",
    notes: str = "",
    admin: bool = False,
) -> dict[str, Any]:
    jid = str(job_id or "").strip()
    if not jid:
        raise ValueError("job_id required")
    if not file_data:
        raise ValueError("Empty file")
    if not table_exists(TABLE, admin=admin):
        raise RuntimeError("documents_hub table not found — run sql/008_documents.sql")
    try:
        from app.config import settings
    except ImportError:
        from config import settings  # type: ignore
    bucket = getattr(settings, "storage_bucket", "ips-storage")
    insert_fn, _, _ = write_fn(admin=admin)
    upload = _upload_fn(admin=admin)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(file_name or "customer_po").strip())[:160] or "customer_po"
    storage_path = f"job_documents/{jid}/{ts}_{safe}"
    upload(storage_path, file_data, content_type=content_type or "application/octet-stream", bucket=bucket)
    payload: dict[str, Any] = {
        "file_name": str(file_name or Path(storage_path).name)[:200],
        "doc_type": CUSTOMER_PO_DOC_TYPE,
        "linked_module": JOB_MODULE,
        "linked_ref": CUSTOMER_PO_LINKED_REF,
        "linked_record_id": jid,
        "upload_date": date.today().isoformat(),
        "uploaded_by": str(uploaded_by or "").strip()[:200],
        "storage_path": storage_path,
        "notes": str(notes or "").strip()[:2000],
    }
    return insert_fn(TABLE, payload)


def link_job_document_to_task(
    document_id: str,
    task_id: str,
    *,
    admin: bool = False,
) -> None:
    did = str(document_id or "").strip()
    tid = str(task_id or "").strip()
    if not did or not tid:
        raise ValueError("document_id and task_id required")
    _, update_fn, _ = write_fn(admin=admin)
    update_fn(TABLE, {"task_id": tid}, {"id": did})


def unlink_job_document_from_task(document_id: str, *, admin: bool = False) -> None:
    did = str(document_id or "").strip()
    if not did:
        raise ValueError("document_id required")
    _, update_fn, _ = write_fn(admin=admin)
    update_fn(TABLE, {"task_id": None}, {"id": did})


def delete_job_document(
    document_id: str,
    *,
    job_id: str | None = None,
    admin: bool = False,
) -> None:
    did = str(document_id or "").strip()
    if not did:
        raise ValueError("document_id required")
    if not table_exists(TABLE, admin=admin):
        raise RuntimeError("documents_hub table not found — run sql/008_documents.sql")
    fn = fetch_fn(admin=admin)
    rows = fn(TABLE, {"id": did}, limit=1)
    row = rows[0] if rows else None
    if not isinstance(row, dict):
        raise ValueError("Document not found")
    if not _is_user_job_document(row):
        raise ValueError("Cannot delete this document")
    jid = str(job_id or "").strip()
    linked_job = str(row.get("linked_record_id") or "").strip()
    if jid and linked_job and linked_job != jid:
        raise ValueError("Document does not belong to this job")
    storage_path = str(row.get("storage_path") or "").strip()
    if storage_path and admin:
        try:
            from app.config import settings
        except ImportError:
            from config import settings  # type: ignore
        bucket = getattr(settings, "storage_bucket", "ips-storage")
        try:
            from app.db import delete_storage_object_admin
        except ImportError:
            from db import delete_storage_object_admin  # type: ignore
        try:
            delete_storage_object_admin(storage_path, bucket=bucket)
        except Exception:
            _LOG.warning("Storage delete failed for %s", storage_path, exc_info=True)
    _, _, delete_fn = write_fn(admin=admin)
    delete_fn(TABLE, {"id": did})
