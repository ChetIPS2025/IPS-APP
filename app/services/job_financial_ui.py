"""Job financial field helpers for manual entry and projected margin display."""

from __future__ import annotations

from typing import Any


def parse_money(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def projected_gross_profit(contract_value: float, estimated_cost: float) -> float:
    return round(float(contract_value or 0) - float(estimated_cost or 0), 2)


def projected_margin_pct(contract_value: float, estimated_cost: float) -> float:
    contract = float(contract_value or 0)
    if contract <= 0:
        return 0.0
    profit = projected_gross_profit(contract, estimated_cost)
    return round((profit / contract) * 100.0, 1)


def apply_projected_financials_to_job_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Compute and attach projected profit/margin fields for jobs table persistence."""
    out = dict(payload)
    contract = float(out.get("awarded_amount") or out.get("contract_value") or 0)
    estimated = float(out.get("estimated_cost") or 0)
    out["projected_gross_profit"] = projected_gross_profit(contract, estimated)
    out["projected_margin_pct"] = projected_margin_pct(contract, estimated)
    return out


def job_list_financials_from_row(job: dict[str, Any]) -> dict[str, float | bool]:
    """Fast list/detail snapshot from stored job columns (no ledger recompute)."""
    contract = float(job.get("awarded_amount") or job.get("contract_value") or 0)
    estimated = float(job.get("estimated_cost") or 0)
    profit_raw = job.get("projected_gross_profit")
    margin_raw = job.get("projected_margin_pct")
    if profit_raw is not None:
        profit = float(profit_raw)
    else:
        profit = projected_gross_profit(contract, estimated)
    if margin_raw is not None:
        margin = float(margin_raw)
    else:
        margin = projected_margin_pct(contract, estimated)
    return {
        "contract_value": contract,
        "estimated_cost": estimated,
        "actual_cost": 0.0,
        "profit": profit,
        "margin_pct": margin,
        "has_contract": contract > 0,
        "has_estimated": estimated > 0,
        "has_actual": False,
    }


def _fetch_estimate_for_financial_lock(estimate_id: str) -> dict[str, Any]:
    eid = str(estimate_id or "").strip()
    if not eid:
        return {}
    try:
        from app.pages._core._data import get_estimate
    except ImportError:
        from pages._core._data import get_estimate  # type: ignore
    return get_estimate(eid) or {}


def _job_matches_linked_estimate_quote(job: dict[str, Any], estimate: dict[str, Any]) -> bool:
    try:
        from app.services.job_from_estimate import _job_matches_estimate_quote
    except ImportError:
        from services.job_from_estimate import _job_matches_estimate_quote  # type: ignore
    quote = str(estimate.get("quote_number") or estimate.get("estimate_number") or "").strip()
    return bool(quote) and _job_matches_estimate_quote(job, quote)


def job_financials_locked_by_approved_estimate(job: dict[str, Any]) -> bool:
    """
    True only when this job is tied to an approved estimate through the estimate workflow
    (``jobs.estimate_id`` + approved estimate with matching ``estimates.job_id`` or quote).
    Manual jobs without that link remain editable even if another estimate references the job.
    """
    jid = str(job.get("id") or "").strip()
    eid = str(job.get("estimate_id") or "").strip()
    if not jid or not eid:
        return False
    try:
        from app.services.job_cost_transaction_service import _estimate_is_approved
    except ImportError:
        from services.job_cost_transaction_service import _estimate_is_approved  # type: ignore
    est = _fetch_estimate_for_financial_lock(eid)
    if not est or not _estimate_is_approved(est):
        return False
    if str(est.get("job_id") or "").strip() == jid:
        return True
    return _job_matches_linked_estimate_quote(job, est)


def job_manual_financials_editable(job: dict[str, Any]) -> bool:
    """Manual jobs may edit contract/estimated cost; estimate-synced jobs may not."""
    return not job_financials_locked_by_approved_estimate(job)
