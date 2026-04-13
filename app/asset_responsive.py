"""Mobile/tablet layout helpers for Asset Database and Asset Detail."""

from __future__ import annotations

import streamlit as st

try:
    from app.mobile_ui import inject_ips_global_mobile_css
except ImportError:
    from mobile_ui import inject_ips_global_mobile_css  # type: ignore

# Asset Detail: one-column flow on small screens, touch targets, tabs/dataframes, grouped actions.
_ASSET_DETAIL_MOBILE_CSS = """
<style>
/* Back — full width on phones */
@media (max-width: 900px) {
  .ips-ad-back-wrap { width: 100%; max-width: 100%; }
  .ips-ad-back-wrap .stButton,
  .ips-ad-back-wrap .stButton > button {
    width: 100% !important;
  }
  .ips-ad-back-wrap .stButton > button {
    min-height: 3rem;
    font-size: 1.05rem;
  }
}
/* Hero: photo uses full column; slightly tighter vertical rhythm on mobile */
@media (max-width: 900px) {
  .ips-ad-photo-col img {
    width: 100% !important;
    max-width: 100% !important;
    height: auto !important;
    border-radius: 8px;
  }
  .ips-ad-photo-col { margin-bottom: 0.25rem; }
  .ips-ad-meta-col .ips-v { margin-bottom: 10px !important; }
  .ips-ad-meta-col .ips-k { margin-bottom: 2px !important; }
  .ips-ad-hero-stack { margin-top: 0.35rem; }
}
/* Primary image card: full-bleed photo, clear header (field-style screen) */
@media (max-width: 900px) {
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-primary) {
    padding: 0 0 2px 0 !important;
    margin-bottom: 1.1rem !important;
    border-radius: 12px !important;
    overflow: hidden;
    box-shadow: inset 0 3px 0 0 rgba(59, 130, 246, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.04) !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-primary) h5 {
    padding: 12px 14px 10px 14px !important;
    margin: 0 !important;
    border-bottom: 1px solid rgba(71, 85, 105, 0.65) !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.02em !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-primary) [data-testid="stImage"] {
    width: 100% !important;
    max-width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-primary) [data-testid="stImage"] img {
    width: 100% !important;
    max-width: 100% !important;
    height: auto !important;
    border-radius: 0 !important;
    display: block !important;
    object-fit: contain;
    max-height: min(56vh, 480px);
    margin: 0 auto !important;
    background: rgba(15, 23, 42, 0.5);
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-primary) [data-testid="stCaption"] {
    padding: 10px 14px 12px 14px !important;
    margin-top: 0 !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-primary) [data-testid="stAlert"] {
    margin: 10px 14px !important;
  }
}
/* Photos vs Documents: distinct sections, consistent IPS spacing */
@media (max-width: 900px) {
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-photos) {
    border-left: 3px solid rgba(96, 165, 250, 0.7) !important;
    margin-bottom: 1.35rem !important;
    padding: 14px 14px 16px 14px !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-docs) {
    border-left: 3px solid rgba(251, 191, 36, 0.65) !important;
    margin-top: 0.15rem !important;
    margin-bottom: 1.25rem !important;
    padding: 14px 14px 16px 14px !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-photos) h5,
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-section-docs) h5 {
    margin-top: 0 !important;
  }
}
/* QR: compact card below asset info, centered */
@media (max-width: 900px) {
  .ips-ad-qr { text-align: center; margin-top: 0.35rem; margin-bottom: 0.15rem; }
  .ips-ad-qr img,
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-qr-tool) [data-testid="stImage"] img {
    max-width: 112px !important;
    width: 112px !important;
    height: auto !important;
    margin-left: auto !important;
    margin-right: auto !important;
    display: block !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-qr-tool) {
    max-width: 220px !important;
    width: 100% !important;
    margin-left: auto !important;
    margin-right: auto !important;
    margin-top: 0.35rem !important;
    margin-bottom: 0.85rem !important;
    text-align: center !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-qr-tool) .stDownloadButton {
    width: 100% !important;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:has(.ips-ad-qr-tool) .stDownloadButton > button {
    width: 100% !important;
    max-width: 100% !important;
  }
}
/* Top actions + grouped rows: single column on narrow viewports for large tap targets */
@media (max-width: 900px) {
  [data-testid="stVerticalBlock"]:has(.ips-ad-detail-top-actions) .stButton,
  [data-testid="stVerticalBlock"]:has(.ips-ad-detail-top-actions) .stButton > button {
    width: 100% !important;
    max-width: 100% !important;
  }
  .ips-ad-detail-top-actions .stButton > button {
    min-height: 3.1rem !important;
    font-size: 1.05rem !important;
  }
  .ips-ad-actions-primary [data-testid="stHorizontalBlock"],
  .ips-ad-actions-service [data-testid="stHorizontalBlock"],
  .ips-ad-actions-updates [data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 0.55rem !important;
    grid-template-columns: unset !important;
    flex-wrap: nowrap !important;
    align-items: stretch !important;
  }
  .ips-ad-actions-primary [data-testid="column"],
  .ips-ad-actions-service [data-testid="column"],
  .ips-ad-actions-updates [data-testid="column"] {
    width: 100% !important;
    min-width: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
  }
  .ips-ad-actions-primary .stButton > button,
  .ips-ad-actions-service .stButton > button,
  .ips-ad-actions-updates .stButton > button {
    min-height: 3rem !important;
    font-size: 1rem !important;
    width: 100% !important;
    max-width: 100% !important;
  }
  .ips-ad-actions-danger .stButton,
  .ips-ad-actions-danger .stButton > button {
    width: 100% !important;
    max-width: 100% !important;
    min-height: 3rem;
    font-size: 1rem;
  }
  .ips-ad-rental-panel .ips-ad-rental-grid {
    grid-template-columns: 1fr !important;
    gap: 10px !important;
  }
  .ips-ad-hero-stack [data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child .stButton > button {
    min-width: 2.75rem !important;
    min-height: 2.75rem !important;
    font-size: 1.15rem !important;
  }
  .ips-ad-gallery-wrap .stButton > button {
    min-height: 2.85rem !important;
    font-size: 0.95rem !important;
  }
}
/* Tabs: wrap labels, avoid horizontal crawl */
@media (max-width: 900px) {
  [data-testid="stTabs"] [role="tablist"] {
    flex-wrap: wrap !important;
    gap: 0.25rem !important;
    row-gap: 0.35rem !important;
  }
  [data-testid="stTabs"] [role="tab"] {
    font-size: 0.82rem !important;
    padding: 0.35rem 0.5rem !important;
    white-space: normal !important;
    line-height: 1.2 !important;
  }
  [data-testid="stTabs"] [data-testid="stVerticalBlock"] {
    padding-top: 0.35rem !important;
  }
}
/* History dataframes: scroll inside viewport */
@media (max-width: 900px) {
  [data-testid="stMain"] [data-testid="stDataFrame"] {
    max-width: 100vw;
    font-size: 0.85rem;
  }
}
/* Photos & documents: make tap targets friendlier */
@media (max-width: 900px) {
  .ips-ad-gallery-wrap a[href*="ips_gpv"] {
    display: block !important;
    border-radius: 10px;
  }
  .ips-ad-gallery-wrap a[href*="ips_gpv"] img {
    width: 100% !important;
    height: auto !important;
    border-radius: 10px;
  }
  .ips-ad-gallery-thumb-hint {
    font-size: 0.9rem !important;
    margin-top: 6px !important;
    margin-bottom: 8px !important;
  }
  .ips-ad-gallery-preview-panel {
    margin-top: 0.65rem !important;
    padding: 14px 12px 16px 12px !important;
  }
  .ips-ad-gallery-preview-panel .stButton > button {
    min-height: 2.9rem !important;
    font-size: 0.98rem !important;
  }
  /* Document rows: keep the action button prominent */
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"] .stLinkButton > a,
  div[data-testid="stHorizontalBlock"] > div[data-testid="column"] .stDownloadButton > button {
    min-height: 2.85rem !important;
  }
  .ips-ad-doc-mobile-card {
    background: rgba(15, 23, 42, 0.55);
    border: 1px solid rgba(71, 85, 105, 0.5);
    border-radius: 10px;
    padding: 12px 12px 10px 12px;
    margin-bottom: 12px;
  }
  .ips-ad-doc-mobile-icon {
    font-size: 1.75rem;
    margin: 0 0 6px 0;
    line-height: 1.2;
  }
  .ips-ad-doc-mobile-card .stLinkButton,
  .ips-ad-doc-mobile-card .stLinkButton > a,
  .ips-ad-doc-mobile-card .stDownloadButton,
  .ips-ad-doc-mobile-card .stDownloadButton > button {
    width: 100% !important;
    max-width: 100% !important;
    box-sizing: border-box !important;
  }
  .ips-ad-doc-mobile-card .stLinkButton > a,
  .ips-ad-doc-mobile-card .stDownloadButton > button {
    min-height: 3.05rem !important;
    font-size: 1.02rem !important;
    margin-top: 6px !important;
    justify-content: center !important;
  }
}
</style>
"""


def inject_asset_workflow_mobile_css() -> None:
    inject_ips_global_mobile_css()
    st.markdown(_ASSET_DETAIL_MOBILE_CSS, unsafe_allow_html=True)
