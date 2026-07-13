"""Remove legacy ImportError fallback imports; keep app.* imports only."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
SCRIPTS = ROOT / "scripts"

BARE_PREFIXES = (
    "auth",
    "components",
    "proposal",
    "services",
    "pages",
    "ui",
    "db",
    "navigation",
    "styles",
    "utils",
    "branding",
    "data_cache",
    "errors",
    "config",
    "phase2",
    "pwa",
    "device_label",
    "confirm_delete",
    "table_actions",
    "ips_crud_list_styles",
    "estimate",
    "data",
    "mobile_ui",
    "perf_debug",
    "logging_config",
    "ips_app_shell",
)

BARE_IMPORT_RE = re.compile(
    r"^(\s*)from\s+(" + "|".join(re.escape(p) for p in BARE_PREFIXES) + r")(\.| import)"
)
APP_IMPORT_RE = re.compile(r"^(\s*)from\s+app\.")


def _import_module_name(line: str) -> str | None:
    stripped = line.strip()
    m = re.match(r"^from ([\w.]+) import", stripped)
    if m:
        return m.group(1)
    m = re.match(r"^import ([\w.]+)", stripped)
    if m:
        return m.group(1).split(".", 1)[0]
    return None


def _module_is_legacy(module: str) -> bool:
    for prefix in BARE_PREFIXES:
        if module == prefix or module.startswith(f"{prefix}."):
            return True
    return False


def _is_legacy_fallback_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("from ") and not stripped.startswith("import "):
        return False
    if stripped.startswith("from app.") or stripped.startswith("import app."):
        return False
    module = _import_module_name(stripped)
    if not module:
        return False
    return _module_is_legacy(module)


def _convert_bare_to_app(line: str) -> str:
    stripped = line.lstrip()
    indent = line[: len(line) - len(stripped)]
    module = _import_module_name(stripped)
    if not module or not _module_is_legacy(module):
        return line
    if stripped.startswith("from "):
        return indent + stripped.replace(f"from {module}", f"from app.{module}", 1)
    if stripped.startswith("import "):
        root = module.split(".", 1)[0]
        return indent + stripped.replace(f"import {root}", f"import app.{root}", 1)
    return line


def _block_indent(lines: list[str], start: int) -> int:
    m = re.match(r"^(\s*)", lines[start])
    return len(m.group(1)) if m else 0


def _is_try_import_fallback(lines: list[str], i: int) -> bool:
    if not lines[i].strip().startswith("try:"):
        return False
    base = _block_indent(lines, i)
    j = i + 1
    has_app = False
    while j < len(lines):
        line = lines[j]
        if not line.strip():
            j += 1
            continue
        ind = _block_indent(lines, j)
        if ind <= base and line.strip():
            break
        if APP_IMPORT_RE.match(line) or "import app." in line:
            has_app = True
        j += 1
    if j >= len(lines) or not lines[j].strip().startswith("except ImportError"):
        return False
    k = j + 1
    has_bare = False
    has_only_app_dup = True
    saw_except_import = False
    while k < len(lines):
        line = lines[k]
        if not line.strip():
            k += 1
            continue
        ind = _block_indent(lines, k)
        if ind <= base and line.strip():
            break
        stripped = line.strip()
        if stripped.startswith("from ") or stripped.startswith("import "):
            saw_except_import = True
            if _is_legacy_fallback_line(line):
                has_bare = True
                has_only_app_dup = False
            elif not (stripped.startswith("from app.") or stripped.startswith("import app.")):
                has_only_app_dup = False
        k += 1
    if has_app and has_bare:
        return True
    if has_app and has_only_app_dup and saw_except_import:
        return True
    return False


def _unwrap_try_except(lines: list[str], i: int) -> tuple[list[str], int]:
    base = _block_indent(lines, i)
    body_indent = base + 4
    dedent = body_indent - base
    j = i + 1
    body: list[str] = []
    while j < len(lines):
        line = lines[j]
        if not line.strip():
            j += 1
            continue
        ind = _block_indent(lines, j)
        if ind <= base and line.strip():
            break
        if ind >= body_indent:
            new_indent = max(base, ind - dedent)
            content = line[ind:].rstrip("\n")
            body.append(" " * new_indent + content)
        j += 1
    while j < len(lines) and not lines[j].strip().startswith("except ImportError"):
        j += 1
    if j < len(lines):
        j += 1
        while j < len(lines):
            line = lines[j]
            if not line.strip():
                j += 1
                continue
            ind = _block_indent(lines, j)
            if ind <= base:
                break
            j += 1
    return body, j


def transform_source(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        if _is_try_import_fallback(lines, i):
            body, nxt = _unwrap_try_except(lines, i)
            for b in body:
                out.append(b + "\n")
            i = nxt
            continue
        line = lines[i]
        if _is_legacy_fallback_line(line.rstrip("\n")):
            converted = _convert_bare_to_app(line.rstrip("\n"))
            out.append(converted + ("\n" if line.endswith("\n") else ""))
        else:
            out.append(line)
        i += 1
    return "".join(out)


def process_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = transform_source(original)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main() -> int:
    changed: list[str] = []
    targets = list(APP.rglob("*.py"))
    targets.extend(SCRIPTS.glob("*.py"))
    targets = [p for p in targets if p.name != "remove_legacy_import_fallbacks.py"]
    for path in sorted(targets):
        if process_file(path):
            changed.append(str(path.relative_to(ROOT)))
    print(f"Updated {len(changed)} files")
    for name in changed:
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
