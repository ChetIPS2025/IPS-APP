"""Tests for Jobs list table HTML helpers."""

from __future__ import annotations

from app.components.jobs_list_table import (
    build_jobs_html_table,
    handle_jobs_table_action,
    job_list_link_html,
)


def test_job_list_link_html_includes_action_and_id():
    html_out = job_list_link_html(
        "j-123",
        "J26015",
        extra_class="ips-jobs-number-link",
        bridge_key="job_bridge_open_j123",
    )
    assert 'data-job-action="open"' in html_out
    assert 'data-job-id="j-123"' in html_out
    assert 'data-row-id="j-123"' in html_out
    assert 'data-bridge-key="job_bridge_open_j123"' in html_out
    assert "J26015" in html_out
    assert "ips-jobs-number-link" in html_out
    assert "ips-dash-est-link" in html_out
    assert "ips-row-open-link" in html_out
    assert '<button type="button"' in html_out
    assert "ips-jobs-open-link" in html_out


def test_handle_jobs_table_action_strips_open_prefix():
    opened: list[tuple[str, dict]] = []

    handle_jobs_table_action(
        "open:j-123",
        {"j-123": {"id": "j-123", "job_number": "J26015"}},
        last_action_key="jobs_test_last_action",
        open_job_fn=lambda job_id, job: opened.append((job_id, job)),
    )

    assert opened == [("j-123", {"id": "j-123", "job_number": "J26015"})]


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
    assert 'data-job-action="open"' in html_out
    assert "J100" in html_out
    assert "Test project" in html_out
    assert 'data-job-action="menu"' in html_out
