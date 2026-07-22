"""Regression tests: Serialized Tools native links and field-mode bridge."""

from __future__ import annotations

from pathlib import Path

from app.components.serialized_tools_list_table import (
    build_serialized_tools_html_table,
    serialized_tool_detail_href,
)


def _assets_source() -> str:
    path = Path(__file__).resolve().parents[1] / "app" / "pages" / "assets.py"
    return path.read_text(encoding="utf-8")


def test_serialized_tool_detail_href_uses_asset_detail_query() -> None:
    href = serialized_tool_detail_href(
        {
            "row_type": "asset",
            "id": "tool-1",
            "_detail_asset_id": "tool-1",
        }
    )
    assert "asset_detail=tool-1" in href
    assert "ips_nav=assets" in href


def test_serialized_kit_item_links_to_parent_kit_tab() -> None:
    href = serialized_tool_detail_href(
        {
            "row_type": "kit_item",
            "parent_asset_id": "parent-1",
            "_detail_asset_id": "parent-1",
            "_detail_tab": "kit",
        }
    )
    assert "asset_detail=parent-1" in href
    assert "asset_tab=kit" in href


def test_serialized_tools_table_uses_native_links_without_open_bridge() -> None:
    src = _assets_source()
    table_block = src.split("def _render_small_tools_table(")[1].split("@fragment\ndef _render_equipment_list")[0]
    assert "build_serialized_tools_html_table" in table_block
    assert "render_serialized_tools_table_bridge_legacy" in table_block
    assert "if field_mode:" in table_block
    assert "render_serialized_tools_table_open_buttons" not in table_block


def test_serialized_tools_normal_mode_html_has_no_select_column() -> None:
    html = build_serialized_tools_html_table(
        [
            {
                "_row_id": "tool-1",
                "_display_name": "Drill",
                "_display_model": "M18",
                "_display_serial": "SN-1",
                "_display_trailer": "Trailer",
                "_display_job": "—",
                "_display_status": "Available",
                "_display_condition": "Good",
                "_detail_asset_id": "tool-1",
                "_thumb_asset": {"id": "tool-1", "asset_name": "Drill"},
            }
        ],
        field_mode=False,
    )
    assert 'data-st-action="select"' not in html
    assert "<a " in html
    assert "asset_detail=tool-1" in html


def test_equipment_table_uses_field_mode_bridge_only() -> None:
    src = _assets_source()
    table_block = src.split("def _render_custom_assets_table(")[1].split("def _render_small_tools_table_column_filters")[0]
    assert "render_assets_table_open_buttons" not in table_block
    assert "render_assets_table_bridge_legacy" in table_block
    assert "if field_mode:" in table_block
    assert "_capture_asset_detail_query()" in src


def test_asset_fragments_escalate_modal_to_app_rerun() -> None:
    src = _assets_source().replace("\r\n", "\n")
    equipment_block = src.split("@fragment\ndef _render_equipment_list")[1].split(
        "@fragment\ndef _render_small_tools_list"
    )[0]
    serialized_block = src.split("@fragment\ndef _render_small_tools_list")[1].split(
        "def _apply_assets_search_filter"
    )[0]
    assert "_rerun_if_assets_modal_pending()" in equipment_block
    assert "_rerun_if_assets_modal_pending()" in serialized_block


def test_render_uses_directory_services_not_load_assets() -> None:
    src = _assets_source()
    render_block = src.split("def render() -> None:")[1]
    assert "load_assets()" not in render_block
    assert "list_equipment_page" in src
    assert "list_serialized_tools_page" in src
