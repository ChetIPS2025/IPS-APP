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

    def test_render_page_header_uses_four_column_layout(self) -> None:
        from app.ui import page_header as ui_page_header

        src = inspect.getsource(ui_page_header)
        render_src = inspect.getsource(ui_page_header.render_page_header)
        self.assertIn("back_col, logo_col, title_col, actions_col", render_src)
        self.assertIn("header_primary_action", render_src)
        self.assertIn("header_date_range", src)
        self.assertIn("height=56", render_src)
        self.assertIn("ips_page_header", render_src)
        self.assertIn('format="MM/DD/YYYY"', src)
        self.assertNotIn('format="MMM D, YYYY"', src)
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

    def test_headers_module_delegates_to_ui_page_header(self) -> None:
        from app.components import headers

        src = inspect.getsource(headers.render_page_header)
        self.assertIn("app.ui.page_header", src)

    def test_page_header_styles_are_scoped(self) -> None:
        from app.ui.page_header_styles import inject_page_header_styles

        src = inspect.getsource(inject_page_header_styles)
        self.assertIn("ips-page-header-styles-v14", src)
        self.assertIn("body.ips-authed-app section[data-testid=\"stMain\"]", src)
        self.assertIn("st-key-header_page_toolbar", src)
        self.assertIn('[class*="st-key-ips_page_header"]', src)
        self.assertIn(".st-key-header_primary_action", src)
        self.assertIn(".st-key-header_secondary_action", src)
        self.assertIn("st-key-header_help [data-testid=\"stPopover\"]", src)
        self.assertIn("ips-header-notify-badge", src)
        self.assertIn("background: transparent !important", src)
        self.assertIn("stIconMaterial", src)
        self.assertNotIn("width: 100vw", src)

    def test_header_utility_buttons_use_icon_only_labels(self) -> None:
        from app.ui import page_header as ui_page_header

        src = inspect.getsource(ui_page_header)
        self.assertIn('st.button("🔄"', src)
        self.assertIn('st.button("🔔"', src)
        self.assertIn('st.popover("❓"', src)
        self.assertIn('st.button("⚙️"', src)
        self.assertNotIn("🔔 {int(unread)}", src)

    def test_full_page_detail_skips_duplicate_modal_header(self) -> None:
        from app.pages import customers as customers_page
        from app.pages import estimates as estimates_page

        est_src = inspect.getsource(estimates_page.render_estimate_detail_dialog)
        self.assertIn("page_mode", est_src)
        self.assertIn("if not page_mode:", est_src)

        cust_src = inspect.getsource(customers_page.render_customer_detail_dialog)
        self.assertIn("page_mode", cust_src)
        self.assertIn("if not page_mode:", cust_src)

        inv_src = inspect.getsource(__import__("app.pages.inventory_scan", fromlist=["render"]).render)
        self.assertNotIn("st.title", inv_src)

    def test_date_range_label_formats_like_mockup(self) -> None:
        from datetime import date

        from app.ui.page_header import _format_date_range_label

        self.assertEqual(
            _format_date_range_label(date(2026, 7, 13), date(2026, 7, 19)),
            "Jul 13 – Jul 19, 2026",
        )

    def test_global_header_css_avoids_negative_margins(self) -> None:
        from app.styles import inject_global_css

        src = inspect.getsource(inject_global_css)
        self.assertIn("ips-global-styles-v18", src)
        self.assertIn("padding-top: 0 !important", src)
        self.assertNotIn("margin-left: -22px", src)
        self.assertNotIn("margin-right: -22px", src)

    def test_global_css_injects_from_sidebar(self) -> None:
        from app.styles import inject_global_css

        src = inspect.getsource(inject_global_css)
        self.assertIn("with st.sidebar:", src)

    def test_page_header_styles_inject_from_sidebar(self) -> None:
        from app.ui.page_header_styles import inject_page_header_styles

        src = inspect.getsource(inject_page_header_styles)
        self.assertIn("with st.sidebar:", src)

    def test_app_shell_script_uses_st_html_for_inline_js(self) -> None:
        from app.ui.app_shell_styles import inject_app_shell_script

        src = inspect.getsource(inject_app_shell_script)
        self.assertIn("st.html", src)
        self.assertIn("unsafe_allow_javascript=True", src)

    def test_authenticated_shell_css_injects_from_sidebar(self) -> None:
        from app.styles import inject_authenticated_shell_css

        src = inspect.getsource(inject_authenticated_shell_css)
        self.assertIn("with st.sidebar:", src)
        self.assertIn("inject_app_shell_script", src)

    def test_app_shell_layout_styles_reset_main_top_gap(self) -> None:
        from app.ui.app_shell_styles import inject_app_shell_layout_styles

        src = inspect.getsource(inject_app_shell_layout_styles)
        self.assertIn("ips-app-shell-layout-v5", src)
        self.assertIn("stMainBlockContainer", src)
        self.assertIn("padding-top: var(--ips-main-top-gap)", src)
        self.assertIn("ips-app-shell-script-marker", src)
        self.assertIn("stIFrame", src)
        self.assertNotIn("margin-top: -", src)
        self.assertNotIn("translateY", src)
        self.assertNotIn("position: absolute", src)

    def test_page_header_uses_dynamic_action_slots(self) -> None:
        from app.ui.page_header import _action_slot_columns

        names, ratios = _action_slot_columns(
            show_date_range=False,
            show_refresh=False,
            has_secondary_action=True,
            has_primary_action=True,
        )
        self.assertEqual(names, ["primary", "secondary", "notification", "help", "settings", "avatar"])
        self.assertEqual(len(ratios), 6)

    def test_page_header_uses_dynamic_action_slots_without_secondary(self) -> None:
        from app.ui.page_header import _action_slot_columns

        names, ratios = _action_slot_columns(
            show_date_range=False,
            show_refresh=False,
            has_secondary_action=False,
            has_primary_action=False,
        )
        self.assertEqual(names, ["notification", "help", "settings", "avatar"])
        self.assertEqual(len(ratios), 4)

    def test_page_header_uses_slug_specific_container_key(self) -> None:
        from app.ui.page_header import render_page_header

        src = inspect.getsource(render_page_header)
        self.assertIn('key=f"ips_page_header_{slug}"', src)

    def test_pre_header_cleanup_targets_page_level_siblings_only(self) -> None:
        from app.ui.app_shell_styles import _app_shell_pre_header_cleanup_script

        src = _app_shell_pre_header_cleanup_script()
        self.assertIn("pageRootVertical", src)
        self.assertIn("stMainBlockContainer", src)
        self.assertIn('class*="st-key-ips_page_header"', src)
        self.assertNotIn("setTimeout(run, 500)", src)

    def test_page_header_primary_action_width_override(self) -> None:
        from app.ui.page_header import _action_slot_columns

        names, ratios = _action_slot_columns(
            show_date_range=False,
            show_refresh=False,
            has_secondary_action=False,
            has_primary_action=True,
            primary_action_width=5.8,
        )
        self.assertEqual(names[0], "primary")
        self.assertEqual(ratios[0], 5.8)

    def test_scroll_preserve_injects_from_sidebar(self) -> None:
        from app.ui.streamlit_perf import inject_scroll_preserve

        src = inspect.getsource(inject_scroll_preserve)
        self.assertIn("with st.sidebar:", src)


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
