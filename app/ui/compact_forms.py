"""
Compact form layout: field sizing, reduced control chrome, column-friendly inputs.

Inject via :func:`inject_compact_form_styles` (called from :func:`page_shell.inject_ips_dashboard_layout`).
Mark fields with :func:`field_marker` inside ``st.columns`` so max-width rules apply.
"""

from __future__ import annotations

import streamlit as st

from app.ui.css_inject import inject_css_once

IPS_COMPACT_FORM_CSS_KEY = "ips_compact_form_styles_v2"
IPS_COMPACT_FORM_STYLE_ID = "ips-compact-form-styles-v2"


def inject_compact_form_styles() -> None:
    if not inject_css_once(IPS_COMPACT_FORM_STYLE_ID):
        return
    st.markdown(
        """
        <style id="ips-compact-form-styles-v2">
        /* ----- Compact form scope: tighter vertical rhythm ----- */
        section[data-testid="stMain"]:has(.ips-compact-form) [data-testid="stElementContainer"],
        section[data-testid="stMain"] .ips-compact-form-scope [data-testid="stElementContainer"] {
            margin-bottom: 0.12rem !important;
        }
        section[data-testid="stMain"]:has(.ips-compact-form) [data-testid="stWidgetLabel"] p,
        section[data-testid="stMain"] .ips-compact-form-scope [data-testid="stWidgetLabel"] p {
            margin-bottom: 0.04rem !important;
            font-size: 0.76rem !important;
        }
        section[data-testid="stMain"]:has(.ips-compact-form) [data-testid="stForm"],
        section[data-testid="stMain"] .ips-compact-form-scope [data-testid="stForm"] {
            padding: 0 !important;
        }

        /* Default: do not force every control full viewport width */
        section[data-testid="stMain"] [data-testid="stTextInput"] > div,
        section[data-testid="stMain"] [data-testid="stNumberInput"] > div,
        section[data-testid="stMain"] [data-testid="stSelectbox"] > div,
        section[data-testid="stMain"] [data-testid="stDateInput"] > div {
            width: fit-content !important;
            max-width: 100% !important;
        }
        section[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"] {
            max-width: min(350px, 100%) !important;
            width: 100% !important;
        }
        section[data-testid="stMain"] [data-testid="stTextInput"] input {
            max-width: min(350px, 100%) !important;
            width: 100% !important;
        }
        section[data-testid="stMain"] [data-testid="stNumberInput"] input {
            max-width: min(120px, 100%) !important;
            width: 100% !important;
        }
        section[data-testid="stMain"] [data-testid="stDateInput"] input {
            max-width: min(180px, 100%) !important;
            width: 100% !important;
        }

        /* Field markers (place span in column before widget) */
        div[data-testid="column"]:has(> div .ips-fld-search) [data-testid="stTextInput"] input,
        div[data-testid="stElementContainer"]:has(.ips-fld-search) [data-testid="stTextInput"] input {
            max-width: min(420px, 100%) !important;
            min-width: 12rem !important;
        }
        div[data-testid="column"]:has(.ips-fld-job) [data-baseweb="select"],
        div[data-testid="stElementContainer"]:has(.ips-fld-job) [data-baseweb="select"],
        section[data-testid="stMain"] [data-testid="stForm"]:has(.ips-fld-job) [data-baseweb="select"] {
            max-width: min(600px, 100%) !important;
            width: 100% !important;
        }
        section[data-testid="stMain"] [data-testid="stForm"]:has(.ips-fld-job) [data-testid="stSelectbox"] > div {
            width: fit-content !important;
            max-width: min(600px, 100%) !important;
        }
        div[data-testid="column"]:has(.ips-fld-date) input,
        div[data-testid="stElementContainer"]:has(.ips-fld-date) input {
            max-width: min(180px, 100%) !important;
        }
        div[data-testid="column"]:has(.ips-fld-time-type) [data-baseweb="select"],
        div[data-testid="stElementContainer"]:has(.ips-fld-time-type) [data-baseweb="select"] {
            max-width: min(160px, 100%) !important;
        }
        div[data-testid="column"]:has(.ips-fld-hours) input,
        div[data-testid="column"]:has(.ips-fld-number) input,
        div[data-testid="stElementContainer"]:has(.ips-fld-hours) input,
        div[data-testid="stElementContainer"]:has(.ips-fld-number) input {
            max-width: min(120px, 100%) !important;
        }
        div[data-testid="column"]:has(.ips-fld-medium) input,
        div[data-testid="column"]:has(.ips-fld-medium) [data-baseweb="select"] {
            max-width: min(280px, 100%) !important;
        }
        div[data-testid="column"]:has(.ips-fld-wide) input,
        div[data-testid="column"]:has(.ips-fld-wide) [data-baseweb="select"] {
            max-width: min(480px, 100%) !important;
        }

        /* Compact form submit — not full row width */
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] {
            width: fit-content !important;
            max-width: 100% !important;
        }
        section[data-testid="stMain"] [data-testid="stFormSubmitButton"] button {
            width: auto !important;
            min-width: 5.5rem !important;
            max-width: 11rem !important;
            min-height: 2.125rem !important;
            padding: 0.32rem 0.85rem !important;
            white-space: nowrap !important;
        }
        section[data-testid="stMain"] .ips-compact-form-scope .stButton > button {
            width: auto !important;
            min-width: 4.5rem !important;
            max-width: 10rem !important;
        }
        section[data-testid="stMain"]:has(.ips-compact-form) [data-testid="stHorizontalBlock"] {
            align-items: flex-end !important;
            gap: 0.35rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def compact_form_begin() -> None:
    """Open a compact-form region (CSS scope marker)."""
    inject_compact_form_styles()
    st.markdown(
        '<span class="ips-compact-form ips-compact-form-scope" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )


def field_marker(kind: str) -> None:
    """
    Place before a widget inside a column. ``kind``: search, job, date, time-type,
    hours, number, medium, wide.
    """
    k = str(kind or "").strip().lower().replace("_", "-")
    st.markdown(f'<span class="ips-fld ips-fld-{k}" aria-hidden="true"></span>', unsafe_allow_html=True)
