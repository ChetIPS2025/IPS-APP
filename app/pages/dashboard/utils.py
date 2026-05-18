"""Dashboard helpers: normalization, display frames, and shared constants."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

try:
    from app.services.job_service import job_number_display
except ImportError:
    from services.job_service import job_number_display  # type: ignore

# Session state keys (standardized)
STATE_DATE_START = "dashboard_date_start"
STATE_DATE_END = "dashboard_date_end"
STATE_FILTER_COMPANY = "dashboard_filter_company"
STATE_FILTER_JOB_STATUS = "dashboard_filter_job_status"
STATE_SELECTED_METRIC = "dashboard_selected_metric"
STATE_VIEW_MODE = "dashboard_view_mode"

_DASH_OUT_OVERDUE_DAYS = 7
_KIT_REPL_WINDOW_DAYS = 90
_KIT_REPL_HOT_THRESHOLD = 3

_AWARDED_STATUS_TOKENS = frozenset({"awarded", "won", "active"})
_BIDDING_STATUS_TOKENS = frozenset(
    {
        "bidding",
        "estimating",
        "proposal",
        "quoted",
        "draft",
        "submitted",
        "approved",
        "scheduled",
        "in progress",
        "on hold",
    }
)

_TERMINAL_JOB_STATUSES = frozenset(
    {"closed", "complete", "completed", "cancelled", "canceled"}
)
_TERMINAL_TASK_STATUSES = frozenset(
    {"done", "complete", "completed", "cancelled", "canceled"}
)
_DRAFT_ESTIMATE_STATUSES = frozenset({"draft", "open", "pending", ""})


def norm_status(v: Any) -> str:
    return " ".join(str(v or "").strip().split()).casefold()


def job_status_bucket(status_value: Any) -> str | None:
    s = norm_status(status_value)
    if not s:
        return None
    if s in _AWARDED_STATUS_TOKENS or any(tok in s for tok in _AWARDED_STATUS_TOKENS):
        return "awarded"
    if s in _BIDDING_STATUS_TOKENS or any(tok in s for tok in _BIDDING_STATUS_TOKENS):
        return "bidding"
    return None


def row_ts(row: dict) -> str:
    for k in ("updated_at", "modified_at", "created_at"):
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def recent_rows(rows: list[dict], *, limit: int = 12) -> list[dict]:
    if not rows:
        return []
    return sorted(rows, key=row_ts, reverse=True)[:limit]


def jobs_display_df(rows: list[dict]) -> pd.DataFrame:
    out: list[dict] = []
    for j in rows:
        if not isinstance(j, dict):
            continue
        jn = job_number_display(j.get("job_number"))
        out.append(
            {
                "Job #": jn or "—",
                "Name": str(j.get("job_name") or "").strip() or "—",
                "Status": str(j.get("status") or "").strip() or "—",
            }
        )
    return pd.DataFrame(out)


def estimates_display_df(rows: list[dict]) -> pd.DataFrame:
    out: list[dict] = []
    for e in rows:
        if not isinstance(e, dict):
            continue
        ts = row_ts(e)
        ts_disp = ts[:19].replace("T", " ") if ts else "—"
        try:
            if "T" in ts and len(ts) >= 10:
                ts_disp = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        except Exception:
            ts_disp = ts[:16] if ts else "—"
        out.append(
            {
                "Quote": str(e.get("quote_number") or "").strip() or "—",
                "Status": str(e.get("status") or "").strip() or "—",
                "Updated": ts_disp,
            }
        )
    return pd.DataFrame(out)


def dash_kf(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        s = str(v).strip()
        if not s:
            return default
        return float(s)
    except Exception:
        return default


def parse_co_ts(v: Any) -> datetime | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def days_out_value(last_co: Any) -> float | None:
    dt = parse_co_ts(last_co)
    if not dt:
        return None
    now = datetime.now(timezone.utc)
    return max(0.0, (now - dt).total_seconds() / 86400.0)


def asset_is_out(row: dict) -> bool:
    stt = str((row or {}).get("status") or "").strip()
    holder = str((row or {}).get("current_holder_employee_id") or "").strip()
    return stt == "Checked Out" or bool(holder)


def kit_line_short_qty(it: dict) -> float:
    exp = dash_kf((it or {}).get("quantity"))
    qoh = (it or {}).get("quantity_on_hand")
    if qoh is not None and str(qoh).strip() != "":
        return max(0.0, exp - dash_kf(qoh))
    return max(0.0, dash_kf((it or {}).get("missing_count")))


def is_open_job(job: dict) -> bool:
    return norm_status((job or {}).get("status")) not in _TERMINAL_JOB_STATUSES


def is_pending_estimate(est: dict) -> bool:
    return not str((est or {}).get("job_id") or "").strip()


def inject_dashboard_layout_css() -> None:
    """Compact grid and KPI styling for field tablets."""
    key = "_dashboard_layout_css_v1"
    import streamlit as st

    if st.session_state.get(key):
        return
    st.session_state[key] = True
    st.markdown(
        """
        <style>
        section[data-testid="stMain"]:has(.ips-dashboard-page) .ips-dash-grid [data-testid="column"] {
          min-width: 0 !important;
        }
        section[data-testid="stMain"]:has(.ips-dashboard-page) [data-testid="stMetric"] {
          background: rgba(248, 250, 252, 0.92);
          border: 1px solid rgba(15, 23, 42, 0.06);
          border-radius: 8px;
          padding: 0.35rem 0.5rem 0.4rem !important;
        }
        section[data-testid="stMain"]:has(.ips-dashboard-page) [data-testid="stMetric"] label {
          font-size: 0.72rem !important;
        }
        section[data-testid="stMain"]:has(.ips-dashboard-page) [data-testid="stMetric"] [data-testid="stMetricValue"] {
          font-size: 1.15rem !important;
        }
        @media (max-width: 900px) {
          section[data-testid="stMain"]:has(.ips-dashboard-page) [data-testid="stMetric"] label {
            font-size: 0.68rem !important;
          }
          section[data-testid="stMain"]:has(.ips-dashboard-page) .ips-dash-grid [data-testid="column"] {
            flex: 1 1 45% !important;
            min-width: 8rem !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
