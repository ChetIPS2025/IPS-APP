"""Estimate Materials session state and draft helpers."""

from __future__ import annotations

from typing import Callable
from uuid import uuid4

import streamlit as st

from app.components.estimate_builder.state import (
    DEFAULT_BATCH_ROW_COUNT,
    MAX_BATCH_DRAFT_ROWS,
    initial_batch_draft_rows,
    maybe_auto_extend_batch_draft,
)

_TAKEOFF_DRAFT_COUNT = DEFAULT_BATCH_ROW_COUNT
_MAX_TAKEOFF_DRAFT_ROWS = MAX_BATCH_DRAFT_ROWS
_MATERIAL_LIST_TABLE_KEY = "estimate_materials_list"


def takeoff_open_key(estimate_id: str) -> str:
    return f"ips_estimate_material_takeoff_open_{estimate_id}"


def takeoff_draft_key(estimate_id: str) -> str:
    return f"mat_takeoff_batch_{estimate_id}"


def takeoff_field_key(estimate_id: str, field: str, rid: str) -> str:
    return f"mat_to_{estimate_id}_{field}_{rid}"


def material_detail_tab_key(line_id: str) -> str:
    return f"ips_estimate_material_detail_tab_{line_id}"


def material_detail_query_key() -> str:
    return "material_detail"


def material_search_key() -> str:
    return "mat_search"


def export_ready_key(estimate_id: str) -> str:
    return f"est_mat_export_ready_{estimate_id}"


def new_takeoff_row(*, pick: str) -> dict[str, str]:
    return {"rid": uuid4().hex[:8], "pick": pick}


def initial_takeoff_rows(*, pick: str) -> list[dict[str, str]]:
    return initial_batch_draft_rows(_TAKEOFF_DRAFT_COUNT, pick=pick)


def clear_material_takeoff_draft(estimate_id: str) -> None:
    """Clear draft rows, widget keys, and takeoff form state for one estimate."""
    eid = str(estimate_id or "").strip()
    if not eid:
        return
    draft_key = takeoff_draft_key(eid)
    open_key = takeoff_open_key(eid)
    for key in (draft_key, open_key, f"mat_takeoff_save_{eid}", export_ready_key(eid)):
        st.session_state.pop(key, None)
    prefix = f"mat_to_{eid}_"
    for key in list(st.session_state.keys()):
        sk = str(key)
        if sk.startswith(prefix):
            st.session_state.pop(key, None)


def clear_material_detail_state(line_id: str = "") -> None:
    lid = str(line_id or "").strip()
    if lid:
        st.session_state.pop(material_detail_tab_key(lid), None)
    try:
        qk = material_detail_query_key()
        if qk in st.session_state.get("_ips_query_keys", ()) or True:
            import streamlit as st

            if qk in st.query_params:
                del st.query_params[qk]
    except Exception:
        pass


def maybe_extend_takeoff_draft(
    estimate_id: str,
    draft_rows: list[dict[str, str]],
    *,
    is_row_filled: Callable[[str], bool],
    pick: str,
) -> bool:
    return maybe_auto_extend_batch_draft(
        takeoff_draft_key(estimate_id),
        draft_rows,
        is_row_filled=is_row_filled,
        append_row=lambda: new_takeoff_row(pick=pick),
        max_rows=_MAX_TAKEOFF_DRAFT_ROWS,
    )


__all__ = [
    "_MATERIAL_LIST_TABLE_KEY",
    "_MAX_TAKEOFF_DRAFT_ROWS",
    "_TAKEOFF_DRAFT_COUNT",
    "clear_material_detail_state",
    "clear_material_takeoff_draft",
    "export_ready_key",
    "initial_takeoff_rows",
    "material_detail_query_key",
    "material_detail_tab_key",
    "material_search_key",
    "maybe_extend_takeoff_draft",
    "new_takeoff_row",
    "takeoff_draft_key",
    "takeoff_field_key",
    "takeoff_open_key",
]
