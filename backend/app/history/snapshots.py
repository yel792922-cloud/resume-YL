"""Create and read parse snapshots.

A snapshot is written after every successful extraction. It captures the facts
and summary as JSON so history survives raw-PDF retention cleanup. Snapshots
are immutable and versioned per document (v1, v2, …).
"""
from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.serializers import fact_to_out
from app.models.document import Document
from app.models.fact import ExtractedFact
from app.models.snapshot import ParseSnapshot
from app.summary import build_summary


def _next_version(db: Session, document_id: str) -> int:
    current = (
        db.query(func.max(ParseSnapshot.version))
        .filter(ParseSnapshot.document_id == document_id)
        .scalar()
    )
    return (current or 0) + 1


def create_snapshot(db: Session, document: Document, note: str | None = None) -> ParseSnapshot:
    """Serialize the document's current facts + summary into a new snapshot."""
    facts = (
        db.query(ExtractedFact)
        .filter(ExtractedFact.document_id == document.id)
        .order_by(ExtractedFact.confidence_score.desc())
        .all()
    )
    facts_payload = [fact_to_out(f).model_dump(mode="json") for f in facts]
    summary_payload = build_summary(db, document).model_dump(mode="json")

    snapshot = ParseSnapshot(
        document_id=document.id,
        user_id=document.user_id,
        version=_next_version(db, document.id),
        engine_version="v1",
        fact_count=len(facts),
        page_count=document.page_count,
        language=document.language,
        note=note,
        facts_json=json.dumps(facts_payload, ensure_ascii=False),
        summary_json=json.dumps(summary_payload, ensure_ascii=False),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def list_snapshots(db: Session, document_id: str) -> list[ParseSnapshot]:
    return (
        db.query(ParseSnapshot)
        .filter(ParseSnapshot.document_id == document_id)
        .order_by(ParseSnapshot.version.desc())
        .all()
    )


def get_snapshot(db: Session, document_id: str, version: int) -> ParseSnapshot | None:
    return (
        db.query(ParseSnapshot)
        .filter(ParseSnapshot.document_id == document_id, ParseSnapshot.version == version)
        .first()
    )
