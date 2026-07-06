"""Job Details modal layout helpers."""

from __future__ import annotations

from unittest.mock import patch

from app.components.job_detail_layout import build_job_detail_tab_labels, can_view_job_financial_tab


def test_job_detail_tab_labels_include_core_tabs():
    labels = build_job_detail_tab_labels({"id": "j1"})
    assert labels[0] == "Overview"
    assert labels[1].startswith("Tasks")
    assert "Schedule" in labels
    assert "Crew & Time" in labels
    assert "Activity" in labels


@patch("app.components.job_detail_layout.can_manage_job_actions", return_value=True)
def test_financial_tab_visible_for_managers(_mock_manage):
    labels = build_job_detail_tab_labels({"id": "j1"})
    assert "Financial" in labels
    assert can_view_job_financial_tab()


@patch("app.components.job_detail_layout.can_manage_job_actions", return_value=False)
def test_financial_tab_hidden_for_employees(_mock_manage):
    labels = build_job_detail_tab_labels({"id": "j1"})
    assert "Financial" not in labels
