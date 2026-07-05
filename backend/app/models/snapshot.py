"""ParseSnapshot — an immutable, structured record of one parsing run.

Snapshots are the app's *long-term* memory. Each re-parse of a document writes
a new versioned snapshot capturing the extracted facts and summary as JSON, so
users can review and compare past parsing runs even after the raw PDF has been
removed by the retention policy. Structured parse history is never deleted by
cleanup — only raw files are.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ParseSnapshot(Base):
    __tablename__ = "parse_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)  # 1-based, per document

    engine_version: Mapped[str] = mapped_column(String(32), default="v1")
    fact_count: Mapped[int] = mapped_column(Integer, default=0)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(8), default="unknown")
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Structured payloads (kept long-term, independent of the raw PDF).
    facts_json: Mapped[str] = mapped_column(Text, default="[]")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="snapshots")  # noqa: F821
