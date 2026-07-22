"""Tests for assets equipment HTML table."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

from app.components.assets_list_table import (
    _asset_link_html,
    _asset_thumb_link_html,
    asset_detail_href,
    build_assets_html_table,
)


def test_asset_detail_href_includes_assets_route_and_asset_detail():
    href = asset_detail_href("asset-1")
    assert "ips_nav=assets" in href
    assert "asset_detail=asset-1" in href


def test_asset_detail_href_url_encodes_special_characters():
    href = asset_detail_href("asset id/with&chars")
    assert "asset_detail=asset+id%2Fwith%26chars" in href
    assert "ips_nav=assets" in href


def test_asset_detail_href_supports_tab_query() -> None:
    href = asset_detail_href("ast-1", tab="kit")
    assert "asset_detail=ast-1" in href
    assert "asset_tab=kit" in href
    assert "ips_nav=assets" in href


def test_asset_detail_href_empty_id_returns_hash():
    assert asset_detail_href("") == "#"
    assert asset_detail_href("   ") == "#"


def test_build_assets_html_table_renders_core_columns():
    html_out = build_assets_html_table(
        [
            {
                "id": "ast-1",
                "asset_name": "Pressure Washer",
                "asset_number": "A-100",
                "category": "Equipment",
                "location": "Yard",
                "status": "Available",
            }
        ]
    )
    assert "ips-assets-html-equipment-table" in html_out
    assert "ASSET NAME" in html_out
    assert "Pressure Washer" in html_out
    assert "A-100" in html_out


def test_asset_link_html_uses_native_anchor_href():
    html_out = _asset_link_html("ast-2", "Dump Trailer")
    assert "<a" in html_out
    assert 'href="' in html_out
    assert 'target="_self"' in html_out
    assert "asset_detail=ast-2" in html_out
    assert "ips_nav=assets" in html_out
    assert "Dump Trailer" in html_out
    assert 'type="button"' not in html_out
    assert "clickBridgeButton" not in html_out
    assert "sendValue" not in html_out
    assert "data-row-id" not in html_out
    assert 'data-asset-id="ast-2"' in html_out


def test_asset_thumb_link_html_uses_native_href():
    html_out = _asset_thumb_link_html(
        "ast-1",
        {"id": "ast-1", "asset_name": "Generator"},
    )
    assert "<a" in html_out
    assert 'href="' in html_out
    assert 'target="_self"' in html_out
    assert "asset_detail=ast-1" in html_out
    assert "ips-inventory-thumb-cell-link" in html_out
    assert 'data-asset-id="ast-1"' in html_out
    assert "data-row-id" not in html_out


def test_equipment_asset_links_do_not_require_open_button_harness():
    from pathlib import Path

    table_src = Path(__file__).resolve().parents[1].joinpath(
        "app", "components", "assets_list_table.py"
    ).read_text(encoding="utf-8")
    assets_src = Path(__file__).resolve().parents[1].joinpath(
        "app", "pages", "assets.py"
    ).read_text(encoding="utf-8")
    table_block = assets_src.split("def _render_custom_assets_table(")[1].split(
        "def _render_small_tools_table_column_filters"
    )[0]

    assert "clickBridgeButton" not in _asset_link_html("x", "y")
    assert "sendValue" not in _asset_link_html("x", "y")
    assert "render_assets_table_open_buttons" not in table_block
    assert "render_assets_table_bridge_legacy" in table_block
    assert "if field_mode:" in table_block
    assert "data-bridge-key" not in build_assets_html_table(
        [{"id": "ast-1", "asset_name": "Generator", "asset_number": "A-1"}]
    )


def test_handle_assets_table_action_opens_asset_and_reruns():
    from app.components.assets_list_table import handle_assets_table_action

    opened: list[tuple[str, dict]] = []

    with patch("app.components.assets_list_table.ips_app_rerun") as mock_rerun:
        handle_assets_table_action(
            "open:ast-1",
            {"ast-1": {"id": "ast-1", "asset_name": "Generator"}},
            last_action_key="assets_test_last_action",
            open_asset_fn=lambda asset_id, asset: opened.append((asset_id, asset)),
        )

    assert opened == [("ast-1", {"id": "ast-1", "asset_name": "Generator"})]
    mock_rerun.assert_called_once()

    with patch("app.components.assets_list_table.ips_app_rerun") as mock_rerun:
        handle_assets_table_action(
            "open:ast-1",
            {"ast-1": {"id": "ast-1", "asset_name": "Generator"}},
            last_action_key="assets_test_last_action",
            open_asset_fn=lambda asset_id, asset: opened.append((asset_id, asset)),
        )

    assert opened == [("ast-1", {"id": "ast-1", "asset_name": "Generator"})]
    mock_rerun.assert_not_called()


def test_build_assets_html_table_marks_field_mode_rows_for_expand() -> None:
    html_out = build_assets_html_table(
        [{"id": "ast-1", "asset_name": "Generator", "asset_number": "A-1"}],
        field_mode=True,
    )
    assert 'data-asset-action="expand"' in html_out


def test_assets_table_bridge_field_mode_ignores_link_clicks() -> None:
    from app.components.assets_list_table import render_assets_table_bridge

    src = inspect.getsource(render_assets_table_bridge)
    assert "isInteractive" in src
    assert '"a"' in src or "a," in src
    assert "clickBridgeButton" not in src
    assert "openAssetElement" not in src
    assert "sendValue" in src
    assert "expand:" in src
    assert 'data-asset-action="expand"' not in src


def test_clean_table_open_link_requires_bridge_scope() -> None:
    from app.ui.clean_table import render_clean_table_click_bridge

    src = inspect.getsource(render_clean_table_click_bridge)
    assert "openLinkInBridgeScope" in src
    assert "if (!openLinkInBridgeScope(link)) return false;" in src


def test_capture_asset_detail_query_opens_modal_without_rerun() -> None:
    import streamlit as st

    from app.pages import assets as assets_page

    class _QueryParams(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)

    asset = {"id": "asset-1", "asset_name": "Generator"}

    st.session_state = {}
    st.query_params = _QueryParams({"asset_detail": "asset-1"})

    with patch.object(assets_page, "_cached_asset_for_modal", return_value=asset) as mock_cache:
        with patch.object(assets_page, "_open_assets_detail_modal") as mock_open:
            with patch.object(st, "rerun") as mock_rerun:
                with patch("app.pages.assets.ips_app_rerun") as mock_ips_rerun:
                    assets_page._capture_asset_detail_query()

    mock_cache.assert_called_once_with("asset-1")
    mock_open.assert_called_once_with("asset-1", asset, tab_focus=None)
    mock_rerun.assert_not_called()
    mock_ips_rerun.assert_not_called()


def test_capture_asset_detail_query_unknown_id_sets_error_and_clears_param() -> None:
    import streamlit as st

    from app.pages import assets as assets_page

    class _QueryParams(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)

        def __contains__(self, key):
            return dict.__contains__(self, key)

        def __delitem__(self, key):
            dict.__delitem__(self, key)

    st.session_state = {}
    st.query_params = _QueryParams({"asset_detail": "missing-id", "ips_nav": "assets"})

    with patch.object(assets_page, "_cached_asset_for_modal", return_value=None):
        with patch.object(assets_page, "_open_assets_detail_modal") as mock_open:
            assets_page._capture_asset_detail_query()

    mock_open.assert_not_called()
    assert st.session_state.get(assets_page._ASSET_DETAIL_QUERY_ERROR_KEY) == "missing-id"
    assert "asset_detail" not in st.query_params
    assert st.query_params.get("ips_nav") == "assets"


def test_clear_assets_detail_modal_removes_only_asset_detail_query_param() -> None:
    import streamlit as st

    from app.pages import assets as assets_page

    class _QueryParams(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)

        def __contains__(self, key):
            return dict.__contains__(self, key)

        def __delitem__(self, key):
            dict.__delitem__(self, key)

    st.session_state = {assets_page._ALL_ASSET_IDS_KEY: []}
    st.query_params = _QueryParams(
        {"ips_nav": "assets", "asset_detail": "asset-1", "foo": "bar"}
    )

    with patch("app.pages.assets._clear_asset_selection"):
        with patch("app.pages.assets.clear_edit_modes"):
            with patch("app.pages.assets.clear_record_modal"):
                assets_page._clear_assets_detail_modal()

    assert "asset_detail" not in st.query_params
    assert st.query_params.get("ips_nav") == "assets"
    assert st.query_params.get("foo") == "bar"


def test_custom_assets_table_wires_bridge_without_per_row_open_buttons() -> None:
    from pathlib import Path

    src = Path(__file__).resolve().parents[1].joinpath("app", "pages", "assets.py").read_text(encoding="utf-8")
    block = src.split("def _render_custom_assets_table(")[1].split("def _render_small_tools_table_column_filters")[0]
    assert "render_assets_table_bridge_legacy" in block
    assert "render_assets_table_open_buttons" not in block
    assert "if field_mode:" in block


def test_prepare_open_assets_table_item_sets_modal_session_keys() -> None:
    import streamlit as st

    from app.pages.assets import (
        SELECTED_ASSET_KEY,
        SHOW_ASSET_MODAL_KEY,
        _ASSETS_CACHE_KEY,
        _ASSETS_MODAL_KEY,
        _SEL,
        _prepare_open_assets_table_item,
    )

    class _SessionState(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)

    st.session_state = _SessionState()
    asset = {"id": "asset-id-1", "asset_name": "Test Asset", "asset_number": "T-1"}
    _prepare_open_assets_table_item("asset-id-1", asset)

    assert st.session_state.get(SELECTED_ASSET_KEY) == "asset-id-1"
    assert st.session_state.get(SHOW_ASSET_MODAL_KEY) is True
    assert st.session_state.get(_ASSETS_MODAL_KEY) == "asset-id-1"
    assert st.session_state.get(_SEL) == "asset-id-1"
    assert "asset-id-1" in (st.session_state.get(_ASSETS_CACHE_KEY) or {})


def test_prepare_open_assets_table_item_opens_detail_modal() -> None:
    asset = {"id": "asset-id-1", "asset_name": "Test Asset"}

    with patch("app.pages.assets._open_assets_detail_modal") as mock_open:
        from app.pages.assets import _prepare_open_assets_table_item

        _prepare_open_assets_table_item("asset-id-1", asset)

    mock_open.assert_called_once_with("asset-id-1", asset)
