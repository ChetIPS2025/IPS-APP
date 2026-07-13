"""Job financial field helpers for manual entry and projected margin display."""

from __future__ import annotations

from typing import Any

BILLING_TYPE_FIXED = "fixed_price"
BILLING_TYPE_TM = "time_and_material"

BILLING_TYPE_OPTIONS: tuple[tuple[str, str], ...] = (
    (BILLING_TYPE_FIXED, "Fixed Price"),
    (BILLING_TYPE_TM, "Time & Materials"),
)

BILLING_TYPE_LABELS = dict(BILLING_TYPE_OPTIONS)


def normalize_billing_type(raw: object) -> str:
    raw_str = str(raw or "").strip()
    for value, label in BILLING_TYPE_OPTIONS:
        if raw_str.lower() == label.lower() or raw_str.lower() == value.lower():
            return value
    token = raw_str.lower().replace("-", "_").replace(" ", "_").replace("&", "_")
    while "__" in token:
        token = token.replace("__", "_")
    if token in {
        "tm",
        "t_m",
        "tandm",
        "time_and_material",
        "time_and_materials",
        "time_material",
        "time_materials",
    }:
        return BILLING_TYPE_TM
    if "time" in token and "material" in token:
        return BILLING_TYPE_TM
    return BILLING_TYPE_FIXED


def job_is_time_and_material(job: dict[str, Any]) -> bool:
    return normalize_billing_type(job.get("billing_type")) == BILLING_TYPE_TM


def billing_type_label(raw: object) -> str:
    return BILLING_TYPE_LABELS.get(normalize_billing_type(raw), "Fixed Price")


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
    actual = round(float(job.get("actual_cost") or 0), 2)
    has_actual = actual > 0.005
    profit_raw = job.get("projected_gross_profit")
    margin_raw = job.get("projected_margin_pct")
    if has_actual and contract > 0:
        profit = round(contract - actual, 2)
        margin = round((profit / contract) * 100.0, 1)
    elif profit_raw is not None:
        profit = float(profit_raw)
        margin = float(margin_raw) if margin_raw is not None else projected_margin_pct(contract, estimated)
    else:
        profit = projected_gross_profit(contract, estimated)
        margin = projected_margin_pct(contract, estimated)
    return {
        "contract_value": contract,
        "estimated_cost": estimated,
        "actual_cost": actual,
        "profit": profit,
        "margin_pct": margin,
        "has_contract": contract > 0,
        "has_estimated": estimated > 0,
        "has_actual": has_actual,
    }


def _linked_estimate_for_jobs_table(job: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve estimate linked by ``jobs.estimate_id`` or ``estimates.job_id``."""
    from app.services.estimate_job_workflow_service import _linked_estimate_row_for_job
    row = _linked_estimate_row_for_job(job)
    return row if row else None


def estimate_total_from_record(row: dict[str, Any]) -> float:
    """Estimate selling total from stored estimate fields (not job ledger costing)."""
    for key in ("customer_price", "total", "grand_total", "proposal_total", "final_bid", "amount"):
        amount = parse_money(row.get(key))
        if amount is not None and amount > 0:
            return amount
    return 0.0


def live_job_profit_margin(contract_value: float, actual_cost: float) -> tuple[float, float]:
    """Estimated profit and margin from contract value minus posted actual cost."""
    contract = float(contract_value or 0)
    actual = round(float(actual_cost or 0), 2)
    if contract <= 0:
        return 0.0, 0.0
    profit = round(contract - actual, 2)
    margin = round((profit / contract) * 100.0, 1)
    return profit, margin


def job_table_list_financials_from_row(job: dict[str, Any]) -> dict[str, float | bool]:
    """
    Jobs list table snapshot: contract from award/approved estimate;
    actual from accumulated job cost; profit/margin from contract minus actual.
    """
    fin = dict(job_list_financials_from_row(job))
    est = _linked_estimate_for_jobs_table(job)
    from app.services.job_cost_transaction_service import _contract_value
    contract = _contract_value(job, est if est else None)
    actual = float(fin["actual_cost"])
    profit, margin = live_job_profit_margin(contract, actual)
    fin["contract_value"] = contract
    fin["has_contract"] = contract > 0.005
    fin["profit"] = profit
    fin["margin_pct"] = margin
    return fin


def _fetch_estimate_for_financial_lock(estimate_id: str) -> dict[str, Any]:
    eid = str(estimate_id or "").strip()
    if not eid:
        return {}
    from app.pages._core._data import get_estimate
    return get_estimate(eid) or {}


def _job_matches_linked_estimate_quote(job: dict[str, Any], estimate: dict[str, Any]) -> bool:
    from app.services.job_from_estimate import _job_matches_estimate_quote
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
    from app.services.job_cost_transaction_service import _estimate_is_approved
    est = _fetch_estimate_for_financial_lock(eid)
    if not est or not _estimate_is_approved(est):
        return False
    if str(est.get("job_id") or "").strip() == jid:
        return True
    return _job_matches_linked_estimate_quote(job, est)


def job_manual_financials_editable(job: dict[str, Any]) -> bool:
    """Manual jobs may edit contract/estimated cost; estimate-synced jobs may not."""
    return not job_financials_locked_by_approved_estimate(job)
