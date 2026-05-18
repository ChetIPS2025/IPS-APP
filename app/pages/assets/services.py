"""Business-logic layer for the Assets module.

All database writes happen here.  The db.py helpers (insert_row_admin,
update_rows_admin, delete_rows_admin) automatically clear the read-cache
after every mutation, so callers do not need separate cache-busting calls.
"""
from __future__ import annotations

from typing import Any

try:
    from app.db import (
        delete_rows_admin,
        fetch_by_match_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from app.services.asset_service import optional_numeric
except ImportError:
    from db import (  # type: ignore
        delete_rows_admin,
        fetch_by_match_admin,
        insert_row_admin,
        update_rows_admin,
    )
    from services.asset_service import optional_numeric  # type: ignore

try:
    from app.pages.assets.utils import (
        make_unique_asset_name,
        next_asset_id,
        safe_date_value,
    )
except ImportError:
    from pages.assets.utils import (  # type: ignore
        make_unique_asset_name,
        next_asset_id,
        safe_date_value,
    )


# ---------------------------------------------------------------------------
# Asset CRUD
# ---------------------------------------------------------------------------

def create_asset(form: dict[str, Any], existing_assets: list[dict]) -> str:
    """Insert a new asset row and return the generated asset_id string.

    *form* keys mirror the ``assets`` table column names.  ``asset_id`` and
    ``asset_name`` are validated / made unique before insertion.
    """
    final_id = str(form.get("asset_id") or "").strip() or next_asset_id(existing_assets)
    final_name = make_unique_asset_name(
        str(form.get("asset_name") or "").strip() or "Unnamed Asset",
        existing_assets,
    )

    payload: dict[str, Any] = {
        "asset_id": final_id,
        "asset_name": final_name,
        "asset_type": str(form.get("asset_type") or "").strip(),
        "category": str(form.get("category") or "").strip(),
        "subcategory": str(form.get("subcategory") or "").strip(),
        "serial_number": str(form.get("serial_number") or "").strip(),
        "manufacturer": str(form.get("manufacturer") or "").strip(),
        "model": str(form.get("model") or "").strip(),
        "assigned_employee": str(form.get("assigned_employee") or "").strip(),
        "assigned_job_id": form.get("assigned_job_id"),
        "location": str(form.get("location") or "").strip(),
        "status": str(form.get("status") or "Available").strip(),
        "purchase_date": safe_date_value(form.get("purchase_date")),
        "inspection_due_date": safe_date_value(form.get("inspection_due_date")),
        "maintenance_due_date": safe_date_value(form.get("maintenance_due_date")),
        "notes": str(form.get("notes") or "").strip(),
        "is_active": bool(form.get("is_active", True)),
        "is_rental": bool(form.get("is_rental", False)),
        "rental_notes": str(form.get("rental_notes") or "").strip(),
    }
    if bool(form.get("is_rental")):
        payload["rental_daily_rate"] = optional_numeric(form.get("rental_daily_rate"))
        payload["rental_weekly_rate"] = optional_numeric(form.get("rental_weekly_rate"))
        payload["rental_monthly_rate"] = optional_numeric(form.get("rental_monthly_rate"))

    insert_row_admin("assets", payload)
    return final_id


def update_asset(row_id: str, form: dict[str, Any]) -> None:
    """Persist edited asset fields for the row identified by UUID *row_id*."""
    payload: dict[str, Any] = {
        "asset_id": str(form.get("asset_id") or "").strip(),
        "asset_name": str(form.get("asset_name") or "").strip(),
        "asset_type": str(form.get("asset_type") or "").strip(),
        "category": str(form.get("category") or "").strip(),
        "subcategory": str(form.get("subcategory") or "").strip(),
        "serial_number": str(form.get("serial_number") or "").strip(),
        "manufacturer": str(form.get("manufacturer") or "").strip(),
        "model": str(form.get("model") or "").strip(),
        "assigned_employee": str(form.get("assigned_employee") or "").strip(),
        "assigned_job_id": form.get("assigned_job_id"),
        "location": str(form.get("location") or "").strip(),
        "status": str(form.get("status") or "Available").strip(),
        "purchase_date": safe_date_value(form.get("purchase_date")),
        "inspection_due_date": safe_date_value(form.get("inspection_due_date")),
        "maintenance_due_date": safe_date_value(form.get("maintenance_due_date")),
        "notes": str(form.get("notes") or "").strip(),
        "is_active": bool(form.get("is_active", True)),
        "is_rental": bool(form.get("is_rental", False)),
        "rental_notes": str(form.get("rental_notes") or "").strip(),
    }
    if bool(form.get("is_rental")):
        payload["rental_daily_rate"] = optional_numeric(form.get("rental_daily_rate"))
        payload["rental_weekly_rate"] = optional_numeric(form.get("rental_weekly_rate"))
        payload["rental_monthly_rate"] = optional_numeric(form.get("rental_monthly_rate"))
    update_rows_admin("assets", payload, {"id": row_id})


def deactivate_asset(row_id: str) -> None:
    """Mark asset as inactive (used when history rows exist and hard-delete is unsafe)."""
    update_rows_admin("assets", {"is_active": False, "status": "Inactive"}, {"id": row_id})


def delete_asset(row_id: str) -> None:
    """Hard-delete an asset row. Caller must check dependencies first."""
    delete_rows_admin("assets", {"id": row_id})


# ---------------------------------------------------------------------------
# Dependency check (before delete / deactivate)
# ---------------------------------------------------------------------------

def check_asset_dependencies(row_id: str) -> tuple[bool, bool]:
    """Return (blocked_checked_out, has_history).

    blocked_checked_out
        True when a checkout tool is currently checked out — do not delete.
    has_history
        True when history tables reference this asset — deactivate instead.
    """
    aid = str(row_id or "").strip()
    if not aid:
        return False, False

    recs = fetch_by_match_admin("assets", {"id": aid}, limit=1)
    asset = recs[0] if recs else {}

    try:
        from app.pages.assets.utils import is_checkout_tool_flag
    except ImportError:
        from pages.assets.utils import is_checkout_tool_flag  # type: ignore
    is_tool = is_checkout_tool_flag(asset.get("is_checkout_item"))
    stt = str(asset.get("status") or "").strip()
    holder = str(asset.get("current_holder_employee_id") or "").strip()
    if is_tool and (stt == "Checked Out" or holder):
        return True, True

    def _has(table: str, match: dict) -> bool:
        try:
            return bool(fetch_by_match_admin(table, match, columns="id", limit=1))
        except Exception:
            return False

    has_history = (
        _has("tool_transactions", {"tool_id": aid})
        or _has("asset_expenses", {"asset_id": aid})
        or _has("asset_kit_items", {"parent_asset_id": aid})
        or _has("asset_kit_replacements", {"parent_asset_id": aid})
    )
    return False, has_history
