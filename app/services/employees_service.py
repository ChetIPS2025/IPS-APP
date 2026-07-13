"""
Employees / users module — profiles and HR records.

Schema assumptions: ``employees`` with name, email, role, department, phone, is_active, is_employee.
"""

from __future__ import annotations

from typing import Any

from app.services.certification_attachments_service import (
    cert_has_attachment,
    get_certification_attachment_url,
    upload_certification_attachment,
)
from app.services.phase2_modules_service import (
    delete_certification,
    delete_employee,
    list_all_certifications,
    list_certifications,
    list_employees,
    normalize_cert,
    normalize_employee,
    save_certification,
    save_employee,
)
from app.services.repository import ServiceResult, clear_data_cache_for_table

__all__ = [
    "clear_certifications_cache",
    "create_employee_certification",
    "delete_certification",
    "delete_employee_certification",
    "delete_employee",
    "get_certification_attachment_url",
    "get_employee_certifications",
    "list_all_certifications",
    "list_certifications",
    "list_employees",
    "normalize_cert",
    "normalize_employee",
    "save_certification",
    "save_employee",
    "update_employee_certification",
    "upload_certification_attachment",
]


def clear_certifications_cache() -> None:
    clear_data_cache_for_table("employee_certifications")


def get_employee_certifications(employee_id: str | None = None) -> list[dict[str, Any]]:
    from app.pages._core._data import _DEMO_CERTIFICATIONS
    if employee_id:
        rows, _ = list_certifications(str(employee_id), demo=list(_DEMO_CERTIFICATIONS))
        return rows
    employees, _ = list_employees(demo=[])
    rows, _ = list_all_certifications(demo=list(_DEMO_CERTIFICATIONS), employees=employees)
    return rows


def create_employee_certification(data: dict[str, Any]) -> ServiceResult:
    return save_certification(data)


def update_employee_certification(cert_id: str, data: dict[str, Any]) -> ServiceResult:
    return save_certification(data, row_id=str(cert_id or "").strip())


def delete_employee_certification(cert_id: str) -> ServiceResult:
    return delete_certification(str(cert_id or "").strip())
