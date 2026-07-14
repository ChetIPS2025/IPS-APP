"""Streamlit performance helpers: fragments, app reruns, scroll preservation."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypeVar

import streamlit as st
import streamlit.components.v1 as components

F = TypeVar("F", bound=Callable[..., Any])

try:
    fragment = st.fragment
except AttributeError:  # pragma: no cover — Streamlit < 1.33

    def fragment(func: F) -> F:  # type: ignore[misc]
        return func


def ips_app_rerun() -> None:
    """Rerun the full app (e.g. open a dialog outside the current fragment)."""
    try:
        st.rerun(scope="app")
    except TypeError:
        st.rerun()


def fragment_rerun() -> None:
    """Rerun only the active Streamlit fragment when supported."""
    try:
        st.rerun(scope="fragment")
    except (TypeError, AttributeError):
        st.rerun()


def ips_open_rerun() -> None:
    """Rerun the full app after navigation or opening a dialog outside the fragment."""
    ips_app_rerun()


def inject_scroll_preserve(marker: str) -> None:
    """Persist main-window scroll across Streamlit reruns (sessionStorage)."""
    sk = f"ips_scroll_preserve_injected_{marker}"
    if st.session_state.get(sk):
        return
    st.session_state[sk] = True
    m = json.dumps(str(marker or "default"))
    with st.sidebar:
        components.html(
            f"""
<script>
(function() {{
  const w = window.parent || window;
  const SK = "ips_scroll_" + {m};
  const saved = sessionStorage.getItem(SK);
  if (saved != null && saved !== "") {{
    const y = parseInt(saved, 10);
    if (!Number.isNaN(y) && y > 0) {{
      requestAnimationFrame(function() {{ w.scrollTo(0, y); }});
      setTimeout(function() {{ w.scrollTo(0, y); }}, 50);
    }}
  }}
  if (w.__ipsScrollPreserveHook) return;
  w.__ipsScrollPreserveHook = true;
  let t = null;
  w.addEventListener(
    "scroll",
    function() {{
      if (t) return;
      t = setTimeout(function() {{
        t = null;
        sessionStorage.setItem(SK, String(w.scrollY || 0));
      }}, 120);
    }},
    {{ passive: true }}
  );
}})();
</script>
            """,
            height=0,
        )
