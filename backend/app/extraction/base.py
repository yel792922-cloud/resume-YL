"""Shared types for extractors: a draft fact before it is persisted."""
from __future__ import annotations

from dataclasses import dataclass

from app.models.fact import FactCategory


@dataclass
class FactDraft:
    category: FactCategory
    concept_id: str | None
    metric_name: str
    metric_label: str | None
    raw_label: str | None
    language: str

    metric_value: float | None = None
    value_text: str | None = None
    unit: str | None = None

    source_page_number: int | None = None
    report_section: str | None = None
    source_text_snippet: str | None = None
    source_bbox: list[float] | None = None
    source_table_cell_reference: str | None = None

    confidence_score: float = 0.0
    extraction_method: str | None = None

    def dedupe_key(self) -> tuple:
        # One value per concept per page wins (highest confidence).
        return (self.category, self.concept_id, self.source_page_number)
