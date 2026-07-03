"""Terminology normalization layer.

Maps the many ways a financial line item is written — in Chinese *and*
English — onto a single internal :class:`Concept`. This is what lets the rest
of the app treat "营业收入", "营收", "Revenue", and "Total revenue" as one thing.
"""

from app.normalization.concepts import (
    CONCEPTS,
    Concept,
    concept_by_id,
    iter_concepts,
)
from app.normalization.dictionary import TermMatcher, get_term_matcher

__all__ = [
    "CONCEPTS",
    "Concept",
    "concept_by_id",
    "iter_concepts",
    "TermMatcher",
    "get_term_matcher",
]
