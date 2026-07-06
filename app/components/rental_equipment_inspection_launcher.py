"""Deep-link launcher for rental equipment inspections."""

from __future__ import annotations

from typing import Any

import streamlit as st

try:
    from app.navigation import set_nav_slug
except ImportError:
    from navigation import set_nav_slug  # type: ignore

_CTX_KEYS = (
    "rental_insp_id",
    "rental_insp_asset_id",
    "rental_insp_job_id",
    "rental_insp_type",
)


def rental_inspection_context() -> dict[str, str | None]:
    return {k: str(st.session_state.get(k) or "").strip() or None for k in _CTX_KEYS}


def open_rental_inspection(
    *,
    inspection_id: str | None = None,
    asset_id: str | None = None,
    job_id: str | None = None,
    inspection_type: str | None = None,
) -> None:
    st.session_state["rental_insp_id"] = str(inspection_id or "").strip() or None
    st.session_state["rental_insp_asset_id"] = str(asset_id or "").strip() or None
    st.session_state["rental_insp_job_id"] = str(job_id or "").strip() or None
    st.session_state["rental_insp_type"] = str(inspection_type or "").strip() or None
    set_nav_slug("rental_equipment_inspection")
    st.rerun()


def clear_rental_inspection_context() -> None:
    for k in _CTX_KEYS:
        st.session_state.pop(k, None)
