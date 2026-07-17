"""Catalog cache invalidation should avoid unnecessary cross-module clears."""

from __future__ import annotations

from unittest.mock import patch


def test_clear_estimates_catalog_cache_does_not_clear_jobs() -> None:
    with patch("app.pages._core._data.clear_estimates_list_cache") as mock_est_list:
        with patch("app.pages._core._data.clear_catalog_session_key") as mock_key:
            with patch("app.pages._core._data.clear_dashboard_page_data_cache") as mock_dash:
                with patch("app.pages._core._data.clear_customers_page_data_cache") as mock_customers:
                    with patch("app.pages._core._data.clear_jobs_catalog_cache") as mock_jobs:
                        from app.pages._core._data import clear_estimates_catalog_cache

                        clear_estimates_catalog_cache()

    mock_est_list.assert_called_once()
    mock_key.assert_called_once_with("estimates")
    mock_dash.assert_called_once()
    mock_customers.assert_called_once()
    mock_jobs.assert_not_called()


def test_clear_jobs_catalog_cache_does_not_clear_customers_or_dashboard() -> None:
    with patch("app.pages._core._data.clear_jobs_list_cache") as mock_jobs_list:
        with patch("app.pages._core._data.clear_catalog_session_key") as mock_key:
            with patch("app.pages._core._data.clear_jobs_list_cost_cache") as mock_cost:
                with patch("app.pages._core._data.clear_dashboard_page_data_cache") as mock_dash:
                    with patch("app.pages._core._data.clear_customers_page_data_cache") as mock_customers:
                        from app.pages._core._data import clear_jobs_catalog_cache

                        clear_jobs_catalog_cache()

    mock_jobs_list.assert_called_once()
    mock_key.assert_called_once_with("jobs")
    mock_cost.assert_called_once()
    mock_dash.assert_not_called()
    mock_customers.assert_not_called()


def test_clear_timekeeping_catalog_cache_refreshes_jobs_without_customers_or_dashboard() -> None:
    with patch("app.pages._core._data.clear_timekeeping_summaries_page_data_cache") as mock_tk:
        with patch("app.pages._core._data.clear_jobs_list_cache") as mock_jobs_list:
            with patch("app.pages._core._data.clear_catalog_session_key") as mock_key:
                with patch("app.pages._core._data.clear_jobs_list_cost_cache") as mock_cost:
                    with patch("app.pages._core._data.clear_jobs_catalog_cache") as mock_jobs_catalog:
                        with patch("app.pages._core._data.clear_dashboard_page_data_cache") as mock_dash:
                            with patch(
                                "app.pages._core._data.clear_customers_page_data_cache"
                            ) as mock_customers:
                                from app.pages._core._data import clear_timekeeping_catalog_cache

                                clear_timekeeping_catalog_cache()

    mock_tk.assert_called_once()
    mock_jobs_list.assert_called_once()
    mock_key.assert_called_once_with("jobs")
    mock_cost.assert_called_once()
    mock_jobs_catalog.assert_not_called()
    mock_dash.assert_not_called()
    mock_customers.assert_not_called()


def test_clear_catalog_session_datasets_only_clears_catalog_mirror() -> None:
    session_state = {
        "_ips_catalog_datasets": {"jobs": [{"id": "j1"}]},
        "_ips_page_data_cache": {"customers_page_list_rows": []},
    }
    with patch("app.pages._core._data.st.session_state", session_state):
        with patch("app.pages._core._data.clear_page_data_cache") as mock_page_cache:
            from app.pages._core._data import clear_catalog_session_datasets

            clear_catalog_session_datasets()

    assert "_ips_catalog_datasets" not in session_state
    assert "_ips_page_data_cache" in session_state
    mock_page_cache.assert_not_called()


def test_clear_all_catalog_list_caches_still_clears_page_data_cache() -> None:
    with patch("app.pages._core._data.clear_catalog_session_datasets") as mock_catalog:
        with patch("app.pages._core._data.clear_page_data_cache") as mock_page_cache:
            with patch("app.pages._core._data.clear_jobs_list_cost_cache"):
                with patch("app.pages._core._data.clear_inventory_list_cache"):
                    with patch("app.pages._core._data.clear_assets_list_cache"):
                        with patch("app.pages._core._data.clear_jobs_list_cache"):
                            with patch("app.pages._core._data.clear_customers_list_cache"):
                                with patch("app.pages._core._data.clear_employees_list_cache"):
                                    with patch("app.pages._core._data.clear_estimates_list_cache"):
                                        with patch("app.pages._core._data.clear_user_profiles_cache"):
                                            with patch("app.pages._core._data.clear_labor_rates_cache"):
                                                with patch("app.pages._core._data.clear_tasks_list_cache"):
                                                    with patch(
                                                        "app.services.small_hand_tool_service.clear_hand_tools_list_cache"
                                                    ):
                                                        with patch(
                                                            "app.services.pricing_guide_service.clear_pricing_guide_cache"
                                                        ):
                                                            from app.pages._core._data import (
                                                                clear_all_catalog_list_caches,
                                                            )

                                                            clear_all_catalog_list_caches()

    mock_catalog.assert_called_once()
    mock_page_cache.assert_called_once()
