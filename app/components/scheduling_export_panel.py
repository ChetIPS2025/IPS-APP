"""Explicit weekly schedule CSV export with cached preparation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import date
from typing import Any

import streamlit as st

from app.pages._core.page_data_cache import page_data_cache_get
from app.perf_debug import perf_span
from app.services.scheduling_service import build_weekly_schedule_export_rows, scheduling_data_version

_EXPORT_READY_KEY = "_ips_scheduling_export_ready"
_EXPORT_SCHEMA_VERSION = "1"


def _export_cache_key(
    *,
    week_start: date,
    filters: dict[str, str],
) -> str:
    filt_token = hashlib.sha256(json.dumps(filters or {}, sort_keys=True).encode()).hexdigest()[:16]
    return (
        f"scheduling_export_csv:{scheduling_data_version()}:{_EXPORT_SCHEMA_VERSION}:"
        f"{week_start.isoformat()}:{filt_token}"
    )


def clear_prepared_export() -> None:
    st.session_state.pop(_EXPORT_READY_KEY, None)


def render_scheduling_export_panel(
    *,
    events: list[dict[str, Any]],
    week_start: date,
    filters: dict[str, str],
    jobs_by_id: dict[str, dict[str, Any]],
    employees_by_id: dict[str, dict[str, Any]],
    employee_rows_by_event: dict[str, list[dict[str, Any]]],
    can_export: bool,
) -> None:
    if not can_export:
        return

    with perf_span("scheduling.export"):
        exp_col1, exp_col2 = st.columns([1, 3])
        with exp_col1:
            if st.button("Export Weekly Schedule", key="sched_export_week", use_container_width=True):
                cache_key = _export_cache_key(week_start=week_start, filters=filters)

                def _build_csv() -> str:
                    rows = build_weekly_schedule_export_rows(
                        events,
                        jobs_by_id=jobs_by_id,
                        employees_by_id=employees_by_id,
                        employee_rows_by_event=employee_rows_by_event,
                    )
                    buf = io.StringIO()
                    if rows:
                        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
                        writer.writeheader()
                        writer.writerows(rows)
                    return buf.getvalue()

                csv_text = page_data_cache_get(cache_key, _build_csv)
                st.session_state[_EXPORT_READY_KEY] = {
                    "csv": csv_text,
                    "file_name": f"schedule_{week_start.isoformat()}.csv",
                }

        ready = st.session_state.get(_EXPORT_READY_KEY) or {}
        if isinstance(ready, dict) and ready.get("csv"):
            with exp_col2:
                st.download_button(
                    "Download CSV",
                    data=str(ready.get("csv") or "").encode("utf-8"),
                    file_name=str(ready.get("file_name") or "schedule.csv"),
                    mime="text/csv",
                    key="sched_export_csv_dl",
                )
