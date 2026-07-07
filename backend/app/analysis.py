"""Analysis mode — the single switch that puts data cleaning at the front.

Downstream analytics (Q&A, forecasting, comparison, export) all draw their fact
pool through :func:`document_facts`, so a user can analyze either the original
extraction (``raw``) or the cleaned/normalized version (``clean``) consistently.

Keeping this in one place means "raw vs clean" behaves identically everywhere.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.cleaning import clean_facts
from app.cleaning.rules import CleaningConfig
from app.models.document import Document
from app.models.fact import ExtractedFact
from app.profile import profile_from_json

# Accepted modes. Kept as plain strings so routes can validate with a pattern.
RAW = "raw"
CLEAN = "clean"
MODES = (RAW, CLEAN)


def normalize_mode(mode: str | None) -> str:
    return mode if mode in MODES else CLEAN


def all_facts(db: Session, document: Document) -> list[ExtractedFact]:
    return (
        db.query(ExtractedFact)
        .filter(ExtractedFact.document_id == document.id)
        .order_by(ExtractedFact.category, ExtractedFact.confidence_score.desc())
        .all()
    )


def cleaning_config_for(document: Document) -> CleaningConfig:
    """Pick a cleaning policy from the document's report profile.

    Complex / multi-business reports use "preserve" (keep repeated labels from
    different tables apart); simple single-business reports use "standard".
    """
    profile = profile_from_json(getattr(document, "profile_json", None))
    complex_report = bool(profile) and (
        profile.complexity == "complex"
        or profile.business_structure in ("multi", "conglomerate")
    )
    return CleaningConfig(merge_strength="preserve" if complex_report else "standard")


def document_facts(db: Session, document: Document, mode: str = CLEAN) -> list[ExtractedFact]:
    """Return the fact pool for the chosen mode.

    ``raw``   → every extracted fact, untouched.
    ``clean`` → the non-destructive cleaning pass's retained facts, using a
                profile-aware merge strength.
    """
    facts = all_facts(db, document)
    if normalize_mode(mode) == RAW:
        return facts
    return clean_facts(facts, cleaning_config_for(document)).retained
