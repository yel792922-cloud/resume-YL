"""FastAPI application — the UI-facing boundary over the extraction engine."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_analysis,
    routes_compare,
    routes_documents,
    routes_export,
    routes_qa,
    routes_search,
)
from app.auth import routes_auth
from app.core.config import get_settings
from app.core.db import init_db

settings = get_settings()


import logging

logger = logging.getLogger("app")


def _check_production_config() -> None:
    """Fail fast on unsafe production config; warn on soft issues.

    A non-SQLite database implies production, where a forgeable JWT key is a
    security hole — so refuse to start unless FRA_SECRET_KEY / SECRET_KEY is set.
    """
    if settings.using_default_secret:
        if not settings.is_sqlite:
            raise RuntimeError(
                "SECRET_KEY is unset (using the built-in dev key) but a non-SQLite "
                "database is configured. Set FRA_SECRET_KEY / SECRET_KEY to a long "
                "random value in production."
            )
        logger.warning("Using the insecure dev SECRET_KEY (fine for local dev only).")

    if settings.enable_ocr:
        try:
            from app.parsing.ocr import get_ocr_backend

            if get_ocr_backend().available():
                logger.info("OCR enabled (langs=%s, dpi=%s).", settings.ocr_languages, settings.ocr_dpi)
            else:
                logger.warning(
                    "FRA_ENABLE_OCR is on but the OCR toolchain (tesseract/poppler) "
                    "is unavailable; scanned pages will fall back gracefully."
                )
        except Exception:  # never block startup on the OCR probe
            pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    _check_production_config()
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Stock-research-focused financial report analysis with source traceability.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "0.2.0",
        "max_upload_mb": settings.max_upload_mb,
        "max_uploads_per_user": settings.max_uploads_per_user,
    }


app.include_router(routes_auth.router)
app.include_router(routes_documents.router)
app.include_router(routes_search.router)
app.include_router(routes_compare.router)
app.include_router(routes_export.router)
app.include_router(routes_analysis.router)
app.include_router(routes_qa.router)
