"""Term matching: map a printed label (CN or EN) onto a canonical concept.

The matcher is intentionally simple and deterministic (no ML): it normalizes
whitespace/punctuation and prefers the *longest, highest-priority* alias that
the label contains. Deterministic matching keeps extraction auditable — a core
requirement for a trustworthy, source-first product.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from app.normalization.concepts import CONCEPTS, Concept

_PUNCT = re.compile(r"[\s　:：·\-—()（）\[\]【】,，。\.]+")
_CJK = re.compile(r"[一-鿿]")


def _norm(text: str) -> str:
    return _PUNCT.sub("", text.strip().lower())


def detect_language(text: str) -> str:
    """Rough language detection for a snippet: zh / en / mixed."""
    cjk = len(_CJK.findall(text))
    latin = len(re.findall(r"[a-zA-Z]", text))
    if cjk and latin:
        # If both present, decide by dominant script.
        return "zh" if cjk >= latin else "en"
    if cjk:
        return "zh"
    if latin:
        return "en"
    return "unknown"


@dataclass(frozen=True)
class TermHit:
    concept: Concept
    matched_alias: str
    language: str


class TermMatcher:
    """Precomputed index of (normalized alias -> concept)."""

    def __init__(self, concepts: tuple[Concept, ...]) -> None:
        # alias_norm -> (concept, language, raw_alias)
        self._index: dict[str, tuple[Concept, str, str]] = {}
        for concept in concepts:
            for label, lang in concept.all_labels:
                key = _norm(label)
                if not key:
                    continue
                existing = self._index.get(key)
                if existing is None or concept.priority > existing[0].priority:
                    self._index[key] = (concept, lang, label)
        # Sort aliases by length (desc) so longest match wins on `find_in`.
        self._aliases_by_len: list[str] = sorted(
            self._index.keys(), key=len, reverse=True
        )

    def match_label(self, label: str) -> TermHit | None:
        """Exact (normalized) match for a whole label string."""
        hit = self._index.get(_norm(label))
        if hit is None:
            return None
        concept, lang, raw = hit
        return TermHit(concept, raw, lang)

    def find_in(self, label: str) -> TermHit | None:
        """Find the best concept whose alias is contained in ``label``.

        Used for row labels that carry extra decoration, e.g.
        "营业收入（其中：主营业务）" or "Total net revenues (note 3)".
        """
        norm = _norm(label)
        if not norm:
            return None
        exact = self._index.get(norm)
        if exact is not None:
            concept, lang, raw = exact
            return TermHit(concept, raw, lang)
        for alias_norm in self._aliases_by_len:
            if alias_norm in norm:
                concept, lang, raw = self._index[alias_norm]
                return TermHit(concept, raw, lang)
        return None


@lru_cache
def get_term_matcher() -> TermMatcher:
    return TermMatcher(CONCEPTS)
