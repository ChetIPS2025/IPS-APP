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

_DASH_HEADERS: tuple[tuple[str, str], ...] = (
    ("num", "JOB #"),
    ("desc", "PROJECT / DESCRIPTION"),
    ("customer", "CUSTOMER"),
    ("status", "STATUS"),
    ("contract", "CONTRACT VALUE"),
    ("estimated", "ESTIMATED COST"),
    ("actual", "ACTUAL COST"),
    ("profit", "GROSS PROFIT"),
    ("margin", "MARGIN %"),
    ("subjobs", "OPEN TASKS / SUBJOBS"),
)

_COL_WIDTHS_PX: dict[str, int] = {
    "num": 90,
    "desc": 320,
    "customer": 220,
    "status": 110,
    "contract": 120,
    "estimated": 120,
    "actual": 120,
    "profit": 120,
    "margin": 90,
    "subjobs": 90,
}


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


def _job_link_html(job_id: str, label: str, *, extra_class: str = "") -> str:
    jid = html.escape(str(job_id or "").strip(), quote=True)
    text = html.escape(label)
    title = html.escape(label, quote=True)
    cls = f"ips-dash-job-link {extra_class}".strip()
    return (
        f'<a href="#" class="{html.escape(cls)}" data-job-id="{jid}" '
        f'title="{title}">{text}</a>'
    )


def _cell_wrapper(inner: str, *, extra_class: str = "", align: str = "left") -> str:
    cls = f"cell-wrapper ips-dash-cell ips-dash-cell-{align} {extra_class}".strip()
    return f'<div class="{html.escape(cls)}">{inner}</div>'


def _build_active_jobs_table_html(
    rows: list[dict[str, Any]],
    *,
    subjob_counts: dict[str, int],
) -> str:
    col_parts = [
        f'<col class="ips-dash-col-{html.escape(key)}" style="width:{px}px;" />'
        for key, px in _COL_WIDTHS_PX.items()
    ]
    head_parts = [
        (
            f'<th scope="col" class="ips-dash-th ips-dash-th-{html.escape(key)}" '
            f'style="width:{_COL_WIDTHS_PX[key]}px;max-width:{_COL_WIDTHS_PX[key]}px;">'
            f"{html.escape(label)}</th>"
        )
        for key, label in _DASH_HEADERS
    ]

    body_rows: list[str] = []
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

        num_label = job_no if job_no and job_no != "—" else "View job"
        title_label = project if project and project != "—" else "View job"
        row_parity = "even" if row_idx % 2 else "odd"

        cells = [
            (
                "num",
                "left",
                _cell_wrapper(
                    _job_link_html(jid, num_label, extra_class="ips-dash-job-num-link"),
                    extra_class="ips-dash-job-num-cell",
                ),
            ),
            (
                "desc",
                "left",
                _cell_wrapper(
                    _job_link_html(jid, title_label, extra_class="ips-dash-job-desc-link"),
                    extra_class="ips-dash-job-desc-cell",
                ),
            ),
            (
                "customer",
                "left",
                _cell_wrapper(
                    html.escape(customer),
                    extra_class="ips-dash-customer-cell",
                ),
            ),
            (
                "status",
                "center",
                _cell_wrapper(job_status_pill_html(status), extra_class="ips-dash-status-cell"),
            ),
            (
                "contract",
                "right",
                _cell_wrapper(
                    html.escape(_money_cell(contract_val, available=has_contract)),
                    extra_class=f"ips-dash-money-cell{_money_cell_class(contract_val, available=has_contract)}",
                    align="right",
                ),
            ),
            (
                "estimated",
                "right",
                _cell_wrapper(
                    html.escape(_money_cell(estimated_val, available=has_estimated)),
                    extra_class=f"ips-dash-money-cell{_money_cell_class(estimated_val, available=has_estimated)}",
                    align="right",
                ),
            ),
            (
                "actual",
                "right",
                _cell_wrapper(
                    html.escape(_money_cell(actual_val, available=has_actual)),
                    extra_class=f"ips-dash-money-cell{_money_cell_class(actual_val, available=has_actual)}",
                    align="right",
                ),
            ),
            (
                "profit",
                "right",
                _cell_wrapper(
                    html.escape(_money_cell(profit_val, available=has_profit_data)),
                    extra_class=(
                        f"ips-dash-money-cell{profit_cls}"
                        f"{_money_cell_class(profit_val, available=has_profit_data)}"
                    ),
                    align="right",
                ),
            ),
            (
                "margin",
                "right",
                _cell_wrapper(
                    html.escape(_pct_cell(margin_val) if has_contract else "—"),
                    extra_class=f"ips-dash-money-cell{profit_cls if has_contract else ' ips-jobs-money-empty'}",
                    align="right",
                ),
            ),
            (
                "subjobs",
                "center",
                _cell_wrapper(f"{open_subjobs:,}", extra_class="ips-dash-subjobs-cell", align="center"),
            ),
        ]

        tds = "".join(
            (
                f'<td class="ips-dash-td ips-dash-td-{html.escape(key)}" '
                f'style="width:{_COL_WIDTHS_PX[key]}px;max-width:{_COL_WIDTHS_PX[key]}px;">'
                f"{content}</td>"
            )
            for key, _align, content in cells
        )
        body_rows.append(
            f'<tr class="ips-dash-tr ips-dash-row-{row_parity}" data-job-id="{html.escape(jid, quote=True)}">'
            f"{tds}"
            f"</tr>"
        )

    return (
        '<div class="ips-dash-jobs-table-scroll">'
        '<table class="ips-dash-jobs-html-table">'
        f"<colgroup>{''.join(col_parts)}</colgroup>"
        f"<thead><tr class=\"ips-dash-tr ips-dash-head-row\">{''.join(head_parts)}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
        "</div>"
    )


def _render_dashboard_job_link_bridge(jobs_by_id: dict[str, dict[str, Any]]) -> None:
    try:
        from app.ui.clean_table import _components_html
    except ImportError:
        from ui.clean_table import _components_html  # type: ignore

    st.markdown(
        '<span class="ips-dash-job-link-bridge-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    picked = _components_html(
        """
<script>
(function () {
  const w = window.parent || window;
  const doc = w.document;
  const hookKey = "ipsDashJobLink::active";
  const tblSel = ".ips-dash-jobs-html-table";
  const linkSel = ".ips-dash-job-link[data-job-id]";

  function sendValue(id) {
    const payload = { type: "streamlit:setComponentValue", value: id };
    const frames = [window, window.parent, w].filter(function (f, i, arr) {
      return f && arr.indexOf(f) === i;
    });
    for (var i = 0; i < frames.length; i++) {
      try {
        if (frames[i].Streamlit && typeof frames[i].Streamlit.setComponentValue === "function") {
          frames[i].Streamlit.setComponentValue(id);
          return;
        }
      } catch (err) {}
    }
    for (var j = 0; j < frames.length; j++) {
      try { frames[j].postMessage(payload, "*"); } catch (err) {}
    }
  }

  function bindLinks() {
    doc.querySelectorAll(linkSel).forEach(function (link) {
      if (link.dataset.ipsDashJobBound === "1") return;
      link.dataset.ipsDashJobBound = "1";
      link.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        const id = link.getAttribute("data-job-id");
        if (id) sendValue(id);
      });
    });
  }

  if (!doc.ipsDashJobLinkRegistry) doc.ipsDashJobLinkRegistry = {};
  doc.ipsDashJobLinkRegistry[hookKey] = { bind: bindLinks };
  bindLinks();
  if (!doc.ipsDashJobLinkBindObserver) {
    doc.ipsDashJobLinkBindObserver = new MutationObserver(function () {
      Object.values(doc.ipsDashJobLinkRegistry || {}).forEach(function (cfg) {
        if (cfg && typeof cfg.bind === "function") cfg.bind();
      });
    });
    doc.ipsDashJobLinkBindObserver.observe(doc.body, { childList: true, subtree: true });
  }
})();
</script>
        """,
        component_key="ips_dash_active_jobs_link_bridge",
        height=0,
    )
    open_id = str(picked or "").strip()
    if open_id and open_id in jobs_by_id:
        _open_job_nav(open_id, jobs_by_id[open_id])


def render_dashboard_active_jobs_table(
    jobs: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> None:
    """Render the Active Jobs table on the dashboard using a real HTML table."""
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

        jobs_by_id = {
            str(job.get("id") or "").strip(): job
            for job in rows
            if str(job.get("id") or "").strip()
        }

        st.markdown(
            '<span class="ips-dash-jobs-split-marker" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )
        table_col, actions_col = st.columns([12.73, 1], gap="small")

        with table_col:
            st.markdown(
                _build_active_jobs_table_html(rows, subjob_counts=subjob_counts),
                unsafe_allow_html=True,
            )

        with actions_col:
            st.markdown(
                '<div class="ips-dash-actions-head">ACTIONS</div>',
                unsafe_allow_html=True,
            )
            for job in rows:
                jid = str(job.get("id") or "").strip()
                if not jid:
                    continue
                st.markdown('<div class="ips-dash-action-row">', unsafe_allow_html=True)
                render_job_row_actions(
                    job,
                    on_open=_open_job_nav,
                    on_edit=_open_job_edit,
                    on_status_updated=lambda _jid, _status: None,
                )
                st.markdown("</div>", unsafe_allow_html=True)

        _render_dashboard_job_link_bridge(jobs_by_id)
