"""Unified job timeline / audit trail."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from services.field_ops_util import fetch_fn, table_exists, write_fn

_LOG = logging.getLogger(__name__)

EVENT_DAILY_REPORT = "daily_report"
EVENT_PHOTO = "photo"
EVENT_CHECKIN = "checkin"
EVENT_CREW_TIME = "crew_time"
EVENT_STATUS = "status"
EVENT_NOTE = "note"


def log_job_event(
    *,
    job_id: str,
    event_type: str,
    title: str,
    description: str = "",
    user_name: str = "",
    user_id: str | None = None,
    related_table: str = "",
    related_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    admin: bool = False,
) -> dict[str, Any] | None:
    """Append a timeline row when ``job_timeline`` table exists."""
    jid = str(job_id or "").strip()
    if not jid or not table_exists("job_timeline", admin=admin):
        return None
    insert_fn, _, _ = write_fn(admin=admin)
    row = {
        "job_id": jid,
        "event_type": str(event_type or "note").strip() or "note",
        "title": str(title or "").strip()[:500],
        "description": str(description or "").strip()[:8000],
        "user_name": str(user_name or "").strip()[:200],
        "user_id": str(user_id).strip() if user_id else None,
        "related_table": str(related_table or "").strip()[:120],
        "related_id": str(related_id).strip() if related_id else None,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        return insert_fn("job_timeline", row)
    except Exception as exc:
        _LOG.warning("log_job_event failed: %s", exc)
        return None


def fetch_timeline_for_job(job_id: str, *, admin: bool = False, limit: int = 200) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid or not table_exists("job_timeline", admin=admin):
        return []
    fn = fetch_fn(admin=admin)
    rows = fn("job_timeline", {"job_id": jid}, limit=limit)
    out = list(rows or [])
    out.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return out


def timeline_badge_tone(event_type: str) -> str:
    et = str(event_type or "").strip().lower()
    if et in {"daily_report", "crew_time"}:
        return "primary"
    if et in {"photo", "checkin"}:
        return "neutral"
    if et in {"safety", "incident"}:
        return "danger"
    if et in {"status", "change_order"}:
        return "warning"
    return "neutral"


def format_timeline_row(row: dict[str, Any]) -> str:
    ts = str(row.get("created_at") or "")[:19].replace("T", " ")
    who = str(row.get("user_name") or "").strip() or "—"
    title = str(row.get("title") or "").strip() or "Update"
    desc = str(row.get("description") or "").strip()
    if desc:
        return f"**{title}** · {ts} · {who}\n\n{desc}"
    return f"**{title}** · {ts} · {who}"
