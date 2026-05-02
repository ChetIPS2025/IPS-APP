"""Task photo helpers: compression, after-photo checks, dashboard aggregates."""

from __future__ import annotations

import io
import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

_LOG = logging.getLogger(__name__)

PHOTO_TYPES_BEFORE = "before"
PHOTO_TYPES_AFTER = "after"
PHOTO_TYPES_PROGRESS = "progress"
PHOTO_TYPES = (PHOTO_TYPES_BEFORE, PHOTO_TYPES_AFTER, PHOTO_TYPES_PROGRESS)


def compress_image_bytes(data: bytes, filename_hint: str = "") -> tuple[bytes, str, str]:
    """
    Resize and re-encode for upload. Returns (bytes, content_type, file_suffix).
    Falls back to original bytes if Pillow is missing or input is not a raster image.
    """
    fn = str(filename_hint or "").lower()
    ext = ".jpg"
    if ".png" in fn or fn.endswith("png"):
        ext = ".png"
    elif ".webp" in fn or fn.endswith("webp"):
        ext = ".webp"

    try:
        from PIL import Image, ImageOps
    except ImportError:
        _LOG.debug("Pillow not available; skipping image compression")
        return data, "application/octet-stream", ext

    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im)
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        elif im.mode == "RGBA":
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[3])
            im = bg
        max_side = 1600
        w, h = im.size
        if max(w, h) > max_side:
            ratio = max_side / float(max(w, h))
            im = im.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=82, optimize=True)
        blob = out.getvalue()
        return blob, "image/jpeg", ".jpg"
    except Exception as exc:
        _LOG.warning("Image compression failed, using original: %s", exc)
        return data, "image/jpeg" if ext == ".jpg" else "image/png", ext


def _parse_created_day(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if "T" in s:
        return s[:10]
    return s[:10] if len(s) >= 10 else None


def photos_by_task_id(rows: list[dict[str, Any]] | None) -> dict[str, set[str]]:
    """task_id -> set of photo_type present."""
    m: dict[str, set[str]] = defaultdict(set)
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        tid = str(r.get("task_id") or "").strip()
        pt = str(r.get("photo_type") or "").strip().lower()
        if tid and pt in PHOTO_TYPES:
            m[tid].add(pt)
    return dict(m)


def task_has_after_photo(
    task_id: str,
    task_row: dict[str, Any] | None,
    photos_by_task: dict[str, set[str]] | None,
) -> bool:
    """True if legacy column or job_task_photos has an after image."""
    if task_row and str(task_row.get("after_photo_url") or "").strip():
        return True
    if photos_by_task and task_id in photos_by_task and PHOTO_TYPES_AFTER in photos_by_task[task_id]:
        return True
    return False


def latest_photo_path_by_type(rows: list[dict[str, Any]], *, task_id: str) -> dict[str, str]:
    """For task_id, latest storage_path per photo_type (by created_at)."""
    best: dict[str, tuple[str, str]] = {}  # type -> (path, ts_str)
    for r in rows or []:
        if not isinstance(r, dict) or str(r.get("task_id") or "").strip() != str(task_id):
            continue
        pt = str(r.get("photo_type") or "").strip().lower()
        if pt not in PHOTO_TYPES:
            continue
        path = str(r.get("storage_path") or r.get("file_url") or "").strip()
        if not path:
            continue
        ts = str(r.get("created_at") or "")
        prev = best.get(pt)
        if prev is None or ts >= prev[1]:
            best[pt] = (path, ts)
    return {k: v[0] for k, v in best.items()}


def count_tasks_with_photos_uploaded_today(
    photo_rows: list[dict[str, Any]] | None,
    *,
    today: date,
) -> int:
    """Distinct task_ids with any job_task_photos row created on ``today``."""
    return count_tasks_with_photos_uploaded_today_filtered(photo_rows, today=today, allowed_task_ids=None)


def count_tasks_with_photos_uploaded_today_filtered(
    photo_rows: list[dict[str, Any]] | None,
    *,
    today: date,
    allowed_task_ids: set[str] | None,
) -> int:
    """Distinct task_ids with any job_task_photos row created on ``today`` (optionally scoped to task ids)."""
    t_iso = today.isoformat()[:10]
    seen: set[str] = set()
    for r in photo_rows or []:
        if not isinstance(r, dict):
            continue
        d = _parse_created_day(r.get("created_at"))
        if d != t_iso:
            continue
        tid = str(r.get("task_id") or "").strip()
        if not tid:
            continue
        if allowed_task_ids is not None and tid not in allowed_task_ids:
            continue
        seen.add(tid)
    return len(seen)


def before_after_storage_paths(
    task_row: dict[str, Any],
    photo_rows_for_task: list[dict[str, Any]] | None,
    *,
    task_id: str,
) -> tuple[str, str]:
    """Resolved storage paths (or legacy URLs) for before and after; may be empty strings."""
    paths = latest_photo_path_by_type(list(photo_rows_for_task or []), task_id=str(task_id))
    b = str(paths.get(PHOTO_TYPES_BEFORE) or "").strip() or str(task_row.get("before_photo_url") or "").strip()
    a = str(paths.get(PHOTO_TYPES_AFTER) or "").strip() or str(task_row.get("after_photo_url") or "").strip()
    return b, a


def tasks_completed_today_missing_after(
    tasks: list[dict[str, Any]],
    photos_by_task: dict[str, set[str]],
    *,
    today: date,
) -> int:
    t_iso = today.isoformat()[:10]
    n = 0
    for t in tasks or []:
        if not isinstance(t, dict):
            continue
        tid = str(t.get("id") or "").strip()
        st = str(t.get("status") or "").strip().lower()
        cd = str(t.get("completed_date") or "")[:10]
        if st != "complete" or cd != t_iso:
            continue
        if not task_has_after_photo(tid, t, photos_by_task):
            n += 1
    return n
