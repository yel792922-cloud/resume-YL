"""ExtractedFact — the source-traceable unit of the product.

Every number, metric, or business signal we surface is one of these rows.
It carries *both* the value **and** everything needed to verify it in the
original report, exactly as required by the product spec:

    company_name, report_type, report_period, metric_name, metric_value,
    unit, language, source_page_number, source_text_snippet, source_bbox,
    source_table_cell_reference, confidence_score, extraction_timestamp,
    version_id
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FactCategory(str, enum.Enum):
    """Which part of the report a fact belongs to."""

    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
    BUSINESS = "business"          # segment/geographic/user metrics
    GUIDANCE = "guidance"
    MANAGEMENT = "management"      # management discussion / commentary
    RISK = "risk"                  # risk factors


class ExtractedFact(Base):
    __tablename__ = "extracted_facts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    # ---- Identity (denormalized from the document for export/comparison) ----
    company_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    report_period: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ---- The concept & value ----
    category: Mapped[FactCategory] = mapped_column(Enum(FactCategory))
    concept_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(128))   # canonical English name
    metric_label: Mapped[str | None] = mapped_column(String(128), nullable=True)  # display label
    raw_label: Mapped[str | None] = mapped_column(String(256), nullable=True)     # as printed in report

    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(256), nullable=True)     # for non-numeric facts
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)            # e.g. CNY_100M, %, USD
    language: Mapped[str] = mapped_column(String(8), default="unknown")            # zh | en

    # ---- Source traceability ----
    source_page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_section: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_text_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Normalized bbox on the page: JSON "[x0, top, x1, bottom]" in 0..1 coords.
    source_bbox_json: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # e.g. "table=1;row=3;col=2"
    source_table_cell_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # ---- Provenance / trust ----
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1
    extraction_method: Mapped[str | None] = mapped_column(String(64), nullable=True)  # rule|table|ocr
    extraction_timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    version_id: Mapped[str] = mapped_column(String(32), default="v1")

    document: Mapped["Document"] = relationship(back_populates="facts")  # noqa: F821
