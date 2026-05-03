"""Load and persist job reference attachments (Supabase Storage + ``job_reference_attachments``)."""

from __future__ import annotations

import re
import uuid
from typing import Any

try:
    from app.config import settings
except ImportError:
    from config import settings  # type: ignore


def reference_bucket() -> str:
    return str(getattr(settings, "job_reference_attachments_bucket", "") or "job-reference-attachments").strip()


_ALLOWED_EXT = frozenset({"jpg", "jpeg", "png", "webp", "pdf", "docx", "xlsx"})


def normalize_extension(filename: str) -> str:
    base = str(filename or "").strip().rsplit("/", 1)[-1]
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[-1].lower()


def is_allowed_attachment(filename: str) -> bool:
    return normalize_extension(filename) in _ALLOWED_EXT


def content_type_for_filename(filename: str) -> str:
    ext = normalize_extension(filename)
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(ext, "application/octet-stream")


def is_image_filename(filename: str) -> bool:
    return normalize_extension(filename) in {"jpg", "jpeg", "png", "webp"}


def storage_path_for_upload(job_id: str, original_name: str) -> tuple[str, str]:
    """Return (storage_key, safe_display_name)."""
    ext = normalize_extension(original_name) or "bin"
    if ext not in _ALLOWED_EXT:
        ext = "bin"
    raw = str(original_name or "file").strip().rsplit("/", 1)[-1]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)[:120] or f"file.{ext}"
    if "." not in safe:
        safe = f"{safe}.{ext}"
    key = f"jobs/{str(job_id).strip()}/reference/{uuid.uuid4().hex}_{safe}"
    return key, safe


def filter_rows_for_package(rows: list[dict[str, Any]], visible_task_ids: set[str]) -> list[dict[str, Any]]:
    """Job-wide (no task_id) + rows whose task_id is in the daily package."""
    out: list[dict[str, Any]] = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        tid = str(r.get("task_id") or "").strip()
        if not tid:
            out.append(r)
            continue
        if tid in visible_task_ids:
            out.append(r)
    return out
