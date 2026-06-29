"""Pipeline row builder tests."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.pipeline_service import (
    PIPELINE_STALE_SENT_DAYS,
    build_pipeline_rows,
    filter_pipeline_rows,
    pipeline_filter_options,
    pipeline_stale_hint,
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


def test_stale_sent_quote_after_threshold():
    old = (date.today() - timedelta(days=PIPELINE_STALE_SENT_DAYS + 1)).isoformat()
    rows = build_pipeline_rows(
        [
            {
                "id": "e1",
                "estimate_number": "Q26001",
                "status": "Sent",
                "estimate_date": old,
                "customer_price": 100,
            }
        ],
        [],
    )
    assert rows[0]["is_stale"] is True
    assert "no response" in str(rows[0]["stale_hint"]).lower()


def test_filter_needs_attention_view():
    old = (date.today() - timedelta(days=PIPELINE_STALE_SENT_DAYS + 2)).isoformat()
    rows = build_pipeline_rows(
        [
            {"id": "e1", "estimate_number": "Q26001", "status": "Sent", "estimate_date": old},
            {"id": "e2", "estimate_number": "Q26002", "status": "Draft", "estimate_date": date.today().isoformat()},
        ],
        [],
    )
    stale_rows = filter_pipeline_rows(rows, view="Needs Attention")
    assert len(stale_rows) == 1
    assert stale_rows[0]["quote_number"] == "Q26001"


def test_filter_by_customer_and_supervisor():
    rows = build_pipeline_rows(
        [
            {"id": "e1", "estimate_number": "Q26001", "status": "Draft", "customer": "Acme"},
        ],
        [
            {
                "id": "j1",
                "job_number": "J26002",
                "status": "Active",
                "customer": "Gulf Coast",
                "supervisor": "Leland Daigle",
                "job_name": "Tank work",
            }
        ],
    )
    opts = pipeline_filter_options(rows)
    assert "Acme" in opts["customer"]
    assert "Leland Daigle" in opts["supervisor"]
    assert len(filter_pipeline_rows(rows, customer="Acme")) == 1
    assert len(filter_pipeline_rows(rows, supervisor="Leland Daigle")) == 1


def test_active_job_not_started_is_stale():
    start = (date.today() - timedelta(days=3)).isoformat()
    hint = pipeline_stale_hint(
        {
            "has_job": True,
            "job_status": "Active",
            "job_start_date": start,
            "progress": 0,
            "record_type": "job",
        },
        today=date.today(),
    )
    assert hint is not None
    assert "not started" in hint.lower()
