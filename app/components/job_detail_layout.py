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
<style id="ips-job-detail-layout-v1">
.ips-job-detail-control-page {
  width: 100%;
}
.ips-job-detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  margin: 0 0 1rem 0;
  padding: 0 0 1rem 0;
  border-bottom: 1px solid #e8edf3;
}
.ips-job-detail-header-main {
  flex: 1 1 320px;
  min-width: 0;
}
.ips-job-detail-title-line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.45rem 0.65rem;
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.25;
  letter-spacing: -0.02em;
}
.ips-job-detail-number {
  color: #4361EE;
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
  margin: 0.35rem 0 0 0;
  font-size: 0.92rem;
  color: #64748b;
  font-weight: 500;
}
.ips-job-detail-header-actions {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex: 0 0 auto;
}
.ips-job-detail-meta-row {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.65rem;
  margin-bottom: 1rem;
}
@media (max-width: 1100px) {
  .ips-job-detail-meta-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .ips-job-detail-meta-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.ips-job-detail-meta-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.65rem 0.8rem;
  min-width: 0;
}
.ips-job-detail-meta-label {
  font-size: 0.68rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.2rem;
}
.ips-job-detail-meta-value {
  font-size: 0.84rem;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ips-job-detail-meta-value.is-link {
  color: #4361EE;
}
.ips-job-detail-health-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr 1.2fr;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
@media (max-width: 960px) {
  .ips-job-detail-health-grid {
    grid-template-columns: 1fr;
  }
}
.ips-job-detail-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.85rem 1rem;
  min-height: 118px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.ips-job-detail-panel-title {
  font-size: 0.72rem;
  font-weight: 800;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.55rem;
}
.ips-job-detail-health-status {
  font-size: 1.05rem;
  font-weight: 800;
  margin-bottom: 0.25rem;
}
.ips-job-detail-health-status.is-healthy { color: #15803d; }
.ips-job-detail-health-status.is-warning { color: #b45309; }
.ips-job-detail-health-status.is-danger { color: #dc2626; }
.ips-job-detail-health-status.is-neutral { color: #64748b; }
.ips-job-detail-health-copy {
  font-size: 0.78rem;
  color: #64748b;
  line-height: 1.35;
  margin: 0;
}
.ips-job-detail-progress-main {
  height: 12px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
  margin-top: 0.35rem;
}
.ips-job-detail-progress-main > span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #4361EE, #2563eb);
  border-radius: 999px;
}
.ips-job-detail-progress-pct {
  font-size: 1.35rem;
  font-weight: 800;
  color: #4361EE;
  line-height: 1;
}
.ips-job-detail-sub-progress {
  display: grid;
  gap: 0.55rem;
}
.ips-job-detail-sub-row {
  display: grid;
  grid-template-columns: 5.5rem 1fr 2.5rem;
  gap: 0.45rem;
  align-items: center;
  font-size: 0.75rem;
  color: #475569;
  font-weight: 600;
}
.ips-job-detail-sub-bar {
  height: 7px;
  background: #eef2f7;
  border-radius: 999px;
  overflow: hidden;
}
.ips-job-detail-sub-bar > span {
  display: block;
  height: 100%;
  background: #4361EE;
  border-radius: 999px;
}
.ips-job-detail-quick-stats {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0.65rem;
  margin-bottom: 1rem;
}
@media (max-width: 1100px) {
  .ips-job-detail-quick-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
@media (max-width: 640px) {
  .ips-job-detail-quick-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
.ips-job-detail-stat-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.7rem 0.75rem;
  min-width: 0;
}
.ips-job-detail-stat-label {
  font-size: 0.68rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ips-job-detail-stat-value {
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
  white-space: nowrap;
}
.ips-job-detail-stat-value.is-blue { color: #2563eb; }
.ips-job-detail-stat-value.is-green { color: #15803d; }
.ips-job-detail-body-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 1rem;
  align-items: start;
}
@media (max-width: 980px) {
  .ips-job-detail-body-grid {
    grid-template-columns: 1fr;
  }
}
.ips-job-detail-activity-panel {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.85rem 0.95rem;
  position: sticky;
  top: 0.5rem;
}
.ips-job-detail-activity-title {
  font-size: 0.72rem;
  font-weight: 800;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 0 0 0.65rem 0;
}
.ips-job-detail-activity-item {
  display: flex;
  gap: 0.55rem;
  align-items: flex-start;
  padding: 0.45rem 0;
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
  margin-top: 0.15rem;
}
.ips-job-detail-footer-actions {
  margin-top: 1rem;
  padding-top: 0.85rem;
  border-top: 1px solid #e8edf3;
}
.ips-job-detail-overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
}
@media (max-width: 760px) {
  .ips-job-detail-overview-grid {
    grid-template-columns: 1fr;
  }
}
.ips-jc-card-contract .ips-jc-summary-value { color: #2563eb; }
.ips-jc-card-actual .ips-jc-summary-value { color: #2563eb; }
.ips-jc-card-negative .ips-jc-summary-value { color: #dc2626; }
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) .ips-jc-summary-card {
  min-height: 64px;
  padding: 10px 12px;
}
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) .ips-jc-summary-value {
  font-size: 0.98rem;
}
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) {
  max-width: min(1240px, 97vw) !important;
  width: min(1240px, 97vw) !important;
}
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) [data-testid="stPopover"] button {
  white-space: nowrap !important;
  min-width: fit-content !important;
}
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) .ips-job-detail-footer-actions [data-testid="stHorizontalBlock"] {
  flex-wrap: nowrap !important;
  justify-content: flex-end !important;
  gap: 0.5rem !important;
}
div[data-testid="stDialog"]:has(.ips-job-detail-control-page) .ips-job-detail-footer-actions [data-testid="column"] {
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
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


def render_job_detail_activity_sidebar(job: dict) -> None:
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


def render_job_detail_header_actions(
    job: dict,
    *,
    on_edit: Callable[[dict], None],
    edit_key: str,
) -> None:
    """Actions popover in header — mirrors existing footer action triggers."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        return
    job_key = "".join(ch if ch.isalnum() else "_" for ch in jid) or "job"
    archived = _job_is_archived(job)
    can_manage = can_manage_job_actions()
    status = _normalize_status(job)

    with st.popover("Actions ▾", help="Job actions"):
        st.markdown(
            '<span class="ips-job-detail-actions-popover-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        if on_edit is not None and st.button("Edit Job", key=f"job_hdr_edit_{job_key}", use_container_width=True):
            on_edit(job)
            st.rerun()
        if not archived and can_manage:
            if status not in {"Completed", "Closed"} and st.button(
                "Job Complete",
                key=f"job_hdr_complete_{job_key}",
                use_container_width=True,
            ):
                st.session_state[_confirm_state_key(jid, "complete")] = True
                st.rerun()
            if status != "Cancelled" and st.button(
                "Cancel Job",
                key=f"job_hdr_cancel_{job_key}",
                use_container_width=True,
            ):
                st.session_state[_confirm_state_key(jid, "cancel")] = True
                st.rerun()
            if st.button("Delete Job", key=f"job_hdr_delete_{job_key}", use_container_width=True):
                st.session_state[_confirm_state_key(jid, "delete")] = True
                st.rerun()


def render_job_detail_footer_shell() -> None:
    st.markdown('<div class="ips-job-detail-footer-actions">', unsafe_allow_html=True)


def close_job_detail_footer_shell() -> None:
    st.markdown("</div>", unsafe_allow_html=True)
