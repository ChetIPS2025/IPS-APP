from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / ".env.local")
load_dotenv()


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    supabase_url: str = os.getenv("SUPABASE_URL", "")

    # New preferred keys
    supabase_publishable_key: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    supabase_secret_key: str = os.getenv("SUPABASE_SECRET_KEY", "")

    # Backward-compatible legacy keys
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    app_env: str = os.getenv("APP_ENV", "development")
    app_name: str = os.getenv("APP_NAME", "IPS Estimating")
    storage_bucket: str = os.getenv("STORAGE_BUCKET", "ips-storage")
    # File storage: "supabase" (default) uploads to Supabase Storage; "local" writes under LOCAL_STORAGE_ROOT.
    storage_backend: str = (os.getenv("STORAGE_BACKEND", "supabase") or "supabase").strip().lower()
    # When storage_backend is "local", files are stored under this directory (mirrors bucket key paths).
    local_storage_root: str = os.getenv("LOCAL_STORAGE_ROOT", "").strip()

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5")

    # Operations
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    reference_cache_ttl_seconds: int = _int_env("REFERENCE_CACHE_TTL_SECONDS", 120)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod")


settings = Settings()
