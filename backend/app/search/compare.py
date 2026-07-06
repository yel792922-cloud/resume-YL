"""Cross-report comparison — across periods or across companies.

Builds a metric matrix: rows are concepts, columns are documents (labeled by
period or company). Each cell keeps the full traceable fact so the UI can jump
to the source of any compared number.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.analysis import document_facts
from app.models.document import Document
from app.models.fact import ExtractedFact
from app.models.schemas import CompareCell, CompareResponse, CompareRow
from app.normalization.concepts import concept_by_id, iter_concepts
from app.search.search import _fact_to_out

# Concepts shown in comparison, in a sensible reading order.
_COMPARE_ORDER = [
    "revenue", "gross_profit", "gross_margin", "operating_profit", "net_profit", "eps",
    "operating_cash_flow", "investing_cash_flow", "financing_cash_flow", "free_cash_flow",
    "cash_and_equivalents", "total_assets", "total_liabilities", "current_assets",
    "current_liabilities", "accounts_receivable", "inventory", "debt",
]


def _best_fact_per_concept(db: Session, document: Document, mode: str) -> dict[str, ExtractedFact]:
    facts = document_facts(db, document, mode)
    best: dict[str, ExtractedFact] = {}
    for f in facts:
        if not f.concept_id:
            continue
        cur = best.get(f.concept_id)
        if cur is None or f.confidence_score > cur.confidence_score:
            best[f.concept_id] = f
    return best


def compare_documents(
    db: Session, documents: list[Document], dimension: str = "period", mode: str = "raw"
) -> CompareResponse:
    columns: list[str] = []
    for d in documents:
        if dimension == "company":
            columns.append(d.company_name or d.filename)
        else:
            columns.append(d.report_period or d.filename)

    per_doc = {d.id: _best_fact_per_concept(db, d, mode) for d in documents}

    # Only include concepts present in at least one document, in canonical order.
    present = {cid for facts in per_doc.values() for cid in facts}
    ordered = [cid for cid in _COMPARE_ORDER if cid in present]
    ordered += [c.id for c in iter_concepts() if c.id in present and c.id not in ordered]

    rows: list[CompareRow] = []
    for cid in ordered:
        concept = concept_by_id(cid)
        cells: list[CompareCell] = []
        unit = None
        for d, col in zip(documents, columns):
            fact = per_doc[d.id].get(cid)
            if fact and unit is None:
                unit = fact.unit
            cells.append(
                CompareCell(
                    period=col,
                    document_id=d.id,
                    fact=_fact_to_out(fact) if fact else None,
                )
            )
        rows.append(
            CompareRow(
                concept_id=cid,
                metric_name=concept.canonical_en if concept else cid,
                metric_label=concept.canonical_zh if concept else cid,
                unit=unit,
                cells=cells,
            )
        )

    return CompareResponse(
        dimension=dimension,
        mode=mode,
        columns=columns,
        document_ids=[d.id for d in documents],
        rows=rows,
    )
