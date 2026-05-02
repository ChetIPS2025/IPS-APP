"""Task photo UI: take/upload, thumbnails, replace/delete; daily review progress slots."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Callable

import streamlit as st


def _uploader_profile() -> dict[str, Any]:
    try:
        from auth import current_profile

        p = current_profile()
        return p if isinstance(p, dict) else {}
    except Exception:
        return {}


def _uploader_slug(profile: dict[str, Any]) -> str:
    for k in ("full_name", "display_name", "name"):
        s = str(profile.get(k) or "").strip().lower()
        if s:
            slug = re.sub(r"[^a-z0-9]+", "", s)[:12]
            if slug:
                return slug
    em = str(profile.get("email") or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "", em.split("@")[0])[:12]
    return slug or "user"


def _uploader_display_name(profile: dict[str, Any]) -> str:
    for k in ("full_name", "display_name", "name"):
        v = str(profile.get(k) or "").strip()
        if v:
            return v[:200]
    v = str(profile.get("email") or "").strip()
    return v[:200] if v else ""


def _photo_capture_columns(profile: dict[str, Any]) -> dict[str, Any]:
    """Extra insert columns when sql/052 is applied."""
    uid = str(profile.get("id") or profile.get("user_id") or "").strip()
    name = _uploader_display_name(profile)
    out: dict[str, Any] = {}
    if uid:
        out["captured_by_user_id"] = uid[:500]
    if name:
        out["captured_by_name"] = name[:500]
    return out

try:
    from app.db import (
        create_signed_url,
        delete_rows,
        delete_rows_admin,
        delete_storage_object_admin,
        fetch_by_match,
        fetch_by_match_admin,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
        upload_bytes,
        upload_bytes_admin,
    )
except ImportError:
    from db import (  # type: ignore
        create_signed_url,
        delete_rows,
        delete_rows_admin,
        delete_storage_object_admin,
        fetch_by_match,
        fetch_by_match_admin,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
        upload_bytes,
        upload_bytes_admin,
    )

try:
    from app.config import settings as _settings
except ImportError:
    from config import settings as _settings  # type: ignore

try:
    from app.services import task_photos as tp
except ImportError:
    import services.task_photos as tp  # type: ignore


def _task_photo_bucket_name() -> str:
    return str(getattr(_settings, "task_photos_bucket", None) or "task-photos").strip()


def _is_task_photo_object_key(path: str) -> bool:
    p = str(path or "").strip()
    return bool(re.match(r"^[0-9a-fA-F-]{36}/[0-9a-fA-F-]{36}/", p))


def sign_task_photo_url(path: str, *, expires_in: int = 2400) -> str:
    """Signed URL for a storage key (task-photos bucket vs default ips-storage)."""
    p = str(path or "").strip()
    if not p:
        return ""
    if p.startswith("http"):
        return p
    b = _task_photo_bucket_name() if _is_task_photo_object_key(p) else None
    return create_signed_url(p, expires_in=expires_in, bucket=b)


def _w(admin: bool) -> tuple[Callable, Callable, Callable]:
    if admin:
        return insert_row_admin, update_rows_admin, delete_rows_admin
    return insert_row, update_rows, delete_rows


def _normalize_photo_row(r: dict[str, Any], *, source: str) -> dict[str, Any]:
    path = str(r.get("file_url") or r.get("storage_path") or "").strip()
    row = {**r, "storage_path": path, "file_url": path}
    if source == "task_photos":
        row["_photo_source"] = "task_photos"
    else:
        row["_photo_source"] = "legacy"
    return row


def fetch_task_photos(task_id: str, *, admin: bool) -> list[dict[str, Any]]:
    fn = fetch_by_match_admin if admin else fetch_by_match
    merged: list[dict[str, Any]] = []
    try:
        tp_rows = list(fn("task_photos", {"task_id": str(task_id)}, limit=200) or [])
        merged.extend(_normalize_photo_row(r, source="task_photos") for r in tp_rows if isinstance(r, dict))
    except Exception:
        pass
    have_before = any(str((r or {}).get("photo_type") or "").lower() == tp.PHOTO_TYPES_BEFORE for r in merged)
    have_after = any(str((r or {}).get("photo_type") or "").lower() == tp.PHOTO_TYPES_AFTER for r in merged)
    try:
        leg = list(fn("job_task_photos", {"task_id": str(task_id)}, limit=200) or [])
        for r in leg:
            if not isinstance(r, dict):
                continue
            pt = str(r.get("photo_type") or "").lower()
            if pt == tp.PHOTO_TYPES_BEFORE and have_before:
                continue
            if pt == tp.PHOTO_TYPES_AFTER and have_after:
                continue
            merged.append(_normalize_photo_row(r, source="legacy"))
    except Exception:
        pass
    return merged


def _resolve_job_id(task_id: str, *, admin: bool) -> str:
    fn = fetch_by_match_admin if admin else fetch_by_match
    try:
        rows = fn("job_tasks", {"id": str(task_id)}, limit=1) or []
        if rows and isinstance(rows[0], dict):
            return str(rows[0].get("job_id") or "").strip()
    except Exception:
        pass
    return ""


def _fetch_review_slots(job_id: str, review_date: str, *, admin: bool) -> dict[int, dict[str, Any]]:
    fn = fetch_by_match_admin if admin else fetch_by_match
    out: dict[int, dict[str, Any]] = {}
    for slot in (1, 2, 3):
        try:
            rows = fn(
                "job_daily_review_progress_photos",
                {"job_id": str(job_id), "review_date": str(review_date)[:10], "slot": slot},
                limit=1,
            )
            if rows:
                out[slot] = rows[0]
        except Exception:
            continue
    return out


def _purge_storage(path: str) -> None:
    p = str(path or "").strip()
    if not p:
        return
    try:
        b = _task_photo_bucket_name() if _is_task_photo_object_key(p) else None
        delete_storage_object_admin(p, bucket=b)
    except Exception:
        pass


def _upload_bytes(path: str, data: bytes, ctype: str, *, admin: bool) -> None:
    if admin:
        upload_bytes_admin(path, data, content_type=ctype)
    else:
        upload_bytes(path, data, content_type=ctype)


def _upload_task_photo_object(rel_key: str, data: bytes, ctype: str, *, admin: bool) -> None:
    b = _task_photo_bucket_name()
    if admin:
        upload_bytes_admin(rel_key, data, content_type=ctype, bucket=b)
    else:
        upload_bytes(rel_key, data, content_type=ctype, bucket=b)


def _replace_type_row(
    *,
    task_id: str,
    photo_type: str,
    raw: bytes,
    fname: str,
    admin: bool,
    capture_profile: dict[str, Any] | None = None,
    daily_work_package_id: str | None = None,
) -> str:
    """Replace before/after in ``task_photos`` + ``task-photos`` bucket; returns object key (file_url)."""
    data, ctype, _sfx = tp.compress_image_bytes(raw, fname)
    prof = capture_profile if isinstance(capture_profile, dict) else _uploader_profile()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    job_id = _resolve_job_id(str(task_id), admin=admin)
    if not job_id:
        raise RuntimeError("Could not resolve job_id for task; cannot upload task photo.")
    rel_key = f"{job_id}/{task_id}/{ts}.jpg"
    ins, upd, dlt = _w(admin)
    fn = fetch_by_match_admin if admin else fetch_by_match
    for tbl in ("task_photos", "job_task_photos"):
        try:
            existing = fn(tbl, {"task_id": str(task_id), "photo_type": photo_type}, limit=10) or []
        except Exception:
            existing = []
        for ex in existing:
            eid = str((ex or {}).get("id") or "").strip()
            old = str((ex or {}).get("file_url") or (ex or {}).get("storage_path") or "").strip()
            if old:
                try:
                    if tbl == "task_photos":
                        delete_storage_object_admin(old, bucket=_task_photo_bucket_name())
                    else:
                        _purge_storage(old)
                except Exception:
                    pass
            if eid:
                try:
                    dlt(tbl, {"id": eid})
                except Exception:
                    pass
    _upload_task_photo_object(rel_key, data, ctype, admin=admin)
    up_name = _uploader_display_name(prof)
    row_new: dict[str, Any] = {
        "task_id": str(task_id),
        "job_id": str(job_id),
        "photo_type": str(photo_type),
        "file_url": rel_key[:2000],
        "content_type": ctype[:120],
        "uploaded_by": up_name[:500] if up_name else None,
    }
    dwp = str(daily_work_package_id or "").strip()
    if dwp:
        row_new["daily_work_package_id"] = dwp
    try:
        ins("task_photos", row_new)
    except Exception:
        row_fallback = dict(row_new)
        row_fallback.pop("daily_work_package_id", None)
        try:
            ins("task_photos", row_fallback)
        except Exception:
            slug = _uploader_slug(prof)
            leg_path = f"job_tasks/{task_id}/{photo_type}_{ts}_{slug}{_sfx}"
            _upload_bytes(leg_path, data, ctype, admin=admin)
            ins(
                "job_task_photos",
                {
                    "task_id": str(task_id),
                    "photo_type": str(photo_type),
                    "storage_path": leg_path[:2000],
                    "content_type": ctype[:120],
                    **_photo_capture_columns(prof),
                },
            )
            rel_key = leg_path
    if photo_type == tp.PHOTO_TYPES_AFTER:
        upd(
            "job_tasks",
            {"after_photo_url": rel_key[:2000], "updated_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(task_id)},
        )
    if photo_type == tp.PHOTO_TYPES_BEFORE:
        upd(
            "job_tasks",
            {"before_photo_url": rel_key[:2000], "updated_at": datetime.now(timezone.utc).isoformat()},
            {"id": str(task_id)},
        )
    return rel_key


def _insert_progress(
    *,
    task_id: str,
    raw: bytes,
    fname: str,
    admin: bool,
    capture_profile: dict[str, Any] | None = None,
    daily_work_package_id: str | None = None,
) -> None:
    data, ctype, _sfx = tp.compress_image_bytes(raw, fname)
    prof = capture_profile if isinstance(capture_profile, dict) else _uploader_profile()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    job_id = _resolve_job_id(str(task_id), admin=admin)
    if not job_id:
        raise RuntimeError("Could not resolve job_id for task; cannot upload progress photo.")
    rel_key = f"{job_id}/{task_id}/progress_{ts}.jpg"
    ins, _, _ = _w(admin)
    _upload_task_photo_object(rel_key, data, ctype, admin=admin)
    up_name = _uploader_display_name(prof)
    row_new: dict[str, Any] = {
        "task_id": str(task_id),
        "job_id": str(job_id),
        "photo_type": tp.PHOTO_TYPES_PROGRESS,
        "file_url": rel_key[:2000],
        "content_type": ctype[:120],
        "uploaded_by": up_name[:500] if up_name else None,
    }
    dwp = str(daily_work_package_id or "").strip()
    if dwp:
        row_new["daily_work_package_id"] = dwp
    try:
        ins("task_photos", row_new)
    except Exception:
        row_fb = dict(row_new)
        row_fb.pop("daily_work_package_id", None)
        try:
            ins("task_photos", row_fb)
        except Exception:
            slug = _uploader_slug(prof)
            leg_path = f"job_tasks/{task_id}/progress_{ts}_{slug}{_sfx}"
            _upload_bytes(leg_path, data, ctype, admin=admin)
            ins(
                "job_task_photos",
                {
                    "task_id": str(task_id),
                    "photo_type": tp.PHOTO_TYPES_PROGRESS,
                    "storage_path": leg_path[:2000],
                    "content_type": ctype[:120],
                    **_photo_capture_columns(prof),
                },
            )


def remove_typed_task_photo(*, task_id: str, photo_type: str, admin_read: bool) -> None:
    """Remove before or after from task_photos (and legacy job_task_photos) and clear job_tasks URL columns."""
    if str(photo_type).lower() not in (tp.PHOTO_TYPES_BEFORE, tp.PHOTO_TYPES_AFTER):
        return
    _, upd, dlt = _w(admin_read)
    fn = fetch_by_match_admin if admin_read else fetch_by_match
    for tbl in ("task_photos", "job_task_photos"):
        try:
            ex = fn(tbl, {"task_id": str(task_id), "photo_type": str(photo_type)}, limit=10) or []
        except Exception:
            ex = []
        for e in ex:
            eid = str((e or {}).get("id") or "").strip()
            old = str((e or {}).get("file_url") or (e or {}).get("storage_path") or "").strip()
            if old:
                try:
                    if tbl == "task_photos":
                        delete_storage_object_admin(old, bucket=_task_photo_bucket_name())
                    else:
                        _purge_storage(old)
                except Exception:
                    pass
            if eid:
                try:
                    dlt(tbl, {"id": eid})
                except Exception:
                    pass
    fld = "before_photo_url" if str(photo_type).lower() == tp.PHOTO_TYPES_BEFORE else "after_photo_url"
    upd(
        "job_tasks",
        {fld: "", "updated_at": datetime.now(timezone.utc).isoformat()},
        {"id": str(task_id)},
    )


def _thumb(path: str, *, key: str) -> None:
    p = str(path or "").strip()
    if not p:
        return
    url = sign_task_photo_url(p, expires_in=2400) if not p.startswith("http") else p
    if url:
        try:
            st.image(url, width=120)
        except Exception:
            st.caption("Preview unavailable")


def render_task_photo_strip(
    *,
    task_id: str,
    task_row: dict[str, Any],
    can_edit: bool,
    admin_read: bool,
    daily_work_package_id: str | None = None,
) -> None:
    """Mobile-first: before / progress / after with Take photo + Upload + thumb + delete."""
    st.markdown(
        """
        <style>
        .ips-tph {
            color: #0f172a;
            font-size: 0.9rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-tph-card-anchor) {
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 12px !important;
            padding: 0.75rem !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-tph-card-anchor) button {
            min-height: 44px !important;
            border-radius: 10px !important;
        }
        @media (max-width: 1100px) {
            div[data-testid="stHorizontalBlock"]:has(.ips-tph-card-anchor) {
                flex-wrap: wrap !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.ips-tph-card-anchor) > div[data-testid="column"] {
                flex: 1 1 min(280px, 100%) !important;
                min-width: min(280px, 100%) !important;
                max-width: 100% !important;
            }
        }
        @media (max-width: 640px) {
            div[data-testid="stHorizontalBlock"]:has(.ips-tph-card-anchor) > div[data-testid="column"] {
                flex-basis: 100% !important;
                min-width: 0 !important;
                width: 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    rows = fetch_task_photos(task_id, admin=admin_read)
    latest = tp.latest_photo_path_by_type(rows, task_id=str(task_id))
    progress_rows = [r for r in rows if str((r or {}).get("photo_type") or "").lower() == tp.PHOTO_TYPES_PROGRESS]
    progress_rows.sort(key=lambda r: str((r or {}).get("created_at") or ""), reverse=True)

    def _cell(pt: str, title: str) -> None:
        st.markdown('<span class="ips-tph-card-anchor"></span>', unsafe_allow_html=True)
        st.markdown(f'<div class="ips-tph"><strong>{title}</strong></div>', unsafe_allow_html=True)
        cur = latest.get(pt) or (
            str(task_row.get("before_photo_url") or "").strip()
            if pt == tp.PHOTO_TYPES_BEFORE
            else str(task_row.get("after_photo_url") or "").strip()
            if pt == tp.PHOTO_TYPES_AFTER
            else ""
        )
        if cur and pt != tp.PHOTO_TYPES_PROGRESS:
            _thumb(cur, key=f"th_{task_id}_{pt}")
        if pt == tp.PHOTO_TYPES_PROGRESS:
            for pr in progress_rows[:6]:
                pid = str(pr.get("id") or "")
                pp = str(pr.get("storage_path") or pr.get("file_url") or "")
                c1, c2 = st.columns((3, 1))
                with c1:
                    _thumb(pp, key=f"thp_{pid}")
                with c2:
                    if can_edit and pid and st.button("Del", key=f"delpr_{pid}"):
                        _, _, dlt = _w(admin_read)
                        tbl = "task_photos" if _is_task_photo_object_key(pp) else "job_task_photos"
                        try:
                            if tbl == "task_photos":
                                delete_storage_object_admin(pp, bucket=_task_photo_bucket_name())
                            else:
                                _purge_storage(pp)
                            dlt(tbl, {"id": pid})
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
        if not can_edit:
            return
        st.caption("📷 Take Photo")
        cam = st.camera_input(
            title,
            key=f"cam_{task_id}_{pt}",
            label_visibility="collapsed",
            help=f"Camera: {title}",
        )
        st.caption("⬆ Upload")
        up = st.file_uploader(
            title,
            type=["jpg", "jpeg", "png", "webp"],
            key=f"up_{task_id}_{pt}",
            label_visibility="collapsed",
            help=f"Upload file: {title}",
        )
        src = None
        name = "photo.jpg"
        if cam is not None:
            src = cam.getvalue()
            name = "camera.jpg"
        elif up is not None:
            src = up.getvalue()
            name = str(getattr(up, "name", "") or "upload.jpg")
        if src and st.button(f"Save {title}", key=f"sv_{task_id}_{pt}", use_container_width=True):
            try:
                if pt == tp.PHOTO_TYPES_PROGRESS:
                    _insert_progress(
                        task_id=str(task_id),
                        raw=src,
                        fname=name,
                        admin=admin_read,
                        daily_work_package_id=daily_work_package_id,
                    )
                else:
                    _replace_type_row(
                        task_id=str(task_id),
                        photo_type=pt,
                        raw=src,
                        fname=name,
                        admin=admin_read,
                        daily_work_package_id=daily_work_package_id,
                    )
                st.success("Saved.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        if pt != tp.PHOTO_TYPES_PROGRESS and cur and st.button(
            f"Remove {title}",
            key=f"rm_{task_id}_{pt}",
            use_container_width=True,
        ):
            try:
                remove_typed_task_photo(task_id=str(task_id), photo_type=pt, admin_read=admin_read)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    c1, c2, c3 = st.columns(3, gap="small")
    with c1:
        _cell(tp.PHOTO_TYPES_BEFORE, "Before")
    with c2:
        _cell(tp.PHOTO_TYPES_PROGRESS, "Progress")
    with c3:
        _cell(tp.PHOTO_TYPES_AFTER, "After")


def render_daily_review_progress_strip(
    *,
    job_id: str,
    review_date: str,
    can_edit: bool,
    admin_read: bool,
) -> None:
    """1–3 general progress photos for the job + review day."""
    st.markdown("##### Shift photos (optional, up to 3)")
    st.caption("General site progress — not tied to a single task.")
    slots = _fetch_review_slots(job_id, review_date, admin=admin_read)
    ins, upd, dlt = _w(admin_read)
    r_iso = str(review_date)[:10]
    for slot in (1, 2, 3):
        row = slots.get(slot)
        path = str((row or {}).get("storage_path") or "").strip()
        rid = str((row or {}).get("id") or "").strip()
        with st.container(border=True):
            st.markdown('<span class="ips-tph-card-anchor"></span>', unsafe_allow_html=True)
            st.caption(f"Slot {slot}")
            if path:
                _thumb(path, key=f"jdrps_{job_id}_{r_iso}_{slot}")
            if not can_edit:
                continue
            st.caption("Take Photo")
            cam = st.camera_input(
                f"S{slot}",
                key=f"jdrpc_{job_id}_{r_iso}_{slot}",
                label_visibility="collapsed",
            )
            st.caption("Upload Photo")
            up = st.file_uploader(
                f"Slot{slot}",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"jdrpu_{job_id}_{r_iso}_{slot}",
                label_visibility="collapsed",
            )
            src = None
            name = "photo.jpg"
            if cam is not None:
                src = cam.getvalue()
                name = "camera.jpg"
            elif up is not None:
                src = up.getvalue()
                name = str(getattr(up, "name", "") or "upload.jpg")
            b1, b2 = st.columns(2, gap="small")
            with b1:
                if src and st.button("Save", key=f"jdrpsv_{job_id}_{r_iso}_{slot}", use_container_width=True):
                    data, ctype, sfx = tp.compress_image_bytes(src, name)
                    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
                    new_path = f"job_daily_review/{job_id}/{r_iso}_slot{slot}_{ts}{sfx}"
                    _upload_bytes(new_path, data, ctype, admin=admin_read)
                    try:
                        if rid:
                            _purge_storage(path)
                            dlt("job_daily_review_progress_photos", {"id": rid})
                        ins(
                            "job_daily_review_progress_photos",
                            {
                                "job_id": str(job_id),
                                "review_date": r_iso,
                                "slot": int(slot),
                                "storage_path": new_path[:2000],
                                "content_type": ctype[:120],
                            },
                        )
                        st.success("Saved.")
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))
            with b2:
                if rid and st.button("Delete", key=f"jdrpdl_{job_id}_{r_iso}_{slot}", use_container_width=True):
                    _purge_storage(path)
                    try:
                        dlt("job_daily_review_progress_photos", {"id": rid})
                        st.rerun()
                    except Exception as exc:
                        st.error(str(exc))


def task_has_after_for_validation(
    *,
    task_id: str,
    task_row: dict[str, Any],
    prior_review: dict[str, Any],
    pending_upload_bytes: bytes | None,
    admin_read: bool,
) -> bool:
    """Used before save: after in DB, legacy columns, review row, or new bytes this submit."""
    if pending_upload_bytes:
        return True
    rows = fetch_task_photos(task_id, admin=admin_read)
    by = tp.photos_by_task_id(rows)
    if tp.task_has_after_photo(str(task_id), task_row, by):
        return True
    if str((prior_review or {}).get("after_photo_url") or "").strip():
        return True
    if str(task_row.get("after_photo_url") or "").strip():
        return True
    return False


def save_review_after_photo(
    *,
    task_id: str,
    review_date: str,
    raw: bytes | None,
    fname: str,
    admin_read: bool,
) -> str:
    """Write compressed after image to job_task_photos + sync job_tasks; returns path or ''."""
    if raw is None or not len(raw):
        return ""
    return _replace_type_row(
        task_id=str(task_id),
        photo_type=tp.PHOTO_TYPES_AFTER,
        raw=raw,
        fname=fname,
        admin=admin_read,
        capture_profile=_uploader_profile(),
    )


def save_task_after_photo_bytes(
    *,
    task_id: str,
    raw: bytes,
    fname: str,
    admin_read: bool,
) -> str:
    """After photo only (e.g. quick capture); syncs job_tasks.after_photo_url."""
    return _replace_type_row(
        task_id=str(task_id),
        photo_type=tp.PHOTO_TYPES_AFTER,
        raw=raw,
        fname=fname,
        admin=admin_read,
        capture_profile=_uploader_profile(),
    )
