"""Unified job cost transactions — auto-sync from labor, inventory, equipment, and purchasing."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

_LOG = logging.getLogger(__name__)

_TABLE = "job_cost_transactions"

COST_LABOR = "labor"
COST_MATERIAL = "material"
COST_EQUIPMENT = "equipment"
COST_SUBCONTRACT = "subcontract"
COST_RENTAL = "rental"
COST_OTHER = "other"

SOURCE_TIME_ENTRY = "time_entry"
SOURCE_LABOR_TIME = "labor_time"  # display alias for time_entry
SOURCE_TIMEKEEPING_DAY = "timekeeping_day"
SOURCE_JOB_MATERIAL = "job_material"
SOURCE_INVENTORY_SCAN = "inventory_scan"  # display alias for job_material scans
SOURCE_JOB_EQUIPMENT = "job_equipment"
SOURCE_JOB_EXPENSE = "job_expense"
SOURCE_PURCHASE = "purchase"  # display alias for job_expense
SOURCE_ASSET_ASSIGNMENT = "asset_assignment"
SOURCE_EQUIPMENT_ASSIGNMENT = "equipment_assignment"  # display alias
SOURCE_MANUAL_ADJUSTMENT = "manual_adjustment"
SOURCE_ESTIMATE = "estimate"


def _db():
    try:
        import app.db as db
    except ImportError:
        import db  # type: ignore
    return db


def _safe_float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _job_number_for(job_id: str) -> str:
    jid = str(job_id or "").strip()
    if not jid:
        return ""
    try:
        from app.services.job_service import job_display_primary
    except ImportError:
        from services.job_service import job_display_primary  # type: ignore
    try:
        rows = _db().fetch_by_match("jobs", {"id": jid}, limit=1) or []
    except Exception:
        return ""
    if not rows:
        return ""
    return str(job_display_primary(rows[0]) or "").strip()


def _employee_by_id(employee_id: str | None) -> dict[str, Any] | None:
    eid = str(employee_id or "").strip()
    if not eid:
        return None
    try:
        rows = _db().fetch_by_match("employees", {"id": eid}, limit=1) or []
        return rows[0] if rows else None
    except Exception:
        return None


def _expense_cost_category(category: str) -> str:
    cat = str(category or "").strip().lower()
    if cat == "materials":
        return COST_MATERIAL
    if cat in {"equipment rental", "equipment"}:
        return COST_EQUIPMENT
    if cat == "subcontractor":
        return COST_SUBCONTRACT
    return COST_OTHER


def _expense_source_label(category: str) -> str:
    cat = str(category or "").strip()
    if cat == "Materials":
        return "Purchase order / expense"
    return f"PO / expense ({cat or 'Other'})"


def equipment_internal_rate(asset: dict[str, Any] | None) -> tuple[float, str, float]:
    """
    Return (rate, rate_unit, default_quantity) for internal equipment costing.
    Supports daily, weekly, and monthly internal rates.
    """
    if not asset:
        return 0.0, "day", 1.0
    unit = str(asset.get("rental_rate_unit") or asset.get("rate_unit") or "day").strip().lower()
    daily = _safe_float(asset.get("daily_rate") or asset.get("rental_daily_rate"))
    weekly = _safe_float(asset.get("weekly_rate"))
    monthly = _safe_float(asset.get("monthly_rate"))
    hourly = _safe_float(asset.get("hourly_rate"))
    if unit in {"week", "weekly"} and weekly > 0:
        return weekly, "week", 1.0
    if unit in {"month", "monthly"} and monthly > 0:
        return monthly, "month", 1.0
    if unit in {"hour", "hourly"} and hourly > 0:
        return hourly, "hour", 8.0
    if daily > 0:
        return daily, "day", 1.0
    if weekly > 0:
        return weekly, "week", 1.0
    if hourly > 0:
        return hourly, "hour", 8.0
    if monthly > 0:
        return monthly, "month", 1.0
    return 0.0, "day", 1.0


def upsert_job_cost_transaction(payload: dict[str, Any]) -> bool:
    """Idempotent upsert keyed by (source_type, source_id). Returns False if table missing."""
    source_type = str(payload.get("source_type") or "").strip()
    source_id = str(payload.get("source_id") or "").strip()
    job_id = str(payload.get("job_id") or "").strip()
    if not source_type or not source_id or not job_id:
        return False
    total = round(_safe_float(payload.get("total_cost")), 2)
    if total <= 0:
        delete_job_cost_transaction(source_type, source_id)
        return True
    txn_date = str(payload.get("transaction_date") or "")[:10] or date.today().isoformat()
    body: dict[str, Any] = {
        "job_id": job_id,
        "transaction_date": txn_date,
        "cost_category": str(payload.get("cost_category") or COST_OTHER).strip(),
        "source_type": source_type,
        "source_id": source_id,
        "employee_id": payload.get("employee_id") or None,
        "asset_id": payload.get("asset_id") or None,
        "inventory_item_id": payload.get("inventory_item_id") or None,
        "item_name": str(payload.get("item_name") or payload.get("description") or "")[:500],
        "description": str(payload.get("description") or payload.get("item_name") or "")[:500],
        "quantity": round(_safe_float(payload.get("quantity")), 4),
        "unit_cost": round(_safe_float(payload.get("unit_cost")), 4),
        "total_cost": total,
        "job_number": str(payload.get("job_number") or _job_number_for(job_id))[:80],
        "notes": str(payload.get("notes") or "")[:2000],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.get("created_by"):
        body["created_by"] = payload.get("created_by")
    db = _db()
    try:
        existing = db.fetch_by_match(_TABLE, {"source_type": source_type, "source_id": source_id}, limit=1) or []
        if existing:
            db.update_rows(_TABLE, body, {"id": existing[0]["id"]})
        else:
            db.insert_row(_TABLE, body)
        return True
    except Exception as exc:
        err = str(exc).lower()
        if "relation" in err and "does not exist" in err:
            _LOG.debug("job_cost_transactions table not present: %s", exc)
            return False
        _LOG.warning("upsert_job_cost_transaction failed: %s", exc)
        return False


def delete_job_cost_transaction(source_type: str, source_id: str) -> None:
    st = str(source_type or "").strip()
    sid = str(source_id or "").strip()
    if not st or not sid:
        return
    try:
        _db().delete_rows(_TABLE, {"source_type": st, "source_id": sid})
    except Exception as exc:
        _LOG.debug("delete_job_cost_transaction: %s", exc)


def _safe_sync(fn, *args, **kwargs) -> None:
    try:
        fn(*args, **kwargs)
    except Exception as exc:
        _LOG.warning("job cost sync skipped: %s", exc)


def sync_time_entry(entry: dict[str, Any] | str) -> None:
    """Create/update labor cost from a time_entries row using burdened rates."""
    if isinstance(entry, str):
        rows = _db().fetch_by_match("time_entries", {"id": entry}, limit=1) or []
        if not rows:
            return
        entry = rows[0]
    eid = str(entry.get("id") or "").strip()
    job_id = str(entry.get("job_id") or "").strip()
    if not eid or not job_id:
        delete_job_cost_transaction(SOURCE_TIME_ENTRY, eid)
        return
    hours = _safe_float(entry.get("hours"))
    if hours <= 0:
        delete_job_cost_transaction(SOURCE_TIME_ENTRY, eid)
        return
    emp = _employee_by_id(str(entry.get("employee_id") or ""))
    try:
        from app.services.employee_labor import time_entry_burdened_cost
    except ImportError:
        from services.employee_labor import time_entry_burdened_cost  # type: ignore
    unit_cost, total = time_entry_burdened_cost(entry, emp)
    upsert_job_cost_transaction(
        {
            "job_id": job_id,
            "transaction_date": str(entry.get("work_date") or "")[:10] or date.today().isoformat(),
            "cost_category": COST_LABOR,
            "source_type": SOURCE_TIME_ENTRY,
            "source_id": eid,
            "employee_id": entry.get("employee_id"),
            "item_name": str(entry.get("time_type") or "ST").strip() or "ST",
            "quantity": hours,
            "unit_cost": unit_cost,
            "total_cost": total,
            "notes": str(entry.get("notes") or "")[:500],
        }
    )


def sync_timekeeping_day(row: dict[str, Any] | str) -> None:
    """Labor cost from employee_timekeeping_days (weekly timekeeping allocations)."""
    if isinstance(row, str):
        rows = _db().fetch_by_match("employee_timekeeping_days", {"id": row}, limit=1) or []
        if not rows:
            return
        row = rows[0]
    day_id = str(row.get("id") or "").strip()
    job_id = str(row.get("job_id") or "").strip()
    if not day_id:
        return
    if not job_id:
        delete_job_cost_transaction(SOURCE_TIMEKEEPING_DAY, day_id)
        return
    st_h = _safe_float(row.get("st_hours"))
    ot_h = _safe_float(row.get("ot_hours"))
    dt_h = _safe_float(row.get("dt_hours"))
    total_hours = st_h + ot_h + dt_h
    if total_hours <= 0:
        delete_job_cost_transaction(SOURCE_TIMEKEEPING_DAY, day_id)
        return
    emp = _employee_by_id(str(row.get("employee_id") or ""))
    try:
        from app.services.employee_labor import compute_burdened_labor_cost
    except ImportError:
        from services.employee_labor import compute_burdened_labor_cost  # type: ignore
    total = compute_burdened_labor_cost(emp, st_h, ot_h, dt_h)
    unit_cost = total / total_hours if total_hours > 0 else 0.0
    upsert_job_cost_transaction(
        {
            "job_id": job_id,
            "transaction_date": str(row.get("work_date") or "")[:10] or date.today().isoformat(),
            "cost_category": COST_LABOR,
            "source_type": SOURCE_TIMEKEEPING_DAY,
            "source_id": day_id,
            "employee_id": row.get("employee_id"),
            "item_name": "Labor (ST/OT/DT)",
            "quantity": total_hours,
            "unit_cost": unit_cost,
            "total_cost": total,
            "notes": str(row.get("notes") or "")[:500],
        }
    )


def sync_job_material(row: dict[str, Any] | str) -> None:
    if isinstance(row, str):
        rows = _db().fetch_by_match("job_materials", {"id": row}, limit=1) or []
        if not rows:
            return
        row = rows[0]
    mid = str(row.get("id") or "").strip()
    job_id = str(row.get("job_id") or "").strip()
    if not mid or not job_id:
        return
    qty = _safe_float(row.get("quantity") if row.get("quantity") is not None else row.get("qty"))
    unit = _safe_float(row.get("unit_cost"))
    total = _safe_float(row.get("line_total") or row.get("total_cost"))
    if total <= 0 and qty > 0 and unit > 0:
        total = round(qty * unit, 2)
    if total <= 0:
        delete_job_cost_transaction(SOURCE_JOB_MATERIAL, mid)
        return
    usage = str(row.get("usage_source") or "").strip().lower()
    source_label = "Inventory scan" if usage in {"qr_scan", "inventory_scan", "scan"} else "Job material"
    txn_date = str(row.get("used_at") or row.get("created_at") or "")[:10] or date.today().isoformat()
    item_name = str(row.get("item_name") or row.get("material_name") or "Material")[:500]
    upsert_job_cost_transaction(
        {
            "job_id": job_id,
            "transaction_date": txn_date,
            "cost_category": COST_MATERIAL,
            "source_type": SOURCE_JOB_MATERIAL,
            "source_id": mid,
            "employee_id": row.get("employee_id"),
            "inventory_item_id": row.get("inventory_item_id") or row.get("inventory_id"),
            "item_name": item_name,
            "description": item_name,
            "quantity": qty,
            "unit_cost": unit,
            "total_cost": total,
            "notes": source_label,
        }
    )


def sync_job_equipment(row: dict[str, Any] | str) -> None:
    if isinstance(row, str):
        rows = _db().fetch_by_match("job_equipment", {"id": row}, limit=1) or []
        if not rows:
            return
        row = rows[0]
    eid = str(row.get("id") or "").strip()
    job_id = str(row.get("job_id") or "").strip()
    if not eid or not job_id:
        return
    total = _safe_float(row.get("line_total") or row.get("total_cost"))
    if total <= 0:
        days = _safe_float(row.get("usage_days"))
        hours = _safe_float(row.get("usage_hours"))
        total = days * _safe_float(row.get("rate_per_day")) + hours * _safe_float(row.get("rate_per_hour"))
    if total <= 0:
        delete_job_cost_transaction(SOURCE_JOB_EQUIPMENT, eid)
        return
    qty = _safe_float(row.get("usage_days") or row.get("usage_hours") or row.get("qty") or 1)
    unit = total / qty if qty > 0 else total
    txn_date = str(row.get("created_at") or "")[:10] or date.today().isoformat()
    equip_name = str(row.get("asset_label") or row.get("equipment_name") or "Equipment")[:500]
    upsert_job_cost_transaction(
        {
            "job_id": job_id,
            "transaction_date": txn_date,
            "cost_category": COST_EQUIPMENT,
            "source_type": SOURCE_JOB_EQUIPMENT,
            "source_id": eid,
            "asset_id": row.get("asset_id"),
            "item_name": equip_name,
            "description": equip_name,
            "quantity": qty,
            "unit_cost": unit,
            "total_cost": round(total, 2),
            "notes": str(row.get("notes") or "")[:500],
        }
    )


def sync_job_expense(row: dict[str, Any] | str) -> None:
    if isinstance(row, str):
        rows = _db().fetch_by_match("job_expenses", {"id": row}, limit=1) or []
        if not rows:
            return
        row = rows[0]
    xid = str(row.get("id") or "").strip()
    job_id = str(row.get("job_id") or "").strip()
    if not xid:
        return
    status = str(row.get("status") or "").strip()
    if not job_id or status in {"Rejected", "Open"}:
        delete_job_cost_transaction(SOURCE_JOB_EXPENSE, xid)
        return
    amount = _safe_float(row.get("amount"))
    if amount <= 0:
        delete_job_cost_transaction(SOURCE_JOB_EXPENSE, xid)
        return
    category = str(row.get("category") or "")
    upsert_job_cost_transaction(
        {
            "job_id": job_id,
            "transaction_date": str(row.get("expense_date") or "")[:10] or date.today().isoformat(),
            "cost_category": _expense_cost_category(category),
            "source_type": SOURCE_JOB_EXPENSE,
            "source_id": xid,
            "item_name": str(row.get("description") or row.get("vendor") or category or "Expense")[:500],
            "quantity": 1.0,
            "unit_cost": amount,
            "total_cost": round(amount, 2),
            "notes": _expense_source_label(category),
        }
    )


def sync_asset_assignment_to_job(
    *,
    assignment_id: str,
    asset: dict[str, Any],
    job_id: str,
    check_out_at: str | None = None,
) -> None:
    """Equipment checkout creates an internal equipment cost line + ledger entry."""
    aid = str(assignment_id or "").strip()
    jid = str(job_id or "").strip()
    if not aid or not jid:
        return
    rate, unit, qty = equipment_internal_rate(asset)
    if rate <= 0:
        delete_job_cost_transaction(SOURCE_ASSET_ASSIGNMENT, aid)
        return
    total = round(rate * qty, 2)
    asset_name = str(asset.get("asset_name") or asset.get("name") or "Equipment")[:500]
    txn_date = str(check_out_at or "")[:10] or date.today().isoformat()
    cost_cat = _asset_rental_category(asset)
    upsert_job_cost_transaction(
        {
            "job_id": jid,
            "transaction_date": txn_date,
            "cost_category": cost_cat,
            "source_type": SOURCE_ASSET_ASSIGNMENT,
            "source_id": aid,
            "asset_id": asset.get("id"),
            "item_name": asset_name,
            "description": asset_name,
            "quantity": qty,
            "unit_cost": rate,
            "total_cost": total,
            "notes": f"Equipment assignment ({unit})",
        }
    )
    marker = f"auto:assignment:{aid}"
    try:
        existing = _db().fetch_by_match("job_equipment", {"job_id": jid, "notes": marker}, limit=1) or []
        if existing:
            return
        payload = {
            "job_id": jid,
            "asset_id": asset.get("id"),
            "asset_label": asset_name,
            "usage_days": qty if unit == "day" else 0.0,
            "usage_hours": qty if unit == "hour" else 0.0,
            "rate_per_day": rate if unit == "day" else 0.0,
            "rate_per_hour": rate if unit == "hour" else 0.0,
            "line_total": total,
            "notes": marker,
        }
        if unit == "week":
            payload["usage_days"] = 7.0
            payload["rate_per_day"] = round(rate / 7.0, 4)
        elif unit == "month":
            payload["usage_days"] = 30.0
            payload["rate_per_day"] = round(rate / 30.0, 4)
        _db().insert_row("job_equipment", payload)
    except Exception as exc:
        _LOG.debug("job_equipment auto-line skipped: %s", exc)


def void_asset_assignment_cost(assignment_id: str) -> None:
    """Remove ledger cost when equipment is checked in or assignment voided."""
    delete_job_cost_transaction(SOURCE_ASSET_ASSIGNMENT, str(assignment_id or "").strip())


def fetch_job_cost_transactions(job_id: str, *, limit: int = 2000) -> list[dict[str, Any]]:
    jid = str(job_id or "").strip()
    if not jid:
        return []
    try:
        rows = _db().fetch_by_match(_TABLE, {"job_id": jid}, limit=limit) or []
    except Exception:
        return []
    rows.sort(key=lambda r: (str(r.get("transaction_date") or ""), str(r.get("created_at") or "")), reverse=True)
    return rows


def _estimate_for_job(job: dict[str, Any]) -> dict[str, Any]:
    eid = job.get("estimate_id")
    if not eid:
        return {}
    try:
        rows = _db().fetch_by_match("estimates", {"id": eid}, limit=1) or []
        return rows[0] if rows else {}
    except Exception:
        return {}


def _contract_value(job: dict[str, Any], estimate: dict[str, Any] | None = None) -> float:
    """Contract / revenue baseline from job award or linked estimate."""
    try:
        from app.services.job_costing_service import awarded_or_proposal_amount
    except ImportError:
        from services.job_costing_service import awarded_or_proposal_amount  # type: ignore
    est = estimate or _estimate_for_job(job)
    try:
        return _safe_float(awarded_or_proposal_amount(job, est))
    except Exception:
        return _safe_float(job.get("awarded_amount") or job.get("contract_value"))


def _estimated_cost(job: dict[str, Any], estimate: dict[str, Any] | None = None) -> float:
    """Internal estimated cost from linked estimate (not contract value)."""
    est = estimate or _estimate_for_job(job)
    for key in ("total_cost", "subtotal", "internal_cost", "estimated_cost"):
        val = _safe_float(est.get(key))
        if val > 0:
            return val
    return _safe_float(job.get("estimated_cost") or 0)


def can_manage_manual_cost_adjustments() -> bool:
    """Only admin users may add/edit/delete manual cost adjustments."""
    try:
        from app.auth import current_role
    except ImportError:
        from auth import current_role  # type: ignore
    return str(current_role() or "").strip().lower() == "admin"


def _asset_rental_category(asset: dict[str, Any] | None) -> str:
    if not asset:
        return COST_EQUIPMENT
    if bool(asset.get("is_rentable") or asset.get("rentable")):
        return COST_RENTAL
    return COST_EQUIPMENT


def _task_progress_pct(job_id: str) -> float:
    try:
        rows = _db().fetch_by_match("job_tasks", {"job_id": str(job_id).strip()}, limit=800) or []
    except Exception:
        return 0.0
    if not rows:
        return 0.0
    done = sum(
        1
        for t in rows
        if str(t.get("status") or "").strip().lower() in {"complete", "completed", "closed"}
    )
    return round(100.0 * done / len(rows), 1)


def build_job_cost_summary(job: dict[str, Any], *, progress_pct: float | None = None) -> dict[str, Any]:
    """Roll up ledger transactions into dashboard metrics."""
    jid = str(job.get("id") or "").strip()
    estimate = _estimate_for_job(job)
    contract = _contract_value(job, estimate)
    estimated = _estimated_cost(job, estimate)
    txns = fetch_job_cost_transactions(jid)
    labor = material = equipment = subcontract = rental = other = 0.0
    for t in txns:
        cat = str(t.get("cost_category") or "").strip().lower()
        amt = _safe_float(t.get("total_cost"))
        if cat == COST_LABOR:
            labor += amt
        elif cat == COST_MATERIAL:
            material += amt
        elif cat == COST_EQUIPMENT:
            equipment += amt
        elif cat == COST_SUBCONTRACT:
            subcontract += amt
        elif cat == COST_RENTAL:
            rental += amt
        else:
            other += amt
    actual = round(labor + material + equipment + subcontract + rental + other, 2)
    remaining = round(estimated - actual, 2) if estimated > 0 else None
    profit = round(contract - actual, 2) if contract > 0 else round(estimated - actual, 2)
    margin_pct = round((profit / contract * 100.0), 1) if contract > 0 else 0.0
    variance = round(estimated - actual, 2) if estimated > 0 else round(contract - actual, 2)
    pct = progress_pct if progress_pct is not None else _task_progress_pct(jid)
    status = str(job.get("status") or "").strip().lower()
    if status in {"completed", "closed", "complete"} or pct >= 99.0:
        projected = actual
    elif pct > 5.0:
        projected = round(actual / (pct / 100.0), 2)
    else:
        projected = round(max(actual, estimated or contract), 2)
    return {
        "contract_value": round(contract, 2),
        "estimated_cost": round(estimated, 2),
        "actual_cost": actual,
        "remaining_budget": remaining if remaining is not None else 0.0,
        "has_estimated_cost": estimated > 0,
        "has_contract_value": contract > 0,
        "projected_final_cost": projected,
        "variance": variance,
        "margin_pct": margin_pct,
        "margin_percent": margin_pct,
        "profit": profit,
        "labor_cost": round(labor, 2),
        "material_cost": round(material, 2),
        "equipment_cost": round(equipment, 2),
        "subcontract_cost": round(subcontract, 2),
        "rental_cost": round(rental, 2),
        "other_cost": round(other, 2),
        "transaction_count": len(txns),
        "progress_pct": pct,
    }


def sync_all_sources_for_job(job_id: str) -> None:
    """Backfill ledger rows from existing source tables (idempotent)."""
    jid = str(job_id or "").strip()
    if not jid:
        return
    db = _db()
    for table, sync_fn in (
        ("time_entries", sync_time_entry),
        ("employee_timekeeping_days", sync_timekeeping_day),
        ("job_materials", sync_job_material),
        ("job_equipment", sync_job_equipment),
        ("job_expenses", sync_job_expense),
    ):
        try:
            rows = db.fetch_by_match(table, {"job_id": jid}, limit=5000) or []
        except Exception:
            continue
        for row in rows:
            _safe_sync(sync_fn, row)
    try:
        assignments = db.fetch_by_match("asset_assignments", {"assigned_job_id": jid}, limit=2000) or []
    except Exception:
        assignments = []
    for row in assignments:
        if not row.get("check_in_at"):
            aid = str(row.get("id") or "").strip()
            asset_id = str(row.get("asset_id") or "").strip()
            if not aid or not asset_id:
                continue
            try:
                assets = db.fetch_by_match("assets", {"id": asset_id}, limit=1) or []
            except Exception:
                continue
            if assets:
                _safe_sync(
                    sync_asset_assignment_to_job,
                    assignment_id=aid,
                    asset=assets[0],
                    job_id=jid,
                    check_out_at=str(row.get("check_out_at") or ""),
                )


def create_manual_cost_adjustment(
    *,
    job_id: str,
    transaction_date: str,
    cost_category: str,
    description: str,
    quantity: float,
    unit_cost: float,
    notes: str = "",
    created_by: str | None = None,
) -> bool:
    """Admin-only manual cost line (source_type=manual_adjustment)."""
    import uuid

    jid = str(job_id or "").strip()
    if not jid:
        return False
    qty = _safe_float(quantity)
    unit = _safe_float(unit_cost)
    total = round(qty * unit, 2) if qty > 0 and unit >= 0 else round(_safe_float(quantity), 2)
    if total <= 0:
        return False
    adj_id = str(uuid.uuid4())
    return upsert_job_cost_transaction(
        {
            "job_id": jid,
            "transaction_date": str(transaction_date or "")[:10] or date.today().isoformat(),
            "cost_category": str(cost_category or COST_OTHER).strip(),
            "source_type": SOURCE_MANUAL_ADJUSTMENT,
            "source_id": adj_id,
            "item_name": str(description or "Manual adjustment")[:500],
            "description": str(description or "Manual adjustment")[:500],
            "quantity": qty or 1.0,
            "unit_cost": unit if unit > 0 else total,
            "total_cost": total,
            "notes": str(notes or "Manual adjustment")[:2000],
            "created_by": created_by,
        }
    )


def update_manual_cost_adjustment(txn_id: str, fields: dict[str, Any]) -> bool:
    """Update an existing manual adjustment only."""
    tid = str(txn_id or "").strip()
    if not tid:
        return False
    try:
        rows = _db().fetch_by_match(_TABLE, {"id": tid}, limit=1) or []
    except Exception:
        return False
    if not rows or str(rows[0].get("source_type") or "") != SOURCE_MANUAL_ADJUSTMENT:
        return False
    row = rows[0]
    qty = _safe_float(fields.get("quantity", row.get("quantity")))
    unit = _safe_float(fields.get("unit_cost", row.get("unit_cost")))
    total = round(qty * unit, 2)
    if total <= 0:
        try:
            _db().delete_rows(_TABLE, {"id": tid})
        except Exception:
            return False
        return True
    desc = str(fields.get("description") or row.get("description") or row.get("item_name") or "")[:500]
    return upsert_job_cost_transaction(
        {
            "job_id": row.get("job_id"),
            "transaction_date": str(fields.get("transaction_date") or row.get("transaction_date") or "")[:10],
            "cost_category": str(fields.get("cost_category") or row.get("cost_category") or COST_OTHER),
            "source_type": SOURCE_MANUAL_ADJUSTMENT,
            "source_id": str(row.get("source_id") or tid),
            "item_name": desc,
            "description": desc,
            "quantity": qty,
            "unit_cost": unit,
            "total_cost": total,
            "notes": str(fields.get("notes") or row.get("notes") or "")[:2000],
        }
    )


def delete_manual_cost_adjustment(txn_id: str) -> bool:
    """Delete a manual adjustment row."""
    tid = str(txn_id or "").strip()
    if not tid:
        return False
    try:
        rows = _db().fetch_by_match(_TABLE, {"id": tid}, limit=1) or []
    except Exception:
        return False
    if not rows or str(rows[0].get("source_type") or "") != SOURCE_MANUAL_ADJUSTMENT:
        return False
    try:
        _db().delete_rows(_TABLE, {"id": tid})
        return True
    except Exception:
        return False


def transaction_display_source(row: dict[str, Any]) -> str:
    st = str(row.get("source_type") or "").strip()
    mapping = {
        SOURCE_TIME_ENTRY: "Labor time",
        SOURCE_TIMEKEEPING_DAY: "Timekeeping",
        SOURCE_JOB_MATERIAL: "Material",
        SOURCE_JOB_EQUIPMENT: "Equipment",
        SOURCE_JOB_EXPENSE: "Purchase / expense",
        SOURCE_ASSET_ASSIGNMENT: "Equipment assignment",
        SOURCE_MANUAL_ADJUSTMENT: "Manual adjustment",
        SOURCE_ESTIMATE: "Estimate",
    }
    if st in mapping:
        return mapping[st]
    notes = str(row.get("notes") or "").strip()
    if notes:
        return notes
    return st or "—"


def transaction_employee_name(row: dict[str, Any], employees_by_id: dict[str, dict[str, Any]]) -> str:
    eid = str(row.get("employee_id") or "").strip()
    if eid and eid in employees_by_id:
        return str(employees_by_id[eid].get("name") or "—").strip() or "—"
    return "—"
