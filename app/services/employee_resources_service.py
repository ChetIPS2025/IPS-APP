"""Employee toolbox / resources — CRUD, role-filtered listing, and URL resolution."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.pages._core.page_data_cache import page_data_cache_get
from app.services.employee_resources_cache import (
    employee_resources_data_version,
    finalize_employee_resource_write,
    invalidate_employee_resources_cache,
)
from app.services.repository import ServiceResult
from app.utils.permissions import normalize_role

RESOURCE_TYPES = (
    "Document",
    "Form",
    "Link",
    "Policy",
    "Safety",
    "Training",
    "Equipment Manual",
    "HR",
)

ROLE_VISIBILITY_OPTIONS = (
    "employee",
    "supervisor",
    "project manager",
    "admin",
)

EMPLOYEE_RESOURCES_DEFAULT_PAGE_SIZE = 24
ADMIN_RESOURCES_DEFAULT_PAGE_SIZE = 25

_SAFE_URL_SCHEMES = frozenset({"http", "https", "mailto"})
_UNSAFE_URL_SCHEMES = frozenset({"javascript", "data", "file", "vbscript"})

_SIGNED_URL_TTL_BUFFER = 300

_DEMO_RESOURCES: list[dict[str, Any]] = [
    {
        "id": "demo-res-handbook",
        "title": "IPS Employee Handbook",
        "category": "Document",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/employee-handbook",
        "description": "Company policies, expectations, and benefits overview.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 10,
    },
    {
        "id": "demo-res-pto",
        "title": "Request Vacation / PTO Form",
        "category": "Form",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/forms/pto",
        "description": "Submit paid time off and vacation requests.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 20,
    },
    {
        "id": "demo-res-incident",
        "title": "Incident Report Form",
        "category": "Form",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/forms/incident",
        "description": "Report workplace incidents and injuries.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 30,
    },
    {
        "id": "demo-res-near-miss",
        "title": "Safety Report / Near Miss Form",
        "category": "Safety",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/forms/near-miss",
        "description": "Report hazards and near misses before they become incidents.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 40,
    },
    {
        "id": "demo-res-time",
        "title": "Time Correction Request",
        "category": "Form",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/forms/time-correction",
        "description": "Request a correction to submitted time entries.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 50,
    },
    {
        "id": "demo-res-tool",
        "title": "Tool or Equipment Request",
        "category": "Form",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/forms/tool-request",
        "description": "Request tools or small equipment for field work.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 60,
    },
    {
        "id": "demo-res-material",
        "title": "Material Request",
        "category": "Form",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/forms/material-request",
        "description": "Request materials for an active job.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 70,
    },
    {
        "id": "demo-res-policies",
        "title": "Company Policies",
        "category": "Policy",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/policies",
        "description": "IPS policy library and acknowledgments.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 80,
    },
    {
        "id": "demo-res-sds",
        "title": "SDS / Safety Data Sheets",
        "category": "Safety",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/safety/sds",
        "description": "Search safety data sheets by product.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 90,
    },
    {
        "id": "demo-res-training",
        "title": "Training Documents",
        "category": "Training",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/training",
        "description": "Safety and skills training references.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 100,
    },
    {
        "id": "demo-res-manuals",
        "title": "Equipment Manuals",
        "category": "Equipment Manual",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/equipment-manuals",
        "description": "OEM manuals for common IPS equipment.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 110,
    },
    {
        "id": "demo-res-hr",
        "title": "HR / Payroll Forms",
        "category": "HR",
        "resource_type": "link",
        "url": "https://industrialplantsolution.com/hr-forms",
        "description": "Payroll, benefits, and HR paperwork.",
        "visible_to_roles": "employee,supervisor,admin,project manager",
        "is_active": True,
        "sort_order": 120,
    },
]


@dataclass(frozen=True)
class EmployeeResourcesPage:
    rows: list[dict[str, Any]]
    total_count: int
    page: int
    page_size: int
    categories: list[str]
    is_live: bool
    warning: str | None = None


def _parse_roles(raw: object) -> set[str]:
    text = str(raw or "").strip().lower()
    if not text:
        return set(ROLE_VISIBILITY_OPTIONS)
    parts = {p.strip().replace("_", " ") for p in text.split(",") if p.strip()}
    aliases = {"pm": "project manager", "project_manager": "project manager"}
    return {aliases.get(p, p) for p in parts}


def normalize_resource(row: dict[str, Any]) -> dict[str, Any]:
    delivery = str(row.get("resource_type") or "link").strip().lower()
    if delivery not in {"link", "file"}:
        delivery = "file" if row.get("file_path") else "link"
    category = str(row.get("category") or row.get("resource_category") or "Document").strip() or "Document"
    return {
        "id": str(row.get("id") or ""),
        "title": str(row.get("title") or "").strip(),
        "category": category,
        "resource_type": delivery,
        "url": str(row.get("url") or "").strip(),
        "description": str(row.get("description") or "").strip(),
        "file_name": str(row.get("file_name") or row.get("original_filename") or "").strip(),
        "original_filename": str(row.get("original_filename") or "").strip(),
        "file_path": str(row.get("file_path") or "").strip(),
        "content_type": str(row.get("content_type") or "").strip(),
        "visible_to_roles": str(
            row.get("visible_to_roles") or "employee,supervisor,admin,project manager"
        ).strip(),
        "is_active": row.get("is_active") is not False,
        "sort_order": int(row.get("sort_order") or 0),
        "created_at": str(row.get("created_at") or "")[:19],
        "updated_at": str(row.get("updated_at") or row.get("created_at") or "")[:19],
    }


def resource_visible_to_role(row: dict[str, Any], role: str) -> bool:
    if not row.get("is_active", True):
        return False
    norm = normalize_role(role)
    allowed = _parse_roles(row.get("visible_to_roles"))
    if norm == "admin":
        return True
    return norm in allowed or "all" in allowed


def is_safe_resource_url(url: str) -> bool:
    text = str(url or "").strip()
    if not text:
        return False
    parsed = urlparse(text)
    scheme = str(parsed.scheme or "").lower()
    if not scheme or scheme in _UNSAFE_URL_SCHEMES:
        return False
    return scheme in _SAFE_URL_SCHEMES


def is_safe_direct_link(row: dict[str, Any]) -> bool:
    if str(row.get("resource_type") or "").lower() != "link":
        return False
    url = str(row.get("url") or "").strip()
    return bool(url) and is_safe_resource_url(url)


def _sort_key(row: dict[str, Any]) -> tuple[int, str]:
    return (int(row.get("sort_order") or 0), str(row.get("title") or "").lower())


def _load_catalog_rows() -> tuple[list[dict[str, Any]], bool]:
    from app.services.repository import fetch_list

    rows, used_demo = fetch_list(
        "employee_toolbox_links",
        order_by="sort_order",
        normalize=normalize_resource,
        demo=_DEMO_RESOURCES,
    )
    rows.sort(key=_sort_key)
    return rows, not used_demo


def _apply_search(rows: list[dict[str, Any]], search: str) -> list[dict[str, Any]]:
    q = str(search or "").strip().lower()
    if not q:
        return rows
    out: list[dict[str, Any]] = []
    for row in rows:
        hay = " ".join(
            str(row.get(k) or "") for k in ("title", "description", "category")
        ).lower()
        if q in hay:
            out.append(row)
    return out


def _apply_category_filter(rows: list[dict[str, Any]], categories: list[str] | None) -> list[dict[str, Any]]:
    wanted = [c for c in (categories or []) if str(c or "").strip()]
    if not wanted:
        return rows
    wanted_set = {str(c).strip() for c in wanted}
    return [r for r in rows if str(r.get("category") or "") in wanted_set]


def _apply_status_filter(rows: list[dict[str, Any]], statuses: list[str] | None) -> list[dict[str, Any]]:
    wanted = [s for s in (statuses or []) if str(s or "").strip()]
    if not wanted:
        return rows
    wanted_set = {str(s).strip().lower() for s in wanted}
    out: list[dict[str, Any]] = []
    for row in rows:
        active = bool(row.get("is_active", True))
        label = "active" if active else "inactive"
        if label in wanted_set:
            out.append(row)
    return out


def to_employee_list_row(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": str(row.get("id") or ""),
        "title": str(row.get("title") or ""),
        "category": str(row.get("category") or ""),
        "description": str(row.get("description") or ""),
        "resource_type": str(row.get("resource_type") or "link"),
        "sort_order": int(row.get("sort_order") or 0),
        "updated_at": str(row.get("updated_at") or ""),
    }
    if is_safe_direct_link(row):
        out["url"] = str(row.get("url") or "").strip()
    if str(row.get("resource_type") or "").lower() == "file":
        out["file_name"] = str(row.get("file_name") or "").strip()
    return out


def to_admin_list_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id") or ""),
        "title": str(row.get("title") or ""),
        "category": str(row.get("category") or ""),
        "description": str(row.get("description") or ""),
        "resource_type": str(row.get("resource_type") or "link"),
        "url": str(row.get("url") or ""),
        "file_path": str(row.get("file_path") or ""),
        "file_name": str(row.get("file_name") or ""),
        "visible_to_roles": str(row.get("visible_to_roles") or ""),
        "sort_order": int(row.get("sort_order") or 0),
        "is_active": bool(row.get("is_active", True)),
        "created_at": str(row.get("created_at") or ""),
        "updated_at": str(row.get("updated_at") or ""),
    }


def load_employee_resource_categories(*, role: str, admin: bool = False) -> list[str]:
    version = employee_resources_data_version()
    norm = normalize_role(role)
    cache_key = f"employee_resources:categories:v{version}:role:{norm}:admin:{int(admin)}"

    def _build() -> list[str]:
        from app.perf_debug import perf_span

        with perf_span("employee_resources.categories"):
            raw_rows, _ = _load_catalog_rows()
            if admin:
                scoped = raw_rows
            else:
                scoped = [r for r in raw_rows if resource_visible_to_role(r, role)]
            cats = sorted({str(r.get("category") or "") for r in scoped if r.get("category")})
            return cats

    return page_data_cache_get(cache_key, _build)


def _find_resource_by_id(resource_id: str) -> dict[str, Any] | None:
    rid = str(resource_id or "").strip()
    if not rid:
        return None
    version = employee_resources_data_version()
    cache_key = f"employee_resources:catalog:v{version}"

    def _build() -> dict[str, dict[str, Any]]:
        raw_rows, _ = _load_catalog_rows()
        return {str(r.get("id") or ""): r for r in raw_rows if str(r.get("id") or "")}

    catalog = page_data_cache_get(cache_key, _build)
    return catalog.get(rid)


def get_employee_resource_detail(resource_id: str, *, admin: bool = False) -> dict[str, Any] | None:
    row = _find_resource_by_id(resource_id)
    if not row:
        return None
    if admin:
        return dict(to_admin_list_row(row))
    if not resource_visible_to_role(row, "admin"):
        return None
    return dict(to_admin_list_row(row))


def list_employee_resources_page(
    *,
    role: str,
    search: str = "",
    categories: list[str] | None = None,
    page: int = 1,
    page_size: int = EMPLOYEE_RESOURCES_DEFAULT_PAGE_SIZE,
) -> EmployeeResourcesPage:
    from app.perf_debug import perf_span

    version = employee_resources_data_version()
    norm = normalize_role(role)
    cache_key = (
        f"employee_resources:page:v{version}:role:{norm}:s{search}:c{categories}:"
        f"p{page}:sz{page_size}"
    )

    def _build() -> EmployeeResourcesPage:
        with perf_span("employee_resources.list_query"):
            raw_rows, is_live = _load_catalog_rows()
            visible = [r for r in raw_rows if resource_visible_to_role(r, role)]
            filtered = _apply_category_filter(_apply_search(visible, search), categories)
            filtered.sort(key=_sort_key)
            total = len(filtered)
            pg = max(1, int(page or 1))
            size = max(1, min(200, int(page_size or EMPLOYEE_RESOURCES_DEFAULT_PAGE_SIZE)))
            start = (pg - 1) * size
            page_rows = [to_employee_list_row(dict(r)) for r in filtered[start : start + size]]
            cats = load_employee_resource_categories(role=role, admin=False)
            warning = None if is_live else "Showing sample resources — connect Supabase for live data."
            return EmployeeResourcesPage(
                rows=page_rows,
                total_count=total,
                page=pg,
                page_size=size,
                categories=cats,
                is_live=is_live,
                warning=warning,
            )

    return page_data_cache_get(cache_key, _build)


def list_employee_resources_admin_page(
    *,
    search: str = "",
    categories: list[str] | None = None,
    statuses: list[str] | None = None,
    page: int = 1,
    page_size: int = ADMIN_RESOURCES_DEFAULT_PAGE_SIZE,
) -> EmployeeResourcesPage:
    from app.perf_debug import perf_span

    version = employee_resources_data_version()
    cache_key = (
        f"employee_resources:admin_page:v{version}:s{search}:c{categories}:st{statuses}:"
        f"p{page}:sz{page_size}"
    )

    def _build() -> EmployeeResourcesPage:
        with perf_span("employee_resources.admin.list_query"):
            raw_rows, is_live = _load_catalog_rows()
            filtered = _apply_status_filter(
                _apply_category_filter(_apply_search(raw_rows, search), categories),
                statuses,
            )
            filtered.sort(key=_sort_key)
            total = len(filtered)
            pg = max(1, int(page or 1))
            size = max(1, min(200, int(page_size or ADMIN_RESOURCES_DEFAULT_PAGE_SIZE)))
            start = (pg - 1) * size
            page_rows = [to_admin_list_row(dict(r)) for r in filtered[start : start + size]]
            cats = load_employee_resource_categories(role="admin", admin=True)
            warning = None if is_live else "Showing sample resources — connect Supabase for live data."
            return EmployeeResourcesPage(
                rows=page_rows,
                total_count=total,
                page=pg,
                page_size=size,
                categories=cats,
                is_live=is_live,
                warning=warning,
            )

    return page_data_cache_get(cache_key, _build)


def list_all_employee_resources_admin() -> tuple[list[dict[str, Any]], bool]:
    """Backward-compatible admin listing (full catalog)."""
    raw_rows, is_live = _load_catalog_rows()
    return [to_admin_list_row(r) for r in raw_rows], not is_live


def list_employee_resources(*, role: str) -> tuple[list[dict[str, Any]], bool]:
    """Backward-compatible employee listing (all visible rows)."""
    page = list_employee_resources_page(role=role, page=1, page_size=10_000)
    return page.rows, not page.is_live


def validate_employee_resource_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data = dict(payload or {})
    title = str(data.get("title") or "").strip()
    if not title:
        errors.append("Title is required.")
    category = str(data.get("category") or "").strip()
    if category not in RESOURCE_TYPES:
        errors.append("Choose a valid resource type.")
    resource_type = str(data.get("resource_type") or "link").strip().lower()
    if resource_type not in {"link", "file"}:
        errors.append("Unsupported attachment type.")
    roles_raw = str(data.get("visible_to_roles") or "").strip()
    roles = [r.strip() for r in roles_raw.split(",") if r.strip()]
    if roles:
        allowed = {normalize_role(r) for r in ROLE_VISIBILITY_OPTIONS}
        for role in roles:
            if normalize_role(role) not in allowed and role.lower() != "all":
                errors.append("One or more visibility roles are invalid.")
                break
    if resource_type == "link":
        url = str(data.get("url") or "").strip()
        if not url:
            errors.append("Link resources require a URL.")
        elif not is_safe_resource_url(url):
            errors.append("URL must use a safe scheme (https, http, or mailto).")
    else:
        path = str(data.get("file_path") or "").strip()
        if not path:
            errors.append("File resources require a storage path.")
    sort_order = data.get("sort_order")
    try:
        if int(sort_order) < 0:
            errors.append("Sort order must be zero or greater.")
    except (TypeError, ValueError):
        errors.append("Sort order must be a number.")
    return errors


def save_employee_resource(payload: dict[str, Any], *, row_id: str | None = None) -> ServiceResult:
    from app.services.repository import insert_row, update_row

    errors = validate_employee_resource_payload(payload)
    if errors:
        return ServiceResult(ok=False, error=errors[0])

    data = dict(payload or {})
    roles_raw = str(data.get("visible_to_roles") or "").strip()
    if roles_raw:
        normalized_roles = []
        for part in roles_raw.split(","):
            p = part.strip()
            if p:
                normalized_roles.append(normalize_role(p))
        data["visible_to_roles"] = ",".join(dict.fromkeys(normalized_roles))

    resource_type = str(data.get("resource_type") or "link").strip().lower()
    if resource_type == "file":
        path = str(data.get("file_path") or "").strip()
        data["file_name"] = path.split("/")[-1] if path else ""
        data["url"] = ""
    else:
        data["file_path"] = ""
        data["file_name"] = ""

    if row_id:
        result = update_row("employee_toolbox_links", data, {"id": str(row_id).strip()})
        saved_id = str(row_id).strip()
    else:
        result = insert_row("employee_toolbox_links", data)
        saved_id = ""
        if isinstance(result.data, dict):
            saved_id = str(result.data.get("id") or "")

    if result.ok:
        finalize_employee_resource_write(saved_id or row_id)
    return result


def delete_employee_resource(row_id: str) -> ServiceResult:
    from app.services.repository import delete_row

    rid = str(row_id or "").strip()
    if not rid:
        return ServiceResult(ok=False, error="Missing resource id.")
    result = delete_row("employee_toolbox_links", {"id": rid})
    if result.ok:
        finalize_employee_resource_write(rid)
    return result


def _resolve_signed_url(path: str, *, expires_in: int = 3600) -> str | None:
    from app.db import create_signed_url

    try:
        url = create_signed_url(path, expires_in=expires_in)
    except Exception:
        return None
    text = str(url or "").strip()
    return text or None


def get_employee_resource_open_target(
    resource_id: str,
    *,
    role: str,
    user_id: str = "",
) -> ServiceResult:
    from app.perf_debug import perf_span

    _ = user_id
    rid = str(resource_id or "").strip()
    if not rid:
        return ServiceResult(ok=False, error="Resource not found.")

    row = _find_resource_by_id(rid)
    if not row:
        return ServiceResult(ok=False, error="Resource not found.")
    if not resource_visible_to_role(row, role):
        return ServiceResult(ok=False, error="You do not have access to this resource.")

    delivery = str(row.get("resource_type") or "link").lower()
    with perf_span("employee_resources.open_target"):
        if delivery == "link":
            url = str(row.get("url") or "").strip()
            if not url or not is_safe_resource_url(url):
                return ServiceResult(ok=False, error="This resource link is not available.")
            return ServiceResult(ok=True, data={"url": url, "kind": "direct"})

        path = str(row.get("file_path") or "").strip()
        if not path:
            return ServiceResult(ok=False, error="This resource file is not available.")

        cache_key = f"ips_er_signed_{rid}"
        try:
            import streamlit as st

            cached = st.session_state.get(cache_key)
            if isinstance(cached, dict):
                expires_at = float(cached.get("expires_at") or 0)
                cached_url = str(cached.get("url") or "").strip()
                if cached_url and expires_at > time.time():
                    return ServiceResult(ok=True, data={"url": cached_url, "kind": "signed"})
        except Exception:
            pass

        signed = _resolve_signed_url(path)
        if not signed:
            return ServiceResult(ok=False, error="Could not open this resource.")
        try:
            import streamlit as st

            st.session_state[cache_key] = {
                "url": signed,
                "expires_at": time.time() + 3600 - _SIGNED_URL_TTL_BUFFER,
            }
        except Exception:
            pass
        return ServiceResult(ok=True, data={"url": signed, "kind": "signed"})


def resource_open_url(row: dict[str, Any]) -> str | None:
    """Backward-compatible open URL helper (direct links only; no signing)."""
    if is_safe_direct_link(row):
        return str(row.get("url") or "").strip()
    return None


__all__ = [
    "ADMIN_RESOURCES_DEFAULT_PAGE_SIZE",
    "EMPLOYEE_RESOURCES_DEFAULT_PAGE_SIZE",
    "EmployeeResourcesPage",
    "RESOURCE_TYPES",
    "ROLE_VISIBILITY_OPTIONS",
    "delete_employee_resource",
    "get_employee_resource_detail",
    "get_employee_resource_open_target",
    "invalidate_employee_resources_cache",
    "is_safe_direct_link",
    "is_safe_resource_url",
    "list_all_employee_resources_admin",
    "list_employee_resources",
    "list_employee_resources_admin_page",
    "list_employee_resources_page",
    "load_employee_resource_categories",
    "normalize_resource",
    "resource_open_url",
    "resource_visible_to_role",
    "save_employee_resource",
    "validate_employee_resource_payload",
]
