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
