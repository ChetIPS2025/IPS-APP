"""Shared CRUD helpers for Phase 3 module pages (no UI redesign)."""

from __future__ import annotations

import streamlit as st


def is_demo_id(row_id: str | None) -> bool:
    """True when row id is from demo fallback — skip Supabase writes."""
    rid = str(row_id or "").strip()
    return not rid or rid.startswith("demo-")


def apply_persist_feedback(ok: bool, msg: str, *, clear_keys: tuple[str, ...] = ()) -> bool:
    """Show success/error; return True when save succeeded."""
    if ok:
        st.success(msg)
        for k in clear_keys:
            st.session_state.pop(k, None)
        return True
    st.error(msg or "Save failed.")
    return False


def open_form_flag(key: str) -> bool:
    return bool(st.session_state.get(key))


def set_form_flag(key: str, open_: bool = True) -> None:
    if open_:
        st.session_state[key] = True
    else:
        st.session_state.pop(key, None)
