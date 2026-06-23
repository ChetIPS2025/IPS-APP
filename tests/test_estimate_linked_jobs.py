"""Tests for estimate-linked job workflow helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.repository import ServiceResult
from app.services.estimate_job_workflow_service import award_job_and_sync_estimate
from app.services.job_from_estimate import (
    _estimate_pending_job_is_orphan,
    _job_has_stale_estimate_link,
    _job_matches_estimate_quote,
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

    def test_job_matches_estimate_quote(self) -> None:
        job = {"job_number": "J26070", "source_estimate_number": "Q26070"}
        self.assertTrue(_job_matches_estimate_quote(job, "Q26070"))

    @patch("app.services.job_from_estimate.fetch_by_match_admin")
    def test_stale_estimate_link_detected(self, fetch_mock) -> None:
        fetch_mock.return_value = [{"id": "est-old", "job_id": None}]
        self.assertTrue(
            _job_has_stale_estimate_link({"id": "job-a", "estimate_id": "est-old"})
        )
        fetch_mock.return_value = [{"id": "est-old", "job_id": "other-job"}]
        self.assertTrue(
            _job_has_stale_estimate_link({"id": "job-a", "estimate_id": "est-old"})
        )
        fetch_mock.return_value = [{"id": "est-old", "job_id": "job-a"}]
        self.assertFalse(
            _job_has_stale_estimate_link({"id": "job-a", "estimate_id": "est-old"})
        )

    @patch("app.services.estimate_job_workflow_service.sync_estimate_job_links_and_financials")
    @patch("app.services.estimate_job_workflow_service._fetch_job_row")
    def test_award_job_and_sync_estimate(
        self,
        fetch_job_mock,
        sync_mock,
    ) -> None:
        fetch_job_mock.return_value = {
            "id": "job-1",
            "job_number": "J26070",
            "status": "Estimate Pending",
        }
        sync_mock.return_value = ServiceResult(
            ok=True,
            data={
                "estimate_id": "est-1",
                "job_patch": {"awarded_amount": 10330.0, "estimate_id": "est-1"},
                "customer_price": 10330.0,
            },
        )

        result = award_job_and_sync_estimate("job-1", new_status="Active")

        self.assertTrue(result.ok)
        sync_mock.assert_called_once()
        call_kwargs = sync_mock.call_args.kwargs
        self.assertEqual(call_kwargs.get("job_id"), "job-1")
        self.assertFalse(call_kwargs.get("persist_job"))
        self.assertTrue(call_kwargs.get("skip_if_no_estimate"))


if __name__ == "__main__":
    unittest.main()
