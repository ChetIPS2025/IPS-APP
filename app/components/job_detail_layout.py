"""Job Details modal — professional control-page layout (UI only)."""

from __future__ import annotations

import html
from typing import Any, Callable

import streamlit as st

try:
    from app.services.job_cost_transaction_service import fetch_job_cost_transactions
    from app.services.jobs_service import can_manage_job_actions
except ImportError:
    from services.job_cost_transaction_service import fetch_job_cost_transactions  # type: ignore
    from services.jobs_service import can_manage_job_actions  # type: ignore


def inject_job_detail_layout_css() -> None:
    st.markdown(
        """
<style id="ips-job-detail-layout-v3">
.ips-job-detail-control-page {
  width: 100%;
}
.ips-job-detail-header-shell {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin: 0 0 0.65rem 0;
  padding: 0 0 0.65rem 0;
  border-bottom: 1px solid #e8edf3;
}
.ips-job-detail-header-main {
  flex: 1 1 280px;
  min-width: 0;
}
.ips-job-detail-title-line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.4rem 0.55rem;
  margin: 0;
  font-size: 1.45rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.2;
  letter-spacing: -0.02em;
}
.ips-job-detail-number {
  color: #2563eb;
  white-space: nowrap;
}
.ips-job-detail-sep {
  color: #cbd5e1;
  font-weight: 500;
}
.ips-job-detail-name {
  min-width: 0;
}
.ips-job-detail-customer {
  margin: 0.25rem 0 0 0;
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
}
.ips-job-detail-header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.45rem;
  flex: 0 0 auto;
}
.ips-job-detail-overview-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.55rem 1.25rem;
  margin: 0;
}
@media (max-width: 760px) {
  .ips-job-detail-overview-list {
    grid-template-columns: 1fr;
  }
}
.ips-job-detail-overview-item {
  min-width: 0;
  padding: 0.15rem 0;
}
.ips-job-detail-overview-label {
  font-size: 0.68rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.12rem;
}
.ips-job-detail-overview-value {
  font-size: 0.9rem;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
}
.ips-job-detail-progress-block {
  margin-top: 0.35rem;
}
.ips-job-detail-progress-main {
  height: 10px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
  margin-top: 0.35rem;
}
.ips-job-detail-progress-main > span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #4361EE);
  border-radius: 999px;
}
.ips-job-detail-progress-pct {
  font-size: 1.1rem;
  font-weight: 800;
  color: #2563eb;
  line-height: 1;
}
.ips-job-detail-section-title {
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 0.55rem 0;
}
.ips-job-detail-financial-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
  margin-bottom: 0.75rem;
}
@media (max-width: 960px) {
  .ips-job-detail-financial-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.ips-job-detail-fin-metric {
  background: #ffffff;
  border: 1px solid #dbe3ef;
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  min-width: 0;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.ips-job-detail-fin-label {
  font-size: 0.65rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.18rem;
}
.ips-job-detail-fin-value {
  font-size: 1rem;
  font-weight: 800;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}
.ips-job-detail-fin-value.is-positive { color: #15803d; }
.ips-job-detail-fin-value.is-negative { color: #dc2626; }
.ips-job-detail-fin-value.is-blue { color: #2563eb; }
.ips-job-detail-activity-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.75rem 0.85rem;
  margin-bottom: 0.75rem;
}
.ips-job-detail-activity-title {
  font-size: 0.72rem;
  font-weight: 800;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 0.55rem 0;
}
.ips-job-detail-activity-item {
  display: flex;
  gap: 0.55rem;
  align-items: flex-start;
  padding: 0.4rem 0;
  border-bottom: 1px solid #f1f5f9;
}
.ips-job-detail-activity-item:last-child {
  border-bottom: none;
}
.ips-job-detail-activity-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  margin-top: 0.35rem;
  flex-shrink: 0;
}
.ips-job-detail-activity-text {
  font-size: 0.78rem;
  color: #334155;
  line-height: 1.35;
  margin: 0;
}
.ips-job-detail-activity-ts {
  font-size: 0.68rem;
  color: #94a3b8;
  margin-top: 0.12rem;
}
.ips-job-detail-health-status.is-healthy { color: #15803d; font-weight: 800; }
.ips-job-detail-health-status.is-warning { color: #b45309; font-weight: 800; }
.ips-job-detail-health-status.is-danger { color: #dc2626; font-weight: 800; }
.ips-job-detail-health-status.is-neutral { color: #64748b; font-weight: 800; }
.ips-job-detail-aux-panel {
  margin-bottom: 0.65rem;
}
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) {
  max-width: min(1180px, 96vw) !important;
  width: min(1180px, 96vw) !important;
}
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) [data-testid="stTabs"] {
  margin-top: 0 !important;
}
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) [data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 0.15rem !important;
}
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) [data-testid="stTabs"] button[role="tab"] {
  font-size: 0.8125rem !important;
  font-weight: 700 !important;
  padding: 0.45rem 0.75rem !important;
}
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) .ips-jc-summary-card {
  min-height: 58px;
  padding: 8px 10px;
}
div[data-testid="stDialog"]:has(.ips-job-detail-header-menu-marker) [data-testid="stPopover"] > button {
  min-width: 28px !important;
  width: 28px !important;
  height: 28px !important;
  min-height: 28px !important;
  padding: 0 !important;
  border-radius: 6px !important;
  background: transparent !important;
  border: 1px solid transparent !important;
  color: #64748b !important;
  font-size: 1rem !important;
  font-weight: 700 !important;
}
div[data-testid="stDialog"]:has(.ips-job-detail-header-menu-marker) [data-testid="stPopover"] > button:hover {
  background: #f1f5f9 !important;
  border-color: #e2e8f0 !important;
  color: #0f172a !important;
}
div[data-testid="stPopoverBody"]:has(.job-detail-header-menu-panel) {
  min-width: 210px !important;
}
div[data-testid="stPopoverBody"]:has(.job-detail-header-menu-panel) .stButton > button {
  justify-content: flex-start !important;
  min-height: 34px !important;
  border-radius: 8px !important;
  font-size: 0.8125rem !important;
}
div[data-testid="stDialog"]:has(.ips-job-status-badge-editor-marker) [data-testid="stPopover"] > button {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-width: 0 !important;
  width: auto !important;
  height: 26px !important;
  min-height: 26px !important;
  padding: 0 12px !important;
  border-radius: 999px !important;
  border: none !important;
  box-shadow: none !important;
  font-size: 0.75rem !important;
  font-weight: 800 !important;
  line-height: 1 !important;
  letter-spacing: 0.01em !important;
}
div[data-testid="stDialog"]:has(.ips-job-status-active) [data-testid="stPopover"] > button,
div[data-testid="stDialog"]:has(.ips-job-status-badge-editor-marker.ips-job-status-active) [data-testid="stPopover"] > button {
  background: #dcfce7 !important;
  color: #14532d !important;
}
div[data-testid="stDialog"]:has(.ips-job-status-pending) [data-testid="stPopover"] > button,
div[data-testid="stDialog"]:has(.ips-job-status-badge-editor-marker.ips-job-status-pending) [data-testid="stPopover"] > button {
  background: #f1f5f9 !important;
  color: #475569 !important;
}
div[data-testid="stDialog"]:has(.ips-job-status-scheduled) [data-testid="stPopover"] > button,
div[data-testid="stDialog"]:has(.ips-job-status-badge-editor-marker.ips-job-status-scheduled) [data-testid="stPopover"] > button {
  background: #ffedd5 !important;
  color: #c2410c !important;
}
div[data-testid="stDialog"]:has(.ips-job-status-on-hold) [data-testid="stPopover"] > button,
div[data-testid="stDialog"]:has(.ips-job-status-badge-editor-marker.ips-job-status-on-hold) [data-testid="stPopover"] > button {
  background: #fee2e2 !important;
  color: #b91c1c !important;
}
div[data-testid="stDialog"]:has(.ips-job-status-completed) [data-testid="stPopover"] > button,
div[data-testid="stDialog"]:has(.ips-job-status-badge-editor-marker.ips-job-status-completed) [data-testid="stPopover"] > button {
  background: #dbeafe !important;
  color: #1d4ed8 !important;
}
div[data-testid="stDialog"]:has(.ips-job-status-closed) [data-testid="stPopover"] > button,
div[data-testid="stDialog"]:has(.ips-job-status-badge-editor-marker.ips-job-status-closed) [data-testid="stPopover"] > button {
  background: #e2e8f0 !important;
  color: #475569 !important;
}
div[data-testid="stDialog"]:has(.ips-job-status-badge-editor-marker) [data-testid="stPopover"] > button:hover {
  filter: brightness(0.96) !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _money(v: float | int | None) -> str:
    return f"${float(v or 0):,.2f}"


def _confirm_state_key(job_id: str, action: str) -> str:
    return f"confirm_{action}_job_{job_id}"


def _job_is_archived(job: dict) -> bool:
    if bool(job.get("is_deleted")):
        return True
    status = str(job.get("status") or "").strip().lower()
    return status in {"deleted", "archived"}


def _normalize_status(job: dict) -> str:
    raw = str(job.get("status") or "").strip().lower().replace("_", " ")
    mapping = {
        "completed": "Completed",
        "closed": "Closed",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
        "archived": "Archived",
        "deleted": "Deleted",
    }
    return mapping.get(raw, str(job.get("status") or "Draft").strip() or "Draft")


def _health_from_summary(cost_summary: dict[str, Any]) -> tuple[str, str, str]:
    estimated = float(cost_summary.get("estimated_cost") or 0)
    actual = float(cost_summary.get("actual_cost") or 0)
    projected = float(cost_summary.get("projected_final_cost") or 0)
    if estimated <= 0:
        return "—", "neutral", "Job cost data is not available yet."
    if actual > estimated:
        return "Over Budget", "danger", "Actual costs exceed the estimated budget."
    if projected > estimated * 1.05:
        return "At Risk", "warning", "Projected final cost may exceed budget."
    return "On Budget", "healthy", "The job is performing as expected."


def _progress_bar_html(pct: float, *, height_class: str = "ips-job-detail-progress-main") -> str:
    clamped = max(0.0, min(100.0, float(pct or 0)))
    return f'<div class="{height_class}"><span style="width:{clamped:g}%"></span></div>'


def gather_job_detail_stats(job: dict[str, Any], cost_summary: dict[str, Any]) -> dict[str, Any]:
    """Collect existing counts/costs for quick stats (no new backend logic)."""
    jid = str(job.get("id") or "").strip()
    labor_hours = 0.0
    open_subjobs = 0
    photo_count = 0
    document_count = 0
    weekly_ts_count = 0

    if jid:
        try:
            for txn in fetch_job_cost_transactions(jid):
                if str(txn.get("cost_category") or "").strip().lower() == "labor":
                    labor_hours += float(txn.get("quantity") or 0)
        except Exception:
            labor_hours = 0.0

        try:
            from app.services.tasks_service import get_tasks_by_job
        except ImportError:
            from services.tasks_service import get_tasks_by_job  # type: ignore
        try:
            closed = {"complete", "completed", "closed", "cancelled", "canceled", "duplicate"}
            for task in get_tasks_by_job(jid, include_closed=True):
                if str(task.get("status") or "").strip().lower() not in closed:
                    open_subjobs += 1
        except Exception:
            open_subjobs = 0

        try:
            from app.services.job_documents import fetch_job_documents
        except ImportError:
            from services.job_documents import fetch_job_documents  # type: ignore
        try:
            document_count = len(fetch_job_documents(jid, admin=False, limit=500) or [])
        except Exception:
            document_count = 0

        try:
            from app.services.job_photos import fetch_job_photos
        except ImportError:
            from services.job_photos import fetch_job_photos  # type: ignore
        try:
            photo_count = len(fetch_job_photos(jid, admin=False, limit=500) or [])
        except Exception:
            photo_count = 0

        try:
            from app.services.weekly_job_timesheet_service import list_timesheets_for_job
        except ImportError:
            from services.weekly_job_timesheet_service import list_timesheets_for_job  # type: ignore
        try:
            weekly_ts_count = len(list_timesheets_for_job(jid) or [])
        except Exception:
            weekly_ts_count = 0

    return {
        "labor_hours": round(labor_hours, 1),
        "material_cost": float(cost_summary.get("material_cost") or 0),
        "equipment_cost": float(cost_summary.get("equipment_cost") or 0),
        "open_subjobs": open_subjobs,
        "photo_count": photo_count,
        "document_count": document_count,
        "weekly_ts_count": weekly_ts_count,
        "progress_pct": float(cost_summary.get("progress_pct") or job.get("progress") or 0),
    }


def build_job_detail_tab_labels(job: dict[str, Any]) -> list[str]:
    """Tab labels for the redesigned Job Details modal."""
    jid = str(job.get("id") or "").strip()
    open_subjobs = 0
    document_count = 0
    photo_count = 0

    if jid:
        try:
            from app.services.tasks_service import get_tasks_by_job
        except ImportError:
            from services.tasks_service import get_tasks_by_job  # type: ignore
        try:
            closed = {"complete", "completed", "closed", "cancelled", "canceled", "duplicate"}
            open_subjobs = sum(
                1
                for task in get_tasks_by_job(jid, include_closed=True)
                if str(task.get("status") or "").strip().lower() not in closed
            )
        except Exception:
            open_subjobs = 0

        fetch_job_documents = None
        fetch_job_photos = None
        try:
            from app.services.job_documents import fetch_job_documents as _fetch_job_documents

            fetch_job_documents = _fetch_job_documents
        except Exception:
            pass
        try:
            if fetch_job_documents:
                document_count = len(fetch_job_documents(jid, admin=False, limit=500) or [])
        except Exception:
            document_count = 0

        try:
            from app.services.job_photos import fetch_job_photos as _fetch_job_photos

            fetch_job_photos = _fetch_job_photos
        except Exception:
            pass
        try:
            if fetch_job_photos:
                photo_count = len(fetch_job_photos(jid, admin=False, limit=500) or [])
        except Exception:
            photo_count = 0

    def _count_label(name: str, count: int) -> str:
        return f"{name} ({count})" if count > 0 else name

    labels = [
        "Overview",
        _count_label("Tasks", open_subjobs),
        "Schedule",
        "Crew & Time",
        "Materials",
        "Equipment",
        _count_label("Documents", document_count),
        _count_label("Photos", photo_count),
    ]
    if can_view_job_financial_tab():
        labels.append("Financial")
    labels.append("Activity")
    return labels


def render_job_detail_header(
    *,
    job_number: str,
    job_name: str,
    customer: str,
) -> None:
    st.markdown(
        f"""
        <div class="ips-job-detail-header-main">
          <h2 class="ips-job-detail-title-line">
            <span class="ips-job-detail-number">{html.escape(job_number)}</span>
            <span class="ips-job-detail-sep">|</span>
            <span class="ips-job-detail-name">{html.escape(job_name)}</span>
          </h2>
          <p class="ips-job-detail-customer">{html.escape(customer)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def can_view_job_financial_tab() -> bool:
    return can_manage_job_actions()


def _has_useful_value(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and text not in {"—", "None", "null", "0", "0.0"}


def render_job_detail_overview_section(
    job: dict[str, Any],
    *,
    customer: str,
    project_manager: str,
    supervisor: str,
    start_date: str,
    end_date: str,
    progress_pct: float,
) -> None:
    """Operational overview — only fields with useful data, plus progress."""
    rows: list[tuple[str, str]] = []
    for label, value in (
        ("Customer", customer),
        ("Project Manager", project_manager),
        ("Supervisor", supervisor),
        ("Start Date", start_date),
        ("End Date", end_date),
    ):
        if _has_useful_value(value):
            rows.append((label, str(value).strip()))

    st.markdown('<h3 class="ips-job-detail-section-title">Overview</h3>', unsafe_allow_html=True)
    if rows:
        cells = []
        for label, value in rows:
            cells.append(
                f'<div class="ips-job-detail-overview-item">'
                f'<div class="ips-job-detail-overview-label">{html.escape(label)}</div>'
                f'<div class="ips-job-detail-overview-value">{html.escape(value)}</div>'
                f"</div>"
            )
        st.markdown(
            f'<div class="ips-job-detail-overview-list">{"".join(cells)}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("Add customer, schedule, and team details in Edit Job.")

    progress = max(0.0, min(100.0, float(progress_pct or job.get("progress") or 0)))
    if progress > 0 or job.get("progress") is not None:
        st.markdown(
            f'<div class="ips-job-detail-overview-item ips-job-detail-progress-block">'
            f'<div class="ips-job-detail-overview-label">Progress</div>'
            f'<div class="ips-job-detail-progress-pct">{progress:g}%</div>'
            f"{_progress_bar_html(progress)}"
            f"</div>",
            unsafe_allow_html=True,
        )

    scope_text = str(job.get("scope") or job.get("description") or "").strip()
    if scope_text:
        st.markdown("**Scope**")
        st.markdown(scope_text)


def render_job_detail_financial_section(
    job: dict[str, Any],
    cost_summary: dict[str, Any],
    fin: dict[str, Any],
) -> None:
    """Dedicated financial metrics grid for the Financial tab."""
    has_contract = bool(fin.get("has_contract"))
    has_estimated = bool(fin.get("has_estimated"))
    has_actual = bool(fin.get("has_actual"))
    remaining = fin.get("remaining_budget")
    remaining_display = "—"
    if remaining is not None and (has_contract or has_estimated):
        remaining_display = _money(float(remaining or 0))

    profit = float(fin.get("gross_profit") or cost_summary.get("profit") or 0)
    margin = float(fin.get("margin_pct") or cost_summary.get("margin_pct") or 0)
    profit_cls = "is-positive" if profit > 0 else ("is-negative" if profit < 0 else "")
    margin_cls = profit_cls if has_contract else ""

    metrics = [
        ("Contract Value", _money(fin.get("contract_value", 0)) if has_contract else "—", "is-blue"),
        ("Estimated Cost", _money(fin.get("estimated_cost", 0)) if has_estimated else "—", ""),
        ("Actual Cost", _money(fin.get("actual_cost", 0)) if has_actual else "—", "is-blue"),
        ("Labor Cost", _money(fin.get("labor_cost", 0)) if has_actual else "—", ""),
        ("Material Cost", _money(fin.get("material_cost", 0)) if has_actual else "—", ""),
        ("Equipment Cost", _money(fin.get("equipment_cost", 0)) if has_actual else "—", ""),
        ("Remaining Budget", remaining_display, profit_cls if remaining_display != "—" else ""),
        ("Profit", _money(profit) if has_contract or has_actual else "—", profit_cls),
        ("Margin %", f"{margin:,.1f}%" if has_contract else "—", margin_cls),
    ]
    cells = []
    for label, value, tone in metrics:
        cells.append(
            f'<div class="ips-job-detail-fin-metric">'
            f'<div class="ips-job-detail-fin-label">{html.escape(label)}</div>'
            f'<div class="ips-job-detail-fin-value {tone}">{html.escape(value)}</div>'
            f"</div>"
        )
    st.markdown(
        f'<div class="ips-job-detail-financial-grid">{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )

    health, tone, copy = _health_from_summary(cost_summary)
    if health != "—":
        st.markdown(
            f'<p style="margin:0 0 0.75rem;font-size:0.8125rem;color:#64748b;">'
            f"<strong style=\"color:#0f172a;\">Job health:</strong> "
            f'<span class="ips-job-detail-health-status is-{html.escape(tone)}">{html.escape(health)}</span>'
            f" — {html.escape(copy)}"
            f"</p>",
            unsafe_allow_html=True,
        )


def render_job_detail_metadata_row(
    *,
    customer: str,
    project_manager: str,
    supervisor: str,
    estimate_no: str,
    schedule: str,
) -> None:
    items = [
        ("Customer", customer, True),
        ("Project Manager", project_manager, True),
        ("Supervisor", supervisor, False),
        ("Estimate #", estimate_no, True),
        ("Schedule", schedule, False),
    ]
    cells = []
    for label, value, is_link in items:
        val = value if value and value != "—" else "—"
        link_cls = " is-link" if is_link and val != "—" else ""
        cells.append(
            f'<div class="ips-job-detail-meta-item">'
            f'<div class="ips-job-detail-meta-label">{html.escape(label)}</div>'
            f'<div class="ips-job-detail-meta-value{link_cls}">{html.escape(val)}</div>'
            f"</div>"
        )
    st.markdown(
        f'<div class="ips-job-detail-meta-row">{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )


def render_job_detail_health_section(job: dict, cost_summary: dict[str, Any], stats: dict[str, Any]) -> None:
    health, tone, copy = _health_from_summary(cost_summary)
    progress = float(stats.get("progress_pct") or 0)
    job_progress = float(job.get("progress") or 0)
    labor_pct = job_progress if job_progress > 0 else min(100.0, progress)
    materials_est = float(cost_summary.get("estimated_cost") or 0)
    material_cost = float(cost_summary.get("material_cost") or 0)
    materials_pct = min(100.0, (material_cost / materials_est * 100.0)) if materials_est > 0 else 0.0
    subjobs_pct = progress

    show_sub_progress = progress > 0 or job_progress > 0 or material_cost > 0
    sub_rows = ""
    if show_sub_progress:
        sub_rows = (
            f'<div class="ips-job-detail-sub-row"><span>Labor</span>{_progress_bar_html(labor_pct, height_class="ips-job-detail-sub-bar")}<span>{labor_pct:g}%</span></div>'
            f'<div class="ips-job-detail-sub-row"><span>Materials</span>{_progress_bar_html(materials_pct, height_class="ips-job-detail-sub-bar")}<span>{materials_pct:g}%</span></div>'
            f'<div class="ips-job-detail-sub-row"><span>Subjobs</span>{_progress_bar_html(subjobs_pct, height_class="ips-job-detail-sub-bar")}<span>{subjobs_pct:g}%</span></div>'
        )

    st.markdown(
        f"""
        <div class="ips-job-detail-health-grid">
          <div class="ips-job-detail-panel">
            <div class="ips-job-detail-panel-title">Job Health</div>
            <div class="ips-job-detail-health-status is-{html.escape(tone)}">{html.escape(health)}</div>
            <p class="ips-job-detail-health-copy">{html.escape(copy)}</p>
          </div>
          <div class="ips-job-detail-panel">
            <div class="ips-job-detail-panel-title">Project Progress</div>
            <div class="ips-job-detail-progress-pct">{progress:g}%</div>
            {_progress_bar_html(progress)}
          </div>
          <div class="ips-job-detail-panel">
            <div class="ips-job-detail-panel-title">Progress Breakdown</div>
            <div class="ips-job-detail-sub-progress">{sub_rows or '<p class="ips-job-detail-health-copy">Progress details will appear as work is recorded.</p>'}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_job_detail_quick_stats(stats: dict[str, Any]) -> None:
    cards = [
        ("Labor Hours", f'{float(stats.get("labor_hours") or 0):,.1f}', ""),
        ("Material Cost", _money(stats.get("material_cost")), "is-blue"),
        ("Equipment Cost", _money(stats.get("equipment_cost")), "is-blue"),
        ("Open Subjobs", str(int(stats.get("open_subjobs") or 0)), ""),
        ("Photos", str(int(stats.get("photo_count") or 0)), ""),
        ("Documents", str(int(stats.get("document_count") or 0)), ""),
    ]
    cells = []
    for label, value, tone in cards:
        cells.append(
            f'<div class="ips-job-detail-stat-card">'
            f'<div class="ips-job-detail-stat-label">{html.escape(label)}</div>'
            f'<div class="ips-job-detail-stat-value {tone}">{html.escape(value)}</div>'
            f"</div>"
        )
    st.markdown(
        f'<div class="ips-job-detail-quick-stats">{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )


def render_job_detail_activity_timeline(job: dict) -> None:
    created = str(job.get("created_at") or "").strip()
    updated = str(job.get("updated_at") or "").strip()
    status = str(job.get("status") or "").strip()
    jname = str(job.get("job_name") or "this job").strip()
    items: list[tuple[str, str, str]] = []
    if updated and updated != created:
        items.append((updated[:16].replace("T", ", "), "#4361EE", "Job record updated"))
    if status:
        items.append((created[:16].replace("T", ", ") if created else "—", "#16a34a", f"Status set to {status}"))
    if created:
        items.append((created[:16].replace("T", ", "), "#94a3b8", f"Job created — {jname}"))

    st.markdown('<div class="ips-job-detail-activity-panel">', unsafe_allow_html=True)
    st.markdown('<p class="ips-job-detail-activity-title">Recent Activity</p>', unsafe_allow_html=True)
    if not items:
        st.markdown(
            '<p class="ips-job-detail-activity-text">No recent activity yet.</p>',
            unsafe_allow_html=True,
        )
    else:
        lines = []
        for ts, color, text in items[:5]:
            lines.append(
                f'<div class="ips-job-detail-activity-item">'
                f'<span class="ips-job-detail-activity-dot" style="background:{color}"></span>'
                f'<div><p class="ips-job-detail-activity-text">{html.escape(text)}</p>'
                f'<div class="ips-job-detail-activity-ts">{html.escape(ts)}</div></div></div>'
            )
        st.markdown("".join(lines), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_job_detail_header_menu_slot() -> None:
    """Marker wrapper for header actions column styling."""
    st.markdown(
        '<div class="ips-job-detail-header-actions"><span class="ips-job-detail-header-actions-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )


def close_job_detail_header_menu_slot() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_job_detail_header_actions(
    job: dict,
    *,
    on_edit: Callable[[dict], None],
    edit_key: str,
) -> None:
    """Deprecated — use job_detail_header_menu.render_job_detail_header_menu."""
    _ = (job, on_edit, edit_key)


def render_job_detail_footer_shell() -> None:
    st.markdown('<div class="ips-job-detail-footer-actions">', unsafe_allow_html=True)


def close_job_detail_footer_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
