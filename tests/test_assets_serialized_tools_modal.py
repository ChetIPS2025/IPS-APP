"""Regression tests: Serialized Tools must app-rerun to open asset detail modal."""

from __future__ import annotations

import inspect
from pathlib import Path


def _assets_source() -> str:
    path = Path(__file__).resolve().parents[1] / "app" / "pages" / "assets.py"
    return path.read_text(encoding="utf-8")


def test_serialized_tool_name_click_uses_app_rerun() -> None:
    from app.pages import assets as assets_page

    src = inspect.getsource(assets_page._open_small_tool_row)
    assert "ips_app_rerun()" in src


def test_serialized_tool_checkbox_prepares_modal_without_callback_rerun() -> None:
    from app.pages import assets as assets_page

    checkbox_src = inspect.getsource(assets_page._on_small_tool_checkbox_change)
    name_src = inspect.getsource(assets_page._render_serialized_tool_name_cell)

    assert "_prepare_open_small_tool_row(" in checkbox_src
    assert "_open_small_tool_row(" not in checkbox_src.replace("_prepare_open_small_tool_row(", "")
    assert "_open_small_tool_row(" in name_src
    assert "_prepare_open_small_tool_row(" not in name_src


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
