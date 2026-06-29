"""Unified Pipeline — quotes (Q) and jobs (J) in one list."""

from __future__ import annotations

import html

import streamlit as st

try:
    from app.components.headers import render_page_brand_header
    from app.components.layout import render_filter_bar as layout_filter_bar
    from app.components.table_pagination import paginate_rows, reset_table_page
    from app.pages._core._data import load_estimates, load_jobs
    from app.services.pipeline_service import (
        PIPELINE_VIEWS,
        build_pipeline_rows,
        filter_pipeline_rows,
        pipeline_summary,
    )
    from app.utils.formatting import fmt_currency
except ImportError:
    from components.headers import render_page_brand_header  # type: ignore
    from components.layout import render_filter_bar as layout_filter_bar  # type: ignore
    from components.table_pagination import paginate_rows, reset_table_page  # type: ignore
    from pages._core._data import load_estimates, load_jobs  # type: ignore
    from services.pipeline_service import (  # type: ignore
        PIPELINE_VIEWS,
        build_pipeline_rows,
        filter_pipeline_rows,
        pipeline_summary,
    )
    from utils.formatting import fmt_currency  # type: ignore

_TABLE_KEY = "pipeline_list"
_DEFAULT_VIEW = "All Pipeline"


def _set_nav_slug(slug: str) -> None:
    try:
        from app.navigation import set_nav_slug
    except ImportError:
        from navigation import set_nav_slug  # type: ignore
    set_nav_slug(slug)


def _open_estimate(estimate_id: str) -> None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    st.session_state["selected_estimate_id"] = eid
    st.session_state["show_estimate_detail_modal"] = True
    _set_nav_slug("estimates")
    st.rerun()


def _open_job(job_id: str) -> None:
    jid = str(job_id or "").strip()
    if not jid:
        return
    st.session_state["selected_job_id"] = jid
    st.session_state["show_job_detail_modal"] = True
    _set_nav_slug("jobs")
    st.rerun()


def _new_quote() -> None:
    _set_nav_slug("estimates")
    st.session_state["ips_est_new_dialog_open"] = True
    st.rerun()


def _new_job() -> None:
    _set_nav_slug("jobs")
    st.session_state["ips_job_form"] = True
    st.rerun()


def _render_summary_cards(summary: dict[str, int | float]) -> None:
    cols = st.columns(5, gap="small")
    specs = (
        ("TOTAL", int(summary.get("total") or 0)),
        ("OPEN QUOTES", int(summary.get("open_quotes") or 0)),
        ("APPROVED QUOTES", int(summary.get("approved_quotes") or 0)),
        ("ACTIVE JOBS", int(summary.get("active_jobs") or 0)),
        ("PIPELINE VALUE", fmt_currency(summary.get("pipeline_value") or 0)),
    )
    for col, (label, value) in zip(cols, specs):
        with col:
            display = html.escape(str(value))
            st.markdown(
                f'<div style="border:1px solid #dbe3ef;border-radius:10px;padding:0.65rem 0.75rem;background:#fff;">'
                f'<div style="font-size:0.68rem;font-weight:700;color:#64748b;letter-spacing:0.04em;">{label}</div>'
                f'<div style="font-size:1.15rem;font-weight:800;color:#0f172a;margin-top:0.2rem;">{display}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


def _render_pipeline_table(rows: list[dict]) -> None:
    header = st.columns([0.9, 0.9, 2.1, 1.5, 1.1, 1.0, 1.0], gap="small")
    for col, label in zip(
        header,
        ("QUOTE #", "JOB #", "PROJECT", "CUSTOMER", "STAGE", "VALUE", "OPEN"),
    ):
        with col:
            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;">{label}</div>',
                unsafe_allow_html=True,
            )

    for row in rows:
        cols = st.columns([0.9, 0.9, 2.1, 1.5, 1.1, 1.0, 1.0], gap="small")
        qnum = str(row.get("quote_number") or "—")
        jnum = str(row.get("job_number") or "—")
        with cols[0]:
            st.markdown(f"**{html.escape(qnum)}**")
        with cols[1]:
            st.markdown(f"**{html.escape(jnum)}**")
        with cols[2]:
            st.markdown(html.escape(str(row.get("project") or "—")))
        with cols[3]:
            st.markdown(html.escape(str(row.get("customer") or "—")))
        with cols[4]:
            st.markdown(html.escape(str(row.get("stage") or "—")))
        with cols[5]:
            val = float(row.get("value") or 0)
            st.markdown(f"**{fmt_currency(val) if val else '—'}**")
        with cols[6]:
            key_base = str(row.get("pipeline_key") or "")
            eid = str(row.get("estimate_id") or "")
            jid = str(row.get("job_id") or "")
            if eid and jid:
                q_col, j_col = st.columns(2, gap="small")
                with q_col:
                    if st.button("Q", key=f"pipe_open_q_{key_base}", use_container_width=True):
                        _open_estimate(eid)
                with j_col:
                    if st.button("J", key=f"pipe_open_j_{key_base}", use_container_width=True):
                        _open_job(jid)
            elif eid:
                if st.button("Quote", key=f"pipe_open_q_{key_base}", use_container_width=True):
                    _open_estimate(eid)
            elif jid:
                if st.button("Job", key=f"pipe_open_j_{key_base}", use_container_width=True):
                    _open_job(jid)


def _render_pipeline_page() -> None:
    st.markdown(
        '<span class="ips-pipeline-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    all_rows = build_pipeline_rows(load_estimates(), load_jobs())

    def _new_quote_btn() -> None:
        if st.button("+ New Quote", key="pipeline_new_quote", use_container_width=True):
            _new_quote()

    def _new_job_btn() -> None:
        if st.button("+ New Job", key="pipeline_new_job", use_container_width=True):
            _new_job()

    render_page_brand_header(
        "Pipeline",
        "Quotes (Q) and jobs (J) in one place — Q becomes J when the customer accepts and a job is linked.",
        actions=[_new_quote_btn, _new_job_btn],
    )

    def _filters() -> None:
        c1, c2, c3 = st.columns([3.2, 2.2, 0.6])
        with c1:
            st.text_input(
                "Search",
                placeholder="Search Q/J #, project, customer, stage…",
                key="pipeline_search",
                label_visibility="collapsed",
            )
        with c2:
            st.selectbox(
                "View",
                PIPELINE_VIEWS,
                key="pipeline_view",
                label_visibility="collapsed",
            )
        with c3:
            if st.button("Clear", key="pipeline_clear", use_container_width=True):
                st.session_state.pop("pipeline_search", None)
                st.session_state["pipeline_view"] = _DEFAULT_VIEW
                reset_table_page(_TABLE_KEY)
                st.rerun()

    st.markdown('<div class="ips-pipeline-filter-bar">', unsafe_allow_html=True)
    layout_filter_bar(_filters)
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = filter_pipeline_rows(
        all_rows,
        view=str(st.session_state.get("pipeline_view") or _DEFAULT_VIEW),
        search=str(st.session_state.get("pipeline_search") or ""),
    )
    _render_summary_cards(pipeline_summary(filtered))

    st.caption(f"Showing {len(filtered)} pipeline record{'s' if len(filtered) != 1 else ''}.")
    page_rows, page_idx, total_pages, total_rows = paginate_rows(filtered, _TABLE_KEY)
    if total_pages > 1:
        st.caption(f"Page {page_idx + 1} of {total_pages} ({total_rows} rows)")

    _render_pipeline_table(page_rows)


def render() -> None:
    try:
        from app.pages._core._access import begin_module
    except ImportError:
        from pages._core._access import begin_module  # type: ignore
    if not begin_module("pipeline"):
        return
    _render_pipeline_page()
