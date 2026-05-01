"""Supervisor daily reports for job detail and dashboard summaries."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

try:
    from app.db import (
        create_signed_url,
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
except ImportError:
    from db import (  # type: ignore
        create_signed_url,
        delete_rows_admin,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )


REPORTS_TABLE = "job_daily_reports"
CREW_TABLE = "job_daily_report_crew"
PHOTOS_TABLE = "job_daily_report_photos"

DELAY_REASONS: tuple[str, ...] = (
    "Waiting on material",
    "Waiting on tools",
    "Waiting on direction",
    "Too many people on one task",
    "Rework",
    "Equipment issue",
    "Customer delay",
    "Safety delay",
    "Other",
)
DAILY_REPORT_DELAY_REASONS = DELAY_REASONS
DAILY_DELAY_REASONS = DELAY_REASONS

ACTIVE_JOB_STATUSES: frozenset[str] = frozenset({"awarded", "scheduled", "in progress", "active"})


def today_iso() -> str:
    return date.today().isoformat()


def parse_report_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    s = str(value or "").strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def active_job_rows(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for job in jobs or []:
        st = " ".join(str((job or {}).get("status") or "").strip().split()).casefold()
        if st in ACTIVE_JOB_STATUSES:
            out.append(job)
    return out


def fetch_reports_for_job(job_id: str, *, limit: int = 30) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid:
        return []
    try:
        rows = fetch_by_match_admin(REPORTS_TABLE, {"job_id": jid}, limit=limit)
    except Exception:
        return []
    rows = list(rows or [])
    rows.sort(key=lambda r: str(r.get("report_date") or ""), reverse=True)
    return rows


def fetch_daily_reports_for_job(job_id: str, *, limit: int = 30) -> list[dict[str, Any]]:
    rows = fetch_reports_for_job(job_id, limit=limit)
    for row in rows:
        rid = str(row.get("id") or "").strip()
        row["crew"] = fetch_crew_for_report(rid)
        photos = fetch_photos_for_report(rid)
        for ph in photos:
            if "storage_path" not in ph:
                ph["storage_path"] = ph.get("file_path")
        row["photos"] = photos
    return rows


def fetch_daily_report_tables() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        reports = fetch_table_admin(REPORTS_TABLE, limit=10000, order_by="report_date")
    except Exception:
        reports = []
    try:
        crew = fetch_table_admin(CREW_TABLE, limit=25000, order_by="created_at")
    except Exception:
        crew = []
    return list(reports or []), list(crew or [])


def fetch_crew_for_report(report_id: str) -> list[dict[str, Any]]:
    rid = str(report_id or "").strip()
    if not rid:
        return []
    try:
        rows = fetch_by_match_admin(CREW_TABLE, {"report_id": rid}, limit=200)
    except Exception:
        return []
    return list(rows or [])


def fetch_photos_for_report(report_id: str) -> list[dict[str, Any]]:
    rid = str(report_id or "").strip()
    if not rid:
        return []
    try:
        rows = fetch_by_match_admin(PHOTOS_TABLE, {"report_id": rid}, limit=100)
    except Exception:
        return []
    out = list(rows or [])
    for row in out:
        if "storage_path" not in row:
            row["storage_path"] = row.get("file_path")
        if "file_path" not in row:
            row["file_path"] = row.get("storage_path")
    return out


def signed_report_photo_url(path: str) -> str:
    p = str(path or "").strip()
    if not p:
        return ""
    try:
        return create_signed_url(p, expires_in=3600) or ""
    except Exception:
        return ""


daily_report_photo_signed_url = signed_report_photo_url


def _float_or_zero(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def save_daily_report(
    *,
    job_id: str,
    payload: dict[str, Any] | None = None,
    crew_rows: list[dict[str, Any]] | None = None,
    photo_uploads: list[Any] | None = None,
    report_date: Any = None,
    supervisor: str = "",
    crew_size: int = 0,
    main_goal: str = "",
    on_track: bool | None = None,
    on_track_reason: str = "",
    completed_today: str = "",
    not_completed_reason: str = "",
    delay_reasons: list[str] | None = None,
    other_delay_reason: str = "",
    tomorrow_plan: str = "",
    crew_lines: list[dict[str, Any]] | None = None,
    uploads: list[Any] | None = None,
) -> dict[str, Any]:
    jid = str(job_id or "").strip()
    if not jid:
        raise RuntimeError("Job id is required.")
    if payload is None:
        report_date_s = report_date.isoformat() if hasattr(report_date, "isoformat") else str(report_date or "").strip()
        payload = {
            "report_date": report_date_s[:10],
            "supervisor_name": str(supervisor or "").strip(),
            "crew_size": int(crew_size or 0),
            "main_goal": str(main_goal or "").strip(),
            "midday_on_track": bool(on_track) if on_track is not None else True,
            "midday_reason": str(on_track_reason or "").strip(),
            "completed_today": str(completed_today or "").strip(),
            "not_completed": str(not_completed_reason or "").strip(),
            "delay_reasons": list(delay_reasons or []),
            "delay_other": str(other_delay_reason or "").strip(),
            "tomorrow_plan": str(tomorrow_plan or "").strip(),
        }
    report_date_s = str(payload.get("report_date") or "").strip()
    if not report_date_s:
        raise RuntimeError("Report date is required.")
    crew_rows = list(crew_rows if crew_rows is not None else (crew_lines or []))
    photo_uploads = list(photo_uploads if photo_uploads is not None else (uploads or []))

    payload = dict(payload)
    payload["job_id"] = jid
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    existing = []
    try:
        existing = fetch_by_match_admin(REPORTS_TABLE, {"job_id": jid, "report_date": report_date_s}, limit=1)
    except Exception:
        existing = []

    if existing:
        report_id = str(existing[0].get("id") or "").strip()
        update_rows_admin(REPORTS_TABLE, payload, {"id": report_id})
        row = dict(existing[0])
        row.update(payload)
        delete_rows_admin(CREW_TABLE, {"report_id": report_id})
    else:
        row = insert_row_admin(REPORTS_TABLE, payload)
        report_id = str(row.get("id") or "").strip()

    for idx, crew in enumerate(crew_rows):
        name = str(crew.get("employee_name") or "").strip()
        task = str(crew.get("task") or "").strip()
        notes = str(crew.get("notes") or "").strip()
        hours = _float_or_zero(crew.get("hours"))
        employee_id = str(crew.get("employee_id") or "").strip() or None
        if not any((name, task, notes)) and hours <= 0:
            continue
        insert_row_admin(
            CREW_TABLE,
            {
                "report_id": report_id,
                "job_id": jid,
                "report_date": report_date_s,
                "employee_id": employee_id,
                "employee_name": name,
                "task": task,
                "hours": hours,
                "notes": notes,
                "sort_order": idx,
            },
        )

    for upload in photo_uploads or []:
        data = upload.getvalue()
        if not data:
            continue
        file_name = str(getattr(upload, "name", "") or "photo").strip()
        content_type = str(getattr(upload, "type", "") or "application/octet-stream").strip()
        ext = "jpg"
        if "." in file_name:
            ext = file_name.rsplit(".", 1)[-1].lower()[:8] or ext
        elif "png" in content_type.lower():
            ext = "png"
        storage_path = f"job_daily_reports/{jid}/{report_date_s}/{uuid4().hex}.{ext}"
        upload_bytes_admin(storage_path, data, content_type=content_type)
        insert_row_admin(
            PHOTOS_TABLE,
            {
                "report_id": report_id,
                "job_id": jid,
                "report_date": report_date_s,
                "file_name": file_name,
                "storage_path": storage_path,
                "content_type": content_type,
            },
        )

    row["id"] = report_id
    return row


create_or_update_daily_report = save_daily_report


def upload_daily_report_photo(*, job_id: str, report_id: str, uploaded: Any) -> str | None:
    data = uploaded.getvalue() if uploaded is not None else b""
    if not data:
        return None
    file_name = str(getattr(uploaded, "name", "") or "photo").strip()
    content_type = str(getattr(uploaded, "type", "") or "application/octet-stream").strip()
    ext = file_name.rsplit(".", 1)[-1].lower()[:8] if "." in file_name else "jpg"
    storage_path = f"job_daily_reports/{job_id}/{report_id}/{uuid4().hex}.{ext}"
    upload_bytes_admin(storage_path, data, content_type=content_type)
    insert_row_admin(
        PHOTOS_TABLE,
        {
            "report_id": str(report_id),
            "job_id": str(job_id),
            "file_name": file_name,
            "storage_path": storage_path,
            "content_type": content_type,
        },
    )
    return storage_path


def estimated_labor_by_job(estimates: list[dict[str, Any]]) -> dict[str, float]:
    out: dict[str, float] = {}
    for est in estimates or []:
        jid = str((est or {}).get("job_id") or "").strip()
        if not jid:
            continue
        hours = 0.0
        for key in ("estimated_labor_hours", "labor_hours", "total_labor_hours", "estimated_hours"):
            hours = max(hours, _float_or_zero(est.get(key)))
        raw = est.get("estimate_json")
        if isinstance(raw, str) and raw.strip():
            try:
                raw = json.loads(raw)
            except Exception:
                raw = {}
        if isinstance(raw, dict):
            for line in raw.get("labor") or []:
                if not isinstance(line, dict):
                    continue
                headcount = _float_or_zero(line.get("headcount") or line.get("qty") or 1)
                st_hours = _float_or_zero(line.get("st_hours_per_day") or line.get("hours_per_day") or line.get("hours"))
                ot_hours = _float_or_zero(line.get("ot_hours_per_day"))
                days = _float_or_zero(line.get("days") or 1)
                hours += headcount * (st_hours + ot_hours) * days
        out[jid] = max(out.get(jid, 0.0), hours)
    return out


def actual_labor_hours_by_job(time_entries: list[dict[str, Any]], crew_rows: list[dict[str, Any]]) -> dict[str, float]:
    out: defaultdict[str, float] = defaultdict(float)
    for row in time_entries or []:
        jid = str((row or {}).get("job_id") or "").strip()
        if jid:
            out[jid] += _float_or_zero(row.get("hours"))
    for row in crew_rows or []:
        jid = str((row or {}).get("job_id") or "").strip()
        if jid:
            out[jid] += _float_or_zero(row.get("hours"))
    return dict(out)


def build_dashboard_summary(
    *,
    jobs: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    crew_rows: list[dict[str, Any]],
    estimates: list[dict[str, Any]],
    time_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    today = today_iso()
    active_jobs = active_job_rows(jobs)
    active_ids = {str(j.get("id") or "").strip() for j in active_jobs if str(j.get("id") or "").strip()}
    reports_today = [r for r in reports if str(r.get("report_date") or "")[:10] == today]
    today_job_ids = {str(r.get("job_id") or "").strip() for r in reports_today if str(r.get("job_id") or "").strip()}
    delayed_today = [
        r
        for r in reports_today
        if (r.get("delay_reasons") or [])
        or (str(r.get("midday_on_track") or "").strip().lower() == "false")
        or (r.get("midday_on_track") is False)
    ]

    reason_counter: Counter[str] = Counter()
    for r in reports:
        vals = r.get("delay_reasons") or []
        if isinstance(vals, str):
            vals = [v.strip() for v in vals.strip("{}").split(",") if v.strip()]
        for reason in vals:
            if str(reason or "").strip():
                reason_counter[str(reason).strip()] += 1

    estimated = estimated_labor_by_job(estimates)
    actual = actual_labor_hours_by_job(time_entries, crew_rows)
    over_labor = [
        jid
        for jid, est_hours in estimated.items()
        if est_hours > 0 and actual.get(jid, 0.0) > est_hours
    ]

    return {
        "reports_submitted_today": len(reports_today),
        "missing_reports": len(active_ids - today_job_ids),
        "jobs_with_delays": len({str(r.get("job_id") or "").strip() for r in delayed_today if str(r.get("job_id") or "").strip()}),
        "repeated_delay_reasons": sum(1 for _reason, count in reason_counter.items() if count >= 2),
        "jobs_over_estimated_labor_hours": len(over_labor),
        "top_delay_reasons": reason_counter.most_common(5),
    }
