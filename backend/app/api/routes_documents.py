"""Document routes: upload, seed sample, list, detail, pages, facts, summary."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.serializers import document_to_summary, fact_to_out, page_to_out
from app.core.config import get_settings
from app.core.db import get_db
from app.extraction import extract_document
from app.ingestion import ingest_from_path
from app.ingestion.storage import copy_into_store, new_document_id, save_upload
from app.models.document import Document, DocumentStatus
from app.models.fact import ExtractedFact, FactCategory
from app.models.schemas import DocumentDetail, DocumentSummary, FactOut, PageOut, ReportSummary
from app.sample.sample_report import SAMPLE_COMPANY, SAMPLE_PERIOD, build_sample_pdf
from app.summary import build_summary

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _get_doc_or_404(db: Session, document_id: str) -> Document:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("", response_model=list[DocumentSummary])
def list_documents(favorites_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(Document).order_by(Document.created_at.desc())
    if favorites_only:
        q = q.filter(Document.is_favorite.is_(True))
    return [document_to_summary(db, d) for d in q.all()]


@router.post("/upload", response_model=DocumentSummary)
async def upload_document(
    file: UploadFile = File(...),
    company_name: str | None = Form(None),
    report_period: str | None = Form(None),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    document_id = new_document_id()
    _, storage_path = save_upload(file.file, file.filename, document_id)

    doc = ingest_from_path(
        db, document_id, storage_path, file.filename,
        company_name=company_name, report_period=report_period,
    )
    try:
        extract_document(db, doc)
    except Exception as exc:  # extraction failures shouldn't lose the upload
        doc.status = DocumentStatus.FAILED
        doc.status_detail = f"extraction error: {exc}"
        db.commit()
    return document_to_summary(db, doc)


@router.post("/seed", response_model=DocumentSummary)
def seed_sample(db: Session = Depends(get_db)):
    """Ingest the built-in bilingual sample report for instant exploration."""
    settings = get_settings()
    document_id = new_document_id()
    sample_path = settings.data_dir / "sample_report.pdf"
    build_sample_pdf(sample_path)
    _, storage_path = copy_into_store(str(sample_path), "sample_annual_report.pdf", document_id)

    doc = ingest_from_path(
        db, document_id, storage_path, "sample_annual_report.pdf",
        company_name=SAMPLE_COMPANY, report_period=SAMPLE_PERIOD,
    )
    extract_document(db, doc)
    return document_to_summary(db, doc)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, document_id)
    summary = document_to_summary(db, doc)
    return DocumentDetail(**summary.model_dump(), pages=[p.page_number for p in doc.pages])


@router.delete("/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, document_id)
    db.delete(doc)
    db.commit()
    return {"deleted": document_id}


@router.post("/{document_id}/favorite", response_model=DocumentSummary)
def toggle_favorite(document_id: str, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, document_id)
    doc.is_favorite = not doc.is_favorite
    db.commit()
    return document_to_summary(db, doc)


@router.post("/{document_id}/reextract", response_model=DocumentSummary)
def reextract(document_id: str, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, document_id)
    extract_document(db, doc)
    return document_to_summary(db, doc)


@router.get("/{document_id}/facts", response_model=list[FactOut])
def get_facts(document_id: str, category: FactCategory | None = None, db: Session = Depends(get_db)):
    _get_doc_or_404(db, document_id)
    q = db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id)
    if category:
        q = q.filter(ExtractedFact.category == category)
    facts = q.order_by(ExtractedFact.confidence_score.desc()).all()
    return [fact_to_out(f) for f in facts]


@router.get("/{document_id}/pages/{page_number}", response_model=PageOut)
def get_page(document_id: str, page_number: int, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, document_id)
    page = next((p for p in doc.pages if p.page_number == page_number), None)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return page_to_out(page)


@router.get("/{document_id}/summary", response_model=ReportSummary)
def get_summary(document_id: str, db: Session = Depends(get_db)):
    doc = _get_doc_or_404(db, document_id)
    return build_summary(db, doc)
