"""Capture rendered Assets CSS via mocked Streamlit injection.

Regenerates ``app/components/_assets_css_capture_*.txt`` for
``scripts/build_assets_css_blocks.py``. Edit ``assets_css_blocks.py`` directly
for routine CSS tweaks; rerun this script only when rebundling from injectors.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import streamlit as st

st.session_state.clear()
captured: list[str] = []


def _mock_markdown(html: str, *, unsafe_allow_html: bool = False) -> None:
    captured.append(html)


def _joined_css(chunks: list[str]) -> str:
    parts: list[str] = []
    for html in chunks:
        match = re.search(r"<style[^>]*>(.*?)</style>", html, re.S)
        if match:
            parts.append(match.group(1).strip())
    return "\n\n".join(parts)


st.markdown = _mock_markdown  # type: ignore[method-assign]
st.sidebar = MagicMock()
st.sidebar.markdown = _mock_markdown

from app.components import assets_page_layout
from app.styles import inject_assets_module_css
from app.ui import assets_components

captured.clear()
assets_page_layout.inject_assets_page_layout_css()
layout_css = _joined_css(captured)

captured.clear()
inject_assets_module_css()
module_css = _joined_css(captured)

captured.clear()
assets_components.inject_assets_page_styles()
page_css = _joined_css(captured)

for name, css in [
    ("layout", layout_css),
    ("module", module_css),
    ("page", page_css),
]:
    out = ROOT / "app" / "components" / f"_assets_css_capture_{name}.txt"
    out.write_text(css, encoding="utf-8")
    print(name, len(css), "->", out.name)
