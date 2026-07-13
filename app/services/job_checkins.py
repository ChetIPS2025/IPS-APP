"""Job site check-in / check-out."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.services.field_ops_util import fetch_fn, table_exists, write_fn

_LOG = logging.getLogger(__name__)


def fetch_open_checkin(
    *,
    job_id: str,
    user_id: str | None = None,
    admin: bool = False,
) -> dict[str, Any] | None:
    jid = str(job_id or "").strip()
    if not jid or not table_exists("job_checkins", admin=admin):
        return None
    fn = fetch_fn(admin=admin)
    match: dict[str, Any] = {"job_id": jid, "status": "checked_in"}
    if user_id:
        match["user_id"] = str(user_id).strip()
    rows = fn("job_checkins", match, limit=5)
    rows = sorted(rows or [], key=lambda r: str(r.get("check_in_time") or ""), reverse=True)
    for r in rows or []:
        if isinstance(r, dict) and not r.get("check_out_time"):
            return r
    return None


def check_in(
    *,
    job_id: str,
    user_id: str | None,
    user_name: str,
    latitude: float | None = None,
    longitude: float | None = None,
    notes: str = "",
    admin: bool = False,
) -> dict[str, Any]:
    jid = str(job_id or "").strip()
    if not jid:
        raise ValueError("job_id required")
    if not table_exists("job_checkins", admin=admin):
        raise RuntimeError("job_checkins table not found — run sql/061_field_operations_phase1.sql")
    open_row = fetch_open_checkin(job_id=jid, user_id=user_id, admin=admin)
    if open_row:
        raise RuntimeError("You are already checked in on this job. Check out first.")
    insert_fn, _, _ = write_fn(admin=admin)
    now = datetime.now(timezone.utc).isoformat()
    row = insert_fn(
        "job_checkins",
        {
            "job_id": jid,
            "user_id": str(user_id).strip() if user_id else None,
            "user_name": str(user_name or "").strip()[:200],
            "check_in_time": now,
            "latitude": latitude,
            "longitude": longitude,
            "notes": str(notes or "").strip()[:2000],
            "status": "checked_in",
        },
    )
    from app.services.job_timeline import EVENT_CHECKIN, log_job_event
    log_job_event(
        job_id=jid,
        event_type=EVENT_CHECKIN,
        title="Site check-in",
        description=str(notes or "").strip() or "Arrived on site",
        user_name=user_name,
        user_id=user_id,
        related_table="job_checkins",
        related_id=str(row.get("id") or ""),
        admin=admin,
    )
    return row


def check_out(
    *,
    checkin_id: str,
    notes: str = "",
    latitude: float | None = None,
    longitude: float | None = None,
    admin: bool = False,
) -> dict[str, Any]:
    cid = str(checkin_id or "").strip()
    if not cid:
        raise ValueError("checkin_id required")
    _, update_fn, _ = write_fn(admin=admin)
    now = datetime.now(timezone.utc).isoformat()
    patch: dict[str, Any] = {
        "check_out_time": now,
        "status": "checked_out",
    }
    if notes:
        patch["notes"] = str(notes).strip()[:2000]
    if latitude is not None:
        patch["latitude"] = latitude
    if longitude is not None:
        patch["longitude"] = longitude
    update_fn("job_checkins", patch, {"id": cid})
    fn = fetch_fn(admin=admin)
    rows = fn("job_checkins", {"id": cid}, limit=1)
    row = rows[0] if rows else {"id": cid}
    from app.services.job_timeline import EVENT_CHECKIN, log_job_event
    log_job_event(
        job_id=str(row.get("job_id") or ""),
        event_type=EVENT_CHECKIN,
        title="Site check-out",
        description=str(notes or "").strip() or "Left site",
        user_name=str(row.get("user_name") or ""),
        user_id=str(row.get("user_id") or "") or None,
        related_table="job_checkins",
        related_id=cid,
        admin=admin,
    )
    return row


def fetch_checkins_for_job(job_id: str, *, admin: bool = False, limit: int = 50) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid or not table_exists("job_checkins", admin=admin):
        return []
    fn = fetch_fn(admin=admin)
    rows = list(fn("job_checkins", {"job_id": jid}, limit=limit) or [])
    rows.sort(key=lambda r: str(r.get("check_in_time") or ""), reverse=True)
    return rows
