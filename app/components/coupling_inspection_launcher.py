"""Launch Coupling Inspection workflow from jobs or equipment records."""

from __future__ import annotations

import streamlit as st

try:
    from app.navigation import set_nav_slug
except ImportError:
    from navigation import set_nav_slug  # type: ignore

SESSION_JOB_KEY = "coupling_insp_job_id"
SESSION_EQUIPMENT_KEY = "coupling_insp_equipment_id"
SESSION_INSPECTION_KEY = "coupling_insp_id"


def open_coupling_inspection(
    *,
    job_id: str | None = None,
    equipment_id: str | None = None,
    inspection_id: str | None = None,
) -> None:
    if job_id:
        st.session_state[SESSION_JOB_KEY] = str(job_id).strip()
    if equipment_id:
        st.session_state[SESSION_EQUIPMENT_KEY] = str(equipment_id).strip()
    if inspection_id:
        st.session_state[SESSION_INSPECTION_KEY] = str(inspection_id).strip()
    else:
        st.session_state.pop(SESSION_INSPECTION_KEY, None)
    set_nav_slug("coupling_inspection")
    st.rerun()


def coupling_inspection_context() -> dict[str, str | None]:
    return {
        "job_id": str(st.session_state.get(SESSION_JOB_KEY) or "").strip() or None,
        "equipment_id": str(st.session_state.get(SESSION_EQUIPMENT_KEY) or "").strip() or None,
        "inspection_id": str(st.session_state.get(SESSION_INSPECTION_KEY) or "").strip() or None,
    }


def render_coupling_inspection_launcher(
    *,
    job_id: str | None = None,
    equipment_id: str | None = None,
    key_prefix: str = "ci_launch",
) -> None:
    st.markdown("#### Inspection Forms")
    st.caption("Digital coupling inspection with torque verification, photos, signatures, and PDF export.")
    if st.button(
        "Coupling Inspection",
        type="primary",
        use_container_width=True,
        key=f"{key_prefix}_open",
    ):
        open_coupling_inspection(job_id=job_id, equipment_id=equipment_id)
