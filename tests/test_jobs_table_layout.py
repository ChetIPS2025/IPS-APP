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


def test_jobs_visible_table_layout_hides_empty_financial_columns():
    rows = [
        {
            "id": "j1",
            "contract_value": 0,
            "estimated_cost": 0,
            "actual_cost": 0,
        }
    ]
    markers, headers, weights = jobs_visible_table_layout(rows, _cost_fields)
    assert markers == ("num", "desc", "customer", "status")
    assert "estimated" not in markers
    assert "actual" not in markers
    assert "contract" not in markers
    assert "actions" not in markers
    assert len(headers) == len(weights) == len(markers)


def test_jobs_column_has_data_detects_estimated():
    rows = [{"id": "j1", "estimated_cost": 500, "contract_value": 0}]
    assert jobs_column_has_data(rows, _cost_fields, "estimated")
    assert not jobs_column_has_data(rows, _cost_fields, "actual")
