"""Estimates Waiting Approval table for the operations dashboard (UI only)."""

from __future__ import annotations

import html
from typing import Any

import streamlit as st

try:
    from app.auth import current_role
    from app.pages._core._crud import is_demo_id
    from app.services.estimate_job_workflow_service import (
        can_approve_estimates,
        estimate_status_approvable,
        estimate_visible_in_approved_view,
    )
    from app.utils.formatting import fmt_currency, fmt_date
except ImportError:
    from auth import current_role  # type: ignore
    from pages._core._crud import is_demo_id  # type: ignore
    from services.estimate_job_workflow_service import (  # type: ignore
        can_approve_estimates,
        estimate_status_approvable,
        estimate_visible_in_approved_view,
    )
    from utils.formatting import fmt_currency, fmt_date  # type: ignore

_DASH_HEADERS: tuple[tuple[str, str], ...] = (
    ("num", "ESTIMATE #"),
    ("desc", "PROJECT / DESCRIPTION"),
    ("customer", "CUSTOMER"),
    ("date", "ESTIMATE DATE"),
    ("total", "TOTAL"),
    ("status", "STATUS"),
    ("actions", "ACTIONS"),
)

_COL_WIDTHS_PX: dict[str, int] = {
    "num": 96,
    "desc": 260,
    "customer": 180,
    "date": 118,
    "total": 108,
    "status": 96,
    "actions": 148,
}

_EST_WAITING_LAST_KEY = "_ips_dash_est_waiting_last"


def _normalize_estimate_status(raw: object) -> str:
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


def _estimate_status_pill_html(status: str) -> str:
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


def _estimate_number(row: dict[str, Any]) -> str:
    val = str(row.get("estimate_number") or row.get("number") or "").strip()
    return val or "—"


def _estimate_project(row: dict[str, Any]) -> str:
    try:
        from app.services.phase2_modules_service import estimate_project_title
    except ImportError:
        from services.phase2_modules_service import estimate_project_title  # type: ignore
    return estimate_project_title(row)


def _estimate_customer(row: dict[str, Any]) -> str:
    for key in ("customer_name", "customer"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return "—"


def _estimate_total(row: dict[str, Any]) -> str:
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


def _estimate_sort_date(row: dict[str, Any]) -> str:
    for key in ("estimate_date", "updated_at", "created_at"):
        val = str(row.get(key) or "").strip()
        if val:
            return val[:10]
    return ""


def _waiting_approval_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if estimate_visible_in_approved_view(row):
            continue
        if row.get("archived_from_estimates") is True:
            continue
        if estimate_status_approvable(row.get("status")):
            out.append(row)
    out.sort(key=_estimate_sort_date, reverse=True)
    return out


def _can_show_approve(row: dict[str, Any]) -> bool:
    if not can_approve_estimates(current_role()):
        return False
    eid = str(row.get("id") or "").strip()
    if not eid or is_demo_id(eid):
        return False
    return estimate_status_approvable(row.get("status")) and not estimate_visible_in_approved_view(row)


def _estimate_link_html(eid: str, label: str, *, extra_class: str = "") -> str:
    est_id = html.escape(str(eid or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    cls = f"ips-dash-est-link {extra_class}".strip()
    return (
        f'<a href="#" class="{html.escape(cls)}" data-est-action="open" '
        f'data-estimate-id="{est_id}" title="{title}">{text}</a>'
    )


def _actions_html(eid: str, *, show_approve: bool) -> str:
    est_id = html.escape(str(eid or "").strip(), quote=True)
    parts = [
        (
            f'<button type="button" class="ips-dash-est-action ips-dash-est-view" '
            f'data-est-action="open" data-estimate-id="{est_id}">View</button>'
        )
    ]
    if show_approve:
        parts.insert(
            0,
            (
                f'<button type="button" class="ips-dash-est-action ips-dash-est-approve" '
                f'data-est-action="approve" data-estimate-id="{est_id}">Approve</button>'
            ),
        )
    return f'<div class="ips-dash-est-actions">{"".join(parts)}</div>'


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-est-cell ips-dash-est-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def _build_estimates_waiting_table_html(
    rows: list[dict[str, Any]],
    *,
    approve_flags: dict[str, bool],
) -> str:
    col_parts = [
        f'<col class="ips-dash-est-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in _COL_WIDTHS_PX.items()
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-est-th ips-dash-est-th-{html.escape(key)}" '
            f'style="width:{_COL_WIDTHS_PX[key]}px;max-width:{_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in _DASH_HEADERS
    ]

    body_rows: list[str] = []
    for row_idx, est in enumerate(rows):
        eid = str(est.get("id") or "").strip()
        if not eid:
            continue

        est_no = _estimate_number(est)
        project = _estimate_project(est)
        customer = _estimate_customer(est)
        status = _normalize_estimate_status(est.get("status"))
        est_date = fmt_date(str(est.get("estimate_date") or "")[:10]) if est.get("estimate_date") else "—"
        total = _estimate_total(est)
        num_label = est_no if est_no and est_no != "—" else "Open estimate"
        title_label = project if project and project != "—" else "Open estimate"
        row_parity = "even" if row_idx % 2 else "odd"

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
                _cell_wrapper(_estimate_status_pill_html(status), extra_class="ips-dash-est-status-cell", align="center"),
            ),
            (
                "actions",
                "right",
                _cell_wrapper(
                    _actions_html(eid, show_approve=approve_flags.get(eid, False)),
                    extra_class="ips-dash-est-actions-cell",
                    align="right",
                ),
            ),
        ]

        tds = "".join(
            (
                f'<td class="ips-dash-est-td ips-dash-est-td-{html.escape(key)}" '
                f'style="width:{_COL_WIDTHS_PX[key]}px;max-width:{_COL_WIDTHS_PX[key]}px;">'
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


def _handle_est_waiting_action(raw: str, estimates_by_id: dict[str, dict[str, Any]]) -> None:
    val = str(raw or "").strip()
    if not val:
        return
    if val == str(st.session_state.get(_EST_WAITING_LAST_KEY) or ""):
        return
    st.session_state[_EST_WAITING_LAST_KEY] = val

    if val.startswith("approve:"):
        eid = val.split(":", 1)[1].strip()
        if eid not in estimates_by_id:
            return
        st.session_state["est_pending_approve_id"] = eid
        try:
            from app.navigation import set_nav_slug
        except ImportError:
            from navigation import set_nav_slug  # type: ignore
        set_nav_slug("estimates")
        st.rerun()
        return

    eid = val.split(":", 1)[1].strip() if val.startswith("open:") else val
    if not eid or eid not in estimates_by_id:
        return
    try:
        from app.navigation import navigate_to_estimate_detail
    except ImportError:
        from navigation import navigate_to_estimate_detail  # type: ignore
    navigate_to_estimate_detail(eid)
    st.rerun()


def _render_estimates_waiting_bridge(estimates_by_id: dict[str, dict[str, Any]]) -> None:
    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore

    picked = _components_html(
        """
<script>
(function () {
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = "ipsDashEstWaiting::action";
  const sel = "[data-estimate-id][data-est-action]";

  function sendValue(action) {
    const payload = { type: "streamlit:setComponentValue", value: action };
    const frames = [window, window.parent, w].filter(function (f, i, arr) {
      return f && arr.indexOf(f) === i;
    });
    for (var i = 0; i < frames.length; i++) {
      try {
        if (frames[i].Streamlit && typeof frames[i].Streamlit.setComponentValue === "function") {
          frames[i].Streamlit.setComponentValue(action);
          return;
        }
      } catch (err) {}
    }
    for (var j = 0; j < frames.length; j++) {
      try { frames[j].postMessage(payload, "*"); } catch (err) {}
    }
  }

  function bindTargets() {
    doc.querySelectorAll(sel).forEach(function (el) {
      if (el.dataset.ipsDashEstBound === "1") return;
      el.dataset.ipsDashEstBound = "1";
      el.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        const id = el.getAttribute("data-estimate-id");
        const action = el.getAttribute("data-est-action") || "open";
        if (!id) return;
        sendValue(action + ":" + id);
      });
    });
  }

  if (!doc.ipsDashEstWaitingRegistry) doc.ipsDashEstWaitingRegistry = {};
  doc.ipsDashEstWaitingRegistry[hookKey] = { bind: bindTargets };
  bindTargets();
  if (!doc.ipsDashEstWaitingBindObserver) {
    doc.ipsDashEstWaitingBindObserver = new MutationObserver(function () {
      Object.values(doc.ipsDashEstWaitingRegistry || {}).forEach(function (cfg) {
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      });
    });
    doc.ipsDashEstWaitingBindObserver.observe(doc.body, { childList: true, subtree: true });
  }
})();
</script>
        """,
        component_key="ips_dash_est_waiting_bridge",
        height=0,
    )
    action = str(picked or "").strip()
    if action:
        _handle_est_waiting_action(action, estimates_by_id)


def render_dashboard_estimates_waiting_table(
    estimates: list[dict[str, Any]],
    *,
    limit: int = 5,
) -> None:
    """Render estimates waiting approval above Active Jobs on the dashboard."""
    waiting = _waiting_approval_rows(list(estimates))[: max(1, int(limit))]
    approve_flags = {str(r.get("id") or "").strip(): _can_show_approve(r) for r in waiting}
    estimates_by_id = {
        str(est.get("id") or "").strip(): est
        for est in waiting
        if str(est.get("id") or "").strip()
    }

    with st.container(key="dashboard_estimates_waiting_table"):
        hdr_l, hdr_r = st.columns([4, 1], gap="small", vertical_alignment="center")
        with hdr_l:
            st.markdown(
                '<div class="ips-dash-est-waiting-head">'
                '<p class="ips-ops-section-title ips-dash-est-waiting-title">Estimates Waiting Approval</p>'
                '<p class="ips-dash-est-waiting-subtitle">Estimates that need review before approval</p>'
                "</div>",
                unsafe_allow_html=True,
            )
        with hdr_r:
            if st.button("View All", key="ips_dash_est_waiting_all", use_container_width=True):
                st.session_state["estimates_view"] = "Active Estimates"
                try:
                    from app.navigation import set_nav_slug
                except ImportError:
                    from navigation import set_nav_slug  # type: ignore
                set_nav_slug("estimates")
                st.rerun()

        if not waiting:
            st.markdown(
                '<p class="ips-dash-est-waiting-empty">No estimates waiting approval.</p>',
                unsafe_allow_html=True,
            )
            return

        st.markdown(
            _build_estimates_waiting_table_html(waiting, approve_flags=approve_flags),
            unsafe_allow_html=True,
        )
        _render_estimates_waiting_bridge(estimates_by_id)
