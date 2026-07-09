"""Tests for job save payload normalization."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import patch

from app.services.phase2_modules_service import (
    _filter_job_save_payload,
    _filter_job_update_payload,
    _format_job_save_dev_detail,
    _job_save_date,
    _job_save_money_normalized,
    _job_save_supervisor_text,
    _job_save_text,
    save_job,
)
from app.services.repository import ServiceResult


class TestJobSavePayload(unittest.TestCase):
    def test_job_save_text_coerces_none_to_empty_string(self) -> None:
        self.assertEqual(_job_save_text(None), "")
        self.assertEqual(_job_save_text("Earl Lafont"), "Earl Lafont")

    def test_job_save_date_serializes_date_object(self) -> None:
        self.assertEqual(_job_save_date(date(2024, 6, 22)), "2024-06-22")
        self.assertIsNone(_job_save_date(None))
        self.assertIsNone(_job_save_date(""))

    def test_job_save_money_normalized_blank_defaults_to_none(self) -> None:
        self.assertIsNone(_job_save_money_normalized(None))
        self.assertIsNone(_job_save_money_normalized(""))
        self.assertEqual(_job_save_money_normalized("1250.5"), 1250.5)

    def test_job_save_money_normalized_blank_as_zero_for_insert(self) -> None:
        self.assertEqual(_job_save_money_normalized(None, blank_as_zero=True), 0.0)
        self.assertEqual(_job_save_money_normalized("", blank_as_zero=True), 0.0)

    def test_job_save_supervisor_text_maps_blank_labels_to_empty(self) -> None:
        self.assertEqual(_job_save_supervisor_text("—"), "")
        self.assertEqual(_job_save_supervisor_text("— Select —"), "")
        self.assertEqual(_job_save_supervisor_text("Pat Smith"), "Pat Smith")

    def test_filter_job_save_payload_drops_readonly_fields(self) -> None:
        payload = {
            "job_name": "Tower repaint",
            "awarded_amount": 10000.0,
            "projected_gross_profit": 3000.0,
            "projected_margin_pct": 30.0,
            "actual_cost": 500.0,
            "estimated_profit": 2500.0,
            "profit_percent": 25.0,
        }
        filtered = _filter_job_save_payload(payload)
        self.assertEqual(filtered["job_name"], "Tower repaint")
        self.assertEqual(filtered["awarded_amount"], 10000.0)
        self.assertNotIn("projected_gross_profit", filtered)
        self.assertNotIn("projected_margin_pct", filtered)
        self.assertNotIn("actual_cost", filtered)
        self.assertNotIn("estimated_profit", filtered)
        self.assertNotIn("profit_percent", filtered)

    def test_filter_job_update_payload_excludes_job_number_and_readonly(self) -> None:
        payload = {
            "status": "Active",
            "job_number": "J-100",
            "customer_name": "Acme",
            "awarded_amount": 5000.0,
            "projected_margin_pct": 12.0,
            "updated_at": "2024-01-01",
        }
        filtered = _filter_job_update_payload(payload)
        self.assertEqual(filtered["status"], "Active")
        self.assertEqual(filtered["awarded_amount"], 5000.0)
        self.assertNotIn("job_number", filtered)
        self.assertNotIn("customer_name", filtered)
        self.assertNotIn("projected_margin_pct", filtered)
        self.assertNotIn("updated_at", filtered)

    def test_format_job_save_dev_detail_includes_required_fields(self) -> None:
        detail = _format_job_save_dev_detail(
            RuntimeError("column jobs.foo does not exist"),
            job_id="job-9",
            payload={"status": "Active", "notes": "x"},
        )
        self.assertIn("Job ID: job-9", detail)
        self.assertIn("Payload keys:", detail)
        self.assertIn("notes", detail)
        self.assertIn("Error type: RuntimeError", detail)
        self.assertIn("column jobs.foo does not exist", detail)

    @patch("app.db.fetch_one")
    @patch("app.services.phase2_modules_service.update_row")
    @patch("app.services.phase2_modules_service.table_column_names")
    @patch("app.services.phase2_modules_service._resolve_customer_id_for_job", return_value="cust-1")
    @patch("app.services.phase2_modules_service._resolve_supervisor_id_for_job", return_value=None)
    def test_save_job_update_maps_scope_and_notes_separately(
        self,
        _supervisor_mock,
        _resolve_mock,
        cols_mock,
        update_mock,
        fetch_one_mock,
    ) -> None:
        cols_mock.return_value = frozenset(
            {
                "job_name",
                "status",
                "supervisor",
                "supervisor_id",
                "start_date",
                "target_completion_date",
                "scope_of_work",
                "notes",
                "customer_id",
                "awarded_amount",
                "estimated_cost",
                "po_number",
                "po_date",
                "po_amount",
                "billing_type",
                "percent_complete",
            }
        )
        fetch_one_mock.return_value = {
            "id": "job-1",
            "status": "Active",
            "awarded_amount": 5000,
        }
        update_mock.return_value = ServiceResult(ok=True, data={"id": "job-1"})

        ui = {
            "job_name": "Paint job",
            "job_number": "J-999",
            "status": "Active",
            "supervisor": "— Select —",
            "scope_of_work": "Prep and paint tank exterior",
            "notes": "Customer wants weekend work",
            "contract_value": 12000,
            "estimated_cost": 8000,
            "po_number": "PO-44",
            "po_date": None,
            "po_amount": "",
            "billing_type": "Fixed Price",
            "progress": 10,
        }
        result = save_job(ui, row_id="job-1")
        self.assertTrue(result.ok)
        update_mock.assert_called_once()
        _table, payload, match = update_mock.call_args[0]
        self.assertEqual(_table, "jobs")
        self.assertEqual(match, {"id": "job-1"})
        self.assertEqual(payload["scope_of_work"], "Prep and paint tank exterior")
        self.assertEqual(payload["notes"], "Customer wants weekend work")
        self.assertEqual(payload["awarded_amount"], 12000.0)
        self.assertEqual(payload["estimated_cost"], 8000.0)
        self.assertIsNone(payload["po_amount"])
        self.assertIsNone(payload["po_date"])
        self.assertEqual(payload["supervisor"], "")
        self.assertIsNone(payload["supervisor_id"])
        self.assertNotIn("job_number", payload)
        self.assertNotIn("projected_gross_profit", payload)
        self.assertNotIn("projected_margin_pct", payload)

    @patch("app.db.fetch_one")
    @patch("app.services.phase2_modules_service.update_row")
    @patch("app.services.phase2_modules_service.table_column_names")
    @patch("app.services.phase2_modules_service._resolve_customer_id_for_job", return_value="cust-1")
    def test_save_job_update_failure_returns_structured_dev_detail(
        self,
        _resolve_mock,
        cols_mock,
        update_mock,
        fetch_one_mock,
    ) -> None:
        cols_mock.return_value = frozenset({"status", "notes"})
        fetch_one_mock.return_value = {"id": "job-2", "status": "Active", "awarded_amount": 100}
        update_mock.return_value = ServiceResult(
            ok=False,
            error="Could not complete your update jobs. Please try again.",
            detail='{"code":"23514","message":"invalid input"}',
            dev_context={
                "error_type": "APIError",
                "error_message": '{"code":"23514","message":"invalid input"}',
                "traceback": "Traceback (most recent call last):\n  File fake.py",
            },
        )

        result = save_job({"status": "Active", "notes": "x"}, row_id="job-2")
        self.assertFalse(result.ok)
        detail = str(result.detail or "")
        self.assertIn("Job ID: job-2", detail)
        self.assertIn("Payload keys:", detail)
        self.assertIn("Error type: APIError", detail)
        self.assertIn("invalid input", detail)
        self.assertIn("Traceback:", detail)


if __name__ == "__main__":
    unittest.main()
