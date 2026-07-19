"""In-app notifications for schedule assignment changes."""

from __future__ import annotations

from typing import Any

from app.auth import current_profile
from app.db import get_client, run_user_supabase_operation
from app.services.scheduling_service import list_event_employees


def _employee_user_ids(employee_ids: list[str]) -> dict[str, str]:
    """Map employee_id -> profile user id when available."""
    wanted = {str(e).strip() for e in employee_ids if str(e).strip()}
    if not wanted:
        return {}

    def _run():
        resp = (
            get_client()
            .table("profiles")
            .select("id, employee_id")
            .in_("employee_id", list(wanted))
            .execute()
        )
        out: dict[str, str] = {}
        for row in resp.data or []:
            eid = str(row.get("employee_id") or "").strip()
            uid = str(row.get("id") or "").strip()
            if eid and uid:
                out[eid] = uid
        return out

    try:
        return run_user_supabase_operation("read profile links", _run, friendly_on_failure=False)
    except Exception:
        return {}


def _insert_notification(*, user_id: str, title: str, body: str, event_id: str, ntype: str) -> None:
    if not user_id:
        return

    def _run():
        get_client().table("notifications").insert(
            {
                "user_id": user_id,
                "title": title,
                "body": body,
                "notification_type": ntype,
                "related_table": "schedule_events",
                "related_id": event_id or None,
            }
        ).execute()

    try:
        run_user_supabase_operation("insert schedule notification", _run, friendly_on_failure=False)
    except Exception:
        pass


def notify_schedule_event_saved(
    event: dict[str, Any],
    *,
    previous: dict[str, Any] | None = None,
    employee_ids: list[str] | None = None,
) -> None:
    """Notify assigned employees on meaningful schedule changes (confirmed events only)."""
    if not isinstance(event, dict):
        return
    status = str(event.get("status") or "").strip().lower()
    if status != "confirmed":
        return

    eid = str(event.get("id") or "").strip()
    if not eid:
        return

    prev = previous or {}
    prev_status = str(prev.get("status") or "").strip().lower()
    changed = (
        not prev
        or prev_status != "confirmed"
        or str(prev.get("start_at") or "") != str(event.get("start_at") or "")
        or str(prev.get("end_at") or "") != str(event.get("end_at") or "")
        or str(prev.get("job_id") or "") != str(event.get("job_id") or "")
        or str(prev.get("location") or "") != str(event.get("location") or "")
    )
    if not changed:
        return

    assigned = employee_ids
    if assigned is None:
        assigned = [str(r.get("employee_id") or "") for r in list_event_employees(eid)]

    user_map = _employee_user_ids(assigned)
    title = str(event.get("title") or "Schedule update")
    when = f"{str(event.get('start_at') or '')[:16]} – {str(event.get('end_at') or '')[:16]}"
    location = str(event.get("location") or "").strip()
    body_parts = [when]
    if location:
        body_parts.append(location)
    body = " · ".join(body_parts)

    actor = current_profile() or {}
    _ = actor  # reserved for future audit text

    if str(event.get("status") or "").lower() == "cancelled":
        ntype = "schedule_cancelled"
        title = f"Cancelled: {title}"
    else:
        ntype = "schedule_assignment"

    for emp_id in assigned:
        uid = user_map.get(str(emp_id or "").strip())
        if uid:
            _insert_notification(user_id=uid, title=title, body=body, event_id=eid, ntype=ntype)
