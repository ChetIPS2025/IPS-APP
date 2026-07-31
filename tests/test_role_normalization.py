"""Role alias normalization for page access and navigation."""

from __future__ import annotations

import unittest

from app.auth import current_role
from app.utils.permissions import normalize_role, role_can_access_page
import streamlit as st


class TestRoleNormalization(unittest.TestCase):
    def test_administrator_maps_to_admin(self) -> None:
        self.assertEqual(normalize_role("Administrator"), "admin")
        self.assertTrue(role_can_access_page("Administrator", "timekeeping"))

    def test_owner_maps_to_admin(self) -> None:
        self.assertEqual(normalize_role("Owner"), "admin")
        self.assertTrue(role_can_access_page("owner", "weekly_timesheets"))

    def test_field_supervisor_maps_to_supervisor(self) -> None:
        self.assertEqual(normalize_role("Field Supervisor"), "supervisor")
        self.assertTrue(role_can_access_page("field supervisor", "timekeeping"))

    def test_office_manager_maps_to_project_manager(self) -> None:
        self.assertEqual(normalize_role("Office Manager"), "project manager")
        self.assertTrue(role_can_access_page("office manager", "jobs"))

    def test_unknown_role_still_viewer(self) -> None:
        self.assertEqual(normalize_role("Technician"), "viewer")
        self.assertFalse(role_can_access_page("Technician", "timekeeping"))

    def test_manager_auth_slug_maps_to_project_manager(self) -> None:
        self.assertEqual(normalize_role("manager"), "project manager")
        self.assertTrue(role_can_access_page("manager", "timekeeping"))

    def test_current_role_uses_shared_normalizer(self) -> None:
        st.session_state.clear()
        st.session_state["auth_profile"] = {"role": "Administrator", "id": "u1"}
        self.assertEqual(current_role(), "admin")


if __name__ == "__main__":
    unittest.main()
