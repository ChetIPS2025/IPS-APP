"""Employee Portal — permissions, data filtering, and role landing."""

from __future__ import annotations

from app.services.employee_portal_service import (
    list_active_jobs_for_employee,
    list_bidding_estimates_for_employee,
    strip_estimate_for_employee,
    strip_job_for_employee,
    update_visible_to_role,
)
from app.utils.permissions import normalize_role, role_default_nav_slug


def test_employee_lands_on_portal():
    assert role_default_nav_slug("employee") == "employee_portal"


def test_supervisor_lands_on_field_dashboard():
    assert role_default_nav_slug("supervisor") == "field_dashboard"


def test_admin_lands_on_dashboard():
    assert role_default_nav_slug("admin") == "dashboard"


def test_strip_job_removes_financial_fields():
    raw = {
        "id": "j1",
        "job_name": "Test Job",
        "customer": "Acme",
        "awarded_amount": 99999.0,
        "estimated_cost": 50000.0,
        "projected_gross_profit": 12000.0,
        "status": "Active",
    }
    safe = strip_job_for_employee(raw)
    assert "awarded_amount" not in safe
    assert "estimated_cost" not in safe
    assert "projected_gross_profit" not in safe
    assert safe["job_name"] == "Test Job"


def test_strip_estimate_removes_pricing_fields():
    raw = {
        "id": "e1",
        "project_name": "Bid",
        "customer": "Acme",
        "total": 45000.0,
        "customer_price": 52000.0,
        "markup": 8000.0,
        "status": "Sent",
    }
    safe = strip_estimate_for_employee(raw)
    assert "total" not in safe
    assert "customer_price" not in safe
    assert "markup" not in safe
    assert safe["project_name"] == "Bid"


def test_update_visible_to_role_for_employees():
    all_row = {"title": "All hands", "audience": "All", "status": "Published", "is_active": True}
    emp_row = {"title": "Field note", "audience": "Employees", "status": "Published", "is_active": True}
    admin_row = {"title": "Admin only", "audience": "Admin", "status": "Published", "is_active": True}
    assert update_visible_to_role(all_row, "employee") is True
    assert update_visible_to_role(emp_row, "employee") is True
    assert update_visible_to_role(admin_row, "employee") is False


def test_active_jobs_for_employee_exclude_financials(monkeypatch):
    monkeypatch.setattr(
        "app.pages._core._data.load_jobs",
        lambda: [
            {
                "id": "1",
                "job_name": "Active",
                "customer": "X",
                "status": "Active",
                "awarded_amount": 1000,
            },
            {"id": "2", "job_name": "Done", "customer": "X", "status": "Completed"},
        ],
    )
    rows = list_active_jobs_for_employee()
    assert len(rows) == 1
    assert rows[0]["job_name"] == "Active"
    assert "awarded_amount" not in rows[0]


def test_bidding_estimates_exclude_pricing(monkeypatch):
    monkeypatch.setattr(
        "app.pages._core._data.load_estimates",
        lambda: [
            {"id": "1", "project_name": "Open", "status": "Sent", "total": 9000},
            {"id": "2", "project_name": "Awarded", "status": "Awarded", "total": 9000},
        ],
    )
    rows = list_bidding_estimates_for_employee()
    assert len(rows) == 1
    assert rows[0]["project_name"] == "Open"
    assert "total" not in rows[0]
