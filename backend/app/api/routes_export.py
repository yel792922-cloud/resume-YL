"""Export routes: download the current user's extracted facts as CSV / JSON."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.api.ownership import get_owned_document
from app.auth.deps import get_current_user
from app.core.db import get_db
from app.models.fact import ExtractedFact
from app.models.user import User
from app.summary import facts_to_csv, facts_to_json

router = APIRouter(prefix="/api/documents", tags=["export"])


def _facts(db: Session, document_id: str, user: User) -> list[ExtractedFact]:
    get_owned_document(db, document_id, user)
    return (
        db.query(ExtractedFact)
        .filter(ExtractedFact.document_id == document_id)
        .order_by(ExtractedFact.category, ExtractedFact.confidence_score.desc())
        .all()
    )


@router.get("/{document_id}/export.csv")
def export_csv(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    csv_text = facts_to_csv(_facts(db, document_id, user))
    return PlainTextResponse(
        csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{document_id}_facts.csv"'},
    )


@router.get("/{document_id}/export.json")
def export_json(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    json_text = facts_to_json(_facts(db, document_id, user))
    return Response(
        json_text,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{document_id}_facts.json"'},
    )
