"""Forecast orchestration for a single document.

Pulls the document's facts, runs the (non-destructive) cleaning pass to get a
clean input set, derives each metric's current+prior values, projects the next
period under three scenarios, and assembles a fully source-referenced response.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.analysis import document_facts, normalize_mode
from app.api.serializers import fact_to_out
from app.cleaning.rules import normalize_unit
from app.forecasting.assumptions import EXTERNAL_NOTE, external_assumptions
from app.forecasting.engine import MetricInput, parse_prior_from_snippet, project_metric
from app.forecasting.periods import annualization_factor, cadence_label, next_period_label
from app.models.document import Document
from app.models.fact import ExtractedFact, FactCategory
from app.models.schemas import (
    ForecastMetric,
    ForecastResponse,
    ScenarioForecast,
    SummaryHighlight,
)

# Core metrics we forecast, in reading order. Others are ignored to keep the
# output focused on the stock-research signal.
FORECAST_CONCEPTS = [
    "revenue",
    "gross_margin",
    "operating_profit",
    "net_profit",
    "operating_cash_flow",
    "debt",
]
_PERCENT_CONCEPTS = {"gross_margin"}

DISCLAIMER = (
    "Scenario-based analytical estimates derived from this report's own figures "
    "using simple trend heuristics — not guaranteed predictions or investment advice."
)


def _best_by_concept(facts: list[ExtractedFact]) -> dict[str, ExtractedFact]:
    best: dict[str, ExtractedFact] = {}
    for f in facts:
        if not f.concept_id or f.metric_value is None:
            continue
        cur = best.get(f.concept_id)
        if cur is None or f.confidence_score > cur.confidence_score:
            best[f.concept_id] = f
    return best


def _highlights(facts: list[ExtractedFact], category: FactCategory, limit: int) -> list[SummaryHighlight]:
    out: list[SummaryHighlight] = []
    for f in facts:
        if f.category == category and (f.value_text or f.source_text_snippet):
            out.append(
                SummaryHighlight(
                    text=(f.value_text or f.source_text_snippet or "")[:280],
                    fact_id=f.id,
                    source=fact_to_out(f).source,
                )
            )
        if len(out) >= limit:
            break
    return out


def forecast_document(
    db: Session,
    document: Document,
    growth_override_pct: float | None = None,
    value_delta_pp: float | None = None,
    margin_delta_pp: float | None = None,
    mode: str = "clean",
) -> ForecastResponse:
    mode = normalize_mode(mode)
    pool = document_facts(db, document, mode)
    best = _best_by_concept(pool)

    factor = annualization_factor(document.report_type)
    forecast_period = next_period_label(document.report_period, document.report_type)

    kwargs = {}
    if value_delta_pp is not None:
        kwargs["value_delta_pp"] = value_delta_pp
    if margin_delta_pp is not None:
        kwargs["margin_delta_pp"] = margin_delta_pp

    metrics: list[ForecastMetric] = []
    for cid in FORECAST_CONCEPTS:
        fact = best.get(cid)
        if fact is None:
            continue
        is_percent = cid in _PERCENT_CONCEPTS or (normalize_unit(fact.unit) == "%")
        prior = parse_prior_from_snippet(fact.source_text_snippet, fact.metric_value, is_percent)
        if is_percent:
            observed = round(fact.metric_value - prior, 2) if prior is not None else None
        elif prior and prior > 0 and fact.metric_value > 0:
            observed = round((fact.metric_value / prior - 1) * 100, 2)
        else:
            observed = None

        m = MetricInput(
            concept_id=cid,
            metric_name=fact.metric_name,
            metric_label=fact.metric_label,
            unit=normalize_unit(fact.unit),
            current_value=fact.metric_value,
            prior_value=prior,
            is_percent=is_percent,
            source_confidence=fact.confidence_score,
        )
        scenarios = project_metric(m, growth_override_pct=growth_override_pct, **kwargs)

        out_scenarios: list[ScenarioForecast] = []
        for s in scenarios:
            annualized = (
                round(s.predicted_value * factor, 4)
                if (factor > 1 and not is_percent)
                else None
            )
            out_scenarios.append(
                ScenarioForecast(
                    scenario=s.scenario,
                    period=forecast_period,
                    predicted_value=s.predicted_value,
                    annualized_value=annualized,
                    growth_pct=s.growth_pct,
                    direction=s.direction,
                    confidence=s.confidence,
                    assumptions=s.assumptions,
                    explanation=s.explanation,
                )
            )

        metrics.append(
            ForecastMetric(
                concept_id=cid,
                metric_name=fact.metric_name,
                metric_label=fact.metric_label,
                unit=m.unit,
                is_percent=is_percent,
                current_value=fact.metric_value,
                prior_value=prior,
                observed_growth_pct=observed,
                source=fact_to_out(fact).source,
                scenarios=out_scenarios,
            )
        )

    return ForecastResponse(
        document_id=document.id,
        company_name=document.company_name,
        report_type=document.report_type.value,
        mode=mode,
        base_period=document.report_period,
        forecast_period=forecast_period,
        cadence=cadence_label(document.report_type),
        annualized=factor > 1,
        growth_override_pct=growth_override_pct,
        disclaimer=DISCLAIMER,
        metrics=metrics,
        guidance=_highlights(pool, FactCategory.GUIDANCE, 5),
        key_risks=_highlights(pool, FactCategory.RISK, 5),
        external_assumptions=external_assumptions(),
        external_note=EXTERNAL_NOTE,
    )
