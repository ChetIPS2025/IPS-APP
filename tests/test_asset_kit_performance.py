"""Performance and behavior tests for Asset Kit / Tool Trailer UI."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.components.asset_kit.forms import parse_bulk_serials
from app.components.asset_kit.item_table import build_kit_items_html_table, kit_item_detail_href
from app.components.asset_kit.state import kit_item_row_label, kit_item_select_label
from app.services.asset_kits_service import (
    get_asset_kit_summary,
    invalidate_asset_kit_cache,
    kit_data_version,
)


class TestKitItemRowLabels(unittest.TestCase):
    def test_duplicate_names_disambiguated_by_serial(self) -> None:
        items = [
            {"id": "a1", "item_name": "Drill", "serial_number": "SN-1"},
            {"id": "a2", "item_name": "Drill", "serial_number": "SN-2"},
        ]
        self.assertIn("SN-1", kit_item_row_label(items[0], items))
        self.assertIn("SN-2", kit_item_row_label(items[1], items))

    def test_select_labels_unique_by_id(self) -> None:
        items = [
            {"id": "same-name-1", "item_name": "Hammer"},
            {"id": "same-name-2", "item_name": "Hammer"},
        ]
        l1 = kit_item_select_label(items[0], items)
        l2 = kit_item_select_label(items[1], items)
        self.assertNotEqual(l1, l2)
        self.assertIn("[same-nam", l1)
        self.assertIn("[same-nam", l2)


class TestBulkSerialParsing(unittest.TestCase):
    def test_quantity_one(self) -> None:
        serials, err = parse_bulk_serials("ABC\n", expected=1)
        self.assertIsNone(err)
        self.assertEqual(serials, ["ABC"])

    def test_quantity_25(self) -> None:
        text = "\n".join(f"S{i}" for i in range(25))
        serials, err = parse_bulk_serials(text, expected=25)
        self.assertIsNone(err)
        self.assertEqual(len(serials), 25)

    def test_quantity_26_bulk(self) -> None:
        text = "\n".join(f"S{i}" for i in range(26))
        serials, err = parse_bulk_serials(text, expected=26)
        self.assertIsNone(err)
        self.assertEqual(len(serials), 26)

    def test_duplicate_serials_rejected(self) -> None:
        serials, err = parse_bulk_serials("A\nA", expected=2)
        self.assertIsNone(serials)
        self.assertIn("Duplicate", err or "")

    def test_missing_count_rejected(self) -> None:
        serials, err = parse_bulk_serials("A\nB", expected=3)
        self.assertIsNone(serials)
        self.assertIn("exactly 3", err or "")


class TestKitItemsHtmlTable(unittest.TestCase):
    def test_table_uses_links_not_checkboxes(self) -> None:
        html = build_kit_items_html_table(
            [
                {
                    "id": "item-1",
                    "item_name": "Drill",
                    "serial_number": "SN-1",
                    "item_type": "Tool",
                    "quantity_expected": 1,
                    "quantity_actual": 1,
                    "condition": "Good",
                    "status": "Present",
                    "unit_value": 100,
                    "total_value": 100,
                    "assigned_to_name": "—",
                }
            ],
            asset_id="parent-1",
            all_items=[
                {
                    "id": "item-1",
                    "item_name": "Drill",
                    "serial_number": "SN-1",
                }
            ],
        )
        self.assertIn("ips-kit-item-open-link", html)
        self.assertIn("<a ", html)
        self.assertNotIn("checkbox", html.lower())
        self.assertIn("parent-1", html)
        self.assertIn("item-1", html)

    def test_href_contains_query_params(self) -> None:
        href = kit_item_detail_href("parent-99", "item-42")
        self.assertIn("asset_detail=parent-99", href)
        self.assertIn("kit_item=item-42", href)
        self.assertIn("asset_tab=kit", href)


class TestKitSummaryFromItems(unittest.TestCase):
    def test_summary_reuses_items_without_refetch(self) -> None:
        items = [
            {
                "status": "Present",
                "total_value": 50,
                "quantity_expected": 1,
                "quantity_actual": 1,
                "unit_value": 50,
            },
            {
                "status": "Missing",
                "total_value": 30,
                "quantity_expected": 1,
                "quantity_actual": 0,
                "unit_value": 30,
            },
        ]
        with patch("app.services.asset_kits_service.get_asset_kit_items") as mock_items:
            summary = get_asset_kit_summary("aid-1", {"id": "aid-1"}, items=items)
            mock_items.assert_not_called()
        self.assertEqual(summary["expected_items"], 2)
        self.assertEqual(summary["present_items"], 1)
        self.assertEqual(summary["missing_items"], 1)


class TestKitCacheVersion(unittest.TestCase):
    @patch("app.services.asset_kits_service.st.session_state", new_callable=dict)
    def test_invalidate_bumps_version(self, session: dict) -> None:
        session["_ips_kit_data_versions"] = {"aid-1": 2}
        with patch("app.services.asset_kits_service.clear_page_data_cache_prefix"):
            with patch("app.services.asset_kits_service.clear_kit_items_list_cache"):
                invalidate_asset_kit_cache("aid-1")
        self.assertEqual(kit_data_version("aid-1"), 3)


class TestKitQueryParamHelpers(unittest.TestCase):
    @patch("app.components.asset_kit.state.st.query_params", {"kit_item": "item-1"})
    @patch("app.components.asset_kit.state.st.session_state", new_callable=dict)
    def test_valid_kit_item_selects_item(self, session: dict) -> None:
        from app.components.asset_kit.state import apply_kit_item_query_param

        items = [{"id": "item-1", "item_name": "Wrench"}]
        warn = apply_kit_item_query_param("parent-1", items)
        self.assertIsNone(warn)
        self.assertEqual(session.get("kit_sel_parent-1"), "item-1")
        self.assertEqual(session.get("kit_view_parent-1"), "detail")

    @patch("app.components.asset_kit.state.st.query_params", {"kit_item": "bad-id"})
    @patch("app.components.asset_kit.state.st.session_state", new_callable=dict)
    def test_invalid_kit_item_returns_warning(self, session: dict) -> None:
        from app.components.asset_kit.state import apply_kit_item_query_param

        qp = {"kit_item": "bad-id"}
        with patch("app.components.asset_kit.state.st.query_params", qp):
            warn = apply_kit_item_query_param("parent-1", [{"id": "item-1"}])
        self.assertEqual(warn, "bad-id")
        self.assertNotIn("kit_item", qp)


class TestLazyReferenceLoading(unittest.TestCase):
    def test_readonly_kit_tab_does_not_load_reference_options(self) -> None:
        with patch("app.components.asset_kit.assignment.st.markdown"):
            with patch("app.components.asset_kit.assignment.st.button", return_value=False):
                with patch(
                    "app.components.asset_kit.assignment.get_kit_reference_options"
                ) as mock_refs:
                    from app.components.asset_kit.assignment import render_assignment_section

                    render_assignment_section(
                        {"id": "t1", "assigned_to_name": "Sam", "assigned_job_id": ""},
                        "t1",
                    )
        mock_refs.assert_not_called()

    def test_edit_assignment_loads_employees_and_jobs(self) -> None:
        session = {"kit_assignment_edit_t1": True}
        with patch("app.components.asset_kit.assignment.st.session_state", session):
            with patch("app.components.asset_kit.assignment.st.markdown"):
                with patch(
                    "app.components.asset_kit.assignment.get_kit_reference_options"
                ) as mock_refs:
                    mock_refs.return_value = MagicMock(
                        employees=(("— None —", {}), ("Sam", {"id": "e1"})),
                        jobs=(("— None —", ""),),
                        assets=(),
                        inventory=(),
                    )
                    with patch("app.components.asset_kit.assignment.st.form") as mock_form:
                        mock_form.return_value.__enter__ = MagicMock(return_value=mock_form)
                        mock_form.return_value.__exit__ = MagicMock(return_value=False)
                        with patch("app.components.asset_kit.assignment.st.columns") as mock_cols:
                            col = MagicMock()
                            mock_cols.return_value = [col, col]
                            with patch("app.components.asset_kit.assignment.st.selectbox"):
                                with patch("app.components.asset_kit.assignment.st.text_area"):
                                    with patch(
                                        "app.components.asset_kit.assignment.st.form_submit_button",
                                        return_value=False,
                                    ):
                                        from app.components.asset_kit.assignment import (
                                            render_assignment_section,
                                        )

                                        render_assignment_section(
                                            {"id": "t1", "assigned_to_name": "Sam"},
                                            "t1",
                                        )
        mock_refs.assert_called_once_with(include_employees=True, include_jobs=True)


class TestKitFragmentRerun(unittest.TestCase):
    def test_filter_change_uses_fragment_rerun_not_full_app(self) -> None:
        src = open("app/components/asset_kit/fragment.py", encoding="utf-8").read()
        self.assertIn("fragment_rerun", src)
        self.assertIn("@fragment", src)


if __name__ == "__main__":
    unittest.main()
