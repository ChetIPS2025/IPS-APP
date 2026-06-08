"""QR scan history table — Dashboard card and Inventory QR Scan History tab."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.utils.formatting import fmt_datetime
except ImportError:
    from utils.formatting import fmt_datetime  # type: ignore

_FULL_COLS = (
    ("scanned_at", "Scanned At"),
    ("qr_value", "QR Code / Value"),
    ("item_name", "Item"),
    ("item_type", "Type"),
    ("result", "Result"),
    ("job_shop", "Job / Shop"),
    ("scanned_by", "Scanned By"),
    ("device_source", "Device / Source"),
    ("action_taken", "Action Taken"),
)

_COMPACT_COLS = (
    ("scanned_at", "Scanned At"),
    ("item_name", "Item"),
    ("item_type", "Type"),
    ("result", "Result"),
    ("action_taken", "Action Taken"),
)


def _format_cell(field: str, row: dict[str, Any]) -> str:
    if field == "scanned_at":
        return fmt_datetime(row.get("scanned_at"), compact=True)
    return str(row.get(field) or "—")


def _result_badge(result: str) -> str:
    val = str(result or "—")
    low = val.casefold()
    if low == "success":
        cls = "ips-qr-scan-result-ok"
    elif low == "opened":
        cls = "ips-qr-scan-result-open"
    elif low in {"failed", "unknown item"}:
        cls = "ips-qr-scan-result-warn"
    else:
        cls = "ips-qr-scan-result-neutral"
    return f'<span class="ips-qr-scan-result {cls}">{html.escape(val)}</span>'


def render_qr_scan_history_table(
    rows: list[dict[str, Any]],
    *,
    compact: bool = False,
    empty_message: str = "No QR scans recorded yet.",
) -> None:
    """Render QR scan log rows as a styled grid table."""
    specs = _COMPACT_COLS if compact else _FULL_COLS
    if not rows:
        st.caption(empty_message)
        return

    wrap_cls = "ips-qr-scan-table ips-qr-scan-compact" if compact else "ips-qr-scan-table"
    head_cells = "".join(f"<span>{html.escape(label)}</span>" for _, label in specs)
    head = f'<div class="ips-qr-scan-head">{head_cells}</div>'

    body = ""
    for row in rows:
        cells = []
        for field, _ in specs:
            if field == "result":
                cells.append(f"<span>{_result_badge(str(row.get('result') or '—'))}</span>")
            else:
                cells.append(f"<span>{html.escape(_format_cell(field, row))}</span>")
        body += f'<div class="ips-qr-scan-row">{"".join(cells)}</div>'

    st.markdown(f'<div class="{wrap_cls}">{head}{body}</div>', unsafe_allow_html=True)


def inject_qr_scan_history_css() -> None:
    if st.session_state.get("_ips_qr_scan_history_css"):
        return
    st.session_state["_ips_qr_scan_history_css"] = True
    st.markdown(
        """
        <style>
        .ips-qr-scan-table {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            overflow-x: auto;
            margin-top: 8px;
        }
        .ips-qr-scan-head,
        .ips-qr-scan-row {
            display: grid;
            grid-template-columns:
                1.05fr 1.15fr 1.2fr 0.75fr 0.7fr 1fr 0.95fr 1fr 1fr;
            gap: 8px;
            padding: 8px 10px;
            font-size: 12px;
            align-items: center;
            min-width: 920px;
        }
        .ips-qr-scan-compact .ips-qr-scan-head,
        .ips-qr-scan-compact .ips-qr-scan-row {
            grid-template-columns: 1fr 1.4fr 0.75fr 0.7fr 1.1fr;
            min-width: 520px;
        }
        .ips-qr-scan-head {
            background: #f8fafc;
            font-weight: 800;
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            border-bottom: 1px solid #e2e8f0;
        }
        .ips-qr-scan-row {
            border-bottom: 1px solid #eef2f7;
            color: #0f172a;
        }
        .ips-qr-scan-row:last-child { border-bottom: none; }
        .ips-qr-scan-result {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
        }
        .ips-qr-scan-result-ok { background: #dcfce7; color: #166534; }
        .ips-qr-scan-result-open { background: #dbeafe; color: #1d4ed8; }
        .ips-qr-scan-result-warn { background: #fef3c7; color: #92400e; }
        .ips-qr-scan-result-neutral { background: #f1f5f9; color: #475569; }
        </style>
        """,
        unsafe_allow_html=True,
    )


__all__ = ["inject_qr_scan_history_css", "render_qr_scan_history_table"]
