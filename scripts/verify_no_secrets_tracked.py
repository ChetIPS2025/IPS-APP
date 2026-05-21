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
