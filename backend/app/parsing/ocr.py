"""Pluggable OCR backend for scanned pages.

OCR pulls in heavy native dependencies (tesseract, poppler), so it is
**optional**. The rest of the app depends only on the :class:`OcrBackend`
protocol; if no backend is available we degrade gracefully — scanned pages are
kept as empty pages and the document is flagged ``is_scanned`` so the UI can
tell the user OCR is unavailable, rather than crashing.

To enable: ``pip install -e '.[ocr]'`` and install the tesseract binary with
Chinese + English language packs (``chi_sim``, ``eng``).
"""
from __future__ import annotations

from typing import Protocol

from app.core.config import get_settings
from app.parsing.base import ParsedPage, ParsedWord


class OcrBackend(Protocol):
    def available(self) -> bool: ...

    def ocr_page(self, pdf_path: str, page_number: int) -> ParsedPage: ...


class TesseractOcrBackend:
    """OCR via pytesseract + pdf2image. Imports are lazy and guarded."""

    def __init__(self) -> None:
        self._settings = get_settings()

    def available(self) -> bool:
        try:
            import pytesseract  # noqa: F401
            from pdf2image import convert_from_path  # noqa: F401
        except Exception:
            return False
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def ocr_page(self, pdf_path: str, page_number: int) -> ParsedPage:
        import pytesseract
        from pdf2image import convert_from_path

        settings = self._settings
        images = convert_from_path(
            pdf_path, dpi=settings.ocr_dpi, first_page=page_number, last_page=page_number
        )
        if not images:
            return ParsedPage(page_number, 1.0, 1.0, "", source="ocr")
        image = images[0]
        width, height = image.size

        data = pytesseract.image_to_data(
            image, lang=settings.ocr_languages, output_type=pytesseract.Output.DICT
        )
        words: list[ParsedWord] = []
        parts: list[str] = []
        n = len(data["text"])
        for i in range(n):
            token = (data["text"][i] or "").strip()
            if not token:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            words.append(
                ParsedWord(
                    text=token,
                    x0=x / width,
                    top=y / height,
                    x1=(x + w) / width,
                    bottom=(y + h) / height,
                )
            )
            parts.append(token)
        return ParsedPage(
            page_number=page_number,
            width=float(width),
            height=float(height),
            text=" ".join(parts),
            words=words,
            source="ocr",
        )


class NullOcrBackend:
    """Used when OCR is disabled or unavailable."""

    def available(self) -> bool:
        return False

    def ocr_page(self, pdf_path: str, page_number: int) -> ParsedPage:
        return ParsedPage(page_number, 1.0, 1.0, "", source="ocr")


def get_ocr_backend() -> OcrBackend:
    settings = get_settings()
    if settings.enable_ocr:
        backend = TesseractOcrBackend()
        if backend.available():
            return backend
    return NullOcrBackend()
