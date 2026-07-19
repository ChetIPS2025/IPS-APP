"""Estimate Cost Builder performance and behavior regression tests."""

from __future__ import annotations

import ast
import inspect
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import streamlit as st

from app.components.estimate_builder.state import (
    DEFAULT_BATCH_ROW_COUNT,
    MAX_BATCH_DRAFT_ROWS,
    maybe_auto_extend_batch_draft,
)
from app.pages import estimate_builder_ui as builder_ui
from app.services.estimate_cost_cache import (
    estimate_cost_data_version,
    invalidate_estimate_cost_cache,
)
from app.services.estimate_costing_service import finalize_estimate_cost_write


class TestHiddenWriteRemoval(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_cost_builder_tab_source_has_no_auto_recalc_on_open(self) -> None:
        src = inspect.getsource(builder_ui.render_cost_builder_tab)
        assert "recalculate_and_save_estimate_totals" not in src
        assert "_recalc_and_cache_cost_builder_totals(eid, est)" not in src.split("Recalculate Totals")[0]

    def test_summary_tab_does_not_save_totals_on_render(self) -> None:
        est = {"id": "e-1", "tax_rate": 0, "customer_price": 100.0, "total_cost": 80.0}
        with patch.object(builder_ui, "load_estimate_cost_builder_snapshot") as snap_mock:
            snap_mock.return_value = MagicMock(
                totals={"customer_price": 100.0, "total_cost": 80.0, "gross_margin_percent": 20.0},
                warning=None,
            )
            with patch.object(builder_ui, "render_cost_summary_cards") as cards_mock:
                with patch.object(builder_ui, "load_estimate_builder_permissions") as perm_mock:
                    perm_mock.return_value = MagicMock(can_recalculate=False)
                    with patch.object(builder_ui.st, "button", return_value=False):
                        with patch.object(builder_ui.st, "markdown"):
                            with patch.object(builder_ui.st, "warning"):
                                builder_ui.render_summary_tab(est)
        with patch("app.services.estimate_costing_service.recalculate_and_save_estimate_totals") as save_mock:
            save_mock.assert_not_called()
        cards_mock.assert_called_once()

    def test_proposal_tab_does_not_build_on_first_render(self) -> None:
        est = {"id": "e-1", "estimate_number": "Q-1"}
        with patch.object(builder_ui, "load_estimate_cost_builder_snapshot") as snap_mock:
            snap_mock.return_value = MagicMock(cost_data_version=1)
            with patch.object(builder_ui.st, "button", return_value=False):
                with patch.object(builder_ui.st, "markdown"):
                    with patch("app.services.proposal_pdf_service.build_customer_quote_bundle") as build_mock:
                        builder_ui.render_proposal_preview_tab(est)
        build_mock.assert_not_called()

    def test_explicit_finalize_persists_totals(self) -> None:
        with patch(
            "app.services.estimate_costing_service.recalculate_and_save_estimate_totals",
            return_value=MagicMock(ok=True, data={"customer_price": 200.0}),
        ) as save_mock:
            with patch("app.services.estimate_cost_cache.invalidate_estimate_cost_cache", return_value=1):
                with patch("app.services.estimate_cost_cache.write_cached_totals"):
                    with patch("app.services.estimate_cost_cache.clear_proposal_bundle"):
                        with patch("app.services.estimate_costing_service.clear_estimate_cache"):
                            result = finalize_estimate_cost_write("e-1", tax_rate=0.0)
        save_mock.assert_called_once()
        assert result.ok is True


class TestBatchDraftLimits(unittest.TestCase):
    def test_default_batch_row_count_is_five(self) -> None:
        assert DEFAULT_BATCH_ROW_COUNT == 5

    def test_max_batch_draft_rows_is_twenty_five(self) -> None:
        assert MAX_BATCH_DRAFT_ROWS == 25

    def test_auto_extend_stops_at_max(self) -> None:
        st.session_state.clear()
        draft_key = "test_draft"
        rows = [{"rid": f"r{i}"} for i in range(MAX_BATCH_DRAFT_ROWS)]
        st.session_state[draft_key] = rows
        capped = maybe_auto_extend_batch_draft(
            draft_key,
            rows,
            is_row_filled=lambda _rid: True,
            append_row=lambda: {"rid": "new"},
        )
        assert capped is True
        assert len(st.session_state[draft_key]) == MAX_BATCH_DRAFT_ROWS


class TestCostDataVersion(unittest.TestCase):
    def setUp(self) -> None:
        st.session_state.clear()

    def test_invalidate_increments_version(self) -> None:
        assert estimate_cost_data_version("e-99") == 0
        v1 = invalidate_estimate_cost_cache("e-99")
        v2 = invalidate_estimate_cost_cache("e-99")
        assert v1 == 1
        assert v2 == 2
        assert estimate_cost_data_version("e-99") == 2


class TestCategoryIsolation(unittest.TestCase):
    def test_equipment_tab_uses_list_not_bundle(self) -> None:
        src = inspect.getsource(builder_ui.render_equipment_tab)
        assert "get_estimate_bundle" not in src
        assert "list_estimate_equipment_lines" in src or "_render_paginated_category_lines" in src

    def test_lazy_add_does_not_open_form_by_default(self) -> None:
        src = inspect.getsource(builder_ui.render_labor_tab)
        assert "_open_tab_entry_form" not in src
        assert "_render_lazy_add_button" in src


class TestCostSummaryCardsPure(unittest.TestCase):
    def test_summary_cards_requires_totals(self) -> None:
        sig = inspect.signature(builder_ui.render_cost_summary_cards)
        assert "totals" in sig.parameters
        assert sig.parameters["totals"].default is inspect.Parameter.empty


class TestReferenceServices(unittest.TestCase):
    def test_material_search_does_not_load_full_catalog_helper(self) -> None:
        path = Path(__file__).resolve().parents[1] / "app" / "services" / "estimate_builder_reference_service.py"
        src = path.read_text(encoding="utf-8")
        assert "load_inventory()" not in src
        assert "load_assets()" in src  # rentable search scans assets with filter

    def test_search_estimate_material_options_caps_limit(self) -> None:
        from app.services.estimate_builder_reference_service import search_estimate_material_options

        with patch(
            "app.services.pricing_guide_service.cached_pricing_guide_rows",
            return_value=[{"id": f"p{i}", "description": f"Item {i}", "item_type": "Material", "is_active": True} for i in range(200)],
        ):
            with patch("app.services.pricing_guide_service.pricing_item_to_estimate_option", side_effect=lambda r: {**r, "unit_cost": 1.0, "markup_pct": 0}):
                with patch("app.pages._core.page_data_cache.page_data_cache_get", side_effect=lambda _k, fn: fn()):
                    rows = search_estimate_material_options(limit=50)
        assert len(rows) <= 50


if __name__ == "__main__":
    unittest.main()
