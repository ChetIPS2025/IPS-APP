"""Assets Equipment and Serialized Tools directory performance regressions."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import streamlit as st

from app.pages import assets as assets_page
from app.services.assets_directory_service import AssetsDirectoryPage, list_equipment_page
from app.services.serialized_tools_directory_service import (
    SerializedToolsPage,
    build_serialized_tool_display_row,
    list_serialized_tools_page,
)


def test_equipment_fragment_uses_directory_service() -> None:
    from pathlib import Path

    src = Path("app/pages/assets.py").read_text(encoding="utf-8")
    block = src.split("@fragment\ndef _render_equipment_list")[1].split(
        "@fragment\ndef _render_small_tools_list"
    )[0]
    assert "list_equipment_page(" in block
    assert "load_assets()" not in block


def test_serialized_fragment_uses_directory_service() -> None:
    from pathlib import Path

    src = Path("app/pages/assets.py").read_text(encoding="utf-8")
    block = src.split("@fragment\ndef _render_small_tools_list")[1].split(
        "def _apply_assets_search_filter"
    )[0]
    assert "list_serialized_tools_page(" in block
    assert "_small_tool_context_maps(" not in block


def test_render_does_not_call_load_assets_for_equipment_tab() -> None:
    st.session_state.clear()
    st.session_state[assets_page._ASSETS_MAIN_TAB_KEY] = "Equipment"
    with patch("app.pages._core._access.begin_module", return_value=True):
        with patch.object(assets_page, "_render_equipment_list") as equip_mock:
            with patch("app.pages._core._data.load_assets") as load_mock:
                with patch.object(assets_page, "inject_assets_page_css"):
                    with patch("app.ui.page_header.render_page_header"):
                        with patch.object(assets_page.st, "markdown"):
                            with patch("app.components.tabs.render_tabs", return_value="Equipment"):
                                with patch.object(assets_page, "_capture_asset_detail_query"):
                                    with patch.object(assets_page, "_show_asset_detail_query_error_if_any"):
                                        assets_page.render()
    load_mock.assert_not_called()
    equip_mock.assert_called_once()


def test_build_serialized_tool_display_row_calls_view_once() -> None:
    row = {"id": "tool-1", "row_type": "asset", "asset_name": "Drill", "status": "Available"}
    with patch(
        "app.services.serialized_tools_directory_service.serialized_tool_view",
        return_value={"status": "Available", "serial_number": "SN-1"},
    ) as view_mock:
        out = build_serialized_tool_display_row(
            row,
            assets_by_id={"tool-1": row},
            employees_by_id={},
            jobs_by_id={},
        )
    view_mock.assert_called_once()
    assert out["_row_id"] == "tool-1"
    assert out["_display_name"] == "Drill"


def test_list_equipment_page_returns_only_requested_slice() -> None:
    rows = [{"id": f"a-{i}", "asset_name": f"Asset {i}", "category": "Equipment", "status": "Available"} for i in range(5)]
    with patch("app.services.assets_directory_service._load_equipment_catalog", return_value=(rows, True)):
        with patch(
            "app.services.assets_directory_service.load_equipment_filter_options",
            return_value={"category": [], "location": [], "status": ["Available"], "department": []},
        ):
            page = list_equipment_page(page=1, page_size=2)
    assert len(page.rows) == 2
    assert page.total_count == 5
