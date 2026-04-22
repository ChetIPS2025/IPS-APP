from __future__ import annotations

import base64
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from app.db import create_signed_url, fetch_by_match_admin, fetch_table_admin, insert_row_admin, update_rows_admin, upload_bytes_admin
    from app.services.job_service import job_row_select_label
except ImportError:
    from db import (  # type: ignore
        create_signed_url,
        fetch_by_match_admin,
        fetch_table_admin,
        insert_row_admin,
        update_rows_admin,
        upload_bytes_admin,
    )
    from services.job_service import job_row_select_label  # type: ignore


DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_bounds(week_start: date) -> tuple[date, date]:
    return week_start, week_start + timedelta(days=6)


def _parse_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _sig_png_bytes(signature_data: str) -> bytes | None:
    s = str(signature_data or "").strip()
    if not s:
        return None
    if s.startswith("data:image"):
        try:
            b64 = s.split(",", 1)[1]
            return base64.b64decode(b64)
        except Exception:
            return None
    try:
        return base64.b64decode(s)
    except Exception:
        return None


@dataclass
class TimesheetPdfResult:
    storage_path: str
    signed_url: str


def build_timesheet_pdf_bytes(
    *,
    job: dict,
    customer: dict | None,
    location: dict | None,
    week_start: date,
    time_entries: list[dict],
    signer_name: str = "",
    signer_email: str = "",
    signer_title: str = "",
    signature_data: str = "",
    work_summary: str = "",
    signed_at_utc: datetime | None = None,
) -> bytes:
    """
    Generate a customer-facing weekly timesheet PDF from `time_entries` rows.
    Expects time_entries columns: employee_id, work_date, hours, notes.
    """
    styles = getSampleStyleSheet()
    doc_buf = BytesIO()
    doc = SimpleDocTemplate(doc_buf, pagesize=letter, leftMargin=0.6 * inch, rightMargin=0.6 * inch)

    ws, we = week_bounds(week_start)
    job_label = job_row_select_label(job) if job else ""
    cust_name = str((customer or {}).get("customer_name") or "").strip()
    loc_label = str((location or {}).get("location_name") or (location or {}).get("address") or "").strip()

    story: list[Any] = []
    story.append(Paragraph("Weekly Customer Timesheet", styles["Title"]))
    story.append(Spacer(1, 0.12 * inch))

    meta = [
        ["Job", job_label or str(job.get("job_name") or "")],
        ["Customer", cust_name or "—"],
        ["Location", loc_label or "—"],
        ["Week", f"{ws.isoformat()} to {we.isoformat()}"],
    ]
    tmeta = Table(meta, colWidths=[1.0 * inch, 5.6 * inch])
    tmeta.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(tmeta)
    story.append(Spacer(1, 0.18 * inch))

    # Load employees for labels (best-effort).
    emp_name_by_id: dict[str, str] = {}
    try:
        emps = fetch_table_admin("employees", columns="id,name", limit=5000, order_by="name")
        emp_name_by_id = {str(e.get("id")): str(e.get("name") or "").strip() for e in emps if e.get("id")}
    except Exception:
        emp_name_by_id = {}

    buckets: dict[str, list[float]] = defaultdict(lambda: [0.0] * 7)
    notes: list[str] = []
    for r in time_entries:
        wd = _parse_date(r.get("work_date"))
        if wd is None or wd < ws or wd > we:
            continue
        di = (wd - ws).days
        if di < 0 or di > 6:
            continue
        eid = str(r.get("employee_id") or "").strip()
        nm = emp_name_by_id.get(eid) or str(r.get("employee_name") or "").strip() or "Unknown"
        try:
            h = float(r.get("hours") or 0)
        except (TypeError, ValueError):
            h = 0.0
        buckets[nm][di] += h
        n = str(r.get("notes") or "").strip()
        if n:
            notes.append(n)

    grid = [["Employee"] + DAY_LABELS + ["Total"]]
    total_all = 0.0
    for emp, hrs in sorted(buckets.items(), key=lambda x: x[0].lower()):
        row_total = round(sum(hrs), 2)
        total_all += row_total
        grid.append([emp] + [f"{round(x, 2):g}" if x else "" for x in hrs] + [f"{row_total:g}"])

    if len(grid) == 1:
        grid.append(["—"] + [""] * 7 + ["0"])

    grid.append(["", "", "", "", "", "", "TOTAL", "", f"{round(total_all, 2):g}"])

    t = Table(grid, repeatRows=1, colWidths=[2.1 * inch] + [0.55 * inch] * 7 + [0.75 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("BACKGROUND", (0, 1), (-1, -2), colors.whitesmoke),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.18 * inch))

    if work_summary.strip():
        story.append(Paragraph("<b>Work summary</b>", styles["Heading4"]))
        story.append(Paragraph(work_summary.strip().replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 0.12 * inch))

    if notes:
        story.append(Paragraph("<b>Notes from time entries</b>", styles["Heading4"]))
        story.append(Paragraph(" · ".join(notes[:12]).replace("\n", " "), styles["BodyText"]))
        story.append(Spacer(1, 0.12 * inch))

    story.append(Paragraph("<b>Customer signature</b>", styles["Heading4"]))
    if signer_name.strip():
        title_part = f" · {signer_title.strip()}" if signer_title.strip() else ""
        ts_part = ""
        if signed_at_utc is not None:
            try:
                dt = signed_at_utc.astimezone(timezone.utc)
            except Exception:
                dt = signed_at_utc
            ts_part = f" · {dt.strftime('%Y-%m-%d %H:%M UTC')}"
        story.append(
            Paragraph(
                f"Signed by: {signer_name.strip()}{title_part} ({signer_email.strip()}){ts_part}",
                styles["BodyText"],
            )
        )
    else:
        story.append(Paragraph("Name: ____________________________   Email: ____________________________", styles["BodyText"]))

    sig_bytes = _sig_png_bytes(signature_data)
    if sig_bytes:
        try:
            img = RLImage(BytesIO(sig_bytes), width=2.6 * inch, height=0.9 * inch)
            story.append(Spacer(1, 0.05 * inch))
            story.append(img)
        except Exception:
            pass

    doc.build(story)
    return doc_buf.getvalue()


def upsert_job_weekly_timesheet(
    *,
    job_id: str,
    week_start: date,
    unsigned_pdf_path: str,
    customer_id: str | None,
    customer_location_id: str | None,
    customer_contact_id: str | None,
) -> dict:
    ws, we = week_bounds(week_start)
    existing = fetch_by_match_admin("job_weekly_timesheets", {"job_id": job_id, "week_start": ws.isoformat()}, limit=1)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
    payload = {
        "job_id": job_id,
        "week_start": ws.isoformat(),
        "week_end": we.isoformat(),
        "customer_id": customer_id,
        "customer_location_id": customer_location_id,
        "customer_contact_id": customer_contact_id,
        "unsigned_pdf_url": unsigned_pdf_path,
        "status": "Draft",
        # Column exists after sql/032; safe to ignore if absent.
        "sign_token_expires_at": expires_at,
    }
    if existing:
        rid = existing[0].get("id")
        # Preserve existing expiry if present.
        if str(existing[0].get("sign_token_expires_at") or "").strip():
            payload.pop("sign_token_expires_at", None)
        update_rows_admin("job_weekly_timesheets", payload, {"id": rid})
        fresh = fetch_by_match_admin("job_weekly_timesheets", {"id": rid}, limit=1)
        return fresh[0] if fresh else existing[0]
    return insert_row_admin("job_weekly_timesheets", payload)


def generate_unsigned_timesheet_for_job_week(
    *,
    job_id: str,
    week_start: date,
    work_summary: str = "",
) -> dict:
    job_rows = fetch_by_match_admin("jobs", {"id": job_id}, limit=1)
    job = job_rows[0] if job_rows else {"id": job_id}
    cust = None
    loc = None
    cid = str(job.get("customer_id") or "").strip() or None
    clid = str(job.get("customer_location_id") or "").strip() or None
    ccid = str(job.get("customer_contact_id") or "").strip() or None
    if cid:
        cr = fetch_by_match_admin("customers", {"id": cid}, limit=1)
        cust = cr[0] if cr else None
    if clid:
        lr = fetch_by_match_admin("customer_locations", {"id": clid}, limit=1)
        loc = lr[0] if lr else None

    ws, we = week_bounds(week_start)
    time_rows = fetch_table_admin("time_entries", limit=15000)
    # Filter in Python to avoid relying on query operators in helpers.
    time_rows = [
        r
        for r in time_rows
        if str(r.get("job_id") or "") == str(job_id)
        and (_parse_date(r.get("work_date")) is not None)
        and ws <= _parse_date(r.get("work_date")) <= we  # type: ignore[operator]
    ]
    if not time_rows:
        raise RuntimeError("No time entries found for this job/week.")

    pdf_bytes = build_timesheet_pdf_bytes(
        job=job,
        customer=cust,
        location=loc,
        week_start=ws,
        time_entries=time_rows,
        work_summary=work_summary,
    )
    job_num = str(job.get("job_number") or job.get("job_id") or "").strip() or str(job_id)[:8]
    storage_path = f"job_timesheets/{job_num}/{ws.isoformat()}/unsigned.pdf"
    upload_bytes_admin(storage_path, pdf_bytes, content_type="application/pdf")

    row = upsert_job_weekly_timesheet(
        job_id=str(job_id),
        week_start=ws,
        unsigned_pdf_path=storage_path,
        customer_id=cid,
        customer_location_id=clid,
        customer_contact_id=ccid,
    )
    return row


def signed_url_for_storage_path(path: str) -> str:
    p = str(path or "").strip()
    if not p:
        return ""
    return create_signed_url(p, expires_in=3600)

