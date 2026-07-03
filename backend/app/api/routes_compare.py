"""Comparison route: compare multiple reports across periods or companies."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.document import Document
from app.models.schemas import CompareResponse
from app.search import compare_documents

router = APIRouter(prefix="/api/compare", tags=["compare"])


@router.get("", response_model=CompareResponse)
def compare(
    document_ids: list[str] = Query(..., description="Two or more document ids"),
    dimension: str = Query("period", pattern="^(period|company)$"),
    db: Session = Depends(get_db),
):
    if len(document_ids) < 1:
        raise HTTPException(status_code=400, detail="Provide at least one document id")
    docs = [db.get(Document, did) for did in document_ids]
    missing = [did for did, d in zip(document_ids, docs) if d is None]
    if missing:
        raise HTTPException(status_code=404, detail=f"Documents not found: {missing}")
    return compare_documents(db, [d for d in docs if d is not None], dimension=dimension)
