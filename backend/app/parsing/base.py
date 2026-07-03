"""Parse-layer data structures shared by the digital and OCR parsers.

All coordinates are **normalized to 0..1** relative to page width/height so the
frontend can render highlights independent of zoom / render resolution.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedWord:
    text: str
    x0: float
    top: float
    x1: float
    bottom: float

    def as_dict(self) -> dict:
        return {"text": self.text, "x0": self.x0, "top": self.top, "x1": self.x1, "bottom": self.bottom}


@dataclass
class ParsedTable:
    # Bounding box of the whole table, normalized.
    bbox: list[float]
    rows: list[list[str | None]]

    def as_dict(self) -> dict:
        return {"bbox": self.bbox, "rows": self.rows}


@dataclass
class ParsedPage:
    page_number: int                 # 1-based
    width: float
    height: float
    text: str
    words: list[ParsedWord] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    source: str = "digital"          # digital | ocr

    @property
    def char_count(self) -> int:
        return len(self.text.strip())


@dataclass
class ParsedDocument:
    pages: list[ParsedPage]
    is_scanned: bool
    language: str = "unknown"

    @property
    def page_count(self) -> int:
        return len(self.pages)
