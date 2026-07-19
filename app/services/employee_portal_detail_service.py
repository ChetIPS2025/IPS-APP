"""Employee Portal focused detail queries — updates, jobs, bids, certifications."""

from __future__ import annotations

import time
from typing import Any

from app.services.employee_portal_service import (
    list_assigned_job_ids_for_employee,
    strip_estimate_for_employee,
    strip_job_for_employee,
    update_visible_to_role,
)
from app.services.repository import ServiceResult

_SIGNED_URL_TTL_BUFFER = 300


def _portal_update_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "title": str(row.get("title") or "Untitled"),
        "body": str(row.get("body") or row.get("content") or ""),
        "date": str(row.get("date") or row.get("created_at") or "")[:10],
        "created_at": str(row.get("created_at") or row.get("date") or ""),
        "priority": str(row.get("priority") or "Normal"),
        "category": str(row.get("category") or "General"),
    }


def get_employee_portal_update_detail(
    update_id: str,
    *,
    employee_id: str,
    role: str,
    user_id: str = "",
) -> dict[str, Any] | None:
    _ = (employee_id, user_id)
    uid = str(update_id or "").strip()
    if not uid:
        return None
    from app.components.company_updates_feed import dashboard_update_visible
    from app.pages._core._data import load_company_updates

    for row in load_company_updates():
        if str(row.get("id") or "") != uid:
            continue
        if not dashboard_update_visible(row) or not update_visible_to_role(row, role):
            return None
        return _portal_update_row(row)
    return None


def _employee_can_view_job(job: dict[str, Any], *, employee_id: str, role: str) -> bool:
    from app.utils.permissions import normalize_role

    _ = role
    if not job or job.get("is_deleted"):
        return False
    status = str(job.get("status") or "").strip().lower()
    if status in {"cancelled", "canceled", "deleted"}:
        return False
    eid = str(employee_id or "").strip()
    if not eid:
        return normalize_role(role) == "admin"
    from app.services.employee_portal_service import list_assigned_job_ids_for_employee

    assigned = set(list_assigned_job_ids_for_employee(eid))
    jid = str(job.get("id") or "")
    if jid in assigned:
        return True
    if status in {"active", "on hold"}:
        return True
    return False


def get_employee_portal_job_detail(
    job_id: str,
    *,
    employee_id: str,
    role: str,
) -> dict[str, Any] | None:
    jid = str(job_id or "").strip()
    if not jid:
        return None
    from app.services.repository import fetch_by_id

    row = fetch_by_id("jobs", jid)
    if not row:
        try:
            from app.pages._core._data import _DEMO_JOBS

            row = next((j for j in _DEMO_JOBS if str(j.get("id") or "") == jid), None)
        except Exception:
            row = None
    if not row or not _employee_can_view_job(row, employee_id=employee_id, role=role):
        return None
    safe = strip_job_for_employee(row)
    safe["_portal_assigned"] = jid in set(list_assigned_job_ids_for_employee(employee_id))
    return safe


def _employee_can_view_bid(row: dict[str, Any]) -> bool:
    from app.services.employee_portal_service import _BIDDING_ESTIMATE_STATUSES

    status = str(row.get("status") or "").strip().lower()
    return status in _BIDDING_ESTIMATE_STATUSES


def get_employee_portal_bid_detail(
    estimate_id: str,
    *,
    employee_id: str,
    role: str,
) -> dict[str, Any] | None:
    _ = (employee_id, role)
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    from app.services.repository import fetch_by_id

    row = fetch_by_id("estimates", eid)
    if not row:
        try:
            from app.pages._core._data import load_estimates

            row = next((e for e in load_estimates() if str(e.get("id") or "") == eid), None)
        except Exception:
            row = None
    if not row or not _employee_can_view_bid(row):
        return None
    return strip_estimate_for_employee(row)


def get_employee_certification_open_target(
    certification_id: str,
    *,
    employee_id: str,
) -> ServiceResult:
    cid = str(certification_id or "").strip()
    eid = str(employee_id or "").strip()
    if not cid or not eid:
        return ServiceResult(ok=False, error="Certification not found.")

    from app.services.certification_attachments_service import cert_has_attachment
    from app.services.certification_helpers import certification_visible_to_user
    from app.services.employees_service import get_certification_attachment_url
    from app.pages._core._data import load_certifications

    cert = None
    for row in load_certifications(eid):
        if str(row.get("id") or "") == cid:
            cert = row
            break
    if not cert or not certification_visible_to_user(cert, role="employee", viewer_employee_id=eid):
        return ServiceResult(ok=False, error="You do not have access to this certification.")
    if not cert_has_attachment(cert):
        return ServiceResult(ok=False, error="No document is attached to this certification yet.")

    cache_key = f"ips_ep_cert_signed_{cid}"
    try:
        import streamlit as st

        cached = st.session_state.get(cache_key)
        if isinstance(cached, dict):
            expires_at = float(cached.get("expires_at") or 0)
            url = str(cached.get("url") or "").strip()
            if url and expires_at > time.time():
                return ServiceResult(ok=True, data={"url": url, "kind": "signed"})
    except Exception:
        pass

    url = get_certification_attachment_url(cert)
    if not url:
        return ServiceResult(ok=False, error="Could not open the attached document right now.")
    try:
        import streamlit as st

        st.session_state[cache_key] = {
            "url": url,
            "expires_at": time.time() + 3600 - _SIGNED_URL_TTL_BUFFER,
        }
    except Exception:
        pass
    return ServiceResult(ok=True, data={"url": url, "kind": "signed"})


__all__ = [
    "get_employee_certification_open_target",
    "get_employee_portal_bid_detail",
    "get_employee_portal_job_detail",
    "get_employee_portal_update_detail",
]
