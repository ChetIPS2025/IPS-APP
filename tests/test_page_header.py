"""Tests for shared IPS page header and back navigation."""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components import headers
from app.navigation import IPS_NAV_HISTORY_KEY, navigate_back, set_nav_slug
from app.utils.constants import SESSION_NAV_KEY


class PageHeaderSourceTests(unittest.TestCase):
    def test_render_page_header_signature(self) -> None:
        sig = inspect.signature(headers.render_page_header)
        params = list(sig.parameters)
        self.assertIn("title", params)
        self.assertIn("subtitle", params)
        self.assertIn("icon", params)
        self.assertIn("actions", params)
        self.assertIn("show_back", params)

    def test_render_page_brand_header_delegates(self) -> None:
        src = inspect.getsource(headers.render_page_brand_header)
        self.assertIn("render_page_header", src)

    def test_default_subtitles_cover_core_modules(self) -> None:
        for slug in (
            "dashboard",
            "jobs",
            "customers",
            "inventory",
            "assets",
            "timekeeping",
            "reports",
            "employees",
        ):
            self.assertIn(slug, headers.DEFAULT_PAGE_SUBTITLES)


class NavHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_set_nav_slug_records_history(self) -> None:
        st.session_state[SESSION_NAV_KEY] = "dashboard"
        set_nav_slug("jobs")
        self.assertEqual(st.session_state[SESSION_NAV_KEY], "jobs")
        self.assertEqual(st.session_state[IPS_NAV_HISTORY_KEY], ["dashboard"])

    def test_navigate_back_restores_previous_slug(self) -> None:
        st.session_state[SESSION_NAV_KEY] = "jobs"
        st.session_state[IPS_NAV_HISTORY_KEY] = ["dashboard"]

        with patch.object(st, "rerun", MagicMock()) as rerun_mock:
            navigate_back()

        self.assertEqual(st.session_state[SESSION_NAV_KEY], "dashboard")
        self.assertEqual(st.session_state[IPS_NAV_HISTORY_KEY], [])
        rerun_mock.assert_called_once()

    def test_back_skip_does_not_push_history(self) -> None:
        st.session_state[SESSION_NAV_KEY] = "jobs"
        st.session_state[IPS_NAV_HISTORY_KEY] = ["dashboard"]
        st.session_state["_ips_nav_back_skip"] = True
        set_nav_slug("customers")
        self.assertEqual(st.session_state[IPS_NAV_HISTORY_KEY], ["dashboard"])


if __name__ == "__main__":
    unittest.main()
