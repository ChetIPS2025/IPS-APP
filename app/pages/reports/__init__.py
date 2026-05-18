"""Reports module — modular dashboard for job, labor, inventory, asset, and financial reports."""
from __future__ import annotations

try:
    from app.pages.reports.page import render
except ImportError:
    from pages.reports.page import render  # type: ignore

__all__ = ["render"]
