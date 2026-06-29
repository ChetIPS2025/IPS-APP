"""Job PO / expense CRUD with ledger sync."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

EXPENSE_CATEGORIES: tuple[str, ...] = (
    "Materials",
    "Equipment rental",
    "Subcontractor",
    "Travel",
    "Other",
)

EXPENSE_STATUSES: tuple[str, ...] = ("Open", "Approved", "Rejected")


def _db():
    try:
        import app.db as db
    except ImportError:
        import db  # type: ignore
    return db


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def list_job_expenses(job_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid:
        return []
    try:
        rows = _db().fetch_by_match("job_expenses", {"job_id": jid}, limit=limit) or []
    except Exception:
        return []
    rows.sort(
        key=lambda r: (str(r.get("expense_date") or ""), str(r.get("created_at") or "")),
        reverse=True,
    )
    return rows


def save_job_expense(
    job_id: str,
    ui: dict[str, Any],
    *,
    row_id: str | None = None,
    entered_by: str | None = None,
) -> tuple[bool, str]:
    """Insert or update a job_expenses row and sync the cost ledger."""
    jid = str(job_id or "").strip()
    if not jid:
        return False, "Missing job id."
    amount = round(_safe_float(ui.get("amount")), 2)
    if amount <= 0:
        return False, "Amount must be greater than zero."
    category = str(ui.get("category") or "Other").strip() or "Other"
    status = str(ui.get("status") or "Approved").strip() or "Approved"
    if status not in EXPENSE_STATUSES:
        status = "Approved"
    expense_date = ui.get("expense_date")
    if hasattr(expense_date, "isoformat"):
        expense_date = expense_date.isoformat()[:10]
    else:
        expense_date = str(expense_date or "")[:10] or date.today().isoformat()
    payload: dict[str, Any] = {
        "job_id": jid,
        "expense_date": expense_date,
        "category": category,
        "vendor": str(ui.get("vendor") or "").strip(),
        "po_number": str(ui.get("po_number") or "").strip(),
        "invoice_number": str(ui.get("invoice_number") or "").strip(),
        "description": str(ui.get("description") or "").strip(),
        "amount": amount,
        "status": status,
        "notes": str(ui.get("notes") or "").strip(),
        "updated_at": _utc_now_iso(),
    }
    db = _db()
    saved_id = str(row_id or "").strip()
    try:
        if saved_id:
            db.update_rows("job_expenses", payload, {"id": saved_id})
        else:
            if entered_by:
                payload["entered_by"] = entered_by
            row = db.insert_row("job_expenses", payload)
            saved_id = str((row or {}).get("id") or "").strip()
    except Exception as exc:
        return False, str(exc) or "Could not save expense."
    if not saved_id:
        return False, "Could not save expense."
    try:
        from app.services.job_cost_transaction_service import _safe_sync, sync_job_expense
    except ImportError:
        from services.job_cost_transaction_service import _safe_sync, sync_job_expense  # type: ignore
    _safe_sync(sync_job_expense, saved_id)
    try:
        from app.services.repository import clear_data_cache_for_table
    except ImportError:
        from services.repository import clear_data_cache_for_table  # type: ignore
    clear_data_cache_for_table("job_expenses")
    return True, "Expense saved."


def delete_job_expense(row_id: str) -> tuple[bool, str]:
    xid = str(row_id or "").strip()
    if not xid:
        return False, "Missing expense id."
    db = _db()
    try:
        rows = db.fetch_by_match("job_expenses", {"id": xid}, limit=1) or []
    except Exception:
        rows = []
    try:
        db.delete_rows("job_expenses", {"id": xid})
    except Exception as exc:
        return False, str(exc) or "Could not delete expense."
    try:
        from app.services.job_cost_transaction_service import delete_job_cost_transaction, refresh_job_actual_cost
    except ImportError:
        from services.job_cost_transaction_service import (  # type: ignore
            delete_job_cost_transaction,
            refresh_job_actual_cost,
        )
    delete_job_cost_transaction("job_expense", xid)
    if rows:
        jid = str(rows[0].get("job_id") or "").strip()
        if jid:
            refresh_job_actual_cost(jid)
    try:
        from app.services.repository import clear_data_cache_for_table
    except ImportError:
        from services.repository import clear_data_cache_for_table  # type: ignore
    clear_data_cache_for_table("job_expenses")
    return True, "Expense removed."
