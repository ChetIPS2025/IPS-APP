"""Unit tests for shared quote/job numbering (QYY### / JYYNNN)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.shared_sequence import (
    ensure_quote_number_for_save,
    estimate_quote_to_job_number,
    format_job_number,
    format_quote_number,
    job_number_to_quote_number,
    max_sequence_for_year,
    next_available_quote_number,
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
        from app.services.shared_sequence import get_next_sequence_number_for_year

        mock_client = mock_client_factory.return_value
        mock_client.rpc.return_value.execute.return_value.data = 210

        self.assertEqual(get_next_sequence_number_for_year(2026), 210)
        mock_client.rpc.assert_called_with("ips_next_yearly_seq", {"p_year_yy": 26})


class TestGenerateQuoteJobNumber(unittest.TestCase):
    @patch("app.services.shared_sequence.get_next_sequence_number_for_year", return_value=209)
    def test_generate_quote_number(self, _mock_seq) -> None:
        from app.services.shared_sequence import generate_quote_job_number

        self.assertEqual(generate_quote_job_number("Q", 2026), "Q26209")
        self.assertEqual(generate_quote_job_number("J", 2026), "J26209")


class TestNextAvailableQuoteNumber(unittest.TestCase):
    def test_max_from_quotes_and_jobs(self) -> None:
        existing = ["Q26208", "J26208", "J26209"]
        self.assertEqual(max_sequence_for_year(2026, existing_values=existing), 209)

    @patch("app.services.shared_sequence._quote_number_in_use", return_value=False)
    def test_next_available_after_shared_max(self, _mock_in_use) -> None:
        existing = ["Q26208", "J26208", "J26209"]
        with patch(
            "app.services.shared_sequence.max_sequence_for_year",
            return_value=max_sequence_for_year(2026, existing_values=existing),
        ):
            self.assertEqual(next_available_quote_number(2026), "Q26210")

    @patch("app.services.shared_sequence._quote_number_in_use")
    def test_ensure_keeps_unused_prefill(self, mock_in_use) -> None:
        mock_in_use.return_value = False
        self.assertEqual(
            ensure_quote_number_for_save("Q26208", year=2026),
            "Q26208",
        )
        mock_in_use.assert_called_once_with("Q26208", exclude_estimate_id=None)

    @patch("app.services.shared_sequence.next_available_quote_number", return_value="Q26210")
    @patch("app.services.shared_sequence._quote_number_in_use", return_value=True)
    def test_ensure_replaces_taken_prefill(self, _mock_in_use, mock_next) -> None:
        self.assertEqual(ensure_quote_number_for_save("Q26209", year=2026), "Q26210")
        mock_next.assert_called_once_with(2026, exclude_estimate_id=None)


if __name__ == "__main__":
    unittest.main()
