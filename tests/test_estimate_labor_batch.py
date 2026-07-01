"""Batch labor updates recalculate estimate totals once."""

from __future__ import annotations


def test_update_estimate_labor_batch_recalcs_once(monkeypatch):
    from app.services import estimate_costing_service as svc

    recalc_calls: list[str] = []

    monkeypatch.setattr(
        svc,
        "update_row",
        lambda table, payload, match: type("R", (), {"ok": True, "data": payload, "error": None})(),
    )
    monkeypatch.setattr(
        svc,
        "recalculate_and_save_estimate_totals",
        lambda eid: recalc_calls.append(eid)
        or type("R", (), {"ok": True, "data": {"customer_price": 100.0}, "error": None})(),
    )

    result = svc.update_estimate_labor_batch(
        "est-1",
        [
            {"line_id": "line-a", "st_hours": 8, "ot_hours": 0, "st_rate": 50, "ot_rate": 75, "markup_percent": 10},
            {"line_id": "line-b", "st_hours": 4, "ot_hours": 2, "st_rate": 40, "ot_rate": 60, "markup_percent": 10},
        ],
    )

    assert result.ok
    assert recalc_calls == ["est-1"]
