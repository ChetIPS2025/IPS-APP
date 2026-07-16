"""Tests for lazy asset detail modal cache invalidation."""

from __future__ import annotations

from unittest.mock import patch

from app.services.assets_service import ASSETS_MODAL_CACHE_KEY, invalidate_assets_modal_cache


def test_invalidate_assets_modal_cache_clears_session_map() -> None:
    session_state = {ASSETS_MODAL_CACHE_KEY: {"ast-1": {"id": "ast-1", "asset_name": "Generator"}}}

    with patch("streamlit.session_state", session_state, create=True):
        invalidate_assets_modal_cache()

    assert ASSETS_MODAL_CACHE_KEY not in session_state


def test_clear_assets_catalog_cache_invalidates_modal_cache() -> None:
    with patch("app.pages._core._data.clear_assets_list_cache") as mock_list:
        with patch("app.pages._core._data.clear_catalog_session_key") as mock_key:
            with patch("app.pages._core._data.clear_dashboard_page_data_cache") as mock_dash:
                with patch("app.services.pricing_guide_service.clear_pricing_guide_cache") as mock_pg:
                    with patch(
                        "app.services.assets_service.invalidate_assets_modal_cache"
                    ) as mock_modal:
                        from app.pages._core._data import clear_assets_catalog_cache

                        clear_assets_catalog_cache()

    mock_list.assert_called_once()
    mock_key.assert_called_once_with("assets")
    mock_dash.assert_called_once()
    mock_pg.assert_called_once()
    mock_modal.assert_called_once()
