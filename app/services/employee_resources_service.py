"""Employee toolbox / resources — CRUD and role-filtered listing."""

from __future__ import annotations

from typing import Any

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
    try:
        from app.utils.permissions import normalize_role
    except ImportError:
        from utils.permissions import normalize_role  # type: ignore

    norm = normalize_role(role)
    allowed = _parse_roles(row.get("visible_to_roles"))
    if norm == "admin":
        return True
    return norm in allowed or "all" in allowed


def list_all_employee_resources_admin() -> tuple[list[dict[str, Any]], bool]:
    try:
        from app.services.repository import fetch_list
    except ImportError:
        from services.repository import fetch_list  # type: ignore

    rows, used_demo = fetch_list(
        "employee_toolbox_links",
        order_by="sort_order",
        normalize=normalize_resource,
        demo=_DEMO_RESOURCES,
    )
    rows.sort(key=lambda r: (int(r.get("sort_order") or 0), str(r.get("title") or "")))
    return rows, used_demo


def list_employee_resources(*, role: str) -> tuple[list[dict[str, Any]], bool]:
    try:
        from app.services.repository import fetch_list
    except ImportError:
        from services.repository import fetch_list  # type: ignore

    rows, used_demo = fetch_list(
        "employee_toolbox_links",
        order_by="sort_order",
        normalize=normalize_resource,
        demo=_DEMO_RESOURCES,
    )
    visible = [r for r in rows if resource_visible_to_role(r, role)]
    visible.sort(key=lambda r: (int(r.get("sort_order") or 0), str(r.get("title") or "")))
    return visible, used_demo


def save_employee_resource(payload: dict[str, Any], *, row_id: str | None = None):
    try:
        from app.services.repository import insert_row, update_row, clear_data_cache_for_table
    except ImportError:
        from services.repository import insert_row, update_row, clear_data_cache_for_table  # type: ignore

    data = dict(payload or {})
    if row_id:
        result = update_row("employee_toolbox_links", data, {"id": str(row_id).strip()})
    else:
        result = insert_row("employee_toolbox_links", data)
    if result.ok:
        clear_data_cache_for_table("employee_toolbox_links")
    return result


def delete_employee_resource(row_id: str):
    try:
        from app.services.repository import delete_row, clear_data_cache_for_table
    except ImportError:
        from services.repository import delete_row, clear_data_cache_for_table  # type: ignore

    result = delete_row("employee_toolbox_links", {"id": str(row_id or "").strip()})
    if result.ok:
        clear_data_cache_for_table("employee_toolbox_links")
    return result


def resource_open_url(row: dict[str, Any]) -> str | None:
    url = str(row.get("url") or "").strip()
    if url:
        return url
    path = str(row.get("file_path") or "").strip()
    if not path:
        return None
    try:
        from app.db import create_signed_url
    except ImportError:
        from db import create_signed_url  # type: ignore
    try:
        return create_signed_url(path, expires_in=3600)
    except Exception:
        return None
