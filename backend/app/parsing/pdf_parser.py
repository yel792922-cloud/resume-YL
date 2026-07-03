"""Digital-PDF parser built on pdfplumber.

Extracts, per page: full text, positioned words (normalized bbox), and tables.
A page with almost no extractable text is flagged as *likely scanned* so the
orchestrator can route it through OCR instead.
"""
from __future__ import annotations

import pdfplumber

from app.parsing.base import ParsedPage, ParsedTable, ParsedWord

# Below this many characters, a page is treated as image-only (needs OCR).
_MIN_CHARS_FOR_DIGITAL = 12


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def parse_page(page, page_number: int) -> tuple[ParsedPage, bool]:
    """Parse one pdfplumber page. Returns (page, likely_scanned)."""
    width = float(page.width or 1.0)
    height = float(page.height or 1.0)

    text = page.extract_text() or ""

    words: list[ParsedWord] = []
    for w in page.extract_words(use_text_flow=True, keep_blank_chars=False):
        words.append(
            ParsedWord(
                text=w["text"],
                x0=_clamp01(w["x0"] / width),
                top=_clamp01(w["top"] / height),
                x1=_clamp01(w["x1"] / width),
                bottom=_clamp01(w["bottom"] / height),
            )
        )

    tables: list[ParsedTable] = []
    try:
        found = page.find_tables()
    except Exception:  # pdfplumber can raise on odd geometry
        found = []
    for t in found:
        try:
            rows = t.extract()
        except Exception:
            continue
        if not rows:
            continue
        x0, top, x1, bottom = t.bbox
        tables.append(
            ParsedTable(
                bbox=[_clamp01(x0 / width), _clamp01(top / height), _clamp01(x1 / width), _clamp01(bottom / height)],
                rows=[[(c if c is None else str(c)) for c in row] for row in rows],
            )
        )

    parsed = ParsedPage(
        page_number=page_number,
        width=width,
        height=height,
        text=text,
        words=words,
        tables=tables,
        source="digital",
    )
    likely_scanned = parsed.char_count < _MIN_CHARS_FOR_DIGITAL
    return parsed, likely_scanned


def parse_digital(path: str) -> tuple[list[ParsedPage], list[int]]:
    """Parse every page. Returns (pages, page_numbers_needing_ocr)."""
    pages: list[ParsedPage] = []
    needs_ocr: list[int] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            parsed, scanned = parse_page(page, i)
            pages.append(parsed)
            if scanned:
                needs_ocr.append(i)
    return pages, needs_ocr
