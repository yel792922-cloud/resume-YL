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
# uvicorn configures this logger at INFO, so startup diagnostics reliably show up
# in Render/Vercel logs (the bare "app" logger would be swallowed by default).
startup_logger = logging.getLogger("uvicorn.error")


def _check_production_config(s=None) -> None:
    """Fail fast on unsafe production config; warn on soft issues.

    Two production hazards are guarded here:
    * a forgeable JWT key (dev SECRET_KEY) with a real database, and
    * silently running on **ephemeral SQLite** — which loses every registered
      user and their documents on each redeploy/restart.
    """
    settings = s if s is not None else globals()["settings"]
    # Make the effective persistence backend visible in the logs — the single
    # most useful signal when accounts appear to "disappear".
    startup_logger.info(
        "Auth/persistence: db_backend=%s durable_required=%s secret=%s",
        settings.db_backend,
        settings.require_durable_db,
        "dev-default" if settings.using_default_secret else "configured",
    )

    # Never silently fall back to transient storage in production.
    if settings.require_durable_db and settings.is_sqlite:
        raise RuntimeError(
            "A durable database is required here (hosting platform detected) but "
            "the app is configured to use SQLite, which is ephemeral on this "
            "filesystem — registered users would be lost on every redeploy. Set "
            "DATABASE_URL (or FRA_DATABASE_URL) to your Postgres connection string."
        )

    if settings.using_default_secret:
        if not settings.is_sqlite or settings.require_durable_db:
            raise RuntimeError(
                "SECRET_KEY is unset (using the built-in dev key) in a production "
                "configuration. Set FRA_SECRET_KEY / SECRET_KEY to a long random "
                "value so login tokens stay valid and unforgeable across redeploys."
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
