"""Export routes: download extracted facts (with traceability) as CSV / JSON."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.document import Document
from app.models.fact import ExtractedFact
from app.summary import facts_to_csv, facts_to_json

router = APIRouter(prefix="/api/documents", tags=["export"])


def _facts(db: Session, document_id: str) -> list[ExtractedFact]:
    if db.get(Document, document_id) is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return (
        db.query(ExtractedFact)
        .filter(ExtractedFact.document_id == document_id)
        .order_by(ExtractedFact.category, ExtractedFact.confidence_score.desc())
        .all()
    )


@router.get("/{document_id}/export.csv")
def export_csv(document_id: str, db: Session = Depends(get_db)):
    csv_text = facts_to_csv(_facts(db, document_id))
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{document_id}_facts.csv"'},
    )


@router.get("/{document_id}/export.json")
def export_json(document_id: str, db: Session = Depends(get_db)):
    json_text = facts_to_json(_facts(db, document_id))
    return Response(
        json_text,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{document_id}_facts.json"'},
    )
