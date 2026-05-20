"""
Timekeeping module — weekly summaries and grid persistence.

Schema assumptions: ``employee_timekeeping_weeks``, ``time_entries`` (optional).
"""

from __future__ import annotations

from datetime import date

from app.services.phase2_modules_service import (
    list_timekeeping_summaries,
    normalize_timekeeping_summary,
    save_timekeeping_day,
    save_timekeeping_week,
)

__all__ = [
    "list_timekeeping_summaries",
    "normalize_timekeeping_summary",
    "save_timekeeping_day",
    "save_timekeeping_week",
]
