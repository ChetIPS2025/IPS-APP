"""Tests for customer PO helpers on jobs."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.job_po_service import (
    apply_po_fields_to_job_payload,
    job_po_editable,
    job_po_snapshot,
    po_fields_from_estimate,
)


class TestJobPoService(unittest.TestCase):
    def test_po_fields_from_estimate(self) -> None:
        est = {
            "po_number": "PO-123",
            "po_date": "2026-05-01",
            "po_amount": 15000.50,
        }
        fields = po_fields_from_estimate(est)
        self.assertEqual(fields["po_number"], "PO-123")
        self.assertEqual(fields["po_date"], "2026-05-01")
        self.assertEqual(fields["po_amount"], 15000.50)

    def test_apply_po_fields_overwrites_empty_job(self) -> None:
        job = {"id": "j1"}
        est = {"po_number": "PO-9", "po_date": "2026-01-15", "po_amount": 5000}
        patch = apply_po_fields_to_job_payload(job, est, overwrite=True)
        self.assertEqual(patch["po_number"], "PO-9")
        self.assertEqual(patch["po_date"], "2026-01-15")
        self.assertEqual(patch["po_amount"], 5000.0)

    def test_apply_po_fields_respects_existing_when_not_overwriting(self) -> None:
        job = {"po_number": "KEEP", "po_amount": 100}
        est = {"po_number": "NEW", "po_amount": 5000}
        patch = apply_po_fields_to_job_payload(job, est, overwrite=False)
        self.assertEqual(patch, {})

    @patch("app.services.job_po_service.linked_estimate_for_job")
    def test_job_po_snapshot_prefers_estimate_when_locked(self, link_mock) -> None:
        link_mock.return_value = {
            "id": "e1",
            "po_number": "EST-PO",
            "po_date": "2026-03-01",
            "po_amount": 9000,
        }
        with patch("app.services.job_po_service.job_po_locked_by_estimate", return_value=True):
            snap = job_po_snapshot({"id": "j1", "po_number": "OLD"})
        self.assertEqual(snap["po_number"], "EST-PO")
        self.assertTrue(snap["locked"])

    @patch("app.services.job_po_service.job_po_locked_by_estimate", return_value=True)
    def test_job_po_not_editable_when_locked(self, _lock_mock) -> None:
        self.assertFalse(job_po_editable({"id": "j1", "estimate_id": "e1"}))


if __name__ == "__main__":
    unittest.main()
