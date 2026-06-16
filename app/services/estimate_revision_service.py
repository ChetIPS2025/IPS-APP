"""Approved estimate revision workflow — snapshots, job contract protection."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

try:
    from app.services.estimate_costing_service import (
        calculate_estimate_totals,
        get_estimate_bundle,
        recalculate_and_save_estimate_totals,
    )
    from app.services.estimate_job_workflow_service import (
        current_user_profile_id,
        estimate_visible_in_approved_view,
    )
    from app.services.repository import ServiceResult, fetch_by_id, filter_payload_to_table, update_row
except ImportError:
    from services.estimate_costing_service import (  # type: ignore
        calculate_estimate_totals,
        get_estimate_bundle,
        recalculate_and_save_estimate_totals,
    )
    from services.estimate_job_workflow_service import (  # type: ignore
        current_user_profile_id,
        estimate_visible_in_approved_view,
    )
    from services.repository import ServiceResult, fetch_by_id, filter_payload_to_table, update_row  # type: ignore

try:
    from db import fetch_by_match_admin, insert_row_admin, update_rows_admin
except ImportError:
    from app.db import fetch_by_match_admin, insert_row_admin, update_rows_admin  # type: ignore

_LOG = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_float(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _estimate_customer_price(row: dict[str, Any]) -> float:
    for key in ("customer_price", "total", "grand_total", "proposal_total", "final_bid"):
        amount = _safe_float(row.get(key))
        if amount > 0:
            return amount
    eid = str(row.get("id") or "").strip()
    if eid:
        try:
            totals = calculate_estimate_totals(eid)
            amount = _safe_float(totals.get("customer_price"))
            if amount > 0:
                return amount
        except Exception:
            pass
    return 0.0


def _linked_job_for_estimate(estimate_id: str, row: dict[str, Any] | None = None) -> dict[str, Any] | None:
    est = row or fetch_by_id("estimates", estimate_id) or {}
    jid = str(est.get("job_id") or "").strip()
    if not jid:
        return None
    rows = fetch_by_match_admin("jobs", {"id": jid}, limit=1)
    return rows[0] if rows else None


def _job_contract_amount(job: dict[str, Any] | None) -> float:
    if not job:
        return 0.0
    awarded = _safe_float(job.get("awarded_amount"))
    if awarded > 0:
        return awarded
    return _safe_float(job.get("contract_value"))


def build_estimate_revision_snapshot(estimate_id: str) -> dict[str, Any] | None:
    """Capture estimate row, line bundle, totals, and pinned job contract for revision audit."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return None
    row = fetch_by_id("estimates", eid)
    if not row:
        return None
    try:
        totals = calculate_estimate_totals(eid)
        lines = get_estimate_bundle(eid)
    except Exception as exc:
        _LOG.warning("Could not build revision snapshot for %s: %s", eid, exc)
        totals = {}
        lines = {}
    job = _linked_job_for_estimate(eid, row)
    return {
        "captured_at": _utc_now_iso(),
        "estimate_id": eid,
        "revision_number": int(row.get("revision_number") or 1),
        "estimate": dict(row),
        "totals": totals,
        "lines": lines,
        "job": {
            "id": str(job.get("id") or "") if job else "",
            "awarded_amount": _job_contract_amount(job),
            "status": str(job.get("status") or "") if job else "",
        },
        "approved_customer_price": _estimate_customer_price(row),
        "approved_total_cost": _safe_float(totals.get("total_cost") or row.get("total_cost") or row.get("subtotal")),
    }


def save_estimate_revision_record(
    estimate_id: str,
    *,
    revision_number: int,
    snapshot_json: dict[str, Any],
    note: str = "",
) -> bool:
    eid = str(estimate_id or "").strip()
    if not eid:
        return False
    payload = {
        "estimate_id": eid,
        "revision_number": int(revision_number),
        "snapshot_json": snapshot_json,
        "saved_by": current_user_profile_id(),
        "change_note": str(note or "").strip()[:4000],
    }
    try:
        filtered = filter_payload_to_table("estimate_revisions", payload)
        if filtered:
            insert_row_admin("estimate_revisions", filtered)
        return True
    except Exception as exc:
        _LOG.debug("estimate_revisions insert skipped for %s: %s", eid, exc)
        return False


def pin_linked_job_contract_from_estimate(estimate_id: str, *, customer_price: float | None = None) -> ServiceResult:
    """Pin linked job awarded amount to approved estimate selling price."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Invalid estimate id.")
    row = fetch_by_id("estimates", eid) or {}
    job = _linked_job_for_estimate(eid, row)
    if not job:
        return ServiceResult(ok=True, data={"skipped": True})
    jid = str(job.get("id") or "").strip()
    price = _safe_float(customer_price) if customer_price is not None else _estimate_customer_price(row)
    if price <= 0:
        return ServiceResult(ok=True, data={"skipped": True})
    payload = filter_payload_to_table(
        "jobs",
        {"awarded_amount": round(price, 2), "updated_at": _utc_now_iso()},
    )
    if not payload:
        return ServiceResult(ok=True, data={"skipped": True})
    try:
        update_rows_admin("jobs", payload, {"id": jid})
        return ServiceResult(ok=True, data={"job_id": jid, "awarded_amount": round(price, 2)})
    except Exception as exc:
        return ServiceResult(ok=False, error=str(exc))


def begin_approved_estimate_revision(estimate_id: str, *, note: str) -> ServiceResult:
    """Start an explicit approved-estimate revision; stores baseline snapshot."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Invalid estimate id.")
    row = fetch_by_id("estimates", eid)
    if not row:
        return ServiceResult(ok=False, error="Estimate not found.")
    if not estimate_visible_in_approved_view(row):
        return ServiceResult(ok=False, error="Only approved estimates can be revised with this workflow.")
    reason = str(note or "").strip()
    if not reason:
        return ServiceResult(ok=False, error="A revision reason is required.")

    snapshot = build_estimate_revision_snapshot(eid)
    if not snapshot:
        return ServiceResult(ok=False, error="Could not capture approved estimate snapshot.")

    rev_num = int(row.get("revision_number") or 1)
    save_estimate_revision_record(
        eid,
        revision_number=rev_num,
        snapshot_json={**snapshot, "revision_kind": "approved_baseline"},
        note=f"Revision started: {reason}",
    )
    pin_result = pin_linked_job_contract_from_estimate(
        eid,
        customer_price=_safe_float(snapshot.get("approved_customer_price")),
    )
    if not pin_result.ok:
        _LOG.warning("Could not pin job contract for estimate %s: %s", eid, pin_result.error)

    return ServiceResult(
        ok=True,
        data={
            "snapshot": snapshot,
            "revision_number": rev_num,
            "job_awarded_amount": _safe_float((snapshot.get("job") or {}).get("awarded_amount")),
        },
    )


def complete_approved_estimate_revision(
    estimate_id: str,
    *,
    note: str,
    update_job_contract: bool = False,
) -> ServiceResult:
    """Finalize a revision, bump revision number, optionally update linked job contract."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Invalid estimate id.")
    row = fetch_by_id("estimates", eid)
    if not row:
        return ServiceResult(ok=False, error="Estimate not found.")
    reason = str(note or "").strip()
    if not reason:
        return ServiceResult(ok=False, error="A completion note is required.")

    recalculate_and_save_estimate_totals(eid)
    fresh = fetch_by_id("estimates", eid) or row
    next_rev = int(fresh.get("revision_number") or 1) + 1
    snapshot = build_estimate_revision_snapshot(eid)
    if not snapshot:
        return ServiceResult(ok=False, error="Could not capture revised estimate snapshot.")
    snapshot["revision_kind"] = "approved_completed"

    save_estimate_revision_record(
        eid,
        revision_number=next_rev,
        snapshot_json=snapshot,
        note=reason,
    )

    est_payload = filter_payload_to_table(
        "estimates",
        {"revision_number": next_rev, "updated_at": _utc_now_iso()},
    )
    if est_payload:
        update_rows_admin("estimates", est_payload, {"id": eid})

    job_update_msg = ""
    if update_job_contract:
        new_price = _estimate_customer_price(fresh)
        pin = pin_linked_job_contract_from_estimate(eid, customer_price=new_price)
        if pin.ok and not (isinstance(pin.data, dict) and pin.data.get("skipped")):
            job_update_msg = f" Linked job contract updated to {new_price:,.2f}."
        elif not pin.ok:
            job_update_msg = f" Estimate saved; job contract was not updated ({pin.error})."

    _log_revision_activity(eid, "Estimate revision completed", details=reason)
    return ServiceResult(
        ok=True,
        data={"revision_number": next_rev, "snapshot": snapshot},
        error=None if not job_update_msg else job_update_msg.strip(),
    )


def cancel_approved_estimate_revision(
    estimate_id: str,
    *,
    baseline_snapshot: dict[str, Any],
    restore_estimate_totals: bool = True,
) -> ServiceResult:
    """Exit revision mode; optionally restore approved rollup totals on the estimate row."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return ServiceResult(ok=False, error="Invalid estimate id.")
    if restore_estimate_totals:
        totals = baseline_snapshot.get("totals") if isinstance(baseline_snapshot.get("totals"), dict) else {}
        approved_price = _safe_float(
            baseline_snapshot.get("approved_customer_price") or totals.get("customer_price")
        )
        approved_cost = _safe_float(
            baseline_snapshot.get("approved_total_cost") or totals.get("total_cost")
        )
        payload = filter_payload_to_table(
            "estimates",
            {
                "customer_price": round(approved_price, 2) if approved_price > 0 else None,
                "total": round(approved_price, 2) if approved_price > 0 else None,
                "total_cost": round(approved_cost, 2) if approved_cost > 0 else None,
                "subtotal": round(approved_cost, 2) if approved_cost > 0 else None,
                "updated_at": _utc_now_iso(),
            },
        )
        payload = {k: v for k, v in payload.items() if v is not None}
        if payload:
            try:
                update_rows_admin("estimates", payload, {"id": eid})
            except Exception as exc:
                return ServiceResult(ok=False, error=f"Could not restore approved totals: {exc}")
    _log_revision_activity(eid, "Estimate revision cancelled", details="Revision cancelled without job contract change.")
    return ServiceResult(ok=True)


def _log_revision_activity(estimate_id: str, action: str, *, details: str = "") -> None:
    payload = {
        "estimate_id": estimate_id,
        "activity_type": action[:200],
        "description": details[:4000] or action[:200],
        "created_by": current_user_profile_id(),
        "created_at": _utc_now_iso(),
    }
    try:
        filtered = filter_payload_to_table("estimate_activity_log", payload)
        if filtered:
            insert_row_admin("estimate_activity_log", filtered)
    except Exception as exc:
        _LOG.debug("estimate_activity_log skipped: %s", exc)
