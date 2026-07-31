"""Auth role resolution from profile and linked employee permission."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import streamlit as st

from app.auth import _ensure_auth_employee_attached, _normalized_role_from_session, current_role


class TestAuthRoleResolution(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_employee_permission_upgrades_viewer_profile_role(self) -> None:
        st.session_state["auth_profile"] = {"role": "Welder", "id": "u1", "employee_id": "e1"}
        st.session_state["auth_employee"] = {
            "id": "e1",
            "role": "Admin",
            "trade": "Welder",
        }
        self.assertEqual(_normalized_role_from_session(), "admin")
        self.assertEqual(current_role(), "admin")

    def test_manager_profile_slug_keeps_timekeeping_access(self) -> None:
        st.session_state["auth_profile"] = {"role": "manager", "id": "u1"}
        self.assertEqual(current_role(), "project manager")

    @patch("app.auth._lookup_linked_employee")
    def test_missing_cached_employee_is_loaded_for_role_fallback(self, lookup_mock) -> None:
        st.session_state["auth_profile"] = {"role": "Employee", "id": "u1", "email": "chet@example.com"}
        lookup_mock.return_value = {"id": "e1", "role": "Admin", "email": "chet@example.com"}
        self.assertEqual(current_role(), "admin")
        lookup_mock.assert_called()

    @patch("app.auth._lookup_linked_employee")
    def test_ensure_auth_employee_attached_populates_session(self, lookup_mock) -> None:
        st.session_state["auth_profile"] = {"role": "Employee", "id": "u1"}
        lookup_mock.return_value = {"id": "e1", "role": "Admin"}
        _ensure_auth_employee_attached()
        self.assertEqual(st.session_state["auth_employee"]["id"], "e1")
        self.assertEqual(st.session_state["auth_profile"]["role"], "admin")


if __name__ == "__main__":
    unittest.main()
