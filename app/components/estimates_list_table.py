"""Shared HTML estimates table (dashboard + estimates list page)."""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.auth import current_role, effective_role
    from app.pages._core._crud import is_demo_id
    from app.services.estimate_job_workflow_service import (
        can_approve_estimates,
        estimate_status_approvable,
        estimate_visible_in_approved_view,
    )
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from auth import current_role, effective_role  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from services.estimate_job_workflow_service import (  # type: ignore
        can_approve_estimates,
        estimate_status_approvable,
        estimate_visible_in_approved_view,
    )
    from utils.formatting import fmt_currency, fmt_date  # type: ignore

ESTIMATES_LIST_TABLE_HEADERS: tuple[tuple[str, str], ...] = (
    ("num", "ESTIMATE #"),
    ("desc", "PROJECT / DESCRIPTION"),
    ("customer", "CUSTOMER"),
    ("status", "STATUS"),
    ("total", "TOTAL / CONTRACT VALUE"),
    ("actions", "ACTIONS"),
)

ESTIMATES_DASHBOARD_TABLE_HEADERS: tuple[tuple[str, str], ...] = (
    ("num", "ESTIMATE #"),
    ("desc", "PROJECT / DESCRIPTION"),
    ("customer", "CUSTOMER"),
    ("date", "ESTIMATE DATE"),
    ("total", "TOTAL"),
    ("status", "STATUS"),
    ("actions", "ACTIONS"),
)

# Backward-compatible alias for dashboard callers.
ESTIMATES_TABLE_HEADERS = ESTIMATES_DASHBOARD_TABLE_HEADERS

ESTIMATES_LIST_COL_WIDTHS_PX: dict[str, int] = {
    "num": 96,
    "desc": 240,
    "customer": 160,
    "status": 112,
    "total": 104,
    "actions": 132,
}

ESTIMATES_TABLE_COL_WIDTHS_PX: dict[str, int] = {
    "num": 96,
    "desc": 260,
    "customer": 180,
    "date": 118,
    "total": 108,
    "status": 96,
    "actions": 148,
}

ESTIMATES_TABLE_LAST_ACTION_KEY = "estimates_list_last_action"
ESTIMATES_MODE_KEY = "estimates_mode"
ESTIMATES_SELECTED_ID_KEY = "selected_estimate_id"

_ESTIMATES_LIST_COL_RATIOS = tuple(ESTIMATES_LIST_COL_WIDTHS_PX.values())


def normalize_estimate_status(raw: object) -> str:
    s = str(raw or "").strip().lower().replace("_", " ")
    mapping = {
        "": "Draft",
        "draft": "Draft",
        "pending": "Pending",
        "sent": "Sent",
        "approved": "Approved",
        "awarded": "Awarded",
        "rejected": "Rejected",
        "expired": "Expired",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
        "ready for approval": "Pending",
        "awaiting approval": "Pending",
    }
    if s in mapping:
        return mapping[s]
    label = str(raw or "").strip()
    return label if label else "Draft"


def estimate_status_pill_html(status: str) -> str:
    cls_map = {
        "Draft": "ips-estimate-status-draft",
        "Pending": "ips-estimate-status-pending",
        "Sent": "ips-estimate-status-sent",
        "Approved": "ips-estimate-status-approved",
        "Awarded": "ips-estimate-status-awarded",
        "Rejected": "ips-estimate-status-rejected",
        "Expired": "ips-estimate-status-expired",
        "Cancelled": "ips-estimate-status-cancelled",
    }
    cls = cls_map.get(status, "ips-estimate-status-draft")
    return f'<span class="ips-estimate-status-pill {cls}">{html.escape(status)}</span>'


def estimate_number(row: dict[str, Any]) -> str:
    val = str(
        row.get("estimate_number") or row.get("number") or row.get("quote_number") or ""
    ).strip()
    return val or "—"


def estimate_project(row: dict[str, Any]) -> str:
    try:
        from app.services.phase2_modules_service import estimate_project_title
    except ImportError:
        from services.phase2_modules_service import estimate_project_title  # type: ignore
    return estimate_project_title(row)


def estimate_customer(row: dict[str, Any]) -> str:
    for key in ("customer_name", "customer"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def estimate_total_display(row: dict[str, Any]) -> str:
    for key in ("customer_price", "total", "grand_total", "proposal_total", "subtotal"):
        val = row.get(key)
        if val in (None, ""):
            continue
        try:
            amount = float(val)
        except (TypeError, ValueError):
            continue
        if amount != 0:
            return fmt_currency(amount)
    return fmt_currency(0)


def filter_waiting_approval_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if estimate_visible_in_approved_view(row):
            continue
        if row.get("archived_from_estimates") is True:
            continue
        if estimate_status_approvable(row.get("status")):
            out.append(row)
    return out


def can_show_approve_action(row: dict[str, Any]) -> bool:
    if not can_approve_estimates(effective_role()):
        return False
    eid = str(row.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return False
    return estimate_status_approvable(row.get("status")) and not estimate_visible_in_approved_view(row)


def build_approve_flags(rows: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        str(row.get("id") or "").strip(): can_show_approve_action(row)
        for row in rows
        if str(row.get("id") or "").strip()
    }


def build_approved_flags(rows: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        str(row.get("id") or "").strip(): estimate_visible_in_approved_view(row)
        for row in rows
        if str(row.get("id") or "").strip()
    }


def estimates_bridge_button_key(row: dict[str, Any]) -> str:
    raw = str(row.get("id") or row.get("estimate_number") or "estimate").strip()
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw) or "estimate"
    return f"est_bridge_open_{safe}"


def estimate_list_link_html(
    estimate_id: str,
    label: str,
    *,
    extra_class: str = "",
    bridge_key: str = "",
) -> str:
    eid = html.escape(str(estimate_id or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    cls = f"ips-row-open-link ips-dash-est-link ips-estimates-list-link ips-estimates-open-link {extra_class}".strip()
    bridge_attr = ""
    if bridge_key:
        bridge_attr = f' data-bridge-key="{html.escape(bridge_key, quote=True)}"'
    return (
        f'<button type="button" class="{html.escape(cls)}" '
        f'data-row-id="{eid}" data-estimate-id="{eid}" data-est-action="open"{bridge_attr} '
        f'title="{title}">{text}</button>'
    )


def _estimate_link_html(eid: str, label: str, *, extra_class: str = "") -> str:
    return estimate_list_link_html(eid, label, extra_class=extra_class)


def _actions_html(eid: str, *, show_approve: bool, show_approved_label: bool) -> str:
    est_id = html.escape(str(eid or "").strip(), quote=True)
    view_btn = (
        f'<button type="button" class="ips-dash-est-action ips-dash-est-view" '
        f'data-est-action="open" data-estimate-id="{est_id}">View</button>'
    )
    if show_approve:
        approve_btn = (
            f'<button type="button" class="ips-dash-est-action ips-dash-est-approve" '
            f'data-est-action="approve" data-estimate-id="{est_id}">Approve</button>'
        )
        inner = f"{approve_btn}{view_btn}"
    elif show_approved_label:
        inner = (
            '<span class="ips-est-approve-done">Job Approved</span>'
            f"{view_btn}"
        )
    else:
        inner = view_btn
    return f'<div class="ips-dash-est-actions">{inner}</div>'


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def open_estimate_detail(estimate_id: str) -> None:
    """Navigate to the Estimates page inline detail view using the estimate primary key."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    st.session_state[ESTIMATES_SELECTED_ID_KEY] = eid
    st.session_state[ESTIMATES_MODE_KEY] = "detail"
    st.session_state["show_estimate_detail_modal"] = False


def render_estimates_list_table_header() -> None:
    labels = [label for _key, label in ESTIMATES_LIST_TABLE_HEADERS]
    cols = st.columns(list(_ESTIMATES_LIST_COL_RATIOS), gap="small")
    for col, label in zip(cols, labels):
        with col:
            st.markdown(
                f'<div class="ips-estimates-sl-th">{html.escape(label)}</div>',
                unsafe_allow_html=True,
            )


def render_estimates_list_table_body(
    rows: list[dict[str, Any]],
    *,
    approve_flags: dict[str, bool],
    approved_flags: dict[str, bool] | None = None,
    pending_approve_key: str = "est_pending_approve_id",
) -> None:
    """Estimates list rows with Streamlit open buttons for estimate # and project/description."""
    approved_lookup = approved_flags or {}
    st.markdown('<div class="ips-estimates-sl-table-body">', unsafe_allow_html=True)
    for row_idx, est in enumerate(rows):
        eid = str(est.get("id") or "").strip()
        if not eid:
            continue

        est_no = estimate_number(est)
        project = estimate_project(est)
        customer = estimate_customer(est)
        status = normalize_estimate_status(est.get("status"))
        total = estimate_total_display(est)
        num_label = est_no if est_no and est_no != "—" else "Estimate"
        title_label = str(
            est.get("project_description")
            or est.get("description")
            or estimate_project(est)
            or ""
        ).strip() or "Untitled Estimate"
        row_parity = "even" if row_idx % 2 else "odd"

        st.markdown(
            f'<div class="ips-estimates-sl-row ips-estimates-sl-row-{row_parity}" '
            f'data-estimate-id="{html.escape(eid, quote=True)}"></div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(list(_ESTIMATES_LIST_COL_RATIOS), gap="small")

        with cols[0]:
            if st.button(
                num_label,
                key=f"open_est_num_{eid}",
                type="tertiary",
            ):
                open_estimate_detail(eid)
                st.rerun()

        with cols[1]:
            if st.button(
                title_label,
                key=f"open_est_desc_{eid}",
                type="tertiary",
            ):
                open_estimate_detail(eid)
                st.rerun()

        with cols[2]:
            st.markdown(
                f'<div class="ips-estimates-sl-cell ips-estimates-sl-customer">{html.escape(customer)}</div>',
                unsafe_allow_html=True,
            )

        with cols[3]:
            st.markdown(
                f'<div class="ips-estimates-sl-cell ips-estimates-sl-status">'
                f"{estimate_status_pill_html(status)}</div>",
                unsafe_allow_html=True,
            )

        with cols[4]:
            st.markdown(
                f'<div class="ips-estimates-sl-cell ips-estimates-sl-total">{html.escape(total)}</div>',
                unsafe_allow_html=True,
            )

        with cols[5]:
            show_approve = approve_flags.get(eid, False)
            show_approved_label = approved_lookup.get(eid, False)
            if show_approve or show_approved_label:
                action_cols = st.columns(2, gap="small")
                if show_approve:
                    with action_cols[0]:
                        if st.button(
                            "Approve",
                            key=f"est_approve_{eid}",
                            type="secondary",
                        ):
                            st.session_state[pending_approve_key] = eid
                            st.rerun()
                elif show_approved_label:
                    with action_cols[0]:
                        st.markdown(
                            '<span class="ips-est-approve-done">Job Approved</span>',
                            unsafe_allow_html=True,
                        )
                with action_cols[1]:
                    if st.button(
                        "View",
                        key=f"open_est_view_{eid}",
                        type="secondary",
                    ):
                        open_estimate_detail(eid)
                        st.rerun()
            elif st.button(
                "View",
                key=f"open_est_view_{eid}",
                type="secondary",
            ):
                open_estimate_detail(eid)
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def build_estimates_html_table(
    rows: list[dict[str, Any]],
    *,
    approve_flags: dict[str, bool],
    approved_flags: dict[str, bool] | None = None,
    total_fn: Callable[[dict[str, Any]], str] | None = None,
    layout: str = "dashboard",
) -> str:
    approved_lookup = approved_flags or {}
    format_total = total_fn or estimate_total_display
    if layout == "list":
        headers = ESTIMATES_LIST_TABLE_HEADERS
        widths = ESTIMATES_LIST_COL_WIDTHS_PX
    else:
        headers = ESTIMATES_DASHBOARD_TABLE_HEADERS
        widths = ESTIMATES_TABLE_COL_WIDTHS_PX
    col_parts = [
        f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in widths.items()
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{widths[key]}px;max-width:{widths[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in headers
    ]

    body_rows: list[str] = []
    for row_idx, est in enumerate(rows):
        eid = str(est.get("id") or "").strip()
        if not eid:
            continue

        est_no = estimate_number(est)
        project = estimate_project(est)
        customer = estimate_customer(est)
        status = normalize_estimate_status(est.get("status"))
        est_date = fmt_date(str(est.get("estimate_date") or "")[:10]) if est.get("estimate_date") else "—"
        total = format_total(est)
        num_label = est_no if est_no and est_no != "—" else "Open estimate"
        title_label = project if project and project != "—" else "Open estimate"
        row_parity = "even" if row_idx % 2 else "odd"
        bridge_key = estimates_bridge_button_key(est)

        if layout == "list":
            cells = [
                (
                    "num",
                    "left",
                    _cell_wrapper(
                        estimate_list_link_html(
                            eid,
                            num_label,
                            extra_class="ips-dash-est-num-link",
                            bridge_key=bridge_key,
                        ),
                        extra_class="ips-dash-est-num-cell",
                    ),
                ),
                (
                    "desc",
                    "left",
                    _cell_wrapper(
                        estimate_list_link_html(
                            eid,
                            title_label,
                            extra_class="ips-dash-est-desc-link",
                            bridge_key=bridge_key,
                        ),
                        extra_class="ips-dash-est-desc-cell",
                    ),
                ),
                (
                    "customer",
                    "left",
                    _cell_wrapper(html.escape(customer), extra_class="ips-dash-est-customer-cell"),
                ),
                (
                    "status",
                    "center",
                    _cell_wrapper(
                        estimate_status_pill_html(status),
                        extra_class="ips-dash-est-status-cell",
                        align="center",
                    ),
                ),
                (
                    "total",
                    "right",
                    _cell_wrapper(
                        html.escape(total),
                        extra_class="ips-dash-est-total-cell",
                        align="right",
                    ),
                ),
                (
                    "actions",
                    "right",
                    _cell_wrapper(
                        _actions_html(
                            eid,
                            show_approve=approve_flags.get(eid, False),
                            show_approved_label=approved_lookup.get(eid, False),
                        ),
                        extra_class="ips-dash-est-actions-cell",
                        align="right",
                    ),
                ),
            ]
        else:
            cells = [
                (
                    "num",
                    "left",
                    _cell_wrapper(
                        _estimate_link_html(eid, num_label, extra_class="ips-dash-est-num-link"),
                        extra_class="ips-dash-est-num-cell",
                    ),
                ),
                (
                    "desc",
                    "left",
                    _cell_wrapper(
                        _estimate_link_html(eid, title_label, extra_class="ips-dash-est-desc-link"),
                        extra_class="ips-dash-est-desc-cell",
                    ),
                ),
                (
                    "customer",
                    "left",
                    _cell_wrapper(html.escape(customer), extra_class="ips-dash-est-customer-cell"),
                ),
                (
                    "date",
                    "left",
                    _cell_wrapper(html.escape(est_date), extra_class="ips-dash-est-date-cell"),
                ),
                (
                    "total",
                    "right",
                    _cell_wrapper(
                        html.escape(total),
                        extra_class="ips-dash-est-total-cell",
                        align="right",
                    ),
                ),
                (
                    "status",
                    "center",
                    _cell_wrapper(
                        estimate_status_pill_html(status),
                        extra_class="ips-dash-est-status-cell",
                        align="center",
                    ),
                ),
                (
                    "actions",
                    "right",
                    _cell_wrapper(
                        _actions_html(
                            eid,
                            show_approve=approve_flags.get(eid, False),
                            show_approved_label=approved_lookup.get(eid, False),
                        ),
                        extra_class="ips-dash-est-actions-cell",
                        align="right",
                    ),
                ),
            ]

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{widths[key]}px;max-width:{widths[key]}px;">'
                f"{content}</td>"
            )
            for key, _align, content in cells
        )
        body_rows.append(
            f'<tr class="ips-dash-est-tr ips-dash-est-row-{row_parity}" data-estimate-id="{html.escape(eid, quote=True)}">'
            f"{tds}"
            f"</tr>"
        )

    return (
        '<div class="ips-dash-est-table-scroll">'
        '<table class="ips-dash-est-html-table">'
        f"<colgroup>{''.join(col_parts)}</colgroup>"
        f'<thead><tr class="ips-dash-est-tr ips-dash-est-head-row">{"".join(head_parts)}</tr></thead>'
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )


def handle_estimates_table_action(
    raw: str,
    estimates_by_id: dict[str, dict[str, Any]],
    *,
    last_action_key: str,
    pending_approve_key: str = "est_pending_approve_id",
    open_estimate_fn: Callable[[str, dict[str, Any] | None], None] | None = None,
) -> None:
    val = str(raw or "").strip()
    if not val:
        return
    if val == str(st.session_state.get(last_action_key) or ""):
        return
    st.session_state[last_action_key] = val

    if val.startswith("approve:"):
        eid = val.split(":", 1)[1].strip()
        if eid not in estimates_by_id:
            return
        st.session_state[pending_approve_key] = eid
        st.rerun()
        return

    eid = val.split(":", 1)[1].strip() if val.startswith("open:") else val
    if not eid or eid not in estimates_by_id:
        return
    if open_estimate_fn is not None:
        open_estimate_fn(eid, estimates_by_id.get(eid))
        st.rerun()
        return
    try:
        from app.navigation import navigate_to_estimate_detail
    except ImportError:
        from navigation import navigate_to_estimate_detail  # type: ignore
    navigate_to_estimate_detail(eid)
    st.rerun()


def render_estimates_table_open_buttons(
    estimates: list[dict[str, Any]],
    *,
    open_estimate_fn: Callable[[str, dict[str, Any] | None], None],
) -> None:
    """Hidden Streamlit buttons — HTML link clicks trigger these via the bridge script."""
    with st.container(key="estimates_open_button_harness"):
        for est in estimates:
            eid = str(est.get("id") or "").strip()
            if not eid:
                continue
            bridge_key = estimates_bridge_button_key(est)

            def _open(_eid: str = eid, _est: dict = est) -> None:
                open_estimate_fn(_eid, _est)

            st.button(
                "Open estimate",
                key=bridge_key,
                type="tertiary",
                on_click=_open,
            )


def render_estimates_table_bridge(
    estimates_by_id: dict[str, dict[str, Any]],
    *,
    component_key: str,
    hook_key: str,
    last_action_key: str,
    pending_approve_key: str = "est_pending_approve_id",
    open_estimate_fn: Callable[[str, dict[str, Any] | None], None] | None = None,
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
  const sel = "[data-estimate-id][data-est-action]";

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
      if (el.dataset.ipsEstTableBound === "1") return;
      el.dataset.ipsEstTableBound = "1";
      el.addEventListener("click", function (e) {{
        e.preventDefault();
        e.stopPropagation();
        const id = el.getAttribute("data-estimate-id");
        const action = el.getAttribute("data-est-action") || "open";
        if (!id) return;
        sendValue(action + ":" + id);
      }});
    }});
  }}

  if (!doc.ipsEstTableRegistry) doc.ipsEstTableRegistry = {{}};
  doc.ipsEstTableRegistry[hookKey] = {{ bind: bindTargets }};
  bindTargets();
  if (!doc.ipsEstTableBindObserver) {{
    doc.ipsEstTableBindObserver = new MutationObserver(function () {{
      Object.values(doc.ipsEstTableRegistry || {{}}).forEach(function (cfg) {{
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      }});
    }});
    doc.ipsEstTableBindObserver.observe(doc.body, {{ childList: true, subtree: true }});
  }}
}})();
</script>
        """,
        component_key=component_key,
        height=0,
    )
    action = str(picked or "").strip()
    if action:
        handle_estimates_table_action(
            action,
            estimates_by_id,
            last_action_key=last_action_key,
            pending_approve_key=pending_approve_key,
            open_estimate_fn=open_estimate_fn,
        )
