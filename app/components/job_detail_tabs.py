"""Conditional Job Detail tab routing — only the active tab body executes."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.job_detail_layout import (
    build_job_detail_tab_labels,
    can_view_job_financial_tab,
    gather_job_detail_stats,
    render_job_detail_activity_timeline,
    render_job_detail_financial_section,
    render_job_detail_overview_section,
)
from app.components.job_cost_summary_cards import render_job_cost_breakdown
from app.components.job_cost_tab import render_job_cost_tab
from app.components.job_costing_tab import render_job_costing_tab
from app.components.job_materials_ui import render_job_materials_tab
from app.components.job_labor_readonly_panel import (
    render_job_labor_summary_tab,
    render_job_weekly_timesheets_tab,
)
from app.components.tabs import render_tabs
from app.perf_debug import perf_span
from app.styles import inject_tasks_module_css
from app.utils.formatting import fmt_date

_JOB_DETAIL_ACTIVE_TAB_KEY = "ips_job_detail_active_tab"
_JOB_CREW_SUBTAB_KEY = "ips_job_crew_active_subtab"
_CREW_SUBTABS = ["Labor Summary", "Weekly Timesheets"]


def job_detail_active_tab_key() -> str:
    return _JOB_DETAIL_ACTIVE_TAB_KEY


def reset_job_detail_tab(*, default: str = "Overview") -> None:
    st.session_state[_JOB_DETAIL_ACTIVE_TAB_KEY] = default


def set_job_detail_tab_from_query(tab: str) -> None:
    """Map job_tab query value to visible tab label."""
    raw = str(tab or "").strip()
    if not raw:
        return
    alias = {
        "overview": "Overview",
        "tasks": "Tasks",
        "subjobs": "Tasks",
        "schedule": "Schedule",
        "crew": "Crew & Time",
        "labor": "Crew & Time",
        "cost": "Cost",
        "cost lines": "Cost",
        "materials": "Materials",
        "equipment": "Equipment",
        "documents": "Documents",
        "photos": "Photos",
        "financial": "Financial",
        "job costing": "Financial",
        "costing": "Financial",
        "activity": "Activity",
    }
    resolved = alias.get(raw.lower(), raw)
    st.session_state[_JOB_DETAIL_ACTIVE_TAB_KEY] = resolved
    from app.navigation import JOBS_DETAIL_FOCUS_TAB_KEY

    st.session_state[JOBS_DETAIL_FOCUS_TAB_KEY] = resolved


def _tab_base_label(label: str) -> str:
    return str(label or "").split(" (")[0].strip()


def _active_tab_matches(active: str, *names: str) -> bool:
    base = _tab_base_label(active).lower()
    return base in {n.lower() for n in names}


def _load_cost_summary_if_needed(job: dict, *, active_tab: str) -> dict[str, Any]:
    if not _active_tab_matches(active_tab, "Cost", "Financial"):
        return {}
    jid = str(job.get("id") or "").strip()
    if not jid:
        return {}
    with perf_span("jobs.detail.cost_summary"):
        from app.services.job_cost_transaction_service import load_job_cost_detail_snapshot

        return load_job_cost_detail_snapshot(jid, job=job)


def render_job_detail_tabs(job: dict, *, cost_summary: dict | None = None) -> None:
    """Render Job Details tabs; only the selected tab performs heavy queries."""
    from app.pages.jobs import (
        _job_financial_snapshot,
        _job_session_key,
        _render_dialog_placeholder,
        _render_job_customer_po_overview,
        _render_job_daily_updates_tab,
        _render_job_documents_tab,
        _render_job_equipment_tab,
        _render_job_estimates_section,
        _render_job_photos_tab,
        _resolve_job_estimate_number,
        _safe_value,
    )
    from app.pages.tasks import render_job_linked_tasks_tab

    customer = _safe_value(job.get("customer"))
    supervisor = _safe_value(job.get("supervisor"))
    project_manager = _safe_value(job.get("project_manager"))
    jid = str(job.get("id") or "").strip()
    job_key = _job_session_key(job)
    show_financial = can_view_job_financial_tab()

    tab_labels = build_job_detail_tab_labels(job, include_counts=False)
    active_tab = render_tabs(
        tab_labels,
        session_key=_JOB_DETAIL_ACTIVE_TAB_KEY,
        default="Overview",
    )

    summary = cost_summary if isinstance(cost_summary, dict) else {}
    if not summary and _active_tab_matches(active_tab, "Cost", "Financial"):
        summary = _load_cost_summary_if_needed(job, active_tab=active_tab)
        if summary and jid:
            st.session_state[f"_job_cost_summary_{jid}"] = summary

    fin = _job_financial_snapshot(job, cost_summary=summary or None)
    detail_stats = gather_job_detail_stats(job, summary) if summary else {}
    progress_pct = float(
        detail_stats.get("progress_pct")
        or job.get("progress")
        or (summary.get("progress_pct") if summary else 0)
        or 0
    )

    if _active_tab_matches(active_tab, "Overview"):
        with perf_span("jobs.detail.overview"):
            render_job_detail_overview_section(
                job,
                customer=customer,
                project_manager=project_manager,
                supervisor=supervisor,
                start_date=fmt_date(job.get("start_date")),
                end_date=fmt_date(job.get("end_date")),
                progress_pct=progress_pct,
            )
    elif _active_tab_matches(active_tab, "Tasks"):
        with perf_span("jobs.detail.tasks"):
            inject_tasks_module_css()
            render_job_linked_tasks_tab(job)
    elif _active_tab_matches(active_tab, "Schedule"):
        with perf_span("jobs.detail.schedule"):
            from app.components.scheduling_job_tab import render_job_schedule_tab
            from app.services.scheduling_job_tab_service import employees_for_job_schedule

            employees_by_id = employees_for_job_schedule(jid) if jid else {}
            render_job_schedule_tab(
                job,
                jobs_by_id={jid: job} if jid else {},
                employees_by_id=employees_by_id,
            )
    elif _active_tab_matches(active_tab, "Crew & Time"):
        with perf_span("jobs.detail.crew"):
            if jid:
                crew_tab = render_tabs(
                    _CREW_SUBTABS,
                    session_key=f"{_JOB_CREW_SUBTAB_KEY}_{job_key}",
                    default="Labor Summary",
                )
                if crew_tab == "Labor Summary":
                    st.markdown("#### Labor Summary")
                    render_job_labor_summary_tab(
                        job,
                        key_prefix=f"job_labor_{job_key}",
                    )
                else:
                    st.markdown("#### Weekly Timesheets")
                    render_job_weekly_timesheets_tab(
                        job,
                        key_prefix=f"job_wts_{job_key}",
                    )
            else:
                _render_dialog_placeholder("Save this job before viewing crew and time data.")
    elif _active_tab_matches(active_tab, "Cost"):
        with perf_span("jobs.detail.cost"):
            if jid:
                render_job_cost_tab(job, key_prefix=f"job_cost_lines_{job_key}")
            else:
                _render_dialog_placeholder("Save this job before viewing cost lines.")
    elif _active_tab_matches(active_tab, "Materials"):
        with perf_span("jobs.detail.materials"):
            render_job_materials_tab(job, key_prefix=f"job_mat_{jid}")
    elif _active_tab_matches(active_tab, "Equipment"):
        with perf_span("jobs.detail.equipment"):
            _render_job_equipment_tab(job)
    elif _active_tab_matches(active_tab, "Documents"):
        with perf_span("jobs.detail.documents"):
            _render_job_documents_tab(job)
    elif _active_tab_matches(active_tab, "Photos"):
        with perf_span("jobs.detail.photos"):
            _render_job_photos_tab(job)
    elif show_financial and _active_tab_matches(active_tab, "Financial"):
        with perf_span("jobs.detail.financial"):
            if not summary and jid:
                summary = _load_cost_summary_if_needed(job, active_tab=active_tab)
            render_job_detail_financial_section(job, summary, fin)
            _render_job_customer_po_overview(job)
            st.divider()
            render_job_cost_breakdown(summary)
            st.divider()
            cached_summary = st.session_state.get(f"_job_cost_summary_{jid}")
            render_job_costing_tab(
                job,
                key_prefix=f"job_cost_{jid}",
                cost_summary=cached_summary if isinstance(cached_summary, dict) else summary,
            )
            st.divider()
            with perf_span("jobs.detail.estimates"):
                _render_job_estimates_section(job)
    elif _active_tab_matches(active_tab, "Activity"):
        with perf_span("jobs.detail.activity"):
            render_job_detail_activity_timeline(job)
            st.divider()
            _render_job_daily_updates_tab(job)
            notes_text = _safe_value(job.get("notes") or job.get("description"), "")
            if notes_text and notes_text != "—":
                st.markdown("#### Notes")
                st.markdown(notes_text)
