"""Extract financial metrics from parsed tables — the highest-trust source.

For each table row we match the label column to a concept and take the first
numeric column as the current-period value. Every fact records the exact table
cell reference and an approximate cell bounding box for click-to-jump.
"""
from __future__ import annotations

from app.extraction.base import FactDraft
from app.extraction.value_parser import (
    detect_unit_header,
    looks_numeric,
    parse_number,
)
from app.normalization.dictionary import TermMatcher, detect_language
from app.sourcemap.highlight import bbox_from_cell


def _row_label(row: list) -> tuple[str, int]:
    """Return (label, index of first non-empty label cell)."""
    for i, cell in enumerate(row):
        if cell and str(cell).strip() and not looks_numeric(cell):
            return str(cell).strip(), i
    # Fallback: first non-empty cell.
    for i, cell in enumerate(row):
        if cell and str(cell).strip():
            return str(cell).strip(), i
    return "", 0


def _first_value_cell(row: list, label_idx: int) -> tuple[int, str] | None:
    for j in range(label_idx + 1, len(row)):
        cell = row[j]
        if looks_numeric(cell):
            return j, str(cell).strip()
    return None


def extract_from_tables(
    page_number: int,
    page_text: str,
    tables: list[dict],
    matcher: TermMatcher,
) -> list[FactDraft]:
    drafts: list[FactDraft] = []
    page_unit_hint = detect_unit_header(page_text)

    for t_index, table in enumerate(tables):
        rows = table.get("rows") or []
        for r_index, row in enumerate(rows):
            if not row:
                continue
            label, label_idx = _row_label(row)
            if not label:
                continue
            hit = matcher.find_in(label)
            if hit is None:
                continue
            value_cell = _first_value_cell(row, label_idx)
            if value_cell is None:
                continue
            col_index, cell_text = value_cell

            unit_hint = "%" if hit.concept.unit_hint == "percent" else page_unit_hint
            parsed = parse_number(cell_text, unit_hint=unit_hint)
            if parsed is None:
                continue

            snippet = " | ".join(str(c).strip() for c in row if c and str(c).strip())
            bbox = bbox_from_cell(table, r_index, col_index)
            drafts.append(
                FactDraft(
                    category=hit.concept.category,
                    concept_id=hit.concept.id,
                    metric_name=hit.concept.canonical_en,
                    metric_label=hit.concept.canonical_zh,
                    raw_label=label,
                    language=detect_language(label),
                    metric_value=parsed.value,
                    value_text=parsed.raw,  # clean number, not the raw wrapped cell
                    unit=parsed.unit,
                    source_page_number=page_number,
                    report_section="Financial Statements",
                    source_text_snippet=snippet[:400],
                    source_bbox=bbox,
                    source_table_cell_reference=f"table={t_index};row={r_index};col={col_index}",
                    confidence_score=0.9,
                    extraction_method="table",
                )
            )
    return drafts
