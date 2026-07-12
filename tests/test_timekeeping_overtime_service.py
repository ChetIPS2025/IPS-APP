"""Tests for automatic timekeeping overtime classification."""

from __future__ import annotations

import unittest
from datetime import date

from app.services.timekeeping_overtime_service import (
    new_allocation_line_defaults,
    peek_line_time_type,
    recalculate_week_allocations,
    summarize_week_hours,
    time_type_calculation_reason,
)
from app.utils.dates import week_dates


def _line(*, iso: str, hours: float, job: str = "100 — Job A") -> dict:
    return {
        "line_id": "",
        "job": job,
        "hour_type": "ST",
        "hours": hours,
        "notes": "",
        "status": "Draft",
        "overtime_override": False,
    }


class TestTimekeepingOvertimeService(unittest.TestCase):
    def test_example_week_classifies_friday_saturday_sunday_as_ot(self) -> None:
        week_start = date(2026, 6, 8)  # Monday
        by_date = {
            "2026-06-08": [_line(iso="2026-06-08", hours=10)],
            "2026-06-09": [_line(iso="2026-06-09", hours=10)],
            "2026-06-10": [_line(iso="2026-06-10", hours=10)],
            "2026-06-11": [_line(iso="2026-06-11", hours=10)],
            "2026-06-12": [_line(iso="2026-06-12", hours=6)],
            "2026-06-13": [_line(iso="2026-06-13", hours=8)],
            "2026-06-14": [_line(iso="2026-06-14", hours=4)],
        }
        out = recalculate_week_allocations(
            by_date,
            week_start,
            week_dates_fn=week_dates,
        )
        self.assertEqual(out["2026-06-08"][0]["final_time_type"], "ST")
        self.assertEqual(out["2026-06-12"][0]["final_time_type"], "OT")
        self.assertEqual(out["2026-06-13"][0]["final_time_type"], "OT")
        self.assertEqual(out["2026-06-14"][0]["final_time_type"], "OT")
        totals = summarize_week_hours(out)
        self.assertEqual(totals["st_total"], 40.0)
        self.assertEqual(totals["ot_total"], 18.0)
        self.assertEqual(totals["total_hours"], 58.0)

    def test_weekend_defaults_to_ot_without_consuming_weekday_bucket(self) -> None:
        week_start = date(2026, 6, 8)
        by_date = {
            "2026-06-13": [_line(iso="2026-06-13", hours=8)],
            "2026-06-08": [_line(iso="2026-06-08", hours=10)],
        }
        out = recalculate_week_allocations(
            by_date,
            week_start,
            week_dates_fn=week_dates,
        )
        self.assertEqual(out["2026-06-08"][0]["final_time_type"], "ST")
        self.assertEqual(out["2026-06-13"][0]["final_time_type"], "OT")

    def test_admin_override_is_preserved(self) -> None:
        week_start = date(2026, 6, 8)
        line = _line(iso="2026-06-13", hours=8)
        line["overtime_override"] = True
        line["final_time_type"] = "ST"
        line["hour_type"] = "ST"
        by_date = {"2026-06-13": [line]}
        out = recalculate_week_allocations(
            by_date,
            week_start,
            week_dates_fn=week_dates,
        )
        self.assertEqual(out["2026-06-13"][0]["calculated_time_type"], "OT")
        self.assertEqual(out["2026-06-13"][0]["final_time_type"], "ST")
        self.assertTrue(out["2026-06-13"][0]["overtime_override"])

    def test_peek_line_time_type_after_forty_hours(self) -> None:
        monday = date(2026, 6, 8)
        self.assertEqual(
            peek_line_time_type(work_date=monday, hours=6, weekday_st_used=40.0),
            "OT",
        )

    def test_new_allocation_line_defaults_to_auto(self) -> None:
        line = new_allocation_line_defaults()
        self.assertEqual(line["selected_time_type"], "AUTO")
        self.assertEqual(line["hour_type"], "AUTO")

    def test_time_type_calculation_reason_weekend_and_over_forty(self) -> None:
        saturday = date(2026, 6, 13)
        monday = date(2026, 6, 8)
        self.assertEqual(
            time_type_calculation_reason(work_date=saturday, calculated="OT"),
            "Weekend rule",
        )
        self.assertEqual(
            time_type_calculation_reason(work_date=monday, calculated="OT"),
            "Over 40",
        )
        self.assertEqual(
            time_type_calculation_reason(work_date=monday, calculated="ST"),
            "",
        )


if __name__ == "__main__":
    unittest.main()
