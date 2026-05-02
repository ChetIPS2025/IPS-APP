"""Light field theme for task review / photo flows (mobile-first, no dark mode)."""

from __future__ import annotations

import streamlit as st

_FIELD_LIGHT_CSS = """
<style>
  .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #f8fafc !important;
  }
  [data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] div[data-testid="stExpander"],
  section[data-testid="stSidebar"] {
    background-color: #ffffff !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    padding: 0.65rem 0.75rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
  }
  .stMarkdown, .stMarkdown p, label, [data-testid="stWidgetLabel"] p {
    color: #1e293b !important;
  }
  .stCaption, [data-testid="stCaption"] {
    color: #64748b !important;
  }
  div[data-baseweb="select"] > div, textarea, input {
    border-color: #e2e8f0 !important;
  }
  button[kind="primary"] {
    background-color: #2563eb !important;
    border-color: #2563eb !important;
    color: #ffffff !important;
  }
  button[kind="primary"]:hover {
    background-color: #1d4ed8 !important;
    border-color: #1d4ed8 !important;
  }
  button[kind="secondary"] {
    background-color: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #e2e8f0 !important;
  }
</style>
"""


def inject_field_light_theme() -> None:
    """Inject once per page section; idempotent Streamlit markdown."""
    st.markdown(_FIELD_LIGHT_CSS, unsafe_allow_html=True)
