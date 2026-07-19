"""Scheduling module — plan jobs, crews, travel, and equipment assignments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode

import streamlit as st
from streamlit.runtime.fragment import fragment

from app.auth import current_profile, current_user_display_name, effective_role
from app.components.scheduling_calendar import (
    render_crew_schedule_table,
    render_day_agenda,
    render_equipment_schedule_table,
    render_jobs_schedule_grouped,
    render_week_calendar,
)
from app.components.scheduling_css import inject_scheduling_css
from app.components.scheduling_dialogs import (
    SCHED_FORM_KEY,
    SCHED_OPEN_DETAIL_KEY,
    open_new_schedule_dialog,
    open_schedule_detail,
    show_schedule_detail_dialog,
    show_schedule_event_dialog,
)
from app.components.scheduling_export_panel import clear_prepared_export, render_scheduling_export_panel
from app.components.scheduling_filters import render_scheduling_filters, show_unassigned_enabled
from app.components.scheduling_view_nav import (
    render_view_tabs,
    render_week_navigation,
    scheduling_view_modes,
)
from app.pages._core._access import begin_module
from app.perf_debug import perf_span
from app.services.scheduling_detail_service import get_schedule_event_detail
from app.services.scheduling_page_service import load_scheduling_page_snapshot
from app.services.scheduling_service import invalidate_scheduling_page_cache, monday_of, week_range
from app.ui.streamlit_perf import fragment_rerun, ips_app_rerun
from app.utils.permissions import normalize_role

_MODULE = "scheduling"
_VIEW_KEY = "scheduling_view_mode"
_WEEK_KEY = "scheduling_week_anchor"
_DAY_KEY = "scheduling_day_anchor"
_FILTERS_KEY = "scheduling_filters"
_SCHEDULE_DETAIL_QUERY_KEY = "schedule_detail"
_SCHEDULE_DETAIL_QUERY_ERROR_KEY = "_ips_schedule_detail_query_error"


@dataclass(frozen=True)
class SchedulingPermissions:
    role: str
    user_id: str
    user_name: str
    can_manage: bool
    can_create: bool
    can_edit: bool
    can_delete: bool
    can_export: bool


@dataclass(frozen=True)
class SchedulingRenderContext:
    today: date
    week_anchor: date
    week_start: date
    week_end: date
    selected_day: date
    view_mode: str
    filters: dict[str, str]
    permissions: SchedulingPermissions


def schedule_detail_href(event_id: str) -> str:
    params = urlencode({"ips_nav": _MODULE, _SCHEDULE_DETAIL_QUERY_KEY: str(event_id or "").strip()})
    return f"?{params}"


def _build_permissions() -> SchedulingPermissions:
    role = normalize_role(effective_role())
    profile = current_profile() or {}
    user_id = str(profile.get("id") or profile.get("employee_id") or "").strip()
    user_name = current_user_display_name()
    can_manage = role in {"admin", "supervisor", "project manager"}
    return SchedulingPermissions(
        role=role,
        user_id=user_id,
        user_name=user_name,
        can_manage=can_manage,
        can_create=can_manage,
        can_edit=can_manage,
        can_delete=can_manage,
        can_export=can_manage,
    )


def _week_anchor() -> date:
    raw = st.session_state.get(_WEEK_KEY)
    if isinstance(raw, date):
        return raw
    return monday_of(date.today())


def _view_mode() -> str:
    mode = str(st.session_state.get(_VIEW_KEY) or "Week").strip()
    return mode if mode in scheduling_view_modes() else "Week"


def _build_render_context(*, filters: dict[str, str]) -> SchedulingRenderContext:
    with perf_span("scheduling.context"):
        today = date.today()
        week_start, week_end = week_range(_week_anchor())
        selected_day = st.session_state.get(_DAY_KEY)
        if not isinstance(selected_day, date):
            selected_day = week_start
        return SchedulingRenderContext(
            today=today,
            week_anchor=week_start,
            week_start=week_start,
            week_end=week_end,
            selected_day=selected_day,
            view_mode=_view_mode(),
            filters=filters,
            permissions=_build_permissions(),
        )


def _capture_schedule_detail_query() -> bool:
    """Return True when detail fast path is active."""
    with perf_span("scheduling.detail_lookup"):
        requested_id = str(st.query_params.get(_SCHEDULE_DETAIL_QUERY_KEY) or "").strip()
        if not requested_id:
            return bool(st.session_state.get(SCHED_OPEN_DETAIL_KEY))

        current_id = str(st.session_state.get(SCHED_OPEN_DETAIL_KEY) or "").strip()
        if requested_id == current_id:
            return True

        detail = get_schedule_event_detail(requested_id)
        if not detail:
            st.session_state[_SCHEDULE_DETAIL_QUERY_ERROR_KEY] = requested_id
            if _SCHEDULE_DETAIL_QUERY_KEY in st.query_params:
                del st.query_params[_SCHEDULE_DETAIL_QUERY_KEY]
            return False

        open_schedule_detail(requested_id)
        st.session_state["_sched_detail_cache"] = detail
        return True


def _show_schedule_detail_query_error_if_any() -> None:
    if st.session_state.pop(_SCHEDULE_DETAIL_QUERY_ERROR_KEY, None):
        st.warning("The selected schedule event could not be found.")


def _open_event(event_id: str) -> None:
    open_schedule_detail(event_id)
    st.query_params[_SCHEDULE_DETAIL_QUERY_KEY] = str(event_id or "").strip()
    ips_app_rerun()


def _close_detail() -> None:
    st.session_state.pop(SCHED_OPEN_DETAIL_KEY, None)
    st.session_state.pop("_sched_detail_cache", None)
    if _SCHEDULE_DETAIL_QUERY_KEY in st.query_params:
        del st.query_params[_SCHEDULE_DETAIL_QUERY_KEY]


@fragment
def _render_scheduling_view_content(
    *,
    ctx: SchedulingRenderContext,
    snapshot,
    on_open_event,
) -> None:
    mode = ctx.view_mode
    if mode == "Week":
        with perf_span("scheduling.render.week"):
            render_week_calendar(
                snapshot.events,
                week_anchor=ctx.week_anchor,
                conflict_event_ids=snapshot.conflict_event_ids,
                on_open_event=on_open_event,
            )
    elif mode == "Day":
        st.date_input(
            "Day",
            value=ctx.selected_day,
            min_value=ctx.week_start,
            max_value=ctx.week_end - timedelta(days=1),
            key=_DAY_KEY,
        )
        with perf_span("scheduling.render.day"):
            render_day_agenda(
                snapshot.events,
                day=ctx.selected_day,
                conflict_event_ids=snapshot.conflict_event_ids,
                on_open_event=on_open_event,
            )
    elif mode == "Crew":
        with perf_span("scheduling.render.crew"):
            render_crew_schedule_table(
                snapshot.events,
                week_anchor=ctx.week_anchor,
                employees_by_id=snapshot.employees_by_id,
                employee_rows_by_event=snapshot.employee_assignments_by_event,
                show_unassigned=show_unassigned_enabled(),
                on_open_event=on_open_event,
            )
    elif mode == "Jobs":
        with perf_span("scheduling.render.jobs"):
            render_jobs_schedule_grouped(
                snapshot.events,
                jobs_by_id=snapshot.jobs_by_id,
                on_open_event=on_open_event,
            )
    elif mode == "Equipment":
        with perf_span("scheduling.render.equipment"):
            render_equipment_schedule_table(
                snapshot.events,
                assets_by_id=snapshot.assets_by_id,
                asset_rows_by_event=snapshot.asset_assignments_by_event,
                on_open_event=on_open_event,
            )


def render() -> None:
    if not begin_module(_MODULE):
        return

    inject_scheduling_css()
    permissions = _build_permissions()

    from app.ui.page_header import render_page_header

    def _new_event() -> None:
        open_new_schedule_dialog()
        ips_app_rerun()

    def _refresh() -> None:
        clear_prepared_export()
        invalidate_scheduling_page_cache(force=True)

    render_page_header(
        "Scheduling",
        "Plan jobs, crews, travel, and equipment assignments.",
        icon="📅",
        primary_action=_new_event if permissions.can_create else None,
        show_refresh=True,
        on_refresh=_refresh,
        primary_action_width=2.0,
    )

    _show_schedule_detail_query_error_if_any()
    detail_pending = _capture_schedule_detail_query()

    filt = render_scheduling_filters(filters_key=_FILTERS_KEY)

    if detail_pending:
        detail = st.session_state.get("_sched_detail_cache") or get_schedule_event_detail(
            str(st.session_state.get(SCHED_OPEN_DETAIL_KEY) or "").strip()
        )
        if detail:
            show_schedule_detail_dialog(
                jobs_by_id=detail.get("jobs_by_id") or {},
                employees_by_id=detail.get("employees_by_id") or {},
                assets_by_id=detail.get("assets_by_id") or {},
                detail_bundle=detail,
                permissions=permissions,
                on_close=_close_detail,
            )
        elif st.session_state.get(SCHED_OPEN_DETAIL_KEY):
            show_schedule_detail_dialog(
                jobs_by_id={},
                employees_by_id={},
                assets_by_id={},
                permissions=permissions,
                on_close=_close_detail,
            )
        return

    render_week_navigation(week_key=_WEEK_KEY, day_key=_DAY_KEY, on_week_change=clear_prepared_export)
    render_view_tabs(session_key=_VIEW_KEY, default="Week")
    ctx = _build_render_context(filters=filt)

    with st.spinner("Loading schedule…"):
        with perf_span("scheduling.page_shell"):
            snapshot = load_scheduling_page_snapshot(
                week_start=ctx.week_start,
                week_end=ctx.week_end,
                selected_day=ctx.selected_day,
                view_mode=ctx.view_mode,
                filters=ctx.filters,
                show_unassigned=show_unassigned_enabled(),
            )

    if snapshot.warning:
        st.warning(snapshot.warning)

    render_scheduling_export_panel(
        events=snapshot.events,
        week_start=ctx.week_start,
        filters=ctx.filters,
        jobs_by_id=snapshot.jobs_by_id,
        employees_by_id=snapshot.employees_by_id,
        employee_rows_by_event=snapshot.employee_assignments_by_event,
        can_export=permissions.can_export,
    )

    with st.container(key="scheduling_page_wrap"):
        _render_scheduling_view_content(ctx=ctx, snapshot=snapshot, on_open_event=_open_event)

    if st.session_state.get(SCHED_FORM_KEY):
        with perf_span("scheduling.dialog_options"):
            show_schedule_event_dialog(permissions=permissions)

    if st.session_state.get(SCHED_OPEN_DETAIL_KEY):
        show_schedule_detail_dialog(
            jobs_by_id=snapshot.jobs_by_id,
            employees_by_id=snapshot.employees_by_id,
            assets_by_id=snapshot.assets_by_id,
            permissions=permissions,
            on_close=_close_detail,
        )
