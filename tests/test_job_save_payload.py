"""Tests for job save payload normalization."""

from __future__ import annotations

import unittest
from datetime import date

from app.services.phase2_modules_service import _job_save_date, _job_save_text


class TestJobSavePayload(unittest.TestCase):
    def test_job_save_text_coerces_none_to_empty_string(self) -> None:
        self.assertEqual(_job_save_text(None), "")
        self.assertEqual(_job_save_text("Earl Lafont"), "Earl Lafont")

    def test_job_save_date_serializes_date_object(self) -> None:
        self.assertEqual(_job_save_date(date(2024, 6, 22)), "2024-06-22")
        self.assertIsNone(_job_save_date(None))
        self.assertIsNone(_job_save_date(""))


if __name__ == "__main__":
    unittest.main()
