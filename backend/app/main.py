"""FastAPI application — the UI-facing boundary over the extraction engine."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_compare, routes_documents, routes_export, routes_search
from app.auth import routes_auth
from app.core.config import get_settings
from app.core.db import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
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
