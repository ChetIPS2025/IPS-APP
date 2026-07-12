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

ALLOC_HOUR_TYPE_OPTS = ("Auto", "S/T", "O/T")
# Streamlit column weights (layout widths come from CSS grid/flex in styles.py).
# Reference layout: Assignment | Type | Hours (+ Remaining/Status below) | Notes
ALLOC_LINE_COLS = [3.55, 0.58, 0.78, 1.55]
ALLOC_LINE_COLS_COMPACT = [5.5, 1.0, 1.0]


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
    day_hours_editable: Callable[[str, str], bool]
    handle_alloc_line_submit: Callable[[dict, date, str, str, dict[str, Any]], bool]
    handle_alloc_line_approve: Callable[[dict, date, str], bool]
    handle_alloc_line_reject: Callable[[dict, date, str], bool]
    handle_day_submit_for_date: Callable[[dict, date, str], bool]
    handle_day_approve_for_date: Callable[[dict, date, str], bool]
    handle_day_reject_for_date: Callable[[dict, date, str], bool]
    mark_allocation_dirty: Callable[[str], None]
    save_allocation_day: Callable[[str], None]
    alloc_autosave_status_html: Callable[[str], str]
    can_override_overtime: bool = False
    handle_alloc_type_change: Callable[[str, int], None] | None = None
    overtime_badge_html: Callable[[dict[str, Any]], str] | None = None
    overtime_policy_note: str = ""
    selected_time_type_from_line: Callable[[dict[str, Any]], str] | None = None
    selected_time_type_widget_label: Callable[[str], str] | None = None
    alloc_time_type_hint_html: Callable[[dict[str, Any], str], str] | None = None


def allocation_panel_scope_key(scope: str) -> str:
    """Sanitize timecard/employee scope for Streamlit container keys."""
    return "".join(ch if ch.isalnum() else "_" for ch in str(scope or "").strip()) or "alloc"


@dataclass
class DayAllocationCardContext:
    eid: str
    week_sig: str
    panel_scope: str
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
    record_key: str = ""
    week_status: str = ""
    day_status: str = "Draft"
    can_submit: bool = False
    include_notes: bool = True
    modal_host: bool = False
    daily_hours_label: str = "hrs in row above"


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


def allocation_day_approval_class(day_status: str, *, alloc_state: str = "") -> str:
    """CSS hook for day-level approval state on allocation cards."""
    try:
        from app.services.timekeeping_day_ui import (
            day_fully_approved_and_allocated,
            normalize_timecard_status,
        )
    except ImportError:
        from services.timekeeping_day_ui import (  # type: ignore
            day_fully_approved_and_allocated,
            normalize_timecard_status,
        )

    mapping = {
        "Draft": "timekeeping-alloc-approval-draft",
        "Pending": "timekeeping-alloc-approval-pending",
        "Approved": "timekeeping-alloc-approval-approved",
        "Rejected": "timekeeping-alloc-approval-rejected",
    }
    key = normalize_timecard_status(day_status)
    base = mapping.get(key, "timekeeping-alloc-approval-draft")
    if day_fully_approved_and_allocated(alloc_state, key):
        return f"{base} timekeeping-alloc-approval-approved-complete"
    return base


def allocation_card_state_class(state: str) -> str:
    mapping = {
        "complete": "allocation-complete",
        "incomplete": "allocation-incomplete",
        "overallocated": "allocation-overallocated",
        "needs_assignment": "allocation-needs-assignment",
        "no_hours": "allocation-no-hours",
    }
    return mapping.get(str(state or "").strip(), "allocation-incomplete")


def render_allocation_panel_intro(*, policy_note: str = "", week_totals_html: str = "") -> None:
    st.markdown(
        '<span class="timekeeping-allocation-panel-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="timekeeping-alloc-intro">'
        "<strong>Daily hours are entered in the employee row above.</strong> "
        "Split each day&rsquo;s total across jobs, subjobs, Shop, Administrative, or Vacation, "
        "and mark each row as <strong>S/T</strong> (straight time) or <strong>O/T</strong> (overtime)."
        "</div>",
        unsafe_allow_html=True,
    )
    if policy_note:
        st.caption(policy_note)
    if week_totals_html:
        st.markdown(week_totals_html, unsafe_allow_html=True)


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
    hours_badge_text: str = "hrs in row above",
) -> None:
    """Day card header with separate Streamlit elements (no concatenated labels)."""
    st.markdown(
        (
            f'<span class="timekeeping-day-summary-inline-marker timekeeping-day-allocation-card-marker '
            f"timekeeping-allocation-day-card-marker {html.escape(card_cls)}{balance_cls}\" "
            f'aria-hidden="true"></span>'
        ),
        unsafe_allow_html=True,
    )
    head_cols = st.columns([1.45, 1.55], gap="small")
    with head_cols[0]:
        title_cols = st.columns([0.75, 1.0, 1.15], gap="small")
        with title_cols[0]:
            st.markdown(f"**{html.escape(day_name)}**")
        with title_cols[1]:
            st.caption(f"· {html.escape(fmt_date(iso))}")
        with title_cols[2]:
            st.markdown(
                (
                    f'<span class="timekeeping-hours-badge timekeeping-alloc-day-total">'
                    f"{html.escape(deps.fmt_day_hours(daily_total))} {html.escape(hours_badge_text)}"
                    f"</span>"
                ),
                unsafe_allow_html=True,
            )
    with head_cols[1]:
        alloc_text = (
            f"Allocated {deps.fmt_day_hours(allocated)} / {deps.fmt_day_hours(daily_total)}"
        )
        if type_summary:
            alloc_text += html.escape(type_summary)
        alloc_text += (
            f" · {html.escape(deps.fmt_day_hours(max(0.0, remaining)))} remaining"
        )
        st.markdown(
            f'<div class="timekeeping-alloc-day-split timekeeping-allocation-status-text">'
            f"{alloc_text}</div>",
            unsafe_allow_html=True,
        )


def _render_allocation_hours_input(
    *,
    value: float,
    widget_key: str,
    disabled: bool,
    deps: AllocationRenderDeps,
    on_change: Callable[..., None] | None = None,
    on_change_args: tuple[Any, ...] = (),
) -> float:
    st.markdown(
        '<span class="timekeeping-allocation-hours-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    if disabled:
        st.markdown(
            '<div class="timekeeping-alloc-field-label timekeeping-alloc-field-label-static">'
            "Hours</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="timekeeping-alloc-hours-readonly">{html.escape(deps.fmt_day_hours(value))}</div>',
            unsafe_allow_html=True,
        )
        return float(value)
    hours_kwargs: dict[str, Any] = {
        "label": "Hours",
        "value": float(value),
        "key": widget_key,
        "min_value": 0.0,
        "max_value": 24.0,
        "step": 0.5,
        "format": "%.1f",
        "label_visibility": "collapsed",
    }
    if on_change is not None:
        hours_kwargs["on_change"] = on_change
        hours_kwargs["args"] = on_change_args
    return float(st.number_input(**hours_kwargs))


def _append_assignment_line(
    *,
    deps: AllocationRenderDeps,
    ctx: DayAllocationCardContext,
) -> None:
    iso = ctx.iso
    eid = ctx.eid
    by_date = ctx.by_date
    day_lines = list(by_date.get(iso) or [])
    remaining_hrs = max(
        0.0,
        round(ctx.daily_total - deps.allocated_hours_sum(day_lines), 2),
    )
    day_lines.append(
        {
            "line_id": "",
            "job": ctx.job_opts[0] if ctx.job_opts else "— No assignment —",
            "hour_type": "AUTO",
            "selected_time_type": "AUTO",
            "hours": remaining_hrs,
            "notes": "",
            "status": "Draft",
            "calculated_time_type": "ST",
            "final_time_type": "ST",
            "overtime_override": False,
            "overtime_override_by": None,
            "overtime_override_at": None,
            "overtime_override_reason": None,
        }
    )
    by_date[iso] = day_lines
    st.session_state[deps.alloc_state_key(eid)] = by_date
    deps.mark_allocation_dirty(iso)
    st.rerun()


def _render_day_actions_bar(
    *,
    deps: AllocationRenderDeps,
    ctx: DayAllocationCardContext,
    normalize_timecard_status: Callable[[object], str] | None = None,
) -> None:
    """Footer bar: day status on the left, action buttons in a horizontal row on the right."""
    st.markdown(
        '<span class="timekeeping-allocation-day-actions-bar-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    norm = normalize_timecard_status or (lambda raw: str(raw or "Draft"))
    day_status = norm(ctx.day_status)
    hours_editable = deps.day_hours_editable(day_status, ctx.week_status)

    action_slots: list[str] = []
    if hours_editable:
        action_slots.append("add")
        if ctx.daily_total > 0 and not ctx.modal_host:
            action_slots.append("save")
    if (
        hours_editable
        and ctx.can_submit
        and ctx.daily_total > 0
        and day_status in ("Draft", "Rejected")
        and str(ctx.alloc_state) == "complete"
    ):
        action_slots.append("submit")
    if ctx.can_approve and day_status == "Pending" and ctx.daily_total > 0:
        action_slots.extend(["approve", "reject"])

    status_col, add_col, actions_col = st.columns([1.2, 1.4, 1.4], gap="small", vertical_alignment="center")
    with status_col:
        status_wrap_cls = ""
        try:
            from app.services.timekeeping_day_ui import day_fully_approved_and_allocated
        except ImportError:
            from services.timekeeping_day_ui import day_fully_approved_and_allocated  # type: ignore
        if day_fully_approved_and_allocated(str(ctx.alloc_state or ""), day_status):
            status_wrap_cls = " timekeeping-alloc-day-actions-status-approved-complete"
        st.markdown(
            f'<div class="timekeeping-alloc-day-actions-status{status_wrap_cls}">'
            f'<span class="timekeeping-alloc-day-actions-status-label">Status:</span> '
            f"{deps.timecard_status_pill_html(day_status)}</div>",
            unsafe_allow_html=True,
        )
    with add_col:
        if "add" in action_slots:
            if st.button(
                "+ Add Assignment",
                key=f"timecard_add_{ctx.eid}_{ctx.iso}",
                type="secondary",
                help="Add another assignment row for this day",
            ):
                _append_assignment_line(deps=deps, ctx=ctx)
    with actions_col:
        st.markdown(
            '<span class="timekeeping-allocation-actions-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        if not action_slots and day_status == "Approved":
            st.caption("This day is approved and locked.")
            return
        if not action_slots and day_status == "Pending":
            st.caption("Pending approval — hours are locked until an administrator approves or rejects.")
            return
        if not action_slots:
            return

        trailing_slots = [slot for slot in action_slots if slot != "add"]
        if not trailing_slots:
            return
        btn_cols = st.columns(len(trailing_slots), gap="small")
        for col, slot in zip(btn_cols, trailing_slots):
            with col:
                if slot == "save":
                    if st.button(
                        "Save Day",
                        key=f"timecard_save_{ctx.eid}_{ctx.iso}",
                        type="primary",
                    ):
                        deps.save_allocation_day(ctx.iso)
                        st.rerun()
                elif slot == "submit":
                    if st.button(
                        "Submit day",
                        key=f"tk_submit_day_{ctx.eid}_{ctx.week_sig}_{ctx.iso}",
                    ):
                        if deps.handle_day_submit_for_date(ctx.emp, ctx.week_start_d, ctx.iso):
                            st.rerun()
                elif slot == "approve":
                    if st.button(
                        "Approve day",
                        key=f"tk_approve_day_{ctx.eid}_{ctx.week_sig}_{ctx.iso}",
                        type="primary",
                    ):
                        if deps.handle_day_approve_for_date(ctx.emp, ctx.week_start_d, ctx.iso):
                            st.rerun()
                elif slot == "reject":
                    if st.button(
                        "Reject day",
                        key=f"tk_reject_day_{ctx.eid}_{ctx.week_sig}_{ctx.iso}",
                    ):
                        if deps.handle_day_reject_for_date(ctx.emp, ctx.week_start_d, ctx.iso):
                            st.rerun()


def _render_allocation_row_secondary_actions(
    *,
    deps: AllocationRenderDeps,
    ctx: DayAllocationCardContext,
    line: dict[str, Any],
    lix: int,
    lines: list[dict[str, Any]],
    day_status: str,
    row_editable: bool,
) -> None:
    """Extra rows: remove line; optional submit line when draft."""
    if not row_editable:
        return
    line_id = str(line.get("line_id") or "").strip()
    line_hours = float(line.get("hours") or 0)
    action_taken = False
    btn_cols = st.columns(2, gap="small")
    with btn_cols[0]:
        if (
            line_id
            and line_hours > 0
            and day_status in ("Draft", "Rejected")
            and st.button(
                "Submit line",
                key=f"tk_alloc_submit_{ctx.eid}_{ctx.week_sig}_{ctx.iso}_{lix}",
                use_container_width=True,
            )
        ):
            action_taken = deps.handle_alloc_line_submit(
                ctx.emp, ctx.week_start_d, line_id, ctx.iso, line
            )
    with btn_cols[1]:
        if len(lines) > 1 and st.button(
            "Remove",
            key=f"tk_alloc_del_{ctx.eid}_{ctx.week_sig}_{ctx.iso}_{lix}",
            use_container_width=True,
            help="Remove this assignment row",
        ):
            ctx.by_date[ctx.iso] = [ln for j, ln in enumerate(lines) if j != lix]
            st.session_state[deps.alloc_state_key(ctx.eid)] = ctx.by_date
            deps.mark_allocation_dirty(ctx.iso)
            action_taken = True
    if action_taken:
        st.rerun()


def render_allocation_control_row(
    *,
    deps: AllocationRenderDeps,
    ctx: DayAllocationCardContext,
    line: dict[str, Any],
    lix: int,
    normalize_timecard_status: Callable[[object], str],
) -> None:
    """Single allocation line: one st.columns grid inside a dedicated row container."""
    eid = ctx.eid
    week_sig = ctx.week_sig
    iso = ctx.iso
    lines = ctx.lines
    job_opts = ctx.job_opts

    day_status = normalize_timecard_status(line.get("status"))
    row_editable = deps.day_hours_editable(
        str(ctx.day_status or day_status),
        ctx.week_status,
    )
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
    selected_token = (
        deps.selected_time_type_from_line(line)
        if deps.selected_time_type_from_line is not None
        else hour_type
    )
    widget_label_fn = deps.selected_time_type_widget_label or deps.alloc_hour_type_label
    deps.ensure_alloc_type_widget_label(type_key, selected_token)
    if type_key in st.session_state:
        raw_pick = str(st.session_state[type_key] or "").strip()
        if raw_pick == "Auto":
            selected_token = "AUTO"
        elif raw_pick:
            selected_token = deps.normalize_alloc_hour_type(raw_pick)
    is_primary_row = lix == 0
    line_scope = allocation_panel_scope_key(f"{ctx.panel_scope}_{iso}_{lix}")
    autosave_cb = deps.mark_allocation_dirty if row_editable else None
    autosave_args = (iso,)
    line_cols = ALLOC_LINE_COLS if ctx.include_notes else ALLOC_LINE_COLS_COMPACT
    with st.container(key=f"tk_alloc_line_{line_scope}"):
        row_cols = st.columns(line_cols, gap="small")
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
                    on_change=autosave_cb,
                    args=autosave_args,
                )
            else:
                st.markdown(
                    '<div class="timekeeping-alloc-field-label timekeeping-alloc-field-label-static">'
                    "Assignment</div>",
                    unsafe_allow_html=True,
                )
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
            calculated = deps.normalize_alloc_hour_type(line.get("calculated_time_type") or "ST")
            badge_html = ""
            if deps.overtime_badge_html:
                badge_html = deps.overtime_badge_html(line)
            if badge_html:
                st.markdown(
                    f'<div class="timekeeping-alloc-type-badge-wrap">{badge_html}</div>',
                    unsafe_allow_html=True,
                )
            if not row_editable:
                st.markdown(
                    '<div class="timekeeping-alloc-field-label timekeeping-alloc-field-label-static">'
                    "Time Type</div>",
                    unsafe_allow_html=True,
                )
                display_type = deps.alloc_hour_type_label(
                    line.get("final_time_type") or calculated
                )
                st.markdown(
                    f'<div class="timekeeping-alloc-cell timekeeping-alloc-type-cell '
                    f'timekeeping-hour-type-cell">'
                    f"{html.escape(display_type)}</div>",
                    unsafe_allow_html=True,
                )
            else:
                hour_type_options = list(ALLOC_HOUR_TYPE_OPTS)
                type_label = widget_label_fn(selected_token)
                type_index = (
                    hour_type_options.index(type_label)
                    if type_label in hour_type_options
                    else 0
                )
                type_disabled = not deps.can_override_overtime
                type_kwargs: dict[str, Any] = {
                    "label": "Time Type",
                    "options": hour_type_options,
                    "index": type_index,
                    "key": type_key,
                    "label_visibility": "collapsed",
                    "disabled": type_disabled,
                }
                if deps.can_override_overtime:
                    if deps.handle_alloc_type_change is not None:
                        type_kwargs["on_change"] = deps.handle_alloc_type_change
                        type_kwargs["args"] = (iso, lix)
                    else:
                        type_kwargs["on_change"] = autosave_cb
                        type_kwargs["args"] = autosave_args
                else:
                    type_kwargs["help"] = (
                        f"Calculated as {deps.alloc_hour_type_label(calculated)} — "
                        "administrators may override S/T or O/T"
                    )
                st.selectbox(**type_kwargs)
                if deps.alloc_time_type_hint_html:
                    hint_html = deps.alloc_time_type_hint_html(line, iso)
                    if hint_html:
                        st.markdown(hint_html, unsafe_allow_html=True)
                if selected_token == "AUTO":
                    line["selected_time_type"] = "AUTO"
                    line["hour_type"] = deps.normalize_alloc_hour_type(
                        line.get("final_time_type") or calculated
                    )
                elif line.get("overtime_override") or deps.can_override_overtime:
                    line["selected_time_type"] = selected_token
                    line["hour_type"] = deps.normalize_alloc_hour_type(
                        line.get("final_time_type") or selected_token
                    )
                else:
                    line["selected_time_type"] = "AUTO"
                    line["hour_type"] = deps.normalize_alloc_hour_type(
                        line.get("final_time_type") or calculated
                    )
        with row_cols[2]:
            line["hours"] = _render_allocation_hours_input(
                value=float(line.get("hours") or 0),
                widget_key=f"tk_alloc_hrs_{eid}_{week_sig}_{iso}_{lix}",
                disabled=not row_editable,
                deps=deps,
                on_change=autosave_cb,
                on_change_args=autosave_args,
            )
        if ctx.include_notes:
            with row_cols[3]:
                if row_editable:
                    line["notes"] = st.text_input(
                        "Notes",
                        value=str(line.get("notes") or ""),
                        key=f"tk_alloc_notes_{eid}_{week_sig}_{iso}_{lix}",
                        placeholder="Add notes (optional)",
                        on_change=autosave_cb,
                        args=autosave_args,
                    )
                    if is_primary_row:
                        status_html = deps.alloc_autosave_status_html(iso)
                        if status_html:
                            st.markdown(
                                f'<div class="timekeeping-alloc-row-autosave">{status_html}</div>',
                                unsafe_allow_html=True,
                            )
                else:
                    st.markdown(
                        '<div class="timekeeping-alloc-field-label timekeeping-alloc-field-label-static">'
                        "Notes</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="timekeeping-alloc-cell">'
                        f"{html.escape(str(line.get('notes') or '—'))}</div>",
                        unsafe_allow_html=True,
                    )
                if not is_primary_row:
                    _render_allocation_row_secondary_actions(
                        deps=deps,
                        ctx=ctx,
                        line=line,
                        lix=lix,
                        lines=lines,
                        day_status=day_status,
                        row_editable=row_editable,
                    )
        elif is_primary_row:
            status_html = deps.alloc_autosave_status_html(iso)
            if status_html:
                st.markdown(
                    f'<div class="timekeeping-alloc-row-autosave timekeeping-alloc-row-autosave-compact">'
                    f"{status_html}</div>",
                    unsafe_allow_html=True,
                )
        elif not is_primary_row and row_editable:
            _render_allocation_row_secondary_actions(
                deps=deps,
                ctx=ctx,
                line=line,
                lix=lix,
                lines=lines,
                day_status=day_status,
                row_editable=row_editable,
            )

    line["hour_type"] = deps.normalize_alloc_hour_type(
        line.get("final_time_type") or line.get("hour_type") or "ST"
    )


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

    day_status_norm = normalize_timecard_status(ctx.day_status)
    approval_cls = allocation_day_approval_class(day_status_norm, alloc_state=state)
    scope = allocation_panel_scope_key(ctx.panel_scope)
    with st.container(key=f"tk_alloc_day_{scope}_{ctx.iso}", border=True):
        unbalanced_cls = (
            " timekeeping-alloc-day-unbalanced" if state == "overallocated" else ""
        )
        st.markdown(
            f'<span class="daily-allocation-card daily-allocation-card-marker '
            f"timekeeping-day-allocation-card-marker timekeeping-alloc-day-state-marker "
            f"timekeeping-alloc-day-state-{html.escape(state)}{unbalanced_cls} "
            f"{html.escape(approval_cls)} "
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
            hours_badge_text=ctx.daily_hours_label,
        )
        if ctx.daily_total <= 0:
            hint = (
                "Enter daily total hours above to add assignments."
                if ctx.modal_host
                else "Enter hours for this day in the row above before assigning."
            )
            st.caption(hint)
            return

        st.markdown(
            '<span class="timekeeping-alloc-day-form-body-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<span class="timekeeping-alloc-day-body-marker timekeeping-alloc-day-grid-marker" '
            'aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        for lix, line in enumerate(ctx.lines):
            render_allocation_control_row(
                deps=deps,
                ctx=ctx,
                line=line,
                lix=lix,
                normalize_timecard_status=normalize_timecard_status,
            )
        _render_day_actions_bar(
            deps=deps,
            ctx=ctx,
            normalize_timecard_status=normalize_timecard_status,
        )


def render_allocation_days_panel(*, panel_scope: str, compact: bool = False) -> Any:
    """Wrapper container for all day cards in one expanded employee row."""
    scope = allocation_panel_scope_key(panel_scope)
    compact_cls = " timekeeping-allocation-list-compact-marker" if compact else ""
    st.markdown(
        f'<span class="timekeeping-allocation-days-panel-marker{compact_cls}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    return st.container(key=f"tk_alloc_panel_{scope}")
