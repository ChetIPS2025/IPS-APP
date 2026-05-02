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
    border-radius: 12px !important;
    padding: 0.8rem 0.9rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
  }
  .stMarkdown, .stMarkdown p, label, [data-testid="stWidgetLabel"] p {
    color: #0f172a !important;
  }
  .stCaption, [data-testid="stCaption"] {
    color: #475569 !important;
  }
  section[data-testid="stMain"] [data-testid="stTextInput"] input,
  section[data-testid="stMain"] [data-testid="stNumberInput"] input,
  section[data-testid="stMain"] [data-testid="stDateInput"] input,
  section[data-testid="stMain"] [data-testid="stDateInput"] [data-baseweb="input"],
  section[data-testid="stMain"] [data-testid="stTextArea"] textarea,
  section[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"] > div,
  section[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
  section[data-testid="stMain"] [data-baseweb="input"],
  section[data-testid="stMain"] [data-baseweb="textarea"],
  section[data-testid="stMain"] [data-baseweb="select"],
  section[data-testid="stMain"] [data-baseweb="base-input"],
  section[data-testid="stMain"] [data-baseweb="input"] > div,
  section[data-testid="stMain"] [data-baseweb="select"] > div,
  section[data-testid="stMain"] [data-baseweb="textarea"] > div,
  section[data-testid="stMain"] [data-baseweb="base-input"] > div,
  section[data-testid="stMain"] [role="combobox"],
  div[data-baseweb="select"] > div,
  div[data-baseweb="input"],
  div[data-baseweb="textarea"],
  div[data-baseweb="base-input"],
  textarea,
  input {
    background: #ffffff !important;
    border-color: #e2e8f0 !important;
    border-radius: 10px !important;
    color: #0f172a !important;
    min-height: 44px !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }
  section[data-testid="stMain"] [data-baseweb="input"] *,
  section[data-testid="stMain"] [data-baseweb="textarea"] *,
  section[data-testid="stMain"] [data-baseweb="select"] *,
  section[data-testid="stMain"] [data-baseweb="base-input"] * {
    background-color: transparent !important;
    color: #0f172a !important;
  }
  section[data-testid="stMain"] [data-testid="stSelectbox"] svg,
  section[data-testid="stMain"] [data-testid="stMultiSelect"] svg,
  section[data-testid="stMain"] [data-testid="stDateInput"] svg {
    color: #475569 !important;
    fill: #475569 !important;
  }
  input::placeholder, textarea::placeholder {
    color: #94a3b8 !important;
  }
  section[data-testid="stMain"] [data-testid="stFileUploader"] {
    background: #ffffff !important;
    border: 1px dashed #cbd5e1 !important;
    border-radius: 10px !important;
  }
  section[data-testid="stMain"] [data-testid="stFileUploader"] * {
    color: #0f172a !important;
  }
  section[data-testid="stMain"] .stButton > button,
  section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button,
  section[data-testid="stMain"] [data-testid="stDownloadButton"] button,
  button {
    border-radius: 10px !important;
    min-height: 44px !important;
    box-shadow: none !important;
  }
  section[data-testid="stMain"] .stButton > button[kind="primary"],
  section[data-testid="stMain"] .stButton > button[data-testid="baseButton-primary"],
  section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="primary"],
  section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[data-testid="baseButton-primary"],
  button[kind="primary"] {
    background-color: #2563eb !important;
    background: #2563eb !important;
    border-color: #2563eb !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    min-height: 44px !important;
    font-weight: 650 !important;
  }
  section[data-testid="stMain"] .stButton > button[kind="primary"]:hover,
  section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
  button[kind="primary"]:hover {
    background-color: #1d4ed8 !important;
    background: #1d4ed8 !important;
    border-color: #1d4ed8 !important;
  }
  section[data-testid="stMain"] .stButton > button[kind="secondary"],
  section[data-testid="stMain"] .stButton > button[data-testid="baseButton-secondary"],
  section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="secondary"],
  button[kind="secondary"] {
    background-color: #f1f5f9 !important;
    background: #f1f5f9 !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    min-height: 44px !important;
    font-weight: 600 !important;
  }
  section[data-testid="stMain"] .stButton > button[kind="secondary"]:hover,
  section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="secondary"]:hover,
  button[kind="secondary"]:hover {
    background: #e2e8f0 !important;
    border-color: #94a3b8 !important;
    color: #1e293b !important;
  }
</style>
"""


def inject_field_light_theme() -> None:
    """Inject once per page section; idempotent Streamlit markdown."""
    st.markdown(_FIELD_LIGHT_CSS, unsafe_allow_html=True)
