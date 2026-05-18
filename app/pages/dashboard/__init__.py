"""Modular Dashboard package (replaces monolithic pages.dashboard)."""

from __future__ import annotations

from .calculations import (
    count_active_employees,
    count_awarded_jobs,
    count_bidding_jobs,
    count_open_jobs,
    count_pending_estimates,
)
from .page import render

__all__ = [
    "render",
    "count_awarded_jobs",
    "count_bidding_jobs",
    "count_active_employees",
    "count_open_jobs",
    "count_pending_estimates",
]
