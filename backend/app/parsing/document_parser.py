"""Parse orchestration: digital first, OCR fallback for scanned pages."""
from __future__ import annotations

from app.normalization.dictionary import detect_language
from app.parsing.base import ParsedDocument
from app.parsing.ocr import get_ocr_backend
from app.parsing.pdf_parser import parse_digital

# If more than this share of pages need OCR, call the whole document scanned.
_SCANNED_DOC_THRESHOLD = 0.5


def parse_pdf(path: str) -> ParsedDocument:
    """Parse a PDF into a :class:`ParsedDocument` with source traceability."""
    pages, needs_ocr = parse_digital(path)

    is_scanned = bool(pages) and (len(needs_ocr) / len(pages)) >= _SCANNED_DOC_THRESHOLD

    if needs_ocr:
        backend = get_ocr_backend()
        if backend.available():
            index = {p.page_number: i for i, p in enumerate(pages)}
            for page_number in needs_ocr:
                ocr_page = backend.ocr_page(path, page_number)
                pages[index[page_number]] = ocr_page

    language = detect_language(" ".join(p.text for p in pages[:5]))
    return ParsedDocument(pages=pages, is_scanned=is_scanned, language=language)
