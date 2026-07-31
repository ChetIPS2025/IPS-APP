"""Settings page module wiring."""

from __future__ import annotations

import unittest

from app.phase2 import _resolve_module_render


class TestSettingsPageModule(unittest.TestCase):
    def test_settings_module_exposes_render(self) -> None:
        fn = _resolve_module_render("settings")
        self.assertIsNotNone(fn)
        self.assertEqual(fn.__name__, "render")

    def test_settings_render_calls_admin_settings_page(self) -> None:
        from unittest.mock import patch

        from app.pages.settings import render

        with patch("app.pages.settings.render_settings_page") as settings_mock:
            render()
        settings_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
