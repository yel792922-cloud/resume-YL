"""Configurable external forecast factors + a Custom-scenario growth model.

The base/bull/bear scenarios stay driven by the report's own trend (see
``engine.py``). This module adds a *user-configurable* layer: a catalog of
external drivers (macro, FX, competition, …), each with a weight in
``-2..+2``, that the Custom scenario turns into an explainable growth
adjustment.

Everything here is transparent and traceable — a weight maps to a fixed
per-unit sensitivity, and every contribution is reported back so the UI can
show *which* assumption moved the number and by how much. Nothing is a
black box, and no external market data is fetched (these are user assumptions).
"""
from __future__ import annotations

from dataclasses import dataclass

# Growth-percentage-points contributed per unit of weight, per factor. Small and
# uniform so the Custom scenario stays a gentle, explainable tilt rather than a
# wild swing: a single factor at max strength (+2) adds +2.4pp of growth.
SENSITIVITY_PP = 1.2

# The built-in driver catalog. `id` is stable (API/UI contract); labels are
# bilingual. Order is the display order.
_FACTORS: tuple[tuple[str, str, str], ...] = (
    ("market_expansion", "Market Expansion", "市场扩张"),
    ("market_contraction", "Market Contraction", "市场收缩"),
    ("macro", "Macroeconomic Conditions", "宏观经济"),
    ("interest_rates", "Interest Rates", "利率"),
    ("exchange_rate", "Exchange Rate", "汇率"),
    ("regulatory", "Regulatory Pressure", "监管压力"),
    ("competition", "Competition", "竞争强度"),
    ("sentiment", "Public Sentiment", "公众情绪"),
    ("input_cost", "Input Cost Inflation", "成本通胀"),
    ("supply_chain", "Supply Chain", "供应链"),
    ("consumer_demand", "Consumer Demand", "消费需求"),
)

FACTOR_IDS: frozenset[str] = frozenset(f[0] for f in _FACTORS)
WEIGHT_MIN, WEIGHT_MAX = -2, 2


@dataclass(frozen=True)
class FactorDef:
    id: str
    label_en: str
    label_zh: str


@dataclass(frozen=True)
class FactorContribution:
    id: str
    label_en: str
    label_zh: str
    weight: int
    contribution_pp: float   # growth pp this factor adds (can be negative)


def factor_catalog() -> list[FactorDef]:
    """The selectable factors, for the UI to render weight controls."""
    return [FactorDef(i, en, zh) for i, en, zh in _FACTORS]


def _clamp_weight(w) -> int:
    try:
        wi = int(round(float(w)))
    except (TypeError, ValueError):
        return 0
    return max(WEIGHT_MIN, min(WEIGHT_MAX, wi))


def normalize_weights(weights: dict[str, object] | None) -> dict[str, int]:
    """Keep only known factors, clamp to the allowed range, drop zeros."""
    if not weights:
        return {}
    out: dict[str, int] = {}
    for fid, w in weights.items():
        if fid in FACTOR_IDS:
            wi = _clamp_weight(w)
            if wi != 0:
                out[fid] = wi
    return out


_LABELS = {i: (en, zh) for i, en, zh in _FACTORS}


def contributions(weights: dict[str, int]) -> list[FactorContribution]:
    """Per-factor growth contributions, largest absolute impact first."""
    items = [
        FactorContribution(
            id=fid,
            label_en=_LABELS[fid][0],
            label_zh=_LABELS[fid][1],
            weight=w,
            contribution_pp=round(w * SENSITIVITY_PP, 2),
        )
        for fid, w in weights.items()
    ]
    items.sort(key=lambda c: abs(c.contribution_pp), reverse=True)
    return items


def external_growth_adjustment_pp(weights: dict[str, int]) -> float:
    """Total growth-pp adjustment the weighted factors add to the Custom base."""
    return round(sum(w * SENSITIVITY_PP for w in weights.values()), 2)
