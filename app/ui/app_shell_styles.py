"""Authoritative top spacing for the authenticated IPS app shell."""

from __future__ import annotations

import streamlit as st

IPS_APP_SHELL_LAYOUT_STYLES_KEY = "ips_app_shell_layout_styles_v1"


def inject_app_shell_layout_styles() -> None:
    """Inject shared main-content top spacing once per session."""
    if st.session_state.get(IPS_APP_SHELL_LAYOUT_STYLES_KEY):
        return
    st.session_state[IPS_APP_SHELL_LAYOUT_STYLES_KEY] = True
    st.markdown(
        """
<style id="ips-app-shell-layout-v1">
:root {
  --ips-main-top-gap: 12px;
}
body.ips-authed-app [data-testid="stAppViewContainer"] {
  padding-top: 0 !important;
  margin-top: 0 !important;
}
body.ips-authed-app [data-testid="stAppViewBlockContainer"],
body.ips-authed-app [data-testid="stMainBlockContainer"],
body.ips-authed-app section[data-testid="stMain"] .block-container,
body.ips-authed-app section.main .block-container {
  padding-top: var(--ips-main-top-gap) !important;
  margin-top: 0 !important;
}
body.ips-authed-app section[data-testid="stMain"] > div {
  margin-top: 0 !important;
  padding-top: 0 !important;
}
body.ips-authed-app section[data-testid="stMain"] [data-testid="stVerticalBlock"] > div {
  padding-top: 0 !important;
}
body.ips-authed-app .st-key-ips_page_header,
body.ips-authed-app .st-key-ips_page_header [data-testid="stVerticalBlockBorderWrapper"] {
  margin-top: 0 !important;
}
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(.st-key-ips_page_header) {
  margin-top: 0 !important;
  padding-top: 0 !important;
}
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(style),
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(script) {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(iframe[title="streamlit_components_v1.iframe"][height="0"]),
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(> div[style*="height: 0px"] > iframe[title="streamlit_components_v1.iframe"]),
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(> div[style*="height:0px"] > iframe[title="streamlit_components_v1.iframe"]) {
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
  border: none !important;
}
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(iframe[title="streamlit_components_v1.iframe"][height="0"]) > div,
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(> div[style*="height: 0px"] > iframe[title="streamlit_components_v1.iframe"]) > div,
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(> div[style*="height:0px"] > iframe[title="streamlit_components_v1.iframe"]) > div,
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(iframe[title="streamlit_components_v1.iframe"][height="0"]) iframe,
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(> div[style*="height: 0px"] > iframe[title="streamlit_components_v1.iframe"]) iframe,
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(> div[style*="height:0px"] > iframe[title="streamlit_components_v1.iframe"]) iframe {
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  border: none !important;
  overflow: hidden !important;
}
body.ips-authed-app section[data-testid="stMain"] > div > [data-testid="stVerticalBlock"] {
  gap: 0 !important;
}
body.ips-authed-app section[data-testid="stMain"] [data-testid="stElementContainer"]:has(.ips-page-shell-marker):not(:has(.ips-app-page-header-marker)):not(:has(.st-key-ips_page_header)) {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


__all__ = ["inject_app_shell_layout_styles", "IPS_APP_SHELL_LAYOUT_STYLES_KEY"]
