"""Estimate Materials performance and Cost Builder integration regressions."""

from __future__ import annotations

import ast
import html
import inspect
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.estimate_materials.list_table import build_estimate_material_lines_html
from app.components.estimate_materials.state import (
    _MAX_TAKEOFF_DRAFT_ROWS,
    _TAKEOFF_DRAFT_COUNT,
    clear_material_takeoff_draft,
    takeoff_open_key,
)
from app.components.estimate_builder.state import maybe_auto_extend_batch_draft
from app.pages import estimate_materials as materials_page
from app.services.estimate_costing_service import (
    add_estimate_material_batch,
    finalize_estimate_cost_write,
    normalize_material_line,
)
from app.services.estimate_material_reference_service import search_estimate_inventory_options
from app.services.estimate_materials_page_service import (
    list_estimate_material_lines_page,
    prepare_material_export_bytes,
)


class TestServiceConsolidation(unittest.TestCase):
    def test_normalize_material_line_maps_legacy_qty(self) -> None:
        row = normalize_material_line(
            {"id": "l1", "qty": 3, "unit_cost": 10, "markup_percent": 20, "total_cost": 30},
            "e-1",
        )
        assert row["quantity"] == 3.0
        assert row["cost_total"] == 30.0

    def test_batch_save_recalculates_once(self) -> None:
        with patch("app.services.estimate_costing_service._insert_estimate_line_item", return_value=MagicMock(ok=True)):
            with patch("app.services.estimate_costing_service.finalize_estimate_cost_write") as fin_mock:
                with patch("app.services.estimate_costing_service.get_estimate_materials", return_value=([], False)):
                    result = add_estimate_material_batch(
                        "e-1",
                        [{"description": "A", "quantity": 1, "unit_cost": 5, "markup_percent": 0}],
                    )
        assert result.ok is True
        fin_mock.assert_called_once()

    def test_panel_does_not_call_load_inventory(self) -> None:
        src = inspect.getsource(materials_page.render_estimate_materials_panel)
        assert "load_inventory()" not in src
        assert "load_estimate_materials(" not in src
        assert "persist_estimate_material(" not in src

    def test_panel_does_not_call_legacy_materials_summary(self) -> None:
        src = inspect.getsource(materials_page.render_estimate_materials_panel)
        assert "from app.pages._core._data import" not in src or "materials_summary" not in src.split("from app.pages._core._data import")[-1]
        assert "get_estimate_materials_summary(" in src


class TestInventorySearch(unittest.TestCase):
    def test_reference_service_does_not_load_inventory_helper(self) -> None:
        path = Path(__file__).resolve().parents[1] / "app" / "services" / "estimate_material_reference_service.py"
        src = path.read_text(encoding="utf-8")
        assert "load_inventory()" not in src

    def test_search_caps_results(self) -> None:
        rows = [
            {
                "id": f"p{i}",
                "description": f"Item {i}",
                "item_type": "Material",
                "is_active": True,
                "sku": f"SKU{i}",
            }
            for i in range(200)
        ]
        with patch(
            "app.services.pricing_guide_service.cached_pricing_guide_rows",
            return_value=rows,
        ):
            with patch(
                "app.services.pricing_guide_service.pricing_item_to_estimate_option",
                side_effect=lambda r: {**r, "unit_cost": 1.0, "markup_pct": 0, "pricing_item_id": r["id"]},
            ):
                with patch("app.services.repository.fetch_rows", return_value=([], None)):
                    with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                        out = search_estimate_inventory_options(limit=50)
        assert len(out) <= 50

    def test_custom_item_constant_exists(self) -> None:
        from app.services.estimate_material_reference_service import _CUSTOM_INVENTORY_LABEL

        assert "Custom" in _CUSTOM_INVENTORY_LABEL


class TestLazyTakeoff(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_takeoff_not_open_by_default(self) -> None:
        assert st.session_state.get(takeoff_open_key("e-1")) is None

    def test_initial_draft_count_is_five(self) -> None:
        assert _TAKEOFF_DRAFT_COUNT == 5

    def test_max_draft_rows_is_twenty_five(self) -> None:
        assert _MAX_TAKEOFF_DRAFT_ROWS == 25

    def test_auto_extend_stops_at_max(self) -> None:
        draft_key = "mat_takeoff_batch_e-1"
        rows = [{"rid": f"r{i}"} for i in range(_MAX_TAKEOFF_DRAFT_ROWS)]
        st.session_state[draft_key] = rows
        capped = maybe_auto_extend_batch_draft(
            draft_key,
            rows,
            is_row_filled=lambda _rid: True,
            append_row=lambda: {"rid": "new"},
        )
        assert capped is True
        assert len(st.session_state[draft_key]) == _MAX_TAKEOFF_DRAFT_ROWS

    def test_clear_draft_removes_keys(self) -> None:
        eid = "e-99"
        st.session_state[takeoff_open_key(eid)] = True
        st.session_state[f"mat_to_{eid}_item_abc"] = "X"
        clear_material_takeoff_draft(eid)
        assert takeoff_open_key(eid) not in st.session_state
        assert f"mat_to_{eid}_item_abc" not in st.session_state


class TestPaginationAndTable(unittest.TestCase):
    def test_list_page_returns_slice(self) -> None:
        rows = [
            normalize_material_line(
                {"id": f"m{i}", "estimate_id": "e-1", "description": f"Line {i}", "qty": 1, "unit_cost": 1},
                "e-1",
            )
            for i in range(30)
        ]
        with patch("app.services.estimate_materials_page_service.get_estimate_materials", return_value=(rows, False)):
            with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                page = list_estimate_material_lines_page("e-1", page=2, page_size=10)
        assert page.total_count == 30
        assert len(page.rows) == 10
        assert page.page == 2

    def test_html_table_escapes_values(self) -> None:
        html_out = build_estimate_material_lines_html(
            [
                {
                    "id": "line-1",
                    "item_number": "<script>",
                    "description": "A & B",
                    "category": "Cat",
                    "quantity": 1,
                    "unit": "EA",
                    "unit_cost": 1,
                    "cost_total": 1,
                    "markup_percent": 0,
                    "price_total": 1,
                }
            ],
            estimate_id="e-1",
        )
        assert "<script>" not in html_out
        assert "&lt;script&gt;" in html_out
        assert "A &amp; B" in html_out

    def test_detail_links_use_stable_ids(self) -> None:
        html_out = build_estimate_material_lines_html(
            [{"id": "line-abc", "item_number": "SKU-1", "description": "Valve", "quantity": 1, "unit_cost": 1, "cost_total": 1, "price_total": 1}],
            estimate_id="e-1",
        )
        assert "material_detail=line-abc" in html_out


class TestExportExplicit(unittest.TestCase):
    def test_panel_source_has_prepare_export_not_auto_csv(self) -> None:
        src = inspect.getsource(materials_page.render_estimate_materials_panel)
        assert "Prepare Materials Export" in src or "_render_export_fragment" in src
        assert "_materials_csv_bytes" not in src

    def test_export_uses_authoritative_fields(self) -> None:
        rows = [
            normalize_material_line(
                {
                    "id": "m1",
                    "estimate_id": "e-1",
                    "item_number": "SKU",
                    "description": "Part",
                    "qty": 2,
                    "unit_cost": 5,
                    "markup_percent": 10,
                    "price_total": 11,
                    "taxable": True,
                    "vendor": "Vendor A",
                },
                "e-1",
            )
        ]
        with patch("app.services.estimate_materials_page_service.get_estimate_materials", return_value=(rows, False)):
            with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                data = prepare_material_export_bytes("e-1")
        text = data.decode("utf-8")
        assert "quantity" in text
        assert "markup_percent" in text
        assert "Part" in text


class TestStandaloneRedirect(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_render_redirects_once_when_estimate_active(self) -> None:
        from app.pages._core._data import ACTIVE_ESTIMATE_KEY

        st.session_state[ACTIVE_ESTIMATE_KEY] = "e-redirect"
        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(materials_page, "navigate_to_estimate_detail") as nav_mock:
                with patch.object(materials_page, "current_nav_slug", return_value="estimate_materials"):
                    with patch.object(materials_page, "ips_app_rerun") as rerun_mock:
                        materials_page.render()
        nav_mock.assert_called_once_with("e-redirect", tab="Materials")
        rerun_mock.assert_called_once()

    def test_no_redirect_loop_when_already_on_estimates(self) -> None:
        from app.pages._core._data import ACTIVE_ESTIMATE_KEY

        st.session_state[ACTIVE_ESTIMATE_KEY] = "e-redirect"
        st.session_state[materials_page._STANDALONE_REDIRECT_KEY] = "e-redirect"
        with patch("app.pages._core._access.begin_module", return_value=True):
            with patch.object(materials_page, "navigate_to_estimate_detail") as nav_mock:
                with patch.object(materials_page, "current_nav_slug", return_value="estimates"):
                    with patch.object(materials_page.st, "info"):
                        materials_page.render()
        nav_mock.assert_not_called()


class TestImportSmoke(unittest.TestCase):
    def test_estimate_materials_imports_cleanly(self) -> None:
        tree = ast.parse(Path("app/pages/estimate_materials.py").read_text(encoding="utf-8"))
        assert tree is not None


class TestFinalizeIntegration(unittest.TestCase):
    def test_finalize_estimate_cost_write_called_from_batch(self) -> None:
        with patch(
            "app.services.estimate_costing_service.recalculate_and_save_estimate_totals",
            return_value=MagicMock(ok=True, data={"customer_price": 100.0}),
        ):
            with patch("app.services.estimate_cost_cache.invalidate_estimate_cost_cache", return_value=1):
                with patch("app.services.estimate_cost_cache.write_cached_totals"):
                    with patch("app.services.estimate_cost_cache.clear_proposal_bundle"):
                        with patch("app.services.estimate_costing_service.clear_estimate_cache"):
                            result = finalize_estimate_cost_write("e-1", tax_rate=0.0)
        assert result.ok is True


if __name__ == "__main__":
    unittest.main()
