"""Optional dashboard charts (render only when data exists)."""

from __future__ import annotations

from collections import Counter

import streamlit as st

from .utils import job_status_bucket, norm_status


def _status_counts(rows: list[dict], *, field: str = "status") -> dict[str, int]:
    c: Counter[str] = Counter()
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        label = str(r.get(field) or "").strip() or "Unknown"
        c[label] += 1
    return dict(c)


def render_jobs_chart(jobs: list[dict]) -> None:
    if not jobs:
        return
    buckets = Counter()
    for j in jobs:
        b = job_status_bucket((j or {}).get("status"))
        buckets[b or "other"] += 1
    if not buckets:
        return
    st.caption("Jobs by pipeline stage")
    st.bar_chart(dict(buckets))


def render_estimates_chart(estimates: list[dict]) -> None:
    counts = _status_counts(estimates)
    if not counts:
        return
    st.caption("Estimates by status")
    st.bar_chart(counts)


def render_labor_summary_chart(time_entries: list[dict], *, work_date: str) -> None:
    hours = 0.0
    for row in time_entries or []:
        if str((row or {}).get("work_date") or "")[:10] != work_date:
            continue
        try:
            hours += float((row or {}).get("hours") or 0)
        except (TypeError, ValueError):
            pass
    if hours <= 0:
        return
    st.caption(f"Labor hours on {work_date}")
    st.bar_chart({"Today": hours})


def render_profitability_chart(jobs: list[dict]) -> None:
    """Placeholder chart when job rows expose revenue/cost fields."""
    rev = 0.0
    cost = 0.0
    for j in jobs or []:
        if not isinstance(j, dict):
            continue
        try:
            rev += float(j.get("revenue") or j.get("contract_value") or 0)
        except (TypeError, ValueError):
            pass
        try:
            cost += float(j.get("cost") or j.get("actual_cost") or 0)
        except (TypeError, ValueError):
            pass
    if rev <= 0 and cost <= 0:
        return
    st.caption("Revenue vs cost (loaded jobs)")
    st.bar_chart({"Revenue": rev, "Cost": cost})
