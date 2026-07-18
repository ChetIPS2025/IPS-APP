from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

_LOG = logging.getLogger(__name__)

_DELAY_FLAG_KEYS: tuple[str, ...] = (
    "delay_waiting_material",
    "delay_waiting_tools",
    "delay_waiting_direction",
    "delay_too_many_on_task",
    "delay_rework",
    "delay_equipment",
    "delay_customer",
    "delay_safety",
    "delay_other",
)

_DELAY_LABELS: dict[str, str] = {
    "delay_waiting_material": "Waiting on material",
    "delay_waiting_tools": "Waiting on tools",
    "delay_waiting_direction": "Waiting on direction",
    "delay_too_many_on_task": "Too many people on one task",
    "delay_rework": "Rework",
    "delay_equipment": "Equipment issue",
    "delay_customer": "Customer delay",
    "delay_safety": "Safety delay",
    "delay_other": "Other",
}


def delay_labels_map() -> dict[str, str]:
    return dict(_DELAY_LABELS)


def estimated_bid_labor_hours_from_estimate_json(est: dict[str, Any] | None) -> float | None:
    """
    Sum bid labor hours from estimate_json labor rows (headcount × days × (ST+OT hrs/day)).
    Returns None if there is no usable labor section.
    """
    if not est or not isinstance(est, dict):
        return None
    labor = est.get("labor")
    if not isinstance(labor, list) or not labor:
        return None
    total = 0.0
    any_row = False
    for row in labor:
        if not isinstance(row, dict):
            continue
        try:
            hc = float(row.get("headcount") or 0)
            days = float(row.get("days") or 0)
            st = float(row.get("st_hours_per_day") or 0)
            ot = float(row.get("ot_hours_per_day") or 0)
            if st == 0.0 and ot == 0.0 and row.get("hours") is not None:
                st = float(row.get("hours") or 0)
        except (TypeError, ValueError):
            continue
        if hc <= 0 and days <= 0 and st <= 0 and ot <= 0:
            continue
        any_row = True
        total += max(0.0, hc) * max(0.0, days) * (max(0.0, st) + max(0.0, ot))
    if not any_row:
        return None
    return round(total, 2)


def _parse_estimate_json(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            v = json.loads(raw)
            return v if isinstance(v, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def job_status_needs_daily_report(status: Any) -> bool:
    """Active field jobs: expect a daily supervisor report when work is ongoing."""
    from app.services.jobs_service import normalize_job_status
    return normalize_job_status(status) in {"Active", "On Hold"}


def report_has_any_delay(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    return any(bool(row.get(k)) for k in _DELAY_FLAG_KEYS)


def collect_delay_reason_counts(reports: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """Aggregate delay checkboxes across reports; return (label, count) sorted desc."""
    counts: dict[str, int] = {lbl: 0 for lbl in _DELAY_LABELS.values()}
    for r in reports or []:
        if not isinstance(r, dict):
            continue
        for k, lbl in _DELAY_LABELS.items():
            if bool(r.get(k)):
                counts[lbl] = counts.get(lbl, 0) + 1
    pairs = [(lbl, n) for lbl, n in counts.items() if n > 0]
    pairs.sort(key=lambda x: (-x[1], x[0]))
    return pairs


def _fetch_fn(*, admin: bool):
    from app.db import fetch_by_match, fetch_by_match_admin
    return fetch_by_match_admin if admin else fetch_by_match


def _write_fn(*, admin: bool):
    from app.db import (
        delete_rows,
        delete_rows_admin,
        insert_row,
        insert_row_admin,
        update_rows,
        update_rows_admin,
    )
    if admin:
        return insert_row_admin, update_rows_admin, delete_rows_admin
    return insert_row, update_rows, delete_rows


def fetch_reports_for_job(job_id: str, *, admin: bool, limit: int = 120) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid:
        return []
    fn = _fetch_fn(admin=admin)
    try:
        rows = fn(
            "supervisor_daily_reports",
            {"job_id": jid},
            columns="*",
            limit=limit,
        )
    except Exception as exc:
        _LOG.debug("fetch_reports_for_job: %s", exc)
        return []
    rows = list(rows or [])
    rows.sort(key=lambda r: str((r or {}).get("report_date") or ""), reverse=True)
    return rows


def fetch_crew_lines(report_id: str, *, admin: bool) -> list[dict[str, Any]]:
    rid = str(report_id or "").strip()
    if not rid:
        return []
    fn = _fetch_fn(admin=admin)
    try:
        rows = fn(
            "supervisor_daily_report_crew",
            {"report_id": rid},
            columns="*",
            limit=200,
        )
    except Exception as exc:
        _LOG.debug("fetch_crew_lines: %s", exc)
        return []
    rows = list(rows or [])
    rows.sort(key=lambda r: int((r or {}).get("sort_order") or 0))
    return rows


def fetch_photos_for_report(report_id: str, *, admin: bool) -> list[dict[str, Any]]:
    rid = str(report_id or "").strip()
    if not rid:
        return []
    fn = _fetch_fn(admin=admin)
    try:
        rows = fn(
            "supervisor_daily_report_photos",
            {"report_id": rid},
            columns="id,storage_path,file_name,content_type,created_at",
            limit=100,
        )
    except Exception as exc:
        _LOG.debug("fetch_photos_for_report: %s", exc)
        return []
    return list(rows or [])


def fetch_report_for_job_date(job_id: str, report_date: date, *, admin: bool) -> dict[str, Any] | None:
    jid = str(job_id or "").strip()
    if not jid:
        return None
    ds = report_date.isoformat()[:10]
    fn = _fetch_fn(admin=admin)
    try:
        rows = fn(
            "supervisor_daily_reports",
            {"job_id": jid, "report_date": ds},
            columns="*",
            limit=1,
        )
    except Exception as exc:
        _LOG.debug("fetch_report_for_job_date: %s", exc)
        return None
    return rows[0] if rows else None


def replace_crew_lines(
    report_id: str,
    crew_rows: list[dict[str, Any]],
    *,
    admin: bool,
) -> None:
    insert_fn, _, delete_fn = _write_fn(admin=admin)
    rid = str(report_id or "").strip()
    if not rid:
        return
    delete_fn("supervisor_daily_report_crew", {"report_id": rid})
    for i, row in enumerate(crew_rows):
        if not isinstance(row, dict):
            continue
        name = str(row.get("employee_name") or "").strip()
        task = str(row.get("task") or "").strip()
        try:
            hrs = float(row.get("hours") or 0)
        except (TypeError, ValueError):
            hrs = 0.0
        notes = str(row.get("notes") or "").strip()
        if not name and not task and hrs <= 0 and not notes:
            continue
        insert_fn(
            "supervisor_daily_report_crew",
            {
                "report_id": rid,
                "employee_name": name,
                "task": task,
                "hours": max(0.0, min(999.99, hrs)),
                "notes": notes,
                "sort_order": i,
            },
        )


def append_report_photos(
    report_id: str,
    files: list[tuple[bytes, str, str]],
    *,
    admin: bool,
) -> None:
    """Each tuple: (bytes, content_type, file_name). Storage keys use ``report_id``."""
    from app.db import insert_row, insert_row_admin, upload_bytes, upload_bytes_admin
    insert_fn = insert_row_admin if admin else insert_row
    upload_fn = upload_bytes_admin if admin else upload_bytes
    rid = str(report_id or "").strip()
    if not rid:
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    for i, tup in enumerate(files):
        data, ctype, fname = tup[0], tup[1], tup[2]
        if not data:
            continue
        raw_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", str(fname or "photo").strip())[:180] or f"photo_{i}.jpg"
        storage_path = f"supervisor_daily_reports/{rid}/{ts}_{i}_{raw_name}"
        upload_fn(storage_path, data, content_type=ctype or "application/octet-stream")
        insert_fn(
            "supervisor_daily_report_photos",
            {
                "report_id": rid,
                "storage_path": storage_path,
                "file_name": str(fname or Path(storage_path).name),
                "content_type": ctype or "application/octet-stream",
            },
        )


def submit_daily_report(report_id: str, *, admin: bool = False) -> None:
    """Mark report Submitted and log timeline event."""
    rid = str(report_id or "").strip()
    if not rid:
        raise ValueError("report_id required")
    _, update_fn, _ = _write_fn(admin=admin)
    now = datetime.now(timezone.utc).isoformat()
    update_fn(
        "supervisor_daily_reports",
        {"status": "Submitted", "submitted_at": now, "updated_at": now},
        {"id": rid},
    )
    fetch_row, _, _ = _fetch_fn(admin=admin)
    rows = fetch_row("supervisor_daily_reports", {"id": rid}, limit=1)
    if rows:
        r = rows[0]
        from app.services.job_timeline import EVENT_DAILY_REPORT, log_job_event
        log_job_event(
            job_id=str(r.get("job_id") or ""),
            event_type=EVENT_DAILY_REPORT,
            title="Daily report submitted",
            description=str(r.get("completed_today") or r.get("main_goal") or "")[:500],
            user_name=str(r.get("supervisor_name") or ""),
            related_table="supervisor_daily_reports",
            related_id=rid,
            admin=admin,
        )


def review_daily_report(report_id: str, *, reviewed_by: str | None = None, admin: bool = False) -> None:
    rid = str(report_id or "").strip()
    if not rid:
        raise ValueError("report_id required")
    _, update_fn, _ = _write_fn(admin=admin)
    now = datetime.now(timezone.utc).isoformat()
    patch: dict[str, Any] = {"status": "Reviewed", "reviewed_at": now, "updated_at": now}
    if reviewed_by:
        patch["reviewed_by"] = str(reviewed_by).strip()
    update_fn("supervisor_daily_reports", patch, {"id": rid})


def upsert_supervisor_daily_report(
    *,
    job_id: str,
    report_date: date,
    payload: dict[str, Any],
    crew_rows: list[dict[str, Any]],
    new_photo_files: list[tuple[bytes, str, str]],
    admin: bool,
) -> dict[str, Any]:
    """
    Insert or update header row, replace crew lines, append new photos.
    ``payload`` should not include id/job_id/report_date (those passed separately).
    ``new_photo_files`` entries are ``(bytes, content_type, file_name)``.
    """
    insert_fn, update_fn, _ = _write_fn(admin=admin)
    jid = str(job_id or "").strip()
    if not jid:
        raise ValueError("job_id required")
    ds = report_date.isoformat()[:10]
    existing = fetch_report_for_job_date(jid, report_date, admin=admin)
    body = {k: v for k, v in payload.items() if k not in {"id", "job_id", "report_date"}}
    body["job_id"] = jid
    body["report_date"] = ds
    if existing and existing.get("id"):
        rid = str(existing["id"])
        body.pop("created_by", None)
        update_fn("supervisor_daily_reports", body, {"id": rid})
        replace_crew_lines(rid, crew_rows, admin=admin)
        if new_photo_files:
            append_report_photos(rid, new_photo_files, admin=admin)
        out = dict(existing)
        out.update(body)
        out["id"] = rid
        return out
    row = insert_fn("supervisor_daily_reports", body)
    rid = str(row.get("id") or "").strip()
    if not rid:
        raise RuntimeError("insert supervisor_daily_reports returned no id")
    replace_crew_lines(rid, crew_rows, admin=admin)
    if new_photo_files:
        append_report_photos(rid, new_photo_files, admin=admin)
    return row


def fetch_all_reports_since(since: date, *, admin: bool, limit: int = 3000) -> list[dict[str, Any]]:
    """Reports with report_date >= since (for dashboard aggregates)."""
    s = since.isoformat()[:10]
    try:
        if admin:
            from app.db import get_admin_client

            q = (
                get_admin_client()
                .table("supervisor_daily_reports")
                .select("*")
                .gte("report_date", s)
                .order("report_date", desc=True)
                .limit(limit)
            )
            resp = q.execute()
            return list(resp.data or [])
        from app.db import get_client, run_user_supabase_operation

        def _run():
            q = (
                get_client()
                .table("supervisor_daily_reports")
                .select("*")
                .gte("report_date", s)
                .order("report_date", desc=True)
                .limit(limit)
            )
            return q.execute()

        resp = run_user_supabase_operation(
            "read supervisor_daily_reports",
            _run,
            friendly_on_failure=False,
        )
        return list(resp.data or [])
    except Exception as exc:
        _LOG.debug("fetch_all_reports_since: %s", exc)
        return []


def labor_hours_actual_by_job(
    time_entries: list[dict[str, Any]],
) -> dict[str, float]:
    out: dict[str, float] = {}
    for te in time_entries or []:
        if not isinstance(te, dict):
            continue
        jid = str(te.get("job_id") or "").strip()
        if not jid:
            continue
        try:
            h = float(te.get("hours") or 0)
        except (TypeError, ValueError):
            h = 0.0
        out[jid] = out.get(jid, 0.0) + max(0.0, h)
    return out


def labor_hours_actual_by_job_on_date(
    time_entries: list[dict[str, Any]],
    *,
    work_date: date,
) -> dict[str, float]:
    """Sum positive hours per job_id for a single calendar ``work_date`` (time_entries.work_date)."""
    want = work_date.isoformat()[:10]
    out: dict[str, float] = {}
    for te in time_entries or []:
        if not isinstance(te, dict):
            continue
        wd = str(te.get("work_date") or "")[:10]
        if wd != want:
            continue
        jid = str(te.get("job_id") or "").strip()
        if not jid:
            continue
        try:
            h = float(te.get("hours") or 0)
        except (TypeError, ValueError):
            h = 0.0
        out[jid] = out.get(jid, 0.0) + max(0.0, h)
    return out


def jobs_over_estimated_labor_hours(
    jobs: list[dict[str, Any]],
    estimates_by_id: dict[str, dict[str, Any]],
    hours_by_job: dict[str, float],
) -> list[tuple[str, str, float, float]]:
    """
    Returns list of (job_id, label, estimated_hours, actual_hours) where actual > estimated
    and estimated is not null and > 0.
    """
    over: list[tuple[str, str, float, float]] = []
    for j in jobs or []:
        if not isinstance(j, dict):
            continue
        jid = str(j.get("id") or "").strip()
        if not jid:
            continue
        eid = str(j.get("estimate_id") or "").strip()
        if not eid:
            continue
        est = estimates_by_id.get(eid)
        if not est:
            continue
        est_json = _parse_estimate_json(est.get("estimate_json"))
        bid_h = estimated_bid_labor_hours_from_estimate_json(est_json)
        if bid_h is None or bid_h <= 0:
            continue
        act = float(hours_by_job.get(jid, 0.0))
        if act > bid_h + 0.01:
            from app.services.job_service import job_row_select_label
            label = job_row_select_label(j)
            over.append((jid, label, bid_h, act))
    over.sort(key=lambda x: -(x[3] - x[2]))
    return over


def dashboard_daily_report_snapshot(
    *,
    today: date,
    jobs: list[dict[str, Any]],
    reports_today: list[dict[str, Any]],
    reports_recent: list[dict[str, Any]],
    hours_by_job: dict[str, float],
    estimates_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Pre-shaped counts for the main dashboard card row."""
    t_iso = today.isoformat()[:10]
    submitted_today = sum(
        1 for r in (reports_today or []) if isinstance(r, dict) and str(r.get("report_date") or "")[:10] == t_iso
    )
    active_jobs = [j for j in (jobs or []) if isinstance(j, dict) and job_status_needs_daily_report(j.get("status"))]
    reported_job_ids_today = {
        str(r.get("job_id") or "").strip()
        for r in (reports_today or [])
        if isinstance(r, dict) and str(r.get("report_date") or "")[:10] == t_iso
    }
    missing = 0
    missing_labels: list[str] = []
    missing_jobs: list[dict[str, str]] = []
    for j in active_jobs:
        jid = str(j.get("id") or "").strip()
        if jid and jid not in reported_job_ids_today:
            missing += 1
            if len(missing_labels) < 8:
                from app.services.job_service import job_row_select_label
                label = job_row_select_label(j)
                missing_labels.append(label)
                missing_jobs.append({"id": jid, "label": label})

    delay_jobs_recent: set[str] = set()
    for r in reports_recent or []:
        if not isinstance(r, dict):
            continue
        if report_has_any_delay(r):
            jid = str(r.get("job_id") or "").strip()
            if jid:
                delay_jobs_recent.add(jid)

    delay_pairs = collect_delay_reason_counts(list(reports_recent or []))
    over_list = jobs_over_estimated_labor_hours(jobs, estimates_by_id, hours_by_job)

    return {
        "submitted_today": submitted_today,
        "missing_reports": missing,
        "jobs_with_delays": len(delay_jobs_recent),
        "repeated_delay_reasons": delay_pairs[:6],
        "jobs_over_labor": over_list[:12],
        "missing_sample_labels": missing_labels,
        "missing_sample_jobs": missing_jobs,
    }
