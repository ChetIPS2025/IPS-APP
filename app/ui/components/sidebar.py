"""Sidebar chrome — CSS injected from ``ui/__init__.py`` render_sidebar."""

from __future__ import annotations

import streamlit as st

IPS_SIDEBAR_THEME_KEY = "ips_sidebar_theme_v2"


def inject_sidebar_theme() -> None:
    if st.session_state.get(IPS_SIDEBAR_THEME_KEY):
        return
    st.session_state[IPS_SIDEBAR_THEME_KEY] = True
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] [data-testid="stExpander"] details {
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
            font-size: 0.68rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
            padding: 0.2rem 0 !important;
            min-height: 1.75rem !important;
        }
        section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
            background: #2563eb !important;
            border-color: #1d4ed8 !important;
            color: #fff !important;
        }
        section[data-testid="stSidebar"] .ips-sidebar-collapse-row + div.stButton > button {
            font-weight: 700 !important;
            margin-bottom: 0.35rem !important;
        }
        body.ips-sidebar-collapsed section[data-testid="stSidebar"] .ips-sidebar-collapse-row + div.stButton > button p {
            font-size: 1.25rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
