"""Tests for session-scoped derived page data cache."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.pages._core.page_data_cache import (
    clear_customers_page_data_cache,
    clear_dashboard_page_data_cache,
    clear_page_data_cache,
    clear_page_data_cache_prefix,
    page_data_cache_get,
)


class PageDataCacheTests(unittest.TestCase):
    @patch("app.pages._core.page_data_cache.st.session_state", new_callable=dict)
    def test_page_data_cache_get_runs_loader_once(self, session_state: dict) -> None:
        calls = {"n": 0}

        def loader() -> str:
            calls["n"] += 1
            return "payload"

        self.assertEqual(page_data_cache_get("demo_key", loader), "payload")
        self.assertEqual(page_data_cache_get("demo_key", loader), "payload")
        self.assertEqual(calls["n"], 1)

    @patch("app.pages._core.page_data_cache.st.session_state", new_callable=dict)
    def test_clear_page_data_cache_prefix(self, session_state: dict) -> None:
        page_data_cache_get("dashboard_kpis:2026-07-01:2026-07-07", lambda: 1)
        page_data_cache_get("customers_page_list_rows", lambda: 2)
        clear_page_data_cache_prefix("dashboard_")
        store = session_state["_ips_page_data_cache"]
        self.assertNotIn("dashboard_kpis:2026-07-01:2026-07-07", store)
        self.assertIn("customers_page_list_rows", store)

    @patch("app.pages._core.page_data_cache.st.session_state", new_callable=dict)
    def test_clear_customers_page_data_cache(self, session_state: dict) -> None:
        page_data_cache_get("customers_enriched_list", lambda: [])
        page_data_cache_get("customers_page_list_rows", lambda: [])
        clear_customers_page_data_cache()
        self.assertEqual(session_state.get("_ips_page_data_cache"), {})

    @patch("app.pages._core.page_data_cache.st.session_state", new_callable=dict)
    def test_clear_dashboard_page_data_cache(self, session_state: dict) -> None:
        page_data_cache_get("dashboard_item_activity:10", lambda: [])
        clear_dashboard_page_data_cache()
        self.assertEqual(session_state.get("_ips_page_data_cache"), {})

    @patch("app.pages._core.page_data_cache.st.session_state", new_callable=dict)
    def test_clear_page_data_cache_wipes_store(self, session_state: dict) -> None:
        page_data_cache_get("any_key", lambda: 1)
        clear_page_data_cache()
        self.assertNotIn("_ips_page_data_cache", session_state)


if __name__ == "__main__":
    unittest.main()
