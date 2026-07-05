"""Application configuration.

Centralized settings so every layer reads paths/flags from one place.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/  (two parents up from app/core/config.py)
BACKEND_ROOT = Path(__file__).resolve().parents[2]

# Sentinel dev key; production MUST override it (enforced at startup for non-SQLite).
DEFAULT_DEV_SECRET = "dev-insecure-secret-change-me-in-production-0123456789"


def _normalize_db_url(url: str) -> str:
    """Normalize a database URL to a SQLAlchemy-compatible driver form.

    Render/Heroku hand out ``postgres://…``; SQLAlchemy 2.0 needs an explicit
    driver. We standardize on psycopg 3 (``postgresql+psycopg://``).
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
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
        return _normalize_db_url(v) if isinstance(v, str) else v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        # Allow a comma-separated env string, e.g. FRA_CORS_ORIGINS="a,b".
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def using_default_secret(self) -> bool:
        return self.secret_key == DEFAULT_DEV_SECRET

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

    settings = Settings(**overrides)
    settings.ensure_dirs()
    return settings
