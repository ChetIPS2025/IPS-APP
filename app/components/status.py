"""Status pill rendering."""

from __future__ import annotations

import html

_STATUS_CLASS = {
    "active": "ips-status-active",
    "approved": "ips-status-active",
    "awarded": "ips-status-active",
    "in stock": "ips-status-active",
    "open": "ips-status-sent",
    "sent": "ips-status-sent",
    "in progress": "ips-status-sent",
    "pending": "ips-status-pending",
    "draft": "ips-status-draft",
    "low stock": "ips-status-pending",
    "expiring soon": "ips-status-pending",
    "expired": "ips-status-danger",
    "rejected": "ips-status-danger",
    "cancelled": "ips-status-danger",
    "inactive": "ips-status-danger",
    "in service": "ips-status-active",
    "out of service": "ips-status-danger",
    "scheduled": "ips-status-sent",
    "completed": "ips-status-active",
    "on hold": "ips-status-pending",
}


def status_pill_html(label: str) -> str:
    key = str(label or "").strip().lower()
    css = _STATUS_CLASS.get(key, "ips-status-draft")
    return (
        f'<span class="ips-status-pill {css}">{html.escape(str(label or "—"))}</span>'
    )


def render_status_pill(label: str) -> None:
    import streamlit as st

    st.markdown(status_pill_html(label), unsafe_allow_html=True)
