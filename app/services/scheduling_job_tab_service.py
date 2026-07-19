"""Schedule tab helpers — assigned employees only."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.pages._core.page_data_cache import page_data_cache_get


def employees_for_job_schedule(job_id: str) -> dict[str, dict[str, Any]]:
    """Lightweight employee labels for employees assigned on this job's schedule."""
    jid = str(job_id or "").strip()
    if not jid:
        return {}

    def _build() -> dict[str, dict[str, Any]]:
        from app.services.repository import fetch_by_id
        from app.services.scheduling_service import list_job_schedule

        events = list_job_schedule(jid)
        employee_ids: set[str] = set()
        for event in events or []:
            eid = str(event.get("employee_id") or event.get("assigned_employee_id") or "").strip()
            if eid:
                employee_ids.add(eid)
        if not employee_ids:
            return {}
        out: dict[str, dict[str, Any]] = {}
        for eid in employee_ids:
            row = fetch_by_id("employees", eid) or fetch_by_id("user_profiles", eid)
            if row:
                out[eid] = {
                    "id": eid,
                    "name": str(row.get("name") or row.get("full_name") or row.get("email") or eid),
                }
        return out

    cache_key = f"job_schedule_employees:{jid}"
    return page_data_cache_get(cache_key, _build)
