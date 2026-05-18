"""Pure utility functions for the Assets module.

No database calls, no Streamlit calls — safe to import anywhere.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

# Canonical asset type list (superset of asset_constants.ASSET_TYPES).
ASSET_TYPES: list[str] = [
    "Truck",
    "Trailer",
    "Welder",
    "Lift",
    "Forklift",
    "Generator",
    "Compressor",
    "Tool",
    "Machine",
    "Other",
]

# Re-export ASSET_STATUSES from the canonical source so other modules only
# need to import from here.
try:
    from app.services.asset_constants import ASSET_STATUSES
except ImportError:
    from services.asset_constants import ASSET_STATUSES  # type: ignore


def clean_asset_code(text: str) -> str:
    """Uppercase, strip, replace non-alphanumeric runs with hyphens."""
    text = str(text).strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text)
    return text.strip("-")


def next_asset_id(rows: list[dict]) -> str:
    """Return the next sequential AST-NNN id not yet used in *rows*."""
    nums: list[int] = []
    for r in rows:
        value = str(r.get("asset_id", "")).strip().upper()
        if value.startswith("AST-"):
            try:
                nums.append(int(value[4:]))
            except ValueError:
                pass
    return f"AST-{(max(nums) + 1 if nums else 1):03d}"


def make_unique_asset_name(base_value: str, rows: list[dict]) -> str:
    """Append a numeric suffix if *base_value* already exists in *rows*."""
    existing = {str(r.get("asset_name", "")).strip().upper() for r in rows}
    if base_value.upper() not in existing:
        return base_value
    i = 2
    while True:
        candidate = f"{base_value}_{i}"
        if candidate.upper() not in existing:
            return candidate
        i += 1


def safe_date_value(value: Any) -> str | None:
    """Return a non-empty stripped string or None (suitable for date DB columns)."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def disp(val: Any) -> str:
    """Human-readable display value; returns '—' for null/empty/NaN."""
    if val is None or val is pd.NA:
        return "—"
    try:
        if isinstance(val, (float, int)) and pd.isna(val):
            return "—"
    except (TypeError, ValueError):
        pass
    s = str(val).strip()
    return "—" if not s or s.lower() == "nan" else s


def is_truthy(val: Any) -> bool:
    """Tolerant boolean parse for DB flag columns (True / 1 / 'true' / 'yes')."""
    if val is None or val is pd.NA:
        return False
    try:
        if isinstance(val, (float, int)) and pd.isna(val):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "yes", "t")


# Convenience aliases used by components that import from this module.
is_rental_row = is_truthy
is_checkout_tool_flag = is_truthy


# ---------------------------------------------------------------------------
# Status → badge colour mapping
# ---------------------------------------------------------------------------

_STATUS_COLOURS: dict[str, str] = {
    "Available": "#22c55e",      # green
    "Checked Out": "#f97316",    # orange
    "Assigned": "#3b82f6",       # blue
    "In Shop": "#a855f7",        # purple
    "Maintenance": "#eab308",    # yellow
    "Lost": "#ef4444",           # red
    "Out for Repair": "#f97316", # orange
    "Retired": "#6b7280",        # grey
    "Inactive": "#6b7280",
}


def status_colour(status: str) -> str:
    """Return a CSS hex colour for the given asset status string."""
    return _STATUS_COLOURS.get(str(status or "").strip(), "#94a3b8")
