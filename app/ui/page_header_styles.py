"""Authoritative CSS for the shared IPS page header."""

from __future__ import annotations

import streamlit as st

IPS_PAGE_HEADER_STYLES_KEY = "ips_page_header_styles_v2"


def inject_page_header_styles() -> None:
    """Inject shared header styles once per session."""
    if st.session_state.get(IPS_PAGE_HEADER_STYLES_KEY):
        return
    st.session_state[IPS_PAGE_HEADER_STYLES_KEY] = True
    st.markdown(
        """
<style id="ips-page-header-styles-v2">
.st-key-ips_page_header,
.st-key-ips_page_header [data-testid="stVerticalBlockBorderWrapper"] {
  width: 100% !important;
  margin: 0 0 14px 0 !important;
  padding: 10px 14px 8px !important;
  background: #ffffff !important;
  border: 1px solid #e5e7eb !important;
  border-bottom: 2px solid #3158e6 !important;
  border-radius: 0 !important;
  box-sizing: border-box !important;
}
.st-key-ips_page_header [data-testid="stElementContainer"]:has(.ips-header-root) {
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}
.st-key-ips_page_header [data-testid="stHorizontalBlock"] {
  align-items: center !important;
  gap: 8px !important;
  width: 100% !important;
}
.st-key-ips_page_header .stButton,
.st-key-ips_page_header .stDateInput,
.st-key-ips_page_header [data-testid="stPopover"] {
  margin: 0 !important;
}
.st-key-ips_page_header .stButton > button,
.st-key-ips_page_header [data-testid="stPopover"] > button {
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
.st-key-header_help .stButton > button,
.st-key-header_settings .stButton > button {
  width: 40px !important;
  min-width: 40px !important;
  max-width: 40px !important;
  padding: 0 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}
.st-key-header_primary_action .stButton > button {
  width: auto !important;
  min-width: 108px !important;
  padding: 0 16px !important;
  background: #3158e6 !important;
  color: #ffffff !important;
  border-color: #3158e6 !important;
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
.st-key-header_avatar [data-testid="stPopover"] > button {
  width: auto !important;
  min-width: 44px !important;
  max-width: 58px !important;
  padding: 0 10px !important;
}
.ips-header-logo {
  height: 46px !important;
  width: auto !important;
  min-width: 250px !important;
  max-width: 330px !important;
  object-fit: contain !important;
  display: block !important;
  background: transparent !important;
}
.ips-header-title-block {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  min-width: 0 !important;
  overflow: visible !important;
}
.ips-header-icon-wrap {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  width: 28px !important;
  height: 28px !important;
  flex: 0 0 auto !important;
}
.ips-header-icon-wrap .ips-app-header-icon-svg {
  display: block !important;
  width: 22px !important;
  height: 22px !important;
}
.ips-header-text {
  display: flex !important;
  flex-direction: column !important;
  min-width: 0 !important;
  overflow: visible !important;
}
.ips-header-title {
  margin: 0 !important;
  font-size: 25px !important;
  line-height: 1.1 !important;
  font-weight: 700 !important;
  color: #111827 !important;
  letter-spacing: -0.02em !important;
  overflow: visible !important;
  text-overflow: clip !important;
}
.ips-header-subtitle {
  margin: 3px 0 0 0 !important;
  font-size: 12.5px !important;
  color: #64748b !important;
  line-height: 1.3 !important;
  font-weight: 500 !important;
  overflow: visible !important;
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
@media (min-width: 1100px) {
  .ips-header-title {
    white-space: nowrap !important;
  }
  .ips-header-subtitle {
    white-space: nowrap !important;
  }
}
@media (max-width: 1439px) and (min-width: 1100px) {
  .ips-header-logo {
    min-width: 210px !important;
    max-width: 280px !important;
  }
  .st-key-ips_page_header .st-key-header_help {
    display: none !important;
  }
}
@media (max-width: 1099px) {
  .st-key-ips_page_header > div > div > [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    row-gap: 10px !important;
  }
  .st-key-ips_page_header > div > div > [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) {
    flex: 1 1 100% !important;
    width: 100% !important;
    max-width: 100% !important;
  }
  .ips-header-logo {
    min-width: 180px !important;
    max-width: 260px !important;
    height: 44px !important;
  }
  .ips-header-title {
    font-size: 22px !important;
    white-space: normal !important;
  }
}
@media (max-width: 767px) {
  .ips-header-subtitle {
    display: none !important;
  }
  .ips-header-logo {
    min-width: 140px !important;
    max-width: 200px !important;
    height: 40px !important;
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
