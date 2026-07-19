"""Lazy audit history and paginated audit form."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.auth import current_profile
from app.components.asset_kit.reference_options import get_kit_reference_options
from app.components.asset_kit.state import KIT_AUDIT_PAGE_SIZE, audit_page_key, audits_loaded_key, sk
from app.components.kit_audit_item_ui import (
    clear_audit_item_photos,
    collect_audit_line_from_session,
    render_audit_item_fields,
)
from app.pages._core.page_data_cache import page_data_cache_get
from app.services.asset_kits_service import get_asset_kit_audits, kit_data_version
from app.services.serialized_tool_service import audit_trailer_tools
from app.ui.streamlit_perf import ips_app_rerun
from app.utils.formatting import fmt_currency, fmt_date


def render_recent_audits_section(aid: str) -> None:
    loaded_key = audits_loaded_key(aid)
    if not st.session_state.get(loaded_key):
        if st.button("Load Recent Audits", key=f"kit_load_audits_{aid}"):
            st.session_state[loaded_key] = True
            st.rerun()
        return

    version = kit_data_version(aid)

    def _load() -> list[dict[str, Any]]:
        return get_asset_kit_audits(aid, limit=5)

    audits = page_data_cache_get(f"kit_audits_{aid}_v{version}", _load)
    if not audits:
        st.caption("No audits recorded yet.")
    else:
        with st.expander("Recent audits", expanded=False):
            for a in audits:
                st.markdown(
                    f"**{fmt_date(a.get('audit_date'))}** — "
                    f"Missing: {a.get('missing_item_count')} · Damaged: {a.get('damaged_item_count')} · "
                    f"By: {a.get('performed_by_name') or '—'}"
                )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Hide Recent Audits", key=f"kit_hide_audits_{aid}"):
            st.session_state[loaded_key] = False
            st.rerun()
    with c2:
        if st.button("Refresh Recent Audits", key=f"kit_refresh_audits_{aid}"):
            from app.pages._core.page_data_cache import clear_page_data_cache_key

            clear_page_data_cache_key(f"kit_audits_{aid}_v{version}")
            st.rerun()


def render_audit_form(asset: dict, aid: str, items: list[dict]) -> None:
    if st.button("← Back to kit list", key=f"kit_back_audit_{aid}"):
        st.session_state[sk(aid, "view")] = "list"
        st.rerun()
    st.markdown("##### Kit Audit / Inspection")
    st.caption(
        "Verify every item with status, condition, and photo proof. "
        "Missing items require a note explaining where the item was expected or what was checked."
    )
    prof = current_profile() or {}
    user_id = str(prof.get("id") or "").strip() or None

    with st.spinner("Loading audit options..."):
        from app.perf_debug import perf_span

        with perf_span("asset_kit.audit_options"):
            refs = get_kit_reference_options(include_employees=True, include_jobs=True)
    emp_opts = list(refs.employees)
    job_opts = list(refs.jobs)
    emp_labels = [x[0] for x in emp_opts]
    job_labels = [x[0] for x in job_opts]

    c1, c2 = st.columns(2)
    with c1:
        performer = st.text_input(
            "Performed by name",
            value=str(prof.get("full_name") or prof.get("name") or ""),
            key=f"kit_audit_perf_{aid}",
        )
        phone = st.text_input("Phone", key=f"kit_audit_phone_{aid}")
    with c2:
        sup = st.selectbox("Supervisor responsible", emp_labels, key=f"kit_audit_sup_{aid}")
        job_label = st.selectbox("Job", job_labels, key=f"kit_audit_job_{aid}")
    audit_notes = st.text_area("Audit notes (optional)", height=50, key=f"kit_audit_notes_{aid}")

    if not items:
        st.warning("No kit items to audit.")
        return

    page_key = audit_page_key(aid)
    total_pages = max(1, (len(items) + KIT_AUDIT_PAGE_SIZE - 1) // KIT_AUDIT_PAGE_SIZE)
    page = int(st.session_state.get(page_key, 1))
    page = max(1, min(page, total_pages))
    st.session_state[page_key] = page
    start = (page - 1) * KIT_AUDIT_PAGE_SIZE
    page_items = items[start : start + KIT_AUDIT_PAGE_SIZE]

    st.caption(f"Audit items {start + 1}–{min(start + len(page_items), len(items))} of {len(items)}")
    key_prefix = f"kit_audit_{aid}"
    for idx, it in enumerate(page_items):
        st.markdown(f"#### Item {start + idx + 1}")
        render_audit_item_fields(
            it,
            trailer_id=aid,
            key_prefix=key_prefix,
            uploaded_by=user_id,
            show_quantity=True,
        )
        st.divider()

    if total_pages > 1:
        pc1, pc2, pc3 = st.columns([1, 2, 1])
        with pc1:
            if st.button("Previous audit page", disabled=page <= 1, key=f"kit_audit_prev_{aid}"):
                st.session_state[page_key] = page - 1
                st.rerun()
        with pc2:
            st.markdown(f"**Page {page} of {total_pages}**")
        with pc3:
            if st.button("Next audit page", disabled=page >= total_pages, key=f"kit_audit_next_{aid}"):
                st.session_state[page_key] = page + 1
                st.rerun()

    if st.button("Submit Audit", type="primary", key=f"kit_audit_submit_{aid}", use_container_width=True):
        if not str(performer or "").strip():
            st.error("Performed by name is required.")
            return
        lines = [
            collect_audit_line_from_session(
                it,
                trailer_id=aid,
                key_prefix=key_prefix,
                show_quantity=True,
            )
            for it in items
        ]
        emp = next((e for lbl, e in emp_opts if lbl == sup), {})
        jid = next((j for lbl, j in job_opts if lbl == job_label), "")
        result = audit_trailer_tools(
            aid,
            {
                "performed_by_name": performer,
                "performed_by_phone": phone,
                "performed_by_user_id": user_id,
                "performed_by_employee_id": str(prof.get("employee_id") or "").strip() or None,
                "assigned_supervisor_id": emp.get("id"),
                "assigned_supervisor_name": sup if sup != "— None —" else "",
                "job_id": jid or None,
                "notes": audit_notes,
                "audit_type": "Full",
            },
            lines,
        )
        if result.ok:
            clear_audit_item_photos(aid, [str(i.get("id") or "") for i in items])
            data = result.data or {}
            miss_v = data.get("missing_value") or 0
            dmg_v = data.get("damaged_value") or 0
            if miss_v or dmg_v:
                st.warning(
                    f"Audit saved with issues — missing value: {fmt_currency(miss_v)}, "
                    f"damaged value: {fmt_currency(dmg_v)}"
                )
            else:
                st.success("Audit completed — all items accounted for.")
            st.session_state[sk(aid, "view")] = "list"
            st.session_state.pop(page_key, None)
            ips_app_rerun()
        else:
            st.error(result.error or "Audit failed.")
