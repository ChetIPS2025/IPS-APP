from __future__ import annotations

import pandas as pd
import streamlit as st
from branding import render_header
from db import fetch_table


def render() -> None:
    render_header("Admin")
    st.caption("Starter admin area")

    st.session_state.setdefault("admin_main_panel", "Profiles")
    st.radio(
        "Admin sections",
        ["Profiles", "Attachments", "Estimate Revisions"],
        horizontal=True,
        key="admin_main_panel",
        label_visibility="collapsed",
    )
    _ap = str(st.session_state.get("admin_main_panel") or "Profiles")
    if _ap == "Profiles":
        st.dataframe(pd.DataFrame(fetch_table("profiles", limit=1000)), use_container_width=True, hide_index=True)
    elif _ap == "Attachments":
        st.dataframe(pd.DataFrame(fetch_table("attachments", limit=1000)), use_container_width=True, hide_index=True)
    else:
        st.dataframe(pd.DataFrame(fetch_table("estimate_revisions", limit=1000)), use_container_width=True, hide_index=True)
