"""Streamlit perf helpers (fragments, app rerun)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

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


def test_fragment_rerun_is_callable() -> None:
    mod = _load_streamlit_perf()
    assert callable(mod.fragment_rerun)


def test_ips_open_rerun_delegates_to_app_rerun() -> None:
    mod = _load_streamlit_perf()
    with patch.object(mod, "ips_app_rerun") as mock_app_rerun:
        mod.ips_open_rerun()
    mock_app_rerun.assert_called_once()


def test_fragment_rerun_uses_fragment_scope_when_supported() -> None:
    mod = _load_streamlit_perf()
    with patch.object(st, "rerun") as mock_rerun:
        mod.fragment_rerun()
    mock_rerun.assert_called_once_with(scope="fragment")


def test_ips_app_rerun_uses_app_scope_when_supported() -> None:
    mod = _load_streamlit_perf()
    with patch.object(st, "rerun") as mock_rerun:
        mod.ips_app_rerun()
    mock_rerun.assert_called_once_with(scope="app")


def test_fragment_rerun_falls_back_on_type_error() -> None:
    mod = _load_streamlit_perf()
    with patch.object(st, "rerun", side_effect=[TypeError("no scope"), None]) as mock_rerun:
        mod.fragment_rerun()
    assert mock_rerun.call_count == 2
    mock_rerun.assert_any_call(scope="fragment")
    mock_rerun.assert_any_call()
