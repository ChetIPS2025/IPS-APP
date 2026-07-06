"""Employee Portal data — workforce-safe views with financial fields stripped."""

from __future__ import annotations

from datetime import date
from typing import Any

_EMPLOYEE_JOB_KEYS = (
    "id",
    "job_number",
    "job_name",
    "customer",
    "customer_id",
    "location",
    "location_name",
    "status",
    "supervisor",
    "start_date",
    "end_date",
    "description",
    "notes",
    "scope",
)

_EMPLOYEE_ESTIMATE_KEYS = (
    "id",
    "estimate_number",
    "project_name",
    "customer",
    "customer_id",
    "customer_location_id",
    "location",
    "status",
    "expiration_date",
    "estimate_date",
    "created_by",
    "description",
    "scope_of_work",
)

_ACTIVE_JOB_STATUSES = frozenset({"active", "on hold"})
_BIDDING_ESTIMATE_STATUSES = frozenset({"draft", "sent", "pending"})


def strip_job_for_employee(row: dict[str, Any]) -> dict[str, Any]:
    """Return only workforce-safe job fields (no costing or billing)."""
    return {k: row.get(k) for k in _EMPLOYEE_JOB_KEYS if k in row or row.get(k) is not None}


def strip_estimate_for_employee(row: dict[str, Any]) -> dict[str, Any]:
    """Return only workforce-safe estimate fields (no pricing)."""
    out = {k: row.get(k) for k in _EMPLOYEE_ESTIMATE_KEYS}
    loc = str(row.get("location") or row.get("site") or row.get("location_name") or "").strip()
    if loc:
        out["location"] = loc
    return out


def _normalize_audience(raw: object) -> str:
    s = str(raw or "").strip()
    if not s:
        return "All"
    known = {
        "all": "All",
        "admin": "Admin",
        "supervisors": "Supervisors",
        "supervisor": "Supervisors",
        "employees": "Employees",
        "employee": "Employees",
        "field crew": "Field Crew",
        "field": "Field Crew",
        "office": "Office",
        "management": "Management",
    }
    return known.get(s.lower(), s)


def update_visible_to_role(row: dict[str, Any], role: str) -> bool:
    """True when a published update should appear for the given role."""
    try:
        from app.utils.permissions import normalize_role
    except ImportError:
        from utils.permissions import normalize_role  # type: ignore

    if not str(row.get("title") or "").strip():
        return False
    status = str(row.get("status") or "").strip().lower().replace("_", " ")
    if status in {"draft", "archived", "scheduled", "inactive"}:
        return False
    if row.get("is_active") is False:
        return False

    norm = normalize_role(role)
    if norm == "admin":
        return True

    audience = _normalize_audience(row.get("audience") or row.get("visibility")).lower()
    if audience in {"", "all"}:
        return True
    if norm == "employee":
        return audience in {"employees", "field crew", "all"}
    if norm in {"supervisor", "project manager"}:
        return audience in {
            "employees",
            "field crew",
            "supervisors",
            "supervisor",
            "management",
            "office",
            "all",
        }
    if norm == "viewer":
        return audience in {"all", "employees", "office"}
    return audience == "all"


def list_employee_portal_updates(*, role: str) -> list[dict[str, Any]]:
    try:
        from app.components.company_updates_feed import dashboard_update_visible, sort_dashboard_updates
        from app.pages._core._data import load_company_updates
    except ImportError:
        from components.company_updates_feed import dashboard_update_visible, sort_dashboard_updates  # type: ignore
        from pages._core._data import load_company_updates  # type: ignore

    rows = [
        u
        for u in load_company_updates()
        if dashboard_update_visible(u) and update_visible_to_role(u, role)
    ]
    return sort_dashboard_updates(rows)


def list_active_jobs_for_employee() -> list[dict[str, Any]]:
    try:
        from app.pages._core._data import load_jobs
    except ImportError:
        from pages._core._data import load_jobs  # type: ignore

    out: list[dict[str, Any]] = []
    for row in load_jobs():
        if row.get("is_deleted"):
            continue
        status = str(row.get("status") or "").strip().lower()
        if status not in _ACTIVE_JOB_STATUSES:
            continue
        out.append(strip_job_for_employee(row))
    out.sort(key=lambda r: (str(r.get("start_date") or ""), str(r.get("job_name") or "")), reverse=True)
    return out


def list_bidding_estimates_for_employee() -> list[dict[str, Any]]:
    try:
        from app.pages._core._data import load_estimates
    except ImportError:
        from pages._core._data import load_estimates  # type: ignore

    out: list[dict[str, Any]] = []
    for row in load_estimates():
        status = str(row.get("status") or "").strip().lower()
        if status not in _BIDDING_ESTIMATE_STATUSES:
            continue
        out.append(strip_estimate_for_employee(row))
    out.sort(
        key=lambda r: (str(r.get("expiration_date") or ""), str(r.get("project_name") or "")),
    )
    return out


def list_my_certifications_for_portal(employee_id: str) -> list[dict[str, Any]]:
    eid = str(employee_id or "").strip()
    if not eid:
        return []
    try:
        from app.pages._core._data import load_certifications
        from app.services.certification_helpers import (
            certification_visible_to_user,
            compute_certification_status,
        )
    except ImportError:
        from pages._core._data import load_certifications  # type: ignore
        from services.certification_helpers import (  # type: ignore
            certification_visible_to_user,
            compute_certification_status,
        )

    rows = load_certifications(eid)
    out: list[dict[str, Any]] = []
    for cert in rows:
        if not certification_visible_to_user(cert, role="employee", viewer_employee_id=eid):
            continue
        item = dict(cert)
        item["status"] = compute_certification_status(cert)
        out.append(item)
    out.sort(key=lambda c: (str(c.get("expiration_date") or "9999"), str(c.get("cert_type") or "")))
    return out


def portal_greeting_name(profile: dict[str, Any] | None) -> str:
    prof = profile if isinstance(profile, dict) else {}
    nm = str(prof.get("full_name") or prof.get("name") or "").strip()
    if nm:
        return nm.split()[0] if " " in nm else nm
    email = str(prof.get("email") or "").strip()
    if email and "@" in email:
        return email.split("@")[0]
    return "there"


def portal_greeting_period() -> str:
    try:
        from datetime import datetime

        hour = datetime.now().hour
    except Exception:
        hour = 12
    if hour < 12:
        return "Good Morning"
    if hour < 17:
        return "Good Afternoon"
    return "Good Evening"
