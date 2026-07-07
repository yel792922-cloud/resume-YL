"""Extract financial metrics from parsed tables — the highest-trust source.

For each table row we match the label column to a concept and take the first
numeric column as the current-period value. Every fact records the exact table
cell reference and an approximate cell bounding box for click-to-jump.

Segment and geography breakdown tables (common for multi-business
conglomerates) are handled specially: their rows rarely match a core concept
alias, so we capture each line under a ``segment_revenue`` / ``geographic_revenue``
concept and keep the printed line label as the scope, instead of dropping the
breakdown entirely.
"""
from __future__ import annotations

import re

from app.extraction.base import FactDraft
from app.extraction.value_parser import (
    detect_unit_header,
    looks_numeric,
    parse_number,
)
from app.models.fact import FactCategory
from app.normalization.dictionary import TermMatcher, detect_language
from app.sourcemap.highlight import bbox_from_cell

# Table-kind cues (bilingual), matched against the table's header/label column.
_SEGMENT_TABLE = re.compile(r"分部|分业务|分業務|业务分部|業務分部|segment", re.I)
_GEO_TABLE = re.compile(r"分地区|分地區|分区域|分區域|地区|地區|区域|區域|geograph|region", re.I)

# Header / total labels that are not real breakdown line items.
_SKIP_LABELS = re.compile(
    r"^(项目|項目|item|分部|分業務|分业务|segment|地区|地區|region|"
    r"合计|合計|小计|小計|total|subtotal|单位|單位|unit|note|附注)",
    re.I,
)


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


def _classify_table(rows: list[list]) -> str:
    """Return 'segment' | 'geography' | 'statement' from the table's labels.

    Looks at the header row and the label column so a table titled '分部
    Segment' or 'Revenue by region' is recognised as a breakdown table.
    """
    header = " ".join(str(c) for c in (rows[0] if rows else []) if c)
    labels = " ".join(_row_label(r)[0] for r in rows[:6])
    text = f"{header} {labels}"
    if _SEGMENT_TABLE.search(text):
        return "segment"
    if _GEO_TABLE.search(text):
        return "geography"
    return "statement"


_BREAKDOWN_META = {
    "segment": ("segment_revenue", "Segment Revenue", "分部收入", "Segment Revenue"),
    "geography": ("geographic_revenue", "Geographic Revenue", "分地区收入", "Geographic Revenue"),
}


def _extract_breakdown_rows(
    kind: str,
    page_number: int,
    t_index: int,
    table: dict,
    rows: list[list],
    page_unit_hint: str | None,
) -> list[FactDraft]:
    """Capture every data row of a segment/geography table as one scoped fact."""
    concept_id, metric_en, metric_zh, section = _BREAKDOWN_META[kind]
    drafts: list[FactDraft] = []
    for r_index, row in enumerate(rows):
        if not row:
            continue
        label, label_idx = _row_label(row)
        if not label or _SKIP_LABELS.match(label.strip()):
            continue
        value_cell = _first_value_cell(row, label_idx)
        if value_cell is None:
            continue
        col_index, cell_text = value_cell
        parsed = parse_number(cell_text, unit_hint=page_unit_hint)
        if parsed is None:
            continue
        snippet = " | ".join(str(c).strip() for c in row if c and str(c).strip())
        drafts.append(
            FactDraft(
                category=FactCategory.BUSINESS,
                concept_id=concept_id,
                metric_name=metric_en,
                metric_label=metric_zh,
                raw_label=label,            # the segment / region name = the scope
                language=detect_language(label),
                metric_value=parsed.value,
                value_text=parsed.raw,
                unit=parsed.unit,
                source_page_number=page_number,
                report_section=section,
                source_text_snippet=snippet[:400],
                source_bbox=bbox_from_cell(table, r_index, col_index),
                source_table_cell_reference=f"table={t_index};row={r_index};col={col_index}",
                confidence_score=0.8,
                extraction_method="table",
            )
        )
    return drafts


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

        # Segment / geography breakdown tables: capture every line item as a
        # scoped business fact instead of trying (and failing) to map each
        # business name onto a core statement concept.
        kind = _classify_table(rows)
        if kind in _BREAKDOWN_META:
            drafts.extend(
                _extract_breakdown_rows(kind, page_number, t_index, table, rows, page_unit_hint)
            )
            continue

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
