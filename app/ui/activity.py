"""Activity / audit trail panels for detail views."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.ui.page_shell import inject_ips_dashboard_layout
except ImportError:
    from ui.page_shell import inject_ips_dashboard_layout  # type: ignore


def _fmt_ts(val: Any) -> str:
    s = str(val or "").strip()
    if not s:
        return "—"
    return s[:19].replace("T", " ")


def render_activity_panel(
    *,
    title: str = "Activity",
    created_at: Any = None,
    updated_at: Any = None,
    status: Any = None,
    created_by: Any = None,
    updated_by: Any = None,
    extra_lines: list[tuple[str, str]] | None = None,
) -> None:
    """Compact activity strip for job/estimate detail drawers."""
    inject_ips_dashboard_layout()
    lines: list[tuple[str, str]] = []
    if status is not None and str(status).strip():
        lines.append(("Status", str(status).strip()))
    if created_at is not None:
        lines.append(("Created", _fmt_ts(created_at)))
    if created_by is not None and str(created_by).strip():
        lines.append(("Created by", str(created_by).strip()))
    if updated_at is not None:
        lines.append(("Updated", _fmt_ts(updated_at)))
    if updated_by is not None and str(updated_by).strip():
        lines.append(("Updated by", str(updated_by).strip()))
    if extra_lines:
        lines.extend(extra_lines)
    if not lines:
        st.caption("No activity recorded.")
        return

    rows_html = "".join(
        f'<tr><td class="ips-act-k">{html.escape(k)}</td>'
        f'<td class="ips-act-v">{html.escape(v)}</td></tr>'
        for k, v in lines
    )
    st.markdown(
        f"""
        <style>
        p.ips-act-title {{
            font-size: 0.88rem; font-weight: 700; color: #111827;
            margin: 0 0 0.35rem 0;
        }}
        table.ips-act-table {{
            width: 100%; border-collapse: collapse; font-size: 0.8125rem;
        }}
        table.ips-act-table td {{
            padding: 0.2rem 0.35rem 0.2rem 0;
            vertical-align: top;
        }}
        td.ips-act-k {{
            color: #6b7280; font-weight: 600; width: 7.5rem; white-space: nowrap;
        }}
        td.ips-act-v {{ color: #1f2937; }}
        </style>
        <p class="ips-act-title">{html.escape(title)}</p>
        <table class="ips-act-table">{rows_html}</table>
        """,
        unsafe_allow_html=True,
    )
