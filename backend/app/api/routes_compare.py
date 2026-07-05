"""Comparison route: compare the current user's reports across periods/companies."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_db
from app.models.document import Document
from app.models.schemas import CompareResponse
from app.models.user import User
from app.search import compare_documents

router = APIRouter(prefix="/api/compare", tags=["compare"])


@router.get("", response_model=CompareResponse)
def compare(
    document_ids: list[str] = Query(..., description="Two or more document ids"),
    dimension: str = Query("period", pattern="^(period|company)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if len(document_ids) < 1:
        raise HTTPException(status_code=400, detail="Provide at least one document id")
    # Only load documents owned by the current user; any id that isn't theirs
    # (or doesn't exist) is treated as not found — no cross-user comparison.
    docs = []
    for did in document_ids:
        doc = db.get(Document, did)
        if doc is None or doc.user_id != user.id:
            raise HTTPException(status_code=404, detail=f"Document not found: {did}")
        docs.append(doc)
    return compare_documents(db, docs, dimension=dimension)
