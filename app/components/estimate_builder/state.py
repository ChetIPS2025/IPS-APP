"""Estimate Cost Builder session state and draft helpers."""

from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

import streamlit as st

DEFAULT_BATCH_ROW_COUNT = 5
MAX_BATCH_DRAFT_ROWS = 25
ESTIMATE_COST_LINE_PAGE_SIZE = 25
COST_BUILDER_SECTION_KEY = "ips_estimate_cost_builder_section"


def batch_draft_key(section: str, key_prefix: str, eid: str) -> str:
    return f"{key_prefix}_{section}_batch_{eid}"


def form_state_key(section: str, eid: str, *, prefix: str = "ecb") -> str:
    return f"{prefix}_form_{section}_{eid}"


def line_page_table_key(category: str, eid: str) -> str:
    return f"ecb_lines_{category}_{eid}"


def clear_estimate_builder_draft(estimate_id: str, section: str, *, key_prefix: str = "ecb") -> None:
    """Clear draft rows, form-open flag, and related widget keys for one section."""
    eid = str(estimate_id or "").strip()
    sec = str(section or "").strip().lower()
    if not eid or not sec:
        return
    draft_key = batch_draft_key(sec[:3], f"{key_prefix}_{sec[:3]}", eid)
    fk = form_state_key(sec[:3], eid, prefix=key_prefix)
    for key in (draft_key, fk, f"{key_prefix}_adv_mk_open_{eid}"):
        st.session_state.pop(key, None)
    prefix = f"{key_prefix}_"
    for key in list(st.session_state.keys()):
        sk = str(key)
        if eid in sk and sk.startswith(prefix) and (
            f"_{sec}" in sk or f"_{sec[:3]}_" in sk or f"batch_{eid}" in sk
        ):
            st.session_state.pop(key, None)


def clear_all_estimate_builder_drafts(estimate_id: str) -> None:
    for section in ("mat", "lab", "eq", "trv", "sub", "oth"):
        clear_estimate_builder_draft(estimate_id, section)


def new_blank_batch_row(**extra: str) -> dict[str, str]:
    return {"rid": uuid4().hex[:8], **extra}


def initial_batch_draft_rows(count: int = DEFAULT_BATCH_ROW_COUNT, **extra: str) -> list[dict[str, str]]:
    return [new_blank_batch_row(**extra) for _ in range(count)]


def ensure_batch_draft(
    draft_key: str,
    init_rows: Callable[[], list[dict[str, str]]],
) -> list[dict[str, str]]:
    rows = list(st.session_state.get(draft_key) or [])
    if len(rows) < DEFAULT_BATCH_ROW_COUNT:
        st.session_state[draft_key] = init_rows()
        rows = list(st.session_state.get(draft_key) or [])
    return rows


def open_batch_add_form(*, form_state_key: str, draft_key: str) -> None:
    st.session_state[form_state_key] = True
    st.session_state.pop(draft_key, None)


def close_batch_form(*, form_state_key: str, draft_key: str) -> None:
    st.session_state.pop(form_state_key, None)
    st.session_state.pop(draft_key, None)


def reset_batch_draft(draft_key: str, init_rows: Callable[[], list[dict[str, str]]]) -> None:
    st.session_state[draft_key] = init_rows()


def maybe_auto_extend_batch_draft(
    draft_key: str,
    draft_rows: list[dict[str, str]],
    *,
    is_row_filled: Callable[[str], bool],
    append_row: Callable[[], dict[str, str]],
    max_rows: int = MAX_BATCH_DRAFT_ROWS,
) -> bool:
    """Extend draft by one row when the last row is filled, up to max_rows. Returns True if capped."""
    if not draft_rows:
        return False
    if len(draft_rows) >= max_rows:
        last_rid = str(draft_rows[-1].get("rid") or "")
        if last_rid and is_row_filled(last_rid):
            return True
        return False
    last_rid = str(draft_rows[-1].get("rid") or "")
    if last_rid and is_row_filled(last_rid):
        extended = list(draft_rows)
        extended.append(append_row())
        st.session_state[draft_key] = extended
        return len(extended) >= max_rows
    return False
