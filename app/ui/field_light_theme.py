"""High-contrast field theme overrides (aligns with ``ips_app_shell`` tokens for task/photo pages)."""

from __future__ import annotations

import streamlit as st

_FIELD_LIGHT_CSS = """
<style>
  .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #c5cad3 !important;
  }
  [data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"] div[data-testid="stExpander"],
  section[data-testid="stSidebar"],
  [data-testid="stSidebar"] {
    background-color: #cbd5e1 !important;
    background: #cbd5e1 !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 12px !important;
    padding: 0 !important;
    box-shadow: 0 1px 2px rgba(17, 24, 39, 0.08) !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 12px 16px !important;
  }
  .stMarkdown, .stMarkdown p, .stMarkdown li, label, [data-testid="stWidgetLabel"] p {
    color: #1f2937 !important;
    font-weight: 500 !important;
  }
  [data-testid="stWidgetLabel"] label, [data-testid="stWidgetLabel"] span {
    color: #111827 !important;
    font-weight: 600 !important;
  }
  .stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    color: #1f2937 !important;
    font-weight: 500 !important;
  }
  section[data-testid="stMain"] [data-testid="stTextInput"] input,
  section[data-testid="stMain"] [data-testid="stNumberInput"] input,
  section[data-testid="stMain"] [data-testid="stDateInput"] input,
  section[data-testid="stMain"] [data-testid="stDateInput"] [data-baseweb="input"],
  section[data-testid="stMain"] [data-testid="stTextArea"] textarea,
  section[data-testid="stMain"] [data-baseweb="input"],
  section[data-testid="stMain"] [data-baseweb="textarea"],
  section[data-testid="stMain"] [data-baseweb="base-input"],
  section[data-testid="stMain"] [data-baseweb="input"] > div,
  section[data-testid="stMain"] [data-baseweb="textarea"] > div,
  section[data-testid="stMain"] [data-baseweb="base-input"] > div,
  section[data-testid="stMain"] textarea,
  section[data-testid="stMain"] input {
    background: #ffffff !important;
    border: 1px solid #9ca3af !important;
    border-radius: 10px !important;
    color: #111827 !important;
    min-height: 48px !important;
    width: 100% !important;
    box-sizing: border-box !important;
    font-weight: 500 !important;
  }
  /* Select / multiselect: single outer field; inner nodes transparent (chips use explicit tag rule below). */
  section[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"],
  section[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] {
    background: #ffffff !important;
    background-color: #ffffff !important;
    border: 1px solid #9ca3af !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    min-height: 48px !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }
  section[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"] > div,
  section[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
  section[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
  section[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div > div {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    min-height: 48px !important;
    padding: 10px 12px !important;
    color: #111827 !important;
  }
  section[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"] span,
  section[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] span {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #111827 !important;
  }
  section[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"] input,
  section[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] input {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #111827 !important;
    min-height: auto !important;
    padding: 0 !important;
  }
  section[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"] [role="combobox"],
  section[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] [role="combobox"] {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    min-height: auto !important;
    color: #111827 !important;
  }
  section[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] ul {
    background: transparent !important;
    border: none !important;
    gap: 6px !important;
  }
  section[data-testid="stMain"] [data-testid="stMultiSelect"] [data-baseweb="select"] [data-baseweb="tag"] {
    background: #e5e7eb !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
    color: #111827 !important;
    box-shadow: none !important;
  }
  section[data-testid="stMain"] [data-baseweb="input"] *,
  section[data-testid="stMain"] [data-baseweb="textarea"] *,
  section[data-testid="stMain"] [data-baseweb="base-input"] * {
    background-color: transparent !important;
    color: #111827 !important;
  }
  section[data-testid="stMain"] [data-testid="stSelectbox"] svg,
  section[data-testid="stMain"] [data-testid="stMultiSelect"] svg,
  section[data-testid="stMain"] [data-testid="stDateInput"] svg {
    color: #374151 !important;
    fill: #374151 !important;
  }
  input::placeholder, textarea::placeholder {
    color: #4b5563 !important;
    font-weight: 500 !important;
  }
  section[data-testid="stMain"] [data-testid="stFileUploader"] {
    background: #ffffff !important;
    border: 1px dashed #9ca3af !important;
    border-radius: 10px !important;
  }
  section[data-testid="stMain"] [data-testid="stFileUploader"] * {
    color: #111827 !important;
  }
  section[data-testid="stMain"] .stButton > button,
  section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button,
  section[data-testid="stMain"] [data-testid="stDownloadButton"] button,
  button {
    border-radius: 10px !important;
    min-height: 48px !important;
    box-shadow: none !important;
    font-weight: 600 !important;
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
    min-height: 48px !important;
    font-weight: 600 !important;
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
    background-color: #e5e7eb !important;
    background: #e5e7eb !important;
    color: #111827 !important;
    border: 1px solid #9ca3af !important;
    border-radius: 10px !important;
    min-height: 48px !important;
    font-weight: 600 !important;
  }
  section[data-testid="stMain"] .stButton > button[kind="secondary"]:hover,
  section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button[kind="secondary"]:hover,
  button[kind="secondary"]:hover {
    background: #d1d5db !important;
    border-color: #6b7280 !important;
    color: #111827 !important;
  }
</style>
"""


def inject_field_light_theme() -> None:
    """Inject once per page section; idempotent Streamlit markdown."""
    st.markdown(_FIELD_LIGHT_CSS, unsafe_allow_html=True)
