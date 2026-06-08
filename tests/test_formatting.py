"""Unit tests for app.utils.formatting display helpers."""

from __future__ import annotations

import unittest
from datetime import date, datetime

from app.utils.formatting import (
    fmt_currency,
    fmt_date,
    fmt_datetime,
    fmt_hours,
    fmt_money,
    fmt_percent,
    fmt_qty,
)


class TestFormatting(unittest.TestCase):
    def test_fmt_date_iso_string(self) -> None:
        self.assertEqual(fmt_date("2026-05-30"), "May 30, 2026")

    def test_fmt_date_datetime_z_suffix(self) -> None:
        self.assertEqual(fmt_date("2026-05-30T14:45:00Z"), "May 30, 2026")

    def test_fmt_date_empty(self) -> None:
        self.assertEqual(fmt_date(None), "—")
        self.assertEqual(fmt_date(""), "—")

    def test_fmt_datetime_long(self) -> None:
        result = fmt_datetime("2026-05-30T14:45:00Z")
        self.assertIn("May 30, 2026", result)
        self.assertIn("PM", result)

    def test_fmt_datetime_compact(self) -> None:
        self.assertEqual(
            fmt_datetime("2026-05-30T14:45:00Z", compact=True),
            "2026-05-30 14:45",
        )
        self.assertEqual(
            fmt_datetime("2026-05-30T14:45:07Z", compact=True, include_seconds=True),
            "2026-05-30 14:45:07",
        )

    def test_fmt_money_defaults(self) -> None:
        self.assertEqual(fmt_money(1234.5), "$1,234.50")
        self.assertEqual(fmt_money(None), "$0.00")
        self.assertEqual(fmt_currency(0), "$0.00")

    def test_fmt_money_empty_and_zero(self) -> None:
        self.assertEqual(fmt_money(0, empty="—", zero_as_empty=True), "—")
        self.assertEqual(fmt_money(0, empty="", zero_as_empty=True), "")

    def test_fmt_qty_with_unit(self) -> None:
        self.assertEqual(fmt_qty(12, "EA"), "12 EA")
        self.assertEqual(fmt_qty(1250.5, "FT"), "1250.5 FT")

    def test_fmt_percent(self) -> None:
        self.assertEqual(fmt_percent(12.5), "12.5%")
        self.assertEqual(fmt_percent(None), "—")

    def test_fmt_hours_empty_zero(self) -> None:
        self.assertEqual(fmt_hours(0, empty_zero=True), "")
        self.assertEqual(fmt_hours(8.5, empty_zero=True), "8.5")
        self.assertEqual(fmt_hours(8.0), "8.0")

    def test_fmt_date_date_object(self) -> None:
        self.assertEqual(fmt_date(date(2026, 5, 30)), "May 30, 2026")
        self.assertEqual(fmt_datetime(datetime(2026, 5, 30, 9, 15), compact=True), "2026-05-30 09:15")


if __name__ == "__main__":
    unittest.main()
