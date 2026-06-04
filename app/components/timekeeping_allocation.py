"""Timekeeping list-view daily allocation UI (one card per day, one control row per line)."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

import streamlit as st

try:
    from app.utils.formatting import fmt_date
except ImportError:
    from utils.formatting import fmt_date  # type: ignore

ALLOC_HOUR_TYPE_OPTS = ("S/T", "O/T")
ALLOC_LINE_COLS = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
ALLOC_LINE_COLS_PRIMARY = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

ALLOCATION_HEADER_ROW_HTML = """
<div class="timekeeping-allocation-header-row timekeeping-allocation-header-row-component" aria-hidden="true">
  <div>Assignment</div>
  <div>Type</div>
  <div>Hours</div>
  <div>Remaining</div>
  <div>Status</div>
  <div>Notes</div>
  <div>Actions</div>
</div>
"""


@dataclass(frozen=True)
class AllocationRenderDeps:
    """Callbacks and formatters supplied by the timekeeping page (avoids circular imports)."""

    fmt_day_hours: Callable[[object], str]
    coerce_assignment_label: Callable[[str, list[str]], str]
    assignment_option_index: Callable[[list[str], str], int]
    sync_assignment_job_widget: Callable[[str, list[str], str], str]
    normalize_alloc_hour_type: Callable[[object], str]
    ensure_alloc_type_widget_label: Callable[[str, str], None]
    alloc_hour_type_label: Callable[[str], str]
    timecard_status_pill_html: Callable[[str], str]
    allocated_hours_sum: Callable[[list[dict[str, Any]]], float]
    alloc_state_key: Callable[[str], str]
    day_is_editable: Callable[[str], bool]
    handle_alloc_line_submit: Callable[[dict, date, str], bool]
    handle_alloc_line_approve: Callable[[dict, date, str], bool]
    handle_alloc_line_reject: Callable[[dict, date, str], bool]


@dataclass
class DayAllocationCardContext:
    eid: str
    week_sig: str
    iso: str
    day_name: str
    daily_total: float
    allocated: float
    remaining: float
    type_summary: str
    alloc_state: str
    lines: list[dict[str, Any]]
    week_locked: bool
    job_opts: list[str]
    can_approve: bool
    emp: dict
    week_start_d: date
    by_date: dict[str, list[dict[str, Any]]]


def allocation_day_block_class(state: str) -> str:
    if state == "complete":
        return " timekeeping-alloc-day-complete"
    if state == "overallocated":
        return " timekeeping-alloc-day-overallocated"
    if state == "needs_assignment":
        return " timekeeping-alloc-day-needs-assignment"
    if state == "incomplete":
        return " timekeeping-alloc-day-incomplete"
    return ""


def allocation_card_state_class(state: str) -> str:
    mapping = {
        "complete": "allocation-complete",
        "incomplete": "allocation-incomplete",
        "overallocated": "allocation-overallocated",
        "needs_assignment": "allocation-needs-assignment",
        "no_hours": "allocation-no-hours",
    }
    return mapping.get(str(state or "").strip(), "allocation-incomplete")


def render_allocation_panel_intro() -> None:
    st.markdown(
        '<span class="timekeeping-allocation-panel-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="timekeeping-alloc-intro">'
        "<strong>Daily hours are entered in the employee row above.</strong> "
        "Split each day&rsquo;s total across jobs, subjobs, Shop, or Administrative, "
        "and mark each row as <strong>S/T</strong> (straight time) or <strong>O/T</strong> (overtime)."
        "</div>",
        unsafe_allow_html=True,
    )


def render_day_summary_inline(
    *,
    day_name: str,
    iso: str,
    daily_total: float,
    allocated: float,
    remaining: float,
    type_summary: str,
    balance_cls: str,
    card_cls: str,
    deps: AllocationRenderDeps,
) -> None:
    """DayAllocationCard → DaySummaryInline."""
    st.markdown(
        (
            f'<div class="timekeeping-day-summary-inline timekeeping-day-summary-inline-marker '
            f'timekeeping-alloc-day-summary {html.escape(card_cls)}\">'
            f"<strong>{html.escape(day_name)}</strong>"
            f'<span class="timekeeping-alloc-day-date">{html.escape(fmt_date(iso))}</span>'
            f'<span class="timekeeping-hours-badge timekeeping-alloc-day-total">'
            f"{html.escape(deps.fmt_day_hours(daily_total))} hrs in row above"
            f"</span>"
            f'<span class="timekeeping-allocation-status-text timekeeping-alloc-day-split">'
            f"Allocated {deps.fmt_day_hours(allocated)} / {deps.fmt_day_hours(daily_total)}"
            f"{html.escape(type_summary)} · {deps.fmt_day_hours(max(0.0, remaining))} remaining"
            f"</span>"
            f"</div>"
        ),
        unsafe_allow_html=True,
    )


def render_allocation_header_row() -> None:
    """DayAllocationCard → AllocationHeaderRow (static labels, no Streamlit widgets)."""
    st.markdown(ALLOCATION_HEADER_ROW_HTML, unsafe_allow_html=True)


def _allocation_row_col_weights(*, is_primary_row: bool) -> list[float]:
    return ALLOC_LINE_COLS_PRIMARY if is_primary_row else ALLOC_LINE_COLS


def _render_allocation_hours_input(
    *,
    value: float,
    widget_key: str,
    disabled: bool,
    deps: AllocationRenderDeps,
) -> float:
    st.markdown(
        '<span class="timekeeping-allocation-hours-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    if disabled:
        st.markdown(
            f'<div class="timekeeping-alloc-hours-readonly">{html.escape(deps.fmt_day_hours(value))}</div>',
            unsafe_allow_html=True,
        )
        return float(value)
    return float(
        st.number_input(
            "Hours",
            value=float(value),
            key=widget_key,
            label_visibility="collapsed",
            min_value=0.0,
            max_value=24.0,
            step=0.5,
            format="%.1f",
        )
    )


def _render_allocation_row_actions(
    *,
    deps: AllocationRenderDeps,
    emp: dict,
    week_start_d: date,
    eid: str,
    week_sig: str,
    iso: str,
    lines: list[dict[str, Any]],
    line: dict[str, Any],
    lix: int,
    day_status: str,
    row_editable: bool,
    can_approve: bool,
    by_date: dict[str, list[dict[str, Any]]],
    daily_total: float,
    job_opts: list[str],
    is_primary_row: bool,
) -> None:
    st.markdown(
        '<span class="timekeeping-allocation-actions-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    line_id = str(line.get("line_id") or "").strip()
    line_hours = float(line.get("hours") or 0)
    action_taken = False

    if (
        row_editable
        and day_status == "Pending"
        and can_approve
        and line_id
        and line_hours > 0
    ):
        approve_col, reject_col = st.columns(2, gap="small")
        with approve_col:
            if st.button(
                "Approve",
                key=f"tk_alloc_ok_{eid}_{week_sig}_{iso}_{lix}",
                use_container_width=False,
            ):
                action_taken = deps.handle_alloc_line_approve(emp, week_start_d, line_id)
        with reject_col:
            if st.button(
                "Reject",
                key=f"tk_alloc_no_{eid}_{week_sig}_{iso}_{lix}",
                use_container_width=False,
            ):
                action_taken = deps.handle_alloc_line_reject(emp, week_start_d, line_id)
    elif is_primary_row:
        submit_col, add_col, remove_col = st.columns([1.5, 1.65, 0.95], gap="small")
        with submit_col:
            if (
                row_editable
                and line_id
                and line_hours > 0
                and day_status in ("Draft", "Rejected")
                and st.button(
                    "Submit day line",
                    key=f"tk_alloc_submit_{eid}_{week_sig}_{iso}_{lix}",
                    use_container_width=False,
                )
            ):
                action_taken = deps.handle_alloc_line_submit(emp, week_start_d, line_id)
        with add_col:
            if row_editable and st.button(
                "+ Add assignment",
                key=f"tk_alloc_add_{eid}_{week_sig}_{iso}",
                use_container_width=False,
                help="Add another assignment row for this day",
            ):
                day_lines = list(by_date.get(iso) or [])
                remaining_hrs = max(
                    0.0,
                    round(daily_total - deps.allocated_hours_sum(day_lines), 2),
                )
                day_lines.append(
                    {
                        "line_id": "",
                        "job": job_opts[0] if job_opts else "— No assignment —",
                        "hour_type": "ST",
                        "hours": remaining_hrs,
                        "notes": "",
                        "status": "Draft",
                    }
                )
                by_date[iso] = day_lines
                st.session_state[deps.alloc_state_key(eid)] = by_date
                st.rerun()
        with remove_col:
            if row_editable and len(lines) > 1 and st.button(
                "Remove",
                key=f"tk_alloc_del_{eid}_{week_sig}_{iso}_{lix}",
                use_container_width=False,
                help="Remove this assignment row",
            ):
                by_date[iso] = [ln for j, ln in enumerate(lines) if j != lix]
                st.session_state[deps.alloc_state_key(eid)] = by_date
                st.rerun()
    else:
        submit_col, remove_col = st.columns([1.35, 0.95], gap="small")
        with submit_col:
            if (
                row_editable
                and line_id
                and line_hours > 0
                and day_status in ("Draft", "Rejected")
                and st.button(
                    "Submit day line",
                    key=f"tk_alloc_submit_{eid}_{week_sig}_{iso}_{lix}",
                    use_container_width=False,
                )
            ):
                action_taken = deps.handle_alloc_line_submit(emp, week_start_d, line_id)
        with remove_col:
            if row_editable and len(lines) > 1 and st.button(
                "Remove",
                key=f"tk_alloc_del_{eid}_{week_sig}_{iso}_{lix}",
                use_container_width=False,
                help="Remove this assignment row",
            ):
                by_date[iso] = [ln for j, ln in enumerate(lines) if j != lix]
                st.session_state[deps.alloc_state_key(eid)] = by_date
                st.rerun()

    if action_taken:
        st.rerun()


def render_allocation_control_row(
    *,
    deps: AllocationRenderDeps,
    ctx: DayAllocationCardContext,
    line: dict[str, Any],
    lix: int,
    remaining: float,
    normalize_timecard_status: Callable[[object], str],
) -> None:
    """Single allocation line: one st.columns grid inside a dedicated row container."""
    eid = ctx.eid
    week_sig = ctx.week_sig
    iso = ctx.iso
    lines = ctx.lines
    job_opts = ctx.job_opts
    by_date = ctx.by_date
    daily_total = ctx.daily_total

    day_status = normalize_timecard_status(line.get("status"))
    row_editable = not ctx.week_locked and deps.day_is_editable(day_status)
    job_key = f"tk_alloc_job_{eid}_{week_sig}_{iso}_{lix}"
    live_job = deps.sync_assignment_job_widget(
        job_key,
        job_opts,
        str(line.get("job") or job_opts[0]),
    )
    if job_key in st.session_state:
        live_job = deps.coerce_assignment_label(str(st.session_state[job_key]), job_opts)
    hour_type = deps.normalize_alloc_hour_type(line.get("hour_type"))
    type_key = f"tk_alloc_type_{eid}_{week_sig}_{iso}_{lix}"
    deps.ensure_alloc_type_widget_label(type_key, hour_type)
    if type_key in st.session_state:
        hour_type = deps.normalize_alloc_hour_type(st.session_state[type_key])
    is_primary_row = lix == 0

    with st.container(key=f"tk_alloc_row_{eid}_{week_sig}_{iso}_{lix}"):
        row_cols = st.columns(
            _allocation_row_col_weights(is_primary_row=is_primary_row),
            gap="small",
        )
        marker_classes = (
            "timekeeping-allocation-line-marker "
            "timekeeping-allocation-control-row-marker "
            "timekeeping-allocation-assignment-marker"
        )
        if is_primary_row:
            marker_classes += " timekeeping-allocation-primary-row-marker"
        with row_cols[0]:
            st.markdown(
                f'<span class="{marker_classes}" aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            if row_editable:
                line["job"] = st.selectbox(
                    "Assignment",
                    job_opts,
                    index=deps.assignment_option_index(job_opts, live_job),
                    key=job_key,
                    label_visibility="collapsed",
                )
            else:
                st.markdown(
                    f'<div class="timekeeping-alloc-cell">'
                    f"{html.escape(deps.coerce_assignment_label(str(line.get('job') or '—'), job_opts))}</div>",
                    unsafe_allow_html=True,
                )
        with row_cols[1]:
            st.markdown(
                '<span class="timekeeping-allocation-type-marker timekeeping-hour-type-cell" '
                'aria-hidden="true"></span>',
                unsafe_allow_html=True,
            )
            if row_editable:
                hour_type_options = list(ALLOC_HOUR_TYPE_OPTS)
                type_label = deps.alloc_hour_type_label(hour_type)
                deps.ensure_alloc_type_widget_label(type_key, hour_type)
                type_index = (
                    hour_type_options.index(type_label)
                    if type_label in hour_type_options
                    else 0
                )
                picked = st.selectbox(
                    "Type",
                    options=hour_type_options,
                    index=type_index,
                    key=type_key,
                    label_visibility="collapsed",
                )
                line["hour_type"] = deps.normalize_alloc_hour_type(picked)
            else:
                st.markdown(
                    f'<div class="timekeeping-alloc-cell timekeeping-alloc-type-cell '
                    f'timekeeping-hour-type-cell">'
                    f"{html.escape(deps.alloc_hour_type_label(hour_type))}</div>",
                    unsafe_allow_html=True,
                )
        with row_cols[2]:
            line["hours"] = _render_allocation_hours_input(
                value=float(line.get("hours") or 0),
                widget_key=f"tk_alloc_hrs_{eid}_{week_sig}_{iso}_{lix}",
                disabled=not row_editable,
                deps=deps,
            )
        with row_cols[3]:
            st.markdown(
                f'<div class="timekeeping-alloc-remaining-cell">'
                f"{html.escape(deps.fmt_day_hours(remaining))}</div>",
                unsafe_allow_html=True,
            )
        with row_cols[4]:
            st.markdown(
                f'<div class="timekeeping-alloc-status-cell">'
                f"{deps.timecard_status_pill_html(day_status)}</div>",
                unsafe_allow_html=True,
            )
        with row_cols[5]:
            if row_editable:
                line["notes"] = st.text_input(
                    "Notes",
                    value=str(line.get("notes") or ""),
                    key=f"tk_alloc_notes_{eid}_{week_sig}_{iso}_{lix}",
                    label_visibility="collapsed",
                    placeholder="Notes…",
                )
            else:
                st.markdown(
                    f'<div class="timekeeping-alloc-cell">'
                    f"{html.escape(str(line.get('notes') or '—'))}</div>",
                    unsafe_allow_html=True,
                )
        with row_cols[6]:
            _render_allocation_row_actions(
                deps=deps,
                emp=ctx.emp,
                week_start_d=ctx.week_start_d,
                eid=eid,
                week_sig=week_sig,
                iso=iso,
                lines=lines,
                line=line,
                lix=lix,
                day_status=day_status,
                row_editable=row_editable,
                can_approve=ctx.can_approve,
                by_date=by_date,
                daily_total=daily_total,
                job_opts=job_opts,
                is_primary_row=is_primary_row,
            )

    line["hour_type"] = deps.normalize_alloc_hour_type(line.get("hour_type"))


def render_day_allocation_card(
    *,
    deps: AllocationRenderDeps,
    ctx: DayAllocationCardContext,
    normalize_timecard_status: Callable[[object], str],
) -> None:
    """DayAllocationCard: summary, optional header, and one AllocationControlRow per line."""
    state = str(ctx.alloc_state)
    balance_cls = allocation_day_block_class(state)
    if state == "overallocated":
        balance_cls += " timekeeping-alloc-day-unbalanced"
    card_cls = allocation_card_state_class(state)

    with st.container(key=f"tk_alloc_day_{ctx.eid}_{ctx.week_sig}_{ctx.iso}"):
        unbalanced_cls = (
            " timekeeping-alloc-day-unbalanced" if state == "overallocated" else ""
        )
        st.markdown(
            f'<span class="timekeeping-day-allocation-card-marker timekeeping-alloc-day-state-marker '
            f"timekeeping-alloc-day-state-{html.escape(state)}{unbalanced_cls} "
            f'timekeeping-allocation-day-card-marker timekeeping-allocation-day-group-marker" '
            f'aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        render_day_summary_inline(
            day_name=ctx.day_name,
            iso=ctx.iso,
            daily_total=ctx.daily_total,
            allocated=ctx.allocated,
            remaining=ctx.remaining,
            type_summary=ctx.type_summary,
            balance_cls=balance_cls,
            card_cls=card_cls,
            deps=deps,
        )
        if ctx.daily_total <= 0:
            st.caption("Enter hours for this day in the row above before assigning.")
            return

        render_allocation_header_row()
        for lix, line in enumerate(ctx.lines):
            render_allocation_control_row(
                deps=deps,
                ctx=ctx,
                line=line,
                lix=lix,
                remaining=ctx.remaining,
                normalize_timecard_status=normalize_timecard_status,
            )
