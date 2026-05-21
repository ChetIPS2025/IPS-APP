"""Tests for scripts/verify_no_secrets_tracked.py (stdlib unittest — no extra deps)."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_VERIFY_SCRIPT = ROOT / "scripts" / "verify_no_secrets_tracked.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("verify_no_secrets_tracked", _VERIFY_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestLiveSecretDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_module()

    def test_detects_toml_jwt_assignment(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False, encoding="utf-8") as f:
            f.write('SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123xyz"\n')
            path = Path(f.name)
        try:
            hits = self.mod._file_has_live_secrets(path)
            self.assertTrue(any("SUPABASE_SERVICE_ROLE_KEY" in h for h in hits))
        finally:
            path.unlink(missing_ok=True)

    def test_detects_env_jwt_assignment(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8") as f:
            f.write("SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123xyz\n")
            path = Path(f.name)
        try:
            hits = self.mod._file_has_live_secrets(path)
            self.assertTrue(any("SUPABASE_SERVICE_ROLE_KEY" in h for h in hits))
        finally:
            path.unlink(missing_ok=True)

    def test_skips_example_files(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".env.example", delete=False, encoding="utf-8"
        ) as f:
            f.write("SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc123xyz\n")
            path = Path(f.name)
        try:
            self.assertEqual(self.mod._file_has_live_secrets(path), [])
        finally:
            path.unlink(missing_ok=True)

    def test_is_local_secrets_file(self) -> None:
        self.assertTrue(self.mod._is_local_secrets_file(".env"))
        self.assertTrue(self.mod._is_local_secrets_file(".streamlit/secrets.toml"))
        self.assertFalse(self.mod._is_local_secrets_file(".env.example"))
        self.assertFalse(self.mod._is_local_secrets_file(".streamlit/secrets.toml.example"))


if __name__ == "__main__":
    unittest.main()
