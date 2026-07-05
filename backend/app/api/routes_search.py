"""Search route: search within a single report (owner-scoped)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.ownership import get_owned_document
from app.auth.deps import get_current_user
from app.core.db import get_db
from app.models.schemas import SearchResponse
from app.models.user import User
from app.search import search_document

router = APIRouter(prefix="/api/documents", tags=["search"])


@router.get("/{document_id}/search", response_model=SearchResponse)
def search_in_document(
    document_id: str,
    q: str = Query("", description="Search query (CN or EN)"),
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = get_owned_document(db, document_id, user)
    return search_document(db, doc, q, limit=limit)
