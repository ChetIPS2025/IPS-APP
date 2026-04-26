from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in minimal environments

    def load_dotenv(
        dotenv_path: str | os.PathLike[str] | None = None,
        *args: object,
        **kwargs: object,
    ) -> bool:
        return False


ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent


def _load_environment_files() -> None:
    """
    Load local env files from the project root (next to ``app/``).

    - ``.env`` is applied first and does **not** override variables already set in
      ``os.environ`` (so Render / Docker / CI injected values win).
    - ``.env.local`` is applied second and **does** override values from ``.env`` so
      developers can override project defaults without editing shared ``.env`` files.

    Missing files are ignored. We intentionally do **not** call ``load_dotenv()`` with
    no path (cwd-based), which is brittle under different launch directories.
    """
    root_env = ROOT_DIR / ".env"
    root_local = ROOT_DIR / ".env.local"

    if root_env.is_file():
        load_dotenv(root_env, override=False, encoding="utf-8")
    if root_local.is_file():
        load_dotenv(root_local, override=True, encoding="utf-8")


_load_environment_files()


def _strip_env(name: str, default: str = "") -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    s = str(raw).strip()
    return s if s else default


def _first_nonempty(*names: str) -> str:
    for name in names:
        v = _strip_env(name)
        if v:
            return v
    return ""


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _publishable_key() -> str:
    """Prefer ``SUPABASE_PUBLISHABLE_KEY``; fall back to legacy ``SUPABASE_ANON_KEY``."""
    return _first_nonempty("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY")


def _anon_key() -> str:
    """Legacy anon key column (may be empty when only the new publishable key is set)."""
    return _strip_env("SUPABASE_ANON_KEY")


def _service_role_key() -> str:
    return _strip_env("SUPABASE_SERVICE_ROLE_KEY")


def _secret_key() -> str:
    """Often used for the Supabase service-role JWT under newer naming (see ``db``)."""
    return _strip_env("SUPABASE_SECRET_KEY")


def _openai_model() -> str:
    return _strip_env("OPENAI_MODEL", "gpt-5") or "gpt-5"


def _storage_backend() -> str:
    v = (os.getenv("STORAGE_BACKEND", "supabase") or "supabase").strip().lower()
    return v if v else "supabase"


@dataclass(frozen=True)
class Settings:
    supabase_url: str = field(default_factory=lambda: _strip_env("SUPABASE_URL"))

    # Preferred keys (publishable also accepts legacy SUPABASE_ANON_KEY via _publishable_key)
    supabase_publishable_key: str = field(default_factory=_publishable_key)
    supabase_secret_key: str = field(default_factory=_secret_key)

    # Backward-compatible legacy key names (still read directly from env)
    supabase_anon_key: str = field(default_factory=_anon_key)
    supabase_service_role_key: str = field(default_factory=_service_role_key)

    app_env: str = field(default_factory=lambda: _strip_env("APP_ENV", "development"))
    app_name: str = field(default_factory=lambda: _strip_env("APP_NAME", "IPS Estimating"))
    # Public base URL for deep links (no trailing slash), e.g. https://ips-app.onrender.com
    app_base_url: str = field(default_factory=lambda: _strip_env("APP_BASE_URL"))
    storage_bucket: str = field(default_factory=lambda: _strip_env("STORAGE_BUCKET", "ips-storage"))
    # File storage: "supabase" (default) uploads to Supabase Storage; "local" writes under LOCAL_STORAGE_ROOT.
    storage_backend: str = field(default_factory=_storage_backend)
    # When storage_backend is "local", files are stored under this directory (mirrors bucket key paths).
    local_storage_root: str = field(default_factory=lambda: _strip_env("LOCAL_STORAGE_ROOT"))

    openai_api_key: str = field(default_factory=lambda: _strip_env("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=_openai_model)

    # Operations
    log_level: str = field(default_factory=lambda: _strip_env("LOG_LEVEL", "INFO"))
    reference_cache_ttl_seconds: int = field(
        default_factory=lambda: _int_env("REFERENCE_CACHE_TTL_SECONDS", 120)
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod")


settings = Settings()
