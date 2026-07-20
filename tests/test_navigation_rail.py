"""Desktop nav rail and first-click module navigation tests."""

from __future__ import annotations

import inspect
import unittest
from unittest import mock

import streamlit as st

from app.components.sidebar_shell import (
    IPS_NAV_QUERY_APPLIED_KEY,
    STALE_MODULE_DETAIL_QUERY_KEYS,
    _desktop_nav_rail_click_script,
    _desktop_nav_rail_html,
    capture_nav_slug_from_query,
    sidebar_nav_href,
)
from app.navigation import IPS_NAV_HISTORY_KEY, IPS_NAV_PENDING_KEY
from app.utils.constants import SESSION_NAV_KEY


class TestDesktopNavRailHtml(unittest.TestCase):
    def test_timekeeping_link_uses_direct_href(self) -> None:
        rows = [{"slug": "timekeeping", "label": "Timekeeping", "icon": "⏱"}]
        markup = _desktop_nav_rail_html(rows, "dashboard")
        self.assertIn('href="?ips_nav=timekeeping"', markup)
        self.assertIn('target="_self"', markup)
        self.assertNotIn('data-ips-rail-slug="timekeeping" href="#"', markup.replace("\n", " "))

    def test_sidebar_nav_href_urlencodes_slug(self) -> None:
        self.assertEqual(sidebar_nav_href("timekeeping"), "?ips_nav=timekeeping")
        self.assertEqual(sidebar_nav_href("scan inventory"), "?ips_nav=scan+inventory")

    def test_rail_script_does_not_bridge_hidden_sidebar_buttons(self) -> None:
        script = _desktop_nav_rail_click_script()
        self.assertNotIn("st-key-nav_", script)
        self.assertNotIn("sidebarNavButton", script)
        self.assertNotIn("data-ips-rail-slug", script)
        self.assertIn("data-ips-rail-logout", script)

    def test_other_module_links_use_direct_hrefs(self) -> None:
        slugs = (
            "jobs",
            "customers",
            "estimates",
            "inventory",
            "assets",
            "scheduling",
            "tasks",
            "reports",
        )
        rows = [{"slug": slug, "label": slug.title(), "icon": "•"} for slug in slugs]
        markup = _desktop_nav_rail_html(rows, "dashboard")
        for slug in slugs:
            self.assertIn(f'href="?ips_nav={slug}"', markup)


class TestFirstClickNavigation(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()
        st.query_params.clear()

    def test_dashboard_to_timekeeping_first_click(self) -> None:
        st.session_state[SESSION_NAV_KEY] = "dashboard"
        st.query_params["ips_nav"] = "timekeeping"
        capture_nav_slug_from_query()
        self.assertEqual(st.session_state[SESSION_NAV_KEY], "timekeeping")
        self.assertNotIn("ips_nav", st.query_params)

    def test_query_capture_clears_stale_detail_params(self) -> None:
        st.session_state[SESSION_NAV_KEY] = "customers"
        st.query_params.update(
            {
                "ips_nav": "timekeeping",
                "customer_detail": "cust-1",
                "contact_detail": "ct-1",
            }
        )
        capture_nav_slug_from_query()
        self.assertEqual(st.session_state[SESSION_NAV_KEY], "timekeeping")
        self.assertNotIn("customer_detail", st.query_params)
        self.assertNotIn("contact_detail", st.query_params)
        for key in STALE_MODULE_DETAIL_QUERY_KEYS:
            self.assertNotIn(key, st.query_params)

    def test_pending_navigation_does_not_block_timekeeping_query(self) -> None:
        st.session_state[IPS_NAV_PENDING_KEY] = "Jobs"
        st.query_params["ips_nav"] = "timekeeping"
        capture_nav_slug_from_query()
        self.assertEqual(st.session_state[SESSION_NAV_KEY], "timekeeping")
        self.assertNotIn(IPS_NAV_PENDING_KEY, st.session_state)

    def test_nav_query_guard_clears_after_follow_up_run(self) -> None:
        st.session_state[SESSION_NAV_KEY] = "dashboard"
        st.query_params["ips_nav"] = "timekeeping"
        capture_nav_slug_from_query()
        self.assertEqual(st.session_state.get(IPS_NAV_QUERY_APPLIED_KEY), "timekeeping")
        capture_nav_slug_from_query()
        self.assertNotIn(IPS_NAV_QUERY_APPLIED_KEY, st.session_state)

    def test_navigation_history_records_previous_module_once(self) -> None:
        st.session_state[SESSION_NAV_KEY] = "dashboard"
        st.query_params["ips_nav"] = "timekeeping"
        capture_nav_slug_from_query()
        history = list(st.session_state.get(IPS_NAV_HISTORY_KEY) or [])
        self.assertEqual(history, ["dashboard"])


class TestNavigationMainFlow(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()
        st.query_params.clear()

    def test_main_query_capture_does_not_require_second_click(self) -> None:
        from app.navigation import apply_pending_navigation, current_nav_slug, ensure_nav_defaults
        from app.components.sidebar_shell import capture_nav_slug_from_query

        st.session_state[SESSION_NAV_KEY] = "dashboard"
        st.query_params["ips_nav"] = "timekeeping"
        apply_pending_navigation()
        capture_nav_slug_from_query()
        ensure_nav_defaults()
        slug = current_nav_slug()
        st.session_state[SESSION_NAV_KEY] = slug
        self.assertEqual(slug, "timekeeping")
        self.assertEqual(st.session_state[SESSION_NAV_KEY], "timekeeping")
        self.assertNotIn("ips_nav", st.query_params)


class TestViewAsTimekeepingNavigation(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_supervisor_preview_keeps_timekeeping(self) -> None:
        from app.utils.view_as import ensure_view_as_navigation, set_view_as

        nav_calls: list[str] = []

        with mock.patch("app.utils.view_as.current_role", return_value="admin"):
            with mock.patch("app.navigation.set_nav_slug", side_effect=lambda slug: nav_calls.append(slug)):
                set_view_as("supervisor")
                nav_calls.clear()
                st.session_state[SESSION_NAV_KEY] = "timekeeping"
                ensure_view_as_navigation()
        self.assertEqual(nav_calls, [])

    def test_admin_preview_keeps_timekeeping(self) -> None:
        from app.utils.view_as import ensure_view_as_navigation

        nav_calls: list[str] = []
        st.session_state[SESSION_NAV_KEY] = "timekeeping"
        with mock.patch("app.utils.view_as.is_view_as_active", return_value=False):
            with mock.patch("app.navigation.set_nav_slug", side_effect=lambda slug: nav_calls.append(slug)):
                ensure_view_as_navigation()
        self.assertEqual(nav_calls, [])


class TestEnsureNavDefaults(unittest.TestCase):
    def test_ensure_nav_defaults_does_not_replace_existing_timekeeping(self) -> None:
        from app.navigation import ensure_nav_defaults

        st.session_state.clear()
        st.session_state[SESSION_NAV_KEY] = "timekeeping"
        ensure_nav_defaults()
        self.assertEqual(st.session_state[SESSION_NAV_KEY], "timekeeping")


class TestSidebarNavButtons(unittest.TestCase):
    def test_sidebar_uses_single_set_nav_slug_and_rerun(self) -> None:
        from app.components import sidebar as sidebar_mod

        src = inspect.getsource(sidebar_mod._render_sidebar_body)
        self.assertIn("set_nav_slug(slug)", src)
        self.assertIn("st.rerun()", src)
        self.assertNotIn("capture_nav_slug_from_query", src)


if __name__ == "__main__":
    unittest.main()
