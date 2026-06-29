"""Streamlit perf helpers (fragments, app rerun)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import streamlit as st


def _load_streamlit_perf():
    path = Path(__file__).resolve().parents[1] / "app" / "ui" / "streamlit_perf.py"
    spec = importlib.util.spec_from_file_location("streamlit_perf", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fragment_is_streamlit_fragment_or_passthrough() -> None:
    mod = _load_streamlit_perf()
    assert callable(mod.fragment)
    if hasattr(st, "fragment"):
        assert mod.fragment is st.fragment


def test_ips_app_rerun_is_callable() -> None:
    mod = _load_streamlit_perf()
    assert callable(mod.ips_app_rerun)
