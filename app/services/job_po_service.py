"""Customer PO fields on jobs: display, persistence, and estimate sync."""

from __future__ import annotations

import logging
from typing import Any

_LOG = logging.getLogger(__name__)


def _fetch_estimate_row(estimate_id: str) -> dict[str, Any]:
    eid = str(estimate_id or "").strip()
    if not eid:
        return {}
    try:
        from app.pages._core._data import get_estimate
    except ImportError:
        from pages._core._data import get_estimate  # type: ignore
    return get_estimate(eid) or {}


def linked_estimate_for_job(job: dict[str, Any]) -> dict[str, Any]:
    """Primary linked estimate for PO display/sync."""
    eid = str(job.get("estimate_id") or "").strip()
    if eid:
        est = _fetch_estimate_row(eid)
        if est:
            return est
    jid = str(job.get("id") or "").strip()
    if not jid:
        return {}
    try:
        from app.db import fetch_by_match_admin
    except ImportError:
        from db import fetch_by_match_admin  # type: ignore
    try:
        rows = fetch_by_match_admin("estimates", {"job_id": jid}, limit=1)
        if rows:
            return rows[0]
    except Exception:
        _LOG.debug("linked_estimate_for_job lookup failed", exc_info=True)
    return {}


def po_fields_from_estimate(estimate: dict[str, Any]) -> dict[str, Any]:
    """Extract PO metadata from an estimate row."""
    po_number = str(estimate.get("po_number") or estimate.get("customer_po") or "").strip()
    po_date_raw = estimate.get("po_date")
    po_date = str(po_date_raw or "").strip()[:10] if po_date_raw not in (None, "") else ""
    try:
        po_amount = round(float(estimate.get("po_amount") or 0), 2)
    except (TypeError, ValueError):
        po_amount = 0.0
    return {
        "po_number": po_number,
        "po_date": po_date or None,
        "po_amount": po_amount if po_amount > 0 else None,
    }


def job_po_locked_by_estimate(job: dict[str, Any]) -> bool:
    """PO fields sync from approved estimate workflow (same gate as financial lock)."""
    try:
        from app.services.job_financial_ui import job_financials_locked_by_approved_estimate
    except ImportError:
        from services.job_financial_ui import job_financials_locked_by_approved_estimate  # type: ignore
    return job_financials_locked_by_approved_estimate(job)


def job_po_editable(job: dict[str, Any]) -> bool:
    return not job_po_locked_by_estimate(job)


def job_po_snapshot(job: dict[str, Any], *, estimate: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merged PO view for UI: job columns with estimate fallback when linked."""
    locked = job_po_locked_by_estimate(job)
    est = estimate if isinstance(estimate, dict) else linked_estimate_for_job(job)
    po_number = str(job.get("po_number") or "").strip()
    po_date = str(job.get("po_date") or "").strip()[:10] if job.get("po_date") not in (None, "") else ""
    try:
        po_amount = round(float(job.get("po_amount") or 0), 2)
    except (TypeError, ValueError):
        po_amount = 0.0

    if est:
        est_po = po_fields_from_estimate(est)
        if locked or not po_number:
            po_number = str(est_po.get("po_number") or po_number).strip()
        if locked or not po_date:
            po_date = str(est_po.get("po_date") or po_date).strip()[:10]
        if locked or po_amount <= 0:
            try:
                fallback_amt = float(est_po.get("po_amount") or 0)
            except (TypeError, ValueError):
                fallback_amt = 0.0
            if fallback_amt > 0:
                po_amount = fallback_amt

    return {
        "po_number": po_number,
        "po_date": po_date,
        "po_amount": po_amount,
        "locked": locked,
        "estimate_id": str(est.get("id") or "").strip() if est else "",
        "has_po": bool(po_number or po_date or po_amount > 0),
    }


def apply_po_fields_to_job_payload(
    job: dict[str, Any],
    estimate: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Build jobs-table patch from estimate PO fields."""
    patch: dict[str, Any] = {}
    est_po = po_fields_from_estimate(estimate)
    for key in ("po_number", "po_date", "po_amount"):
        val = est_po.get(key)
        if val in (None, "", 0, 0.0):
            continue
        if overwrite or not str(job.get(key) or "").strip():
            patch[key] = val
    return patch


def _fetch_estimate_po_attachments(estimate_id: str) -> list[dict[str, Any]]:
    eid = str(estimate_id or "").strip()
    if not eid:
        return []
    try:
        from app.db import fetch_by_match_admin
    except ImportError:
        from db import fetch_by_match_admin  # type: ignore
    try:
        rows = fetch_by_match_admin("attachments", {"estimate_id": eid}, limit=50)
    except Exception:
        return []
    return [
        r
        for r in (rows or [])
        if isinstance(r, dict) and str(r.get("category") or "").strip().lower() == "po_attachment"
    ]


def _download_storage_bytes(storage_path: str) -> bytes | None:
    path = str(storage_path or "").strip()
    if not path:
        return None
    try:
        from app.db import create_signed_url
    except ImportError:
        from db import create_signed_url  # type: ignore
    try:
        url = create_signed_url(path, expires_in=300)
    except Exception:
        url = ""
    if not url:
        return None
    try:
        import urllib.request

        with urllib.request.urlopen(url, timeout=120) as resp:
            return resp.read()
    except Exception:
        _LOG.debug("Could not download PO attachment from %s", path, exc_info=True)
        return None


def ensure_customer_po_document_from_estimate(
    job_id: str,
    estimate_id: str,
    *,
    uploaded_by: str = "",
    admin: bool = True,
) -> bool:
    """Copy first estimate PO attachment to job documents when job has none yet."""
    jid = str(job_id or "").strip()
    eid = str(estimate_id or "").strip()
    if not jid or not eid:
        return False
    try:
        from app.services.job_documents import fetch_customer_po_document, upload_customer_po_document
    except ImportError:
        from services.job_documents import fetch_customer_po_document, upload_customer_po_document  # type: ignore

    if fetch_customer_po_document(jid, admin=admin):
        return False
    atts = _fetch_estimate_po_attachments(eid)
    if not atts:
        return False
    att = atts[0]
    storage_path = str(att.get("storage_path") or "").strip()
    data = _download_storage_bytes(storage_path)
    if not data:
        return False
    file_name = str(att.get("file_name") or att.get("name") or "customer_po.pdf").strip() or "customer_po.pdf"
    content_type = str(att.get("content_type") or att.get("file_type") or "application/pdf").strip()
    try:
        upload_customer_po_document(
            job_id=jid,
            file_data=data,
            file_name=file_name,
            content_type=content_type,
            uploaded_by=uploaded_by,
            notes="Synced from linked estimate PO attachment.",
            admin=admin,
        )
        return True
    except Exception:
        _LOG.warning("Could not copy estimate PO attachment to job %s", jid, exc_info=True)
        return False


def sync_job_po_from_estimate(
    job_id: str,
    *,
    job: dict[str, Any] | None = None,
    estimate: dict[str, Any] | None = None,
    copy_attachment: bool = True,
    uploaded_by: str = "",
    admin: bool = True,
) -> dict[str, Any]:
    """Persist estimate PO fields onto the job and optionally copy PO file."""
    jid = str(job_id or "").strip()
    if not jid:
        return {"ok": False, "error": "job_id required"}
    job_row = dict(job or {})
    if not job_row.get("id"):
        try:
            from app.db import fetch_one
        except ImportError:
            from db import fetch_one  # type: ignore
        job_row = fetch_one("jobs", {"id": jid}) or {}
    est = dict(estimate or linked_estimate_for_job(job_row))
    if not est:
        return {"ok": False, "error": "No linked estimate found."}
    patch = apply_po_fields_to_job_payload(job_row, est, overwrite=True)
    copied = False
    if patch:
        try:
            from app.services.repository import filter_payload_to_table, update_row
        except ImportError:
            from services.repository import filter_payload_to_table, update_row  # type: ignore
        filtered = filter_payload_to_table("jobs", patch)
        if filtered:
            result = update_row("jobs", filtered, {"id": jid})
            if not result.ok:
                return {"ok": False, "error": result.error or "Could not update job PO fields."}
    if copy_attachment:
        copied = ensure_customer_po_document_from_estimate(
            jid,
            str(est.get("id") or ""),
            uploaded_by=uploaded_by,
            admin=admin,
        )
    try:
        from app.pages._core._data import clear_all_catalog_list_caches
    except ImportError:
        from pages._core._data import clear_all_catalog_list_caches  # type: ignore
    clear_all_catalog_list_caches()
    return {"ok": True, "patch": patch, "attachment_copied": copied}
