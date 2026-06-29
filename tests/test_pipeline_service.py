"""Pipeline row builder tests."""

from __future__ import annotations

from app.services.pipeline_service import (
    build_pipeline_rows,
    filter_pipeline_rows,
    pipeline_summary,
)


def test_open_quote_row_uses_q_number():
    rows = build_pipeline_rows(
        [
            {
                "id": "e1",
                "estimate_number": "Q26099",
                "status": "Draft",
                "customer": "Acme",
                "project_name": "Test Project",
                "customer_price": 1000,
            }
        ],
        [],
    )
    assert len(rows) == 1
    assert rows[0]["record_type"] == "quote"
    assert rows[0]["quote_number"] == "Q26099"
    assert rows[0]["job_number"] == ""
    assert rows[0]["stage"] == "Quote — Draft"


def test_linked_estimate_and_job_merge_to_one_row():
    rows = build_pipeline_rows(
        [
            {
                "id": "e1",
                "estimate_number": "Q26086",
                "status": "Approved",
                "customer": "McIlhenny Company",
                "project_name": "Sauce Transfer Line Modifications",
                "customer_price": 8100,
            }
        ],
        [
            {
                "id": "j1",
                "estimate_id": "e1",
                "job_number": "J26086",
                "status": "Active",
                "customer": "McIlhenny Company",
                "job_name": "Sauce Transfer Line Modifications",
                "contract_value": 8100,
            }
        ],
    )
    assert len(rows) == 1
    assert rows[0]["quote_number"] == "Q26086"
    assert rows[0]["job_number"] == "J26086"
    assert rows[0]["display_number"] == "J26086"
    assert rows[0]["record_type"] == "awarded"


def test_standalone_job_appears_as_j_row():
    rows = build_pipeline_rows(
        [],
        [
            {
                "id": "j9",
                "job_number": "J26015",
                "status": "Active",
                "customer": "Birla Carbons - USA",
                "job_name": "Shower House Water Line Repair",
                "contract_value": 10680.32,
            }
        ],
    )
    assert len(rows) == 1
    assert rows[0]["record_type"] == "job"
    assert rows[0]["job_number"] == "J26015"


def test_filter_open_quotes():
    rows = build_pipeline_rows(
        [
            {"id": "e1", "estimate_number": "Q26001", "status": "Draft"},
            {"id": "e2", "estimate_number": "Q26002", "status": "Approved"},
        ],
        [],
    )
    open_rows = filter_pipeline_rows(rows, view="Open Quotes")
    assert len(open_rows) == 1
    assert open_rows[0]["quote_number"] == "Q26001"


def test_pipeline_summary_counts():
    rows = build_pipeline_rows(
        [
            {"id": "e1", "estimate_number": "Q26001", "status": "Sent", "customer_price": 100},
            {"id": "e2", "estimate_number": "Q26002", "status": "Approved", "customer_price": 200},
        ],
        [
            {
                "id": "j1",
                "estimate_id": "e2",
                "job_number": "J26002",
                "status": "Active",
                "contract_value": 200,
            },
            {
                "id": "j2",
                "job_number": "J26003",
                "status": "Active",
                "contract_value": 300,
            },
        ],
    )
    summary = pipeline_summary(rows)
    assert summary["total"] == 3
    assert summary["open_quotes"] == 1
    assert summary["approved_quotes"] == 0
    assert summary["active_jobs"] == 2
