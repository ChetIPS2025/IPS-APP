from __future__ import annotations

import html
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

try:
    from app.config import settings
except ImportError:
    from config import settings  # type: ignore

_LOG = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _norm_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        vals = [str(x or "").strip() for x in raw]
    elif isinstance(raw, str):
        vals = [p.strip() for p in re.split(r"[,\n;]+", raw) if p.strip()]
    else:
        vals = [str(raw).strip()]

    out: list[str] = []
    seen: set[str] = set()
    for v in vals:
        if not v:
            continue
        vl = v.lower()
        if vl in seen:
            continue
        seen.add(vl)
        out.append(v)
    return out


def _valid_emails(emails: list[str]) -> list[str]:
    return [e for e in (str(x or "").strip() for x in emails) if e and _EMAIL_RE.match(e)]


def _escape(v: Any) -> str:
    return html.escape(str(v or "").strip())


def _bool(v: Any, default: bool = False) -> bool:
    if v is None:
        return default
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _table_exists_admin(table_name: str) -> bool:
    try:
        from app.db import fetch_table_admin
    except ImportError:
        from db import fetch_table_admin  # type: ignore
    try:
        fetch_table_admin(table_name, columns="id", limit=1, order_by=None)
        return True
    except Exception:
        return False


def upsert_job_email_settings(
    job_id: str,
    *,
    customer_recipients: Any,
    internal_recipients: Any,
    cc_recipients: Any,
    enable_daily: bool,
    enable_weekly_friday: bool,
    enable_safety: bool,
    enable_budget_po_alerts: bool,
    is_active: bool,
    notes: str,
) -> None:
    jid = str(job_id or "").strip()
    if not jid:
        raise ValueError("job_id required")
    try:
        from app.db import fetch_by_match_admin
    except ImportError:
        from db import fetch_by_match_admin  # type: ignore
    try:
        from app.services.repository import insert_row_admin, update_row_admin
    except ImportError:
        from services.repository import insert_row_admin, update_row_admin  # type: ignore

    existing = None
    try:
        rows = fetch_by_match_admin("job_email_settings", {"job_id": jid}, limit=1)
        existing = rows[0] if rows else None
    except Exception:
        existing = None

    payload = {
        "job_id": jid,
        "customer_recipients": _valid_emails(_norm_list(customer_recipients)),
        "internal_recipients": _valid_emails(_norm_list(internal_recipients)),
        "cc_recipients": _valid_emails(_norm_list(cc_recipients)),
        "enable_daily_update_emails": bool(enable_daily),
        "enable_weekly_friday_update_emails": bool(enable_weekly_friday),
        "enable_safety_item_update_emails": bool(enable_safety),
        "enable_budget_po_alerts": bool(enable_budget_po_alerts),
        "is_active": bool(is_active),
        "notes": str(notes or "").strip(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if existing and existing.get("id"):
        update_row_admin("job_email_settings", payload, {"id": existing["id"]})
    else:
        insert_row_admin("job_email_settings", payload)


def fetch_job_email_settings_row(job_id: str, *, admin: bool) -> dict[str, Any] | None:
    jid = str(job_id or "").strip()
    if not jid:
        return None
    try:
        from app.db import fetch_by_match, fetch_by_match_admin
    except ImportError:
        from db import fetch_by_match, fetch_by_match_admin  # type: ignore
    fn = fetch_by_match_admin if admin else fetch_by_match
    try:
        rows = fn("job_email_settings", {"job_id": jid}, limit=1)
    except Exception:
        return None
    return rows[0] if rows else None


def _log_email_notification(
    *,
    notification_type: str,
    job_id: str | None,
    to_emails: list[str],
    cc_emails: list[str],
    bcc_emails: list[str],
    subject: str,
    text_body: str,
    html_body: str,
    status: str,
    provider: str,
    provider_message_id: str = "",
    error_message: str = "",
    meta: dict[str, Any] | None = None,
    sent: bool = False,
) -> None:
    try:
        from app.db import insert_row_admin
    except ImportError:
        from db import insert_row_admin  # type: ignore
    insert_row_admin(
        "email_notifications",
        {
            "notification_type": str(notification_type or "").strip(),
            "job_id": str(job_id).strip() if job_id else None,
            "to_emails": list(to_emails or []),
            "cc_emails": list(cc_emails or []),
            "bcc_emails": list(bcc_emails or []),
            "subject": str(subject or "").strip(),
            "text_body": str(text_body or ""),
            "html_body": str(html_body or ""),
            "meta": meta or {},
            "status": str(status or "pending"),
            "provider": str(provider or "").strip(),
            "provider_message_id": str(provider_message_id or "").strip(),
            "error_message": str(error_message or "").strip(),
            "sent_at": datetime.now(timezone.utc).isoformat() if sent else None,
        },
    )


def _send_email(
    *,
    to_emails: list[str],
    cc_emails: list[str],
    bcc_emails: list[str],
    subject: str,
    text_body: str,
    html_body: str,
    notification_type: str,
    job_id: str | None,
    meta: dict[str, Any] | None = None,
) -> None:
    provider = (settings.email_provider or "resend").strip().lower()
    if not (settings.email_from or "").strip():
        raise RuntimeError("EMAIL_FROM is required.")
    to_ok = _valid_emails(_norm_list(to_emails))
    cc_ok = _valid_emails(_norm_list(cc_emails))
    bcc_ok = _valid_emails(_norm_list(bcc_emails))
    if not to_ok:
        _log_email_notification(
            notification_type=notification_type,
            job_id=job_id,
            to_emails=[],
            cc_emails=cc_ok,
            bcc_emails=bcc_ok,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            status="skipped",
            provider=provider,
            error_message="No valid recipients.",
            meta=meta,
            sent=False,
        )
        return

    try:
        if provider == "resend":
            from app.services.email_provider_resend import send_via_resend

            mid = send_via_resend(
                api_key=settings.email_api_key,
                from_email=settings.email_from.strip(),
                reply_to=(settings.email_reply_to.strip() or None),
                to_emails=to_ok,
                cc_emails=cc_ok or None,
                bcc_emails=bcc_ok or None,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                tags=[{"name": "type", "value": notification_type}],
            )
        else:
            raise RuntimeError(f"Unsupported EMAIL_PROVIDER={provider!r}. Use 'resend'.")
    except Exception as exc:
        _log_email_notification(
            notification_type=notification_type,
            job_id=job_id,
            to_emails=to_ok,
            cc_emails=cc_ok,
            bcc_emails=bcc_ok,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            status="failed",
            provider=provider,
            error_message=str(exc),
            meta=meta,
            sent=False,
        )
        raise
    else:
        _log_email_notification(
            notification_type=notification_type,
            job_id=job_id,
            to_emails=to_ok,
            cc_emails=cc_ok,
            bcc_emails=bcc_ok,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            status="sent",
            provider=provider,
            provider_message_id=mid,
            error_message="",
            meta=meta,
            sent=True,
        )


def _delay_labels(report: dict[str, Any]) -> list[str]:
    try:
        from app.services.supervisor_daily_reports import delay_labels_map
    except ImportError:
        from services.supervisor_daily_reports import delay_labels_map  # type: ignore
    labels = delay_labels_map()
    out: list[str] = []
    for k, lbl in labels.items():
        if bool(report.get(k)):
            out.append(lbl)
    other_notes = str(report.get("delay_other_notes") or "").strip()
    if other_notes and "Other" not in out:
        out.append("Other")
    return out


def _daily_bodies(
    *,
    job: dict[str, Any],
    report: dict[str, Any],
    crew_lines: list[dict[str, Any]],
    photo_urls: list[str],
) -> tuple[str, str]:
    rd = str(report.get("report_date") or "")[:10] or "—"
    job_name = str(job.get("job_name") or "").strip() or "—"
    supervisor = str(report.get("supervisor_name") or "").strip() or "—"
    crew_size = str(report.get("crew_size") or "").strip() or "—"
    completed = str(report.get("completed_today") or "").strip() or "—"
    not_done_why = str(report.get("not_completed_reason") or "").strip()
    tomorrow = str(report.get("tomorrows_plan") or "").strip() or "—"
    midday_ok = "Yes" if bool(report.get("midday_on_track", True)) else "No"
    midday_reason = str(report.get("midday_reason") or "").strip()
    delays = ", ".join(_delay_labels(report)) or "—"

    crew_txt = ""
    crew_html = ""
    if crew_lines:
        lines_txt: list[str] = []
        lines_html: list[str] = []
        for cl in crew_lines[:20]:
            nm = str(cl.get("employee_name") or "").strip()
            tk = str(cl.get("task") or "").strip()
            hrs = str(cl.get("hours") or "").strip()
            nt = str(cl.get("notes") or "").strip()
            if not (nm or tk or hrs or nt):
                continue
            row = " — ".join([p for p in (nm, tk, (hrs + " hrs" if hrs else ""), nt) if p])
            lines_txt.append(f"- {row}")
            lines_html.append(f"<li>{_escape(row)}</li>")
        if lines_txt:
            crew_txt = "\n\nCrew assignments:\n" + "\n".join(lines_txt)
            crew_html = "<h4>Crew assignments</h4><ul>" + "".join(lines_html) + "</ul>"

    photos_txt = ""
    photos_html = ""
    if photo_urls:
        photos_txt = "\n\nPhotos:\n" + "\n".join(f"- {u}" for u in photo_urls[:10])
        photos_html = "<h4>Photos</h4><ul>" + "".join(
            f"<li><a href='{_escape(u)}' target='_blank' rel='noreferrer noopener'>Photo</a></li>"
            for u in photo_urls[:10]
        ) + "</ul>"

    text = (
        f"Job: {job_name}\n"
        f"Date: {rd}\n"
        f"Supervisor: {supervisor}\n"
        f"Crew size: {crew_size}\n"
        f"Midday on track: {midday_ok}\n"
        + (f"Midday reason: {midday_reason}\n" if midday_reason and midday_ok == "No" else "")
        + f"\nCompleted today:\n{completed}\n"
        + (f"\nNot completed reason:\n{not_done_why}\n" if not_done_why else "")
        + f"\nDelays/inefficiencies: {delays}\n"
        + f"\nTomorrow’s plan:\n{tomorrow}\n"
        + crew_txt
        + photos_txt
    )

    html_body = (
        "<div style='font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial'>"
        "<h3>Daily job update</h3>"
        f"<p><b>Job:</b> {_escape(job_name)}<br/>"
        f"<b>Date:</b> {_escape(rd)}<br/>"
        f"<b>Supervisor:</b> {_escape(supervisor)}<br/>"
        f"<b>Crew size:</b> {_escape(crew_size)}<br/>"
        f"<b>Midday on track:</b> {_escape(midday_ok)}"
        + (f"<br/><b>Reason:</b> {_escape(midday_reason)}" if midday_reason and midday_ok == "No" else "")
        + "</p>"
        f"<h4>Completed today</h4><div style='white-space:pre-wrap'>{_escape(completed)}</div>"
        + (
            f"<h4>Not completed reason</h4><div style='white-space:pre-wrap'>{_escape(not_done_why)}</div>"
            if not_done_why
            else ""
        )
        + f"<h4>Delays / inefficiencies</h4><p>{_escape(delays)}</p>"
        + f"<h4>Tomorrow’s plan</h4><div style='white-space:pre-wrap'>{_escape(tomorrow)}</div>"
        + crew_html
        + photos_html
        + "</div>"
    )
    return text, html_body


def run_daily_supervisor_report_emails(
    *,
    target_date: date | None = None,
    send_missing_reminders: bool = True,
) -> dict[str, int]:
    """
    Sends:
    - Daily supervisor report summaries (customer_recipients first; fallback internal_recipients)
    - Missing daily report reminders (internal_recipients) when enabled and missing
    """
    d = target_date or date.today()
    if not _table_exists_admin("job_email_settings") or not _table_exists_admin("supervisor_daily_reports"):
        return {"sent": 0, "skipped": 0, "failed": 0}
    try:
        from app.db import create_signed_url, fetch_by_match_admin, fetch_table_admin, get_admin_client
    except ImportError:
        from db import create_signed_url, fetch_by_match_admin, fetch_table_admin, get_admin_client  # type: ignore

    jobs = list(fetch_table_admin("jobs", limit=8000, order_by="job_number") or [])
    settings_rows = list(fetch_table_admin("job_email_settings", limit=10000, order_by=None) or [])
    set_by_job = {str(r.get("job_id") or "").strip(): r for r in settings_rows if isinstance(r, dict)}

    ds = d.isoformat()[:10]
    reports = (
        get_admin_client()
        .table("supervisor_daily_reports")
        .select("*")
        .eq("report_date", ds)
        .limit(10000)
        .execute()
        .data
        or []
    )
    rep_by_job = {str(r.get("job_id") or "").strip(): r for r in reports if isinstance(r, dict)}

    sent = skipped = failed = 0
    for job in jobs:
        jid = str((job or {}).get("id") or "").strip()
        if not jid:
            continue
        st_row = set_by_job.get(jid) or {}
        if not st_row or not _bool(st_row.get("is_active"), True):
            continue
        if not _bool(st_row.get("enable_daily_update_emails"), False):
            continue

        cust = _valid_emails(_norm_list(st_row.get("customer_recipients")))
        internal = _valid_emails(_norm_list(st_row.get("internal_recipients")))
        cc = _valid_emails(_norm_list(st_row.get("cc_recipients")))
        to_list = cust or internal
        if not to_list:
            skipped += 1
            continue

        report = rep_by_job.get(jid)
        if not report:
            if send_missing_reminders and internal:
                subj = f"Missing Daily Report — {str(job.get('job_name') or '').strip() or 'Job'} — {ds}"
                txt = f"Daily supervisor report is missing.\n\nJob: {str(job.get('job_name') or '').strip() or '—'}\nDate: {ds}\n"
                html_body = (
                    "<div style='font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial'>"
                    "<h3>Missing daily supervisor report</h3>"
                    f"<p><b>Job:</b> {_escape(job.get('job_name'))}<br/><b>Date:</b> {_escape(ds)}</p>"
                    "</div>"
                )
                try:
                    _send_email(
                        to_emails=internal,
                        cc_emails=[],
                        bcc_emails=[],
                        subject=subj,
                        text_body=txt,
                        html_body=html_body,
                        notification_type="missing_daily_report_reminder",
                        job_id=jid,
                        meta={"report_date": ds},
                    )
                    sent += 1
                except Exception:
                    failed += 1
            else:
                skipped += 1
            continue

        rid = str(report.get("id") or "").strip()
        crew = []
        photos = []
        if rid:
            try:
                crew = fetch_by_match_admin("supervisor_daily_report_crew", {"report_id": rid}, limit=200)
            except Exception:
                crew = []
            try:
                photos = fetch_by_match_admin(
                    "supervisor_daily_report_photos",
                    {"report_id": rid},
                    columns="storage_path,file_name",
                    limit=100,
                )
            except Exception:
                photos = []

        photo_urls: list[str] = []
        for ph in photos or []:
            pth = str((ph or {}).get("storage_path") or "").strip()
            if not pth:
                continue
            try:
                u = create_signed_url(pth, expires_in=7 * 24 * 3600)
            except Exception:
                u = ""
            if u:
                photo_urls.append(u)

        subj = f"Daily Update — {str(job.get('job_name') or '').strip() or 'Job'} — {ds}"
        text_body, html_body = _daily_bodies(
            job=job,
            report=report,
            crew_lines=list(crew or []),
            photo_urls=photo_urls,
        )
        try:
            _send_email(
                to_emails=to_list,
                cc_emails=cc,
                bcc_emails=[],
                subject=subj,
                text_body=text_body,
                html_body=html_body,
                notification_type="daily_supervisor_report_summary",
                job_id=jid,
                meta={"report_date": ds, "has_photos": bool(photo_urls)},
            )
            sent += 1
        except Exception:
            failed += 1

    return {"sent": sent, "skipped": skipped, "failed": failed}


def _week_bounds_for(friday: date) -> tuple[date, date]:
    start = friday - timedelta(days=friday.weekday())  # Monday
    end = start + timedelta(days=6)  # Sunday
    return start, end


def run_weekly_friday_customer_updates(*, friday: date | None = None) -> dict[str, int]:
    """Weekly email: summarizes all reports for Mon–Sun week containing Friday; only runs on Fridays."""
    f = friday or date.today()
    if f.weekday() != 4:
        return {"sent": 0, "skipped": 0, "failed": 0}
    if not _table_exists_admin("job_email_settings") or not _table_exists_admin("supervisor_daily_reports"):
        return {"sent": 0, "skipped": 0, "failed": 0}
    try:
        from app.db import fetch_table_admin, get_admin_client
    except ImportError:
        from db import fetch_table_admin, get_admin_client  # type: ignore

    week_start, week_end = _week_bounds_for(f)
    s_iso = week_start.isoformat()[:10]
    e_iso = week_end.isoformat()[:10]

    jobs = list(fetch_table_admin("jobs", limit=8000, order_by="job_number") or [])
    settings_rows = list(fetch_table_admin("job_email_settings", limit=10000, order_by=None) or [])
    set_by_job = {str(r.get("job_id") or "").strip(): r for r in settings_rows if isinstance(r, dict)}

    reports = (
        get_admin_client()
        .table("supervisor_daily_reports")
        .select("*")
        .gte("report_date", s_iso)
        .lte("report_date", e_iso)
        .limit(20000)
        .execute()
        .data
        or []
    )
    reps_by_job: dict[str, list[dict[str, Any]]] = {}
    for r in reports:
        if not isinstance(r, dict):
            continue
        jid = str(r.get("job_id") or "").strip()
        if jid:
            reps_by_job.setdefault(jid, []).append(r)
    for lst in reps_by_job.values():
        lst.sort(key=lambda x: str(x.get("report_date") or ""))

    sent = skipped = failed = 0
    for job in jobs:
        jid = str((job or {}).get("id") or "").strip()
        if not jid:
            continue
        st_row = set_by_job.get(jid) or {}
        if not st_row or not _bool(st_row.get("is_active"), True):
            continue
        if not _bool(st_row.get("enable_weekly_friday_update_emails"), False):
            continue

        cust = _valid_emails(_norm_list(st_row.get("customer_recipients")))
        internal = _valid_emails(_norm_list(st_row.get("internal_recipients")))
        cc = _valid_emails(_norm_list(st_row.get("cc_recipients")))
        to_list = cust or internal
        if not to_list:
            skipped += 1
            continue
        week_reports = reps_by_job.get(jid) or []
        if not week_reports:
            skipped += 1
            continue

        job_name = str(job.get("job_name") or "").strip() or "—"
        subj = f"Weekly Update — {job_name} — {s_iso} to {e_iso}"

        rows_txt: list[str] = []
        rows_html: list[str] = []
        for r in week_reports:
            ds = str(r.get("report_date") or "")[:10] or "—"
            sup = str(r.get("supervisor_name") or "").strip() or "—"
            crew = str(r.get("crew_size") or "").strip() or "—"
            done = str(r.get("completed_today") or "").strip() or "—"
            delays = ", ".join(_delay_labels(r)) or "—"
            rows_txt.append(f"{ds} — Supervisor: {sup} — Crew: {crew} — Delays: {delays}\nCompleted: {done}")
            rows_html.append(
                "<tr>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>{_escape(ds)}</td>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>{_escape(sup)}</td>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>{_escape(crew)}</td>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>{_escape(delays)}</td>"
                f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;white-space:pre-wrap'>{_escape(done)}</td>"
                "</tr>"
            )

        text = f"Weekly job update\nJob: {job_name}\nWeek: {s_iso} to {e_iso}\n\n" + "\n\n".join(rows_txt)
        html_body = (
            "<div style='font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial'>"
            "<h3>Weekly job update</h3>"
            f"<p><b>Job:</b> {_escape(job_name)}<br/><b>Week:</b> {_escape(s_iso)} to {_escape(e_iso)}</p>"
            "<table style='border-collapse:collapse;width:100%;max-width:900px'>"
            "<thead><tr>"
            "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #e5e7eb'>Date</th>"
            "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #e5e7eb'>Supervisor</th>"
            "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #e5e7eb'>Crew</th>"
            "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #e5e7eb'>Delays</th>"
            "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #e5e7eb'>Completed</th>"
            "</tr></thead><tbody>"
            + "".join(rows_html)
            + "</tbody></table></div>"
        )
        try:
            _send_email(
                to_emails=to_list,
                cc_emails=cc,
                bcc_emails=[],
                subject=subj,
                text_body=text,
                html_body=html_body,
                notification_type="weekly_friday_customer_update",
                job_id=jid,
                meta={"week_start": s_iso, "week_end": e_iso, "reports": len(week_reports)},
            )
            sent += 1
        except Exception:
            failed += 1

    return {"sent": sent, "skipped": skipped, "failed": failed}


def pipeline_digest_recipients(*, override: list[str] | None = None) -> list[str]:
    if override:
        return _valid_emails(_norm_list(override))
    return _valid_emails(_norm_list(getattr(settings, "pipeline_digest_recipients", "") or ""))


def _pipeline_attention_rows() -> list[dict[str, Any]]:
    try:
        from app.services.pipeline_service import build_pipeline_rows, filter_pipeline_rows
    except ImportError:
        from services.pipeline_service import build_pipeline_rows, filter_pipeline_rows  # type: ignore

    try:
        from app.pages._core._data import load_estimates, load_jobs
    except ImportError:
        from pages._core._data import load_estimates, load_jobs  # type: ignore

    rows = build_pipeline_rows(load_estimates(), load_jobs())
    return filter_pipeline_rows(rows, view="Needs Attention")


def _pipeline_digest_bodies(rows: list[dict[str, Any]]) -> tuple[str, str]:
    lines_txt: list[str] = []
    rows_html: list[str] = []
    for row in rows[:50]:
        q = str(row.get("quote_number") or "—")
        j = str(row.get("job_number") or "—")
        cust = str(row.get("customer") or "—")
        hint = str(row.get("stale_hint") or "Needs follow-up")
        val = float(row.get("value") or 0)
        val_txt = f"${val:,.2f}" if val else "—"
        lines_txt.append(f"- {q} / {j} — {cust} — {hint} — {val_txt}")
        rows_html.append(
            "<tr>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>{_escape(q)}</td>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>{_escape(j)}</td>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>{_escape(cust)}</td>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb'>{_escape(hint)}</td>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;text-align:right'>{_escape(val_txt)}</td>"
            "</tr>"
        )
    extra = len(rows) - 50
    if extra > 0:
        lines_txt.append(f"... and {extra} more")
    text = (
        f"Pipeline attention digest — {len(rows)} item(s) need follow-up.\n\n"
        + "\n".join(lines_txt)
    )
    html_body = (
        "<div style='font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial'>"
        f"<h3>Pipeline needs attention ({len(rows)})</h3>"
        "<p>Quotes and jobs flagged for follow-up in IPS Pipeline.</p>"
        "<table style='border-collapse:collapse;width:100%;max-width:960px'>"
        "<thead><tr>"
        "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #e5e7eb'>Quote</th>"
        "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #e5e7eb'>Job</th>"
        "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #e5e7eb'>Customer</th>"
        "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #e5e7eb'>Reason</th>"
        "<th style='text-align:right;padding:6px 8px;border-bottom:2px solid #e5e7eb'>Value</th>"
        "</tr></thead><tbody>"
        + "".join(rows_html)
        + "</tbody></table>"
        + (f"<p style='margin-top:12px;color:#64748b'>+ {extra} more not shown.</p>" if extra > 0 else "")
        + "</div>"
    )
    return text, html_body


def run_pipeline_attention_digest(
    *,
    recipients: list[str] | None = None,
) -> dict[str, int]:
    """
    Email supervisors/ops a digest of pipeline rows in the **Needs Attention** view.

    Recipients: ``recipients`` arg, else ``PIPELINE_DIGEST_RECIPIENTS`` env (comma-separated).
    """
    rows = _pipeline_attention_rows()
    to_list = pipeline_digest_recipients(override=recipients)
    if not rows:
        return {"sent": 0, "skipped": 1, "failed": 0}
    if not to_list:
        return {"sent": 0, "skipped": 1, "failed": 0}

    ds = date.today().isoformat()
    subj = f"Pipeline Attention — {len(rows)} item(s) — {ds}"
    text_body, html_body = _pipeline_digest_bodies(rows)
    try:
        _send_email(
            to_emails=to_list,
            cc_emails=[],
            bcc_emails=[],
            subject=subj,
            text_body=text_body,
            html_body=html_body,
            notification_type="pipeline_attention_digest",
            job_id=None,
            meta={"stale_count": len(rows), "report_date": ds},
        )
        return {"sent": 1, "skipped": 0, "failed": 0}
    except Exception:
        return {"sent": 0, "skipped": 0, "failed": 1}

