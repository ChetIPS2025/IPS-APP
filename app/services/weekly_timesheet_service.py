"""Weekly job timesheet service — spec API over weekly_job_timesheet_service."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

try:
    from app.db import fetch_by_match_admin, insert_row_admin, update_rows_admin, upload_bytes_admin
    from app.services.job_weekly_timesheets import monday_of_week, week_bounds
    from app.services.weekly_job_timesheet_service import (
        TimesheetLine,
        WeeklyJobTimesheetData,
        build_timesheet_data,
        fetch_timesheet_by_job_week,
        list_timesheets_for_job,
        load_timesheet_data,
        save_timesheet,
        signed_url_for_timesheet,
    )
    from app.services.weekly_timesheet_export_service import (
        export_data_to_pdf,
        export_weekly_timesheet_to_excel,
        export_weekly_timesheet_to_pdf,
    )
except ImportError:
    from db import fetch_by_match_admin, insert_row_admin, update_rows_admin, upload_bytes_admin  # type: ignore
    from services.job_weekly_timesheets import monday_of_week, week_bounds  # type: ignore
    from services.weekly_job_timesheet_service import (  # type: ignore
        TimesheetLine,
        WeeklyJobTimesheetData,
        build_timesheet_data,
        fetch_timesheet_by_job_week,
        list_timesheets_for_job,
        load_timesheet_data,
        save_timesheet,
        signed_url_for_timesheet,
    )
    from services.weekly_timesheet_export_service import (  # type: ignore
        export_data_to_pdf,
        export_weekly_timesheet_to_excel,
        export_weekly_timesheet_to_pdf,
    )

_SHEET_TABLE = "weekly_job_timesheets"
_LOCKED = frozenset({"Approved", "Signed", "Voided"})


def timesheet_is_locked(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    status = str(row.get("status") or "")
    return status in _LOCKED and bool(row.get("locked_at") or status in {"Approved", "Signed"})


def get_weekly_timesheets_for_job(job_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    return list_timesheets_for_job(job_id, limit=limit)


def get_weekly_timesheet(timesheet_id: str) -> tuple[dict[str, Any] | None, WeeklyJobTimesheetData | None]:
    rows = fetch_by_match_admin(_SHEET_TABLE, {"id": timesheet_id}, limit=1)
    row = rows[0] if rows else None
    data = load_timesheet_data(timesheet_id) if row else None
    return row, data


def generate_weekly_timesheet_data(
    job_id: str,
    week_start: date,
    *,
    po_number: str = "",
    approved_by: str = "",
    work_performed: str = "",
) -> WeeklyJobTimesheetData:
    return build_timesheet_data(
        job_id,
        week_start,
        po_number=po_number,
        approved_by=approved_by,
        work_performed=work_performed,
    )


def create_weekly_timesheet(
    job_id: str,
    week_start: date,
    data: WeeklyJobTimesheetData,
    *,
    created_by: str | None = None,
) -> dict[str, Any]:
    data.job_id = job_id
    ws = monday_of_week(week_start)
    _, we = week_bounds(ws)
    data.week_start = ws.isoformat()
    data.week_end = we.isoformat()
    data.status = "Generated"
    return save_timesheet(data, created_by=created_by, lock=False, regenerate_exports=True)


def update_weekly_timesheet(
    timesheet_id: str,
    data: WeeklyJobTimesheetData,
    *,
    created_by: str | None = None,
    allow_locked: bool = False,
) -> dict[str, Any]:
    row, _ = get_weekly_timesheet(timesheet_id)
    if row and timesheet_is_locked(row) and not allow_locked:
        raise RuntimeError("Approved timesheets are locked. Void the timesheet or contact an admin.")
    existing = fetch_by_match_admin(_SHEET_TABLE, {"id": timesheet_id}, limit=1)
    if existing:
        data.job_id = str(existing[0].get("job_id") or data.job_id)
    return save_timesheet(data, created_by=created_by, lock=False, regenerate_exports=True)


def create_weekly_timesheet_lines(timesheet_id: str, lines: list[TimesheetLine]) -> None:
    data = load_timesheet_data(timesheet_id)
    if not data:
        raise ValueError("Timesheet not found.")
    labor = [ln for ln in lines if ln.line_type in {"labor", "equipment"}]
    materials = [ln for ln in lines if ln.line_type in {"material", "expense"}]
    data.labor_lines = labor or data.labor_lines
    data.material_lines = materials or data.material_lines
    update_weekly_timesheet(timesheet_id, data)


def generate_weekly_timesheet_excel(timesheet_id: str) -> bytes:
    return export_weekly_timesheet_to_excel(timesheet_id)


def generate_weekly_timesheet_pdf(timesheet_id: str) -> bytes:
    return export_weekly_timesheet_to_pdf(timesheet_id)


def generate_weekly_timesheet_pdf_from_data(data: WeeklyJobTimesheetData) -> bytes:
    return export_data_to_pdf(data)


def mark_timesheet_sent(timesheet_id: str) -> dict[str, Any]:
    update_rows_admin(
        _SHEET_TABLE,
        {"status": "Sent", "updated_at": datetime.now(timezone.utc).isoformat()},
        {"id": timesheet_id},
    )
    rows = fetch_by_match_admin(_SHEET_TABLE, {"id": timesheet_id}, limit=1)
    return rows[0] if rows else {"id": timesheet_id, "status": "Sent"}


def approve_timesheet(
    timesheet_id: str,
    approved_by: str,
    *,
    signature: str | None = None,
    approved_by_title: str = "",
    created_by: str | None = None,
) -> dict[str, Any]:
    data = load_timesheet_data(timesheet_id)
    if not data:
        raise ValueError("Timesheet not found.")
    data.approved_by = approved_by.strip()
    data.status = "Approved"
    if signature:
        data.signature_data = signature
    now = datetime.now(timezone.utc)
    data.signed_at = now.isoformat()
    row = save_timesheet(data, created_by=created_by, lock=True, regenerate_exports=True)
    extra = {
        "approved_by_name": approved_by.strip(),
        "approved_by_title": approved_by_title.strip(),
        "approved_at": now.isoformat(),
        "approved_by": approved_by.strip(),
    }
    update_rows_admin(_SHEET_TABLE, extra, {"id": timesheet_id})
    _register_timesheet_documents(timesheet_id)
    fresh = fetch_by_match_admin(_SHEET_TABLE, {"id": timesheet_id}, limit=1)
    return fresh[0] if fresh else row


def void_timesheet(timesheet_id: str) -> dict[str, Any]:
    update_rows_admin(
        _SHEET_TABLE,
        {"status": "Voided", "updated_at": datetime.now(timezone.utc).isoformat()},
        {"id": timesheet_id},
    )
    rows = fetch_by_match_admin(_SHEET_TABLE, {"id": timesheet_id}, limit=1)
    return rows[0] if rows else {"id": timesheet_id, "status": "Voided"}


def _register_timesheet_documents(timesheet_id: str) -> None:
    """Insert approved timesheet PDF/Excel into documents_hub for the job."""
    row, data = get_weekly_timesheet(timesheet_id)
    if not row or not data:
        return
    job_id = str(row.get("job_id") or "")
    if not job_id:
        return
    ws = str(row.get("week_start") or "")[:10]
    job_num = str(row.get("job_number") or "job")
    uploaded_by = "Weekly Timesheet"
    for path_key, url_key, doc_type, suffix in (
        ("pdf_path", "pdf_url", "Weekly Timesheet PDF", "pdf"),
        ("excel_path", "excel_url", "Weekly Timesheet Excel", "xlsx"),
    ):
        storage = str(row.get(path_key) or row.get("pdf_file_url" if suffix == "pdf" else "") or "").strip()
        if not storage:
            continue
        file_name = f"Weekly_Timesheet_{job_num}_{ws}.{suffix}"
        payload = {
            "file_name": file_name,
            "doc_type": doc_type,
            "linked_module": "jobs",
            "linked_ref": f"weekly_timesheet:{timesheet_id}",
            "linked_record_id": job_id,
            "uploaded_by": uploaded_by,
            "storage_path": storage,
            "notes": f"Week {ws} — {row.get('status') or 'Approved'}",
        }
        existing = fetch_by_match_admin(
            "documents_hub",
            {"linked_ref": payload["linked_ref"], "doc_type": doc_type},
            limit=1,
        )
        if existing:
            update_rows_admin("documents_hub", payload, {"id": existing[0]["id"]})
        else:
            try:
                insert_row_admin("documents_hub", payload)
            except Exception:
                pass
