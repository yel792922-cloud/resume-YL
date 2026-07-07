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
from app.forecasting.engine import (
    MetricInput,
    parse_prior_from_snippet,
    project_custom,
    project_metric,
)
from app.forecasting.factors import (
    contributions,
    external_growth_adjustment_pp,
    factor_catalog,
    normalize_weights,
)
from app.forecasting.periods import (
    annualization_factor,
    cadence_label,
    next_period_label,
)
from app.models.document import Document
from app.models.fact import ExtractedFact, FactCategory
from app.models.schemas import (
    FactorImpact,
    ForecastFactor,
    ForecastMetric,
    ForecastResponse,
    ImpactDriver,
    ImpactSummary,
    PolicyEmphasis,
    ScenarioForecast,
    SummaryHighlight,
)
from app.profile import policy_for, profile_from_json

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
    factor_weights: dict | None = None,
    custom_notes: str | None = None,
) -> ForecastResponse:
    mode = normalize_mode(mode)
    pool = document_facts(db, document, mode)
    best = _best_by_concept(pool)

    # Active analysis policy from the report profile — shapes the forecast emphasis
    # and the suggested Custom-scenario factor weights (suggestions, not applied).
    policy = policy_for(profile_from_json(getattr(document, "profile_json", None)))

    factor = annualization_factor(document.report_type)
    forecast_period = next_period_label(document.report_period, document.report_type)

    # Configurable external factors → an explainable Custom-scenario tilt.
    weights = normalize_weights(factor_weights)
    external_pp = external_growth_adjustment_pp(weights)
    factor_contribs = contributions(weights)
    has_custom = bool(weights) or custom_notes or growth_override_pct is not None

    kwargs = {}
    if value_delta_pp is not None:
        kwargs["value_delta_pp"] = value_delta_pp
    if margin_delta_pp is not None:
        kwargs["margin_delta_pp"] = margin_delta_pp

    metrics: list[ForecastMetric] = []
    drivers: list[tuple[str, float, bool]] = []  # (metric_name, observed, is_percent)
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
        scenarios = list(project_metric(m, growth_override_pct=growth_override_pct, **kwargs))
        # Custom scenario: base trend (or user override) + weighted factors.
        if has_custom:
            scenarios.append(project_custom(m, growth_override_pct, external_pp))

        out_scenarios: list[ScenarioForecast] = []
        for s in scenarios:
            # Annualized value is an OPTIONAL companion view — the primary
            # predicted_value already follows the report's own cadence (next
            # quarter/half/year); we never replace it with an annualized figure.
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

        if observed is not None:
            drivers.append((fact.metric_name, observed, is_percent))

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

    impact = _impact_summary(drivers, factor_contribs, external_pp, has_custom, custom_notes)

    return ForecastResponse(
        document_id=document.id,
        company_name=document.company_name,
        report_type=document.report_type.value,
        mode=mode,
        base_period=document.report_period,
        forecast_period=forecast_period,
        cadence=cadence_label(document.report_type),
        annualized=factor > 1,
        annualized_note=(
            f"Optional view: ×{factor} annualization of the {cadence_label(document.report_type)} "
            "forecast, shown alongside — not instead of — the period figure."
            if factor > 1 else None
        ),
        growth_override_pct=growth_override_pct,
        disclaimer=DISCLAIMER,
        metrics=metrics,
        guidance=_highlights(pool, FactCategory.GUIDANCE, 5),
        key_risks=_highlights(pool, FactCategory.RISK, 5),
        external_assumptions=external_assumptions(),
        external_note=EXTERNAL_NOTE,
        factors=[ForecastFactor(id=f.id, label_en=f.label_en, label_zh=f.label_zh) for f in factor_catalog()],
        factor_weights=weights,
        custom_notes=custom_notes,
        impact_summary=impact,
        policy_emphasis=PolicyEmphasis(
            preferred_metric_families=policy.preferred_metric_families,
            suggested_factor_weights=policy.forecast_driver_weights,
            note=(policy.notes[-1] if policy.notes else None),
        ),
    )


def _impact_summary(
    drivers: list[tuple[str, float, bool]],
    factor_contribs,
    external_pp: float,
    has_custom: bool,
    custom_notes: str | None,
) -> ImpactSummary:
    """Explain the forecast: strongest internal metric moves + external factors."""
    # Internal drivers — rank the report's own metrics by absolute observed change.
    ranked = sorted(drivers, key=lambda d: abs(d[1]), reverse=True)
    internal: list[ImpactDriver] = []
    for name, observed, is_percent in ranked[:4]:
        unit = "pp" if is_percent else "%"
        verb = "rose" if observed > 0 else ("fell" if observed < 0 else "was flat")
        internal.append(
            ImpactDriver(
                label=name,
                detail=f"{name} {verb} {observed:+.1f}{unit} vs the prior period, driving its projection.",
                magnitude_pp=observed,
            )
        )

    external = [
        FactorImpact(
            id=c.id, label_en=c.label_en, label_zh=c.label_zh,
            weight=c.weight, contribution_pp=c.contribution_pp,
        )
        for c in factor_contribs
    ]

    top_metric = ranked[0][0] if ranked else None
    parts: list[str] = []
    if top_metric:
        parts.append(f"Projection is anchored on {top_metric}'s observed trend")
    if has_custom and external:
        top = external[0]
        parts.append(
            f"external factors add {external_pp:+.1f}pp of growth "
            f"(largest: {top.label_en} {top.contribution_pp:+.1f}pp)"
        )
    elif has_custom:
        parts.append("no external factor weights applied (Custom uses your growth override only)")
    headline = "; ".join(parts) + "." if parts else "Base/bull/bear scenarios follow the report's own trend."

    return ImpactSummary(
        headline=headline,
        internal_drivers=internal,
        external_drivers=external,
        notes=custom_notes,
    )
