"""Search & comparison layer: in-report search and cross-report comparison."""

from app.search.compare import compare_documents
from app.search.search import search_document

__all__ = ["search_document", "compare_documents"]
