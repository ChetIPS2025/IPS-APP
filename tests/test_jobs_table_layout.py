"""Jobs list table layout helpers (UI column visibility)."""

from __future__ import annotations

from app.components.jobs_page_layout import jobs_column_has_data, jobs_visible_table_layout


def _cost_fields(row: dict) -> dict:
    try:
        from app.services.job_financial_ui import job_list_financials_from_row
    except ImportError:
        from services.job_financial_ui import job_list_financials_from_row  # type: ignore
    fin = job_list_financials_from_row(row)
    return {
        "has_estimated": bool(fin["has_estimated"]),
        "has_actual": bool(fin["has_actual"]),
        "has_contract": bool(fin["has_contract"]),
    }


def test_jobs_visible_table_layout_includes_financial_dashboard_columns():
    rows = [
        {
            "id": "j1",
            "contract_value": 0,
            "estimated_cost": 0,
            "actual_cost": 0,
        }
    ]
    markers, headers, weights = jobs_visible_table_layout(rows, _cost_fields)
    assert markers == (
        "num",
        "desc",
        "customer",
        "status",
        "contract",
        "actual",
        "profit",
        "profit_pct",
    )
    assert headers[4][0] == "CONTRACT VALUE"
    assert headers[5][0] == "ACTUAL COST"
    assert headers[6][0] == "EST. PROFIT"
    assert headers[7][0] == "PROFIT %"
    assert "actions" not in markers
    assert len(headers) == len(weights) == len(markers)


def test_jobs_column_has_data_detects_contract():
    rows = [{"id": "j1", "awarded_amount": 500, "actual_cost": 0}]
    assert jobs_column_has_data(rows, _cost_fields, "contract")
    assert jobs_column_has_data(rows, _cost_fields, "actual")
    assert not jobs_column_has_data(rows, _cost_fields, "estimated")
