"""Authoritative CSS for the shared IPS page header."""

from __future__ import annotations

import streamlit as st

from app.ui.css_inject import inject_css_once

IPS_PAGE_HEADER_STYLES_KEY = "ips_page_header_styles_v22"
IPS_PAGE_HEADER_STYLE_ID = "ips-page-header-styles-v22"


def inject_page_header_styles() -> None:
    """Inject shared header styles once per session."""
    if not inject_css_once(IPS_PAGE_HEADER_STYLE_ID):
        return
    with st.sidebar:
        st.markdown(
            """
<style id="ips-page-header-styles-v22">
[class*="st-key-ips_page_header"],
[class*="st-key-ips_page_header"] [data-testid="stVerticalBlockBorderWrapper"] {
  width: 100% !important;
  margin: 0 0 14px 0 !important;
  padding: clamp(10px, 1.2vw, 14px) clamp(12px, 1.5vw, 20px) clamp(16px, 2vw, 22px) !important;
  min-height: 96px !important;
  background: #ffffff !important;
  border: 1px solid #e5e7eb !important;
  border-bottom: 2px solid #3158e6 !important;
  border-radius: 0 !important;
  box-sizing: border-box !important;
  overflow: visible !important;
  position: relative !important;
}
[class*="st-key-ips_page_header"] [data-testid="stElementContainer"]:has(.ips-header-root) {
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}
section[data-testid="stMain"] [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has(.ips-app-page-header-marker):has(~ [data-testid="stElementContainer"]:has(.ips-app-page-header-marker)) {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  border: none !important;
}
[class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] {
  display: flex !important;
  align-items: center !important;
  gap: clamp(12px, 1.6vw, 20px) !important;
  width: 100% !important;
  flex-wrap: nowrap !important;
  overflow: visible !important;
}
[class*="st-key-ips_page_header"] [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  gap: clamp(10px, 1.2vw, 16px) !important;
  width: 100% !important;
  overflow: visible !important;
}
[class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) {
  flex: 0 1 auto !important;
  width: auto !important;
  min-width: clamp(200px, 18vw, 340px) !important;
  max-width: 340px !important;
  overflow: visible !important;
}
[class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) {
  overflow: visible !important;
  z-index: 1 !important;
}
[class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) {
  flex: 0 1 auto !important;
  min-width: 260px !important;
  max-width: 100% !important;
  margin-left: auto !important;
  overflow: visible !important;
}
@media (min-width: 768px) {
  [class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) {
    position: absolute !important;
    left: 50% !important;
    top: 50% !important;
    transform: translate(-50%, -50%) !important;
    flex: 0 0 auto !important;
    width: max-content !important;
    min-width: 0 !important;
    max-width: min(520px, 52vw) !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    pointer-events: none !important;
  }
}
[class*="st-key-header_page_toolbar"] {
  width: 100% !important;
  margin-top: 12px !important;
  padding-top: 12px !important;
  border-top: 1px solid #e5e7eb !important;
  box-sizing: border-box !important;
}
[class*="st-key-header_page_toolbar"] [data-testid="stHorizontalBlock"] {
  display: flex !important;
  flex-wrap: wrap !important;
  justify-content: flex-end !important;
  align-items: center !important;
  gap: 10px !important;
  width: 100% !important;
  overflow: visible !important;
}
[class*="st-key-header_page_toolbar"] [data-testid="column"] {
  flex: 0 0 auto !important;
  flex-shrink: 0 !important;
  width: auto !important;
  min-width: max-content !important;
  max-width: none !important;
}
[class*="st-key-header_page_toolbar"] .stButton,
[class*="st-key-header_page_toolbar"] [data-testid="stDownloadButton"] {
  width: auto !important;
  margin: 0 !important;
}
[class*="st-key-header_page_toolbar"] .stButton > button,
[class*="st-key-header_page_toolbar"] [data-testid="stDownloadButton"] > button {
  width: auto !important;
  min-width: max-content !important;
  max-width: none !important;
  white-space: nowrap !important;
}
[class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) > [data-testid="stHorizontalBlock"] {
  display: flex !important;
  flex-wrap: nowrap !important;
  justify-content: flex-end !important;
  align-items: stretch !important;
  gap: 0 !important;
  width: 100% !important;
  min-height: 40px !important;
  overflow: visible !important;
}
.st-key-header_bottom_actions,
[class*="st-key-header_bottom_actions"] {
  position: absolute !important;
  top: auto !important;
  bottom: 0 !important;
  right: 0 !important;
  left: auto !important;
  flex: 0 0 auto !important;
  min-width: max-content !important;
  max-width: max-content !important;
  z-index: 4 !important;
}
.st-key-header_bottom_actions [data-testid="stHorizontalBlock"],
[class*="st-key-header_bottom_actions"] [data-testid="stHorizontalBlock"] {
  display: flex !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 8px !important;
  width: max-content !important;
  max-width: max-content !important;
  margin: 0 !important;
}
.st-key-header_bottom_actions [data-testid="stHorizontalBlock"] > [data-testid="column"],
[class*="st-key-header_bottom_actions"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {
  flex: 0 0 auto !important;
  flex-shrink: 0 !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  padding: 0 !important;
  position: relative !important;
  overflow: visible !important;
}
.st-key-header_bottom_actions [data-testid="stHorizontalBlock"] > [data-testid="column"]:has(.st-key-header_date_range),
.st-key-header_bottom_actions [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([class*="st-key-header_date_range"]),
[class*="st-key-header_bottom_actions"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:has(.st-key-header_date_range),
[class*="st-key-header_bottom_actions"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([class*="st-key-header_date_range"]) {
  min-width: 230px !important;
  width: 230px !important;
  max-width: 230px !important;
}
.st-key-header_bottom_actions [data-testid="stHorizontalBlock"] > [data-testid="column"]:has(.st-key-header_primary_action),
.st-key-header_bottom_actions [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([class*="st-key-header_primary_action"]),
[class*="st-key-header_bottom_actions"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:has(.st-key-header_primary_action),
[class*="st-key-header_bottom_actions"] [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([class*="st-key-header_primary_action"]) {
  min-width: max-content !important;
  width: auto !important;
  max-width: none !important;
}
.st-key-header_bottom_actions [data-testid="column"],
[class*="st-key-header_bottom_actions"] [data-testid="column"] {
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  padding: 0 !important;
}
.st-key-header_bottom_actions .st-key-header_date_range,
[class*="st-key-header_bottom_actions"] .st-key-header_date_range {
  min-width: 230px !important;
  max-width: 230px !important;
  width: 230px !important;
  flex: 0 0 auto !important;
}
.st-key-header_bottom_actions .st-key-header_primary_action,
[class*="st-key-header_bottom_actions"] .st-key-header_primary_action {
  min-width: max-content !important;
  max-width: none !important;
  flex: 0 0 auto !important;
  width: auto !important;
}
.st-key-header_bottom_actions .st-key-header_primary_action .stButton,
.st-key-header_bottom_actions .st-key-header_primary_action [data-testid="stDownloadButton"],
[class*="st-key-header_bottom_actions"] .st-key-header_primary_action .stButton,
[class*="st-key-header_bottom_actions"] .st-key-header_primary_action [data-testid="stDownloadButton"] {
  width: auto !important;
  margin: 0 !important;
}
.st-key-header_bottom_actions .st-key-header_primary_action .stButton > button,
[class*="st-key-header_bottom_actions"] .st-key-header_primary_action .stButton > button {
  width: auto !important;
  min-width: 112px !important;
  max-width: none !important;
}
[class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) > [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([class*="st-key-header_bottom_actions"]) {
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  padding: 0 !important;
  overflow: visible !important;
  flex: 0 0 0 !important;
}
.st-key-header_trailing_actions,
[class*="st-key-header_trailing_actions"] {
  position: absolute !important;
  top: 0 !important;
  bottom: auto !important;
  right: 0 !important;
  left: auto !important;
  margin-left: 0 !important;
  flex: 0 0 auto !important;
  min-width: max-content !important;
  max-width: max-content !important;
  align-self: auto !important;
  z-index: 4 !important;
}
[class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) > [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([class*="st-key-header_bottom_actions"]),
[class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) > [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([class*="st-key-header_trailing_actions"]) {
  position: static !important;
}
[class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) > [data-testid="stHorizontalBlock"] > [data-testid="column"]:has([class*="st-key-header_trailing_actions"]) {
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  padding: 0 !important;
  overflow: visible !important;
  flex: 0 0 0 !important;
}
.st-key-header_trailing_actions [data-testid="stHorizontalBlock"],
[class*="st-key-header_trailing_actions"] [data-testid="stHorizontalBlock"] {
  display: flex !important;
  flex-wrap: nowrap !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 2px !important;
  width: max-content !important;
  max-width: max-content !important;
  margin: 0 !important;
}
.st-key-header_trailing_actions [data-testid="column"],
[class*="st-key-header_trailing_actions"] [data-testid="column"] {
  flex: 0 0 auto !important;
  width: auto !important;
  min-width: 0 !important;
  max-width: none !important;
  padding: 0 !important;
}
.st-key-header_trailing_actions .st-key-header_refresh,
.st-key-header_trailing_actions .st-key-header_notifications,
.st-key-header_trailing_actions .st-key-header_help,
.st-key-header_trailing_actions .st-key-header_settings,
.st-key-header_trailing_actions .st-key-header_avatar,
[class*="st-key-header_trailing_actions"] .st-key-header_refresh,
[class*="st-key-header_trailing_actions"] .st-key-header_notifications,
[class*="st-key-header_trailing_actions"] .st-key-header_help,
[class*="st-key-header_trailing_actions"] .st-key-header_settings,
[class*="st-key-header_trailing_actions"] .st-key-header_avatar {
  min-width: 40px !important;
  max-width: 40px !important;
}
.st-key-header_trailing_actions .st-key-header_secondary_action,
[class*="st-key-header_trailing_actions"] .st-key-header_secondary_action {
  min-width: max-content !important;
  max-width: none !important;
  margin-right: 2px !important;
}
.st-key-header_trailing_actions .st-key-header_secondary_action .stButton > button,
[class*="st-key-header_trailing_actions"] .st-key-header_secondary_action .stButton > button {
  width: auto !important;
  min-width: max-content !important;
  max-width: none !important;
  padding: 0 12px !important;
}
[class*="st-key-ips_page_header"]:has(.ips-assets-page-header-actions),
[class*="st-key-ips_page_header"]:has(.ips-jobs-page-header-actions),
[class*="st-key-ips_page_header"]:has(.ips-page-header-inline-actions) > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) > [data-testid="stHorizontalBlock"] {
  flex-wrap: nowrap !important;
  gap: 6px !important;
}
[class*="st-key-ips_page_header"]:has(.ips-assets-page-header-actions),
[class*="st-key-ips_page_header"]:has(.ips-jobs-page-header-actions),
[class*="st-key-ips_page_header"]:has(.ips-page-header-inline-actions) .st-key-header_bottom_actions .st-key-header_primary_action,
[class*="st-key-ips_page_header"]:has(.ips-assets-page-header-actions) .st-key-header_bottom_actions .st-key-header_primary_action,
[class*="st-key-ips_page_header"]:has(.ips-jobs-page-header-actions) .st-key-header_bottom_actions .st-key-header_primary_action,
[class*="st-key-ips_page_header"]:has(.ips-page-header-inline-actions) .st-key-header_primary_action {
  min-width: max-content !important;
  flex: 0 0 auto !important;
  max-width: none !important;
  margin-right: 0 !important;
}
[class*="st-key-ips_page_header"]:has(.ips-assets-page-header-actions),
[class*="st-key-ips_page_header"]:has(.ips-jobs-page-header-actions),
[class*="st-key-ips_page_header"]:has(.ips-page-header-inline-actions) .st-key-header_primary_action .stButton > button[kind="primary"] {
  background: #3158e6 !important;
  border-color: #3158e6 !important;
  color: #ffffff !important;
}
[class*="st-key-ips_page_header"]:has(.ips-assets-page-header-actions),
[class*="st-key-ips_page_header"]:has(.ips-jobs-page-header-actions),
[class*="st-key-ips_page_header"]:has(.ips-page-header-inline-actions) .st-key-header_primary_action .stButton > button[kind="secondary"],
[class*="st-key-ips_page_header"]:has(.ips-assets-page-header-actions) .st-key-header_primary_action [data-testid="stDownloadButton"] > button {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  color: #374151 !important;
}
[class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) [data-testid="column"]:not(:has([class*="st-key-header_bottom_actions"])):not(:has([class*="st-key-header_trailing_actions"])) {
  flex: 0 0 auto !important;
  flex-shrink: 0 !important;
  width: auto !important;
  min-width: 0 !important;
  overflow: visible !important;
  position: relative !important;
}
[class*="st-key-ips_page_header"] [class*="st-key-header_"] {
  flex: 0 0 auto !important;
  flex-shrink: 0 !important;
  width: auto !important;
  max-width: none !important;
}
[class*="st-key-ips_page_header"] .stButton,
[class*="st-key-ips_page_header"] .stDateInput,
[class*="st-key-ips_page_header"] [data-testid="stPopover"] {
  margin: 0 !important;
}
[class*="st-key-ips_page_header"] .stButton > button,
[class*="st-key-ips_page_header"] [data-testid="stPopover"] > button {
  min-height: 40px !important;
  height: 40px !important;
  margin: 0 !important;
  white-space: nowrap !important;
  box-sizing: border-box !important;
  overflow: visible !important;
}
.st-key-header_back .stButton > button,
.st-key-header_menu .stButton > button,
.st-key-header_refresh .stButton > button,
.st-key-header_notifications .stButton > button,
.st-key-header_help [data-testid="stPopover"] > button,
.st-key-header_settings .stButton > button {
  width: 40px !important;
  min-width: 40px !important;
  max-width: 40px !important;
  padding: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 1.05rem !important;
  line-height: 1 !important;
  box-shadow: none !important;
}
.st-key-header_back .stButton > button,
.st-key-header_menu .stButton > button {
  background: #ffffff !important;
  border: 1px solid #e2e8f0 !important;
  color: #374151 !important;
}
.st-key-header_refresh .stButton > button,
.st-key-header_notifications .stButton > button,
.st-key-header_help [data-testid="stPopover"] > button,
.st-key-header_settings .stButton > button,
[class*="st-key-header_refresh"] .stButton > button,
[class*="st-key-header_refresh"] [data-testid="stButton"] > button,
[class*="st-key-header_notifications"] .stButton > button,
[class*="st-key-header_notifications"] [data-testid="stButton"] > button,
[class*="st-key-header_settings"] .stButton > button,
[class*="st-key-header_settings"] [data-testid="stButton"] > button,
[class*="st-key-header_help"] [data-testid="stPopover"] > button,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_refresh"] .stButton > button,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_refresh"] [data-testid="stButton"] > button,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_notifications"] .stButton > button,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_notifications"] [data-testid="stButton"] > button,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_settings"] .stButton > button,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_settings"] [data-testid="stButton"] > button,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_help"] [data-testid="stPopover"] > button,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_refresh"] .stButton > button[kind="tertiary"],
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_refresh"] [data-testid="stButton"] > button[kind="tertiary"],
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_notifications"] .stButton > button[kind="tertiary"],
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_notifications"] [data-testid="stButton"] > button[kind="tertiary"],
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_settings"] .stButton > button[kind="tertiary"],
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_settings"] [data-testid="stButton"] > button[kind="tertiary"],
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_help"] [data-testid="stPopover"] > button[kind="tertiary"] {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  border-width: 0 !important;
  outline: none !important;
  color: inherit !important;
  font-weight: 400 !important;
}
.st-key-header_refresh .stButton > button:hover,
.st-key-header_notifications .stButton > button:hover,
.st-key-header_help [data-testid="stPopover"] > button:hover,
.st-key-header_settings .stButton > button:hover,
[class*="st-key-header_refresh"] .stButton > button:hover,
[class*="st-key-header_notifications"] .stButton > button:hover,
[class*="st-key-header_settings"] .stButton > button:hover,
[class*="st-key-header_help"] [data-testid="stPopover"] > button:hover,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_refresh"] .stButton > button:hover,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_notifications"] .stButton > button:hover,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_settings"] .stButton > button:hover,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_help"] [data-testid="stPopover"] > button:hover,
.st-key-header_refresh .stButton > button:focus,
.st-key-header_notifications .stButton > button:focus,
.st-key-header_help [data-testid="stPopover"] > button:focus,
.st-key-header_settings .stButton > button:focus,
[class*="st-key-header_refresh"] .stButton > button:focus,
[class*="st-key-header_notifications"] .stButton > button:focus,
[class*="st-key-header_settings"] .stButton > button:focus,
[class*="st-key-header_help"] [data-testid="stPopover"] > button:focus,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_refresh"] .stButton > button:focus,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_notifications"] .stButton > button:focus,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_settings"] .stButton > button:focus,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_help"] [data-testid="stPopover"] > button:focus,
.st-key-header_refresh .stButton > button:focus-visible,
.st-key-header_notifications .stButton > button:focus-visible,
.st-key-header_help [data-testid="stPopover"] > button:focus-visible,
.st-key-header_settings .stButton > button:focus-visible,
[class*="st-key-header_refresh"] .stButton > button:focus-visible,
[class*="st-key-header_notifications"] .stButton > button:focus-visible,
[class*="st-key-header_settings"] .stButton > button:focus-visible,
[class*="st-key-header_help"] [data-testid="stPopover"] > button:focus-visible,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_refresh"] .stButton > button:focus-visible,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_notifications"] .stButton > button:focus-visible,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_settings"] .stButton > button:focus-visible,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_help"] [data-testid="stPopover"] > button:focus-visible {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  border-width: 0 !important;
  box-shadow: none !important;
  opacity: 0.72 !important;
}
.st-key-header_help [data-testid="stPopover"] > button [data-testid="stIconMaterial"],
[class*="st-key-header_help"] [data-testid="stPopover"] > button [data-testid="stIconMaterial"],
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_help"] [data-testid="stPopover"] > button [data-testid="stIconMaterial"] {
  display: none !important;
}
[class*="st-key-header_refresh"][data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-header_notifications"][data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-header_help"][data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-header_settings"][data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-header_refresh"] [data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-header_notifications"] [data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-header_help"] [data-testid="stVerticalBlockBorderWrapper"],
[class*="st-key-header_settings"] [data-testid="stVerticalBlockBorderWrapper"],
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-header-utility-icon-slot) {
  border: none !important;
  border-width: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
  background-color: transparent !important;
  padding: 0 !important;
}
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-header-utility-icon-slot) > div {
  padding: 0 !important;
}
.st-key-header_refresh .stButton > button p,
.st-key-header_notifications .stButton > button p,
.st-key-header_help [data-testid="stPopover"] > button p,
.st-key-header_settings .stButton > button p,
.st-key-header_back .stButton > button p,
.st-key-header_menu .stButton > button p {
  margin: 0 !important;
  line-height: 1 !important;
  font-size: 1.05rem !important;
}
.st-key-header_notifications {
  position: relative !important;
}
.st-key-header_notifications .ips-header-notify-badge {
  position: absolute !important;
  top: 2px !important;
  right: 2px !important;
  z-index: 2 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-width: 16px !important;
  height: 16px !important;
  padding: 0 4px !important;
  border-radius: 999px !important;
  background: #ef4444 !important;
  color: #ffffff !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  line-height: 1 !important;
  pointer-events: none !important;
}
.st-key-header_primary_action .stButton > button {
  width: auto !important;
  min-width: 112px !important;
  max-width: none !important;
  padding: 0 16px !important;
  background: #3158e6 !important;
  color: #ffffff !important;
  border-color: #3158e6 !important;
}
.st-key-header_primary_action {
  min-width: 112px !important;
}
.st-key-header_secondary_action .stButton > button,
.st-key-header_secondary_action [data-testid="stPopover"] > button {
  width: auto !important;
  min-width: max-content !important;
  max-width: none !important;
  padding: 0 14px !important;
  white-space: nowrap !important;
}
.st-key-header_secondary_action {
  min-width: max-content !important;
}
.st-key-header_date_range {
  min-width: 190px !important;
  max-width: 230px !important;
  flex: 0 0 auto !important;
}
.st-key-header_refresh,
.st-key-header_help,
.st-key-header_settings,
.st-key-header_notifications,
.st-key-header_avatar {
  min-width: 40px !important;
  max-width: 40px !important;
}
.st-key-header_date_range [data-testid="stDateInput"] {
  width: 100% !important;
  min-width: 190px !important;
  max-width: 230px !important;
}
.st-key-header_date_range [data-testid="stDateInput"] > div {
  min-height: 40px !important;
  height: 40px !important;
}
.st-key-header_date_range [data-testid="stDateInput"] input {
  min-height: 40px !important;
  height: 40px !important;
  font-size: 0.8125rem !important;
}
.st-key-header_avatar [data-testid="stPopover"] > button,
[class*="st-key-header_avatar"] [data-testid="stPopover"] > button,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_avatar"] [data-testid="stPopover"] > button {
  width: 40px !important;
  min-width: 40px !important;
  max-width: 40px !important;
  height: 40px !important;
  min-height: 40px !important;
  padding: 0 !important;
  border-radius: 50% !important;
  background: #e2e8f0 !important;
  border: 1px solid #cbd5e1 !important;
  color: #334155 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.01em !important;
  box-shadow: none !important;
  overflow: hidden !important;
}
.st-key-header_avatar [data-testid="stPopover"] > button [data-testid="stIconMaterial"],
[class*="st-key-header_avatar"] [data-testid="stPopover"] > button [data-testid="stIconMaterial"],
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_avatar"] [data-testid="stPopover"] > button [data-testid="stIconMaterial"] {
  display: none !important;
}
.st-key-header_avatar [data-testid="stPopover"] > button p,
[class*="st-key-header_avatar"] [data-testid="stPopover"] > button p,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_avatar"] [data-testid="stPopover"] > button p {
  margin: 0 !important;
  line-height: 1 !important;
  font-size: 0.72rem !important;
  font-weight: 700 !important;
}
.st-key-header_avatar [data-testid="stPopover"] > button:hover,
.st-key-header_avatar [data-testid="stPopover"] > button:focus,
.st-key-header_avatar [data-testid="stPopover"] > button:focus-visible,
[class*="st-key-header_avatar"] [data-testid="stPopover"] > button:hover,
[class*="st-key-header_avatar"] [data-testid="stPopover"] > button:focus,
[class*="st-key-header_avatar"] [data-testid="stPopover"] > button:focus-visible,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_avatar"] [data-testid="stPopover"] > button:hover,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_avatar"] [data-testid="stPopover"] > button:focus,
body.ips-authed-app section[data-testid="stMain"] [class*="st-key-ips_page_header"] [class*="st-key-header_avatar"] [data-testid="stPopover"] > button:focus-visible {
  background: #cbd5e1 !important;
  border-color: #94a3b8 !important;
  color: #1e293b !important;
  opacity: 1 !important;
  box-shadow: none !important;
}
.ips-header-logo {
  width: clamp(200px, 18vw, 340px) !important;
  height: auto !important;
  max-height: 72px !important;
  min-width: 200px !important;
  object-fit: contain !important;
  display: block !important;
  background: transparent !important;
}
.ips-header-title-block {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
  min-width: 0 !important;
  overflow: visible !important;
  padding-bottom: 2px !important;
  text-align: center !important;
  width: 100% !important;
}
.ips-header-icon-wrap {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 32px !important;
  height: 32px !important;
  flex: 0 0 auto !important;
  margin-top: 0 !important;
}
.ips-header-icon-wrap .ips-app-header-icon-svg {
  display: block !important;
  width: 24px !important;
  height: 24px !important;
}
.ips-header-text {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  min-width: 0 !important;
  overflow: visible !important;
  padding-bottom: 4px !important;
  text-align: center !important;
  width: 100% !important;
}
.ips-header-title {
  margin: 0 !important;
  font-size: clamp(24px, 2.1vw, 30px) !important;
  line-height: 1.15 !important;
  font-weight: 700 !important;
  color: #111827 !important;
  letter-spacing: -0.02em !important;
  overflow: visible !important;
  text-overflow: clip !important;
}
.ips-header-subtitle {
  margin: 7px 0 0 0 !important;
  font-size: 13px !important;
  color: #64748b !important;
  line-height: 1.4 !important;
  font-weight: 500 !important;
  overflow: visible !important;
  padding-bottom: 2px !important;
}
.ips-header-badge {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-width: 16px !important;
  height: 16px !important;
  padding: 0 4px !important;
  border-radius: 999px !important;
  background: #ef4444 !important;
  color: #ffffff !important;
  font-size: 10px !important;
  font-weight: 700 !important;
  margin-left: 4px !important;
}
.ips-header-root,
.ips-page-shell-marker {
  display: none !important;
  height: 0 !important;
  width: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
}
.stApp:has(.ips-desktop-nav-rail) .st-key-header_menu {
  display: none !important;
}
@media (min-width: 1440px) {
  [class*="st-key-ips_page_header"],
  [class*="st-key-ips_page_header"] [data-testid="stVerticalBlockBorderWrapper"] {
    min-height: 104px !important;
  }
  .ips-header-title {
    font-size: 30px !important;
  }
}
@media (max-width: 1279px) and (min-width: 1100px) {
  [class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    row-gap: 12px !important;
  }
  [class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) {
    flex: 1 1 100% !important;
    width: 100% !important;
    min-width: 100% !important;
  }
}
@media (max-width: 1439px) and (min-width: 1100px) {
  .ips-header-logo {
    width: clamp(200px, 16vw, 300px) !important;
    min-width: 200px !important;
  }
  [class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) {
    min-width: 480px !important;
  }
  [class*="st-key-ips_page_header"] .st-key-header_help {
    display: none !important;
  }
}
@media (max-width: 1099px) {
  [class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    row-gap: 14px !important;
    align-items: flex-start !important;
  }
  [class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    max-width: 100% !important;
  }
  [class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) {
    flex: 1 1 100% !important;
    width: 100% !important;
    max-width: 100% !important;
  }
  .ips-header-logo {
    width: clamp(220px, 42vw, 340px) !important;
    min-width: 220px !important;
  }
  .ips-header-title {
    font-size: 26px !important;
    white-space: normal !important;
  }
}
@media (max-width: 767px) {
  [class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    row-gap: 10px !important;
  }
  [class*="st-key-ips_page_header"] > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(3) {
    position: static !important;
    left: auto !important;
    top: auto !important;
    transform: none !important;
    flex: 1 1 100% !important;
    width: 100% !important;
    max-width: 100% !important;
    pointer-events: auto !important;
  }
  [class*="st-key-ips_page_header"],
  [class*="st-key-ips_page_header"] [data-testid="stVerticalBlockBorderWrapper"] {
    min-height: 96px !important;
    padding: 16px 16px 18px !important;
  }
  .ips-header-subtitle {
    font-size: 12px !important;
    margin-top: 6px !important;
  }
  .ips-header-logo {
    width: clamp(180px, 58vw, 280px) !important;
    min-width: 180px !important;
  }
  .st-key-header_help {
    display: none !important;
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


__all__ = ["inject_page_header_styles", "IPS_PAGE_HEADER_STYLES_KEY"]
