"""Upsert core workforce employees by employee_number (no login accounts)."""

from __future__ import annotations

from typing import Any

try:
    from app.data.employee_seed import CORE_EMPLOYEE_SEEDS
    from app.services.repository import (
        ServiceResult,
        clear_all_data_caches,
        fetch_rows,
        insert_row,
        table_column_names,
        update_row,
    )
except ImportError:
    from data.employee_seed import CORE_EMPLOYEE_SEEDS  # type: ignore
    from services.repository import (  # type: ignore
        ServiceResult,
        clear_all_data_caches,
        fetch_rows,
        insert_row,
        table_column_names,
        update_row,
    )


def _normalize_number(val: object) -> str:
    return str(val or "").strip().upper()


def _seed_row_to_payload(row: dict[str, Any], cols: frozenset[str]) -> dict[str, Any]:
    name = str(row.get("full_name") or row.get("name") or "").strip()
    status = str(row.get("status") or "Active").strip() or "Active"
    active = status.lower() in {"active", "true", "1"}
    payload: dict[str, Any] = {
        "name": name,
        "email": str(row.get("email") or "").strip(),
        "phone": str(row.get("phone") or "").strip(),
        "role": str(row.get("role") or row.get("position") or "Employee").strip(),
        "position": str(row.get("position") or row.get("role") or "").strip(),
        "trade": str(row.get("trade") or "").strip(),
        "hire_date": str(row.get("hire_date") or "").strip() or None,
        "employee_number": str(row.get("employee_number") or "").strip(),
        "department": str(row.get("department") or "Field Operations").strip(),
        "status": status,
        "is_active": active,
        "is_employee": bool(row.get("is_employee", True)),
    }
    if not cols:
        return payload
    return {k: v for k, v in payload.items() if k in cols}


def find_employee_by_number(employee_number: str) -> dict[str, Any] | None:
    num = _normalize_number(employee_number)
    if not num:
        return None
    rows, _ = fetch_rows("employees", limit=10000, order_by="name")
    for row in rows:
        if _normalize_number(row.get("employee_number")) == num:
            return row
    return None


def find_employee_by_email(email: str) -> dict[str, Any] | None:
    em = str(email or "").strip().lower()
    if not em or em in {"—", "-", "none"}:
        return None
    rows, _ = fetch_rows("employees", limit=10000, order_by="name")
    for row in rows:
        if str(row.get("email") or "").strip().lower() == em:
            return row
    return None


def _clean_employee_number(raw: object) -> str:
    num = str(raw or "").strip()
    if not num or num in {"—", "-", "none", "null"}:
        return ""
    return num


def upsert_employee_seed(row: dict[str, Any]) -> ServiceResult:
    num = _clean_employee_number(row.get("employee_number"))
    email = str(row.get("email") or "").strip()
    if not num and not email:
        return ServiceResult(ok=False, error="employee_number or email is required for seed upsert.")
    cols = table_column_names("employees")
    payload = _seed_row_to_payload(row, cols)
    if not payload.get("name"):
        return ServiceResult(ok=False, error="Employee name is required.")
    payload["employee_number"] = num or None

    existing = find_employee_by_number(num) if num else None
    if not existing and email:
        existing = find_employee_by_email(email)
    if existing and existing.get("id"):
        result = update_row("employees", payload, {"id": str(existing["id"])})
    else:
        result = insert_row("employees", payload)
    return result


def ensure_core_employee_seed(*, force: bool = False) -> ServiceResult:
    """Insert or update IPS workforce employees; match by employee_number, else email."""
    del force  # always upsert — idempotent by employee_number
    if not CORE_EMPLOYEE_SEEDS:
        return ServiceResult(ok=True, data={"updated": 0})

    updated = 0
    errors: list[str] = []
    for row in CORE_EMPLOYEE_SEEDS:
        result = upsert_employee_seed(row)
        if result.ok:
            updated += 1
        elif result.error:
            errors.append(str(result.error))

    if errors and updated == 0:
        return ServiceResult(ok=False, error="; ".join(errors[:3]))
    clear_all_data_caches()
    return ServiceResult(ok=True, data={"updated": updated, "errors": errors})
