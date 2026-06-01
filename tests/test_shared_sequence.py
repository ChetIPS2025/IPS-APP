"""Unit tests for shared quote/job numbering (QYY### / JYYNNN)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.shared_sequence import (
    estimate_quote_to_job_number,
    format_job_number,
    format_quote_number,
    job_number_to_quote_number,
    parse_stored_sequence_value,
    quote_number_to_job_number,
)


class TestSharedSequenceFormatting(unittest.TestCase):
    def test_format_quote_and_job_share_sequence_slot(self) -> None:
        self.assertEqual(format_quote_number(208), "Q26208")
        self.assertEqual(format_job_number(208), "J26208")

    def test_format_sequence_padding(self) -> None:
        self.assertEqual(format_quote_number(1), "Q26001")
        self.assertEqual(format_job_number(999), "J26999")

    def test_format_rejects_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            format_quote_number(1000)

    def test_quote_to_job_preserves_numeric_tail(self) -> None:
        self.assertEqual(quote_number_to_job_number("Q26208"), "J26208")
        self.assertEqual(estimate_quote_to_job_number("Q26208"), "J26208")
        self.assertEqual(job_number_to_quote_number("J26208"), "Q26208")

    def test_quote_to_job_empty(self) -> None:
        self.assertEqual(quote_number_to_job_number(""), "")

    def test_parse_current_format(self) -> None:
        self.assertEqual(parse_stored_sequence_value("Q26208"), 208)
        self.assertEqual(parse_stored_sequence_value("J26209"), 209)

    def test_parse_legacy_job_prefix(self) -> None:
        self.assertEqual(parse_stored_sequence_value("JOB-42"), 42)


class TestSharedSequenceAllocation(unittest.TestCase):
    @patch("app.db.get_admin_client")
    def test_prefers_yearly_rpc(self, mock_client_factory) -> None:
        from app.services.shared_sequence import get_next_sequence_number

        mock_client = mock_client_factory.return_value
        mock_client.rpc.return_value.execute.return_value.data = 210

        self.assertEqual(get_next_sequence_number(), 210)
        mock_client.rpc.assert_called_once_with("ips_next_yearly_seq", {})


if __name__ == "__main__":
    unittest.main()
