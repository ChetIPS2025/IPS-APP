"""Employee Portal — permissions, data filtering, and role landing."""

from __future__ import annotations

from app.services.employee_portal_service import (
    list_active_jobs_for_employee,
    list_assigned_job_ids_for_employee,
    list_bidding_estimates_for_employee,
    list_portal_dashboard_jobs,
    portal_employee_avatar_html,
    portal_initials,
    resolve_employee_avatar_url,
    strip_estimate_for_employee,
    strip_job_for_employee,
    update_visible_to_role,
)
from app.utils.permissions import role_default_nav_slug


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
        "app.services.employee_portal_service._iter_active_job_rows",
        lambda **kwargs: [
            {"id": "1", "job_name": "Active", "customer": "X", "status": "Active"},
        ],
    )
    rows = list_active_jobs_for_employee()
    assert len(rows) == 1
    assert rows[0]["job_name"] == "Active"
    assert "awarded_amount" not in rows[0]


def test_bidding_estimates_exclude_pricing(monkeypatch):
    monkeypatch.setattr(
        "app.services.employee_portal_service._iter_bidding_estimate_rows",
        lambda **kwargs: [{"id": "1", "project_name": "Open", "status": "Sent"}],
    )
    rows = list_bidding_estimates_for_employee()
    assert len(rows) == 1
    assert rows[0]["project_name"] == "Open"
    assert "total" not in rows[0]


def test_portal_initials_from_name():
    assert portal_initials("Chance Burgess") == "CB"
    assert portal_initials("Titus") == "TI"


def test_resolve_employee_avatar_url_prefers_http():
    profile = {"photo_url": "https://cdn.example.com/me.jpg", "avatar_url": ""}
    assert resolve_employee_avatar_url(profile) == "https://cdn.example.com/me.jpg"


def test_portal_employee_avatar_html_uses_initials_without_photo():
    html_out = portal_employee_avatar_html({"full_name": "Chance Burgess"}, None)
    assert "ips-ep-avatar-initials" in html_out
    assert "CB" in html_out
    assert "<img" not in html_out


def test_portal_employee_avatar_html_uses_profile_photo():
    html_out = portal_employee_avatar_html(
        {"full_name": "Chance Burgess", "photo_url": "https://cdn.example.com/me.jpg"},
        None,
    )
    assert 'class="ips-ep-avatar"' in html_out
    assert "https://cdn.example.com/me.jpg" in html_out


def test_assigned_job_ids_from_time_entries(monkeypatch):
    monkeypatch.setattr(
        "app.services.employee_portal_service._load_time_entries",
        lambda: [
            {"employee_id": "emp-a", "job_id": "j2", "work_date": "2026-07-01"},
            {"employee_id": "emp-a", "job_id": "j1", "work_date": "2026-07-08"},
            {"employee_id": "emp-b", "job_id": "j9", "work_date": "2026-07-08"},
        ],
    )
    assert list_assigned_job_ids_for_employee("emp-a") == ["j1", "j2"]


def test_employee_portal_quick_action_keys_are_unique_for_employee_role():
    from app.pages.employee_portal import _quick_action_button_key, build_employee_portal_quick_actions

    actions = [a for a in build_employee_portal_quick_actions("employee") if a.get("enabled")]
    keys = [
        _quick_action_button_key(
            str(a["action_id"]),
            employee_id="emp-42",
            view_mode="employee",
        )
        for a in actions
    ]
    assert len(keys) == len(set(keys))
    nav_slugs = [str(a["nav_slug"]) for a in actions]
    assert nav_slugs.count("employee_qr_scan") == 2


def test_portal_dashboard_jobs_assigned_first_and_limited(monkeypatch):
    monkeypatch.setattr(
        "app.services.employee_portal_service.list_assigned_job_ids_for_employee",
        lambda _eid: ["j3", "j1"],
    )
    monkeypatch.setattr(
        "app.services.employee_portal_service._fetch_jobs_by_ids",
        lambda ids: {jid: {"id": jid, "job_name": jid, "status": "Active"} for jid in ids},
    )
    monkeypatch.setattr(
        "app.services.employee_portal_service._iter_active_job_rows",
        lambda **kwargs: [
            {"id": "j2", "job_name": "Two", "status": "Active"},
            {"id": "j4", "job_name": "Four", "status": "Active"},
        ],
    )
    rows = list_portal_dashboard_jobs("emp-a", limit=4)
    assert len(rows) == 4
    assert [r["id"] for r in rows] == ["j3", "j1", "j2", "j4"]
    assert rows[0]["_portal_assigned"] is True
    assert rows[1]["_portal_assigned"] is True
    assert rows[2]["_portal_assigned"] is False
