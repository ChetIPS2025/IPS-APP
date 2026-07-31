"""Small Hand Tools native detail links and query capture."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import streamlit as st

from app.components.small_hand_tools_list_table import (
    _tool_link_html,
    build_hand_tools_html_table,
    hand_tool_detail_href,
)
from app.components.small_hand_tools_ui import (
    HAND_TOOL_DETAIL_QUERY_KEY,
    capture_hand_tool_detail_query,
)


def test_hand_tool_detail_href_uses_query_param() -> None:
    href = hand_tool_detail_href({"id": "tool-1", "editable": True})
    assert "hand_tool_detail=tool-1" in href
    assert "ips_nav=assets" in href


def test_kit_item_links_to_parent_trailer_kit_tab() -> None:
    href = hand_tool_detail_href(
        {
            "id": "kit-1",
            "editable": False,
            "container_asset_id": "trailer-1",
            "row_type": "kit_item",
        }
    )
    assert "asset_detail=trailer-1" in href
    assert "asset_tab=kit" in href


def test_hand_tools_table_uses_native_links_without_open_bridge() -> None:
    src = Path("app/pages/assets.py").read_text(encoding="utf-8")
    ui_src = Path("app/components/small_hand_tools_ui.py").read_text(encoding="utf-8")
    assert "render_hand_tools_table_open_buttons" not in ui_src
    assert "capture_hand_tool_detail_query(" in src
    assert "show_hand_tool_detail_query_error_if_any()" in src


def test_tool_link_html_uses_native_href() -> None:
    html_out = _tool_link_html({"id": "tool-2", "editable": True}, "Hammer")
    assert 'href="' in html_out
    assert "hand_tool_detail=tool-2" in html_out
    assert 'target="_self"' in html_out
    assert "Hammer" in html_out
    assert 'href="#"' not in html_out


def test_build_hand_tools_html_table_renders_native_detail_links() -> None:
    from app.services.catalog_images import CatalogImageContext

    html_out = build_hand_tools_html_table(
        [
            {
                "id": "tool-3",
                "tool_name": "Pliers",
                "category": "Pliers",
                "quantity_expected": 2,
                "quantity_on_hand": 2,
                "location_display": "Shop",
                "storage_type": "Shop",
                "status": "Available",
                "editable": True,
            }
        ],
        image_context=CatalogImageContext(),
    )
    assert "hand_tool_detail=tool-3" in html_out
    assert "data-bridge-key" not in html_out


def test_capture_hand_tool_detail_query_opens_modal_without_rerun() -> None:
    from app.pages import assets as assets_page

    class _QueryParams(dict):
        def get(self, key, default=None):
            return dict.get(self, key, default)

        def __contains__(self, key):
            return dict.__contains__(self, key)

        def __delitem__(self, key):
            dict.__delitem__(self, key)

    tool = {"id": "tool-4", "tool_name": "Wrench", "editable": True}
    opened: list[dict] = []
    st.session_state = {}
    st.query_params = _QueryParams({HAND_TOOL_DETAIL_QUERY_KEY: "tool-4"})

    with patch(
        "app.components.small_hand_tools_ui._cached_hand_tool_for_modal",
        return_value=tool,
    ):
        capture_hand_tool_detail_query(
            assets_main_tab_key=assets_page._ASSETS_MAIN_TAB_KEY,
            open_tool_row_fn=lambda row: opened.append(row),
        )

    assert opened == [tool]
    assert st.session_state.get(assets_page._ASSETS_MAIN_TAB_KEY) == "Small Tools"
