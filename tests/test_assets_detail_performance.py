"""Assets detail modal and Equipment list performance regressions."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import streamlit as st

from app.pages import assets as assets_page


class TestAssetsDetailPerformance(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_detail_fast_path_skips_equipment_table(self) -> None:
        st.session_state[assets_page.SHOW_ASSET_MODAL_KEY] = True
        st.session_state[assets_page._ASSETS_MODAL_KEY] = "asset-1"

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(assets_page, "_render_equipment_list") as equip_mock:
                with patch("app.pages.assets.list_equipment_page") as list_mock:
                    with patch.object(assets_page, "_show_assets_modal_if_selected") as modal_mock:
                        with patch.object(assets_page, "inject_assets_page_css"):
                            with patch("app.ui.page_header.render_page_header"):
                                with patch.object(assets_page.st, "markdown"):
                                    assets_page.render()

        equip_mock.assert_not_called()
        list_mock.assert_not_called()
        modal_mock.assert_called_once()

    def test_detail_fast_path_does_not_call_directory_services(self) -> None:
        st.session_state[assets_page.SHOW_ASSET_MODAL_KEY] = True
        st.session_state[assets_page._ASSETS_MODAL_KEY] = "asset-2"

        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch("app.pages.assets.list_equipment_page") as equip_mock:
                with patch("app.pages.assets.list_serialized_tools_page") as serialized_mock:
                    with patch.object(assets_page, "_show_assets_modal_if_selected"):
                        with patch.object(assets_page, "inject_assets_page_css"):
                            with patch("app.ui.page_header.render_page_header"):
                                with patch.object(assets_page.st, "markdown"):
                                    assets_page.render()

        equip_mock.assert_not_called()
        serialized_mock.assert_not_called()

    def test_overview_tab_only_runs_overview_renderers(self) -> None:
        asset = {
            "id": "asset-1",
            "asset_number": "A-1",
            "asset_name": "Generator",
            "status": "Available",
        }
        st.session_state[assets_page._ASSET_DETAIL_ACTIVE_TAB_KEY] = "Overview"

        with patch("app.components.tabs.render_tabs", return_value="Overview"):
            with patch("app.pages.assets.render_kit_contents_tab") as kit_mock:
                with patch("app.pages.assets._render_asset_maintenance_tab") as maint_mock:
                    with patch("app.pages.assets._render_asset_documents_tab") as docs_mock:
                        with patch("app.pages.assets.render_asset_activity_snippet") as act_mock:
                            with patch("app.pages.assets.asset_documents_count") as count_mock:
                                with patch("app.pages.assets._render_asset_photo_manager"):
                                    with patch("app.pages.assets._render_asset_qr_section"):
                                        with patch("app.pages.assets.render_asset_reclassification_panel"):
                                            with patch("app.pages.assets.st.columns") as cols_mock:
                                                cols_mock.return_value = [MagicMock(), MagicMock()]
                                                with patch("app.pages.assets.st.markdown"):
                                                    assets_page._render_asset_detail_tabs(asset)

        kit_mock.assert_not_called()
        maint_mock.assert_not_called()
        docs_mock.assert_not_called()
        act_mock.assert_not_called()
        count_mock.assert_not_called()

    def test_maintenance_tab_queries_not_called_on_overview(self) -> None:
        asset = {"id": "asset-1", "asset_number": "A-1", "asset_name": "Gen", "status": "Available"}
        st.session_state[assets_page._ASSET_DETAIL_ACTIVE_TAB_KEY] = "Overview"

        with patch("app.components.tabs.render_tabs", return_value="Overview"):
            with patch("app.pages.assets.get_asset_inspections") as insp_mock:
                with patch("app.pages.assets.get_asset_issues") as issues_mock:
                    with patch("app.pages.assets._render_asset_photo_manager"):
                        with patch("app.pages.assets._render_asset_qr_section"):
                            with patch("app.pages.assets.render_asset_reclassification_panel"):
                                with patch("app.pages.assets.st.columns") as cols_mock:
                                    cols_mock.return_value = [MagicMock(), MagicMock()]
                                    with patch("app.pages.assets.st.markdown"):
                                        assets_page._render_asset_detail_tabs(asset)

        insp_mock.assert_not_called()
        issues_mock.assert_not_called()

    def test_documents_queries_not_called_on_overview(self) -> None:
        asset = {"id": "asset-1", "asset_number": "A-1", "asset_name": "Gen", "status": "Available"}
        st.session_state[assets_page._ASSET_DETAIL_ACTIVE_TAB_KEY] = "Overview"

        with patch("app.components.tabs.render_tabs", return_value="Overview"):
            with patch("app.pages.assets._render_asset_documents_tab") as docs_mock:
                with patch("app.pages.assets.asset_documents_count") as count_mock:
                    with patch("app.pages.assets._render_asset_photo_manager"):
                        with patch("app.pages.assets._render_asset_qr_section"):
                            with patch("app.pages.assets.render_asset_reclassification_panel"):
                                with patch("app.pages.assets.st.columns") as cols_mock:
                                    cols_mock.return_value = [MagicMock(), MagicMock()]
                                    with patch("app.pages.assets.st.markdown"):
                                        assets_page._render_asset_detail_tabs(asset)

        docs_mock.assert_not_called()
        count_mock.assert_not_called()

    def test_kit_contents_not_called_on_overview(self) -> None:
        asset = {"id": "asset-1", "asset_number": "A-1", "asset_name": "Gen", "status": "Available"}
        st.session_state[assets_page._ASSET_DETAIL_ACTIVE_TAB_KEY] = "Overview"

        with patch("app.components.tabs.render_tabs", return_value="Overview"):
            with patch("app.pages.assets.render_kit_contents_tab") as kit_mock:
                with patch("app.pages.assets._render_asset_photo_manager"):
                    with patch("app.pages.assets._render_asset_qr_section"):
                        with patch("app.pages.assets.render_asset_reclassification_panel"):
                            with patch("app.pages.assets.st.columns") as cols_mock:
                                cols_mock.return_value = [MagicMock(), MagicMock()]
                                with patch("app.pages.assets.st.markdown"):
                                    assets_page._render_asset_detail_tabs(asset)

        kit_mock.assert_not_called()

    def test_qr_block_not_called_until_requested(self) -> None:
        asset = {"id": "asset-1", "asset_number": "A-1", "asset_name": "Gen", "status": "Available"}

        with patch("app.pages.assets.st.button", return_value=False):
            with patch("app.pages.assets._render_asset_qr_block") as qr_mock:
                assets_page._render_asset_qr_section(asset, "asset-1")

        qr_mock.assert_not_called()

        st.session_state[assets_page._asset_qr_loaded_key("asset-1")] = True
        with patch("app.pages.assets._render_asset_qr_block") as qr_mock:
            assets_page._render_asset_qr_section(asset, "asset-1")
        qr_mock.assert_called_once()

    def test_bulk_move_toolbar_not_rendered_while_closed(self) -> None:
        from pathlib import Path

        src = Path("app/pages/assets.py").read_text(encoding="utf-8")
        equip_block = src.split("@fragment\ndef _render_equipment_list")[1].split(
            "@fragment\ndef _render_small_tools_list"
        )[0]
        assert 'with st.expander("Bulk move tools"' not in equip_block
        assert "_BULK_MOVE_OPEN_KEY" in equip_block
        assert "render_equipment_bulk_move_toolbar" in equip_block

    def test_equipment_fragment_uses_directory_service(self) -> None:
        from pathlib import Path

        src = Path("app/pages/assets.py").read_text(encoding="utf-8")
        equip_block = src.split("@fragment\ndef _render_equipment_list")[1].split(
            "@fragment\ndef _render_small_tools_list"
        )[0]
        assert "list_equipment_page" in equip_block
        assert "load_assets()" not in equip_block

    def test_assets_catalog_version_increments_on_cache_clear(self) -> None:
        from app.pages._core._data import assets_catalog_data_version, clear_assets_catalog_cache

        st.session_state.clear()
        self.assertEqual(assets_catalog_data_version(), 0)
        clear_assets_catalog_cache()
        self.assertEqual(assets_catalog_data_version(), 1)
        clear_assets_catalog_cache()
        self.assertEqual(assets_catalog_data_version(), 2)

    def test_clear_detail_modal_restores_list_path(self) -> None:
        st.session_state[assets_page.SHOW_ASSET_MODAL_KEY] = True
        st.session_state[assets_page._ASSETS_MODAL_KEY] = "asset-1"
        st.session_state[assets_page._ALL_ASSET_IDS_KEY] = []

        def _clear_modal_keys(**_kwargs: object) -> None:
            st.session_state.pop(assets_page._ASSETS_MODAL_KEY, None)
            st.session_state.pop(assets_page._SEL, None)

        with patch("app.pages.assets.clear_edit_modes"):
            with patch("app.pages.assets.clear_record_modal", side_effect=_clear_modal_keys):
                assets_page._clear_assets_detail_modal()

        self.assertFalse(assets_page._detail_modal_pending())

    def test_native_asset_links_still_present(self) -> None:
        from app.components.assets_list_table import asset_detail_href, build_assets_html_table

        href = asset_detail_href("ast-1")
        assert "asset_detail=ast-1" in href
        html_out = build_assets_html_table(
            [{"id": "ast-1", "asset_name": "Generator", "asset_number": "A-1"}]
        )
        assert "asset_detail=ast-1" in html_out

    def test_field_mode_expansion_still_wired(self) -> None:
        from pathlib import Path

        src = Path("app/pages/assets.py").read_text(encoding="utf-8")
        table_block = src.split("def _render_custom_assets_table(")[1].split(
            "def _render_small_tools_table_column_filters"
        )[0]
        assert "if field_mode:" in table_block
        assert "render_assets_table_bridge_legacy" in table_block
        assert "_render_asset_expand_panel" in table_block


if __name__ == "__main__":
    unittest.main()
