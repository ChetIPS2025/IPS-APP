"""Layout constants for the Assets Small Hand Tools table."""

from __future__ import annotations

import unittest


class TestSmallHandToolsTableLayout(unittest.TestCase):
    def test_eight_column_specs_match_grid(self) -> None:
        from app.components.assets_css import HAND_TOOLS_TABLE_GRID
        from app.components.small_hand_tools_ui import _COLS, _HEADER_SPECS

        self.assertEqual(len(_COLS), 8)
        self.assertEqual(len(_HEADER_SPECS), 8)
        self.assertEqual(_HEADER_SPECS[0][0], "Tool")
        self.assertEqual(_HEADER_SPECS[-1][0], "Actions")
        self.assertEqual(len(HAND_TOOLS_TABLE_GRID.split("minmax(")) - 1, 8)

    def test_hand_tools_css_uses_shared_grid_variable(self) -> None:
        from app.components.assets_css import HAND_TOOLS_TABLE_FIX_CSS

        self.assertIn("--ips-hand-tools-grid", HAND_TOOLS_TABLE_FIX_CSS)
        self.assertIn("grid-template-columns: var(--ips-hand-tools-grid)", HAND_TOOLS_TABLE_FIX_CSS)
        self.assertIn("grid-template-columns: 40px minmax(0, 1fr)", HAND_TOOLS_TABLE_FIX_CSS)
        self.assertNotIn("word-break: break-word", HAND_TOOLS_TABLE_FIX_CSS)


if __name__ == "__main__":
    unittest.main()
