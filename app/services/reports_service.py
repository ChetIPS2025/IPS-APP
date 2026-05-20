"""
Reports dashboard — aggregated reads (no direct UI queries).

Uses repository fetch helpers; individual report sections may query multiple tables.
"""

from __future__ import annotations

from typing import Any

try:
    from app.services.repository import fetch_rows
except ImportError:
    from services.repository import fetch_rows  # type: ignore


def fetch_report_table(table: str, *, limit: int = 500, order_by: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """Load rows for a report section with graceful error string."""
    return fetch_rows(table, limit=limit, order_by=order_by)
