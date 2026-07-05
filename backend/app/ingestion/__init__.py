"""Document ingestion layer: store uploads, register documents, run parsing."""

from app.ingestion.ingest import ingest_document, ingest_from_path
from app.ingestion.preprocess import (
    PreprocessResult,
    UploadTooLargeError,
    check_upload_size,
    preprocess_pdf,
)
from app.ingestion.storage import save_upload

__all__ = [
    "ingest_document",
    "ingest_from_path",
    "save_upload",
    "preprocess_pdf",
    "check_upload_size",
    "UploadTooLargeError",
    "PreprocessResult",
]
