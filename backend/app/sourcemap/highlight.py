"""Resolve highlight bounding boxes from a page's positioned words.

Coordinates in and out are normalized 0..1. All functions accept plain word
dicts (``{text, x0, top, x1, bottom}``) as persisted on :class:`Page`.
"""
from __future__ import annotations

import re

Word = dict
BBox = list[float]

_STRIP = re.compile(r"[\s　,，。.::;；%()（）\-—]+")


def _norm(s: str) -> str:
    return _STRIP.sub("", s.lower())


def union_bbox(words: list[Word]) -> BBox | None:
    """Smallest box covering all ``words``."""
    boxed = [w for w in words if all(k in w for k in ("x0", "top", "x1", "bottom"))]
    if not boxed:
        return None
    return [
        min(w["x0"] for w in boxed),
        min(w["top"] for w in boxed),
        max(w["x1"] for w in boxed),
        max(w["bottom"] for w in boxed),
    ]


def _tokens(snippet: str) -> list[str]:
    # Split on whitespace; for CJK (no spaces) fall back to per-char tokens.
    parts = snippet.split()
    if len(parts) <= 1 and any("一" <= ch <= "鿿" for ch in snippet):
        return [ch for ch in snippet if not _STRIP.match(ch)]
    return parts


def locate_snippet(words: list[Word], snippet: str, max_words: int = 40) -> BBox | None:
    """Find the run of page words whose concatenation contains ``snippet``.

    Returns the union bbox of the matching run, or ``None`` if not found.
    """
    target = _norm(snippet)
    if not target:
        return None

    normed = [_norm(w.get("text", "")) for w in words]

    # Sliding window: grow a run until it contains the target, then shrink.
    for start in range(len(words)):
        acc = ""
        for end in range(start, min(start + max_words, len(words))):
            acc += normed[end]
            if not acc:
                continue
            if target in acc:
                return union_bbox(words[start : end + 1])
            if len(acc) > len(target) + 24:  # window overshot; move start
                break
    return None


def locate_terms(words: list[Word], query: str) -> list[BBox]:
    """Locate every occurrence of ``query`` on the page (for search highlight)."""
    boxes: list[BBox] = []
    target = _norm(query)
    if not target:
        return boxes
    normed = [_norm(w.get("text", "")) for w in words]
    for start in range(len(words)):
        acc = ""
        for end in range(start, min(start + 30, len(words))):
            acc += normed[end]
            if target in acc:
                box = union_bbox(words[start : end + 1])
                if box:
                    boxes.append(box)
                break
            if len(acc) > len(target) + 24:
                break
    return boxes


def bbox_from_cell(table: dict, row: int, col: int) -> BBox | None:
    """Approximate a cell's bbox from the table bbox by even row/col slicing.

    pdfplumber gives us the table's outer bbox and its row grid; without the
    per-cell geometry we approximate uniformly. Good enough to scroll-and-flash
    the right region; exact cell geometry can refine this later.
    """
    bbox = table.get("bbox")
    rows = table.get("rows") or []
    if not bbox or not rows:
        return None
    n_rows = len(rows)
    n_cols = max((len(r) for r in rows), default=1)
    if n_rows == 0 or n_cols == 0:
        return None
    x0, top, x1, bottom = bbox
    cell_w = (x1 - x0) / n_cols
    cell_h = (bottom - top) / n_rows
    cx0 = x0 + cell_w * max(0, min(col, n_cols - 1))
    cy0 = top + cell_h * max(0, min(row, n_rows - 1))
    return [cx0, cy0, cx0 + cell_w, cy0 + cell_h]
