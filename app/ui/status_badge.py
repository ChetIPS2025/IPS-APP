"""Shared IPS status badge component."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.status import status_pill_html as _legacy_pill_html
except ImportError:
    from components.status import status_pill_html as _legacy_pill_html  # type: ignore

_DISPLAY_LABELS: dict[str, str] = {
    "active": "Active",
    "inactive": "Inactive",
    "draft": "Draft",
    "submitted": "Submitted",
    "approved": "Approved",
    "completed": "Completed",
    "complete": "Completed",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
    "on hold": "On Hold",
    "expired": "Expired",
    "in stock": "In Stock",
    "out of stock": "Out of Stock",
    "missing": "Missing",
    "pending": "Pending",
    "pending approval": "Pending Approval",
}


def _display_label(status: str) -> str:
    raw = str(status or "").strip()
    if not raw:
        return "—"
    key = raw.lower()
    return _DISPLAY_LABELS.get(key, raw)


def status_badge_html(status: str) -> str:
    """Return HTML for a shared status badge (aliases legacy status pill)."""
    label = _display_label(status)
    legacy = _legacy_pill_html(label)
    return legacy.replace('class="ips-status-pill', 'class="ips-status-badge ips-status-pill', 1)


def render_status_badge(status: str) -> None:
    """Render a shared status badge."""
    st.markdown(status_badge_html(status), unsafe_allow_html=True)


__all__ = ["status_badge_html", "render_status_badge"]
