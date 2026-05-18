"""Shared constants for the Jobs module."""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Job lifecycle statuses (used in form selects and filters)
# ---------------------------------------------------------------------------
JOB_STATUSES: list[str] = [
    "Draft",
    "Quoted",
    "Submitted",
    "Approved",
    "Awarded",
    "Scheduled",
    "In Progress",
    "On Hold",
    "Completed",
    "Closed",
]

# ---------------------------------------------------------------------------
# Status → accent colour (used for inline badges)
# ---------------------------------------------------------------------------
JOB_STATUS_COLORS: dict[str, str] = {
    "complete": "#16a34a",
    "completed": "#16a34a",
    "closed": "#16a34a",
    "in progress": "#f59e0b",
    "scheduled": "#f59e0b",
    "awarded": "#f59e0b",
    "blocked": "#dc2626",
    "on hold": "#dc2626",
    "not started": "#64748b",
    "draft": "#64748b",
    "electrical": "#7c3aed",
    "electrical / other trade": "#7c3aed",
    "duplicate": "#64748b",
    "waiting on customer": "#0891b2",
}

# ---------------------------------------------------------------------------
# DataFrame column visibility
# ---------------------------------------------------------------------------
HIDDEN_COLUMNS: frozenset[str] = frozenset(
    {
        "source_type",
        "project_manager",
        "supervisor",
        "start_date",
        "target_completion_date",
        "completed_date",
        "notes",
    }
)

# Kept on the DataFrame for filters / search / logic but not shown in the table.
COLUMNS_HIDDEN_FROM_TABLE: frozenset[str] = frozenset(
    {"customer_id", "estimate_label", "Source"}
) | HIDDEN_COLUMNS

# ---------------------------------------------------------------------------
# Session-state cache-busting keys (increment to force a fresh DB read)
# ---------------------------------------------------------------------------
STYLE_KEY_RESPONSIVE = "job_db_responsive_styles_injected_v14"
STYLE_KEY_DETAIL_VIEW = "job_db_detail_view_css_v1"

# ---------------------------------------------------------------------------
# Standardised session-state keys for Job Database routing
# ---------------------------------------------------------------------------
KEY_VIEW_MODE = "job_view_mode"      # "list" | "create" | "edit" | "view"
KEY_SELECTED_ID = "selected_job_id"  # str UUID or None
KEY_EDIT_ID = "job_edit_id"          # legacy alias kept for backwards-compat
KEY_JOB_MODE = "job_mode"            # legacy alias ("add" / "edit")
KEY_DATA_VERSION = "job_db_data_version"  # int; bump to bust caches
