"""Job-level photo timeline (``job_photos`` table + Storage)."""

from __future__ import annotations

import io
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.field_ops_util import fetch_fn, table_exists, write_fn

_LOG = logging.getLogger(__name__)

PHOTO_CATEGORIES: tuple[str, ...] = (
    "Before",
    "During",
    "Completed",
    "Safety",
    "Damage",
    "Materials",
    "Progress",
)


def _upload_fn(*, admin: bool):
    try:
        from app.db import upload_bytes, upload_bytes_admin
    except ImportError:
        from db import upload_bytes, upload_bytes_admin  # type: ignore
    return upload_bytes_admin if admin else upload_bytes


def _compress_image(data: bytes, content_type: str, *, max_dim: int = 1920) -> tuple[bytes, str]:
    """Best-effort resize for field uploads; returns original on failure."""
    if not data or len(data) < 400_000:
        return data, content_type
    try:
        from PIL import Image
    except ImportError:
        return data, content_type
    try:
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
        w, h = img.size
        if max(w, h) > max_dim:
            ratio = max_dim / float(max(w, h))
            img = img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=85, optimize=True)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return data, content_type


def fetch_job_photos(
    job_id: str,
    *,
    admin: bool = False,
    category: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid or not table_exists("job_photos", admin=admin):
        return []
    fn = fetch_fn(admin=admin)
    match: dict[str, Any] = {"job_id": jid}
    if category and str(category).strip() in PHOTO_CATEGORIES:
        match["category"] = str(category).strip()
    rows = fn("job_photos", match, limit=limit)
    out = list(rows or [])
    out.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return out


def upload_job_photos(
    *,
    job_id: str,
    files: list[tuple[bytes, str, str]],
    uploaded_by: str = "",
    caption: str = "",
    category: str = "Progress",
    latitude: float | None = None,
    longitude: float | None = None,
    location_note: str = "",
    task_id: str | None = None,
    admin: bool = False,
) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid:
        raise ValueError("job_id required")
    if not table_exists("job_photos", admin=admin):
        raise RuntimeError("job_photos table not found — run sql/061_field_operations_phase1.sql")
    cat = str(category or "Progress").strip()
    if cat not in PHOTO_CATEGORIES:
        cat = "Progress"
    insert_fn, _, _ = write_fn(admin=admin)
    upload = _upload_fn(admin=admin)
    try:
        from app.config import settings
    except ImportError:
        from config import settings  # type: ignore
    bucket = getattr(settings, "task_photos_bucket", "task-photos")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    created: list[dict[str, Any]] = []
    for i, tup in enumerate(files):
        data, ctype, fname = tup[0], tup[1], tup[2]
        if not data:
            continue
        data, ctype = _compress_image(data, ctype or "image/jpeg")
        safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(fname or "photo").strip())[:160] or f"photo_{i}.jpg"
        storage_path = f"job_photos/{jid}/{ts}_{i}_{safe}"
        upload(storage_path, data, content_type=ctype, bucket=bucket)
        row = insert_fn(
            "job_photos",
            {
                "job_id": jid,
                "task_id": str(task_id).strip() if task_id else None,
                "uploaded_by": str(uploaded_by or "").strip()[:200],
                "caption": str(caption or "").strip()[:2000],
                "category": cat,
                "storage_path": storage_path,
                "file_name": str(fname or Path(storage_path).name)[:200],
                "content_type": ctype,
                "latitude": latitude,
                "longitude": longitude,
                "location_note": str(location_note or "").strip()[:500],
            },
        )
        created.append(row)
        try:
            from services.job_timeline import EVENT_PHOTO, log_job_event
        except ImportError:
            from app.services.job_timeline import EVENT_PHOTO, log_job_event  # type: ignore
        log_job_event(
            job_id=jid,
            event_type=EVENT_PHOTO,
            title=f"Photo · {cat}",
            description=str(caption or safe).strip(),
            user_name=uploaded_by,
            related_table="job_photos",
            related_id=str(row.get("id") or ""),
            admin=admin,
        )
    return created
