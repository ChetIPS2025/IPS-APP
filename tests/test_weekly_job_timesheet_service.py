"""Tests for weekly job timesheet charge sections."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from app.services.weekly_job_timesheet_service import (
    TimesheetLine,
    WeeklyJobTimesheetData,
    _build_charges_from_job_cost_transactions,
    _weekly_summary,
    build_timesheet_data,
    render_timesheet_html,
)


class TestWeeklyJobTimesheetCharges(unittest.TestCase):
    def test_weekly_summary_totals(self) -> None:
        data = WeeklyJobTimesheetData(
            labor_lines=[
                TimesheetLine(line_type="labor", description="Alice", st_hours=8, ot_hours=2),
            ],
            material_lines=[TimesheetLine(line_type="material", description="Pipe", qty=2, unit_cost=10, cost=20)],
            equipment_lines=[TimesheetLine(line_type="equipment", description="Lift", qty=1, unit_cost=150, cost=150)],
            other_lines=[TimesheetLine(line_type="expense", description="Permit", qty=1, unit_cost=75, cost=75)],
        )
        totals = _weekly_summary(data)
        self.assertEqual(totals["labor_hours"], 10.0)
        self.assertEqual(totals["materials"], 20.0)
        self.assertEqual(totals["equipment"], 150.0)
        self.assertEqual(totals["other"], 75.0)
        self.assertEqual(totals["charges"], 245.0)

    @patch("app.services.job_cost_transaction_service.fetch_job_cost_transactions")
    def test_build_charges_skips_hidden_invoice_lines(self, fetch_mock) -> None:
        fetch_mock.return_value = [
            {
                "transaction_date": "2026-05-28",
                "cost_category": "material",
                "quantity": 1,
                "unit_cost": 10,
                "total_cost": 10,
                "description": "Visible",
                "show_on_invoice": True,
            },
            {
                "transaction_date": "2026-05-28",
                "cost_category": "material",
                "quantity": 1,
                "unit_cost": 99,
                "total_cost": 99,
                "description": "Hidden",
                "show_on_invoice": False,
            },
        ]
        with patch("app.services.weekly_job_timesheet_service._safe_admin_fetch", return_value=[]):
            materials, equipment, other = _build_charges_from_job_cost_transactions(
                "job-1",
                date(2026, 5, 25),
                date(2026, 5, 31),
            )
        self.assertEqual(len(materials), 1)
        self.assertEqual(materials[0].description, "Visible")

    @patch("app.services.job_cost_transaction_service.fetch_job_cost_transactions")
    def test_build_charges_from_job_cost_transactions(self, fetch_mock) -> None:
        fetch_mock.return_value = [
            {
                "transaction_date": "2026-05-28",
                "cost_category": "labor",
                "total_cost": 500,
                "description": "Should skip",
            },
            {
                "transaction_date": "2026-05-27",
                "cost_category": "material",
                "quantity": 3,
                "unit_cost": 12.5,
                "total_cost": 37.5,
                "description": "Gloves",
                "notes": "Inventory scan",
            },
            {
                "transaction_date": "2026-05-29",
                "cost_category": "equipment",
                "quantity": 2,
                "unit_cost": 100,
                "total_cost": 200,
                "item_name": "Forklift",
                "notes": "Equipment assignment (day)",
                "asset_id": "asset-1",
            },
            {
                "transaction_date": "2026-05-30",
                "cost_category": "other",
                "quantity": 1,
                "unit_cost": 40,
                "total_cost": 40,
                "description": "Misc fee",
            },
        ]
        with patch("app.services.weekly_job_timesheet_service._safe_admin_fetch", return_value=[]):
            materials, equipment, other = _build_charges_from_job_cost_transactions(
                "job-1",
                date(2026, 5, 25),
                date(2026, 5, 31),
            )
        self.assertEqual(len(materials), 1)
        self.assertEqual(materials[0].description, "Gloves")
        self.assertEqual(materials[0].line_total, 37.5)
        self.assertEqual(len(equipment), 1)
        self.assertEqual(equipment[0].charge_unit, "day")
        self.assertEqual(len(other), 1)
        self.assertEqual(other[0].description, "Misc fee")

    @patch("app.services.weekly_job_timesheet_service._build_work_performed", return_value="")
    @patch("app.services.weekly_job_timesheet_service._build_charges_from_job_cost_transactions")
    @patch("app.services.weekly_job_timesheet_service._build_labor_from_timekeeping_days")
    @patch("app.services.weekly_job_timesheet_service._employees_map", return_value={})
    @patch("app.services.job_cost_transaction_service.sync_all_sources_for_job")
    @patch("app.services.weekly_job_timesheet_service.get_job_timesheet_header")
    @patch("app.services.weekly_job_timesheet_service._fetch_job")
    def test_build_timesheet_data_separates_equipment(
        self,
        job_mock,
        header_mock,
        sync_mock,
        emp_mock,
        labor_mock,
        charges_mock,
        work_mock,
    ) -> None:
        job_mock.return_value = {"id": "job-1", "job_number": "100"}
        header_mock.return_value = {
            "job_number": "100",
            "client_name": "Acme",
            "job_name": "Demo",
            "po_number": "PO-1",
            "sheet_date": "2026-05-31",
            "week_start": "2026-05-25",
            "week_end": "2026-05-31",
        }
        labor_mock.return_value = [TimesheetLine(line_type="labor", description="Bob", st_hours=8)]
        charges_mock.return_value = (
            [TimesheetLine(line_type="material", description="Bolt", cost=5)],
            [TimesheetLine(line_type="equipment", description="Crane", cost=300)],
            [],
        )
        data = build_timesheet_data("job-1", date(2026, 5, 25))
        self.assertEqual(len(data.labor_lines), 1)
        self.assertEqual(data.labor_lines[0].line_type, "labor")
        self.assertEqual(len(data.material_lines), 1)
        self.assertEqual(len(data.equipment_lines), 1)
        self.assertFalse(any(ln.line_type == "equipment" for ln in data.labor_lines))

    def test_render_html_includes_all_sections(self) -> None:
        data = WeeklyJobTimesheetData(
            job_number="100",
            client_name="Acme",
            job_name="Demo",
            week_start="2026-05-25",
            week_end="2026-05-31",
            sheet_date="2026-05-31",
            labor_lines=[TimesheetLine(line_type="labor", description="Bob", st_hours=8)],
            material_lines=[TimesheetLine(line_type="material", description="Bolt", qty=1, cost=5)],
            equipment_lines=[TimesheetLine(line_type="equipment", description="Crane", qty=1, cost=300)],
            other_lines=[TimesheetLine(line_type="expense", description="Fee", qty=1, cost=25)],
        )
        html_doc = render_timesheet_html(data, week_start=date(2026, 5, 25))
        self.assertIn("1. LABOR", html_doc)
        self.assertIn("2. INVENTORY / MATERIALS", html_doc)
        self.assertIn("3. EQUIPMENT", html_doc)
        self.assertIn("4. OTHER CHARGES", html_doc)
        self.assertIn("5. WEEKLY SUMMARY / TOTALS", html_doc)
        self.assertIn("Bolt", html_doc)
        self.assertIn("Crane", html_doc)


if __name__ == "__main__":
    unittest.main()
