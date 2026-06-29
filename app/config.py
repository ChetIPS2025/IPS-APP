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


def _is_placeholder(value: str) -> bool:
    """True when a secrets value looks like an unfilled template."""
    low = value.lower()
    return any(
        p in low
        for p in (
            "your-project",
            "your_project",
            "your-publishable",
            "your-anon",
            "your_anon",
            "your-service",
            "changeme",
            "placeholder",
            "example.com",
        )
    ) or len(value) < 10


def _load_streamlit_secrets() -> None:
    """
    Copy ``.streamlit/secrets.toml`` into ``os.environ`` for keys not already set.

    Priority (highest → lowest):
      1. Real values already in ``os.environ`` (set by Render/Docker/CI or a previous load).
      2. ``secrets.toml`` values that are not placeholders.
      3. ``.env`` values (loaded above by ``_load_environment_files``).

    Placeholder values (e.g. "YOUR_PROJECT", "your-publishable-or-anon-key") are silently
    ignored so a half-filled template never blocks real credentials loaded from ``.env``.
    """
    try:
        import streamlit as st
    except ImportError:
        return
    try:
        secrets = st.secrets
    except Exception:
        return

    def _set_env(key: str, value: object) -> None:
        # Never overwrite a value already present in the environment.
        if os.getenv(key):
            return
        if value is None:
            return
        s = str(value).strip().strip('"').strip("'")
        if s and not _is_placeholder(s):
            os.environ[key] = s

    for key in (
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_SECRET_KEY",
        "APP_BASE_URL",
        "APP_ENV",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "TOOL_VISION_PROVIDER",
        "TOOL_VISION_API_KEY",
        "TOOL_OCR_PROVIDER",
        "TOOL_OCR_API_KEY",
        "TOOL_IMAGE_SEARCH_PROVIDER",
        "TOOL_IMAGE_SEARCH_API_KEY",
        "LOG_LEVEL",
    ):
        try:
            if key in secrets:
                _set_env(key, secrets[key])
        except Exception:
            pass

    try:
        if "supabase" in secrets:
            block = secrets["supabase"]
            _set_env("SUPABASE_URL", block.get("url") or block.get("SUPABASE_URL"))
            _set_env(
                "SUPABASE_PUBLISHABLE_KEY",
                block.get("publishable_key")
                or block.get("key")
                or block.get("SUPABASE_PUBLISHABLE_KEY"),
            )
            _set_env(
                "SUPABASE_ANON_KEY",
                block.get("anon_key") or block.get("anon") or block.get("SUPABASE_ANON_KEY"),
            )
            _set_env(
                "SUPABASE_SERVICE_ROLE_KEY",
                block.get("service_role_key") or block.get("SUPABASE_SERVICE_ROLE_KEY"),
            )
    except Exception:
        pass


_load_streamlit_secrets()


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


def _bool_env(name: str, default: bool = False) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
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


_LOCAL_DEV_APP_BASE_URL = "http://localhost:8501"


def _resolve_app_base_url() -> str:
    """
    Public origin, no trailing slash — from ``st.secrets["APP_BASE_URL"]``, env ``APP_BASE_URL``,
    or ``http://localhost:8501`` for local development.
    """
    raw = _strip_env("APP_BASE_URL")
    return raw.strip().rstrip("/") if raw else _LOCAL_DEV_APP_BASE_URL


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
    app_name: str = field(default_factory=lambda: _strip_env("APP_NAME", "IPS Operations"))
    # Public base URL for deep links (no trailing slash). Defaults to live Render; override with APP_BASE_URL.
    app_base_url: str = field(default_factory=_resolve_app_base_url)
    storage_bucket: str = field(default_factory=lambda: _strip_env("STORAGE_BUCKET", "ips-storage"))
    # Supabase Storage bucket for task before/progress/after images (create in dashboard + policies).
    task_photos_bucket: str = field(default_factory=lambda: _strip_env("TASK_PHOTOS_BUCKET", "task-photos"))
    # PM reference uploads (drawings, PDFs) for supervisors — create bucket + policies in Supabase.
    job_reference_attachments_bucket: str = field(
        default_factory=lambda: _strip_env("JOB_REFERENCE_ATTACHMENTS_BUCKET", "job-reference-attachments")
    )
    # File storage: "supabase" (default) uploads to Supabase Storage; "local" writes under LOCAL_STORAGE_ROOT.
    storage_backend: str = field(default_factory=_storage_backend)
    # When storage_backend is "local", files are stored under this directory (mirrors bucket key paths).
    local_storage_root: str = field(default_factory=lambda: _strip_env("LOCAL_STORAGE_ROOT"))

    openai_api_key: str = field(default_factory=lambda: _strip_env("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=_openai_model)

    # Quick Add Tool — photo vision, receipt OCR, image search (provider: openai)
    tool_vision_provider: str = field(default_factory=lambda: _strip_env("TOOL_VISION_PROVIDER", "openai"))
    tool_vision_api_key: str = field(default_factory=lambda: _strip_env("TOOL_VISION_API_KEY"))
    tool_ocr_provider: str = field(default_factory=lambda: _strip_env("TOOL_OCR_PROVIDER", "openai"))
    tool_ocr_api_key: str = field(default_factory=lambda: _strip_env("TOOL_OCR_API_KEY"))
    tool_image_search_provider: str = field(
        default_factory=lambda: _strip_env("TOOL_IMAGE_SEARCH_PROVIDER", "openai")
    )
    tool_image_search_api_key: str = field(default_factory=lambda: _strip_env("TOOL_IMAGE_SEARCH_API_KEY"))

    # Email notifications (provider-agnostic)
    email_provider: str = field(default_factory=lambda: _strip_env("EMAIL_PROVIDER", "resend"))
    email_api_key: str = field(default_factory=lambda: _strip_env("EMAIL_API_KEY"))
    email_from: str = field(default_factory=lambda: _strip_env("EMAIL_FROM", "IPS Updates <no-reply@ips-app.local>"))
    email_reply_to: str = field(default_factory=lambda: _strip_env("EMAIL_REPLY_TO", ""))
    pipeline_digest_recipients: str = field(
        default_factory=lambda: _strip_env("PIPELINE_DIGEST_RECIPIENTS", "")
    )

    # Operations
    log_level: str = field(default_factory=lambda: _strip_env("LOG_LEVEL", "INFO"))
    # When true, logs ``[perf] … ms`` for major blocks (see ``app.perf_debug``). Env: IPS_DEBUG_PERFORMANCE or DEBUG_PERFORMANCE.
    debug_performance: bool = field(
        default_factory=lambda: _bool_env("IPS_DEBUG_PERFORMANCE") or _bool_env("DEBUG_PERFORMANCE")
    )
    debug_qr: bool = field(default_factory=lambda: _bool_env("DEBUG_QR"))
    reference_cache_ttl_seconds: int = field(
        default_factory=lambda: _int_env("REFERENCE_CACHE_TTL_SECONDS", 120)
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in ("production", "prod")


def validate_supabase_public_config() -> str | None:
    """
    Return a user-facing error message when URL/key are missing or obviously wrong.
    None means configuration looks usable.
    """
    url = (settings.supabase_url or "").strip()
    key = (_publishable_key() or "").strip()
    if not url or not key:
        return (
            "Supabase is not configured. Add SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY "
            "(or SUPABASE_ANON_KEY) to `.streamlit/secrets.toml` or a project-root `.env` file."
        )
    low_url, low_key = url.lower(), key.lower()
    if "your-project" in low_url or "your_project" in low_url:
        return "SUPABASE_URL is still a placeholder. Use your project URL from Supabase → Settings → API."
    placeholders = (
        "your-publishable",
        "your-anon",
        "your_publishable",
        "your_anon",
        "changeme",
        "placeholder",
        "example.com",
    )
    if any(p in low_key for p in placeholders) or len(key) < 20:
        return (
            "SUPABASE_PUBLISHABLE_KEY (or SUPABASE_ANON_KEY) is missing or still a placeholder. "
            "In Supabase Dashboard → Project Settings → API, copy the **anon public** key "
            "(JWT starting with eyJ…, or sb_publishable_…). Do not paste the service_role key here."
        )
    if key.startswith(("sb_secret_", "sbp_")) and not key.startswith("sb_publishable_"):
        return (
            "The configured key looks like a **secret/service** key. For sign-in, use the "
            "**anon / publishable** key from Supabase → Settings → API."
        )
    if not (
        key.startswith("eyJ")
        or key.startswith("sb_publishable_")
    ):
        return (
            "SUPABASE_PUBLISHABLE_KEY does not look like a valid Supabase anon/publishable key. "
            "Copy it again from Supabase → Settings → API (anon public)."
        )
    return None


# Visible in sidebar / PWA cache busting (override with IPS_APP_VERSION in env).
APP_VERSION: str = _strip_env("IPS_APP_VERSION", "2.5.0")

settings = Settings()
