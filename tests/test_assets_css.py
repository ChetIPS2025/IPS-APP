"""Tests for tab-scoped Assets page CSS injection."""

from __future__ import annotations

import unittest
from unittest.mock import patch


class TestAssetsPageCss(unittest.TestCase):
    @patch("app.components.assets_css.inject_assets_detail_css")
    @patch("app.components.assets_css.inject_assets_hand_tools_css")
    @patch("app.components.assets_css.inject_assets_serialized_css")
    @patch("app.components.assets_css.inject_assets_equipment_css")
    @patch("app.components.assets_css.inject_assets_shared_module_css")
    @patch("app.components.assets_css.inject_assets_shell_css")
    def test_equipment_tab_injects_equipment_bundle_only(
        self,
        mock_shell,
        mock_shared,
        mock_equipment,
        mock_serialized,
        mock_hand_tools,
        mock_detail,
    ) -> None:
        from app.components.assets_css import inject_assets_page_css

        inject_assets_page_css("Equipment", detail_open=False)

        mock_shell.assert_called_once()
        mock_shared.assert_called_once()
        mock_equipment.assert_called_once()
        mock_serialized.assert_not_called()
        mock_hand_tools.assert_not_called()
        mock_detail.assert_not_called()

    @patch("app.components.assets_css.inject_assets_detail_css")
    @patch("app.components.assets_css.inject_assets_hand_tools_css")
    @patch("app.components.assets_css.inject_assets_serialized_css")
    @patch("app.components.assets_css.inject_assets_equipment_css")
    @patch("app.components.assets_css.inject_assets_shared_module_css")
    @patch("app.components.assets_css.inject_assets_shell_css")
    def test_serialized_tab_injects_serialized_bundle_only(
        self,
        mock_shell,
        mock_shared,
        mock_equipment,
        mock_serialized,
        mock_hand_tools,
        mock_detail,
    ) -> None:
        from app.components.assets_css import inject_assets_page_css

        inject_assets_page_css("Serialized Tools", detail_open=False)

        mock_shell.assert_called_once()
        mock_shared.assert_called_once()
        mock_serialized.assert_called_once()
        mock_equipment.assert_not_called()
        mock_hand_tools.assert_not_called()
        mock_detail.assert_not_called()

    @patch("app.components.assets_css.inject_assets_detail_css")
    @patch("app.components.assets_css.inject_assets_hand_tools_css")
    @patch("app.components.assets_css.inject_assets_serialized_css")
    @patch("app.components.assets_css.inject_assets_equipment_css")
    @patch("app.components.assets_css.inject_assets_shared_module_css")
    @patch("app.components.assets_css.inject_assets_shell_css")
    def test_hand_tools_tab_injects_hand_tools_bundle_only(
        self,
        mock_shell,
        mock_shared,
        mock_equipment,
        mock_serialized,
        mock_hand_tools,
        mock_detail,
    ) -> None:
        from app.components.assets_css import inject_assets_page_css

        inject_assets_page_css("Small Tools", detail_open=False)

        mock_shell.assert_called_once()
        mock_shared.assert_called_once()
        mock_hand_tools.assert_called_once()
        mock_equipment.assert_not_called()
        mock_serialized.assert_not_called()
        mock_detail.assert_not_called()

    def test_hand_tools_css_includes_overflow_fix(self) -> None:
        from app.components.assets_css import HAND_TOOLS_TABLE_FIX_CSS, HAND_TOOLS_TABLE_GRID

        self.assertIn("--ips-hand-tools-grid", HAND_TOOLS_TABLE_FIX_CSS)
        self.assertIn(HAND_TOOLS_TABLE_GRID.strip(), HAND_TOOLS_TABLE_FIX_CSS)
        self.assertIn("grid-template-columns: var(--ips-hand-tools-grid)", HAND_TOOLS_TABLE_FIX_CSS)
        self.assertIn("overflow-x: auto", HAND_TOOLS_TABLE_FIX_CSS)
        self.assertNotIn("word-break: break-word", HAND_TOOLS_TABLE_FIX_CSS)

    @patch("app.components.assets_css.inject_assets_detail_css")
    @patch("app.components.assets_css.inject_assets_equipment_css")
    @patch("app.components.assets_css.inject_assets_shared_module_css")
    @patch("app.components.assets_css.inject_assets_shell_css")
    def test_detail_open_adds_detail_css(
        self,
        mock_shell,
        mock_shared,
        mock_equipment,
        mock_detail,
    ) -> None:
        from app.components.assets_css import inject_assets_page_css

        inject_assets_page_css("Equipment", detail_open=True)

        mock_detail.assert_called_once()

    @patch("app.components.assets_css.inject_assets_detail_css")
    @patch("app.components.assets_css.inject_assets_hand_tools_css")
    @patch("app.components.assets_css.inject_assets_serialized_css")
    @patch("app.components.assets_css.inject_assets_equipment_css")
    @patch("app.components.assets_css.inject_assets_shared_module_css")
    @patch("app.components.assets_css.inject_assets_shell_css")
    def test_legacy_page_styles_injects_all_bundles(
        self,
        mock_shell,
        mock_shared,
        mock_equipment,
        mock_serialized,
        mock_hand_tools,
        mock_detail,
    ) -> None:
        from app.ui.assets_components import inject_assets_page_styles

        inject_assets_page_styles()

        mock_shell.assert_called_once()
        mock_shared.assert_called_once()
        mock_equipment.assert_called_once()
        mock_serialized.assert_called_once()
        mock_hand_tools.assert_called_once()
        mock_detail.assert_called_once()

    @patch("app.components.assets_css.inject_assets_equipment_css")
    @patch("app.components.assets_css.inject_assets_shell_css")
    def test_legacy_layout_css_injects_shell_and_equipment(
        self,
        mock_shell,
        mock_equipment,
    ) -> None:
        from app.components.assets_page_layout import inject_assets_page_layout_css

        inject_assets_page_layout_css()

        mock_shell.assert_called_once()
        mock_equipment.assert_called_once()


    @patch("app.components.assets_css.inject_assets_hand_tools_css")
    @patch("app.components.assets_css.inject_assets_serialized_css")
    @patch("app.components.assets_css.inject_assets_equipment_css")
    @patch("app.components.assets_css.inject_assets_shared_module_css")
    def test_legacy_module_css_injects_all_module_bundles(
        self,
        mock_shared,
        mock_equipment,
        mock_serialized,
        mock_hand_tools,
    ) -> None:
        from app.styles import inject_assets_module_css

        inject_assets_module_css()

        mock_shared.assert_called_once()
        mock_equipment.assert_called_once()
        mock_serialized.assert_called_once()
        mock_hand_tools.assert_called_once()


if __name__ == "__main__":
    unittest.main()
