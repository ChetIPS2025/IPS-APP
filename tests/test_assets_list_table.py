"""Tests for assets equipment HTML table."""

from __future__ import annotations

import inspect
from unittest.mock import patch

from app.components.assets_list_table import (
    _asset_link_html,
    _asset_thumb_link_html,
    build_assets_html_table,
)


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


def test_asset_thumb_link_html_wraps_catalog_thumbnail():
    html_out = _asset_thumb_link_html(
        "ast-1",
        {"id": "ast-1", "asset_name": "Generator"},
    )
    assert "ips-inventory-thumb-cell-link" in html_out
    assert 'data-asset-id="ast-1"' in html_out


def test_asset_link_html_uses_open_action():
    html_out = _asset_link_html("ast-2", "Dump Trailer", bridge_key="ast_bridge_open_ast_2")
    assert 'data-asset-action="open"' in html_out
    assert 'data-bridge-key="ast_bridge_open_ast_2"' in html_out
    assert 'type="button"' in html_out
    assert "Dump Trailer" in html_out


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


def test_build_assets_html_table_includes_matching_bridge_keys():
    asset = {
        "id": "ast-uuid-1",
        "asset_name": "Generator",
        "asset_number": "A-100",
        "category": "Equipment",
        "location": "Yard",
        "status": "Available",
    }
    from app.components.assets_list_table import assets_bridge_button_key

    bridge_key = assets_bridge_button_key(asset)
    html_out = build_assets_html_table([asset])
    assert f'data-bridge-key="{bridge_key}"' in html_out
    assert bridge_key == "ast_bridge_open_ast_uuid_1"


def test_assets_open_buttons_use_on_click_callback() -> None:
    from app.components.assets_list_table import render_assets_table_open_buttons

    src = inspect.getsource(render_assets_table_open_buttons)
    assert "on_click=_open" in src
    assert "st.rerun()" not in src
    assert "ips_app_rerun()" not in src


def test_assets_table_bridge_uses_keyed_hidden_buttons() -> None:
    from app.components.assets_list_table import render_assets_table_bridge

    src = inspect.getsource(render_assets_table_bridge)
    assert "clickBridgeButton" in src
    assert "data-bridge-key" in src
    assert "CSS.escape" in src
    assert "btn.click()" in src
    assert "sendValue" in src
    assert "render_clean_table_click_bridge" not in src
    assert ".st-key-assets_table_wrap" in src
    assert "expand:" in src
    assert 'getAttribute("data-asset-action")' in src
    assert "rowExpandMode" in src
    assert "if (fieldMode)" not in src


def test_build_assets_html_table_marks_field_mode_rows_for_expand() -> None:
    html_out = build_assets_html_table(
        [{"id": "ast-1", "asset_name": "Generator", "asset_number": "A-1"}],
        field_mode=True,
    )
    assert 'data-asset-action="expand"' in html_out


def test_custom_assets_table_wires_open_buttons_before_bridge() -> None:
    from pathlib import Path

    src = Path(__file__).resolve().parents[1].joinpath("app", "pages", "assets.py").read_text(encoding="utf-8")
    block = src.split("def _render_custom_assets_table(")[1].split("def _render_small_tools_table_column_filters")[0]
    assert "render_assets_table_open_buttons" in block
    assert "render_assets_table_bridge_legacy" in block
    open_idx = block.index("render_assets_table_open_buttons")
    bridge_idx = block.index("render_assets_table_bridge_legacy")
    assert open_idx < bridge_idx


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
