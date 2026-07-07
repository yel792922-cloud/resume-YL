"""Export extracted facts with their full source traceability (CSV / JSON)."""
from __future__ import annotations

import csv
import io
import json

from app.models.fact import ExtractedFact
from app.normalization.scope import derive_scope

# Column order mirrors the spec's per-fact data model. scope_type / scope_label
# are appended so a spreadsheet can tell same-named metrics apart by scope.
_COLUMNS = [
    "company_name", "report_type", "report_period", "category", "concept_id",
    "metric_name", "metric_label", "raw_label", "scope_type", "scope_label",
    "metric_value", "value_text",
    "unit", "language", "source_page_number", "report_section",
    "source_text_snippet", "source_bbox", "source_table_cell_reference",
    "confidence_score", "extraction_method", "extraction_timestamp", "version_id",
]


def _row(f: ExtractedFact) -> dict:
    scope = derive_scope(f.category, f.concept_id, f.raw_label, f.report_section)
    return {
        "company_name": f.company_name,
        "report_type": f.report_type,
        "report_period": f.report_period,
        "category": f.category.value,
        "concept_id": f.concept_id,
        "metric_name": f.metric_name,
        "metric_label": f.metric_label,
        "raw_label": f.raw_label,
        "scope_type": scope.scope_type,
        "scope_label": scope.scope_label,
        "metric_value": f.metric_value,
        "value_text": f.value_text,
        "unit": f.unit,
        "language": f.language,
        "source_page_number": f.source_page_number,
        "report_section": f.report_section,
        "source_text_snippet": f.source_text_snippet,
        "source_bbox": f.source_bbox_json,
        "source_table_cell_reference": f.source_table_cell_reference,
        "confidence_score": f.confidence_score,
        "extraction_method": f.extraction_method,
        "extraction_timestamp": f.extraction_timestamp.isoformat() if f.extraction_timestamp else None,
        "version_id": f.version_id,
    }


def facts_to_csv(facts: list[ExtractedFact]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_COLUMNS)
    writer.writeheader()
    for f in facts:
        writer.writerow(_row(f))
    return buf.getvalue()


def facts_to_json(facts: list[ExtractedFact]) -> str:
    return json.dumps([_row(f) for f in facts], ensure_ascii=False, indent=2)
