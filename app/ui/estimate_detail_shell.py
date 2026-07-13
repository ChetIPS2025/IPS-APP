"""Shared layout chrome for estimate detail sub-pages (Materials, Labor, …)."""

from __future__ import annotations

import html
from datetime import date, datetime, timedelta
from typing import Any

import streamlit as st

from app.navigation import IPS_NAV_PENDING_KEY

_EST_DETAIL_STYLE_KEY = "ips_estimate_detail_styles_v1"

ESTIMATE_DETAIL_TABS: tuple[str, ...] = (
    "Overview",
    "Materials",
    "Labor",
    "Equipment",
    "Subcontractors",
    "Markups",
    "Summary",
    "Notes",
    "Attachments",
    "History",
)

_TAB_TO_EDITOR_SECTION: dict[str, str] = {
    "Labor": "Labor",
    "Equipment": "Equipment",
    "Notes": "Job Scope",
    "Attachments": "Attachments / P.O.",
    "Summary": "Review / Save",
    "Markups": "Review / Save",
    "Overview": "Review / Save",
    "History": "Review / Save",
}


def inject_estimate_detail_styles() -> None:
    if st.session_state.get(_EST_DETAIL_STYLE_KEY):
        return
    st.session_state[_EST_DETAIL_STYLE_KEY] = True
    st.markdown(
        """
        <style>
        section[data-testid="stMain"]:has(.ips-estimate-detail-marker) .block-container {
            padding: 1.25rem 1.5rem 1.5rem !important;
            max-width: 1680px !important;
        }
        .ips-est-breadcrumb {
            font-size: 0.78rem;
            color: #64748b;
            margin: 0 0 0.65rem 0;
            font-weight: 500;
        }
        .ips-est-breadcrumb strong { color: #334155; font-weight: 600; }
        .ips-est-title-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 0.65rem 1rem;
            margin-bottom: 0.25rem;
        }
        .ips-est-title-row h1 {
            font-size: 1.65rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0;
            letter-spacing: -0.02em;
        }
        .ips-est-status-pill {
            display: inline-block;
            padding: 0.2rem 0.65rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: capitalize;
            background: #eff6ff;
            color: #1d4ed8;
            border: 1px solid #bfdbfe;
        }
        .ips-est-subtitle {
            font-size: 0.88rem;
            color: #64748b;
            margin: 0 0 1rem 0;
        }
        .ips-est-info-card {
            background: #ffffff;
            border: 1px solid #e5eaf2;
            border-radius: 14px;
            padding: 1.1rem 1.25rem;
            margin-bottom: 1rem;
        }
        .ips-est-info-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 0.85rem 1.25rem;
            align-items: start;
        }
        @media (max-width: 1100px) {
            .ips-est-info-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        }
        @media (max-width: 640px) {
            .ips-est-info-grid { grid-template-columns: 1fr 1fr; }
        }
        .ips-est-info-k {
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: #94a3b8;
            margin-bottom: 0.2rem;
        }
        .ips-est-info-v {
            font-size: 0.9rem;
            font-weight: 600;
            color: #0f172a;
            line-height: 1.35;
        }
        .ips-est-info-total { text-align: right; }
        .ips-est-info-total .ips-est-info-v {
            font-size: 1.35rem;
            font-weight: 800;
        }
        .ips-est-surface-card {
            background: #ffffff;
            border: 1px solid #e5eaf2;
            border-radius: 14px;
            padding: 1.15rem 1.2rem;
            margin-bottom: 1rem;
        }
        .ips-est-card-title {
            font-size: 1rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 0.85rem 0;
        }
        .ips-est-mat-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.8125rem;
        }
        .ips-est-mat-table thead th {
            background: #ffffff;
            color: #475569;
            font-weight: 700;
            text-align: left;
            padding: 0.55rem 0.5rem;
            border-bottom: 1px solid #e5eaf2;
            white-space: nowrap;
        }
        .ips-est-mat-table tbody td {
            padding: 0.62rem 0.5rem;
            border-bottom: 1px solid #f1f5f9;
            color: #0f172a;
            vertical-align: middle;
        }
        .ips-est-mat-table tbody tr:hover td { background: #F8FAFC; }
        .ips-est-item-link { color: #2563eb; font-weight: 600; }
        .ips-est-drag { color: #cbd5e1; font-size: 1rem; user-select: none; }
        .ips-est-summary-card {
            background: #ffffff;
            border: 1px solid #e5eaf2;
            border-radius: 14px;
            padding: 1rem 1.1rem;
        }
        .ips-est-summary-row {
            display: flex;
            justify-content: space-between;
            font-size: 0.84rem;
            padding: 0.28rem 0;
            color: #334155;
        }
        .ips-est-summary-row strong { color: #0f172a; }
        .ips-est-summary-divider {
            border-top: 1px solid #e5eaf2;
            margin: 0.45rem 0;
        }
        .ips-est-markup-box {
            background: #ffffff;
            border: 1px solid #e5eaf2;
            border-radius: 10px;
            padding: 0.75rem 0.85rem;
            margin-top: 0.65rem;
        }
        .ips-est-doc-row {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            padding: 0.55rem 0;
            border-bottom: 1px solid #f1f5f9;
        }
        .ips-est-empty {
            text-align: center;
            padding: 1.5rem 1rem;
            color: #64748b;
            font-size: 0.88rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_estimate_detail_marker() -> None:
    st.markdown('<span class="ips-estimate-detail-marker" aria-hidden="true"></span>', unsafe_allow_html=True)


def _fmt_date_short(v: Any) -> str:
    if not v:
        return "—"
    s = str(v).strip()
    if not s:
        return "—"
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%b %d, %Y")
        return date.fromisoformat(s[:10]).strftime("%b %d, %Y")
    except Exception:
        return s[:10] if len(s) >= 10 else s


def _valid_through_html(expiration_date: Any) -> str:
    """Render valid-through date (already resolved; not estimate date + 30)."""
    if not expiration_date:
        return "—"
    try:
        if isinstance(expiration_date, date):
            valid = expiration_date
        elif isinstance(expiration_date, datetime):
            valid = expiration_date.date()
        else:
            s = str(expiration_date).strip()
            if "T" in s:
                valid = datetime.fromisoformat(s.replace("Z", "+00:00")).date()
            else:
                valid = date.fromisoformat(s[:10])
        days = (valid - date.today()).days
        vt = valid.strftime("%b %d, %Y")
        if days > 0:
            extra = f' <span style="color:#64748b;font-weight:500;">({days} days left)</span>'
        elif days == 0:
            extra = ' <span style="color:#f59e0b;font-weight:600;">(expires today)</span>'
        else:
            extra = f' <span style="color:#dc2626;font-weight:600;">({abs(days)} days ago)</span>'
        return html.escape(vt) + extra
    except Exception:
        return html.escape(_fmt_date_short(expiration_date))


def render_breadcrumb(*, quote_label: str, tab_label: str) -> None:
    st.markdown(
        f'<p class="ips-est-breadcrumb">Estimates <span aria-hidden="true">›</span> '
        f"<strong>{html.escape(quote_label)}</strong> "
        f'<span aria-hidden="true">›</span> <strong>{html.escape(tab_label)}</strong></p>',
        unsafe_allow_html=True,
    )
    if st.button("← Back to Estimates", key="est_det_bc_list", type="secondary"):
        st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
        st.session_state["estimates_view"] = "list"
        st.rerun()


def render_detail_header(
    *,
    quote_number: str,
    status: str,
    project_name: str,
    customer_name: str,
) -> None:
    qn = html.escape(str(quote_number or "—").strip() or "—")
    stt = html.escape(str(status or "draft").strip() or "draft")
    proj = html.escape(str(project_name or "").strip() or "—")
    cust = html.escape(str(customer_name or "").strip() or "—")
    st.markdown(
        f'<div class="ips-est-title-row"><h1>Estimate {qn}</h1>'
        f'<span class="ips-est-status-pill">{stt}</span></div>'
        f'<p class="ips-est-subtitle">{proj} <span style="color:#cbd5e1;">•</span> {cust}</p>',
        unsafe_allow_html=True,
    )

    a1, a2, a3, _ = st.columns([0.7, 0.7, 1.1, 3.5], gap="small")
    with a1:
        st.button("More", key="est_det_hdr_more", type="secondary", use_container_width=True)
    with a2:
        if st.button("Export", key="est_det_hdr_export", type="secondary", use_container_width=True):
            st.session_state["est_det_export_open"] = True
    with a3:
        if st.button("Edit Estimate", key="est_det_hdr_edit", type="primary", use_container_width=True):
            st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
            st.session_state["estimates_view"] = "edit"
            st.rerun()


def render_info_card(
    *,
    customer_name: str,
    customer_id: str | None,
    job_label: str,
    job_id: str | None,
    estimate_date: Any,
    valid_through_base: Any,
    prepared_by: str,
    estimated_total: str,
) -> None:
    st.markdown(
        f"""
        <div class="ips-est-info-card">
          <div class="ips-est-info-grid">
            <div><div class="ips-est-info-k">Client</div>
            <div class="ips-est-info-v">{html.escape(customer_name or "—")}</div></div>
            <div><div class="ips-est-info-k">Job</div>
            <div class="ips-est-info-v">{html.escape(job_label or "—")}</div></div>
            <div><div class="ips-est-info-k">Estimate Date</div>
            <div class="ips-est-info-v">{html.escape(_fmt_date_short(estimate_date))}</div></div>
            <div><div class="ips-est-info-k">Valid Through</div>
            <div class="ips-est-info-v">{_valid_through_html(valid_through_base)}</div></div>
            <div><div class="ips-est-info-k">Prepared By</div>
            <div class="ips-est-info-v">{html.escape(prepared_by or "—")}</div></div>
            <div class="ips-est-info-total"><div class="ips-est-info-k">Estimated Total</div>
            <div class="ips-est-info-v">{html.escape(estimated_total)}</div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    l1, l2, _, _, _, _ = st.columns(6, gap="small")
    with l1:
        if customer_id and st.button("View Client", key="est_det_view_client", type="secondary"):
            st.session_state[IPS_NAV_PENDING_KEY] = "Customers"
            st.session_state["cust_detail_id"] = customer_id
            st.rerun()
    with l2:
        if job_id and st.button("View Job", key="est_det_view_job", type="secondary"):
            st.session_state[IPS_NAV_PENDING_KEY] = "Job Database"
            st.session_state["job_view_mode"] = "view"
            st.session_state["selected_job_id"] = job_id
            st.rerun()


def render_tab_bar(*, active_tab: str, key_prefix: str = "est_det_tab") -> str | None:
    clicked: str | None = None
    cols = st.columns(len(ESTIMATE_DETAIL_TABS), gap="small")
    for i, tab in enumerate(ESTIMATE_DETAIL_TABS):
        with cols[i]:
            is_active = tab == active_tab
            if st.button(
                tab,
                key=f"{key_prefix}_{tab}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                if not is_active:
                    clicked = tab
    return clicked


def navigate_estimate_tab(tab: str) -> None:
    if tab == "Materials":
        eid = str(st.session_state.get("selected_estimate_id") or st.session_state.get("ips_sel_estimates") or "").strip()
        from app.navigation import ESTIMATE_DETAIL_TAB_KEY, navigate_to_estimate_detail
        if eid:
            navigate_to_estimate_detail(eid, tab="Materials")
        else:
            st.session_state[ESTIMATE_DETAIL_TAB_KEY] = "Materials"
            st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
        st.rerun()
        return
    section = _TAB_TO_EDITOR_SECTION.get(tab)
    st.session_state[IPS_NAV_PENDING_KEY] = "Estimates"
    st.session_state["estimates_view"] = "edit"
    if section:
        st.session_state["estimate_editor_section"] = section
    st.rerun()
