"""Employee Portal data — workforce-safe views with financial fields stripped."""

from __future__ import annotations

import html
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


_AVATAR_URL_KEYS = (
    "photo_url",
    "image_url",
    "avatar_url",
    "profile_image_url",
    "picture",
    "photo_path",
)


def portal_initials(name: str) -> str:
    parts = [p for p in str(name or "").strip().split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _looks_like_image_url(value: str) -> bool:
    v = str(value or "").strip().lower()
    return v.startswith(("http://", "https://", "data:image", "/"))


def resolve_employee_avatar_url(
    profile: dict[str, Any] | None,
    employee: dict[str, Any] | None = None,
) -> str:
    """Return a displayable avatar URL from profile or employee record, if present."""
    for source in (profile, employee):
        if not isinstance(source, dict):
            continue
        for key in _AVATAR_URL_KEYS:
            raw = str(source.get(key) or "").strip()
            if raw and _looks_like_image_url(raw):
                return raw
    return ""


def portal_employee_display_name(
    profile: dict[str, Any] | None,
    employee: dict[str, Any] | None = None,
) -> str:
    prof = profile if isinstance(profile, dict) else {}
    emp = employee if isinstance(employee, dict) else {}
    for source in (prof, emp):
        nm = str(source.get("full_name") or source.get("name") or "").strip()
        if nm:
            return nm
    email = str(prof.get("email") or emp.get("email") or "").strip()
    if email and "@" in email:
        return email.split("@")[0]
    return "Employee"


def portal_employee_avatar_html(
    profile: dict[str, Any] | None,
    employee: dict[str, Any] | None = None,
) -> str:
    name = portal_employee_display_name(profile, employee)
    url = resolve_employee_avatar_url(profile, employee)
    if url:
        return (
            f'<img class="ips-ep-avatar" src="{html.escape(url)}" '
            f'alt="{html.escape(name)}" />'
        )
    initials = portal_initials(name)
    return (
        f'<div class="ips-ep-avatar ips-ep-avatar-initials" '
        f'aria-label="{html.escape(name)}">{html.escape(initials)}</div>'
    )


def portal_employee_title(
    profile: dict[str, Any] | None,
    employee: dict[str, Any] | None = None,
    *,
    role: str = "",
) -> str:
    emp = employee if isinstance(employee, dict) else {}
    prof = profile if isinstance(profile, dict) else {}
    for source in (emp, prof):
        for key in ("position", "trade", "title", "job_title"):
            val = str(source.get(key) or "").strip()
            if val:
                return val
    role_label = str(role or prof.get("role") or "").strip().replace("_", " ").title()
    return role_label or "Employee"


def _load_time_entries() -> list[dict[str, Any]]:
    try:
        from app.pages._core._data import _fetch_table
    except ImportError:
        from pages._core._data import _fetch_table  # type: ignore
    return list(_fetch_table("time_entries", limit=5000, order_by="work_date") or [])


def list_assigned_job_ids_for_employee(employee_id: str) -> list[str]:
    """Job ids the employee has logged time against, most recent work first."""
    eid = str(employee_id or "").strip()
    if not eid:
        return []
    rows = [
        r
        for r in _load_time_entries()
        if str(r.get("employee_id") or "").strip() == eid
        and str(r.get("job_id") or "").strip()
    ]
    rows.sort(
        key=lambda r: (
            str(r.get("work_date") or r.get("date") or r.get("created_at") or ""),
            str(r.get("updated_at") or r.get("created_at") or ""),
        ),
        reverse=True,
    )
    seen: set[str] = set()
    ordered: list[str] = []
    for row in rows:
        jid = str(row.get("job_id") or "").strip()
        if jid and jid not in seen:
            seen.add(jid)
            ordered.append(jid)
    return ordered


def list_portal_dashboard_jobs(employee_id: str, *, limit: int = 4) -> list[dict[str, Any]]:
    """Up to ``limit`` jobs: assigned first, then most recent active company jobs."""
    cap = max(1, int(limit))
    assigned_ids = list_assigned_job_ids_for_employee(employee_id)
    active_jobs = list_active_jobs_for_employee()
    active_by_id = {str(j.get("id") or ""): j for j in active_jobs}

    all_by_id: dict[str, dict[str, Any]] = dict(active_by_id)
    try:
        from app.pages._core._data import load_jobs
    except ImportError:
        from pages._core._data import load_jobs  # type: ignore
    for row in load_jobs():
        if row.get("is_deleted"):
            continue
        jid = str(row.get("id") or "").strip()
        if jid and jid not in all_by_id:
            all_by_id[jid] = strip_job_for_employee(row)

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for jid in assigned_ids:
        if len(out) >= cap:
            break
        job = all_by_id.get(jid)
        if not job:
            continue
        item = dict(job)
        item["_portal_assigned"] = True
        out.append(item)
        seen.add(jid)

    for job in active_jobs:
        if len(out) >= cap:
            break
        jid = str(job.get("id") or "").strip()
        if jid and jid not in seen:
            item = dict(job)
            item["_portal_assigned"] = False
            out.append(item)
            seen.add(jid)
    return out
