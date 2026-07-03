"""Financial extraction layer.

Rule-based, bilingual extractors that turn parsed pages into
:class:`ExtractedFact` rows — each with a value *and* full source
traceability. Deterministic rules keep every extraction auditable.
"""

from app.extraction.pipeline import extract_document

__all__ = ["extract_document"]
