"""Document routes: upload, seed, list, detail, pages, facts, summary, history.

All routes require authentication and are scoped to the current user — a user
can only see and act on their own documents.
"""
from __future__ import annotations

import io
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.ownership import get_owned_document as _get_owned_doc_or_404
from app.api.serializers import document_to_summary, fact_to_out, page_to_out
from app.auth.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.extraction import extract_document
from app.history import create_snapshot, get_snapshot, list_snapshots
from app.ingestion import (
    UploadTooLargeError,
    check_upload_size,
    ingest_from_path,
    preprocess_pdf,
    save_upload,
)
from app.ingestion.storage import copy_into_store, new_document_id
from app.models.document import Document, DocumentStatus
from app.models.fact import ExtractedFact, FactCategory
from app.models.schemas import (
    DocumentDetail,
    DocumentSummary,
    FactOut,
    PageOut,
    ReportSummary,
    SnapshotDetail,
    SnapshotSummary,
)
from app.models.user import User
from app.sample.sample_report import SAMPLE_COMPANY, SAMPLE_PERIOD, build_sample_pdf
from app.storage import delete_raw_file, enforce_retention
from app.summary import build_summary

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _finalize_extraction(db: Session, doc: Document, user_id: int) -> None:
    """Snapshot the parse run and enforce per-user raw-file retention."""
    create_snapshot(db, doc)
    enforce_retention(db, user_id)


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    favorites_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Document).filter(Document.user_id == user.id).order_by(Document.created_at.desc())
    if favorites_only:
        q = q.filter(Document.is_favorite.is_(True))
    return [document_to_summary(db, d) for d in q.all()]


@router.post("/upload", response_model=DocumentSummary)
async def upload_document(
    file: UploadFile = File(...),
    company_name: str | None = Form(None),
    report_period: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Hard size check *before* persisting, with a clear user-facing message.
    contents = await file.read()
    try:
        check_upload_size(len(contents))
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    document_id = new_document_id()
    _, storage_path = save_upload(io.BytesIO(contents), file.filename, document_id)

    # Optional compression for large/image-heavy PDFs (safe, falls back).
    preprocess_pdf(storage_path)

    doc = ingest_from_path(
        db, document_id, storage_path, file.filename, user_id=user.id,
        company_name=company_name, report_period=report_period,
    )
    try:
        extract_document(db, doc)
        _finalize_extraction(db, doc, user.id)
    except Exception as exc:  # extraction failures shouldn't lose the upload
        doc.status = DocumentStatus.FAILED
        doc.status_detail = f"extraction error: {exc}"
        db.commit()
    return document_to_summary(db, doc)


@router.post("/seed", response_model=DocumentSummary)
def seed_sample(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Ingest the built-in bilingual sample report for the current user."""
    settings = get_settings()
    document_id = new_document_id()
    sample_path = settings.data_dir / "sample_report.pdf"
    build_sample_pdf(sample_path)
    _, storage_path = copy_into_store(str(sample_path), "sample_annual_report.pdf", document_id)

    doc = ingest_from_path(
        db, document_id, storage_path, "sample_annual_report.pdf", user_id=user.id,
        company_name=SAMPLE_COMPANY, report_period=SAMPLE_PERIOD,
    )
    extract_document(db, doc)
    _finalize_extraction(db, doc, user.id)
    return document_to_summary(db, doc)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_owned_doc_or_404(db, document_id, user)
    summary = document_to_summary(db, doc)
    return DocumentDetail(**summary.model_dump(), pages=[p.page_number for p in doc.pages])


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_owned_doc_or_404(db, document_id, user)
    delete_raw_file(doc)  # remove the raw PDF from disk before dropping the row
    db.delete(doc)
    db.commit()
    return {"deleted": document_id}


@router.post("/{document_id}/favorite", response_model=DocumentSummary)
def toggle_favorite(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_owned_doc_or_404(db, document_id, user)
    doc.is_favorite = not doc.is_favorite
    db.commit()
    return document_to_summary(db, doc)


@router.post("/{document_id}/reextract", response_model=DocumentSummary)
def reextract(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_owned_doc_or_404(db, document_id, user)
    extract_document(db, doc)
    create_snapshot(db, doc, note="manual re-extract")
    return document_to_summary(db, doc)


@router.get("/{document_id}/facts", response_model=list[FactOut])
def get_facts(
    document_id: str,
    category: FactCategory | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_doc_or_404(db, document_id, user)
    q = db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id)
    if category:
        q = q.filter(ExtractedFact.category == category)
    facts = q.order_by(ExtractedFact.confidence_score.desc()).all()
    return [fact_to_out(f) for f in facts]


@router.get("/{document_id}/pages/{page_number}", response_model=PageOut)
def get_page(
    document_id: str,
    page_number: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = _get_owned_doc_or_404(db, document_id, user)
    page = next((p for p in doc.pages if p.page_number == page_number), None)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page_to_out(page)


@router.get("/{document_id}/summary", response_model=ReportSummary)
def get_summary(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get_owned_doc_or_404(db, document_id, user)
    return build_summary(db, doc)


# ---------------------------- Parse history ----------------------------
@router.get("/{document_id}/history", response_model=list[SnapshotSummary])
def get_history(document_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _get_owned_doc_or_404(db, document_id, user)
    return [SnapshotSummary.model_validate(s) for s in list_snapshots(db, document_id)]


@router.get("/{document_id}/history/{version}", response_model=SnapshotDetail)
def get_history_version(
    document_id: str,
    version: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_doc_or_404(db, document_id, user)
    snap = get_snapshot(db, document_id, version)
    if snap is None:
        raise HTTPException(status_code=404, detail="Snapshot version not found")
    base = SnapshotSummary.model_validate(snap).model_dump()
    return SnapshotDetail(
        **base,
        facts=[FactOut(**f) for f in json.loads(snap.facts_json)],
        summary=ReportSummary(**json.loads(snap.summary_json)),
    )
