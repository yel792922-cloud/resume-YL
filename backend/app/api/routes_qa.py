"""v4 Q&A route: evidence-grounded question answering for a single report.

Owner-scoped, read-only, computed on demand (nothing persisted).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.ownership import get_owned_document
from app.auth.deps import get_current_user
from app.core.db import get_db
from app.models.schemas import AnswerResponse, AskRequest
from app.models.user import User
from app.qa import answer_question

router = APIRouter(prefix="/api/documents", tags=["qa"])


@router.post("/{document_id}/ask", response_model=AnswerResponse)
def ask(
    document_id: str,
    body: AskRequest,
    mode: str = Query("clean", pattern="^(raw|clean)$", description="Analyze raw or cleaned facts"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = get_owned_document(db, document_id, user)
    return answer_question(db, doc, body.question, mode)
