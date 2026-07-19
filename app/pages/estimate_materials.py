"""Estimate Materials module (Phase 2B) — Cost Builder–aligned materials panel."""

from __future__ import annotations

import html

import streamlit as st

from app.components.estimate_materials.detail import render_material_detail_panel
from app.components.estimate_materials.list_table import build_estimate_material_lines_html
from app.components.estimate_materials.permissions import (
    EstimateMaterialsPermissions,
    load_estimate_materials_permissions,
)
from app.components.estimate_materials.state import (
    _MATERIAL_LIST_TABLE_KEY,
    clear_material_detail_state,
    clear_material_takeoff_draft,
    export_ready_key,
    material_detail_query_key,
    material_search_key,
    takeoff_open_key,
)
from app.components.estimate_materials.summary import (
    render_materials_summary_breakdown,
    render_materials_summary_panel,
)
from app.components.estimate_materials.takeoff_form import render_material_takeoff_form
from app.components.layout import render_filter_bar as layout_filter_bar
from app.components.status import status_pill_html
from app.components.table_pagination import (
    render_table_pagination_footer,
    render_table_pagination_header,
)
from app.components.tabs import render_tabs
from app.navigation import current_nav_slug, navigate_to_estimate_detail
from app.pages._core._data import ACTIVE_ESTIMATE_KEY
from app.perf_debug import perf_span
from app.services.estimate_materials_page_service import (
    _ESTIMATE_MATERIAL_PAGE_SIZE,
    clear_prepared_material_export,
    get_estimate_materials_summary,
    list_estimate_material_lines_page,
    prepare_material_export_bytes,
)
from app.ui.streamlit_perf import fragment, fragment_rerun, ips_app_rerun
from app.utils.formatting import fmt_currency

_STANDALONE_REDIRECT_KEY = "_ips_estimate_materials_redirected"


def _estimate_materials_date(est: dict) -> str:
    from app.services.estimate_expiration_service import format_estimate_date

    return format_estimate_date(est)


def _estimate_materials_expiration(est: dict) -> str:
    from app.services.estimate_expiration_service import format_effective_expiration

    return format_effective_expiration(est)


def _render_summary_card(est: dict) -> None:
    st.markdown('<div class="ips-summary-card">', unsafe_allow_html=True)
    cols = st.columns(6)
    fields = [
        ("Client", str(est.get("customer") or "—")),
        ("Job", f"{est.get('job_number') or '—'} — {est.get('project_name') or ''}"),
        ("Estimate Date", _estimate_materials_date(est)),
        ("Valid Through", _estimate_materials_expiration(est)),
        ("Prepared By", str(est.get("created_by") or "—")),
        ("Estimated Total", fmt_currency(est.get("total") or est.get("customer_price"))),
    ]
    for col, (lbl, val) in zip(cols, fields):
        with col:
            lg = " val-lg" if lbl == "Estimated Total" else ""
            st.markdown(
                f'<p class="lbl">{html.escape(lbl)}</p><p class="val{lg}">{html.escape(val)}</p>',
                unsafe_allow_html=True,
            )
    st.markdown(
        f'<p style="margin:0.5rem 0 0;">{status_pill_html(str(est.get("status") or ""))} '
        f'<strong>{html.escape(str(est.get("estimate_number") or ""))}</strong> — '
        f'{html.escape(str(est.get("project_name") or ""))}</p>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _capture_material_detail_query(estimate_id: str) -> str:
    try:
        return str(st.query_params.get(material_detail_query_key()) or "").strip()
    except Exception:
        return ""


def _clear_material_detail_query() -> None:
    try:
        qk = material_detail_query_key()
        if qk in st.query_params:
            del st.query_params[qk]
    except Exception:
        pass


@fragment
def _render_saved_lines_fragment(
    estimate_id: str,
    *,
    search: str,
    table_key: str,
) -> None:
    page = int(st.session_state.get(f"ips_pg_page_{table_key}", 1))
    page_size = int(st.session_state.get(f"ips_pg_size_{table_key}", _ESTIMATE_MATERIAL_PAGE_SIZE))
    with perf_span("estimate_materials.pagination"):
        lines_page = list_estimate_material_lines_page(
            estimate_id,
            search=search,
            page=page,
            page_size=page_size,
        )
    total = lines_page.total_count
    if total <= 0:
        st.caption("No saved material lines yet.")
        return
    render_table_pagination_header(total, table_key, item_label="line")
    with perf_span("estimate_materials.table_html"):
        html_out = build_estimate_material_lines_html(lines_page.rows, estimate_id=estimate_id)
    if html_out:
        st.markdown(html_out, unsafe_allow_html=True)
    render_table_pagination_footer(total, table_key)


@fragment
def _render_export_fragment(
    estimate_id: str,
    est: dict,
    *,
    search: str,
    can_export: bool,
) -> None:
    if not can_export:
        return
    eid = str(estimate_id or "").strip()
    ready_key = export_ready_key(eid)
    export_name = f"estimate_{est.get('estimate_number') or eid}_materials.csv"
    if st.button("Prepare Materials Export", key=f"mat_export_prepare_{eid}", use_container_width=True):
        with perf_span("estimate_materials.export"):
            data = prepare_material_export_bytes(eid, search=search)
            st.session_state[ready_key] = data
            fragment_rerun()
    if st.session_state.get(ready_key):
        st.download_button(
            "Download Materials CSV",
            data=st.session_state[ready_key],
            file_name=export_name,
            mime="text/csv",
            key=f"mat_export_download_{eid}",
            use_container_width=True,
        )


def render_estimate_materials_panel(
    *,
    estimate_id: str,
    est: dict,
    materials: list[dict] | None = None,
    summary: dict | None = None,
    permissions: EstimateMaterialsPermissions | None = None,
) -> None:
    """Materials takeoff UI — embedded in estimate detail."""
    _ = materials
    _ = summary
    with perf_span("estimate_materials.panel"):
        pick = str(estimate_id or "").strip()
        if not pick:
            st.warning("No estimate selected.")
            return
        perms = permissions or load_estimate_materials_permissions()
        mat_summary = get_estimate_materials_summary(est)
        tax_label = f"Tax ({mat_summary.tax_rate:g}%)" if mat_summary.tax_rate else "Tax"

        export_col, _ = st.columns([1, 3], gap="small")
        with export_col:
            search_q = str(st.session_state.get(material_search_key()) or "").strip()
            _render_export_fragment(pick, est, search=search_q, can_export=perms.can_export)

        _render_summary_card(est)

        mat_tab = render_tabs(
            ["Materials", "Summary"],
            session_key="ips_mat_section_tab",
            default="Materials",
        )

        detail_line_id = _capture_material_detail_query(pick)

        def _on_material_write() -> None:
            clear_prepared_material_export(pick)
            st.session_state.pop(export_ready_key(pick), None)

        if detail_line_id:
            render_material_detail_panel(
                pick,
                detail_line_id,
                can_edit=perms.can_edit,
                can_delete=perms.can_delete,
                on_close=_clear_material_detail_query,
                on_saved=_on_material_write,
            )
            return

        def _filters() -> None:
            st.text_input(
                "Search",
                placeholder="Search materials…",
                key=material_search_key(),
                label_visibility="collapsed",
            )

        layout_filter_bar(_filters)
        search_q = str(st.session_state.get(material_search_key()) or "").strip()

        main_l, main_r = st.columns([2.4, 1], gap="medium")

        with main_l:
            if mat_tab == "Summary":
                render_materials_summary_breakdown(mat_summary, tax_label=tax_label)
            else:
                _render_saved_lines_fragment(pick, search=search_q, table_key=_MATERIAL_LIST_TABLE_KEY)
                if perms.can_edit:
                    open_key = takeoff_open_key(pick)
                    if not st.session_state.get(open_key):
                        if st.button("+ Add Material Lines", key=f"mat_open_takeoff_{pick}", use_container_width=True):
                            st.session_state[open_key] = True
                            fragment_rerun()
                    else:
                        render_material_takeoff_form(
                            pick,
                            est,
                            can_edit=True,
                            on_saved=_on_material_write,
                        )

        with main_r:
            render_materials_summary_panel(mat_summary, tax_label=tax_label)
            avg_markup = 0.0
            if mat_summary.material_cost > 0:
                avg_markup = (mat_summary.material_markup / mat_summary.material_cost) * 100
            st.markdown(
                f'<div class="ips-side-line"><span>Avg material markup</span>'
                f"<span>{html.escape(f'{avg_markup:.2f}')}%</span></div>",
                unsafe_allow_html=True,
            )


def render() -> None:
    from app.pages._core._access import begin_module

    if not begin_module("estimate_materials"):
        return

    eid = str(st.session_state.get(ACTIVE_ESTIMATE_KEY) or "").strip()
    if eid:
        if current_nav_slug() == "estimates" and st.session_state.get(_STANDALONE_REDIRECT_KEY) == eid:
            st.info("Materials are managed inside the selected estimate.")
            return
        navigate_to_estimate_detail(eid, tab="Materials")
        st.session_state[_STANDALONE_REDIRECT_KEY] = eid
        ips_app_rerun()
        return

    st.session_state.pop(_STANDALONE_REDIRECT_KEY, None)
    st.info("Materials are managed inside each estimate. Open an estimate from the Estimates list.")
    if st.button("Go to Estimates", key="mat_redirect_estimates"):
        from app.navigation import ESTIMATE_DETAIL_TAB_KEY, set_nav_slug

        st.session_state.pop(ESTIMATE_DETAIL_TAB_KEY, None)
        set_nav_slug("estimates")
        ips_app_rerun()


def clear_estimate_materials_session(estimate_id: str) -> None:
    """Clear draft/detail session state when leaving estimate detail."""
    clear_material_takeoff_draft(estimate_id)
    clear_material_detail_state()


__all__ = [
    "clear_estimate_materials_session",
    "render",
    "render_estimate_materials_panel",
]
