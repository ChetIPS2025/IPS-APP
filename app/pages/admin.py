from __future__ import annotations

import pandas as pd
import streamlit as st
from branding import render_header
from db import fetch_table


def render() -> None:
    render_header("Admin")
    st.caption("Starter admin area")

    tabs = st.tabs(["Profiles", "Attachments", "Estimate Revisions"])
    with tabs[0]:
        st.dataframe(pd.DataFrame(fetch_table("profiles", limit=1000)), use_container_width=True, hide_index=True)
    with tabs[1]:
        st.dataframe(pd.DataFrame(fetch_table("attachments", limit=1000)), use_container_width=True, hide_index=True)
    with tabs[2]:
        st.dataframe(pd.DataFrame(fetch_table("estimate_revisions", limit=1000)), use_container_width=True, hide_index=True)
