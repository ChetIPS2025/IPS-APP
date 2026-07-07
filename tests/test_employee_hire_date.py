"""Tests for editable employee hire date."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from app.services.phase2_modules_service import _parse_employee_hire_date, normalize_employee, save_employee
from app.services.users_service import can_edit_employee_profile
from app.utils.formatting import fmt_date


class TestEmployeeHireDate(unittest.TestCase):
    def test_normalize_empty_hire_date_renders_dash(self) -> None:
        row = {"id": "e1", "name": "Pat", "hire_date": None, "created_at": "2020-01-15"}
        emp = normalize_employee(row)
        self.assertEqual(emp["hire_date"], "—")
        self.assertEqual(fmt_date(emp.get("hire_date")), "—")

    def test_member_since_does_not_use_hire_date(self) -> None:
        row = {
            "id": "e1",
            "name": "Pat",
            "hire_date": "2024-06-01",
            "created_at": "2020-01-15T12:00:00",
        }
        emp = normalize_employee(row)
        self.assertEqual(emp["member_since"], "2020-01-15")
        self.assertEqual(emp["hire_date"], "2024-06-01")

    def test_parse_hire_date_valid_and_clear(self) -> None:
        iso, err = _parse_employee_hire_date(date(2021, 5, 13))
        self.assertIsNone(err)
        self.assertEqual(iso, "2021-05-13")
        cleared, clear_err = _parse_employee_hire_date(None)
        self.assertIsNone(clear_err)
        self.assertIsNone(cleared)
        cleared2, clear_err2 = _parse_employee_hire_date("")
        self.assertIsNone(clear_err2)
        self.assertIsNone(cleared2)

    def test_parse_hire_date_invalid(self) -> None:
        iso, err = _parse_employee_hire_date("not-a-date")
        self.assertIsNone(iso)
        self.assertIn("valid date", str(err or "").lower())

    @patch("app.services.phase2_modules_service.update_row_admin")
    @patch("app.services.users_service.can_edit_employee_profile", return_value=True)
    @patch("app.services.employee_role_service.sync_linked_profile_permission_role", return_value=None)
    def test_save_employee_persists_hire_date(self, _sync, _can, update_mock) -> None:
        update_mock.return_value = type("R", (), {"ok": True, "data": {"id": "emp-1"}})()
        result = save_employee(
            {
                "name": "Pat",
                "email": "pat@example.com",
                "status": "Active",
                "hire_date": date(2022, 3, 4),
            },
            row_id="emp-1",
        )
        self.assertTrue(result.ok)
        payload = update_mock.call_args[0][1]
        self.assertEqual(payload["hire_date"], "2022-03-04")

    @patch("app.services.phase2_modules_service.update_row_admin")
    @patch("app.services.users_service.can_edit_employee_profile", return_value=True)
    @patch("app.services.employee_role_service.sync_linked_profile_permission_role", return_value=None)
    def test_save_employee_reports_missing_row(self, _sync, _can, update_mock) -> None:
        update_mock.return_value = type("R", (), {"ok": True, "data": None})()
        result = save_employee({"name": "Pat", "status": "Active"}, row_id="emp-missing")
        self.assertFalse(result.ok)
        self.assertIn("not found", str(result.error or "").lower())

    @patch("app.services.users_service.can_edit_employee_profile", return_value=False)
    def test_save_employee_unauthorized(self, _can) -> None:
        result = save_employee({"name": "Pat", "hire_date": "2022-03-04"}, row_id="emp-1")
        self.assertFalse(result.ok)
        self.assertIn("permission", str(result.error or "").lower())

    @patch("app.auth.current_role", return_value="employee")
    def test_can_edit_employee_profile_denies_employee(self, _role) -> None:
        self.assertFalse(can_edit_employee_profile())

    @patch("app.auth.current_role", return_value="admin")
    def test_can_edit_employee_profile_allows_admin(self, _role) -> None:
        self.assertTrue(can_edit_employee_profile())


if __name__ == "__main__":
    unittest.main()
