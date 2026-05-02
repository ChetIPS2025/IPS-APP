"""Light field theme for task review / photo flows (mobile-first, no dark mode)."""

from __future__ import annotations

import streamlit as st

_FIELD_LIGHT_CSS = """
<style>
  .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #f5f7fa !important;
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
    color: #0f172a !important;
  }
  .stCaption, [data-testid="stCaption"] {
    color: #475569 !important;
  }
  div[data-baseweb="select"] > div, textarea, input {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #0f172a !important;
    width: 100% !important;
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
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
    border: 1px solid #e2e8f0 !important;
  }
  button {
    min-height: 2.75rem !important;
  }
</style>
"""


def inject_field_light_theme() -> None:
    """Inject once per page section; idempotent Streamlit markdown."""
    st.markdown(_FIELD_LIGHT_CSS, unsafe_allow_html=True)
