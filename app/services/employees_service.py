"""
Employees / users module — profiles and HR records.

Schema assumptions: ``employees`` with name, email, role, department, phone, is_active, is_employee.
"""

from __future__ import annotations

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

__all__ = [
    "delete_certification",
    "delete_employee",
    "list_all_certifications",
    "list_certifications",
    "list_employees",
    "normalize_cert",
    "normalize_employee",
    "save_certification",
    "save_employee",
]
