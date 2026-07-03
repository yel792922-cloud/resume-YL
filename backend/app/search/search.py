"""In-report search across both extracted facts and raw page text.

Every hit carries a source reference (page + snippet + bbox) so results are as
traceable as everything else in the product.
"""
from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.models.document import Document, Page
from app.models.fact import ExtractedFact
from app.models.schemas import FactOut, SearchHit, SearchResponse, SourceRef
from app.normalization.dictionary import get_term_matcher
from app.sourcemap.highlight import locate_terms

_SNIPPET_RADIUS = 60


def _fact_to_out(f: ExtractedFact) -> FactOut:
    bbox = json.loads(f.source_bbox_json) if f.source_bbox_json else None
    return FactOut(
        id=f.id,
        document_id=f.document_id,
        category=f.category,
        concept_id=f.concept_id,
        metric_name=f.metric_name,
        metric_label=f.metric_label,
        raw_label=f.raw_label,
        metric_value=f.metric_value,
        value_text=f.value_text,
        unit=f.unit,
        language=f.language,
        report_period=f.report_period,
        confidence_score=f.confidence_score,
        extraction_method=f.extraction_method,
        version_id=f.version_id,
        source=SourceRef(
            page_number=f.source_page_number,
            section=f.report_section,
            snippet=f.source_text_snippet,
            bbox=bbox,
            table_cell=f.source_table_cell_reference,
        ),
    )


def _expand_query(query: str) -> list[str]:
    """Expand the query with concept aliases so CN search finds EN facts & vice-versa."""
    terms = {query.strip().lower()}
    matcher = get_term_matcher()
    hit = matcher.find_in(query)
    if hit:
        for label, _lang in hit.concept.all_labels:
            terms.add(label.lower())
    return [t for t in terms if t]


def search_document(db: Session, document: Document, query: str, limit: int = 50) -> SearchResponse:
    query = (query or "").strip()
    if not query:
        return SearchResponse(query=query, total=0, hits=[])

    terms = _expand_query(query)
    hits: list[SearchHit] = []

    # 1) Fact matches (highest value for a research tool).
    facts = db.query(ExtractedFact).filter(ExtractedFact.document_id == document.id).all()
    for f in facts:
        haystack = " ".join(
            x for x in (f.metric_name, f.metric_label, f.raw_label, f.value_text, f.source_text_snippet) if x
        ).lower()
        if any(t in haystack for t in terms):
            out = _fact_to_out(f)
            hits.append(
                SearchHit(
                    kind="fact",
                    page_number=f.source_page_number,
                    section=f.report_section,
                    snippet=f.source_text_snippet or f"{f.metric_name}: {f.value_text or f.metric_value}",
                    bbox=out.source.bbox,
                    fact=out,
                    score=f.confidence_score + 1.0,  # rank facts above raw text
                )
            )

    # 2) Raw text matches with in-page highlight boxes.
    pages = db.query(Page).filter(Page.document_id == document.id).all()
    for page in pages:
        low = page.text.lower()
        for term in terms:
            for m in re.finditer(re.escape(term), low):
                start = max(0, m.start() - _SNIPPET_RADIUS)
                end = min(len(page.text), m.end() + _SNIPPET_RADIUS)
                snippet = page.text[start:end].replace("\n", " ").strip()
                words = json.loads(page.words_json or "[]")
                boxes = locate_terms(words, term)
                bbox = boxes[0] if boxes else None
                hits.append(
                    SearchHit(
                        kind="text",
                        page_number=page.page_number,
                        section=None,
                        snippet=snippet,
                        bbox=bbox,
                        score=0.5,
                    )
                )
                break  # one hit per term per page keeps results tidy

    hits.sort(key=lambda h: h.score, reverse=True)
    return SearchResponse(query=query, total=len(hits), hits=hits[:limit])
