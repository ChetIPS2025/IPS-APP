"""Pricing Guide module performance and lazy-loading regressions."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.pricing_guide_directory_table import pricing_guide_detail_href
from app.components.pricing_guide_list_table import _pg_link_html, build_pricing_guide_html_table
from app.pages import pricing_guide as pricing_guide_page
from app.services.pricing_guide_directory_service import PricingGuidePage, list_pricing_guide_page
from app.services.pricing_guide_service import calc_sell_price


class TestPricingGuideDirectoryService(unittest.TestCase):
    def test_list_pricing_guide_page_returns_only_requested_slice(self) -> None:
        rows = [
            {
                "id": f"pg-{i}",
                "description": f"Item {i}",
                "item_class": "Non-Inventory",
                "category": "Misc",
                "vendor": "Acme",
                "status": "Active",
                "is_active": True,
                "default_cost": 1.0,
                "default_markup_percent": 10.0,
                "default_sell_price": 1.1,
            }
            for i in range(30)
        ]
        fetch_result = MagicMock(rows=rows, source="pricing_guide_items", warning=None)

        with patch(
            "app.services.pricing_guide_directory_service._load_catalog_result",
            return_value=fetch_result,
        ):
            with patch(
                "app.services.pricing_guide_directory_service.load_pricing_guide_filter_options",
                return_value={"item_class": ["Non-Inventory"], "category": ["Misc"], "vendor": ["Acme"], "status": ["Active"]},
            ):
                page = list_pricing_guide_page(page=2, page_size=10, table_key="pg_test")

        assert page.total_count == 30
        assert len(page.rows) == 10
        assert page.rows[0]["id"] == "pg-10"


class TestPricingGuideNativeLinks(unittest.TestCase):
    def test_pg_link_html_uses_native_anchor(self) -> None:
        html_out = _pg_link_html("pg-123", "Hydraulic hose")
        assert "<a " in html_out
        assert 'target="_self"' in html_out
        assert "pricing_detail=pg-123" in html_out
        assert "ips_nav=pricing_guide" in html_out

    def test_pricing_detail_href_encodes_tab(self) -> None:
        href = pricing_guide_detail_href("id/with space", tab="pricing")
        assert "pricing_detail=id%2Fwith+space" in href or "pricing_detail=id%2Fwith%20space" in href
        assert "pricing_tab=pricing" in href

    def test_build_table_has_no_hidden_open_buttons(self) -> None:
        rows = [{"id": "pg-1", "item": "Widget", "item_class": "Inventory", "category": "A", "unit": "EA", "default_cost": 1, "markup_pct": 0, "customer_price": 1, "vendor": "V", "status": "Active"}]
        html_out = build_pricing_guide_html_table(rows)
        assert "data-pg-action" not in html_out
        assert "pricing_detail=pg-1" in html_out


class TestPricingGuideDetailFastPath(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_detail_pending_skips_catalog_fragment(self) -> None:
        st.session_state[pricing_guide_page.SHOW_PG_MODAL_KEY] = True
        st.session_state[pricing_guide_page._MODAL_KEY] = "pg-1"

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(pricing_guide_page, "_render_pricing_guide_catalog_fragment") as catalog_mock:
                with patch.object(pricing_guide_page, "_show_detail_modal") as modal_mock:
                    with patch.object(pricing_guide_page, "_capture_pricing_detail_query"):
                        with patch.object(pricing_guide_page, "inject_pricing_guide_module_css"):
                            with patch.object(pricing_guide_page, "inject_pricing_guide_page_layout_css"):
                                with patch.object(pricing_guide_page, "render_page_brand_header"):
                                    with patch.object(pricing_guide_page.st, "markdown"):
                                        pricing_guide_page.render()

        catalog_mock.assert_not_called()
        modal_mock.assert_called()


class TestLaborRatesIsolation(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_labor_rates_does_not_query_catalog(self) -> None:
        st.session_state["pg_main_tab"] = "Labor Rates"

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch("app.services.pricing_guide_directory_service.list_pricing_guide_page") as list_mock:
                with patch.object(pricing_guide_page, "render_labor_rates_panel") as labor_mock:
                    with patch.object(pricing_guide_page, "_capture_pricing_detail_query"):
                        with patch.object(pricing_guide_page, "inject_pricing_guide_module_css"):
                            with patch.object(pricing_guide_page, "inject_pricing_guide_page_layout_css"):
                                with patch.object(pricing_guide_page, "render_page_brand_header"):
                                    with patch.object(pricing_guide_page, "render_tabs", return_value="Labor Rates"):
                                        with patch.object(pricing_guide_page.st, "markdown"):
                                            pricing_guide_page.render()

        list_mock.assert_not_called()
        labor_mock.assert_called()


class TestPricingGuideDetailTabs(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_overview_does_not_load_price_history(self) -> None:
        row = {"id": "pg-1", "item": "Widget", "item_class": "Non-Inventory", "item_type": "Material", "status": "Active"}
        perms = pricing_guide_page.PricingGuidePermissions(
            role="admin",
            user_id="u1",
            user_name="Admin",
            can_manage=True,
            can_edit=True,
            can_delete=True,
            can_import=True,
            can_manage_stock_policy=True,
        )

        with patch("app.components.tabs.render_tabs", return_value="Overview"):
            with patch("app.services.pricing_guide_detail_service.list_pricing_price_history") as history_mock:
                with patch("app.components.pricing_guide_detail_tabs.st.columns", return_value=[MagicMock(), MagicMock()]):
                    with patch("app.components.pricing_guide_detail_tabs.st.markdown"):
                        from app.components.pricing_guide_detail_tabs import render_pricing_guide_detail_tabs

                    render_pricing_guide_detail_tabs(
                        row,
                        permissions=perms,
                        render_overview_photo_fn=lambda *_a, **_k: None,
                        render_links_panel_fn=lambda *_a, **_k: None,
                    )

        history_mock.assert_not_called()


class TestPricingPrecision(unittest.TestCase):
    def test_calc_sell_price_rounding(self) -> None:
        assert calc_sell_price(0, 25) == 0.0
        assert calc_sell_price(10, 0) == 10.0
        assert calc_sell_price(12.34, 25) == 15.43
        assert calc_sell_price(99.99, 33.33) == round(99.99 + 99.99 * 33.33 / 100.0, 2)


if __name__ == "__main__":
    unittest.main()
