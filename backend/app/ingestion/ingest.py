"""Ingest orchestration: parse a stored PDF and persist its pages.

Extraction is run separately (see :mod:`app.extraction.pipeline`) so parsing
and extraction stay decoupled and independently re-runnable.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus, Page
from app.parsing import parse_pdf


def persist_parsed_document(db: Session, document: Document) -> Document:
    """Parse ``document.storage_path`` and write its pages to the DB."""
    document.status = DocumentStatus.PARSING
    db.add(document)
    db.commit()

    try:
        parsed = parse_pdf(document.storage_path)
    except Exception as exc:  # keep the record; surface the failure
        document.status = DocumentStatus.FAILED
        document.status_detail = f"parse error: {exc}"
        db.commit()
        raise

    # Replace any previous pages (re-ingest is idempotent).
    for old in list(document.pages):
        db.delete(old)
    db.flush()

    for p in parsed.pages:
        db.add(
            Page(
                document_id=document.id,
                page_number=p.page_number,
                width=p.width,
                height=p.height,
                text=p.text,
                source=p.source,
                words_json=json.dumps([w.as_dict() for w in p.words], ensure_ascii=False),
                tables_json=json.dumps([t.as_dict() for t in p.tables], ensure_ascii=False),
            )
        )

    document.page_count = parsed.page_count
    document.is_scanned = parsed.is_scanned
    if document.language in (None, "unknown"):
        document.language = parsed.language
    document.status = DocumentStatus.EXTRACTING
    db.commit()
    db.refresh(document)
    return document


def ingest_document(db: Session, document: Document) -> Document:
    """Full ingest for an already-registered document row."""
    return persist_parsed_document(db, document)


def ingest_from_path(
    db: Session,
    document_id: str,
    storage_path: str,
    filename: str,
    company_name: str | None = None,
    report_period: str | None = None,
) -> Document:
    """Register + ingest a file already present in the store."""
    document = Document(
        id=document_id,
        filename=filename,
        storage_path=storage_path,
        company_name=company_name,
        report_period=report_period,
        status=DocumentStatus.UPLOADED,
    )
    db.add(document)
    db.commit()
    return persist_parsed_document(db, document)
