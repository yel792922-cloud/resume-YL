"""Data models — defined first, as the foundation every layer builds on.

ORM entities (persistence) live alongside the domain enums. Pydantic API
schemas live in ``schemas.py``. The central entity is :class:`ExtractedFact`,
which carries full source traceability for every extracted value.
"""

from app.models.document import Document, DocumentStatus, Page, ReportType
from app.models.fact import ExtractedFact, FactCategory

__all__ = [
    "Document",
    "DocumentStatus",
    "Page",
    "ReportType",
    "ExtractedFact",
    "FactCategory",
]
