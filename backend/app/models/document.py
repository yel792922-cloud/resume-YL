"""Document & Page ORM models — the ingested report and its parsed pages."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReportType(str, enum.Enum):
    """Report type — kept language-neutral; display labels handled in UI."""

    ANNUAL = "annual"            # 年报
    INTERIM = "interim"          # 中报 / 半年报
    QUARTERLY = "quarterly"      # 季报
    PROSPECTUS = "prospectus"    # 招股书
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    EXTRACTING = "extracting"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    """An uploaded financial report."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # Owner — every document belongs to exactly one user (v0.2 multi-user).
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(512))
    # Path to the original PDF. May become NULL after retention cleanup removes
    # the raw file; structured data (pages, facts, snapshots) is preserved.
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    raw_available: Mapped[bool] = mapped_column(default=True)

    # Report identity (best-effort at ingest; refined by extraction)
    company_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ticker: Mapped[str | None] = mapped_column(String(32), nullable=True)
    report_type: Mapped[ReportType] = mapped_column(
        Enum(ReportType), default=ReportType.OTHER
    )
    report_period: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. "2024 FY"
    language: Mapped[str] = mapped_column(String(8), default="unknown")  # zh | en | mixed

    # Ingest metadata
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    is_scanned: Mapped[bool] = mapped_column(default=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.UPLOADED
    )
    status_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_favorite: Mapped[bool] = mapped_column(default=False)
    # Report-profile hint/inference (JSON): business structure, geo scope,
    # industry, complexity + rationale. NULL for legacy rows (→ auto-detect).
    profile_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="documents")  # noqa: F821
    pages: Mapped[list["Page"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Page.page_number"
    )
    facts: Mapped[list["ExtractedFact"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["ParseSnapshot"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan", order_by="ParseSnapshot.version"
    )


class Page(Base):
    """A single parsed page: full text plus positioned words and tables.

    ``words`` and ``tables`` are stored as JSON blobs (SQLite ``JSON``) so the
    source-mapping layer can resolve any snippet back to a bounding box.
    """

    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    page_number: Mapped[int] = mapped_column(Integer)  # 1-based

    width: Mapped[float] = mapped_column(Float, default=0.0)
    height: Mapped[float] = mapped_column(Float, default=0.0)
    text: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(16), default="digital")  # digital | ocr

    # Positioned tokens: [{text, x0, top, x1, bottom}], normalized 0..1 coords.
    words_json: Mapped[str] = mapped_column(Text, default="[]")
    # Extracted tables: [{bbox, rows:[[cell,...]]}]
    tables_json: Mapped[str] = mapped_column(Text, default="[]")

    document: Mapped["Document"] = relationship(back_populates="pages")
