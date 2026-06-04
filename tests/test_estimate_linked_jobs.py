"""Tests for estimate-linked job workflow helpers."""

from __future__ import annotations

import unittest

from app.services.job_from_estimate import (
    _estimate_pending_job_is_orphan,
    estimate_quote_to_job_number,
)


class TestEstimateLinkedJobs(unittest.TestCase):
    def test_quote_to_job_number(self) -> None:
        self.assertEqual(estimate_quote_to_job_number("Q26070"), "J26070")
        self.assertEqual(estimate_quote_to_job_number("Q26071"), "J26071")

    def test_orphan_estimate_pending_without_estimate_id(self) -> None:
        self.assertTrue(
            _estimate_pending_job_is_orphan(
                {"id": "j1", "status": "Estimate Pending", "estimate_id": ""}
            )
        )

if __name__ == "__main__":
    unittest.main()
