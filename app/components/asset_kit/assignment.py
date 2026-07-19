"""Lazy assignment / accountability section."""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.components.asset_kit.reference_options import get_kit_reference_options
from app.components.asset_kit.state import assignment_edit_key
from app.services.serialized_tool_service import dispatch_trailer_to_job
from app.ui.streamlit_perf import ips_app_rerun


def render_assignment_section(asset: dict, aid: str) -> None:
    st.markdown("##### Assignment / Accountability")
    cur_sup = str(asset.get("assigned_to_name") or asset.get("operator") or "—")
    cur_job_id = str(asset.get("assigned_job_id") or "")
    job_label = cur_job_id or "—"
    st.markdown(
        f"Supervisor: **{cur_sup}** · Job ID: **{job_label}**",
    )
    edit_key = assignment_edit_key(aid)
    if not st.session_state.get(edit_key):
        if st.button("Edit Assignment", key=f"kit_assign_edit_{aid}"):
            st.session_state[edit_key] = True
            st.rerun()
        return

    from app.perf_debug import perf_span

    with perf_span("asset_kit.assignment_options"):
        refs = get_kit_reference_options(include_employees=True, include_jobs=True)
    emp_opts = list(refs.employees)
    job_opts = list(refs.jobs)
    emp_labels = [x[0] for x in emp_opts]
    job_labels = [x[0] for x in job_opts]

    with st.form(f"kit_assign_{aid}"):
        c1, c2 = st.columns(2)
        with c1:
            sup_idx = emp_labels.index(cur_sup) if cur_sup in emp_labels else 0
            sup_label = st.selectbox("Assigned supervisor", emp_labels, index=sup_idx)
        with c2:
            job_idx = 0
            for i, (_, jid) in enumerate(job_opts):
                if jid == cur_job_id:
                    job_idx = i
                    break
            job_label_sel = st.selectbox("Assigned job", job_labels, index=job_idx)
        notes = st.text_area("Assignment notes", value="", height=60)
        save = st.form_submit_button("Save Assignment", type="primary")
        cancel = st.form_submit_button("Cancel")

    if cancel:
        st.session_state[edit_key] = False
        st.rerun()
    if save:
        emp = next((e for lbl, e in emp_opts if lbl == sup_label), {})
        jid = next((j for lbl, j in job_opts if lbl == job_label_sel), "")
        result = dispatch_trailer_to_job(
            aid,
            job_id=jid or None,
            employee_id=str(emp.get("id") or "") or None,
            employee_name=sup_label if sup_label != "— None —" else "",
            notes=notes,
        )
        if result.ok:
            st.session_state[edit_key] = False
            ips_app_rerun()
        else:
            st.error(result.error or "Could not save assignment.")
