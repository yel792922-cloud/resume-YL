"""v3 analysis routes: cleaned facts and scenario forecasts (owner-scoped).

Both are additive, read-only, and computed on demand — they don't change any
existing endpoint or persist anything new.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.ownership import get_owned_document
from app.api.serializers import fact_to_out
from app.auth.deps import get_current_user
from app.cleaning import active_rule_ids, clean_facts
from app.core.db import get_db
from app.forecasting import forecast_document
from app.models.fact import ExtractedFact
from app.models.schemas import (
    CleanedFactsResponse,
    CleaningAuditEntry,
    ForecastResponse,
)
from app.models.user import User

router = APIRouter(prefix="/api/documents", tags=["analysis"])


@router.get("/{document_id}/cleaned", response_model=CleanedFactsResponse)
def get_cleaned_facts(
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the cleaned, de-duplicated, unit-normalized facts plus an audit
    trail of what was filtered/normalized and why. Non-destructive."""
    doc = get_owned_document(db, document_id, user)
    facts = db.query(ExtractedFact).filter(ExtractedFact.document_id == doc.id).all()
    result = clean_facts(facts)

    retained = [
        fact_to_out(f).model_copy(update={"unit": result.unit_for(f)}) for f in result.retained
    ]
    audit = [CleaningAuditEntry(**vars(a)) for a in result.audit]
    return CleanedFactsResponse(
        document_id=doc.id, stats=result.stats, rules=active_rule_ids(),
        retained=retained, audit=audit,
    )


@router.get("/{document_id}/forecast", response_model=ForecastResponse)
def get_forecast(
    document_id: str,
    growth_override_pct: float | None = Query(
        None, ge=-100, le=1000,
        description="Optional user growth override (%, or pp for margins) applied to the base scenario",
    ),
    value_delta_pp: float | None = Query(None, ge=0, le=200, description="Bull/bear spread for value metrics (growth pp)"),
    margin_delta_pp: float | None = Query(None, ge=0, le=100, description="Bull/bear spread for margin metrics (pp)"),
    mode: str = Query("clean", pattern="^(raw|clean)$", description="Forecast from raw or cleaned facts"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Period-aware base/bull/bear forecast for the report. Ephemeral."""
    doc = get_owned_document(db, document_id, user)
    return forecast_document(
        db, doc,
        growth_override_pct=growth_override_pct,
        value_delta_pp=value_delta_pp,
        margin_delta_pp=margin_delta_pp,
        mode=mode,
    )
