"""Retrieve and group the report evidence relevant to a question.

Reuses existing primitives: the cleaning pass (prefer cleaned facts), the
bilingual concept layer, and the in-report search. Everything returned still
carries a source reference, so answers stay traceable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.cleaning import clean_facts
from app.models.document import Document
from app.models.fact import ExtractedFact, FactCategory
from app.normalization.concepts import concept_by_id
from app.qa.intent import QuestionIntent
from app.search.search import search_document


@dataclass
class Retrieved:
    pool: list[ExtractedFact]                     # cleaned fact pool
    best_by_concept: dict[str, ExtractedFact]
    concept_facts: list[ExtractedFact]            # facts for the question's concepts
    drivers: list[ExtractedFact]                  # management/guidance explanations
    risks: list[ExtractedFact]
    text_hits: list = field(default_factory=list)  # search hits (fallback/general)


def _best_by_concept(facts: list[ExtractedFact]) -> dict[str, ExtractedFact]:
    best: dict[str, ExtractedFact] = {}
    for f in facts:
        if not f.concept_id or f.metric_value is None:
            continue
        cur = best.get(f.concept_id)
        if cur is None or f.confidence_score > cur.confidence_score:
            best[f.concept_id] = f
    return best


def _category(facts: list[ExtractedFact], category: FactCategory) -> list[ExtractedFact]:
    items = [f for f in facts if f.category == category]
    items.sort(key=lambda f: f.confidence_score, reverse=True)
    return items


def _mentions_concept(fact: ExtractedFact, concept_ids: list[str]) -> bool:
    text = (fact.source_text_snippet or fact.value_text or "").lower()
    if not text:
        return False
    for cid in concept_ids:
        concept = concept_by_id(cid)
        if concept and any(label.lower() in text for label, _lang in concept.all_labels):
            return True
    return False


def gather(db: Session, document: Document, qi: QuestionIntent, question: str) -> Retrieved:
    pool = clean_facts(
        db.query(ExtractedFact).filter(ExtractedFact.document_id == document.id).all()
    ).retained
    best = _best_by_concept(pool)

    concept_facts = [best[c] for c in qi.concepts if c in best]

    management = _category(pool, FactCategory.MANAGEMENT) + _category(pool, FactCategory.GUIDANCE)
    # Prefer management/guidance lines that actually mention the target concept;
    # fall back to the top general commentary when none match.
    if qi.concepts:
        focused = [f for f in management if _mentions_concept(f, qi.concepts)]
        drivers = focused or management[:3]
    else:
        drivers = management[:3]

    risks = _category(pool, FactCategory.RISK)

    text_hits = search_document(db, document, question, limit=6).hits

    return Retrieved(
        pool=pool,
        best_by_concept=best,
        concept_facts=concept_facts,
        drivers=drivers,
        risks=risks,
        text_hits=text_hits,
    )
