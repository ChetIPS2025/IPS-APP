"""Tests for Jobs list table HTML helpers."""

from __future__ import annotations

from app.components.jobs_list_table import (
    _profit_pct_color_class,
    build_jobs_html_table,
    handle_jobs_table_action,
    job_list_link_html,
)


def test_job_list_link_html_includes_action_and_id():
    html_out = job_list_link_html(
        "j-123",
        "J26015",
        extra_class="ips-jobs-number-link",
    )
    assert 'href="' in html_out
    assert "job_detail=j-123" in html_out
    assert 'target="_self"' in html_out
    assert "J26015" in html_out
    assert "ips-jobs-number-link" in html_out
    assert "ips-jobs-open-link" in html_out
    assert '<button type="button"' not in html_out


def test_handle_jobs_table_action_strips_open_prefix():
    opened: list[tuple[str, dict]] = []

    handle_jobs_table_action(
        "open:j-123",
        {"j-123": {"id": "j-123", "job_number": "J26015"}},
        last_action_key="jobs_test_last_action",
        open_job_fn=lambda job_id, job: opened.append((job_id, job)),
    )

    assert opened == [("j-123", {"id": "j-123", "job_number": "J26015"})]

    handle_jobs_table_action(
        "open:j-123",
        {"j-123": {"id": "j-123", "job_number": "J26015"}},
        last_action_key="jobs_test_last_action",
        open_job_fn=lambda job_id, job: opened.append((job_id, job)),
    )

    assert opened == [("j-123", {"id": "j-123", "job_number": "J26015"})]


def test_profit_pct_color_classes():
    assert _profit_pct_color_class(30) == "ips-jobs-profit-pct-green"
    assert _profit_pct_color_class(25) == "ips-jobs-profit-pct-yellow"
    assert _profit_pct_color_class(15) == "ips-jobs-profit-pct-yellow"
    assert _profit_pct_color_class(10) == "ips-jobs-profit-pct-yellow"
    assert _profit_pct_color_class(5) == "ips-jobs-profit-pct-orange"
    assert _profit_pct_color_class(-1) == "ips-jobs-profit-pct-red"


def test_build_jobs_html_table_includes_financial_dashboard_columns():
    rows = [
        {
            "id": "j-1",
            "job_number": "J100",
            "job_name": "Test project",
            "customer_name": "Acme",
            "status": "Active",
            "awarded_amount": 10000,
            "actual_cost": 500,
        }
    ]

    def cost_fields(job: dict) -> dict:
        contract = float(job.get("awarded_amount") or 0)
        actual = float(job.get("actual_cost") or 0)
        profit = contract - actual
        margin = round((profit / contract) * 100.0, 1) if contract > 0 else 0.0
        return {
            "contract_value": contract,
            "actual_cost": actual,
            "profit": profit,
            "margin_pct": margin,
            "has_contract": contract > 0,
            "raw_summary": {},
        }

    html_out = build_jobs_html_table(
        rows,
        visible_markers=("num", "desc", "customer", "status", "contract", "actual", "profit", "profit_pct"),
        cost_fields_fn=cost_fields,
    )
    assert "CONTRACT VALUE" in html_out
    assert "ACTUAL COST" in html_out
    assert "EST. PROFIT" in html_out
    assert "PROFIT %" in html_out
    assert "$10,000.00" in html_out
    assert "$500.00" in html_out
    assert "$9,500.00" in html_out
    assert "95.0%" in html_out
    assert "ips-jobs-profit-pct-green" in html_out


def test_build_jobs_html_table_shows_zero_actual_cost():
    rows = [{"id": "j-1", "job_number": "J100", "status": "Active"}]

    def cost_fields(_job: dict) -> dict:
        return {
            "contract_value": 0.0,
            "actual_cost": 0.0,
            "profit": 0.0,
            "margin_pct": 0.0,
            "has_contract": False,
            "raw_summary": {},
        }

    html_out = build_jobs_html_table(
        rows,
        visible_markers=("num", "status", "actual"),
        cost_fields_fn=cost_fields,
    )
    assert "$0.00" in html_out


def test_build_jobs_html_table_includes_actions_and_links():
    rows = [
        {
            "id": "j-1",
            "job_number": "J100",
            "job_name": "Test project",
            "customer_name": "Acme",
            "status": "Active",
            "estimated_cost": 1000,
            "actual_cost": 500,
        }
    ]

    def cost_fields(job: dict) -> dict:
        return {
            "estimated_cost": float(job.get("estimated_cost") or 0),
            "actual_cost": float(job.get("actual_cost") or 0),
            "has_estimated": True,
            "has_actual": True,
            "raw_summary": {},
        }

    html_out = build_jobs_html_table(
        rows,
        visible_markers=("num", "desc", "customer", "status"),
        cost_fields_fn=cost_fields,
    )
    assert "ips-dash-est-html-table" in html_out
    assert "ACTIONS" in html_out
    assert 'href="' in html_out
    assert "J100" in html_out
    assert "Test project" in html_out
    assert 'data-job-action="menu"' in html_out
