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


def job_manual_financials_editable(job: dict[str, Any]) -> bool:
    """Manual jobs may edit contract/estimated cost; approved estimate-linked jobs may not."""
    eid = str(job.get("estimate_id") or "").strip()
    if not eid:
        return True
    try:
        from app.services.job_cost_transaction_service import (
            _approved_estimate_for_job,
            _estimate_is_approved,
        )
    except ImportError:
        from services.job_cost_transaction_service import (  # type: ignore
            _approved_estimate_for_job,
            _estimate_is_approved,
        )
    try:
        est = _approved_estimate_for_job(job)
        if est and _estimate_is_approved(est):
            return False
    except Exception:
        return True
    return True
