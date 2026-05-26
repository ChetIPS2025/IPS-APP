"""
Timekeeping module — weekly summaries and grid persistence.

Schema assumptions: ``employee_timekeeping_weeks``, ``employee_timekeeping_days``.
"""

from __future__ import annotations

from datetime import date

from app.services.phase2_modules_service import (
    approve_timekeeping_week,
    list_timekeeping_days,
    list_timekeeping_summaries,
    normalize_timekeeping_summary,
    reject_timekeeping_week,
    save_timekeeping_day,
    save_timekeeping_week,
    submit_timekeeping_week,
)

__all__ = [
    "approve_timekeeping_week",
    "list_timekeeping_days",
    "list_timekeeping_summaries",
    "normalize_timekeeping_summary",
    "reject_timekeeping_week",
    "save_timekeeping_day",
    "save_timekeeping_week",
    "submit_timekeeping_week",
]
