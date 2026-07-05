"""The cleaning pass: retain high-value facts, drop noise, dedup, normalize.

Pure and non-destructive — it reads a list of :class:`ExtractedFact` and returns
the retained subset plus an audit trail. It never mutates the ORM objects or the
database, so it is safe to call from read-only endpoints and from forecasting.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.cleaning.rules import (
    CleaningConfig,
    is_boilerplate,
    looks_like_ocr_garbage,
    normalize_unit,
    _informative_char_count,
)
from app.models.fact import ExtractedFact, FactCategory

_NUMERIC_CATEGORIES = {
    FactCategory.INCOME_STATEMENT,
    FactCategory.BALANCE_SHEET,
    FactCategory.CASH_FLOW,
    FactCategory.BUSINESS,
}
_QUALITATIVE_CATEGORIES = {
    FactCategory.RISK,
    FactCategory.MANAGEMENT,
    FactCategory.GUIDANCE,
}
_WS = re.compile(r"\s+")


@dataclass
class AuditEntry:
    action: str                 # "removed" | "deduped" | "normalized"
    reason: str
    fact_id: int | None = None
    concept_id: str | None = None
    metric_name: str | None = None
    snippet: str | None = None
    detail: str | None = None
    confidence: float | None = None


@dataclass
class CleanResult:
    retained: list[ExtractedFact]
    audit: list[AuditEntry] = field(default_factory=list)
    # normalized unit per retained fact id (applied at serialization; the ORM
    # objects themselves are never mutated).
    normalized_units: dict[int, str] = field(default_factory=dict)

    @property
    def stats(self) -> dict[str, int]:
        counts = {"retained": len(self.retained), "removed": 0, "deduped": 0, "normalized": 0}
        for a in self.audit:
            counts[a.action] = counts.get(a.action, 0) + 1
        return counts

    def unit_for(self, fact: ExtractedFact) -> str | None:
        """The (possibly normalized) unit to display for a retained fact."""
        return self.normalized_units.get(fact.id, fact.unit)


def _is_numeric(fact: ExtractedFact) -> bool:
    return fact.concept_id is not None and fact.metric_value is not None


def _norm_text(s: str | None) -> str:
    return _WS.sub(" ", (s or "").strip().lower())[:160]


def clean_facts(facts: list[ExtractedFact], config: CleaningConfig | None = None) -> CleanResult:
    cfg = config or CleaningConfig()
    audit: list[AuditEntry] = []

    def _audit(action: str, reason: str, f: ExtractedFact, detail: str | None = None) -> None:
        audit.append(
            AuditEntry(
                action=action,
                reason=reason,
                fact_id=f.id,
                concept_id=f.concept_id,
                metric_name=f.metric_name,
                snippet=(f.source_text_snippet or f.value_text or "")[:160] or None,
                detail=detail,
                confidence=f.confidence_score,
            )
        )

    # --- Pass 1: drop low-value noise (never touches numeric concept facts
    # except a hard confidence floor). ---
    kept: list[ExtractedFact] = []
    for f in facts:
        if _is_numeric(f):
            if f.confidence_score < cfg.min_numeric_confidence:
                _audit("removed", "numeric fact below confidence floor", f)
                continue
            kept.append(f)
            continue

        # Qualitative / non-concept facts: filter obvious noise.
        snippet = f.source_text_snippet or f.value_text or ""
        if cfg.enable_boilerplate_filter and is_boilerplate(snippet):
            _audit("removed", "boilerplate / header / page-number", f)
            continue
        if looks_like_ocr_garbage(snippet):
            _audit("removed", "likely OCR garbage", f)
            continue
        if _informative_char_count(snippet) < cfg.min_informative_word_chars:
            _audit("removed", "low-information row", f)
            continue
        kept.append(f)

    # --- Pass 2: de-duplicate (keep the highest-confidence instance per key). ---
    if cfg.enable_dedup:
        groups: dict[tuple, list[ExtractedFact]] = {}
        for f in kept:
            groups.setdefault(_dedupe_key(f), []).append(f)
        winners: set[int] = set()
        for members in groups.values():
            winner = max(members, key=lambda x: x.confidence_score)
            winners.add(id(winner))
            for loser in members:
                if loser is winner:
                    continue
                _audit(
                    "deduped",
                    "duplicate fact",
                    loser,
                    detail=f"kept fact #{winner.id} (higher/equal confidence)",
                )
        retained = [f for f in kept if id(f) in winners]  # preserves original order
    else:
        retained = kept

    # --- Pass 3: unit normalization (recorded; applied at output). ---
    normalized_units: dict[int, str] = {}
    if cfg.enable_unit_normalization:
        for f in retained:
            canon = normalize_unit(f.unit)
            if canon and canon != f.unit:
                normalized_units[f.id] = canon
                _audit("normalized", "unit notation normalized", f, detail=f"{f.unit!r} -> {canon!r}")

    return CleanResult(retained=retained, audit=audit, normalized_units=normalized_units)


def _dedupe_key(f: ExtractedFact) -> tuple:
    if _is_numeric(f):
        return (f.concept_id, round(f.metric_value, 4), normalize_unit(f.unit))
    return (f.category, _norm_text(f.source_text_snippet or f.value_text))
