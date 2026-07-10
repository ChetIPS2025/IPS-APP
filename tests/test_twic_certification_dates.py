"""Tests for TWIC certification date auto-calculation."""

from __future__ import annotations

import unittest
from datetime import date

from app.services.certification_helpers import (
    is_twic_certification_type,
    normalize_certification_ui_dates,
    subtract_years,
    twic_issue_date_from_expiration,
)


class TestTwicCertificationDates(unittest.TestCase):
    def test_is_twic_certification_type(self) -> None:
        self.assertTrue(is_twic_certification_type("TWIC"))
        self.assertTrue(is_twic_certification_type(" twic "))
        self.assertFalse(is_twic_certification_type("OSHA 10"))

    def test_twic_issue_date_from_expiration_example(self) -> None:
        issue = twic_issue_date_from_expiration(date(2030, 9, 24))
        self.assertEqual(issue, date(2025, 9, 24))

    def test_twic_issue_date_recalculates_when_expiration_changes(self) -> None:
        first = twic_issue_date_from_expiration("2028-01-14")
        second = twic_issue_date_from_expiration("2030-01-14")
        self.assertEqual(first, date(2023, 1, 14))
        self.assertEqual(second, date(2025, 1, 14))

    def test_subtract_years_handles_leap_day(self) -> None:
        self.assertEqual(subtract_years(date(2028, 2, 29), 5), date(2023, 2, 28))

    def test_normalize_twic_overwrites_issue_date(self) -> None:
        ui = {
            "cert_type": "TWIC",
            "issue_date": date(2020, 1, 1),
            "expiration_date": date(2030, 9, 24),
        }
        normalized = normalize_certification_ui_dates(ui)
        self.assertEqual(normalized["issue_date"], date(2025, 9, 24))
        self.assertEqual(normalized["expiration_date"], date(2030, 9, 24))

    def test_normalize_non_twic_leaves_issue_date(self) -> None:
        ui = {
            "cert_type": "OSHA 30",
            "issue_date": date(2024, 3, 1),
            "expiration_date": date(2027, 3, 1),
        }
        normalized = normalize_certification_ui_dates(ui)
        self.assertEqual(normalized["issue_date"], date(2024, 3, 1))


if __name__ == "__main__":
    unittest.main()
