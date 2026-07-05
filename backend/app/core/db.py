"""Database engine / session management (SQLAlchemy 2.0)."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def init_db() -> None:
    """Ensure tables exist. Import models so they register on the metadata.

    ``create_all`` is idempotent (``checkfirst=True``) so it is safe to call on
    every startup: on a fresh database it creates the schema, and on an existing
    one it is a no-op. For controlled schema *changes* in production, use the
    Alembic migrations in ``backend/alembic`` (``alembic upgrade head``).
    """
    from app.models import document, fact, snapshot, user  # noqa: F401  (registers tables)

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
