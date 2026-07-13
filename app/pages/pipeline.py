"""Unified Pipeline — quotes (Q) and jobs (J) in one list."""

from __future__ import annotations

import html

import streamlit as st

from app.auth import current_role, effective_role
from app.components.headers import render_page_brand_header
from app.components.layout import render_filter_bar as layout_filter_bar
from app.components.table_pagination import paginate_rows, reset_table_page
from app.pages._core._data import load_estimates, load_jobs
from app.services.estimate_job_workflow_service import (
    approve_estimate_and_sync_job,
    can_approve_estimates,
    estimate_status_approvable,
)
from app.services.pipeline_service import (
    PIPELINE_VIEWS,
    build_pipeline_rows,
    filter_pipeline_rows,
    pipeline_filter_options,
    pipeline_summary,
)
from app.services.repository import clear_data_cache_for_table
from app.utils.formatting import fmt_currency
_TABLE_KEY = "pipeline_list"
_DEFAULT_VIEW = "All Pipeline"
_FILTER_ALL = "All"


def _set_nav_slug(slug: str) -> None:
    from app.navigation import set_nav_slug
    set_nav_slug(slug)


def _open_estimate(estimate_id: str) -> None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    st.session_state["selected_estimate_id"] = eid
    st.session_state["estimates_mode"] = "detail"
    st.session_state["show_estimate_detail_modal"] = False
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


def _approve_quote(estimate_id: str) -> None:
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    res = approve_estimate_and_sync_job(eid)
    if res.ok:
        clear_data_cache_for_table("estimates")
        st.success(res.message or "Estimate approved and linked job activated.")
        st.rerun()
    st.error(res.message or "Could not approve estimate.")


def _new_quote() -> None:
    _set_nav_slug("estimates")
    st.session_state["ips_est_new_dialog_open"] = True
    st.rerun()


def _new_job() -> None:
    _set_nav_slug("jobs")
    st.session_state["ips_job_form"] = True
    st.rerun()


def _can_show_approve(row: dict) -> bool:
    eid = str(row.get("estimate_id") or "").strip()
    if not eid:
        return False
    if not can_approve_estimates(effective_role()):
        return False
    return estimate_status_approvable(row.get("estimate_status"))


def _render_summary_cards(summary: dict[str, int | float]) -> None:
    cols = st.columns(6, gap="small")
    specs = (
        ("TOTAL", int(summary.get("total") or 0)),
        ("NEEDS ATTENTION", int(summary.get("stale_count") or 0)),
        ("OPEN QUOTES", int(summary.get("open_quotes") or 0)),
        ("APPROVED QUOTES", int(summary.get("approved_quotes") or 0)),
        ("ACTIVE JOBS", int(summary.get("active_jobs") or 0)),
        ("PIPELINE VALUE", fmt_currency(summary.get("pipeline_value") or 0)),
    )
    for col, (label, value) in zip(cols, specs):
        with col:
            display = html.escape(str(value))
            accent = "#b45309" if label == "NEEDS ATTENTION" and int(summary.get("stale_count") or 0) > 0 else "#0f172a"
            st.markdown(
                f'<div style="border:1px solid #dbe3ef;border-radius:10px;padding:0.65rem 0.75rem;background:#fff;">'
                f'<div style="font-size:0.68rem;font-weight:700;color:#64748b;letter-spacing:0.04em;">{label}</div>'
                f'<div style="font-size:1.15rem;font-weight:800;color:{accent};margin-top:0.2rem;">{display}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


def _stage_cell_html(row: dict) -> str:
    stage = html.escape(str(row.get("stage") or "—"))
    hint = str(row.get("stale_hint") or "").strip()
    if not hint:
        return stage
    tip = html.escape(hint)
    return (
        f'{stage}<br><span style="font-size:0.72rem;font-weight:600;color:#b45309;" title="{tip}">'
        f"⚠ {tip}</span>"
    )


def _render_pipeline_table(rows: list[dict]) -> None:
    header = st.columns([0.85, 0.85, 2.0, 1.35, 1.0, 1.35, 0.95, 1.35], gap="small")
    for col, label in zip(
        header,
        ("QUOTE #", "JOB #", "PROJECT", "CUSTOMER", "SUPERVISOR", "STAGE", "VALUE", "ACTIONS"),
    ):
        with col:
            st.markdown(
                f'<div style="font-size:0.72rem;font-weight:700;color:#64748b;">{label}</div>',
                unsafe_allow_html=True,
            )

    for row in rows:
        cols = st.columns([0.85, 0.85, 2.0, 1.35, 1.0, 1.35, 0.95, 1.35], gap="small")
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
            st.markdown(html.escape(str(row.get("supervisor") or "—")))
        with cols[5]:
            st.markdown(_stage_cell_html(row), unsafe_allow_html=True)
        with cols[6]:
            val = float(row.get("value") or 0)
            st.markdown(f"**{fmt_currency(val) if val else '—'}**")
        with cols[7]:
            key_base = str(row.get("pipeline_key") or "")
            eid = str(row.get("estimate_id") or "")
            jid = str(row.get("job_id") or "")
            show_approve = _can_show_approve(row)
            if show_approve and eid and jid:
                a_col, q_col, j_col = st.columns(3, gap="small")
                with a_col:
                    if st.button("✓", key=f"pipe_approve_{key_base}", help="Approve quote"):
                        _approve_quote(eid)
                with q_col:
                    if st.button("Q", key=f"pipe_open_q_{key_base}", use_container_width=True):
                        _open_estimate(eid)
                with j_col:
                    if st.button("J", key=f"pipe_open_j_{key_base}", use_container_width=True):
                        _open_job(jid)
            elif show_approve and eid:
                a_col, q_col = st.columns(2, gap="small")
                with a_col:
                    if st.button("✓", key=f"pipe_approve_{key_base}", help="Approve quote"):
                        _approve_quote(eid)
                with q_col:
                    if st.button("Q", key=f"pipe_open_q_{key_base}", use_container_width=True):
                        _open_estimate(eid)
            elif eid and jid:
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


def _ensure_pipeline_filter_defaults(filter_opts: dict[str, list[str]]) -> None:
    if "pipeline_view" not in st.session_state:
        st.session_state["pipeline_view"] = _DEFAULT_VIEW
    if "pipeline_customer" not in st.session_state:
        st.session_state["pipeline_customer"] = _FILTER_ALL
    elif st.session_state["pipeline_customer"] not in filter_opts.get("customer", [_FILTER_ALL]):
        st.session_state["pipeline_customer"] = _FILTER_ALL
    if "pipeline_supervisor" not in st.session_state:
        st.session_state["pipeline_supervisor"] = _FILTER_ALL
    elif st.session_state["pipeline_supervisor"] not in filter_opts.get("supervisor", [_FILTER_ALL]):
        st.session_state["pipeline_supervisor"] = _FILTER_ALL


def _render_pipeline_page() -> None:
    st.markdown(
        '<span class="ips-pipeline-page ips-page-shell-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )

    all_rows = build_pipeline_rows(load_estimates(), load_jobs())
    filter_opts = pipeline_filter_options(all_rows)
    _ensure_pipeline_filter_defaults(filter_opts)

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
                st.session_state["pipeline_customer"] = _FILTER_ALL
                st.session_state["pipeline_supervisor"] = _FILTER_ALL
                reset_table_page(_TABLE_KEY)
                st.rerun()

        c4, c5, _ = st.columns([2.2, 2.2, 1.6])
        with c4:
            st.selectbox(
                "Customer",
                filter_opts.get("customer") or [_FILTER_ALL],
                key="pipeline_customer",
                label_visibility="collapsed",
            )
        with c5:
            st.selectbox(
                "Supervisor",
                filter_opts.get("supervisor") or [_FILTER_ALL],
                key="pipeline_supervisor",
                label_visibility="collapsed",
            )

    st.markdown('<div class="ips-pipeline-filter-bar">', unsafe_allow_html=True)
    layout_filter_bar(_filters)
    st.markdown("</div>", unsafe_allow_html=True)

    filtered = filter_pipeline_rows(
        all_rows,
        view=str(st.session_state.get("pipeline_view") or _DEFAULT_VIEW),
        search=str(st.session_state.get("pipeline_search") or ""),
        customer=str(st.session_state.get("pipeline_customer") or _FILTER_ALL),
        supervisor=str(st.session_state.get("pipeline_supervisor") or _FILTER_ALL),
    )
    summary = pipeline_summary(filtered)
    _render_summary_cards(summary)

    stale_n = int(summary.get("stale_count") or 0)
    if stale_n:
        cap_col, digest_col = st.columns([4, 1])
        with cap_col:
            st.caption(
                f"{stale_n} record{'s' if stale_n != 1 else ''} need attention "
                "(aging sent quotes, unlinked approvals, or not-started jobs)."
            )
        with digest_col:
            from app.services.email_notifications import pipeline_digest_recipients, run_pipeline_attention_digest
            if pipeline_digest_recipients() and st.button(
                "Email digest",
                key="pipeline_email_digest",
                use_container_width=True,
            ):
                result = run_pipeline_attention_digest()
                if result.get("sent"):
                    st.success("Pipeline attention digest sent.")
                elif result.get("failed"):
                    st.error("Could not send digest — check email settings.")
                else:
                    st.info("Nothing to send.")

    st.caption(f"Showing {len(filtered)} pipeline record{'s' if len(filtered) != 1 else ''}.")
    page_rows, page_idx, total_pages, total_rows = paginate_rows(filtered, _TABLE_KEY)
    if total_pages > 1:
        st.caption(f"Page {page_idx + 1} of {total_pages} ({total_rows} rows)")

    _render_pipeline_table(page_rows)


def render() -> None:
    from app.pages._core._access import begin_module
    if not begin_module("pipeline"):
        return
    _render_pipeline_page()
