"""Employee Portal data — workforce-safe views with financial fields stripped."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.employee_portal_cache import employee_portal_data_version

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


@dataclass(frozen=True)
class EmployeePortalContext:
    role: str
    user_id: str
    employee_id: str
    employee_name: str
    profile: dict[str, Any]
    employee: dict[str, Any] | None
    view_as_mode: str
    today: date
    can_view_timekeeping: bool
    can_view_resources: bool
    can_scan_assets: bool


@dataclass(frozen=True)
class EmployeePortalSnapshot:
    employee: dict[str, Any] | None
    updates: list[dict[str, Any]]
    certifications: list[dict[str, Any]]
    recent_jobs: list[dict[str, Any]]
    upcoming_schedule: list[dict[str, Any]]
    warnings: list[str]


@dataclass(frozen=True)
class EmployeePortalJobsPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int


@dataclass(frozen=True)
class EmployeePortalBidsPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int


def build_employee_portal_context(
    profile: dict[str, Any] | None,
    *,
    role: str,
    employee_id: str,
    employee: dict[str, Any] | None,
) -> EmployeePortalContext:
    from app.utils.permissions import role_can_access_page
    from app.utils.view_as import is_view_as_active, view_as_mode

    prof = profile if isinstance(profile, dict) else {}
    user_id = str(prof.get("id") or prof.get("sub") or "")
    view_as = f"preview_{view_as_mode()}" if is_view_as_active() else "employee"
    return EmployeePortalContext(
        role=str(role or ""),
        user_id=user_id,
        employee_id=str(employee_id or ""),
        employee_name=portal_employee_display_name(prof, employee),
        profile=prof,
        employee=employee,
        view_as_mode=view_as,
        today=date.today(),
        can_view_timekeeping=role_can_access_page(role, "timekeeping"),
        can_view_resources=role_can_access_page(role, "employee_resources"),
        can_scan_assets=role_can_access_page(role, "scan_asset") or role_can_access_page(role, "employee_qr_scan"),
    )


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
    from app.utils.permissions import normalize_role
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


def _portal_update_card(row: dict[str, Any]) -> dict[str, Any]:
    from app.components.company_updates_feed import _is_update_unread

    body = str(row.get("body") or row.get("content") or "")
    return {
        "id": str(row.get("id") or ""),
        "title": str(row.get("title") or "Untitled"),
        "body": body[:500],
        "snippet": body[:140],
        "date": str(row.get("date") or row.get("created_at") or "")[:10],
        "created_at": str(row.get("created_at") or row.get("date") or ""),
        "priority": str(row.get("priority") or "Normal"),
        "category": str(row.get("category") or "General"),
        "is_unread": _is_update_unread(row),
    }


def list_employee_portal_updates(*, role: str, limit: int = 8) -> list[dict[str, Any]]:
    from app.components.company_updates_feed import dashboard_update_visible, sort_dashboard_updates
    from app.pages._core._data import load_company_updates

    cap = max(1, int(limit or 8))
    version = employee_portal_data_version()
    cache_key = f"employee_portal:updates:v{version}:role:{role}:limit:{cap}"

    def _build() -> list[dict[str, Any]]:
        from app.perf_debug import perf_span

        with perf_span("employee_portal.updates"):
            rows = [
                u
                for u in load_company_updates()
                if dashboard_update_visible(u) and update_visible_to_role(u, role)
            ]
            sorted_rows = sort_dashboard_updates(rows)
            return [_portal_update_card(r) for r in sorted_rows[:cap]]

    return page_data_cache_get(cache_key, _build)


def _fetch_jobs_by_ids(job_ids: list[str]) -> dict[str, dict[str, Any]]:
    from app.services.repository import fetch_by_id

    out: dict[str, dict[str, Any]] = {}
    for jid in job_ids:
        rid = str(jid or "").strip()
        if not rid or rid in out:
            continue
        row = fetch_by_id("jobs", rid)
        if row and not row.get("is_deleted"):
            out[rid] = strip_job_for_employee(row)
    if out:
        return out
    try:
        from app.pages._core._data import _DEMO_JOBS

        for row in _DEMO_JOBS:
            jid = str(row.get("id") or "")
            if jid in job_ids and jid not in out:
                out[jid] = strip_job_for_employee(row)
    except Exception:
        pass
    return out


def _iter_active_job_rows(*, scan_limit: int = 500) -> list[dict[str, Any]]:
    from app.services.repository import fetch_list

    try:
        from app.pages._core._data import _DEMO_JOBS
    except ImportError:
        _DEMO_JOBS = []
    rows, _ = fetch_list("jobs", order_by="start_date", limit=scan_limit, demo=list(_DEMO_JOBS))
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.get("is_deleted"):
            continue
        status = str(row.get("status") or "").strip().lower()
        if status not in _ACTIVE_JOB_STATUSES:
            continue
        out.append(strip_job_for_employee(row))
    out.sort(key=lambda r: (str(r.get("start_date") or ""), str(r.get("job_name") or "")), reverse=True)
    return out


def _apply_job_search(rows: list[dict[str, Any]], search: str) -> list[dict[str, Any]]:
    q = str(search or "").strip().lower()
    if not q:
        return rows
    out: list[dict[str, Any]] = []
    for row in rows:
        hay = " ".join(
            str(row.get(k) or "")
            for k in ("job_number", "job_name", "customer", "location", "location_name", "supervisor")
        ).lower()
        if q in hay:
            out.append(row)
    return out


def list_active_jobs_for_employee() -> list[dict[str, Any]]:
    """Backward-compatible full active job list."""
    return _iter_active_job_rows()


def list_active_jobs_for_employee_page(
    *,
    employee_id: str,
    role: str,
    search: str = "",
    page: int = 1,
    page_size: int = 25,
) -> EmployeePortalJobsPage:
    _ = (employee_id, role)
    version = employee_portal_data_version(employee_id)
    cache_key = f"employee_portal:active_jobs:v{version}:s{search}:p{page}:sz{page_size}"

    def _build() -> EmployeePortalJobsPage:
        from app.perf_debug import perf_span

        with perf_span("employee_portal.all_jobs_query"):
            filtered = _apply_job_search(_iter_active_job_rows(), search)
            total = len(filtered)
            pg = max(1, int(page or 1))
            size = max(1, min(100, int(page_size or 25)))
            start = (pg - 1) * size
            return EmployeePortalJobsPage(
                rows=filtered[start : start + size],
                total_count=total,
                page=pg,
                page_size=size,
            )

    return page_data_cache_get(cache_key, _build)


def _iter_bidding_estimate_rows(*, scan_limit: int = 500) -> list[dict[str, Any]]:
    from app.services.repository import fetch_list

    try:
        from app.pages._core._data import _DEMO_ESTIMATES
    except ImportError:
        _DEMO_ESTIMATES = []
    rows, _ = fetch_list("estimates", order_by="expiration_date", limit=scan_limit, demo=list(_DEMO_ESTIMATES))
    out: list[dict[str, Any]] = []
    for row in rows:
        status = str(row.get("status") or "").strip().lower()
        if status not in _BIDDING_ESTIMATE_STATUSES:
            continue
        out.append(strip_estimate_for_employee(row))
    out.sort(key=lambda r: (str(r.get("expiration_date") or ""), str(r.get("project_name") or "")))
    return out


def _apply_bid_search(rows: list[dict[str, Any]], search: str) -> list[dict[str, Any]]:
    q = str(search or "").strip().lower()
    if not q:
        return rows
    out: list[dict[str, Any]] = []
    for row in rows:
        hay = " ".join(
            str(row.get(k) or "")
            for k in (
                "estimate_number",
                "project_name",
                "customer",
                "location",
                "status",
                "created_by",
                "description",
            )
        ).lower()
        if q in hay:
            out.append(row)
    return out


def list_bidding_estimates_for_employee() -> list[dict[str, Any]]:
    return _iter_bidding_estimate_rows()


def list_bidding_estimates_for_employee_page(
    *,
    employee_id: str,
    role: str,
    search: str = "",
    page: int = 1,
    page_size: int = 25,
) -> EmployeePortalBidsPage:
    _ = (employee_id, role)
    version = employee_portal_data_version()
    cache_key = f"employee_portal:bids:v{version}:s{search}:p{page}:sz{page_size}"

    def _build() -> EmployeePortalBidsPage:
        from app.perf_debug import perf_span

        with perf_span("employee_portal.bids_query"):
            filtered = _apply_bid_search(_iter_bidding_estimate_rows(), search)
            total = len(filtered)
            pg = max(1, int(page or 1))
            size = max(1, min(100, int(page_size or 25)))
            start = (pg - 1) * size
            return EmployeePortalBidsPage(
                rows=filtered[start : start + size],
                total_count=total,
                page=pg,
                page_size=size,
            )

    return page_data_cache_get(cache_key, _build)


def _cert_sort_key(cert: dict[str, Any]) -> tuple:
    from app.services.certification_helpers import compute_certification_status

    status = str(compute_certification_status(cert) or "")
    rank = {"Expiring Soon": 0, "Active": 1, "Expired": 2}.get(status, 3)
    return (rank, str(cert.get("expiration_date") or "9999"), str(cert.get("cert_type") or "").lower())


def list_portal_certification_summaries(employee_id: str, *, limit: int = 12) -> list[dict[str, Any]]:
    eid = str(employee_id or "").strip()
    if not eid:
        return []
    version = employee_portal_data_version(eid)
    cache_key = f"employee_portal:certs:v{version}:eid:{eid}:limit:{limit}"

    def _build() -> list[dict[str, Any]]:
        from app.perf_debug import perf_span
        from app.services.certification_attachments_service import cert_has_attachment
        from app.services.certification_helpers import (
            certification_visible_to_user,
            compute_certification_status,
        )

        with perf_span("employee_portal.certifications"):
            from app.pages._core._data import load_certifications

            rows = load_certifications(eid)
            out: list[dict[str, Any]] = []
            for cert in rows:
                if not certification_visible_to_user(cert, role="employee", viewer_employee_id=eid):
                    continue
                out.append(
                    {
                        "id": str(cert.get("id") or ""),
                        "cert_type": str(cert.get("cert_type") or cert.get("certification_type") or "Certification"),
                        "expiration_date": str(cert.get("expiration_date") or "")[:10],
                        "status": compute_certification_status(cert),
                        "has_attachment": cert_has_attachment(cert),
                    }
                )
            out.sort(key=_cert_sort_key)
            return out[: max(1, int(limit or 12))]

    return page_data_cache_get(cache_key, _build)


def list_my_certifications_for_portal(employee_id: str) -> list[dict[str, Any]]:
    """Backward-compatible certification list."""
    summaries = list_portal_certification_summaries(employee_id, limit=50)
    return [
        {
            "id": s["id"],
            "cert_type": s["cert_type"],
            "certification_type": s["cert_type"],
            "expiration_date": s["expiration_date"],
            "status": s["status"],
            "has_attachment": s.get("has_attachment"),
        }
        for s in summaries
    ]


def list_employee_upcoming_schedule(
    employee_id: str,
    *,
    start_date: date | None = None,
    days: int = 14,
    limit: int = 10,
) -> list[dict[str, Any]]:
    eid = str(employee_id or "").strip()
    if not eid:
        return []
    _ = (start_date, days)
    version = employee_portal_data_version(eid)
    cache_key = f"employee_portal:schedule:v{version}:eid:{eid}:limit:{limit}"

    def _build() -> list[dict[str, Any]]:
        from app.perf_debug import perf_span
        from app.services.scheduling_service import enrich_events, list_upcoming_employee_schedule

        with perf_span("employee_portal.schedule"):
            events = list_upcoming_employee_schedule(eid, limit=limit)
            job_ids = sorted({str(ev.get("job_id") or "").strip() for ev in events if ev.get("job_id")})
            sup_ids = sorted({str(ev.get("supervisor_id") or "").strip() for ev in events if ev.get("supervisor_id")})
            jobs_by_id = _fetch_jobs_by_ids(job_ids)
            employees_by_id: dict[str, dict[str, Any]] = {}
            if sup_ids:
                from app.services.employees_service import get_employee

                for sid in sup_ids:
                    emp = get_employee(sid)
                    if emp:
                        employees_by_id[sid] = emp
            return enrich_events(events, jobs_by_id=jobs_by_id, employees_by_id=employees_by_id)

    return page_data_cache_get(cache_key, _build)


def load_employee_portal_snapshot(
    *,
    employee_id: str,
    role: str,
    user_id: str,
    updates_limit: int = 8,
    recent_jobs_limit: int = 4,
    schedule_limit: int = 10,
) -> EmployeePortalSnapshot:
    version = employee_portal_data_version(employee_id)
    cache_key = (
        f"employee_portal:snapshot:v{version}:eid:{employee_id}:role:{role}:uid:{user_id}:"
        f"u{updates_limit}:j{recent_jobs_limit}:s{schedule_limit}"
    )

    def _build() -> EmployeePortalSnapshot:
        from app.perf_debug import perf_span
        from app.services.employees_service import get_employee

        warnings: list[str] = []
        employee = None
        updates: list[dict[str, Any]] = []
        certifications: list[dict[str, Any]] = []
        recent_jobs: list[dict[str, Any]] = []
        upcoming_schedule: list[dict[str, Any]] = []

        with perf_span("employee_portal.snapshot"):
            if employee_id:
                try:
                    with perf_span("employee_portal.employee"):
                        employee = get_employee(employee_id)
                except Exception:
                    warnings.append("Profile details are temporarily unavailable.")
            try:
                updates = list_employee_portal_updates(role=role, limit=updates_limit)
            except Exception:
                warnings.append("Company updates are temporarily unavailable.")
            if employee_id:
                try:
                    certifications = list_portal_certification_summaries(employee_id)
                except Exception:
                    warnings.append("Certifications are temporarily unavailable.")
                try:
                    recent_jobs = list_portal_dashboard_jobs(employee_id, limit=recent_jobs_limit)
                except Exception:
                    warnings.append("Recent jobs are temporarily unavailable.")
                try:
                    upcoming_schedule = list_employee_upcoming_schedule(employee_id, limit=schedule_limit)
                except Exception:
                    warnings.append("Upcoming schedule is temporarily unavailable.")

        return EmployeePortalSnapshot(
            employee=employee,
            updates=updates,
            certifications=certifications,
            recent_jobs=recent_jobs,
            upcoming_schedule=upcoming_schedule,
            warnings=warnings,
        )

    return page_data_cache_get(cache_key, _build)

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
    from app.pages._core._data import _fetch_table
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
    version = employee_portal_data_version(employee_id)
    cache_key = f"employee_portal:recent_jobs:v{version}:eid:{employee_id}:limit:{cap}"

    def _build() -> list[dict[str, Any]]:
        from app.perf_debug import perf_span

        with perf_span("employee_portal.recent_jobs"):
            assigned_ids = list_assigned_job_ids_for_employee(employee_id)
            jobs_map = _fetch_jobs_by_ids(assigned_ids[: cap * 2])
            out: list[dict[str, Any]] = []
            seen: set[str] = set()
            for jid in assigned_ids:
                if len(out) >= cap:
                    break
                job = jobs_map.get(jid)
                if not job:
                    continue
                item = dict(job)
                item["_portal_assigned"] = True
                out.append(item)
                seen.add(jid)

            if len(out) < cap:
                for job in _iter_active_job_rows(scan_limit=max(cap * 8, 40)):
                    if len(out) >= cap:
                        break
                    jid = str(job.get("id") or "").strip()
                    if jid and jid not in seen:
                        item = dict(job)
                        item["_portal_assigned"] = False
                        out.append(item)
                        seen.add(jid)
            return out

    return page_data_cache_get(cache_key, _build)
