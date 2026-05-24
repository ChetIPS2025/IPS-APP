"""Status pill rendering."""

from __future__ import annotations

import html

_STATUS_CLASS = {
    "active": "ips-status-success",
    "approved": "ips-status-success",
    "awarded": "ips-status-success",
    "in stock": "ips-status-success",
    "completed": "ips-status-success",
    "complete": "ips-status-success",
    "checked in": "ips-status-success",
    "inspection passed": "ips-status-success",
    "available": "ips-status-success",
    "good": "ips-status-success",
    "present": "ips-status-success",
    "open": "ips-status-primary",
    "sent": "ips-status-primary",
    "in progress": "ips-status-primary",
    "scheduled": "ips-status-primary",
    "pending": "ips-status-warning",
    "pending approval": "ips-status-warning",
    "expiring soon": "ips-status-warning",
    "low stock": "ips-status-warning",
    "missing documents": "ips-status-warning",
    "needs audit": "ips-status-warning",
    "warning": "ips-status-warning",
    "due soon": "ips-status-warning",
    "estimate pending": "ips-status-warning",
    "out for repair": "ips-status-attention",
    "needs attention": "ips-status-attention",
    "restricted": "ips-status-attention",
    "damaged": "ips-status-attention",
    "draft": "ips-status-neutral",
    "inactive": "ips-status-neutral",
    "archived": "ips-status-neutral",
    "retired": "ips-status-neutral",
    "closed": "ips-status-neutral",
    "expired": "ips-status-danger",
    "rejected": "ips-status-danger",
    "cancelled": "ips-status-danger",
    "canceled": "ips-status-danger",
    "missing": "ips-status-danger",
    "out of stock": "ips-status-attention",
    "out of service": "ips-status-danger",
    "in service": "ips-status-success",
    "on hold": "ips-status-warning",
}


def status_pill_html(label: str) -> str:
    key = str(label or "").strip().lower()
    css = _STATUS_CLASS.get(key, "ips-status-neutral")
    return (
        f'<span class="ips-status-pill {css}">{html.escape(str(label or "—"))}</span>'
    )


def render_status_pill(label: str) -> None:
    import streamlit as st

    st.markdown(status_pill_html(label), unsafe_allow_html=True)
