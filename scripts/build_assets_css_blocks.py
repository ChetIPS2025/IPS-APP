"""Build assets_css_blocks.py from captured rendered CSS."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "app" / "components"


def _read(name: str) -> str:
    return (COMP / f"_assets_css_capture_{name}.txt").read_text(encoding="utf-8")


def _py_str(value: str) -> str:
    return repr(value)


def _css_blocks(css: str) -> list[str]:
    """Split CSS into rule blocks (best-effort)."""
    blocks: list[str] = []
    depth = 0
    start = 0
    for idx, ch in enumerate(css):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                block = css[start : idx + 1].strip()
                if block:
                    blocks.append(block)
                start = idx + 1
    tail = css[start:].strip()
    if tail:
        blocks.append(tail)
    return blocks


def _filter_blocks(blocks: list[str], *, include: str | None = None, exclude: tuple[str, ...] = ()) -> str:
    kept: list[str] = []
    for block in blocks:
        if exclude and any(token in block for token in exclude):
            continue
        if include and include not in block:
            continue
        kept.append(block)
    return "\n\n".join(kept)


def main() -> None:
    layout = _read("layout")
    module = _read("module")
    page = _read("page")

    table_idx = layout.find(".st-key-assets_table_wrap {")
    layout_shell = layout[:table_idx].strip() if table_idx > 0 else layout
    layout_equipment = layout[table_idx:].strip() if table_idx > 0 else ""

    ser_marker = (
        '.st-key-assets_small_tools_table_wrap [data-testid="stVerticalBlock"] '
        '> [data-testid="stHorizontalBlock"]'
    )
    ser_idx = module.find(ser_marker)
    hdr_idx = module.find(".ips-assets-header-row {")
    module_equipment = module[:ser_idx].strip() if ser_idx > 0 else module
    module_serialized = module[ser_idx:hdr_idx].strip() if ser_idx > 0 and hdr_idx > ser_idx else ""
    module_shared = module[hdr_idx:].strip() if hdr_idx > 0 else ""

    ht_idx = page.find("/* Small Hand Tools tab")
    det_idx = page.find("/* Detail panel inside table card */")
    page_before_hand = page[:ht_idx].strip() if ht_idx > 0 else page
    page_hand = page[ht_idx:det_idx].strip() if ht_idx > 0 and det_idx > ht_idx else ""
    page_detail = page[det_idx:].strip() if det_idx > 0 else ""

    page_blocks = _css_blocks(page_before_hand)
    page_chrome = _filter_blocks(
        page_blocks,
        exclude=("assets_small_tools_table_wrap", "assets_hand_tools_table_wrap", "assets_table_wrap"),
    )
    page_equipment = _filter_blocks(
        page_blocks,
        include="assets_table_wrap",
        exclude=("assets_small_tools_table_wrap", "assets_hand_tools_table_wrap"),
    )
    page_serialized = _filter_blocks(page_blocks, include="assets_small_tools_table_wrap")

    out = COMP / "assets_css_blocks.py"
    body = "\n".join(
        [
            '"""Tab-scoped CSS blocks for the Assets page (rendered tokens)."""',
            "from __future__ import annotations",
            "",
            f"LAYOUT_SHELL_CSS = {_py_str(layout_shell)}",
            "",
            f"LAYOUT_EQUIPMENT_CSS = {_py_str(layout_equipment)}",
            "",
            f"MODULE_EQUIPMENT_CSS = {_py_str(module_equipment)}",
            "",
            f"MODULE_SERIALIZED_CSS = {_py_str(module_serialized)}",
            "",
            f"MODULE_SHARED_CSS = {_py_str(module_shared)}",
            "",
            f"PAGE_CHROME_CSS = {_py_str(page_chrome)}",
            "",
            f"PAGE_EQUIPMENT_CSS = {_py_str(page_equipment)}",
            "",
            f"PAGE_SERIALIZED_CSS = {_py_str(page_serialized)}",
            "",
            f"PAGE_HAND_TOOLS_CSS = {_py_str(page_hand)}",
            "",
            f"PAGE_DETAIL_CSS = {_py_str(page_detail)}",
            "",
        ]
    )
    out.write_text(body, encoding="utf-8")
    sizes = {
        "layout_shell": len(layout_shell),
        "layout_equipment": len(layout_equipment),
        "module_equipment": len(module_equipment),
        "module_serialized": len(module_serialized),
        "module_shared": len(module_shared),
        "page_chrome": len(page_chrome),
        "page_equipment": len(page_equipment),
        "page_serialized": len(page_serialized),
        "page_hand": len(page_hand),
        "page_detail": len(page_detail),
    }
    print("Wrote assets_css_blocks.py", sizes)


if __name__ == "__main__":
    main()
