"""Per-user raw-PDF retention.

Keeps only the newest ``FRA_MAX_UPLOADS_PER_USER`` original files per user.
Older raw PDFs are deleted from disk and their ``storage_path`` cleared, but the
Document row and all structured data (pages, facts, snapshots) stay intact — so
the report remains fully analyzable and source-traceable (the source view is
reconstructed from stored word coordinates, not the PDF).
"""
from __future__ import annotations

import os

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document


def _unlink_quietly(path: str | None) -> None:
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        # Never let cleanup failures break the request; the DB flag is the
        # source of truth for whether the raw file is considered available.
        pass


def delete_raw_file(document: Document) -> None:
    """Remove a single document's raw PDF and mark it unavailable."""
    _unlink_quietly(document.storage_path)
    document.storage_path = None
    document.raw_available = False


def enforce_retention(db: Session, user_id: int, keep: int | None = None) -> list[str]:
    """Trim a user's raw uploads to the newest ``keep`` files.

    Returns the ids of documents whose raw file was removed. Structured parse
    data is never deleted here.
    """
    settings = get_settings()
    keep = settings.max_uploads_per_user if keep is None else keep
    if keep < 0:
        return []

    with_raw = (
        db.query(Document)
        .filter(Document.user_id == user_id, Document.raw_available.is_(True))
        .order_by(Document.created_at.desc())
        .all()
    )

    removed: list[str] = []
    for doc in with_raw[keep:]:
        delete_raw_file(doc)
        removed.append(doc.id)

    if removed:
        db.commit()
    return removed
