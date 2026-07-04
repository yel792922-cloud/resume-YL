"""Application configuration.

Centralized settings so every layer reads paths/flags from one place.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/  (two parents up from app/core/config.py)
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FRA_", env_file=".env", extra="ignore")

    app_name: str = "Financial Report Analyzer"

    # Storage
    data_dir: Path = BACKEND_ROOT / "data"
    uploads_dirname: str = "uploads"
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'data' / 'app.db'}"

    # Parsing / OCR
    enable_ocr: bool = True            # try OCR for scanned pages if backend available
    ocr_languages: str = "chi_sim+eng"  # tesseract language packs
    ocr_dpi: int = 200

    # CORS (frontend dev server)
    cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://resume-yl.vercel.app/",
]

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / self.uploads_dirname

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
