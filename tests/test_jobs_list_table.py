"""Tests for Jobs list table HTML helpers."""

from __future__ import annotations

from app.components.jobs_list_table import job_list_link_html


def test_job_list_link_html_includes_action_and_id():
    html_out = job_list_link_html("j-123", "J26015", extra_class="ips-jobs-number-link")
    assert 'data-job-action="open"' in html_out
    assert 'data-job-id="j-123"' in html_out
    assert "J26015" in html_out
    assert "ips-jobs-number-link" in html_out
