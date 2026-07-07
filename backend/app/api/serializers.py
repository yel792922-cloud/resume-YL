"""ORM → Pydantic serializers shared across routes."""
from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document, Page
from app.models.fact import ExtractedFact
from app.models.snapshot import ParseSnapshot
from app.models.schemas import DocumentSummary, FactOut, PageOut, ReportProfileOut, SourceRef
from app.normalization.scope import derive_scope
from app.normalization.metric_kind import classify_kind
from app.profile import infer_profile, profile_from_json


def fact_to_out(f: ExtractedFact) -> FactOut:
    bbox = json.loads(f.source_bbox_json) if f.source_bbox_json else None
    scope = derive_scope(f.category, f.concept_id, f.raw_label, f.report_section)
    kind = classify_kind(f.category, f.concept_id, f.raw_label, f.unit, f.unit == "%")
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
        scope_type=scope.scope_type,
        scope_label=scope.scope_label,
        metric_kind=kind,
        source=SourceRef(
            page_number=f.source_page_number,
            section=f.report_section,
            snippet=f.source_text_snippet,
            bbox=bbox,
            table_cell=f.source_table_cell_reference,
        ),
    )


def document_to_summary(db: Session, d: Document) -> DocumentSummary:
    fact_count = (
        db.query(func.count(ExtractedFact.id))
        .filter(ExtractedFact.document_id == d.id)
        .scalar()
        or 0
    )
    version_count = (
        db.query(func.count(ParseSnapshot.id))
        .filter(ParseSnapshot.document_id == d.id)
        .scalar()
        or 0
    )
    # Stored profile if present; otherwise infer on the fly for legacy rows.
    prof = profile_from_json(d.profile_json)
    if prof is None and d.facts:
        prof = infer_profile(d, list(d.facts), None)
    profile_out = ReportProfileOut(**{
        k: getattr(prof, k) for k in ReportProfileOut.model_fields
    }) if prof else None
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
        raw_available=d.raw_available,
        fact_count=int(fact_count),
        version_count=int(version_count),
        profile=profile_out,
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
