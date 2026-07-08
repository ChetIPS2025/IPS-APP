"""Shared HTML jobs table (list page) and click bridge."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.components.job_status_ui import job_status_pill_html, job_status_table_label
    from app.services.jobs_service import can_manage_job_actions
except ImportError:
    from components.job_status_ui import job_status_pill_html, job_status_table_label  # type: ignore
    from services.jobs_service import can_manage_job_actions  # type: ignore

JOBS_TABLE_LAST_ACTION_KEY = "jobs_list_last_action"
JOBS_TABLE_PENDING_STATUS_KEY = "jobs_table_pending_status_id"
JOBS_TABLE_PENDING_MENU_KEY = "jobs_table_pending_menu_id"

JOBS_TABLE_HEADER_LABELS: dict[str, str] = {
    "num": "JOB #",
    "desc": "PROJECT / DESCRIPTION",
    "customer": "CUSTOMER",
    "status": "STATUS",
    "estimated": "ESTIMATED COST",
    "actual": "ACTUAL COST",
    "actions": "ACTIONS",
}

JOBS_TABLE_COL_WIDTHS_PX: dict[str, int] = {
    "num": 96,
    "desc": 260,
    "customer": 180,
    "status": 120,
    "estimated": 108,
    "actual": 108,
    "actions": 132,
}


def _job_is_archived(job: dict[str, Any]) -> bool:
    if bool(job.get("is_deleted")):
        return True
    status = str(job.get("status") or "").strip().lower()
    return status in {"deleted", "archived"}


def can_show_job_status_action(job: dict[str, Any]) -> bool:
    jid = str(job.get("id") or "").strip()
    if not jid or _job_is_archived(job):
        return False
    return can_manage_job_actions()


def job_list_link_html(
    job_id: str,
    label: str,
    *,
    extra_class: str = "",
) -> str:
    jid = html.escape(str(job_id or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    cls = f"ips-dash-est-link ips-jobs-list-link {extra_class}".strip()
    return (
        f'<a href="#" class="{html.escape(cls)}" data-job-action="open" '
        f'data-job-id="{jid}" title="{title}">{text}</a>'
    )


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def _money_cell(value: float, *, available: bool = True) -> str:
    if not available:
        return "—"
    if abs(float(value or 0)) < 0.005:
        return "—"
    return f"${float(value):,.2f}"


def _money_cell_class(value: float, *, available: bool = True) -> str:
    return " ips-jobs-money-empty" if _money_cell(value, available=available) == "—" else ""


def _actual_cost_cell_html(
    actual_val: float,
    *,
    estimated_val: float,
    has_actual: bool,
    has_estimated: bool,
) -> str:
    display = _money_cell(actual_val, available=has_actual)
    empty_cls = _money_cell_class(actual_val, available=has_actual)
    over = (
        has_actual
        and has_estimated
        and float(estimated_val or 0) > 0
        and float(actual_val or 0) > float(estimated_val or 0)
    )
    over_cls = " ips-jobs-actual-over-estimate" if over else ""
    warn = ""
    if over:
        warn = (
            '<span class="ips-jobs-actual-over-icon" '
            'title="Actual cost has exceeded the estimated cost." '
            'aria-label="Actual cost has exceeded the estimated cost.">⚠</span>'
        )
    return (
        f'<div class="ips-jobs-money ips-jobs-cell ips-jobs-col-money ips-jobs-money-actual'
        f"{empty_cls}{over_cls}\">"
        f"{html.escape(display)}{warn}</div>"
    )


def _actions_html(
    job_id: str,
    *,
    show_status: bool,
    show_menu: bool,
    field_mode: bool = False,
    expanded: bool = False,
) -> str:
    jid = html.escape(str(job_id or "").strip(), quote=True)
    parts: list[str] = []
    if field_mode:
        expand_label = "▾" if expanded else "▸"
        parts.append(
            f'<button type="button" class="ips-dash-est-action ips-dash-est-approve ips-jobs-expand-btn" '
            f'data-job-action="expand" data-job-id="{jid}" title="Expand job details">'
            f"{html.escape(expand_label)}</button>"
        )
    if show_status:
        parts.append(
            f'<button type="button" class="ips-dash-est-action ips-dash-est-approve" '
            f'data-job-action="status" data-job-id="{jid}">Status</button>'
        )
    if show_menu:
        parts.append(
            f'<button type="button" class="ips-dash-est-action ips-dash-est-view" '
            f'data-job-action="menu" data-job-id="{jid}">Actions</button>'
        )
    if not parts:
        return ""
    return f'<div class="ips-dash-est-actions">{"".join(parts)}</div>'


def build_jobs_html_table(
    rows: list[dict[str, Any]],
    *,
    visible_markers: tuple[str, ...],
    cost_fields_fn: Callable[[dict[str, Any]], dict[str, Any]],
    health_badge_fn: Callable[[dict[str, Any]], str] | None = None,
    field_mode: bool = False,
    expanded_job_id: str = "",
) -> str:
    columns: list[str] = [marker for marker in visible_markers if marker in JOBS_TABLE_HEADER_LABELS]
    if "actions" not in columns:
        columns.append("actions")

    col_parts = [
        (
            f'<col class="ips-dash-est-col-{html.escape(key)}" '
            f'style="width:{JOBS_TABLE_COL_WIDTHS_PX[key]}px;" />'
        )
        for key in columns
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{JOBS_TABLE_COL_WIDTHS_PX[key]}px;'
            f'max-width:{JOBS_TABLE_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(JOBS_TABLE_HEADER_LABELS[key])}</th>"
        )
        for key in columns
    ]

    body_rows: list[str] = []
    for row_idx, job in enumerate(rows):
        jid = str(job.get("id") or "").strip()
        if not jid:
            continue

        costs = cost_fields_fn(job)
        estimated_val = float(costs.get("estimated_cost") or 0)
        actual_val = float(costs.get("actual_cost") or 0)
        has_estimated = bool(costs.get("has_estimated"))
        has_actual = bool(costs.get("has_actual"))
        raw_summary = costs.get("raw_summary")
        health_html = ""
        if health_badge_fn is not None and isinstance(raw_summary, dict) and raw_summary:
            health_html = health_badge_fn(raw_summary)

        job_no = "—"
        for key in ("job_number", "number"):
            val = str(job.get(key) or "").strip()
            if val:
                job_no = val
                break
        project = "—"
        for key in ("job_name", "project_name", "project_description", "description"):
            val = str(job.get(key) or "").strip()
            if val:
                project = val
                break
        customer = "—"
        for key in ("customer_name", "customer"):
            val = str(job.get(key) or "").strip()
            if val:
                customer = val
                break

        num_label = job_no if job_no and job_no != "—" else "View job"
        title_label = project if project and project != "—" else "View job"
        row_parity = "even" if row_idx % 2 else "odd"
        expanded = field_mode and expanded_job_id == jid

        cell_builders: dict[str, tuple[str, str]] = {
            "num": (
                "left",
                _cell_wrapper(
                    job_list_link_html(jid, num_label, extra_class="ips-dash-est-num-link"),
                    extra_class="ips-dash-est-num-cell",
                ),
            ),
            "desc": (
                "left",
                _cell_wrapper(
                    job_list_link_html(jid, title_label, extra_class="ips-dash-est-desc-link"),
                    extra_class="ips-dash-est-desc-cell",
                ),
            ),
            "customer": (
                "left",
                _cell_wrapper(
                    html.escape(customer),
                    extra_class="ips-dash-est-customer-cell",
                ),
            ),
            "status": (
                "center",
                _cell_wrapper(
                    job_status_pill_html(job_status_table_label(job.get("status"))) + health_html,
                    extra_class="ips-dash-est-status-cell ips-jobs-status-stack",
                    align="center",
                ),
            ),
            "estimated": (
                "right",
                _cell_wrapper(
                    (
                        f'<div class="ips-jobs-money ips-jobs-cell ips-jobs-col-money'
                        f'{_money_cell_class(estimated_val, available=has_estimated)}">'
                        f"{html.escape(_money_cell(estimated_val, available=has_estimated))}</div>"
                    ),
                    extra_class="ips-dash-est-total-cell",
                    align="right",
                ),
            ),
            "actual": (
                "right",
                _cell_wrapper(
                    _actual_cost_cell_html(
                        actual_val,
                        estimated_val=estimated_val,
                        has_actual=has_actual,
                        has_estimated=has_estimated,
                    ),
                    extra_class="ips-dash-est-total-cell",
                    align="right",
                ),
            ),
            "actions": (
                "right",
                _cell_wrapper(
                    _actions_html(
                        jid,
                        show_status=can_show_job_status_action(job),
                        show_menu=True,
                        field_mode=field_mode,
                        expanded=expanded,
                    ),
                    extra_class="ips-dash-est-actions-cell",
                    align="right",
                ),
            ),
        }

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{JOBS_TABLE_COL_WIDTHS_PX[key]}px;'
                f'max-width:{JOBS_TABLE_COL_WIDTHS_PX[key]}px;">'
                f"{cell_builders[key][1]}</td>"
            )
            for key in columns
            if key in cell_builders
        )
        body_rows.append(
            f'<tr class="ips-dash-est-tr ips-dash-est-row-{row_parity}" data-job-id="{html.escape(jid, quote=True)}">'
            f"{tds}"
            f"</tr>"
        )

    min_width = sum(JOBS_TABLE_COL_WIDTHS_PX[key] for key in columns)
    return (
        f'<div class="ips-dash-est-table-scroll" style="min-width:0;">'
        f'<table class="ips-dash-est-html-table" style="min-width:{min_width}px;">'
        f"<colgroup>{''.join(col_parts)}</colgroup>"
        f'<thead><tr class="ips-dash-est-tr ips-dash-est-head-row">{"".join(head_parts)}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )


def handle_jobs_table_action(
    raw: str,
    jobs_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str,
    open_job_fn: Callable[[str, dict[str, Any]], None],
    pending_status_key: str = JOBS_TABLE_PENDING_STATUS_KEY,
    pending_menu_key: str = JOBS_TABLE_PENDING_MENU_KEY,
    on_expand_fn: Callable[[str, dict[str, Any]], None] | None = None,
) -> None:
    val = str(raw or "").strip()
    if not val:
        return
    if val == str(st.session_state.get(last_action_key) or ""):
        return
    st.session_state[last_action_key] = val

    if val.startswith("status:"):
        job_id = val.split(":", 1)[1].strip()
        if job_id in jobs_by_id:
            st.session_state[pending_status_key] = job_id
            st.session_state.pop(pending_menu_key, None)
            st.rerun()
        return

    if val.startswith("menu:"):
        job_id = val.split(":", 1)[1].strip()
        if job_id in jobs_by_id:
            st.session_state[pending_menu_key] = job_id
            st.session_state.pop(pending_status_key, None)
            st.rerun()
        return

    if val.startswith("expand:"):
        job_id = val.split(":", 1)[1].strip()
        job = jobs_by_id.get(job_id)
        if job and on_expand_fn is not None:
            on_expand_fn(job_id, job)
            st.rerun()
        return

    job_id = val.split(":", 1)[1].strip() if val.startswith("open:") else val
    if not job_id:
        return
    open_job = jobs_by_id.get(job_id)
    if not open_job:
        return
    st.session_state.pop(pending_status_key, None)
    st.session_state.pop(pending_menu_key, None)
    open_job_fn(job_id, open_job)


def render_jobs_table_bridge(
    jobs_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str = "ips_jobs_list_bridge",
    hook_key: str = "ipsJobsList::action",
    last_action_key: str = JOBS_TABLE_LAST_ACTION_KEY,
    pending_status_key: str = JOBS_TABLE_PENDING_STATUS_KEY,
    pending_menu_key: str = JOBS_TABLE_PENDING_MENU_KEY,
    open_job_fn: Callable[[str, dict[str, Any]], None],
    on_expand_fn: Callable[[str, dict[str, Any]], None] | None = None,
) -> None:
    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore

    picked = _components_html(
        f"""
<script>
(function () {{
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = {hook_key!r};
  const sel = "[data-job-id][data-job-action]";

  function sendValue(action) {{
    const payload = {{ type: "streamlit:setComponentValue", value: action }};
    const frames = [window, window.parent, w].filter(function (f, i, arr) {{
      return f && arr.indexOf(f) === i;
    }});
    for (var i = 0; i < frames.length; i++) {{
      try {{
        if (frames[i].Streamlit && typeof frames[i].Streamlit.setComponentValue === "function") {{
          frames[i].Streamlit.setComponentValue(action);
          return;
        }}
      }} catch (err) {{}}
    }}
    for (var j = 0; j < frames.length; j++) {{
      try {{ frames[j].postMessage(payload, "*"); }} catch (err) {{}}
    }}
  }}

  function bindTargets() {{
    doc.querySelectorAll(sel).forEach(function (el) {{
      if (el.dataset.ipsJobsTableBound === "1") return;
      el.dataset.ipsJobsTableBound = "1";
      el.addEventListener("click", function (e) {{
        e.preventDefault();
        e.stopPropagation();
        const id = el.getAttribute("data-job-id");
        const action = el.getAttribute("data-job-action") || "open";
        if (!id) return;
        sendValue(action + ":" + id);
      }});
    }});
  }}

  if (!doc.ipsJobsTableRegistry) doc.ipsJobsTableRegistry = {{}};
  doc.ipsJobsTableRegistry[hookKey] = {{ bind: bindTargets }};
  bindTargets();
  if (!doc.ipsJobsTableBindObserver) {{
    doc.ipsJobsTableBindObserver = new MutationObserver(function () {{
      Object.values(doc.ipsJobsTableRegistry || {{}}).forEach(function (cfg) {{
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      }});
    }});
    doc.ipsJobsTableBindObserver.observe(doc.body, {{ childList: true, subtree: true }});
  }}
}})();
</script>
        """,
        component_key=component_key,
        height=0,
    )
    action = str(picked or "").strip()
    if action:
        handle_jobs_table_action(
            action,
            jobs_by_id,
            last_action_key=last_action_key,
            pending_status_key=pending_status_key,
            pending_menu_key=pending_menu_key,
            open_job_fn=open_job_fn,
            on_expand_fn=on_expand_fn,
        )


def render_jobs_table_link_bridge(
    jobs_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str = "ips_jobs_list_bridge",
    hook_key: str = "ipsJobsList::action",
    last_action_key: str = JOBS_TABLE_LAST_ACTION_KEY,
    open_job_fn: Callable[[str, dict[str, Any]], None],
) -> None:
    """Backward-compatible alias for the unified jobs table bridge."""
    render_jobs_table_bridge(
        jobs_by_id,
        component_key=component_key,
        hook_key=hook_key,
        last_action_key=last_action_key,
        open_job_fn=open_job_fn,
    )


def resolve_jobs_table_link_action(
    action: str | None,
    jobs_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    job_id = str(action or "").strip()
    if job_id.startswith("open:"):
        job_id = job_id.split(":", 1)[1].strip()
    if not job_id:
        return None
    return jobs_by_id.get(job_id)
