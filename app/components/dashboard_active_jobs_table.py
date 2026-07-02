"""Compact Active Jobs table for the operations dashboard (UI only)."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.components.job_row_actions_ui import render_job_row_actions
    from app.components.job_status_ui import job_status_pill_html
    from app.services.job_financial_ui import job_list_financials_from_row
    from app.services.jobs_service import normalize_job_status
    from app.services.tasks_service import count_open_subjobs_by_job_id
except ImportError:
    from components.job_row_actions_ui import render_job_row_actions  # type: ignore
    from components.job_status_ui import job_status_pill_html  # type: ignore
    from services.job_financial_ui import job_list_financials_from_row  # type: ignore
    from services.jobs_service import normalize_job_status  # type: ignore
    from services.tasks_service import count_open_subjobs_by_job_id  # type: ignore

_DASH_JOB_COLS = [0.55, 2.35, 1.15, 0.68, 0.72, 0.72, 0.72, 0.72, 0.58, 0.42, 0.62]
_DASH_JOB_COL_MARKERS = (
    "num",
    "desc",
    "customer",
    "status",
    "contract",
    "estimated",
    "actual",
    "profit",
    "margin",
    "subjobs",
    "actions",
)
_DASH_JOB_HEADERS: list[tuple[str, str | None]] = [
    ("JOB #", None),
    ("PROJECT / DESCRIPTION", None),
    ("CUSTOMER", None),
    ("STATUS", None),
    ("CONTRACT VALUE", None),
    ("ESTIMATED COST", None),
    ("ACTUAL COST", None),
    ("GROSS PROFIT", None),
    ("MARGIN %", None),
    ("OPEN TASKS / SUBJOBS", None),
    ("ACTIONS", None),
]


def _col_marker(name: str) -> str:
    return (
        f'<span class="ips-jobs-col-marker ips-jobs-col-{html.escape(name)}" '
        f'aria-hidden="true"></span>'
    )


def _money_cell(value: float, *, available: bool = True) -> str:
    if not available:
        return "—"
    if abs(float(value or 0)) < 0.005:
        return "—"
    return f"${float(value):,.2f}"


def _money_cell_class(value: float, *, available: bool = True) -> str:
    return " ips-jobs-money-empty" if _money_cell(value, available=available) == "—" else ""


def _pct_cell(value: float) -> str:
    return f"{float(value or 0):,.1f}%"


def _job_number(job: dict[str, Any]) -> str:
    for key in ("job_number", "number"):
        val = str(job.get(key) or "").strip()
        if val:
            return val
    return "—"


def _job_project(job: dict[str, Any]) -> str:
    for key in ("job_name", "project_name", "project_description", "description"):
        val = str(job.get(key) or "").strip()
        if val:
            return val
    return "—"


def _job_customer(job: dict[str, Any]) -> str:
    for key in ("customer_name", "customer"):
        val = str(job.get(key) or "").strip()
        if val:
            return val
    return "—"


def _job_cost_fields(job: dict[str, Any]) -> dict[str, float | bool]:
    fin = job_list_financials_from_row(job)
    return {
        "contract_value": float(fin["contract_value"]),
        "estimated_cost": float(fin["estimated_cost"]),
        "actual_cost": float(fin["actual_cost"]),
        "profit": float(fin["profit"]),
        "margin_pct": float(fin["margin_pct"]),
        "has_contract": bool(fin["has_contract"]),
        "has_estimated": bool(fin["has_estimated"]),
        "has_actual": bool(fin["has_actual"]),
    }


def _open_job_nav(job_id: str, job: dict[str, Any]) -> None:
    jid = str(job_id or "").strip()
    if not jid:
        return
    st.session_state["selected_job_id"] = jid
    st.session_state["show_job_detail_modal"] = True
    try:
        from app.navigation import set_nav_slug
    except ImportError:
        from navigation import set_nav_slug  # type: ignore
    set_nav_slug("jobs")
    st.rerun()


def _open_job_edit(job: dict[str, Any]) -> None:
    jid = str(job.get("id") or "").strip()
    if jid:
        st.session_state[f"job_edit_mode_{jid}"] = True


def _render_job_link(
    label: str,
    *,
    key: str,
    job: dict[str, Any],
    extra_class: str = "",
    truncate: bool = False,
) -> None:
    link_class = extra_class
    if truncate:
        link_class = f"{link_class} ips-jobs-cell-truncate".strip()
    st.markdown(f'<div class="ips-jobs-table-link {link_class}">', unsafe_allow_html=True)
    if st.button(
        label,
        key=key,
        type="tertiary",
        help="Open job details",
        use_container_width=not truncate,
    ):
        _open_job_nav(str(job.get("id") or ""), job)
    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard_active_jobs_table(
    jobs: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> None:
    """Render the jobs-page-style Active Jobs table on the dashboard."""
    try:
        from app.components.jobs_page_layout import inject_dashboard_active_jobs_table_css
    except ImportError:
        from components.jobs_page_layout import inject_dashboard_active_jobs_table_css  # type: ignore

    inject_dashboard_active_jobs_table_css()
    rows = list(jobs)[: max(1, int(limit))]

    def _go_jobs() -> None:
        try:
            from app.navigation import set_nav_slug
        except ImportError:
            from navigation import set_nav_slug  # type: ignore
        set_nav_slug("jobs")
        st.rerun()

    with st.container(key="dashboard_active_jobs_table"):
        hdr_l, hdr_r = st.columns([4, 1], gap="small", vertical_alignment="center")
        with hdr_l:
            st.markdown(
                '<p class="ips-ops-section-title ips-ops-jobs-table-title">Active Jobs</p>',
                unsafe_allow_html=True,
            )
        with hdr_r:
            if st.button("View All Jobs", key="ips_dash_jobs_all", use_container_width=True):
                _go_jobs()

        if not rows:
            st.markdown(
                '<p class="ips-dash-cu-empty">No active jobs.</p>',
                unsafe_allow_html=True,
            )
            return

        try:
            subjob_counts = count_open_subjobs_by_job_id()
        except Exception:
            subjob_counts = {}

        st.markdown('<div class="ips-jobs-table-wrap jobs-table ips-dash-jobs-table">', unsafe_allow_html=True)

        header_cols = st.columns(_DASH_JOB_COLS, gap="small", vertical_alignment="center")
        for col, (label, _field), marker in zip(header_cols, _DASH_JOB_HEADERS, _DASH_JOB_COL_MARKERS):
            with col:
                st.markdown(_col_marker(marker), unsafe_allow_html=True)
                st.markdown(
                    f'<div class="ips-jobs-header-row ips-jobs-cell">{html.escape(label)}</div>',
                    unsafe_allow_html=True,
                )

        for row_idx, job in enumerate(rows):
            jid = str(job.get("id") or "").strip()
            if not jid:
                continue

            job_no = _job_number(job)
            project = _job_project(job)
            customer = _job_customer(job)
            status = normalize_job_status(job.get("status"))
            costs = _job_cost_fields(job)
            contract_val = float(costs["contract_value"])
            estimated_val = float(costs["estimated_cost"])
            actual_val = float(costs["actual_cost"])
            profit_val = float(costs["profit"])
            margin_val = float(costs["margin_pct"])
            open_subjobs = int(subjob_counts.get(jid, 0))
            has_contract = bool(costs["has_contract"])
            has_estimated = bool(costs["has_estimated"])
            has_actual = bool(costs["has_actual"])
            has_profit_data = has_contract

            profit_cls = ""
            if has_profit_data:
                if profit_val > 0:
                    profit_cls = " ips-jobs-money-positive"
                elif profit_val < 0:
                    profit_cls = " ips-jobs-money-negative"

            row_parity = "even" if row_idx % 2 else "odd"
            cols = st.columns(_DASH_JOB_COLS, gap="small", vertical_alignment="center")

            with cols[0]:
                st.markdown(
                    f'<span class="ips-jobs-row-marker ips-jobs-table-row job-row jobs-table-row '
                    f'ips-jobs-row-{row_parity}" data-row-id="{html.escape(jid, quote=True)}" '
                    f'aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown(_col_marker("num"), unsafe_allow_html=True)
                num_label = job_no if job_no and job_no != "—" else "View job"
                _render_job_link(
                    num_label,
                    key=f"dash_job_num_{jid}",
                    job=job,
                    extra_class="ips-jobs-number-link job-number-link",
                )

            with cols[1]:
                st.markdown(_col_marker("desc"), unsafe_allow_html=True)
                title_label = project if project and project != "—" else "View job"
                _render_job_link(
                    title_label,
                    key=f"dash_job_title_{jid}",
                    job=job,
                    extra_class="ips-jobs-title-link job-project-link ips-jobs-cell job-cell jobs-table-cell",
                    truncate=True,
                )

            with cols[2]:
                st.markdown(_col_marker("customer"), unsafe_allow_html=True)
                customer_title = html.escape(customer, quote=True)
                st.markdown(
                    f'<div class="ips-jobs-cell job-cell jobs-table-cell ips-jobs-customer-cell '
                    f'ips-jobs-cell-truncate" title="{customer_title}">{html.escape(customer)}</div>',
                    unsafe_allow_html=True,
                )

            with cols[3]:
                st.markdown(_col_marker("status"), unsafe_allow_html=True)
                st.markdown(
                    '<span class="job-status-cell ips-jobs-status-cell" aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                st.markdown(job_status_pill_html(status), unsafe_allow_html=True)

            with cols[4]:
                st.markdown(_col_marker("contract"), unsafe_allow_html=True)
                contract_cls = _money_cell_class(contract_val, available=has_contract)
                st.markdown(
                    f'<div class="ips-jobs-money ips-jobs-cell ips-jobs-col-money{contract_cls}">'
                    f"{html.escape(_money_cell(contract_val, available=has_contract))}</div>",
                    unsafe_allow_html=True,
                )
            with cols[5]:
                st.markdown(_col_marker("estimated"), unsafe_allow_html=True)
                estimated_cls = _money_cell_class(estimated_val, available=has_estimated)
                st.markdown(
                    f'<div class="ips-jobs-money ips-jobs-cell ips-jobs-col-money{estimated_cls}">'
                    f"{html.escape(_money_cell(estimated_val, available=has_estimated))}</div>",
                    unsafe_allow_html=True,
                )
            with cols[6]:
                st.markdown(_col_marker("actual"), unsafe_allow_html=True)
                actual_cls = _money_cell_class(actual_val, available=has_actual)
                st.markdown(
                    f'<div class="ips-jobs-money ips-jobs-cell ips-jobs-col-money ips-jobs-money-actual{actual_cls}">'
                    f"{html.escape(_money_cell(actual_val, available=has_actual))}</div>",
                    unsafe_allow_html=True,
                )
            with cols[7]:
                st.markdown(_col_marker("profit"), unsafe_allow_html=True)
                profit_display_cls = _money_cell_class(profit_val, available=has_profit_data)
                st.markdown(
                    f'<div class="ips-jobs-money ips-jobs-cell ips-jobs-col-money{profit_cls}{profit_display_cls}">'
                    f"{html.escape(_money_cell(profit_val, available=has_profit_data))}</div>",
                    unsafe_allow_html=True,
                )
            with cols[8]:
                st.markdown(_col_marker("margin"), unsafe_allow_html=True)
                margin_display = _pct_cell(margin_val) if has_contract else "—"
                margin_cls = profit_cls if has_contract else " ips-jobs-money-empty"
                st.markdown(
                    f'<div class="ips-jobs-money ips-jobs-cell ips-jobs-col-money{margin_cls}">'
                    f"{html.escape(margin_display)}</div>",
                    unsafe_allow_html=True,
                )
            with cols[9]:
                st.markdown(_col_marker("subjobs"), unsafe_allow_html=True)
                st.markdown(
                    f'<div class="ips-jobs-cell job-cell jobs-table-cell ips-jobs-col-subjobs">'
                    f"{open_subjobs:,}</div>",
                    unsafe_allow_html=True,
                )
            with cols[10]:
                st.markdown(_col_marker("actions"), unsafe_allow_html=True)
                st.markdown(
                    '<span class="ips-jobs-actions-cell ips-jobs-actions-toolbar job-actions-cell" '
                    'aria-hidden="true"></span>',
                    unsafe_allow_html=True,
                )
                render_job_row_actions(
                    job,
                    on_open=_open_job_nav,
                    on_edit=_open_job_edit,
                    on_status_updated=lambda _jid, _status: None,
                )

        st.markdown("</div>", unsafe_allow_html=True)
