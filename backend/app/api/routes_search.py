"""Search route: search within a single report."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.document import Document
from app.models.schemas import SearchResponse
from app.search import search_document

router = APIRouter(prefix="/api/documents", tags=["search"])


@router.get("/{document_id}/search", response_model=SearchResponse)
def search_in_document(
    document_id: str,
    q: str = Query("", description="Search query (CN or EN)"),
    limit: int = 50,
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return search_document(db, doc, q, limit=limit)
