"""Backward compatibility: :func:`render_pm_matrix` lives in :mod:`pages.pm_matrix_entry`."""

try:
    from pages.pm_matrix_entry import render_pm_matrix
except ImportError:
    from app.pages.pm_matrix_entry import render_pm_matrix  # type: ignore

__all__ = ["render_pm_matrix"]
