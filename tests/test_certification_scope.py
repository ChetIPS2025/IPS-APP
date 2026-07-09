"""Certification visibility scoped to logged-in employee."""

from __future__ import annotations

from app.services.certification_helpers import (
    can_delete_employee_certifications,
    can_manage_employee_certifications,
    certification_visible_to_user,
    resolve_logged_in_employee_id,
)


def test_resolve_logged_in_employee_id_from_profile_link():
    assert resolve_logged_in_employee_id({"employee_id": "emp-1", "email": "a@ips.com"}) == "emp-1"


def test_resolve_logged_in_employee_id_from_email(monkeypatch):
    monkeypatch.setattr(
        "app.services.certification_helpers.load_employees",
        lambda: [{"id": "emp-2", "email": "user@industrialplantsolution.com", "name": "User"}],
        raising=False,
    )
    monkeypatch.setattr(
        "app.pages._core._data.load_employees",
        lambda: [{"id": "emp-2", "email": "user@industrialplantsolution.com", "name": "User"}],
    )
    assert (
        resolve_logged_in_employee_id({"email": "user@industrialplantsolution.com"})
        == "emp-2"
    )


def test_employee_sees_only_own_certifications():
    cert = {"id": "c1", "employee_id": "emp-1", "cert_type": "Forklift"}
    assert certification_visible_to_user(cert, role="employee", viewer_employee_id="emp-1") is True
    assert certification_visible_to_user(cert, role="employee", viewer_employee_id="emp-2") is False


def test_supervisor_sees_all_certifications():
    cert = {"id": "c1", "employee_id": "emp-1", "cert_type": "Forklift"}
    assert certification_visible_to_user(cert, role="supervisor", viewer_employee_id="") is True
    assert can_manage_employee_certifications("project manager") is True
    assert can_manage_employee_certifications("employee") is False


def test_only_admin_can_delete_certifications():
    assert can_delete_employee_certifications("admin") is True
    assert can_delete_employee_certifications("supervisor") is False
    assert can_delete_employee_certifications("project manager") is False
    assert can_delete_employee_certifications("employee") is False


def test_cert_attachment_file_name_from_path():
    from app.pages.employee_certifications import _cert_attachment_file_name

    cert = {"attachment_path": "employee-certifications/c1/20260101_report.pdf"}
    assert _cert_attachment_file_name(cert) == "20260101_report.pdf"
    cert_named = {
        "attachment_path": "employee-certifications/c1/20260101_report.pdf",
        "attachment_file_name": "Forklift Card.pdf",
    }
    assert _cert_attachment_file_name(cert_named) == "Forklift Card.pdf"
