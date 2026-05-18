"""Read-only dashboard data access (no Streamlit UI)."""

from __future__ import annotations

from typing import Any

try:
    from app.data_cache import fetch_table_for_session
except ImportError:
    from data_cache import fetch_table_for_session  # type: ignore


def _fetch(
    table: str,
    *,
    session_key: str,
    use_admin: bool,
    limit: int,
    order_by: str | None,
) -> list[dict[str, Any]]:
    try:
        return fetch_table_for_session(
            table,
            session_key=session_key,
            limit=limit,
            order_by=order_by,
            use_admin=use_admin,
        )
    except Exception:
        return []


def fetch_jobs(session_key: str, *, use_admin: bool, limit: int = 5000) -> list[dict]:
    return _fetch("jobs", session_key=session_key, use_admin=use_admin, limit=limit, order_by="job_number")


def fetch_estimates(session_key: str, *, use_admin: bool, limit: int = 5000) -> list[dict]:
    return _fetch("estimates", session_key=session_key, use_admin=use_admin, limit=limit, order_by="quote_number")


def fetch_employees(session_key: str, *, use_admin: bool, limit: int = 5000) -> list[dict]:
    return _fetch("employees", session_key=session_key, use_admin=use_admin, limit=limit, order_by="name")


def fetch_assets(session_key: str, *, use_admin: bool, limit: int = 5000) -> list[dict]:
    return _fetch("assets", session_key=session_key, use_admin=use_admin, limit=limit, order_by="asset_name")


def fetch_inventory(session_key: str, *, use_admin: bool, limit: int = 12000) -> list[dict]:
    return _fetch("inventory_items", session_key=session_key, use_admin=use_admin, limit=limit, order_by="item_name")


def fetch_todos(session_key: str, *, use_admin: bool, limit: int = 2000) -> list[dict]:
    return _fetch("todos", session_key=session_key, use_admin=use_admin, limit=limit, order_by="created_at")


def fetch_job_tasks(session_key: str, *, use_admin: bool, limit: int = 12000) -> list[dict]:
    return _fetch("job_tasks", session_key=session_key, use_admin=use_admin, limit=limit, order_by="planned_date")


def fetch_time_entries(session_key: str, *, use_admin: bool, limit: int = 8000) -> list[dict]:
    return _fetch("time_entries", session_key=session_key, use_admin=use_admin, limit=limit, order_by="work_date")


def fetch_po_expenses(session_key: str, *, use_admin: bool, limit: int = 3000) -> list[dict]:
    return _fetch("po_expenses", session_key=session_key, use_admin=use_admin, limit=limit, order_by="created_at")


def fetch_job_expenses(session_key: str, *, use_admin: bool, limit: int = 10000) -> list[dict]:
    """Primary expense/invoice lines (PO / Expenses page)."""
    return _fetch("job_expenses", session_key=session_key, use_admin=use_admin, limit=limit, order_by="expense_date")


def fetch_customers(session_key: str, *, use_admin: bool, limit: int = 5000) -> list[dict]:
    return _fetch("customers", session_key=session_key, use_admin=use_admin, limit=limit, order_by="customer_name")


def fetch_company_updates(session_key: str, *, use_admin: bool, limit: int = 500) -> list[dict]:
    return _fetch("company_updates", session_key=session_key, use_admin=use_admin, limit=limit, order_by="created_at")


def fetch_company_update_reads(session_key: str, *, use_admin: bool, limit: int = 5000) -> list[dict]:
    return _fetch("company_update_reads", session_key=session_key, use_admin=use_admin, limit=limit, order_by=None)


def fetch_profiles(session_key: str, *, use_admin: bool, limit: int = 5000) -> list[dict]:
    return _fetch("profiles", session_key=session_key, use_admin=use_admin, limit=limit, order_by="email")


def fetch_daily_work_packages(session_key: str, *, use_admin: bool, limit: int = 12000) -> list[dict]:
    return _fetch("daily_work_packages", session_key=session_key, use_admin=use_admin, limit=limit, order_by="work_date")


def fetch_daily_work_package_tasks(session_key: str, *, use_admin: bool, limit: int = 24000) -> list[dict]:
    return _fetch(
        "daily_work_package_tasks",
        session_key=session_key,
        use_admin=use_admin,
        limit=limit,
        order_by=None,
    )


def fetch_supervisor_daily_execution(session_key: str, *, use_admin: bool, limit: int = 12000) -> list[dict]:
    return _fetch(
        "supervisor_daily_execution",
        session_key=session_key,
        use_admin=use_admin,
        limit=limit,
        order_by="updated_at",
    )


def fetch_task_photos_merged(session_key: str, *, use_admin: bool) -> list[dict[str, Any]]:
    tp_new = _fetch("task_photos", session_key=session_key, use_admin=use_admin, limit=12000, order_by="created_at")
    legacy = _fetch("job_task_photos", session_key=session_key, use_admin=use_admin, limit=12000, order_by="created_at")
    rows: list[dict[str, Any]] = []
    for r in tp_new or []:
        if isinstance(r, dict):
            rows.append({**r, "storage_path": str(r.get("file_url") or r.get("storage_path") or "")})
    rows.extend([x for x in (legacy or []) if isinstance(x, dict)])
    return rows


def fetch_asset_kit_items(session_key: str, *, use_admin: bool, limit: int = 12000) -> list[dict]:
    return _fetch("asset_kit_items", session_key=session_key, use_admin=use_admin, limit=limit, order_by=None)


def fetch_asset_kit_replacements(session_key: str, *, use_admin: bool, limit: int = 12000) -> list[dict]:
    return _fetch(
        "asset_kit_replacements",
        session_key=session_key,
        use_admin=use_admin,
        limit=limit,
        order_by="replacement_date",
    )
