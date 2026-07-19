"""Inventory module performance and lazy-loading regressions."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.inventory_directory_table import inventory_detail_href
from app.components.inventory_list_table import _inventory_link_html
from app.pages import inventory as inventory_page
from app.services.inventory_directory_service import InventoryPage, list_inventory_page


class TestInventoryDirectoryService(unittest.TestCase):
    def test_list_inventory_page_returns_only_requested_slice(self) -> None:
        rows = [
            {
                "id": f"inv-{i}",
                "sku": f"SKU-{i}",
                "name": f"Item {i}",
                "status": "In Stock",
                "stock_policy": "none",
            }
            for i in range(30)
        ]

        with patch("app.services.inventory_directory_service._load_enriched_catalog", return_value=rows):
            with patch(
                "app.services.inventory_directory_service.load_inventory_filter_options",
                return_value={"category": [], "location": [], "status": ["In Stock"], "vendor": []},
            ):
                page = list_inventory_page(search="", stock_view="All tracked", page=2, page_size=10, table_key="inv_test")

        self.assertEqual(page.total_count, 30)
        self.assertEqual(len(page.rows), 10)
        self.assertEqual(page.rows[0]["id"], "inv-10")


class TestInventoryNativeLinks(unittest.TestCase):
    def test_inventory_link_html_uses_native_anchor(self) -> None:
        html_out = _inventory_link_html("inv-1", "SKU-100")
        self.assertIn("<a ", html_out)
        self.assertIn('target="_self"', html_out)
        self.assertIn("inventory_detail=inv-1", html_out)
        self.assertNotIn("<button", html_out)

    def test_inventory_detail_href_encodes_tab(self) -> None:
        href = inventory_detail_href("id/with space", tab="transactions")
        self.assertIn("inventory_detail=", href)
        self.assertIn("inventory_tab=transactions", href)


class TestInventoryDetailFastPath(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_detail_pending_skips_items_fragment(self) -> None:
        st.session_state[inventory_page.SHOW_INVENTORY_MODAL_KEY] = True
        st.session_state[inventory_page._MODAL_KEY] = "inv-1"

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(inventory_page, "_render_inventory_items_fragment") as items_mock:
                with patch.object(inventory_page, "show_modal_if_pending") as modal_mock:
                    with patch.object(inventory_page, "_capture_inventory_detail_query"):
                        with patch.object(inventory_page, "inject_inventory_module_css"):
                            with patch.object(inventory_page, "inject_inventory_page_layout_css"):
                                with patch("app.ui.page_header.render_page_header"):
                                    with patch.object(inventory_page.st, "markdown"):
                                        inventory_page.render()

        items_mock.assert_not_called()
        modal_mock.assert_called()


class TestInventoryMainTabs(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_qr_history_does_not_load_directory(self) -> None:
        st.session_state[inventory_page._INVENTORY_MAIN_TAB_KEY] = "QR Scan History"

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch("app.components.tabs.render_tabs", return_value="QR Scan History"):
                with patch.object(inventory_page, "list_inventory_page") as list_mock:
                    with patch.object(inventory_page, "_capture_inventory_detail_query"):
                        with patch.object(inventory_page, "inject_inventory_module_css"):
                            with patch.object(inventory_page, "inject_inventory_page_layout_css"):
                                with patch("app.ui.page_header.render_page_header"):
                                    with patch.object(inventory_page, "_inv_export_header"):
                                        with patch("app.pages._core._data.load_recent_qr_scans", return_value=([], False)):
                                            with patch("app.components.qr_scan_history_ui.render_qr_scan_history_table"):
                                                with patch.object(inventory_page.st, "markdown"):
                                                    with patch.object(inventory_page.st, "caption"):
                                                        inventory_page.render()

        list_mock.assert_not_called()


class TestInventoryConditionalTabs(unittest.TestCase):
    def test_overview_does_not_load_transactions(self) -> None:
        item = {"id": "inv-1", "sku": "SKU-1", "name": "Widget", "status": "In Stock"}
        st.session_state["ips_inventory_detail_active_tab"] = "Overview"

        with patch("app.components.tabs.render_tabs", return_value="Overview"):
            with patch("app.pages.inventory._render_inventory_transactions_tab") as txn_mock:
                with patch("app.pages.inventory._render_inventory_detail_overview"):
                    from app.components.inventory_detail_tabs import render_inventory_detail_tabs

                    render_inventory_detail_tabs(item)

        txn_mock.assert_not_called()


class TestInventoryHeaderBeforeList(unittest.TestCase):
    def test_render_page_header_before_items_fragment(self) -> None:
        calls: list[str] = []

        def _header(*args, **kwargs):
            calls.append("header")

        def _items_fragment():
            calls.append("items_fragment")

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch("app.ui.page_header.render_page_header", side_effect=_header):
                with patch.object(inventory_page, "_capture_inventory_detail_query"):
                    with patch.object(inventory_page, "_inventory_detail_pending", return_value=False):
                        with patch("app.components.tabs.render_tabs", return_value="Items"):
                            with patch.object(inventory_page, "_render_inventory_items_fragment", side_effect=_items_fragment):
                                with patch.object(inventory_page, "inject_inventory_module_css"):
                                    with patch.object(inventory_page, "inject_inventory_page_layout_css"):
                                        with patch.object(inventory_page, "_inv_export_header"):
                                            with patch.object(inventory_page.st, "markdown"):
                                                inventory_page.render()

        self.assertEqual(calls[0], "header")
        self.assertEqual(calls[1], "items_fragment")


if __name__ == "__main__":
    unittest.main()
