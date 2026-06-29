"""Canonical status map helpers."""

from __future__ import annotations

from app.services.status_maps import (
    is_estimate_open_for_customer_count,
    is_job_open_for_customer_count,
    normalize_asset_status,
    normalize_task_status_label,
    task_status_filter_bucket,
    task_status_to_db,
)


def test_job_open_for_customer_count_uses_normalized_status():
    assert is_job_open_for_customer_count({"status": "Active", "is_deleted": False}) is True
    assert is_job_open_for_customer_count({"status": "Completed", "is_deleted": False}) is False
    assert is_job_open_for_customer_count({"status": "Awarded", "is_deleted": False}) is True


def test_estimate_open_for_customer_count_matches_active_view():
    assert is_estimate_open_for_customer_count({"status": "Sent"}) is True
    assert is_estimate_open_for_customer_count({"status": "Approved"}) is False
    assert is_estimate_open_for_customer_count({"status": "Draft"}) is True


def test_task_status_label_and_db():
    assert normalize_task_status_label("In Progress") == "In Progress"
    assert task_status_to_db("In Progress") == "In Progress"
    assert task_status_filter_bucket("In Progress") == "Open"
    assert task_status_filter_bucket("Done") == "Closed"
    assert task_status_to_db("Done") == "Complete"


def test_normalize_asset_status_maps_active_to_in_service():
    assert normalize_asset_status("active") == "In Service"
    assert normalize_asset_status("Available") == "Available"
