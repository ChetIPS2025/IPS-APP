"""Users module — compatibility wrapper for unified people management.

Users and Employees share one implementation in ``app.pages.employees``.
This module must remain a thin re-export only (no queries, widgets, or UI).
"""

from __future__ import annotations

from app.pages.employees import render

__all__ = ["render"]
