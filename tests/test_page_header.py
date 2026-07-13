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
        self.assertIn("ips-page-header-styles-v3", src)
        self.assertIn(".st-key-ips_page_header", src)
        self.assertIn(".st-key-header_primary_action", src)
        self.assertNotIn("position: absolute", src)
        self.assertNotIn("width: 100vw", src)

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
        self.assertIn("ips-global-styles-v16", src)
        self.assertNotIn("margin-left: -22px", src)
        self.assertNotIn("margin-right: -22px", src)


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
