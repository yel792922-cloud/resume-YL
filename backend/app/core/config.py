"""Application configuration.

Centralized settings so every layer reads paths/flags from one place.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

# backend/  (two parents up from app/core/config.py)
BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Sentinel dev key; production MUST override it (enforced at startup for non-SQLite).
DEFAULT_DEV_SECRET = "dev-insecure-secret-change-me-in-production-0123456789"

_PSYCOPG_DRIVER = "postgresql+psycopg"


def coerce_db_url(value: str | URL) -> URL:
    """The single source of truth for the database URL.

    Parses any accepted URL (env string or ``URL``) into a SQLAlchemy
    :class:`~sqlalchemy.engine.URL` and standardizes Postgres onto psycopg 3.
    Using ``make_url`` (parser) + ``URL.set`` (builder) — never string surgery —
    means a password with URL-sensitive characters (``%``, ``@``, ``:``, ``/``,
    ``?``, ``#``, ``&``, spaces, …) is decoded once and carried safely to the
    driver. Render/Heroku's ``postgres://`` scheme is upgraded here too.
    """
    url = value if isinstance(value, URL) else make_url(value)
    # get_backend_name() ignores the +driver suffix, so this also upgrades
    # postgresql+psycopg2:// (and a bare postgres://) onto psycopg 3.
    if url.get_backend_name() in ("postgres", "postgresql"):
        url = url.set(drivername=_PSYCOPG_DRIVER)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FRA_", env_file=".env", extra="ignore")

    app_name: str = "Financial Report Analyzer"

    # Storage
    data_dir: Path = BACKEND_ROOT / "data"
    uploads_dirname: str = "uploads"
    # Local dev defaults to SQLite; production sets FRA_DATABASE_URL (or the
    # platform's DATABASE_URL, honored below) to a Postgres URL.
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'data' / 'app.db'}"

    # Auth — MUST be overridden in production via FRA_SECRET_KEY / SECRET_KEY.
    secret_key: str = DEFAULT_DEV_SECRET
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    jwt_algorithm: str = "HS256"

    # Retention (raw file cap per user; structured data is always preserved)
    max_uploads_per_user: int = 10                  # FRA_MAX_UPLOADS_PER_USER

    # Upload / preprocessing
    max_upload_mb: int = 15                          # hard reject above this
    preprocess_enabled: bool = True                  # try to shrink large PDFs
    preprocess_threshold_mb: float = 4.0             # only preprocess files larger than this

    # Parsing / OCR
    enable_ocr: bool = True            # try OCR for scanned pages if backend available
    ocr_languages: str = "chi_sim+eng"  # tesseract language packs
    # Rasterization DPI. Kept conservative (150) so a page image stays ~4 MB and
    # OCR fits comfortably in a 512 MB free-tier instance. Raise for accuracy.
    ocr_dpi: int = 150

    # CORS (frontend origins allowed for direct/browser access).
    # Includes the production Vercel origin (main added it too); comma-separated
    # FRA_CORS_ORIGINS can override. No trailing slash — browsers send the bare
    # origin, so a trailing slash would fail to match.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://resume-yl.vercel.app",
    ]

    @field_validator("database_url", mode="before")
    @classmethod
    def _fix_db_url(cls, v: str) -> str:
        # Store the canonical, safely re-encoded string form (driver upgraded).
        # hide_password=False keeps the real password; render_as_string
        # percent-encodes any special characters correctly.
        if isinstance(v, str) and v:
            return coerce_db_url(v).render_as_string(hide_password=False)
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        # Allow a comma-separated env string, e.g. FRA_CORS_ORIGINS="a,b".
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # When true, the app refuses to start on ephemeral SQLite (see main.py) so a
    # missing DATABASE_URL can never silently drop us onto transient storage that
    # loses users/documents on every redeploy. Auto-enabled on hosting platforms.
    require_durable_db: bool = False           # FRA_REQUIRE_DURABLE_DB

    @property
    def sqlalchemy_url(self) -> URL:
        """The canonical SQLAlchemy URL object — pass this to create_engine and
        Alembic so no layer re-parses/re-formats the URL string by hand."""
        return coerce_db_url(self.database_url)

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_url.get_backend_name() == "sqlite"

    @property
    def using_default_secret(self) -> bool:
        return self.secret_key == DEFAULT_DEV_SECRET

    @property
    def db_backend(self) -> str:
        """Coarse backend name for logging (never exposes credentials)."""
        return self.sqlalchemy_url.get_backend_name() or "unknown"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / self.uploads_dirname

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    import os

    overrides: dict = {}
    # Honor the platform's unprefixed env vars (Render/Heroku set DATABASE_URL).
    if "FRA_DATABASE_URL" not in os.environ and os.environ.get("DATABASE_URL"):
        overrides["database_url"] = os.environ["DATABASE_URL"]
    if "FRA_SECRET_KEY" not in os.environ and os.environ.get("SECRET_KEY"):
        overrides["secret_key"] = os.environ["SECRET_KEY"]

    # Auto-require a durable DB when running on a hosting platform (Render sets
    # RENDER, Heroku sets DYNO). This turns a misconfigured/missing DATABASE_URL
    # into a hard startup failure instead of silent, data-losing SQLite.
    if "FRA_REQUIRE_DURABLE_DB" not in os.environ and (
        os.environ.get("RENDER") or os.environ.get("DYNO")
    ):
        overrides["require_durable_db"] = True

    settings = Settings(**overrides)
    settings.ensure_dirs()
    return settings
