"""Sidebar chrome — CSS injected from ``ui/__init__.py`` render_sidebar."""

from __future__ import annotations

import streamlit as st

IPS_SIDEBAR_THEME_KEY = "ips_sidebar_theme_v3"


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
            font-size: 0.625rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.08em !important;
            text-transform: uppercase !important;
            padding: 0.2rem 0 !important;
            min-height: 1.75rem !important;
            color: #64748b !important;
        }
        section[data-testid="stSidebar"] .sidebar-nav-item + div.stButton > button,
        section[data-testid="stSidebar"] .sidebar-nav-item + div.stButton > button[kind="secondary"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        section[data-testid="stSidebar"] [class*="st-key-ips_sidebar_collapse_toggle"] .stButton > button {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
