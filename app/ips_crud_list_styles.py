"""
Shared IPS dark-theme layout for CRUD list pages (Customers, Labor, Employees): toolbar + side panel.

- Toolbar marker: ``<div class="ips-crud-toolbar-root"></div>`` inside ``st.container(border=True)``
- Side panel marker: ``<span class="ips-crud-side-anchor"></span>`` inside bordered panel
- Page split: :data:`IPS_CRUD_LIST_PAGE_SPLIT` + :data:`IPS_CRUD_LIST_PAGE_GAP` for main vs side columns

Call :func:`inject_ips_crud_list_styles` once per page render (or rely on first toolbar render).
"""

from __future__ import annotations

import streamlit as st

IPS_CRUD_LIST_STYLES_KEY = "ips_crud_list_styles_injected"

# Main grid vs side panel — use everywhere (Customers, Labor, Employees) so widths stay identical.
IPS_CRUD_LIST_PAGE_SPLIT: tuple[float, float] = (2.35, 1.0)
IPS_CRUD_LIST_PAGE_GAP = "medium"


def inject_ips_crud_list_styles() -> None:
    if st.session_state.get(IPS_CRUD_LIST_STYLES_KEY):
        return
    st.session_state[IPS_CRUD_LIST_STYLES_KEY] = True
    st.markdown(
        """
        <style>
        /* ----- Page subtitle (under render_header) ----- */
        p.ips-crud-page-subtitle {
            color: #94a3b8;
            font-size: 0.9rem;
            line-height: 1.45;
            margin: 0 0 1rem 0;
            padding: 0;
        }

        /* ----- Search + Status row: match column rhythm ----- */
        div[data-testid="stHorizontalBlock"]:has(.ips-crud-filter-row-start) {
            gap: 0.75rem !important;
            align-items: flex-end !important;
            margin-bottom: 0.35rem !important;
        }

        /* ----- Action toolbar (Add / Edit / Deactivate / Delete) ----- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-toolbar-root) {
            padding: 6px 8px 8px 8px !important;
            margin-bottom: 8px !important;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] {
            align-items: center;
            gap: 0.35rem;
        }
        /* Selection count vertically centered with buttons */
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) {
            display: flex !important;
            align-items: center !important;
            min-height: 2.25rem;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1) .ips-ta-summary {
            line-height: 1.35;
        }
        /* All action buttons: same min-height (Materials-style) */
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"] button {
            min-height: 2.25rem !important;
            border-radius: 8px !important;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(4) button:not(:disabled) {
            background: rgba(234, 179, 8, 0.14) !important;
            border-color: rgba(250, 204, 21, 0.55) !important;
            color: #fde68a !important;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(4) button:not(:disabled):hover {
            background: rgba(234, 179, 8, 0.22) !important;
            border-color: rgba(253, 224, 71, 0.75) !important;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5) button:not(:disabled) {
            background: rgba(220, 38, 38, 0.18) !important;
            border-color: rgba(248, 113, 113, 0.75) !important;
            color: #fecaca !important;
        }
        .ips-crud-toolbar-root ~ div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5) button:not(:disabled):hover {
            background: rgba(220, 38, 38, 0.28) !important;
            border-color: rgba(252, 165, 165, 0.9) !important;
        }

        /* ----- Side panel (add / edit) ----- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-side-anchor) {
            background: rgba(15, 23, 42, 0.72) !important;
            border-color: rgba(71, 85, 105, 0.55) !important;
            border-radius: 10px !important;
            padding: 12px 14px 14px 14px !important;
            margin-bottom: 8px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-side-anchor) h3 {
            color: #e2e8f0 !important;
            font-size: 1.05rem !important;
            font-weight: 650 !important;
            margin: 0 0 10px 0 !important;
            padding-bottom: 8px !important;
            border-bottom: 1px solid rgba(100, 116, 139, 0.35) !important;
        }
        /* Side panel: Save / Cancel / Close — match toolbar button height and radius */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-side-anchor) button {
            min-height: 2.25rem !important;
            border-radius: 8px !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-side-anchor)
            button[data-testid="baseButton-primary"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-crud-side-anchor) button[kind="primary"] {
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_crud_list_subtitle(text: str) -> None:
    """Same subtitle spacing/styling for Employees, Customers, etc."""
    import html

    inject_ips_crud_list_styles()
    st.markdown(
        f'<p class="ips-crud-page-subtitle">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )
