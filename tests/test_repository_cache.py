"""Repository cache invalidation (narrow vs full clear)."""

from __future__ import annotations

from unittest.mock import patch

from app.services.repository import (
    clear_data_cache_for_table,
    delete_row,
    insert_row_admin,
    update_row,
)


def test_clear_data_cache_for_table_calls_targeted_handler_for_jobs() -> None:
    with patch("app.services.repository._clear_db_read_caches") as mock_db:
        with patch("app.pages._core._data.clear_jobs_catalog_cache") as mock_jobs:
            clear_data_cache_for_table("jobs")
    mock_db.assert_called_once()
    mock_jobs.assert_called_once()


def test_clear_data_cache_for_table_normalizes_table_name() -> None:
    with patch("app.services.repository._clear_db_read_caches"):
        with patch("app.pages._core._data.clear_inventory_catalog_cache") as mock_inv:
            clear_data_cache_for_table("  INVENTORY_ITEMS  ")
    mock_inv.assert_called_once()


def test_clear_data_cache_for_table_unknown_table_falls_back_to_catalog_clear() -> None:
    with patch("app.services.repository._clear_db_read_caches") as mock_db:
        with patch("app.pages._core._data.clear_all_catalog_list_caches") as mock_catalog:
            clear_data_cache_for_table("asset_documents")
    mock_db.assert_called_once()
    mock_catalog.assert_called_once()


def test_clear_data_cache_for_table_estimate_line_items_clears_estimates() -> None:
    with patch("app.services.repository._clear_db_read_caches"):
        with patch("app.pages._core._data.clear_estimates_catalog_cache") as mock_est:
            clear_data_cache_for_table("estimate_line_items")
    mock_est.assert_called_once()


def test_update_row_invalidates_table_cache() -> None:
    with patch("app.services.repository._db") as mock_db:
        mock_db.return_value.update_rows.return_value = [{"id": "j1"}]
        with patch("app.services.repository.clear_data_cache_for_table") as mock_clear:
            with patch("app.services.repository.filter_payload_to_table", side_effect=lambda _t, p: p):
                result = update_row("jobs", {"status": "Active"}, {"id": "j1"})
    assert result.ok is True
    mock_clear.assert_called_once_with("jobs")


def test_delete_row_invalidates_table_cache() -> None:
    with patch("app.services.repository._db") as mock_db:
        mock_db.return_value.delete_rows.return_value = [{"id": "j1"}]
        with patch("app.services.repository.clear_data_cache_for_table") as mock_clear:
            result = delete_row("jobs", {"id": "j1"})
    assert result.ok is True
    mock_clear.assert_called_once_with("jobs")


def test_insert_row_admin_invalidates_table_cache() -> None:
    payload = {"tool_name": "Hammer", "quantity_on_hand": 1}
    with patch("app.services.repository.table_column_names", return_value=frozenset(payload)):
        with patch("app.services.repository._db") as mock_db:
            mock_db.return_value.insert_row_admin.return_value = {"id": "t1", **payload}
            with patch("app.services.repository.clear_data_cache_for_table") as mock_clear:
                result = insert_row_admin("small_hand_tools", payload)
    assert result.ok is True
    mock_clear.assert_called_once_with("small_hand_tools")
