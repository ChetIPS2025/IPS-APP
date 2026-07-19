"""Customers module performance and lazy-loading regressions."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.customers_directory_table import customer_detail_href, customer_name_link_html
from app.pages import customers as customers_page
from app.services.customers_directory_service import CustomersPage, list_customers_page


class TestCustomersDirectoryService(unittest.TestCase):
    def test_list_customers_page_returns_only_requested_slice(self) -> None:
        rows = [
            {
                "id": f"cust-{i}",
                "customer_name": f"Customer {i}",
                "company_name": f"Customer {i}",
                "status": "Active",
            }
            for i in range(30)
        ]

        with patch("app.services.customers_directory_service._load_raw_customers", return_value=(rows, True)):
            with patch(
                "app.services.customers_directory_service.load_customer_filter_options",
                return_value={"status": ["Active"]},
            ):
                with patch(
                    "app.services.customers_directory_service._bulk_location_summary",
                    return_value={f"cust-{i}": {"location_count": 0, "primary_location_name": "—", "primary_location_city": "—", "primary_location_state": "—"} for i in range(30)},
                ):
                    with patch(
                        "app.services.customers_directory_service._bulk_contact_counts",
                        return_value={f"cust-{i}": 0 for i in range(30)},
                    ):
                        with patch(
                            "app.services.customers_directory_service.count_open_jobs_by_customer_ids",
                            return_value={f"cust-{i}": 0 for i in range(30)},
                        ):
                            with patch(
                                "app.services.customers_directory_service.count_open_estimates_by_customer_ids",
                                return_value={f"cust-{i}": 0 for i in range(30)},
                            ):
                                page = list_customers_page(page=2, page_size=10)

        self.assertEqual(page.total_count, 30)
        self.assertEqual(len(page.rows), 10)
        self.assertEqual(page.page, 2)


class TestCustomersOpenCounts(unittest.TestCase):
    def test_count_services_do_not_load_full_catalog_helpers(self) -> None:
        with patch("app.services.customer_relationships_service._fetch_job_count_rows", return_value=[]):
            with patch("app.services.customer_relationships_service._fetch_estimate_count_rows", return_value=[]):
                from app.services.customer_relationships_service import (
                    count_open_estimates_by_customer_ids,
                    count_open_jobs_by_customer_ids,
                )

                with patch("app.pages._core._data.load_jobs") as jobs_mock:
                    with patch("app.pages._core._data.load_estimates") as est_mock:
                        count_open_jobs_by_customer_ids([("cust-1", "Acme")])
                        count_open_estimates_by_customer_ids([("cust-1", "Acme")])
                jobs_mock.assert_not_called()
                est_mock.assert_not_called()


class TestCustomersNativeLinks(unittest.TestCase):
    def test_customer_name_link_uses_native_anchor(self) -> None:
        html_out = customer_name_link_html("cust-1", "Acme Corp")
        self.assertIn("<a ", html_out)
        self.assertIn('target="_self"', html_out)
        self.assertIn("customer_detail=cust-1", html_out)
        self.assertIn("ips_nav=customers", html_out)
        self.assertNotIn('role="button"', html_out)

    def test_detail_href_encodes_tab(self) -> None:
        href = customer_detail_href("id/with space", tab="locations")
        self.assertIn("customer_detail=", href)
        self.assertIn("customer_tab=locations", href)


class TestCustomersDetailFastPath(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_detail_pending_skips_catalog_fragment(self) -> None:
        st.session_state[customers_page.CUSTOMERS_MODE_KEY] = "detail"
        st.session_state[customers_page.CUSTOMERS_SELECTED_ID_KEY] = "cust-1"

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(customers_page, "_render_customers_catalog_fragment") as catalog_mock:
                with patch.object(customers_page, "render_customer_detail") as detail_mock:
                    with patch.object(customers_page, "_capture_customer_detail_query"):
                        with patch.object(customers_page, "load_customer_permissions"):
                            with patch.object(customers_page, "inject_customers_module_css"):
                                with patch.object(customers_page, "inject_customers_page_layout_css"):
                                    with patch.object(customers_page, "render_page_brand_header"):
                                        with patch.object(customers_page.st, "markdown"):
                                            customers_page.render()

        catalog_mock.assert_not_called()
        detail_mock.assert_called()


class TestCustomersHeaderBeforeList(unittest.TestCase):
    def test_render_page_header_before_catalog_fragment(self) -> None:
        calls: list[str] = []

        def _header(*args, **kwargs):
            calls.append("header")

        def _catalog():
            calls.append("catalog")

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(customers_page, "render_page_brand_header", side_effect=_header):
                with patch.object(customers_page, "_capture_customer_detail_query"):
                    with patch.object(customers_page, "_customers_detail_pending", return_value=False):
                        with patch.object(customers_page, "_render_customers_catalog_fragment", side_effect=_catalog):
                            with patch.object(customers_page, "load_customer_permissions"):
                                with patch.object(customers_page, "inject_customers_module_css"):
                                    with patch.object(customers_page, "inject_customers_page_layout_css"):
                                        with patch.object(customers_page.st, "markdown"):
                                            customers_page.render()

        self.assertEqual(calls[0], "header")
        self.assertEqual(calls[1], "catalog")

    def test_render_source_has_no_pre_header_list_load(self) -> None:
        import inspect

        source = inspect.getsource(customers_page.render)
        self.assertNotIn("_load_customers_list_rows", source)
        self.assertNotIn("load_jobs()", source)
        self.assertNotIn("load_estimates()", source)


if __name__ == "__main__":
    unittest.main()
