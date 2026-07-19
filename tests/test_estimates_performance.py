"""Tests for Estimates module performance and lazy-loading regressions."""

from __future__ import annotations

import inspect
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.estimates_list_table import estimate_detail_href, estimate_list_link_html
from app.pages import estimates as estimates_page
from app.services.estimates_directory_service import EstimatesPage, list_estimates_page, stored_customer_price_amount


class TestEstimatesDirectoryService(unittest.TestCase):
    def test_list_estimates_page_returns_only_requested_slice(self) -> None:
        rows = [
            {
                "id": f"e-{i}",
                "estimate_number": f"Q-{i}",
                "project_name": f"Project {i}",
                "customer": "Acme",
                "status": "Draft",
                "customer_price": 1000.0 + i,
            }
            for i in range(30)
        ]

        with patch("app.services.estimates_directory_service._load_catalog_rows", return_value=(rows, True)):
            with patch(
                "app.services.estimates_directory_service.load_estimates_filter_options",
                return_value={"customer": ["Acme"], "status": ["Draft"]},
            ):
                page = list_estimates_page(view="All Estimates", page=2, page_size=10, table_key="est_test")

        assert page.total_count == 30
        assert len(page.rows) == 10
        assert page.rows[0]["id"] == "e-10"


class TestEstimatesNativeLinks(unittest.TestCase):
    def test_estimate_list_link_html_uses_native_anchor(self) -> None:
        html_out = estimate_list_link_html("e-123", "Q-123")
        assert "<a " in html_out
        assert 'target="_self"' in html_out
        assert "estimate_detail=e-123" in html_out
        assert "ips_nav=estimates" in html_out

    def test_estimate_detail_href_encodes_tab(self) -> None:
        href = estimate_detail_href("id/with space", tab="materials")
        assert "estimate_detail=id%2Fwith+space" in href or "estimate_detail=id%2Fwith%20space" in href
        assert "estimate_tab=materials" in href


class TestEstimatesDetailFastPath(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_detail_pending_skips_catalog_fragment(self) -> None:
        st.session_state[estimates_page.ESTIMATES_MODE_KEY] = "detail"
        st.session_state[estimates_page.SELECTED_ESTIMATE_KEY] = "e-1"

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(estimates_page, "_render_estimates_catalog_fragment") as catalog_mock:
                with patch.object(estimates_page, "render_estimate_detail") as detail_mock:
                    with patch.object(estimates_page, "_capture_estimate_detail_query"):
                        with patch.object(estimates_page, "inject_estimates_module_css"):
                            with patch.object(estimates_page, "inject_estimates_page_layout_css"):
                                with patch("app.ui.page_header.render_page_header"):
                                    with patch.object(estimates_page.st, "markdown"):
                                        estimates_page.render()

        catalog_mock.assert_not_called()
        detail_mock.assert_called()


class TestEstimatesRollups(unittest.TestCase):
    def test_stored_customer_price_does_not_call_calculate(self) -> None:
        row = {"customer_price": 1500.0}
        with patch("app.services.estimate_costing_service.calculate_estimate_totals") as calc_mock:
            amount = stored_customer_price_amount(row)
        calc_mock.assert_not_called()
        assert amount == 1500.0

    def test_list_render_does_not_sync_stale_rollups(self) -> None:
        rows = [{"id": "e-1", "customer_price": 0}]
        with patch("app.services.estimate_costing_service.recalculate_and_save_estimate_totals") as save_mock:
            refreshed = estimates_page._sync_stale_estimate_rollups(rows)
        save_mock.assert_not_called()
        assert refreshed == {}


class TestEstimatesHeaderBeforeList(unittest.TestCase):
    def test_render_page_header_before_directory_query(self) -> None:
        path = Path(__file__).resolve().parents[1] / "app" / "pages" / "estimates.py"
        src = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        render_block = src.split("\ndef render(")[1].split("\ndef _export_estimates_csv")[0]
        fragment_block = src.split("@fragment\ndef _render_estimates_catalog_fragment")[1].split("\ndef render(")[0]
        header_pos = render_block.find("render_page_header")
        list_pos = fragment_block.find("list_estimates_page")
        assert header_pos >= 0
        assert list_pos >= 0
        assert render_block.find("load_estimates()") < 0
        assert header_pos < list_pos


if __name__ == "__main__":
    unittest.main()
