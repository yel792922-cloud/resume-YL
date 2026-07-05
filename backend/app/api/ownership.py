"""Shared ownership guard used by all document-scoped routes."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.user import User


def get_owned_document(db: Session, document_id: str, user: User) -> Document:
    """Return the document only if it belongs to ``user``; else 404.

    We return 404 (not 403) for someone else's document so the API never
    reveals that a given document id exists.
    """
    doc = db.get(Document, document_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
