#!/usr/bin/env python3
"""Fail if Streamlit secrets or common credential files are tracked by git."""

from __future__ import annotations

import re
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

# Supabase keys that may hold JWTs (TOML: KEY = "eyJ…" / .env: KEY=eyJ…)
_JWT_SECRET_KEYS = (
    "SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_SECRET_KEY",
)


def _jwt_key_pattern(key: str) -> re.Pattern[str]:
    """Match assignment with optional spaces/quotes around ``=`` (.env and TOML)."""
    return re.compile(
        rf"{re.escape(key)}\s*=\s*\"?(eyJ[A-Za-z0-9_-]{{20,}})",
        re.MULTILINE,
    )


def _build_live_secret_patterns() -> list[tuple[str, re.Pattern[str]]]:
    patterns: list[tuple[str, re.Pattern[str]]] = [
        ("sb_secret_", re.compile(r"sb_secret_[A-Za-z0-9_-]{8,}")),
        ("sb_publishable_", re.compile(r"sb_publishable_[A-Za-z0-9_-]{8,}")),
    ]
    for key in _JWT_SECRET_KEYS:
        patterns.append((f"{key} JWT", _jwt_key_pattern(key)))
    return patterns


_LIVE_SECRET_PATTERNS = _build_live_secret_patterns()


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


def _is_local_secrets_file(rel: str) -> bool:
    norm = rel.replace("\\", "/")
    if norm.endswith(".example"):
        return False
    if norm.endswith("secrets.toml"):
        return True
    name = Path(norm).name
    return name == ".env" or (name.startswith(".env.") and name != ".env.example")


def _file_has_live_secrets(path: Path) -> list[str]:
    if path.name.endswith(".example"):
        return []
    hits: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return hits
    for label, pattern in _LIVE_SECRET_PATTERNS:
        if pattern.search(text):
            hits.append(label)
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

    for ignored in (".streamlit/secrets.toml", ".env"):
        ignore_proc = subprocess.run(
            ["git", "check-ignore", "-q", ignored],
            cwd=ROOT,
            check=False,
        )
        if ignore_proc.returncode != 0:
            errors.append(f"{ignored} is not listed in .gitignore")

    for rel in _git_staged_files():
        if not _is_local_secrets_file(rel):
            continue
        errors.append(f"Staged secrets file must not be committed: {rel}")
        path = ROOT / rel
        if path.is_file():
            for label in _file_has_live_secrets(path):
                errors.append(f"  Staged {rel} contains live credential pattern: {label}")

    for path in FORBIDDEN_TRACKED:
        full = ROOT / path
        if full.is_file():
            for label in _file_has_live_secrets(full):
                if path in tracked:
                    errors.append(f"Tracked {path} contains live credential pattern: {label}")

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
