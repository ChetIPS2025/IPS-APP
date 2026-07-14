"""Shared row action button colors for list tables."""

from __future__ import annotations

import streamlit as st

from app.ui.css_inject import inject_css_once
from app.ui.theme import COLORS
IPS_ROW_ACTION_COLORS_KEY = "ips_row_action_colors_v2"
IPS_ROW_ACTION_COLORS_STYLE_ID = "ips-row-action-colors-v1"

ROW_ACTION_COLORS = {
    "open_bg": COLORS.get("action_open", COLORS["primary"]),
    "open_hover": COLORS.get("action_open_hover", COLORS["primary_hover"]),
    "open_text": "#ffffff",
    "neutral_bg": COLORS.get("action_neutral_bg", "#ffffff"),
    "neutral_border": COLORS.get("action_neutral_border", "#e2e8f0"),
    "neutral_text": COLORS.get("action_neutral_text", "#374151"),
    "neutral_hover_bg": "#f8fafc",
    "neutral_hover_border": "#cbd5e1",
    "danger": COLORS["danger"],
    "danger_hover": COLORS.get("danger_hover", "#b91c1c"),
}

# Streamlit widget keys → st-key-* classes (use these suffixes in button keys).
OPEN_VIEW_KEY_FRAGMENTS = (
    "ast_open_",
    "ast_view_",
    "ast_row_view_",
    "assets_view_",
    "jrow_open_",
    "jrow_view_",
    "tk_open_",
    "tk_view_",
    "inv_open_",
    "inv_view_",
    "est_open_",
    "est_view_",
    "users_open_",
    "users_view_",
)

EDIT_KEY_FRAGMENTS = (
    "_more_edit_",
    "_det_edit_",
    "ast_row_edit_",
    "estimates_modal_edit_",
    "_tool_edit_",
)

MOVE_KEY_FRAGMENTS = (
    "_trailer_go_",
    "_ctype_",
    "_row_move_",
    "_reclass_",
)

CANCEL_KEY_FRAGMENTS = (
    "_confirm_cancel_",
    "est_cancel_new",
    "job_cancel_new",
)


def row_action_key(prefix: str, action: str, record_id: str) -> str:
    """Build a row-action button key: ``{prefix}_{action}_{record_id}``."""
    return f"{prefix}_{action}_{record_id}"


def _btn_selectors(fragments: tuple[str, ...]) -> str:
    lines: list[str] = []
    for frag in fragments:
        base = f'[class*="st-key-{frag}"]'
        lines.append(f"{base} .stButton > button")
        lines.append(f"{base} [data-testid=\"stButton\"] > button")
        lines.append(f".ips-clean-actions {base} .stButton > button")
        lines.append(
            f"section[data-testid=\"stMain\"]:has(.ips-assets-page) "
            f'div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-assets-table-wrap) '
            f"{base} .stButton > button"
        )
    return ",\n".join(lines)


def _label_selectors(fragments: tuple[str, ...]) -> str:
    btn = _btn_selectors(fragments)
    parts: list[str] = []
    for sel in btn.split(",\n"):
        parts.append(f"{sel} p")
        parts.append(f"{sel} span")
        parts.append(f"{sel} div")
    return ",\n".join(parts)


def inject_row_action_colors_css() -> None:
    """Open/View=blue, Edit/Cancel=neutral, Move=blue. Delete stays in inject_action_colors_css."""
    if not inject_css_once(IPS_ROW_ACTION_COLORS_STYLE_ID):
        return

    c = ROW_ACTION_COLORS
    open_btns = _btn_selectors(OPEN_VIEW_KEY_FRAGMENTS)
    open_labels = _label_selectors(OPEN_VIEW_KEY_FRAGMENTS)
    edit_btns = _btn_selectors(EDIT_KEY_FRAGMENTS)
    move_btns = _btn_selectors(MOVE_KEY_FRAGMENTS)
    cancel_btns = _btn_selectors(CANCEL_KEY_FRAGMENTS)

    st.markdown(
        f"""
<style id="ips-row-action-colors-v1">
:root {{
  --ips-action-open-bg: {c["open_bg"]};
  --ips-action-open-hover: {c["open_hover"]};
  --ips-action-open-text: {c["open_text"]};
  --ips-action-neutral-bg: {c["neutral_bg"]};
  --ips-action-neutral-border: {c["neutral_border"]};
  --ips-action-neutral-text: {c["neutral_text"]};
  --ips-action-danger: {c["danger"]};
}}

/* Open / View — compact blue row actions */
{open_btns} {{
  background: var(--ips-action-open-bg) !important;
  border: 1px solid var(--ips-action-open-bg) !important;
  color: var(--ips-action-open-text) !important;
  box-shadow: none !important;
  white-space: nowrap !important;
  min-width: 5.5rem !important;
  width: auto !important;
}}
{open_btns}:hover,
{open_btns}:focus {{
  background: var(--ips-action-open-hover) !important;
  border-color: var(--ips-action-open-hover) !important;
  color: var(--ips-action-open-text) !important;
}}
{open_labels} {{
  color: var(--ips-action-open-text) !important;
  white-space: nowrap !important;
}}

/* Edit — neutral outline */
{edit_btns} {{
  background: var(--ips-action-neutral-bg) !important;
  border: 1px solid var(--ips-action-neutral-border) !important;
  color: var(--ips-action-neutral-text) !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
  white-space: nowrap !important;
}}
{edit_btns}:hover,
{edit_btns}:focus {{
  background: {c["neutral_hover_bg"]} !important;
  border-color: {c["neutral_hover_border"]} !important;
}}

/* Move / Reclassify — blue (same as open) */
{move_btns} {{
  background: var(--ips-action-open-bg) !important;
  border: 1px solid var(--ips-action-open-bg) !important;
  color: var(--ips-action-open-text) !important;
  box-shadow: none !important;
  white-space: nowrap !important;
}}
{move_btns}:hover,
{move_btns}:focus {{
  background: var(--ips-action-open-hover) !important;
  border-color: var(--ips-action-open-hover) !important;
  color: var(--ips-action-open-text) !important;
}}

/* Cancel — neutral outline */
{cancel_btns} {{
  background: var(--ips-action-neutral-bg) !important;
  border: 1px solid var(--ips-action-neutral-border) !important;
  color: var(--ips-action-neutral-text) !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04) !important;
  white-space: nowrap !important;
}}
{cancel_btns}:hover,
{cancel_btns}:focus {{
  background: {c["neutral_hover_bg"]} !important;
  border-color: {c["neutral_hover_border"]} !important;
}}
</style>
""",
        unsafe_allow_html=True,
    )
