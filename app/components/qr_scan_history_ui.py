"""QR scan history table — Dashboard card and Inventory QR Scan History tab."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.components.tables import data_table_html
except ImportError:
    from components.tables import data_table_html  # type: ignore

try:
    from app.utils.formatting import fmt_datetime
except ImportError:
    from utils.formatting import fmt_datetime  # type: ignore

_FULL_COLS = (
    ("summary", "Scan"),
    ("scanned_at", "Scanned At"),
    ("scanned_by", "Scanned By"),
    ("device_label", "Device"),
    ("qr_value", "QR Code / Value"),
    ("item_name", "Item"),
    ("item_type", "Type"),
    ("result", "Result"),
    ("job_shop", "Job / Shop"),
    ("device_source", "Source"),
    ("action_taken", "Action Taken"),
)

_COMPACT_COLS = (
    ("summary", "Recent Scan"),
    ("result", "Result"),
    ("action_taken", "Action"),
)

_FULL_COL_FR = ["2.2fr", "1fr", "0.95fr", "0.85fr", "1fr", "1.1fr", "0.7fr", "0.7fr", "1fr", "0.9fr", "0.95fr"]
_COMPACT_COL_FR = ["2.4fr", "0.75fr", "0.95fr"]


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


def _qr_cell_renderer(field: str, row: dict[str, Any]) -> str:
    if field == "result":
        return _result_badge(str(row.get("result") or "—"))
    if field == "scanned_at":
        return html.escape(fmt_datetime(row.get("scanned_at"), compact=True))
    if field == "summary":
        summary = str(row.get("summary") or "").strip()
        if summary:
            return f'<span class="ips-qr-scan-summary">{html.escape(summary)}</span>'
    if field == "device_label":
        device = str(row.get("device_label") or "").strip()
        if device:
            return html.escape(device)
    return html.escape(str(row.get(field) or "—"))


def qr_scan_history_table_html(
    rows: list[dict[str, Any]],
    *,
    compact: bool = False,
    empty_message: str = "No QR scans recorded yet.",
) -> str:
    """Return QR scan log rows as HTML for embedding inside panel cards."""
    specs = _COMPACT_COLS if compact else _FULL_COLS
    table_class = (
        "ips-data-table-wrap ips-data-table-stable ips-dash-list-table ips-qr-scan-dash-table"
        if compact
        else "ips-data-table-wrap ips-data-table-stable ips-data-table-nested ips-qr-scan-full-table"
    )
    return data_table_html(
        rows,
        list(specs),
        col_fr=_COMPACT_COL_FR if compact else _FULL_COL_FR,
        cell_renderer=_qr_cell_renderer,
        table_class=table_class,
        empty_message=empty_message,
        row_id_key="scanned_at",
    )


def render_qr_scan_history_table(
    rows: list[dict[str, Any]],
    *,
    compact: bool = False,
    empty_message: str = "No QR scans recorded yet.",
) -> None:
    """Render QR scan log rows as a styled grid table."""
    if not rows:
        st.caption(empty_message)
        return
    st.markdown(
        qr_scan_history_table_html(rows, compact=compact, empty_message=empty_message),
        unsafe_allow_html=True,
    )


def inject_qr_scan_history_css() -> None:
    """Inject result-badge styles (grid layout comes from shared data-table CSS)."""
    if st.session_state.get("_ips_qr_scan_history_css"):
        return
    st.session_state["_ips_qr_scan_history_css"] = True
    st.markdown(
        """
        <style>
        .ips-qr-scan-result {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
        }
        .ips-qr-scan-result-ok { background: #dcfce7; color: #166534; }
        .ips-qr-scan-result-open { background: #dbeafe; color: #1d4ed8; }
        .ips-qr-scan-result-warn { background: #fef3c7; color: #92400e; }
        .ips-qr-scan-result-neutral { background: #f1f5f9; color: #475569; }
        .ips-qr-scan-dash-table .ips-data-table-header,
        .ips-qr-scan-dash-table .ips-data-row {
            min-width: 36rem;
            cursor: default;
        }
        .ips-qr-scan-dash-table .ips-data-row:hover { background: transparent; }
        .ips-qr-scan-full-table .ips-data-table-header,
        .ips-qr-scan-full-table .ips-data-row {
            min-width: 56rem;
            cursor: default;
        }
        .ips-qr-scan-full-table .ips-data-row:hover { background: transparent; }
        .ips-qr-scan-summary {
            font-weight: 700;
            color: #0f172a;
            line-height: 1.35;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


__all__ = [
    "inject_qr_scan_history_css",
    "qr_scan_history_table_html",
    "render_qr_scan_history_table",
]
