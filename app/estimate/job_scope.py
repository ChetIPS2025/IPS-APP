"""Job Scope tab: session-bound text areas, debounced DB sync, load rebinding."""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import streamlit as st

# Quiet period after last edit signal before autos PATCH (seconds).
SCOPE_AUTOSAVE_DEBOUNCE_S = 1.75


def _scope_sig(estimate_id: str | None) -> str:
    s = str(estimate_id or "").strip()
    return s if s else "new"


def scope_text_area_keys(estimate_id: str | None) -> tuple[str, str]:
    """Streamlit widget keys scoped per open estimate so reopening cannot reuse stale widget state."""
    sig = _scope_sig(estimate_id)
    return (f"est_scope_sow_{sig}", f"est_scope_cr_{sig}")


def _scope_last_saved_keys(estimate_id: str | None) -> tuple[str, str]:
    sig = _scope_sig(estimate_id)
    return (f"est_scope_saved_sow_{sig}", f"est_scope_saved_cr_{sig}")


def refresh_scope_saved_baseline_from_est(est: dict, estimate_id: str | None = None) -> None:
    """After a full estimate save, align widgets + dirty baselines with ``est`` (no bind-signature change)."""
    s = str(est.get("scope_of_work") or "")
    c = str(est.get("customer_responsibilities") or "")
    k_sow, k_cr = scope_text_area_keys(estimate_id)
    lk_sow, lk_cr = _scope_last_saved_keys(estimate_id)
    st.session_state[k_sow] = s
    st.session_state[k_cr] = c
    st.session_state[lk_sow] = s
    st.session_state[lk_cr] = c


def ensure_scope_widgets_bound(est: dict, estimate_id: str | None) -> None:
    """
    When the opened estimate changes, copy DB-backed scope strings into widget session keys
    so tab switches do not resurrect stale text or drop in-progress edits for the wrong quote.
    """
    sig = _scope_sig(estimate_id)
    if st.session_state.get("_est_scope_bind_sig") == sig:
        return
    st.session_state["_est_scope_bind_sig"] = sig
    k_sow, k_cr = scope_text_area_keys(estimate_id)
    lk_sow, lk_cr = _scope_last_saved_keys(estimate_id)
    st.session_state[k_sow] = str(est.get("scope_of_work") or "")
    st.session_state[k_cr] = str(est.get("customer_responsibilities") or "")
    st.session_state[lk_sow] = st.session_state[k_sow]
    st.session_state[lk_cr] = st.session_state[k_cr]
    st.session_state["est_scope_last_edit_mono"] = 0.0
    st.session_state["est_scope_autosave_status"] = "idle"
    st.session_state.pop("est_scope_autosave_err", None)


def bump_scope_edit_clock() -> None:
    st.session_state["est_scope_last_edit_mono"] = time.monotonic()
    if st.session_state.get("est_scope_autosave_status") == "error":
        st.session_state["est_scope_autosave_status"] = "idle"
        st.session_state.pop("est_scope_autosave_err", None)


def scope_is_dirty(estimate_id: str | None) -> bool:
    k_sow, k_cr = scope_text_area_keys(estimate_id)
    lk_sow, lk_cr = _scope_last_saved_keys(estimate_id)
    sow = str(st.session_state.get(k_sow, ""))
    cr = str(st.session_state.get(k_cr, ""))
    return sow != str(st.session_state.get(lk_sow, "")) or cr != str(st.session_state.get(lk_cr, ""))


def _scope_values_for_save(estimate_id: str | None) -> tuple[str, str]:
    k_sow, k_cr = scope_text_area_keys(estimate_id)
    return (str(st.session_state.get(k_sow, "")), str(st.session_state.get(k_cr, "")))


def _mark_scope_saved(estimate_id: str | None, sow: str, cr: str) -> None:
    lk_sow, lk_cr = _scope_last_saved_keys(estimate_id)
    st.session_state[lk_sow] = sow
    st.session_state[lk_cr] = cr
    st.session_state["est_scope_autosave_status"] = "saved"
    st.session_state["est_scope_saved_clock"] = datetime.now().strftime("%I:%M %p")
    st.session_state.pop("est_scope_autosave_err", None)


def maybe_autosave_scope(est: dict, estimate_id: str | None) -> None:
    """Debounced PATCH when an estimate row exists; no ``st.rerun``."""
    from app.estimate.persistence import patch_estimate_job_scope

    eid = str(estimate_id or "").strip()
    if not eid or not scope_is_dirty(estimate_id):
        return
    last_edit = float(st.session_state.get("est_scope_last_edit_mono") or 0.0)
    if last_edit <= 0.0:
        return
    if time.monotonic() - last_edit < SCOPE_AUTOSAVE_DEBOUNCE_S:
        return

    sow, cr = _scope_values_for_save(estimate_id)
    st.session_state["est_scope_autosave_status"] = "saving"
    ok, err = patch_estimate_job_scope(eid, est, scope_of_work=sow, customer_responsibilities=cr)
    if ok:
        _mark_scope_saved(estimate_id, sow, cr)
        st.session_state["est_scope_last_edit_mono"] = 0.0
        est.pop("proposal_preview_html", None)
    else:
        st.session_state["est_scope_autosave_status"] = "error"
        st.session_state["est_scope_autosave_err"] = err


def render_scope_autosave_poller(est: dict, estimate_id: str | None) -> None:
    """Periodic fragment rerun (Streamlit ≥1.33) so idle debounced saves flush without other clicks."""
    frag = getattr(st, "fragment", None)
    eid = str(estimate_id or "").strip()
    if frag is None or not eid:
        return
    try:

        @frag(run_every=timedelta(seconds=2))
        def _poll() -> None:
            maybe_autosave_scope(est, estimate_id)

        _poll()
    except Exception:
        try:

            @frag(run_every=2.0)
            def _poll2() -> None:
                maybe_autosave_scope(est, estimate_id)

            _poll2()
        except Exception:
            return


def save_scope_now(est: dict, estimate_id: str | None) -> tuple[bool, str]:
    """Immediate PATCH (manual save). ``patch_estimate_job_scope`` rolls back ``est`` on failure."""
    from app.estimate.persistence import patch_estimate_job_scope

    eid = str(estimate_id or "").strip()
    if not eid:
        return False, "Save the estimate once before syncing scope to the database."
    sow, cr = _scope_values_for_save(estimate_id)
    ok, err = patch_estimate_job_scope(eid, est, scope_of_work=sow, customer_responsibilities=cr)
    if ok:
        _mark_scope_saved(estimate_id, sow, cr)
        st.session_state["est_scope_last_edit_mono"] = 0.0
        est.pop("proposal_preview_html", None)
        return True, ""
    st.session_state["est_scope_autosave_status"] = "error"
    st.session_state["est_scope_autosave_err"] = err
    return False, err
