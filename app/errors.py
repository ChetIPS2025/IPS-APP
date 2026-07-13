from __future__ import annotations

import logging

import streamlit as st

from app.config import settings
_LOG = logging.getLogger(__name__)


def show_page_error(exc: BaseException, *, context: str = "page") -> None:
    """Log full exception; show a generic message in production."""
    _LOG.error("%s failed: %s", context, exc, exc_info=True)
    if settings.is_production:
        st.error(
            "Something went wrong while loading this page. "
            "If it keeps happening, contact your administrator with the approximate time."
        )
    else:
        st.error(f"**Development mode** — `{context}`")
        st.exception(exc)


def show_auth_error(exc: BaseException) -> None:
    _LOG.warning("Authentication failed: %s", exc)
    if settings.is_production:
        st.error("Sign in failed. Check your email and password, or try again in a moment.")
    else:
        st.error(f"Sign in failed: {exc}")
