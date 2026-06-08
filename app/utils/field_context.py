"""Shared session context for Field Supervisor Mode (active job, navigation helpers)."""

from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from app.services.job_service import job_row_select_label
except ImportError:
    from services.job_service import job_row_select_label  # type: ignore

FIELD_JOB_SESSION_KEY = "ips_field_job_id"
FIELD_EXPANDED_JOB_KEY = "ips_field_expanded_job_id"
FIELD_EXPANDED_TASK_KEY = "ips_field_expanded_task_id"
FIELD_EXPANDED_INVENTORY_KEY = "ips_field_expanded_inv_id"
FIELD_EXPANDED_ASSET_KEY = "ips_field_expanded_asset_id"
FIELD_DAY_TAB_KEY = "ips_field_day_tab"
FIELD_PAGE_SLUGS = frozenset(
    {
        "field_dashboard",
        "field_day",
        "field_daily_reports",
        "field_crew_time",
    }
)
FIELD_DAY_TABS = ("Report", "Crew", "Time", "Tasks")
SDR_WIZARD_STEP_PREFIX = "ips_sdr_wizard_step"


def _inject_field_job_bar_css() -> None:
    if st.session_state.get("_ips_field_job_bar_css"):
        return
    st.session_state["_ips_field_job_bar_css"] = True
    st.markdown(
        """
<style id="ips-field-job-bar-v1">
.ips-field-job-bar {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 12px;
  padding: 10px 12px 6px;
  margin: 0 0 0.75rem;
}
.ips-field-job-bar [data-testid="stCaptionContainer"] p {
  margin-top: 0.15rem;
  font-size: 0.72rem;
  color: #475569;
}
</style>
""",
        unsafe_allow_html=True,
    )


def is_field_mode() -> bool:
    return bool(st.session_state.get("ips_field_mode"))


def _active_nav_slug(slug: str | None = None) -> str:
    if slug:
        return str(slug).strip()
    try:
        from app.pages._core._session import nav_slug
    except ImportError:
        from pages._core._session import nav_slug  # type: ignore
    return str(nav_slug() or st.session_state.get("ips_nav_page") or "").strip()


def is_field_context(*, slug: str | None = None) -> bool:
    """True when UI should use field-optimized layouts (wizard, expand rows, slim tabs)."""
    if is_field_mode():
        return True
    return _active_nav_slug(slug) in FIELD_PAGE_SLUGS


def get_field_day_tab() -> str:
    tab = str(st.session_state.get(FIELD_DAY_TAB_KEY) or "Report").strip()
    return tab if tab in FIELD_DAY_TABS else "Report"


def set_field_day_tab(tab: str) -> None:
    picked = str(tab or "Report").strip()
    st.session_state[FIELD_DAY_TAB_KEY] = picked if picked in FIELD_DAY_TABS else "Report"


def navigate_to_field_day(*, job_id: str | None = None, tab: str = "Report") -> None:
    set_field_day_tab(tab)
    navigate_to_field_page("field_day", job_id=job_id)


def sdr_wizard_step(job_id: str) -> int:
    jid = str(job_id or "").strip()
    key = f"{SDR_WIZARD_STEP_PREFIX}_{jid}"
    try:
        step = int(st.session_state.get(key) or 0)
    except (TypeError, ValueError):
        step = 0
    return max(0, min(2, step))


def set_sdr_wizard_step(job_id: str, step: int) -> None:
    jid = str(job_id or "").strip()
    if not jid:
        return
    st.session_state[f"{SDR_WIZARD_STEP_PREFIX}_{jid}"] = max(0, min(2, int(step)))


def inject_field_day_shell_css() -> None:
    if st.session_state.get("_ips_field_day_shell_css"):
        return
    st.session_state["_ips_field_day_shell_css"] = True
    inject_field_row_expand_css()
    st.markdown(
        """
<style id="ips-field-day-shell-v1">
.ips-field-day-shell {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px 12px 4px;
  margin: 0 0 0.75rem;
}
.ips-field-wizard-steps {
  display: flex;
  gap: 0.35rem;
  margin: 0 0 0.65rem;
  flex-wrap: wrap;
}
.ips-field-wizard-step {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.28rem 0.55rem;
  border-radius: 999px;
  border: 1px solid #cbd5e1;
  color: #64748b;
  background: #f8fafc;
}
.ips-field-wizard-step.is-active {
  border-color: #2563eb;
  color: #1d4ed8;
  background: #eff6ff;
}
.ips-field-wizard-step.is-done {
  border-color: #86efac;
  color: #166534;
  background: #f0fdf4;
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_field_day_tab_bar(*, key_prefix: str = "field_day") -> str:
    """Horizontal section picker for the unified field day shell."""
    inject_field_day_shell_css()
    tabs = list(FIELD_DAY_TABS)
    current = get_field_day_tab()
    if current not in tabs:
        current = tabs[0]
        set_field_day_tab(current)
    st.markdown('<div class="ips-field-day-shell">', unsafe_allow_html=True)
    picked = st.radio(
        "Today's work",
        tabs,
        index=tabs.index(current),
        horizontal=True,
        key=f"{key_prefix}_tab_radio",
        label_visibility="collapsed",
    )
    set_field_day_tab(str(picked))
    st.caption("One job, four workflows — switch sections without leaving the page.")
    st.markdown("</div>", unsafe_allow_html=True)
    return str(picked)


def render_field_checkin_block(
    *,
    job_id: str,
    user_id: str | None,
    user_name: str,
    admin: bool,
    key_prefix: str = "fci",
) -> None:
    """Site check-in / check-out for the active field job."""
    jid = str(job_id or "").strip()
    if not jid:
        return
    try:
        from app.services.job_checkins import check_in, check_out, fetch_open_checkin
    except ImportError:
        from services.job_checkins import check_in, check_out, fetch_open_checkin  # type: ignore

    open_ci = fetch_open_checkin(job_id=jid, user_id=user_id, admin=admin)
    with st.expander("Site check-in / check-out", expanded=open_ci is None):
        if open_ci:
            st.success(f"Checked in since {str(open_ci.get('check_in_time') or '')[:16]}")
            note_out = st.text_input("Check-out note", key=f"{key_prefix}_co_note")
            if st.button("Check out", type="primary", key=f"{key_prefix}_checkout"):
                try:
                    check_out(checkin_id=str(open_ci["id"]), notes=note_out, admin=admin)
                    st.success("Checked out.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            note_in = st.text_input("Check-in note (GPS optional later)", key=f"{key_prefix}_ci_note")
            if st.button("Check in on site", type="primary", key=f"{key_prefix}_checkin"):
                try:
                    check_in(
                        job_id=jid,
                        user_id=user_id,
                        user_name=user_name,
                        notes=note_in,
                        admin=admin,
                    )
                    st.success("Checked in.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))


def get_field_job_id() -> str:
    return str(st.session_state.get(FIELD_JOB_SESSION_KEY) or "").strip()


def set_field_job_id(job_id: str) -> None:
    jid = str(job_id or "").strip()
    if jid:
        st.session_state[FIELD_JOB_SESSION_KEY] = jid


def clear_field_job_id() -> None:
    st.session_state.pop(FIELD_JOB_SESSION_KEY, None)


def job_index_for_id(jobs: list[dict[str, Any]], job_id: str | None) -> int:
    target = str(job_id or "").strip()
    ids = [str(j.get("id") or "").strip() for j in jobs if isinstance(j, dict)]
    if target and target in ids:
        return ids.index(target)
    return 0


def render_field_job_bar(
    jobs: list[dict[str, Any]],
    *,
    key_prefix: str = "field",
) -> tuple[str, str, dict[str, Any] | None]:
    """Sticky active-job picker shared across field modules."""
    _inject_field_job_bar_css()
    if not jobs:
        st.warning("No jobs loaded.")
        return "", "", None

    labels = [job_row_select_label(j) for j in jobs]
    ids = [str(j.get("id") or "").strip() for j in jobs]
    ix = job_index_for_id(jobs, get_field_job_id())
    st.markdown('<div class="ips-field-job-bar">', unsafe_allow_html=True)
    picked_ix = st.selectbox(
        "Active job",
        range(len(ids)),
        index=ix,
        format_func=lambda i: labels[i],
        key=f"{key_prefix}_field_job_ix",
    )
    jid = ids[int(picked_ix)]
    set_field_job_id(jid)
    st.caption("This job carries across Daily Report, Crew Time, and Tasks in Field Mode.")
    st.markdown("</div>", unsafe_allow_html=True)
    job = jobs[int(picked_ix)]
    return jid, labels[int(picked_ix)], job


def navigate_to_field_page(slug: str, *, job_id: str | None = None) -> None:
    if job_id:
        set_field_job_id(job_id)
    try:
        from app.navigation import set_nav_slug
    except ImportError:
        from navigation import set_nav_slug  # type: ignore
    set_nav_slug(slug)


def inject_field_row_expand_css() -> None:
    if st.session_state.get("_ips_field_row_expand_css"):
        return
    st.session_state["_ips_field_row_expand_css"] = True
    st.markdown(
        """
<style id="ips-field-row-expand-v1">
.ips-field-row-expand {
  background: #f8fafc;
  border-top: 1px solid #dbeafe;
  border-bottom: 2px solid #cbd5e1;
  padding: 12px 14px 16px;
  margin: 0;
}
.ips-field-scan-bar {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 12px 14px 8px;
  margin: 0 0 0.75rem;
}
.ips-field-scan-bar [data-testid="stCaptionContainer"] p {
  margin-top: 0.35rem;
  font-size: 0.72rem;
  color: #475569;
}
</style>
""",
        unsafe_allow_html=True,
    )


def field_expanded_id(session_key: str) -> str | None:
    rid = str(st.session_state.get(session_key) or "").strip()
    return rid or None


def toggle_field_expanded(session_key: str, record_id: str) -> None:
    rid = str(record_id or "").strip()
    if not rid:
        return
    if field_expanded_id(session_key) == rid:
        st.session_state.pop(session_key, None)
    else:
        st.session_state[session_key] = rid


def clear_field_expanded(session_key: str) -> None:
    st.session_state.pop(session_key, None)


def render_field_scan_bar(*actions: tuple[str, str]) -> None:
    """Primary scan CTAs for field inventory/assets. Each action is (label, nav slug)."""
    if not actions:
        return
    inject_field_row_expand_css()
    st.markdown('<div class="ips-field-scan-bar">', unsafe_allow_html=True)
    cols = st.columns(len(actions))
    for col, (label, slug) in zip(cols, actions):
        with col:
            if st.button(label, key=f"field_scan_{slug}", type="primary", use_container_width=True):
                navigate_to_field_page(slug)
    st.caption(
        "Scan a QR: inventory (use/consume), serialized tools (check out/in), or small tools (count/audit)."
    )
    st.markdown("</div>", unsafe_allow_html=True)


def open_job_detail(job_id: str) -> None:
    """Jump to My Jobs and open the job detail modal."""
    jid = str(job_id or "").strip()
    if not jid:
        return
    set_field_job_id(jid)
    try:
        from app.pages._core._session import select_key
    except ImportError:
        from pages._core._session import select_key  # type: ignore
    st.session_state["selected_job_id"] = jid
    st.session_state["show_job_detail_modal"] = True
    st.session_state["ips_jobs_detail_modal_id"] = jid
    st.session_state[select_key("jobs")] = jid
    navigate_to_field_page("jobs", job_id=jid)
