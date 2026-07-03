"""OCR & parsing layer.

Turns a PDF into structured :class:`ParsedPage` objects carrying positioned
words and tables (normalized 0..1 coordinates), regardless of whether the
source is a digital or scanned PDF.
"""

from app.parsing.base import ParsedDocument, ParsedPage, ParsedTable, ParsedWord
from app.parsing.document_parser import parse_pdf

__all__ = [
    "ParsedDocument",
    "ParsedPage",
    "ParsedTable",
    "ParsedWord",
    "parse_pdf",
]
