"""Tests for assets equipment HTML table."""

from __future__ import annotations

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
        bridge_key="ast_bridge_open_ast_1",
    )
    assert "ips-inventory-thumb-cell-link" in html_out
    assert 'data-asset-id="ast-1"' in html_out


def test_asset_link_html_uses_open_action():
    html_out = _asset_link_html("ast-2", "Dump Trailer", bridge_key="ast_bridge_open_ast_2")
    assert 'data-asset-action="open"' in html_out
    assert 'type="button"' in html_out
    assert "Dump Trailer" in html_out
