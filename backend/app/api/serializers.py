"""ORM → Pydantic serializers shared across routes."""
from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document, Page
from app.models.fact import ExtractedFact
from app.models.schemas import DocumentSummary, FactOut, PageOut, SourceRef


def fact_to_out(f: ExtractedFact) -> FactOut:
    bbox = json.loads(f.source_bbox_json) if f.source_bbox_json else None
    return FactOut(
        id=f.id,
        document_id=f.document_id,
        category=f.category,
        concept_id=f.concept_id,
        metric_name=f.metric_name,
        metric_label=f.metric_label,
        raw_label=f.raw_label,
        metric_value=f.metric_value,
        value_text=f.value_text,
        unit=f.unit,
        language=f.language,
        report_period=f.report_period,
        confidence_score=f.confidence_score,
        extraction_method=f.extraction_method,
        version_id=f.version_id,
        source=SourceRef(
            page_number=f.source_page_number,
            section=f.report_section,
            snippet=f.source_text_snippet,
            bbox=bbox,
            table_cell=f.source_table_cell_reference,
        ),
    )


def document_to_summary(db: Session, d: Document) -> DocumentSummary:
    count = (
        db.query(func.count(ExtractedFact.id))
        .filter(ExtractedFact.document_id == d.id)
        .scalar()
        or 0
    )
    return DocumentSummary(
        id=d.id,
        filename=d.filename,
        company_name=d.company_name,
        ticker=d.ticker,
        report_type=d.report_type,
        report_period=d.report_period,
        language=d.language,
        page_count=d.page_count,
        is_scanned=d.is_scanned,
        status=d.status,
        status_detail=d.status_detail,
        is_favorite=d.is_favorite,
        fact_count=int(count),
        created_at=d.created_at,
    )


def page_to_out(p: Page) -> PageOut:
    return PageOut(
        page_number=p.page_number,
        width=p.width,
        height=p.height,
        text=p.text,
        source=p.source,
        words=json.loads(p.words_json or "[]"),
        tables=json.loads(p.tables_json or "[]"),
    )
