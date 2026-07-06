"""Compact header menu for Job Details modal."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import streamlit as st

try:
    from app.auth import current_role
    from app.services.jobs_service import can_manage_job_actions
except ImportError:
    from auth import current_role  # type: ignore
    from services.jobs_service import can_manage_job_actions  # type: ignore


def _confirm_state_key(job_id: str, action: str) -> str:
    return f"confirm_{action}_job_{job_id}"


def _job_is_archived(job: dict[str, Any]) -> bool:
    if bool(job.get("is_deleted")):
        return True
    status = str(job.get("status") or "").strip().lower()
    return status in {"deleted", "archived"}


def _normalize_status(job: dict[str, Any]) -> str:
    raw = str(job.get("status") or "").strip().lower().replace("_", " ")
    mapping = {
        "completed": "Completed",
        "complete": "Completed",
        "closed": "Closed",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }
    return mapping.get(raw, str(job.get("status") or "Active").strip() or "Active")


def _is_job_admin() -> bool:
    return str(current_role() or "").strip().lower() == "admin"


def _menu_button(*, marker: str, label: str, key: str, tone: str = "default") -> bool:
    st.markdown(
        f'<span class="job-detail-menu-marker job-detail-menu-{marker} '
        f'job-detail-menu-tone-{tone}" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    return st.button(label, key=key, use_container_width=True)


def _linked_estimate_for_job(job: dict[str, Any]) -> dict[str, Any] | None:
    jid = str(job.get("id") or "").strip()
    job_est_id = str(job.get("estimate_id") or "").strip()
    if not jid and not job_est_id:
        return None
    try:
        from app.pages._core._data import load_estimates
    except ImportError:
        from pages._core._data import load_estimates  # type: ignore
    linked = [
        e
        for e in load_estimates()
        if str(e.get("job_id") or "") == jid or (job_est_id and str(e.get("id") or "") == job_est_id)
    ]
    return linked[0] if linked else None


def _generate_estimate_pdf(est: dict[str, Any]) -> tuple[bytes | None, str, str]:
    """Return proposal PDF bytes, download name, and optional user-facing error note."""
    est_no = str(est.get("estimate_number") or "estimate").strip() or "estimate"
    try:
        from app.services.proposal_pdf_service import generate_estimate_proposal_pdf_by_id
    except ImportError:
        from services.proposal_pdf_service import generate_estimate_proposal_pdf_by_id  # type: ignore
    try:
        pdf_bytes = generate_estimate_proposal_pdf_by_id(str(est.get("id") or ""), est)
    except RuntimeError as exc:
        return None, "", str(exc).strip()
    except Exception as exc:
        return None, "", str(exc).strip() or "Could not build proposal PDF."
    return pdf_bytes, f"{est_no}_proposal.pdf", ""


def render_job_detail_header_menu(
    job: dict[str, Any],
    *,
    on_edit: Callable[[dict[str, Any]], None],
    on_add_task: Callable[[dict[str, Any]], None] | None = None,
    on_assign_crew: Callable[[dict[str, Any]], None] | None = None,
    on_print_packet: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    """Vertical ⋮ menu — edit, crew, task, print, export, archive, delete."""
    jid = str(job.get("id") or "").strip()
    if not jid:
        return
    job_key = "".join(ch if ch.isalnum() else "_" for ch in jid) or "job"
    archived = _job_is_archived(job)
    can_manage = can_manage_job_actions()
    is_admin = _is_job_admin()
    status = _normalize_status(job)

    st.markdown(
        '<span class="job-detail-header-menu-marker ips-jobs-row-menu-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.popover(
        "⋮",
        help="Job actions",
        type="secondary",
        key=f"job_detail_menu_{job_key}",
    ):
        st.markdown(
            '<span class="job-detail-header-menu-panel" aria-hidden="true"></span>',
            unsafe_allow_html=True,
        )

        if _menu_button(marker="edit", label="Edit Job", key=f"job_detail_edit_{job_key}"):
            on_edit(job)
            st.rerun()

        if on_assign_crew is not None and _menu_button(
            marker="crew",
            label="Assign Crew",
            key=f"job_detail_crew_{job_key}",
        ):
            on_assign_crew(job)
            st.rerun()

        if on_add_task is not None and _menu_button(
            marker="task",
            label="Add Task",
            key=f"job_detail_task_{job_key}",
        ):
            on_add_task(job)
            st.rerun()

        if on_print_packet is not None and _menu_button(
            marker="print",
            label="Print Job Packet",
            key=f"job_detail_print_{job_key}",
        ):
            on_print_packet(job)
            st.rerun()

        linked_est = _linked_estimate_for_job(job)
        export_cache_key = f"job_detail_export_pdf_{job_key}"
        cached_export = st.session_state.get(export_cache_key)
        if isinstance(cached_export, tuple) and len(cached_export) == 2:
            pdf_bytes, pdf_name = cached_export
            if pdf_bytes:
                st.download_button(
                    "Export PDF",
                    data=pdf_bytes,
                    file_name=pdf_name,
                    mime="application/pdf",
                    key=f"{export_cache_key}_download",
                    use_container_width=True,
                )
        elif linked_est and _menu_button(
            marker="export",
            label="Export PDF",
            key=f"{export_cache_key}_generate",
        ):
            pdf_bytes, pdf_name, pdf_err = _generate_estimate_pdf(linked_est)
            if pdf_bytes:
                st.session_state[export_cache_key] = (pdf_bytes, pdf_name)
                st.rerun()
            elif pdf_err:
                st.warning(pdf_err)
            else:
                st.info("Could not build proposal PDF.")
        elif _menu_button(
            marker="export",
            label="Export PDF",
            key=f"job_detail_export_pdf_missing_{job_key}",
        ):
            st.info("Link an estimate to this job to export a proposal PDF.")

        if not archived and can_manage:
            st.markdown('<hr class="job-detail-menu-divider" aria-hidden="true">', unsafe_allow_html=True)

            if status not in {"Completed", "Closed"} and _menu_button(
                marker="archive",
                label="Archive Job",
                key=f"job_detail_archive_{job_key}",
                tone="warning",
            ):
                st.session_state[_confirm_state_key(jid, "delete")] = True
                st.rerun()

            if is_admin and _menu_button(
                marker="delete",
                label="Delete",
                key=f"job_detail_delete_{job_key}",
                tone="danger",
            ):
                st.session_state[_confirm_state_key(jid, "delete")] = True
                st.rerun()
