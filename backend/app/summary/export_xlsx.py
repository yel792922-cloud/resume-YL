"""Structured .xlsx analysis export — spreadsheet-ready, not a PDF dump.

Builds a multi-sheet workbook of the *analysis* (raw facts, cleaned facts,
forecast results, source mapping, optional Q&A evidence, scenario assumptions),
so users can pivot/chart in a spreadsheet. Every fact row keeps its source
page + snippet + confidence, preserving traceability.
"""
from __future__ import annotations

import io

from sqlalchemy.orm import Session

from app.analysis import all_facts, document_facts, normalize_mode
from app.cleaning import clean_facts
from app.cleaning.rules import normalize_unit
from app.forecasting import forecast_document
from app.forecasting.engine import parse_prior_from_snippet
from app.models.document import Document
from app.models.fact import ExtractedFact
from app.normalization.scope import derive_scope
from app.qa import answer_question

_FACT_HEADERS = [
    "company", "report_period", "category", "concept", "metric", "metric_label",
    "scope_type", "scope_label",
    "value", "value_text", "unit", "yoy_qoq", "source_page", "report_section",
    "source_snippet", "table_cell", "cleaning_status", "confidence", "extraction_method",
]


def _is_percent(f: ExtractedFact) -> bool:
    return f.unit == "%" or f.concept_id == "gross_margin"


def _yoy_qoq(f: ExtractedFact) -> str:
    """Period-over-period change recovered from the fact's own row snippet."""
    if f.metric_value is None:
        return ""
    is_pct = _is_percent(f)
    prior = parse_prior_from_snippet(f.source_text_snippet, f.metric_value, is_pct)
    if prior is None:
        return ""
    if is_pct:
        return f"{f.metric_value - prior:+.1f}pp"
    if prior > 0 and f.metric_value > 0:
        return f"{(f.metric_value / prior - 1) * 100:+.1f}%"
    return ""


def _cleaning_status_map(facts: list[ExtractedFact]) -> dict[int, str]:
    cr = clean_facts(facts)
    retained = {f.id for f in cr.retained}
    normalized = {a.fact_id for a in cr.audit if a.action == "normalized"}
    status: dict[int, str] = {}
    for f in facts:
        status[f.id] = "retained (unit normalized)" if (f.id in retained and f.id in normalized) else (
            "retained" if f.id in retained else "filtered"
        )
    for a in cr.audit:
        if a.action == "removed":
            status[a.fact_id] = f"removed: {a.reason}"
        elif a.action == "deduped":
            status[a.fact_id] = "removed: duplicate"
    return status


def _fact_row(f: ExtractedFact, cleaning_status: str, unit: str | None) -> list:
    scope = derive_scope(f.category, f.concept_id, f.raw_label, f.report_section)
    return [
        f.company_name, f.report_period, f.category.value, f.concept_id,
        f.metric_name, f.metric_label, scope.scope_type, scope.scope_label,
        f.metric_value, f.value_text, unit,
        _yoy_qoq(f), f.source_page_number, f.report_section,
        (f.source_text_snippet or "")[:500], f.source_table_cell_reference,
        cleaning_status, round(f.confidence_score, 3), f.extraction_method,
    ]


def build_workbook(db: Session, document: Document, mode: str = "clean", question: str | None = None) -> bytes:
    from openpyxl import Workbook

    mode = normalize_mode(mode)
    wb = Workbook()
    wb.remove(wb.active)

    def sheet(title: str, headers: list[str], rows: list[list]) -> None:
        ws = wb.create_sheet(title[:31])
        ws.append(headers)
        for r in rows:
            ws.append(r)
        ws.freeze_panes = "A2"

    raw = all_facts(db, document)
    status = _cleaning_status_map(raw)

    # 1) Raw facts — everything extracted, with cleaning verdict per row.
    sheet("Raw Facts", _FACT_HEADERS, [_fact_row(f, status.get(f.id, ""), f.unit) for f in raw])

    # 2) Cleaned facts — retained/normalized subset (normalized unit shown).
    cr = clean_facts(raw)
    sheet("Cleaned Facts", _FACT_HEADERS,
          [_fact_row(f, status.get(f.id, "retained"), cr.unit_for(f)) for f in cr.retained])

    # 3) Forecast results (respects the chosen mode).
    fc = forecast_document(db, document, mode=mode)
    fc_headers = ["company", "concept", "metric", "current", "base", "base_growth",
                  "bull", "bull_growth", "bear", "bear_growth", "confidence_base",
                  "source_page", "forecast_period", "mode"]
    fc_rows = []
    for m in fc.metrics:
        by = {s.scenario: s for s in m.scenarios}
        b, u, r = by.get("base"), by.get("bull"), by.get("bear")
        fc_rows.append([
            fc.company_name, m.concept_id, m.metric_name, m.current_value,
            b.predicted_value if b else None, b.growth_pct if b else None,
            u.predicted_value if u else None, u.growth_pct if u else None,
            r.predicted_value if r else None, r.growth_pct if r else None,
            b.confidence if b else None,
            m.source.page_number if m.source else None, fc.forecast_period, fc.mode,
        ])
    sheet("Forecast", fc_headers, fc_rows)

    # 4) Source mapping — the traceability index.
    sm_headers = ["metric", "concept", "source_page", "report_section", "table_cell", "source_bbox", "source_snippet"]
    sm_rows = [
        [f.metric_name, f.concept_id, f.source_page_number, f.report_section,
         f.source_table_cell_reference, f.source_bbox_json, (f.source_text_snippet or "")[:500]]
        for f in raw if f.source_page_number is not None
    ]
    sheet("Source Mapping", sm_headers, sm_rows)

    # 5) Scenario assumptions (external drivers — assumptions, not facts).
    sa_rows = [[sa.scenario, factor] for sa in fc.external_assumptions for factor in sa.external_factors]
    sheet("Scenario Assumptions", ["scenario", "external_factor (assumption, not a report fact)"], sa_rows)

    # 6) Q&A evidence — only when a question is supplied.
    if question and question.strip():
        ans = answer_question(db, document, question, mode)
        rows = [["QUESTION", question, "", ""], ["ANSWER", ans.answer, f"confidence={ans.confidence}", ""], ["", "", "", ""]]
        for e in ans.evidence:
            rows.append([e.kind, e.text, e.source.page_number if e.source else None,
                         (e.source.snippet or "")[:300] if e.source else ""])
        sheet("QA Evidence", ["kind", "text", "source_page", "source_snippet"], rows)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
