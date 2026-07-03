"""Extraction orchestration.

Runs table → text → section extractors over a document's parsed pages,
dedupes, derives a few metrics (e.g. gross margin), detects report identity,
and persists :class:`ExtractedFact` rows.
"""
from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.extraction.base import FactDraft
from app.extraction.section_extractor import extract_signals
from app.extraction.table_extractor import extract_from_tables
from app.extraction.text_extractor import extract_from_text
from app.models.document import Document, DocumentStatus, ReportType
from app.models.fact import ExtractedFact, FactCategory


def _detect_report_type(text: str) -> ReportType:
    low = text.lower()
    if any(k in text for k in ("年度报告", "年报")) or "annual report" in low:
        return ReportType.ANNUAL
    if any(k in text for k in ("半年度", "中期报告", "半年报", "中报")) or "interim" in low or "half-year" in low:
        return ReportType.INTERIM
    if any(k in text for k in ("季度报告", "季报")) or re.search(r"\bq[1-4]\b", low) or "quarterly" in low:
        return ReportType.QUARTERLY
    if "招股" in text or "prospectus" in low:
        return ReportType.PROSPECTUS
    return ReportType.OTHER


def _detect_period(text: str) -> str | None:
    m = re.search(r"(20\d{2})\s*年度?", text)
    if m:
        return f"{m.group(1)} FY"
    m = re.search(r"(20\d{2})\s*年\s*第?\s*([一二三四1-4])\s*季", text)
    if m:
        return f"{m.group(1)} Q{m.group(2)}"
    m = re.search(r"\bFY\s?20\d{2}\b", text, re.IGNORECASE)
    if m:
        return m.group(0).upper()
    m = re.search(r"\b(20\d{2})\b", text)
    return f"{m.group(1)}" if m else None


def _derive_gross_margin(by_concept: dict[str, FactDraft]) -> FactDraft | None:
    gp = by_concept.get("gross_profit")
    rev = by_concept.get("revenue")
    if gp and rev and rev.metric_value and gp.metric_value is not None and "gross_margin" not in by_concept:
        margin = round(gp.metric_value / rev.metric_value * 100, 2)
        if 0 < margin <= 100:
            return FactDraft(
                category=FactCategory.INCOME_STATEMENT,
                concept_id="gross_margin",
                metric_name="Gross Margin",
                metric_label="毛利率",
                raw_label="derived: gross profit / revenue",
                language=gp.language,
                metric_value=margin,
                value_text=f"{margin}%",
                unit="%",
                source_page_number=gp.source_page_number,
                report_section="Derived",
                source_text_snippet=gp.source_text_snippet,
                source_bbox=gp.source_bbox,
                confidence_score=0.55,
                extraction_method="derived",
            )
    return None


def extract_document(db: Session, document: Document) -> int:
    """Extract facts for a fully-parsed document. Returns fact count."""
    document.status = DocumentStatus.EXTRACTING
    db.add(document)
    db.commit()

    from app.normalization.dictionary import get_term_matcher

    matcher = get_term_matcher()

    # Clear any previous extraction (idempotent re-run).
    for old in list(document.facts):
        db.delete(old)
    db.flush()

    # Best numeric draft per (concept_id, page).
    best: dict[tuple, FactDraft] = {}
    signal_drafts: list[FactDraft] = []
    signal_counts: dict[FactCategory, int] = {}
    front_text = ""

    # Concepts already captured from *tables* (high trust) anywhere in the doc.
    # Narrative extraction skips these to avoid re-reporting growth-rate/year
    # mentions (e.g. "净利润同比增长 68.4%") as if they were the metric value.
    table_concepts: set[str] = set()

    for page in document.pages:
        words = json.loads(page.words_json or "[]")
        tables = json.loads(page.tables_json or "[]")
        if page.page_number <= 3:
            front_text += "\n" + page.text

        table_drafts = extract_from_tables(page.page_number, page.text, tables, matcher)
        for d in table_drafts:
            if d.concept_id:
                table_concepts.add(d.concept_id)
            key = (d.concept_id, d.source_page_number)
            if key not in best or d.confidence_score > best[key].confidence_score:
                best[key] = d

        text_drafts = extract_from_text(page.page_number, page.text, words, matcher, set(table_concepts))
        for d in text_drafts:
            key = (d.concept_id, d.source_page_number)
            if key not in best or d.confidence_score > best[key].confidence_score:
                best[key] = d

        signal_drafts.extend(extract_signals(page.page_number, page.text, words, signal_counts))

    # Derive gross margin from the best revenue/gross-profit if absent.
    top_by_concept: dict[str, FactDraft] = {}
    for d in best.values():
        if d.concept_id and (
            d.concept_id not in top_by_concept
            or d.confidence_score > top_by_concept[d.concept_id].confidence_score
        ):
            top_by_concept[d.concept_id] = d
    derived = _derive_gross_margin(top_by_concept)

    drafts: list[FactDraft] = list(best.values()) + signal_drafts
    if derived:
        drafts.append(derived)

    # Fallback: apply the document's dominant currency unit to currency facts on
    # pages that didn't restate the unit header (e.g. a cash-flow-only page).
    from collections import Counter

    currency_units = Counter(
        d.unit for d in drafts if d.unit and d.unit != "%" and d.metric_value is not None
    )
    if currency_units:
        dominant_unit = currency_units.most_common(1)[0][0]
        currency_categories = {
            FactCategory.INCOME_STATEMENT,
            FactCategory.BALANCE_SHEET,
            FactCategory.CASH_FLOW,
        }
        for d in drafts:
            if (
                d.unit is None
                and d.metric_value is not None
                and d.category in currency_categories
                and d.concept_id != "eps"
            ):
                d.unit = dominant_unit

    # Update report identity from front matter.
    if not document.report_period:
        document.report_period = _detect_period(front_text or document.filename)
    if document.report_type == ReportType.OTHER:
        document.report_type = _detect_report_type(front_text or document.filename)

    # Persist.
    for d in drafts:
        db.add(
            ExtractedFact(
                document_id=document.id,
                company_name=document.company_name,
                report_type=document.report_type.value,
                report_period=document.report_period,
                category=d.category,
                concept_id=d.concept_id,
                metric_name=d.metric_name,
                metric_label=d.metric_label,
                raw_label=d.raw_label,
                metric_value=d.metric_value,
                value_text=d.value_text,
                unit=d.unit,
                language=d.language,
                source_page_number=d.source_page_number,
                report_section=d.report_section,
                source_text_snippet=d.source_text_snippet,
                source_bbox_json=json.dumps(d.source_bbox) if d.source_bbox else None,
                source_table_cell_reference=d.source_table_cell_reference,
                confidence_score=d.confidence_score,
                extraction_method=d.extraction_method,
                version_id="v1",
            )
        )

    document.status = DocumentStatus.READY
    document.status_detail = f"Extracted {len(drafts)} facts"
    db.commit()
    return len(drafts)
