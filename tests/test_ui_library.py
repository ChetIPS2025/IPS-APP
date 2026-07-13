"""Tests for the shared IPS UI component library."""

from __future__ import annotations

import inspect
import unittest

from app.ui import kit
from app.ui import page_header as ui_page_header
from app.ui import status_badge as ui_status_badge


class UiLibraryTests(unittest.TestCase):
    def test_kit_exports_core_components(self) -> None:
        for name in (
            "inject_ips_ui_styles",
            "render_page_header",
            "render_data_table",
            "render_metric_card",
            "render_status_badge",
            "render_action_toolbar",
            "render_detail_header",
            "render_dialog_shell",
        ):
            self.assertTrue(hasattr(kit, name), msg=name)

    def test_page_header_is_self_contained(self) -> None:
        src = inspect.getsource(ui_page_header.render_page_header)
        self.assertIn("back_col, logo_col, title_col, actions_col", src)
        self.assertIn("inject_page_header_styles", src)
        self.assertIn("show_date_range", src)
        self.assertIn("show_refresh", src)
        self.assertNotIn('format="MMM D, YYYY"', src)

    def test_status_badge_normalizes_labels(self) -> None:
        html = ui_status_badge.status_badge_html("pending approval")
        self.assertIn("Pending Approval", html)
        self.assertIn("ips-status-badge", html)

    def test_styles_inject_once_guard(self) -> None:
        from app.ui.styles import IPS_UI_STYLES_KEY, inject_ips_ui_styles

        src = inspect.getsource(inject_ips_ui_styles)
        self.assertIn("IPS_UI_STYLES_KEY", src)
        self.assertEqual(IPS_UI_STYLES_KEY, "ips_ui_styles_v1")
        self.assertIn("ips-ui-library-v1", src)


if __name__ == "__main__":
    unittest.main()
