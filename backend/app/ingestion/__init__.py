"""Document ingestion layer: store uploads, register documents, run parsing."""

from app.ingestion.ingest import ingest_document, ingest_from_path
from app.ingestion.storage import save_upload

__all__ = ["ingest_document", "ingest_from_path", "save_upload"]
