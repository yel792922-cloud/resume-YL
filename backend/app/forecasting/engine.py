"""Pure scenario math. No I/O — easy to unit-test and reason about.

Two projection styles:
- value metrics (revenue, profit, cash flow, debt): multiplicative growth.
- margin metrics (percent): additive in percentage points.

Three scenarios: base (continue observed trend), bull (stronger), bear (weaker).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Default scenario spreads. Value metrics shift growth by ±delta (percentage
# points of growth); margins shift by ±pp. Conservative and easy to tune.
DEFAULT_VALUE_DELTA_PP = 5.0
DEFAULT_MARGIN_DELTA_PP = 1.5

_NUM = re.compile(r"[-+(（]?\s*\d[\d,，]*(?:\.\d+)?\s*[%％)）]?")


@dataclass
class MetricInput:
    concept_id: str
    metric_name: str
    metric_label: str | None
    unit: str | None
    current_value: float
    prior_value: float | None
    is_percent: bool
    source_confidence: float = 0.5


@dataclass
class ScenarioResult:
    scenario: str                 # base | bull | bear
    predicted_value: float
    growth_pct: float | None      # applied growth (value metrics) or pp change (margins)
    direction: str                # up | down | flat
    confidence: str               # low | medium | high
    assumptions: list[str]
    explanation: str


def parse_prior_from_snippet(
    snippet: str | None, current_value: float, is_percent: bool
) -> float | None:
    """Recover the prior-period value from a fact's row snippet.

    Statement rows are captured as e.g. "营业收入 Revenue | 6,096.9 | 5,626.5";
    the number after the current value is the prior period. Returns None when a
    plausible prior can't be found.
    """
    if not snippet:
        return None
    nums: list[float] = []
    for tok in _NUM.findall(snippet):
        cleaned = tok.replace(",", "").replace("，", "").replace("%", "").replace("％", "")
        cleaned = cleaned.replace("(", "-").replace("（", "-").replace(")", "").replace("）", "").strip()
        try:
            nums.append(float(cleaned))
        except ValueError:
            continue
    if len(nums) < 2:
        return None
    # Find the current value, then take the next number as the prior period.
    for i, n in enumerate(nums[:-1]):
        if abs(n - current_value) <= max(0.01, abs(current_value) * 0.001):
            prior = nums[i + 1]
            return prior if prior != 0 else None
    return None


def _direction(current: float, predicted: float) -> str:
    if predicted > current * 1.005:
        return "up"
    if predicted < current * 0.995:
        return "down"
    return "flat"


def _notch_down(level: str) -> str:
    return {"high": "medium", "medium": "low", "low": "low"}[level]


def _base_confidence(has_prior: bool, source_confidence: float) -> str:
    if has_prior and source_confidence >= 0.75:
        return "high"
    if has_prior:
        return "medium"
    return "low"


def _clamp_margin(v: float) -> float:
    return max(0.0, min(100.0, round(v, 2)))


def project_metric(
    m: MetricInput,
    growth_override_pct: float | None = None,
    value_delta_pp: float = DEFAULT_VALUE_DELTA_PP,
    margin_delta_pp: float = DEFAULT_MARGIN_DELTA_PP,
) -> list[ScenarioResult]:
    """Project one metric into base/bull/bear scenarios."""
    has_prior = m.prior_value is not None and m.prior_value != 0
    base_level = _base_confidence(has_prior, m.source_confidence)
    results: list[ScenarioResult] = []

    if m.is_percent:
        observed_change = (m.current_value - m.prior_value) if has_prior else 0.0
        base_change = growth_override_pct if growth_override_pct is not None else observed_change
        spreads = {
            "base": base_change,
            "bull": base_change + margin_delta_pp,
            "bear": base_change - margin_delta_pp,
        }
        for name, change in spreads.items():
            predicted = _clamp_margin(m.current_value + change)
            level = base_level if name == "base" else _notch_down(base_level)
            results.append(
                ScenarioResult(
                    scenario=name,
                    predicted_value=predicted,
                    growth_pct=round(change, 2),
                    direction=_direction(m.current_value, predicted),
                    confidence=level,
                    assumptions=_margin_assumptions(name, observed_change, change, has_prior),
                    explanation=(
                        f"{m.metric_name}: {m.current_value:.1f}% → {predicted:.1f}% "
                        f"({change:+.1f}pp)."
                    ),
                )
            )
        return results

    # Value metric (multiplicative growth).
    observed_growth = ((m.current_value / m.prior_value - 1) * 100) if has_prior else None
    base_growth = (
        growth_override_pct
        if growth_override_pct is not None
        else (observed_growth if observed_growth is not None else 0.0)
    )
    spreads = {
        "base": base_growth,
        "bull": base_growth + value_delta_pp,
        "bear": base_growth - value_delta_pp,
    }
    for name, g in spreads.items():
        predicted = round(m.current_value * (1 + g / 100.0), 4)
        level = base_level if name == "base" else _notch_down(base_level)
        results.append(
            ScenarioResult(
                scenario=name,
                predicted_value=predicted,
                growth_pct=round(g, 2),
                direction=_direction(m.current_value, predicted),
                confidence=level,
                assumptions=_value_assumptions(name, observed_growth, g, has_prior),
                explanation=(
                    f"{m.metric_name}: {m.current_value:g} → {predicted:g} ({g:+.1f}%)."
                ),
            )
        )
    return results


def _value_assumptions(name: str, observed: float | None, applied: float, has_prior: bool) -> list[str]:
    base = (
        f"Observed period-over-period growth {observed:+.1f}%."
        if has_prior and observed is not None
        else "No prior-period value found; assuming flat trend."
    )
    tail = {
        "base": "Base: continue the observed trend.",
        "bull": f"Bull: stronger demand / catalyst → +{applied - (observed or 0):.1f}pp vs base.",
        "bear": f"Bear: weaker demand / margin pressure → {applied - (observed or 0):.1f}pp vs base.",
    }[name]
    return [base, tail]


def _margin_assumptions(name: str, observed: float | None, applied: float, has_prior: bool) -> list[str]:
    base = (
        f"Observed margin change {observed:+.1f}pp."
        if has_prior
        else "No prior-period margin; assuming stable margin."
    )
    tail = {
        "base": "Base: continue the observed margin trajectory.",
        "bull": "Bull: margin expansion (mix / operating leverage).",
        "bear": "Bear: margin compression (cost / pricing pressure).",
    }[name]
    return [base, tail]
