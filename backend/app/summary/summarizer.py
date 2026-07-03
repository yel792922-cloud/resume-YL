"""Evidence-linked report summary.

The summary is deliberately **extractive**: every headline metric and highlight
links to a real fact and its source location. No number appears that can't be
clicked back to the original report — the product's core trust guarantee.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.fact import ExtractedFact, FactCategory
from app.models.schemas import ReportSummary, SourceRef, SummaryHighlight
from app.search.search import _fact_to_out

_HEADLINE_ORDER = ["revenue", "net_profit", "gross_margin", "operating_cash_flow", "eps", "total_assets"]


def _best_by_concept(facts: list[ExtractedFact]) -> dict[str, ExtractedFact]:
    best: dict[str, ExtractedFact] = {}
    for f in facts:
        if not f.concept_id:
            continue
        cur = best.get(f.concept_id)
        if cur is None or f.confidence_score > cur.confidence_score:
            best[f.concept_id] = f
    return best


def _fmt(f: ExtractedFact) -> str:
    val = f.value_text or (f"{f.metric_value:g}" if f.metric_value is not None else "—")
    unit = "" if (f.unit in (None, "%") or (f.value_text and f.unit and f.unit in f.value_text)) else f" {f.unit}"
    label = f.metric_label or f.metric_name
    return f"{label} {val}{unit}".strip()


def build_summary(db: Session, document: Document) -> ReportSummary:
    facts = db.query(ExtractedFact).filter(ExtractedFact.document_id == document.id).all()
    best = _best_by_concept(facts)

    headline = [
        _fact_to_out(best[cid]) for cid in _HEADLINE_ORDER if cid in best
    ]

    highlights: list[SummaryHighlight] = []
    for cid in _HEADLINE_ORDER:
        f = best.get(cid)
        if not f:
            continue
        highlights.append(
            SummaryHighlight(
                text=_fmt(f),
                fact_id=f.id,
                source=SourceRef(
                    page_number=f.source_page_number,
                    section=f.report_section,
                    snippet=f.source_text_snippet,
                    bbox=(_fact_to_out(f).source.bbox),
                    table_cell=f.source_table_cell_reference,
                ),
            )
        )

    # Management/guidance lines add qualitative color, still source-linked.
    for f in facts:
        if f.category in (FactCategory.GUIDANCE, FactCategory.MANAGEMENT) and len(highlights) < 10:
            highlights.append(
                SummaryHighlight(
                    text=f.value_text or "",
                    fact_id=f.id,
                    source=SourceRef(page_number=f.source_page_number, section=f.report_section, snippet=f.source_text_snippet),
                )
            )

    risks = [
        SummaryHighlight(
            text=f.value_text or "",
            fact_id=f.id,
            source=SourceRef(page_number=f.source_page_number, section=f.report_section, snippet=f.source_text_snippet),
        )
        for f in facts
        if f.category == FactCategory.RISK
    ][:8]

    return ReportSummary(
        document_id=document.id,
        company_name=document.company_name,
        report_period=document.report_period,
        headline_metrics=headline,
        highlights=highlights,
        risks=risks,
    )
