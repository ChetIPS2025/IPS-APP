"""Regression tests: Serialized Tools must app-rerun to open asset detail modal."""

from __future__ import annotations

import inspect
from pathlib import Path


def _assets_source() -> str:
    path = Path(__file__).resolve().parents[1] / "app" / "pages" / "assets.py"
    return path.read_text(encoding="utf-8")


def test_serialized_tools_open_bridge_uses_clean_table() -> None:
    from app.components.serialized_tools_list_table import render_serialized_tools_table_open_bridge

    src = inspect.getsource(render_serialized_tools_table_open_bridge)
    assert "render_clean_table_click_bridge" in src
    assert ".ips-serialized-tools-html-table" in src


def test_serialized_tools_open_buttons_use_app_rerun_callback() -> None:
    from app.components.serialized_tools_list_table import render_serialized_tools_table_open_buttons

    src = inspect.getsource(render_serialized_tools_table_open_buttons)
    assert "ips_app_rerun()" in src


def test_serialized_tool_table_open_prepares_modal() -> None:
    from app.pages import assets as assets_page

    src = inspect.getsource(assets_page._open_serialized_tool_table_row)
    assert "_prepare_open_small_tool_row(" in src
    assert "ips_app_rerun()" not in src


def test_serialized_tool_table_select_prepares_modal_without_callback_rerun() -> None:
    from app.pages import assets as assets_page

    select_src = inspect.getsource(assets_page._select_serialized_tool_table_row)
    assert "_prepare_open_small_tool_row(" in select_src
    assert "ips_app_rerun()" not in select_src


def test_serialized_tools_table_uses_html_bridge() -> None:
    src = _assets_source()
    assert "build_serialized_tools_html_table" in src
    assert "render_serialized_tools_table_bridge_legacy" in src
    table_block = src.split("def _render_small_tools_table(")[1].split("def _equipment_summary_counts")[0]
    assert "_render_serialized_tool_name_cell" not in src
    assert "_on_small_tool_checkbox_change" not in src
    assert "render_serialized_tools_table_open_buttons" not in table_block
    assert "render_serialized_tools_table_bridge_legacy" in table_block


def test_equipment_table_uses_open_buttons_and_assets_bridge() -> None:
    src = _assets_source()
    table_block = src.split("def _render_custom_assets_table(")[1].split("def _render_small_tools_table_column_filters")[0]
    assert "render_assets_table_open_buttons" in table_block
    assert "render_assets_table_bridge_legacy" in table_block
    assert "open_asset_fn=_prepare_open_assets_table_item" in table_block
    open_idx = table_block.index("render_assets_table_open_buttons")
    bridge_idx = table_block.index("render_assets_table_bridge_legacy")
    assert open_idx < bridge_idx


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
    assert "_show_assets_modal_if_selected" not in equipment_block
    assert "_show_assets_modal_if_selected" not in serialized_block


def test_asset_modal_shown_from_render_not_fragments() -> None:
    src = _assets_source()
    assert src.count("_show_assets_modal_if_selected()") == 2  # definition + render()
