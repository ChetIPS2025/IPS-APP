#!/usr/bin/env python3
"""Fail if Streamlit secrets or common credential files are tracked by git."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_TRACKED = (
    ".streamlit/secrets.toml",
    ".env",
)

FORBIDDEN_PATTERNS = (
    "secrets.toml",
    "credentials.json",
    "service_account",
)

# Live credential markers (must not appear in staged/tracked secret files)
_LIVE_SECRET_MARKERS = (
    "sb_secret_",
    "sb_publishable_",
    "SUPABASE_SERVICE_ROLE_KEY = \"eyJ",
    "SUPABASE_ANON_KEY = \"eyJ",
)


def _git_ls_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print("verify_no_secrets_tracked: not a git repo or git unavailable", file=sys.stderr)
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _git_staged_files() -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _file_has_live_secrets(path: Path) -> list[str]:
    hits: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    for marker in _LIVE_SECRET_MARKERS:
        if marker in text:
            hits.append(marker)
    return hits


def main() -> int:
    tracked = _git_ls_files()
    errors: list[str] = []

    for path in FORBIDDEN_TRACKED:
        if path in tracked:
            errors.append(f"Tracked file must be removed from git: {path}")

    for path in tracked:
        if path.endswith(".example"):
            continue
        low = path.lower().replace("\\", "/")
        if any(p in low for p in FORBIDDEN_PATTERNS) and "example" not in low:
            if path not in FORBIDDEN_TRACKED:
                errors.append(f"Suspicious tracked path: {path}")

    ignore_proc = subprocess.run(
        ["git", "check-ignore", "-q", ".streamlit/secrets.toml"],
        cwd=ROOT,
        check=False,
    )
    if ignore_proc.returncode != 0:
        errors.append(".streamlit/secrets.toml is not listed in .gitignore")

    for rel in _git_staged_files():
        norm = rel.replace("\\", "/")
        if norm.endswith("secrets.toml") and not norm.endswith(".example"):
            errors.append(f"Staged secrets file must not be committed: {rel}")
            path = ROOT / rel
            if path.is_file():
                for marker in _file_has_live_secrets(path):
                    errors.append(f"  Staged {rel} contains live credential pattern: {marker}")

    for path in FORBIDDEN_TRACKED:
        full = ROOT / path
        if full.is_file():
            for marker in _file_has_live_secrets(full):
                if path in tracked:
                    errors.append(f"Tracked {path} contains live credential pattern: {marker}")

    if errors:
        print("Secrets safety check FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            "\nIf secrets were ever committed, rotate all keys in Supabase and "
            "remove the file from git history before pushing again.",
            file=sys.stderr,
        )
        return 1

    print("Secrets safety check passed (secrets.toml not tracked, gitignore OK).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
