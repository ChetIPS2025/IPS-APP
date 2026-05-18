"""
Compatibility shim — all logic is in app/pages/jobs/.

Re-exports the public API so existing imports continue to work unchanged:

    from pages import job_database
    job_database.render()          # called by main.py
"""
from __future__ import annotations

try:
    from app.pages.jobs.page import render  # noqa: F401
    from app.pages.jobs.constants import (  # noqa: F401
        HIDDEN_COLUMNS,
        JOB_STATUS_COLORS as _JOB_STATUS_COLORS,
        JOB_STATUSES,
    )
except ImportError:
    from pages.jobs.page import render  # type: ignore  # noqa: F401
    from pages.jobs.constants import (  # type: ignore  # noqa: F401
        HIDDEN_COLUMNS,
        JOB_STATUS_COLORS as _JOB_STATUS_COLORS,
        JOB_STATUSES,
    )

__all__ = ["render", "JOB_STATUSES", "HIDDEN_COLUMNS"]
