from __future__ import annotations

import logging

import streamlit as st

try:
    from config import settings
except ImportError:
    from app.config import settings  # type: ignore

_LOG = logging.getLogger(__name__)


def show_page_error(exc: BaseException, *, context: str = "page") -> None:
    """Log full exception; show a generic message in production."""
    _LOG.error("%s failed: %s", context, exc, exc_info=True)
    if settings.is_production:
        st.error("Something went wrong. If this continues, contact your administrator.")
    else:
        st.exception(exc)


def show_auth_error(exc: BaseException) -> None:
    _LOG.warning("Authentication failed: %s", exc)
    if settings.is_production:
        st.error("Sign in failed. Check your email and password.")
    else:
        st.error(str(exc))
