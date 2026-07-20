"""Layout constants for the Assets Small Hand Tools HTML table."""

from __future__ import annotations

import unittest


class TestSmallHandToolsTableLayout(unittest.TestCase):
    def test_html_table_has_nine_columns(self) -> None:
        from app.components.small_hand_tools_list_table import (
            HAND_TOOLS_TABLE_COL_WIDTHS_PX,
            HAND_TOOLS_TABLE_HEADERS,
        )

        self.assertEqual(len(HAND_TOOLS_TABLE_HEADERS), 9)
        self.assertEqual(len(HAND_TOOLS_TABLE_COL_WIDTHS_PX), 9)
        self.assertEqual(HAND_TOOLS_TABLE_HEADERS[1][1], "TOOL")
        self.assertEqual(HAND_TOOLS_TABLE_HEADERS[-1][1], "ACTIONS")

    def test_filter_layout_matches_table_columns(self) -> None:
        from app.components.small_hand_tools_list_table import HAND_TOOLS_TABLE_COL_WIDTHS_PX
        from app.components.small_hand_tools_ui import (
            _HAND_TOOL_FILTER_COL_WEIGHTS,
            _HAND_TOOL_FILTER_COLUMN_LAYOUT,
        )

        self.assertEqual(len(_HAND_TOOL_FILTER_COLUMN_LAYOUT), 9)
        self.assertEqual(len(_HAND_TOOL_FILTER_COL_WEIGHTS), 9)
        self.assertEqual(
            _HAND_TOOL_FILTER_COL_WEIGHTS,
            [HAND_TOOLS_TABLE_COL_WIDTHS_PX[key] for key in HAND_TOOLS_TABLE_COL_WIDTHS_PX],
        )

    def test_hand_tools_css_uses_html_table_selectors(self) -> None:
        from app.components.assets_css import HAND_TOOLS_HTML_TABLE_CSS, HAND_TOOLS_TABLE_GRID

        self.assertIn(".ips-hand-tools-html-table", HAND_TOOLS_HTML_TABLE_CSS)
        self.assertIn("text-overflow: ellipsis", HAND_TOOLS_HTML_TABLE_CSS)
        self.assertIn("white-space: nowrap", HAND_TOOLS_HTML_TABLE_CSS)
        self.assertNotIn("word-break: break-word", HAND_TOOLS_HTML_TABLE_CSS)
        self.assertIn("240px", HAND_TOOLS_TABLE_GRID)


if __name__ == "__main__":
    unittest.main()
