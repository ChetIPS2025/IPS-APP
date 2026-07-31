"""Timekeeping navigation and access regression tests."""

from __future__ import annotations

import unittest
from unittest import mock

import streamlit as st

from app.auth import _ensure_auth_employee_attached, current_role
from app.navigation import IPS_NAV_INTENT_KEY, normalize_nav_slug, set_nav_slug
from app.utils.constants import SESSION_NAV_KEY
from app.utils.permissions import role_can_access_page


class TestTimekeepingNavigationAccess(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_timekeeping_slug_aliases_resolve(self) -> None:
        self.assertEqual(normalize_nav_slug("time_reports"), "timekeeping")
        self.assertEqual(normalize_nav_slug("log_time"), "timekeeping")
        self.assertEqual(normalize_nav_slug("Timekeeping"), "timekeeping")

    def test_jobs_access_implies_timekeeping_access(self) -> None:
        self.assertTrue(role_can_access_page("manager", "jobs"))
        self.assertTrue(role_can_access_page("manager", "timekeeping"))
        self.assertTrue(role_can_access_page("manager", "weekly_timesheets"))

    def test_viewer_still_blocked_from_timekeeping_without_jobs(self) -> None:
        self.assertFalse(role_can_access_page("viewer", "timekeeping"))

    def test_set_nav_slug_records_intent(self) -> None:
        set_nav_slug("timekeeping")
        self.assertEqual(st.session_state[SESSION_NAV_KEY], "timekeeping")
        self.assertEqual(st.session_state[IPS_NAV_INTENT_KEY], "timekeeping")

    def test_query_capture_accepts_time_reports_alias(self) -> None:
        from app.components.sidebar_shell import capture_nav_slug_from_query

        st.session_state[SESSION_NAV_KEY] = "dashboard"

        class _QueryParams(dict):
            def get(self, key, default=None):
                if key == "ips_nav":
                    return "time_reports"
                return default

            def __delitem__(self, key):
                super().pop(key, None)

        with mock.patch.object(st, "query_params", _QueryParams()):
            capture_nav_slug_from_query()

        self.assertEqual(st.session_state[SESSION_NAV_KEY], "timekeeping")

    def test_employee_permission_refreshes_when_profile_role_is_weak(self) -> None:
        st.session_state["auth_profile"] = {
            "role": "Employee",
            "id": "u1",
            "employee_id": "e1",
        }
        st.session_state["auth_employee"] = {
            "id": "e1",
            "role": "Employee",
            "trade": "Welder",
        }

        with mock.patch("app.auth._lookup_linked_employee") as lookup_mock:
            lookup_mock.return_value = {
                "id": "e1",
                "role": "Admin",
                "trade": "Welder",
            }
            _ensure_auth_employee_attached()

        self.assertEqual(current_role(), "admin")
        self.assertEqual(st.session_state["auth_profile"]["role"], "admin")


if __name__ == "__main__":
    unittest.main()
