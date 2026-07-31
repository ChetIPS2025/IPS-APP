"""Auth role resolution from profile and linked employee permission."""

from __future__ import annotations

import unittest

import streamlit as st

from app.auth import _normalized_role_from_session, current_role


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


if __name__ == "__main__":
    unittest.main()
